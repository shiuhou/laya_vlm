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
from pathlib import Path
import random
import subprocess
import sys
import time

import numpy as np

from ..adapters.libero_sensor_env import LiberoSensorEnv
from ..contracts import content_hash, require
from ..perception.recording import FrameRecorder, replay_frames
from ..perception.surface_association import sensor_view_identity
from .p1_segmentation_probe import read, write, seal
from .records import code_identity, file_hash, versions

TASK = 'KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet'
CAMERAS = ('agentview', 'robot0_eye_in_hand')
SETTLE_ACTION = (0., 0., 0., 0., 0., 0., -1.)
SETTLE_TICKS = 10


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


def capture_seed(seed, output, *, dev_only, libero_root='/home/junhongli/projects/LIBERO',
                 config_dir='/tmp/laya-localizer-fresh-libero', factory=create_environment,
                 sensor_factory=LiberoSensorEnv, audit_writer=save_audit):
    """One constructor, one native reset, ten settling ticks, one sensor bundle."""
    require(dev_only is True, 'development-only capture must be explicit')
    require(type(seed) is int and 0 <= seed < 2**32, 'uint32 seed required')
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    audit = root/'collector-audit'
    audit.mkdir()
    sensor_root = root/'sensor'
    sensor_root.mkdir()
    world = sensor = None
    stage, reset_attempts, settle_ticks = 'CONSTRUCTOR', 0, 0
    receipt = dict(schema='p1-localizer-fresh-capture/1', seed=seed, dev_only=True,
        task=TASK, width=384, height=256, cameras=list(CAMERAS), code=code_identity(), versions=versions(),
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
        stage = 'SENSOR_CAPTURE'
        sensor = sensor_factory(world, camera_names=CAMERAS, width=384, height=256,
                                retained_gripper_command=lambda: 'OPEN')
        with FrameRecorder(sensor_root/'frames', episode_id=f'p1-localizer-dev/seed{seed}',
                           clock_domain='localizer-fresh/local-process', condition='fresh-sampled-reset-development/1') as recorder:
            bundle = sensor.sensor_port().capture()
            recorder.append(bundle['views'], bundle['proprio'], emitted_monotonic_ns=time.monotonic_ns())
        recorded = list(replay_frames(sensor_root/'frames'))
        require(len(recorded) == 1, 'exactly one first capture bundle required')
        envelope, views = recorded[0]
        sources = [sensor_view_identity(dict(view, frame_id=view['canonical_frame_id'])) for view in views]
        write(sensor_root/'manifest.json', dict(schema='p1-localizer-sensor-capture/1', seed=seed, dev_only=True,
            episode_id=envelope.episode_id, width=384, height=256, cameras=list(CAMERAS),
            source_identities=sources, recording='frames', allowed_inputs=['RGB', 'metric_depth', 'K', 'T_base_camera', 'robot_proprioception'],
            evaluation_labels_used=False, oracle_inputs=False, novelty_status='NOT_AUDITED', heldout_claim=False))
        seal(sensor_root)
        write(root/'result.json', dict(status='CAPTURE_COMPLETE', seed=seed, explicit_reset_attempts=reset_attempts,
            settle_ticks_completed=settle_ticks, sensor_manifest_sha256=file_hash(sensor_root/'manifest.json'),
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


def capture_batch(seeds, output, *, dev_only, libero_root, config_dir, timeout_s=180):
    require(dev_only is True and seeds and len(seeds) == len(set(seeds))
            and all(type(s) is int and 0 <= s < 2**32 for s in seeds), 'unique explicit development seeds required')
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    write(root/'registration.json', dict(schema='p1-localizer-fresh-batch/1', seeds=seeds, dev_only=True,
        per_seed_fresh_process=True, timeout_s=timeout_s, retry_count=0, novelty_status='NOT_AUDITED', code=code_identity()))
    results = []
    try:
        for seed in seeds:
            folder = root/f'seed-{seed}'
            command = [sys.executable, '-m', 'embodied_runtime.experiments.p1_localizer_capture', '--single',
                '--seed', str(seed), '--output', str(folder), '--dev-only', '--libero-root', libero_root,
                '--config-dir', str(Path(config_dir)/f'seed-{seed}')]
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
    parser.add_argument('--single', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/tmp/laya-localizer-fresh-libero')
    args = parser.parse_args()
    require(not args.single or len(args.seeds) == 1, 'single child requires one seed')
    if args.single:
        capture_seed(args.seeds[0], args.output, dev_only=args.dev_only, libero_root=args.libero_root, config_dir=args.config_dir)
    else:
        capture_batch(args.seeds, args.output, dev_only=args.dev_only, libero_root=args.libero_root, config_dir=args.config_dir)


if __name__ == '__main__':
    main()
