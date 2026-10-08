"""Bounded fresh sampled-reset capture, development only; no perception/control.

Each seed runs in its own process. Full state is collector-audit-only, separately
stored from the sensor recording. There is no old .init load, wrapper reset retry,
success-based selection, replacement seed, approach or PUSH. This tool does not
certify novelty or held-out independence; a separate audit must establish that.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import math
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np

from ..adapters.libero_sensor_env import LiberoSensorEnv, quaternion_xyzw
from ..contracts import canonical_json, content_hash, require
from ..perception.recording import FrameRecorder, replay_frames
from ..perception.surface_association import sensor_view_identity
from .p1_segmentation_probe import read, write, seal
from .records import code_identity, file_hash, versions

TASK = 'KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet'
CAMERAS = ('agentview', 'robot0_eye_in_hand')
SETTLE_ACTION = (0., 0., 0., 0., 0., 0., -1.)
SETTLE_TICKS = 10
WORKSPACE_FRONT = dict(condition="fixed-workspace-front/1", camera_id="frontview",
    position_world_m=[0., .7, 1.35], look_at_world_m=[0., 0., 1.05], world_up=[0., 0., 1.],
    vertical_fov_deg=45., world_reference="fixed workspace origin; configured table z=0.90m",
    source="explicit workspace camera configuration; no robot/object/target pose input")


def camera_look_at_rotation(position, look_at, world_up):
    """MuJoCo camera-to-world rotation: local -Z looks forward, +Y is up."""
    position, target, up = (np.asarray(x, dtype=float) for x in (position, look_at, world_up))
    require(all(x.shape == (3,) and np.isfinite(x).all() for x in (position, target, up)),
            'finite xyz camera configuration required')
    forward = target-position
    require(np.linalg.norm(forward) > 1e-12 and np.linalg.norm(up) > 1e-12, 'nonzero camera direction/up required')
    forward = forward/np.linalg.norm(forward)
    right = np.cross(forward, up)
    require(np.linalg.norm(right) > 1e-12, 'look direction and up must not be parallel')
    right = right/np.linalg.norm(right)
    actual_up = np.cross(right, forward)
    return np.column_stack((right, actual_up, -forward))


def configure_workspace_camera(world):
    """Configure only the unused world-mounted frontview; never aim at a body."""
    sim = world.env.sim
    model = sim.model
    camera = model.camera_name2id(WORKSPACE_FRONT['camera_id'])
    require(int(model.cam_bodyid[camera]) == 0, 'workspace front camera must be world-mounted')
    require(int(model.cam_mode[camera]) == 0, 'workspace front camera must use fixed pose mode')
    before = {name: (np.array(model.cam_pos[model.camera_name2id(name)]),
                    np.array(model.cam_quat[model.camera_name2id(name)]),
                    float(model.cam_fovy[model.camera_name2id(name)])) for name in CAMERAS}
    rotation = camera_look_at_rotation(WORKSPACE_FRONT['position_world_m'],
        WORKSPACE_FRONT['look_at_world_m'], WORKSPACE_FRONT['world_up'])
    xyzw = quaternion_xyzw(rotation)
    wxyz = np.roll(xyzw, 1)
    clock = float(sim.data.time)
    model.cam_pos[camera] = WORKSPACE_FRONT['position_world_m']
    model.cam_quat[camera] = wxyz
    model.cam_fovy[camera] = WORKSPACE_FRONT['vertical_fov_deg']
    sim.forward()
    require(float(sim.data.time) == clock, 'camera configuration must not advance simulation')
    for name, (position, quaternion, fovy) in before.items():
        index = model.camera_name2id(name)
        require(np.array_equal(model.cam_pos[index], position)
                and np.array_equal(model.cam_quat[index], quaternion) and model.cam_fovy[index] == fovy,
                'original camera configuration changed')
    return dict(**WORKSPACE_FRONT, quaternion_camera_to_world_wxyz=wxyz.tolist(),
                rotation_camera_to_world=rotation.tolist(), camera_mount_body_id=0,
                camera_mount_body_name=model.body_id2name(0), camera_mode='fixed',
                original_camera_configs_preserved=True, no_scene_state_used_for_aim=True)


class SensorWorld:
    """Trusted sensing facade; no Jev task features or execution/policy methods."""
    __slots__ = ('env', 'render_enabled')

    def __init__(self, env):
        self.env, self.render_enabled = env, True

    @property
    def data(self):
        return self.env.sim.data._data

    def close(self):
        self.env.close()


def create_environment(*, libero_root, config_dir):
    # Only environment construction is reused. World()/suite init states are not.
    from jev_libero.environment import load_libero
    _, control_env, assets, _ = load_libero(libero_root, config_dir)
    bddl = assets/'bddl_files'/'libero_90'/f'{TASK}.bddl'
    require(bddl.is_file(), 'same task BDDL required')
    env = control_env(bddl_file_name=str(bddl), use_camera_obs=False,
        has_renderer=False, has_offscreen_renderer=True, camera_heights=384, camera_widths=384)
    return SensorWorld(env), dict(bddl_path=str(bddl), bddl_sha256=file_hash(bddl),
        task=TASK, environment_constructor='ControlEnv', use_camera_obs=False,
        implicit_constructor_initialization=True, constructor_state_used_for_capture=False)


def rng_state():
    state = np.random.get_state()
    return dict(numpy=dict(generator=state[0], keys=state[1].tolist(), position=state[2],
        has_gauss=state[3], cached_gaussian=state[4]), python=random.getstate())


def scene_layout(env):
    """Audit-only nonrobot layout. Excludes simulation time, qvel and robot state."""
    native, sim = env.env, env.sim
    objects = []
    for category, collection in (('fixture', native.fixtures_dict), ('object', native.objects_dict)):
        for name, obj in sorted(collection.items()):
            body = sim.model.body_name2id(obj.root_body)
            joints = {}
            for joint in obj.joints:
                joints[joint] = np.asarray(sim.data.get_joint_qpos(joint), dtype=float).tolist()
            objects.append(dict(kind=category, name=name, root_body=obj.root_body,
                world_position_m=np.asarray(sim.data.body_xpos[body], dtype=float).tolist(),
                world_quaternion_wxyz=np.asarray(sim.data.body_xquat[body], dtype=float).tolist(),
                model_position_parent_m=np.asarray(sim.model.body_pos[body], dtype=float).tolist(),
                model_quaternion_parent_wxyz=np.asarray(sim.model.body_quat[body], dtype=float).tolist(),
                joint_qpos=joints))
    require(bool(objects), 'audit needs nonrobot scene members')
    return dict(nonrobot_objects=objects, excludes=['simulation_time', 'robot_qpos', 'qvel', 'controller_state'],
                evaluator_only=True, runtime_may_read=False)


def save_audit(world, output):
    output.mkdir(exist_ok=False)
    sim = world.env.sim
    xml = sim.model.get_xml()
    (output/'model.xml').write_text(xml)
    np.savez_compressed(output/'state.npz', qpos=np.array(sim.data.qpos), qvel=np.array(sim.data.qvel),
        act=np.array(sim.data.act), ctrl=np.array(sim.data.ctrl), time=np.asarray(float(sim.data.time)),
        flattened_sim_state=np.asarray(sim.get_state().flatten()), model_body_pos=np.array(sim.model.body_pos),
        model_body_quat=np.array(sim.model.body_quat))
    layout = scene_layout(world.env)
    identity = dict(scene_layout=layout, scene_fingerprint_sha256=content_hash(layout),
        xml_sha256=file_hash(output/'model.xml'), state_sha256=file_hash(output/'state.npz'),
        rng=rng_state(), evaluator_only=True, runtime_may_read=False,
        novelty_status='NOT_AUDITED', excludes_clock_from_scene_fingerprint=True)
    write(output/'audit.json', identity)
    seal(output)
    return dict(scene_fingerprint_sha256=identity['scene_fingerprint_sha256'],
                xml_sha256=identity['xml_sha256'], audit_seal_sha256=file_hash(output/'sealed.json'))



def capture_schedule(*, frames=None, duration_s=None, capture_hz=10.):
    require(type(capture_hz) in (int, float) and np.isfinite(capture_hz) and 0 < capture_hz <= 20,
            'capture cadence must be positive and at most native20Hz control')
    require(frames is None or duration_s is None, 'choose frame slots or duration, not both')
    if duration_s is not None:
        require(type(duration_s) in (int, float) and np.isfinite(duration_s) and duration_s > 0,
                'positive bounded duration required')
        frames = math.ceil(duration_s*capture_hz)
    else:
        frames = 1 if frames is None else frames
    require(type(frames) is int and 1 <= frames <= 10000, 'bounded1..10000 scheduled slots required')
    return dict(planned_slots=frames, capture_hz=float(capture_hz), period_ns=round(1e9/capture_hz),
                requested_duration_s=duration_s, native_control_hz=20.,
                missed_slot_policy='record DROPPED_DEADLINE; no replacement or burst catch-up',
                failure_policy='record FAILED and NOT_ATTEMPTED_AFTER_FAILURE; stop')



def record_warmup(sensor, recorder, event_stream, count, *, clock_ns=time.monotonic_ns):
    """Explicit render priming: sensor access only, no simulator step capability."""
    require(type(count) is int and 1 <= count <= 16, 'bounded1..16 priming captures required')
    anchor = clock_ns()
    events, first_sim = [], None
    for index in range(count):
        started = clock_ns()
        try:
            bundle = sensor.sensor_port().capture()
            captured = clock_ns()
            sim_times = [v['capture_sim_time_s'] for v in bundle['views']]
            if first_sim is None:
                first_sim = sim_times
            require(sim_times == first_sim, 'priming must not advance simulation')
            emitted = clock_ns()
            message = recorder.append(bundle['views'], bundle['proprio'], emitted_monotonic_ns=emitted)
            finished = clock_ns()
            capture_ns = [v['capture_monotonic_ns'] for v in bundle['views']]
            event = dict(warmup_index=index, status='CAPTURED', reason='GPU_RENDER_INITIALIZATION',
                capture_started_monotonic_ns=started, capture_finished_monotonic_ns=captured,
                emitted_monotonic_ns=emitted, frame_write_finished_monotonic_ns=finished,
                capture_duration_s=(captured-started)/1e9, capture_sim_time_s=sim_times,
                oldest_view_age_at_write_s=(finished-min(capture_ns))/1e9,
                view_capture_monotonic_ns=capture_ns, bundle_message_id=message.message_id,
                source_ids=[f"{recorder.episode_id}/{v['camera_id']}/{v['frame_seq']}" for v in bundle['views']],
                timestamps_fabricated=False, excluded_from_warm_cadence_only=True, simulator_steps=0)
        except Exception as exc:
            event = dict(warmup_index=index, status='FAILED', reason='GPU_RENDER_INITIALIZATION',
                exception_type=type(exc).__name__, error=repr(exc), observed_monotonic_ns=clock_ns(),
                source_ids=[], simulator_steps=0)
            event_stream.write(canonical_json(event)+'\n')
            for rest in range(index+1, count):
                event_stream.write(canonical_json(dict(warmup_index=rest, status='NOT_ATTEMPTED_AFTER_FAILURE', source_ids=[]))+'\n')
            event_stream.flush()
            raise
        events.append(event)
        event_stream.write(canonical_json(event)+'\n')
        event_stream.flush()
    return dict(requested_captures=count, captured_bundles=len(events), wall_elapsed_s=(clock_ns()-anchor)/1e9,
        reason='GPU_RENDER_INITIALIZATION', simulator_steps=0, capture_records=events,
        cold_start_is_preserved=True, excluded_from_warm_cadence_only=True, timestamps_fabricated=False)


def record_sequence(world, sensor, recorder, event_stream, schedule, *, clock_ns=time.monotonic_ns, sleep=time.sleep):
    """Real acquisition timestamps survive; desired cadence never substitutes for them."""
    anchor = clock_ns()
    events, hold_ticks = [], 0
    def emit(event):
        events.append(event)
        event_stream.write(canonical_json(event)+'\n')
        event_stream.flush()
    for slot in range(schedule['planned_slots']):
        deadline = anchor + slot*schedule['period_ns']
        current = clock_ns()
        if current < deadline:
            sleep((deadline-current)/1e9)
            current = clock_ns()
        event = dict(slot_index=slot, scheduled_monotonic_ns=deadline, observed_start_monotonic_ns=current,
                     scheduling_lateness_ns=max(0, current-deadline), hold_ticks_before=hold_ticks)
        if slot > 0 and current-deadline >= schedule['period_ns']:
            emit(dict(event, status='DROPPED_DEADLINE', hold_ticks_after=hold_ticks,
                      source_ids=[], timestamps_fabricated=False))
            continue
        try:
            target_ticks = math.floor(slot*schedule['native_control_hz']/schedule['capture_hz'] + 1e-9)
            while hold_ticks < target_ticks:
                world.env.step(list(SETTLE_ACTION))  # Zero arm / retained OPEN only, no approach policy.
                hold_ticks += 1
            start = clock_ns()
            bundle = sensor.sensor_port().capture()
            capture_finished = clock_ns()
            emitted = clock_ns()
            message = recorder.append(bundle['views'], bundle['proprio'], emitted_monotonic_ns=emitted)
            finished = clock_ns()
            captures = [v['capture_monotonic_ns'] for v in bundle['views']]
            source_ids = [f"{recorder.episode_id}/{v['camera_id']}/{v['frame_seq']}" for v in bundle['views']]
            emit(dict(event, status='CAPTURED', capture_started_monotonic_ns=start,
                capture_finished_monotonic_ns=capture_finished, emitted_monotonic_ns=emitted,
                frame_write_finished_monotonic_ns=finished, hold_ticks_after=hold_ticks,
                source_ids=source_ids, bundle_message_id=message.message_id,
                view_capture_monotonic_ns=captures,
                capture_sim_time_s=[v['capture_sim_time_s'] for v in bundle['views']],
                capture_duration_s=(capture_finished-start)/1e9,
                oldest_view_age_at_write_s=(finished-min(captures))/1e9,
                timestamps_fabricated=False))
        except Exception as exc:
            emit(dict(event, status='FAILED', exception_type=type(exc).__name__, error=repr(exc),
                      finished_monotonic_ns=clock_ns(), hold_ticks_after=hold_ticks,
                      source_ids=[], timestamps_fabricated=False))
            for rest in range(slot+1, schedule['planned_slots']):
                emit(dict(slot_index=rest, scheduled_monotonic_ns=anchor+rest*schedule['period_ns'],
                          status='NOT_ATTEMPTED_AFTER_FAILURE', source_ids=[], timestamps_fabricated=False))
            raise
    end = clock_ns()
    captured = [e for e in events if e['status'] == 'CAPTURED']
    def percentiles(values):
        return dict(n=len(values), p50_s=float(np.percentile(values, 50)) if values else None,
                    p95_s=float(np.percentile(values, 95)) if values else None)
    return dict(**schedule, captured_bundles=len(captured), dropped_slots=sum(e['status']=='DROPPED_DEADLINE' for e in events),
        failed_slots=0, continuous_hold_ticks=hold_ticks, actual_wall_elapsed_s=(end-anchor)/1e9,
        actual_producer_hz=len(captured)/((end-anchor)/1e9) if end > anchor else None,
        camera_capture_time=percentiles([e['capture_duration_s'] for e in captured]),
        oldest_view_age_at_write=percentiles([e['oldest_view_age_at_write_s'] for e in captured]),
        actual_capture_cadence_hz=(len(captured)-1)/((captured[-1]['view_capture_monotonic_ns'][0]-captured[0]['view_capture_monotonic_ns'][0])/1e9)
            if len(captured)>1 and captured[-1]['view_capture_monotonic_ns'][0]>captured[0]['view_capture_monotonic_ns'][0] else None,
        geometry_or_tracking_throughput_measured=False, replay_is_not_live_freshness=True,
        hold_motion_only=True, approach_or_push=False)


def capture_seed(seed, output, *, dev_only, libero_root='/home/junhongli/projects/LIBERO',
                 config_dir='/tmp/laya-localizer-fresh-libero', workspace_front=False, frontview_only=False, frames=None, duration_s=None, capture_hz=10., width=384, height=256, warmup_captures=0, factory=create_environment,
                 sensor_factory=LiberoSensorEnv, audit_writer=save_audit):
    """One reset and ten settling ticks, then bounded sensor slots (default one)."""
    require(dev_only is True, 'development-only capture must be explicit')
    require(type(seed) is int and 0 <= seed < 2**32, 'uint32 seed required')
    require(type(width) is int and type(height) is int and min(width, height) > 0, 'positive native render dimensions required')
    require(type(workspace_front) is bool, 'explicit camera flag required')
    require(type(warmup_captures) is int and 0 <= warmup_captures <= 16, 'bounded0..16 explicit priming captures required')
    require(type(frontview_only) is bool and (not frontview_only or workspace_front), 'frontview-only requires workspace-front')
    cameras = ('frontview',) if frontview_only else CAMERAS + (('frontview',) if workspace_front else ())
    schedule = capture_schedule(frames=frames, duration_s=duration_s, capture_hz=capture_hz)
    condition = 'fresh-sampled-reset-workspace-front-development/1' if workspace_front else 'fresh-sampled-reset-development/1'
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    audit = root/'collector-audit'
    audit.mkdir()
    sensor_root = root/'sensor'
    sensor_root.mkdir()
    world = sensor = None
    sequence_stats = None
    warmup_stats = None
    warmup_sources = []
    stage, reset_attempts, settle_ticks = 'CONSTRUCTOR', 0, 0
    receipt = dict(schema='p1-localizer-fresh-capture/1', seed=seed, dev_only=True,
        task=TASK, width=width, height=height, resolution_source="native_simulator_render_no_interpolation", cameras=list(cameras), warmup_captures=warmup_captures, capture_schedule=schedule, frontview_only=frontview_only, camera_condition=WORKSPACE_FRONT if workspace_front else None, code=code_identity(), versions=versions(),
        process_id=os.getpid(), executable=sys.executable, started_at_utc=datetime.now(timezone.utc).isoformat(),
        render_environment={k:os.environ.get(k) for k in ('MUJOCO_GL', 'MUJOCO_EGL_DEVICE_ID', 'CUDA_VISIBLE_DEVICES')},
        settle_action=list(SETTLE_ACTION), settle_ticks_planned=SETTLE_TICKS, explicit_reset_attempts=0,
        old_init_file_loaded=False, retry_count=0, evaluation_labels_used=False, model_inference=False,
        control_phase_started=False, novelty_status='NOT_AUDITED', heldout_claim=False)
    write(root/'registration.json', receipt)
    try:
        random.seed(seed)
        np.random.seed(seed)
        write(audit/'rng-before-constructor.json', rng_state())
        world, construction = factory(libero_root=libero_root, config_dir=config_dir)
        write(audit/'constructor.json', dict(**construction, rng_after_constructor=rng_state()))
        # Bypass ControlEnv.reset(): it loops forever on RandomizationError.
        stage = 'NATIVE_RESET'
        world.env.seed(seed)
        random.seed(seed)
        write(audit/'rng-before-explicit-reset.json', rng_state())
        reset_attempts += 1
        world.env.env.reset()
        world.env.sim.forward()
        initial = audit_writer(world, audit/'post-reset')
        stage = 'SETTLING'
        for _ in range(SETTLE_TICKS):
            world.env.step(list(SETTLE_ACTION))  # Initialization only; returned reward/done are not read.
            settle_ticks += 1
        world.env.sim.forward()
        settled = audit_writer(world, audit/'post-settle')
        if workspace_front:
            stage = 'WORKSPACE_CAMERA_CONFIGURATION'
            write(audit/'workspace-camera.json', configure_workspace_camera(world))
        stage = 'SENSOR_CAPTURE'
        sensor = sensor_factory(world, camera_names=cameras, width=width, height=height,
                                retained_gripper_command=lambda: 'OPEN')
        if warmup_captures:
            stage = 'RENDER_PRIMING'
            with FrameRecorder(sensor_root/'warmup-frames', episode_id=f'p1-localizer-dev/seed{seed}/warmup',
                               clock_domain='localizer-fresh/local-process', condition='render-priming-explicit/1') as warm_recorder, \
                    (sensor_root/'warmup-attempts.jsonl').open('x') as warm_events:
                warmup_stats = record_warmup(sensor, warm_recorder, warm_events, warmup_captures)
            warmup_sources = [sensor_view_identity(dict(v, frame_id=v['canonical_frame_id']))
                              for _, views in replay_frames(sensor_root/'warmup-frames') for v in views]
            write(sensor_root/'warmup-statistics.json', warmup_stats)
        stage = 'SENSOR_CAPTURE'
        with FrameRecorder(sensor_root/'frames', episode_id=f'p1-localizer-dev/seed{seed}',
                           clock_domain='localizer-fresh/local-process', condition=condition) as recorder, \
                (sensor_root/'capture-attempts.jsonl').open('x') as attempts:
            sequence_stats = record_sequence(world, sensor, recorder, attempts, schedule)
        sequence_stats.update(warmup_captures=warmup_captures,
            cadence_condition='EXPLICIT_RENDER_PRIMING_COMPLETE' if warmup_captures else 'COLD_START_INCLUDED',
            cold_start_receipt='warmup-statistics.json' if warmup_captures else 'capture-attempts.jsonl')
        recorded = list(replay_frames(sensor_root/'frames'))
        require(len(recorded) == sequence_stats['captured_bundles'] and len(recorded) > 0,
                'complete recorded successful slots required')
        envelope = recorded[0][0]
        sources = [sensor_view_identity(dict(view, frame_id=view['canonical_frame_id'])) for _, views in recorded for view in views]
        write(sensor_root/'capture-statistics.json', sequence_stats)
        write(sensor_root/'manifest.json', dict(schema='p1-localizer-sensor-capture/1', seed=seed, dev_only=True,
            episode_id=envelope.episode_id, width=width, height=height, resolution_source="native_simulator_render_no_interpolation", cameras=list(cameras), camera_condition=WORKSPACE_FRONT if workspace_front else None,
            source_identities=sources, warmup_source_identities=warmup_sources, warmup_recording='warmup-frames' if warmup_captures else None, warmup_statistics=warmup_stats, frame_bundle_count=len(recorded), capture_statistics=sequence_stats, recording='frames', allowed_inputs=['RGB', 'metric_depth', 'K', 'T_base_camera', 'robot_proprioception'],
            evaluation_labels_used=False, oracle_inputs=False, novelty_status='NOT_AUDITED', heldout_claim=False))
        seal(sensor_root)
        write(root/'result.json', dict(status='CAPTURE_COMPLETE', seed=seed, explicit_reset_attempts=reset_attempts,
            settle_ticks_completed=settle_ticks, warmup_statistics=warmup_stats, capture_statistics=sequence_stats, sensor_manifest_sha256=file_hash(sensor_root/'manifest.json'),
            audit_only_reset_identity=initial, audit_only_settled_identity=settled,
            stage='COMPLETE', dev_only=True, novelty_status='NOT_AUDITED', heldout_claim=False))
    except Exception as exc:
        write(root/'failure.json', dict(status='FAILED', stage=stage, seed=seed, exception_type=type(exc).__name__,
            error=repr(exc), explicit_reset_attempts=reset_attempts, settle_ticks_completed=settle_ticks,
            retry_count=0, replacement_seed=None, retained_partial_evidence=True))
        raise
    finally:
        if sensor is not None:
            sensor.close()
        if world is not None:
            world.close()
        seal(root)
    return read(root/'result.json')


def capture_batch(seeds, output, *, dev_only, libero_root, config_dir, workspace_front=False, frontview_only=False, frames=None, duration_s=None, capture_hz=10., width=384, height=256, warmup_captures=0, timeout_s=180):
    require(dev_only is True and seeds and len(seeds) == len(set(seeds))
            and all(type(s) is int and 0 <= s < 2**32 for s in seeds), 'unique explicit development seeds required')
    require(type(width) is int and type(height) is int and min(width, height) > 0, 'positive native render dimensions required')
    require(type(warmup_captures) is int and 0 <= warmup_captures <= 16, 'bounded0..16 explicit priming captures required')
    schedule = capture_schedule(frames=frames, duration_s=duration_s, capture_hz=capture_hz)
    require(not frontview_only or workspace_front, 'frontview-only requires workspace-front')
    timeout_s = max(timeout_s, schedule['planned_slots']/capture_hz + 180)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    write(root/'registration.json', dict(schema='p1-localizer-fresh-batch/1', seeds=seeds, dev_only=True,
        per_seed_fresh_process=True, warmup_captures=warmup_captures, width=width, height=height, resolution_source="native_simulator_render_no_interpolation", workspace_front=workspace_front, frontview_only=frontview_only, capture_schedule=schedule, timeout_s=timeout_s, retry_count=0, novelty_status='NOT_AUDITED', code=code_identity()))
    results = []
    try:
        for seed in seeds:
            folder = root/f'seed-{seed}'
            command = [sys.executable, '-m', 'embodied_runtime.experiments.p1_localizer_capture', '--single',
                '--seed', str(seed), '--output', str(folder), '--dev-only', '--libero-root', libero_root,
                '--config-dir', str(Path(config_dir)/f'seed-{seed}')]
            command.extend(['--capture-hz', str(capture_hz), '--width', str(width), '--height', str(height), '--warmup-captures', str(warmup_captures)])
            if duration_s is not None:
                command.extend(['--duration-s', str(duration_s)])
            elif frames is not None:
                command.extend(['--frames', str(frames)])
            if workspace_front:
                command.append('--workspace-front')
            if frontview_only:
                command.append('--frontview-only')
            started = datetime.now(timezone.utc).isoformat()
            with (root/f'seed-{seed}.log').open('x') as log:
                try:
                    run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s)
                    code, timeout = run.returncode, False
                except subprocess.TimeoutExpired:
                    code, timeout = None, True
            process = dict(seed=seed, command=command, started_at_utc=started,
                finished_at_utc=datetime.now(timezone.utc).isoformat(), exit_code=code, timeout=timeout, retry_count=0)
            write(root/f'seed-{seed}-process.json', process)
            results.append(process)
            if code != 0 or timeout:
                break  # Preserve first failure, no resample or additional sequence after failure.
        attempted = {r['seed'] for r in results}
        write(root/'summary.json', dict(results=results, unattempted_seeds=[s for s in seeds if s not in attempted],
            status='COMPLETE' if len(results) == len(seeds) and all(r['exit_code'] == 0 for r in results) else 'STOPPED_ON_FAILURE',
            dev_only=True, novelty_status='NOT_AUDITED', heldout_claim=False))
    finally:
        seal(root)
    return read(root/'summary.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', '--seeds', nargs='+', type=int, required=True, dest='seeds')
    parser.add_argument('--output', required=True)
    parser.add_argument('--dev-only', action='store_true')
    parser.add_argument('--workspace-front', action='store_true', help='Add explicitly configured world-mounted workspace front RGB-D camera')
    parser.add_argument('--frontview-only', action='store_true', help='Capture only configured frontview; requires workspace-front')
    bound = parser.add_mutually_exclusive_group()
    bound.add_argument('--frames', type=int, help='Finite scheduled slots; dropped slots are not replaced')
    bound.add_argument('--duration-s', type=float, help='Finite scheduled window, not a guaranteed run walltime')
    parser.add_argument('--capture-hz', type=float, default=10.)
    parser.add_argument('--width', type=int, default=384, help='Native RGB-D render width; no interpolation')
    parser.add_argument('--height', type=int, default=256, help='Native RGB-D render height; no interpolation')
    parser.add_argument('--warmup-captures', type=int, default=0, help='Explicit no-step priming frames retained separately before timed slot0')
    parser.add_argument('--single', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/tmp/laya-localizer-fresh-libero')
    args = parser.parse_args()
    require(not args.single or len(args.seeds) == 1, 'single child requires one seed')
    if args.single:
        capture_seed(args.seeds[0], args.output, dev_only=args.dev_only, libero_root=args.libero_root, config_dir=args.config_dir, workspace_front=args.workspace_front, frontview_only=args.frontview_only, frames=args.frames, duration_s=args.duration_s, capture_hz=args.capture_hz, width=args.width, height=args.height, warmup_captures=args.warmup_captures)
    else:
        capture_batch(args.seeds, args.output, dev_only=args.dev_only, libero_root=args.libero_root, config_dir=args.config_dir, workspace_front=args.workspace_front, frontview_only=args.frontview_only, frames=args.frames, duration_s=args.duration_s, capture_hz=args.capture_hz, width=args.width, height=args.height, warmup_captures=args.warmup_captures)


if __name__ == '__main__':
    main()
