"""Fresh Task2 approach to a sealed BOX median-ray proxy; passive oracle abort."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import sys
import time

import numpy as np

from ..decision_interface import (CanonicalDecisionInput, CanonicalDecisionState, Evidence,
    FIELD_NAMES, derive_relations, evidence, geometric_effects, shared_atomic_candidates)
from ..runtime_core import AtomicExecutor, MOVE
from .local_grasp_interface import contact_snapshot, native_observer, read_only_measurement
from .records import RunRecorder, code_identity, file_hash, load_records, package_directory, repository_identity, versions

ROOT = Path(__file__).resolve().parents[2]
RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
PROTOCOL = ROOT / 'docs/research/task2_box_point_boundary_protocol.md'
SOURCE_FILES = {
    'interaction-observability-paired-01/close/0000.npz': '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969',
    'task2-box-support-run-02/model-output.json': 'c0545950996092c7ea05d7e10cf115ff0ed3ec318d1b08ff729300d1ee8bb944',
    'task2-box-support-run-02/sensor-representation.json': 'be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead',
    'task2-box-support-run-02/episodes.jsonl': '51dd621269c6da151c39e9b1bd9b0cdf15a890eb2e4af28a59caaea065201a3b',
}
UNCHANGED_FILES = {
    'embodied_runtime/runtime_core.py': '04be07b6be4d287d9b93e6376fb837cfa1a914eb0f81d9d2cf90b7c7f16763c7',
    'embodied_runtime/decision_interface.py': '92c87afe4b28e90bc50ec25293bb09ca6a93c8d52b598ae465e36d4d54f4c917',
    'embodied_runtime/adapters/libero.py': 'f6988f2d72d63b8832e7323a583397eb41b5a3bc8cb6cc380ac420cf0833454f',
    'embodied_runtime/adapters/libero_rgbd.py': 'b9b2e58081f336517d97397037cb7a2e7a31198e18167670b96b6386d2844ab4',
    'embodied_runtime/experiments/local_grasp_interface.py': '17b5ec197ae55cdba6b4e0bd0725a4093c19760ed1446bd7f7c50037724291c7',
}
FRAME_KEYS = ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')
OBS_KEYS = ('robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos', 'robot0_gripper_qvel')


def read(path):
    return json.loads(Path(path).read_text())


def source_packet():
    for name, expected in SOURCE_FILES.items():
        if file_hash(RAW / name) != expected:
            raise ValueError('Frozen sensor source mismatch: ' + name)
    model = read(RAW / 'task2-box-support-run-02/model-output.json')
    sensor = read(RAW / 'task2-box-support-run-02/sensor-representation.json')
    records, errors = load_records(RAW / 'task2-box-support-run-02/episodes.jsonl')
    if errors or sum(r['kind'] == 'call_started' for r in records) != 1 or any(r['kind'] == 'failure' for r in records):
        raise ValueError('Complete single-call source journal required')
    audit = model['generation_audit']
    if model['parsed']['status'] != 'single_box' or not audit['terminal_eos_observed'] or audit['length_limit_reached']:
        raise ValueError('Complete single BOX required')
    point = np.asarray(sensor['point_P']['position_world_m'], dtype=float)
    if point.shape != (3,) or not np.isfinite(point).all() or sensor['status'] != 'candidate_support_recorded':
        raise ValueError('Sealed finite median-ray point required')
    with np.load(RAW / 'interaction-observability-paired-01/close/0000.npz', allow_pickle=False) as archive:
        frame = {key: archive[key] for key in FRAME_KEYS}
    if frame['rgb'].shape != (384, 384, 3) or frame['depth_m'].shape != (384, 384):
        raise ValueError('Actual source frame schema differs')
    return {'position_world_m': point.tolist(), 'box_xyxy': sensor['point_P']['box_xyxy'],
            'definition': 'cached_BOX_center_ray_at_fixed_crop_median_depth',
            'identity_verified': None, 'ownership': None, 'holding': None}, frame


def require_exact_frame(frame, reference):
    checks = {}
    for key in FRAME_KEYS:
        a, b = np.asarray(frame[key]), np.asarray(reference[key])
        checks[key] = bool(a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes())
    if not all(checks.values()):
        raise ValueError('Fresh initial RGB/depth/K/T mismatch: ' + str(checks))
    return checks


def decision(point, proprio, source_time, current_time, revision, history=()):
    age = float(current_time) - float(source_time)
    p = np.asarray(point['position_world_m'], dtype=float)
    if p.shape != (3,) or not np.isfinite(p).all() or age < 0 or not np.isfinite(age):
        raise ValueError('Finite fixed point and nonnegative age required')
    tcp = np.asarray(proprio['tcp_pos_world_m'], dtype=float)
    if tcp.shape != (3,) or not np.isfinite(tcp).all() or not np.isfinite(proprio['gripper_width_m']):
        raise ValueError('Finite own TCP and joint-aperture observation required')
    fields = {name: Evidence() for name in FIELD_NAMES}
    fields['task.instruction'] = evidence('Approach the cached reported point.', 'task', 'approach-only diagnostic')
    fields['task.target_identity'] = evidence('the wine bottle', 'task', 'requested description; not verified identity')
    for dest, source in (('tcp_position_m', 'tcp_pos_world_m'), ('gripper_width_m', 'gripper_width_m'), ('gripper_command', 'gripper_command')):
        fields['robot.' + dest] = evidence(proprio[source], 'proprioception', 'robot observation and retained command')
    fields['target.position_m'] = evidence(p.tolist(), 'sensor', 'unchanged cached BOX median-ray proxy; initial fresh frame exactly matched')
    fields['target.position_definition'] = evidence(point['definition'], 'sensor', 'not a surface centroid, rigid object center or grasp pose')
    fields['quality.geometry_valid'] = evidence(True, 'derived', 'finite proxy admitted under unverified fixed-target assumption')
    for key in ('geometry_age_s', 'semantic_age_s'):
        fields['quality.' + key] = evidence(age, 'sensor', 'time since fresh image equivalence gate; cached inference provenance retained')
    derive_relations(fields)
    state = CanonicalDecisionState(fields, {'revision': revision, 'asof_sim_time': float(current_time),
        'target_source_sim_time_s': float(source_time), 'target_refreshed': False,
        'new_model_calls': 0, 'tracking_active': False, 'stationarity_assumption_verified': None,
        'current_visibility_verified': None, 'robot_observation_exact_sample_time_s': None})
    candidates = tuple(c for c in shared_atomic_candidates() if c.token in {*MOVE, 'STOP'})
    return CanonicalDecisionInput(state, candidates, geometric_effects(state, candidates), history)


def above_threshold_robot_pairs(snapshot, robot):
    return {tuple(sorted(c['geom_ids'])) for c in snapshot['contacts']
            if c['normal_force_N'] > .05 and any(g in robot for g in c['geom_ids'])}


def contact_class(pair, groups):
    a, b = pair
    if a in groups['robot'] and b in groups['robot']:
        return 'self'
    if (a in groups['pads'] and b in groups['bottle']) or (b in groups['pads'] and a in groups['bottle']):
        return 'pad/bottle'
    if (a in groups['gripper'] and b in groups['bottle']) or (b in groups['gripper'] and a in groups['bottle']):
        return 'other_gripper/bottle'
    if a in groups['gripper'] or b in groups['gripper']:
        return 'gripper/other_scene'
    return 'arm/scene'


class PassiveContactRecorder:
    """Persist the first native contact observation; never interrupts execution."""
    def __init__(self, recorder, groups, initial):
        self.recorder, self.groups = recorder, groups
        self.baseline = above_threshold_robot_pairs(initial, groups['robot'])
        self.first = None
        self.previous = {'stage': 'initial', 'time_s': initial['time_s']}

    def record(self, kind, row):
        record_id = self.recorder.record(kind, row)
        if kind not in ('native_before', 'native_after'):
            return record_id
        current = {key: row[key] for key in ('step', 'control', 'index', 'time_s')}
        current.update(stage=kind, raw_record_id=record_id)
        new = sorted(above_threshold_robot_pairs(row, self.groups['robot']) - self.baseline)
        if new and self.first is None:
            self.first = {'previous_observed_sample': self.previous, 'first_observed_sample': current,
                'new_pairs': [{'geom_ids': list(pair), 'class': contact_class(pair, self.groups)} for pair in new],
                'stop_granularity': 'after already-started atomic primitive',
                'cache_semantics': 'native derived buffers; timestamps need not identify contact solve time'}
            self.recorder.record('first_new_robot_contact', self.first)
        self.previous = current
        return record_id


@contextmanager
def observe_controls(world, recorder, step, tracking):
    original, override, controls = world.env.step, world.env.__dict__.get('step'), []
    def observed(command):
        control = len(controls)
        if control >= 8 or not np.isfinite(command).all() or float(command[-1]) != -1:
            raise RuntimeError('Unexpected control count/command/grip')
        tracking['control'] = control
        recorder.record('control_started', {'step': step, 'control': control,
            'command': np.asarray(command).tolist(), 'state_before': world.env.sim.get_state().flatten().tolist(),
            'previous_returned_own_observations': {key: np.asarray(world.obs[key]).tolist() for key in OBS_KEYS}})
        returned = original(command)
        tracking['control'] = None
        row = {'step': step, 'control': control, 'command': np.asarray(command).tolist(),
               'state_after': world.env.sim.get_state().flatten().tolist(),
               'returned_own_observations': {key: np.asarray(returned[0][key]).tolist() for key in OBS_KEYS}}
        recorder.record('control_completed', row)
        controls.append(row)
        return returned
    world.env.step = observed
    try:
        yield controls
    finally:
        tracking['control'] = None
        if override is None:
            world.env.__dict__.pop('step', None)
        else:
            world.env.step = override


def preflight(args):
    point, frame = source_packet()
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('Commit protocol/code before preflight or physics')
    for name, expected in UNCHANGED_FILES.items():
        if file_hash(ROOT / name) != expected:
            raise ValueError('Registered runtime/observer changed: ' + name)
    from jev_libero.environment import load_libero
    load_libero(args.libero_root, args.config_dir)
    from .native_substep_observability import stepping_identity
    import jev_libero.world
    frozen = {'code': identity, 'source_sha256': SOURCE_FILES, 'unchanged_source_sha256': UNCHANGED_FILES,
        'point': point, 'source_frame_shapes': {key: list(value.shape) for key, value in frame.items()},
        'protocol_sha256': file_hash(PROTOCOL), 'versions': versions(),
        'stepping_sources': stepping_identity(), 'jev': repository_identity(package_directory(jev_libero.world)),
        'world_constructed_during_preflight': False, 'new_model_calls': 0,
        'environment': {key: os.environ.get(key) for key in ('CUDA_VISIBLE_DEVICES', 'MUJOCO_GL', 'MUJOCO_EGL_DEVICE_ID')}}
    if frozen['environment'] != {'CUDA_VISIBLE_DEVICES': '4', 'MUJOCO_GL': 'egl', 'MUJOCO_EGL_DEVICE_ID': '4'}:
        raise ValueError('Frozen GPU4/EGL4 allocation required')
    return frozen, point, frame


def collect(args):
    wall_start = time.monotonic()
    frozen, point, original_frame = preflight(args)
    if not args.review or not Path(args.review).is_file():
        raise ValueError('Independent prospective review receipt required')
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    from ..adapters.libero_rgbd import LiberoRgbdSource
    from jev_libero.measurements import Measurements
    frozen.update(review_path=str(Path(args.review).resolve()), review_sha256=file_hash(args.review),
                  seed=1, init_state_id=0, max_actions=40, wall_limit_s=900, argv=sys.argv,
                  source_state_restored=False, archived_controls_used=False)
    recorder = RunRecorder(args.output, {'condition': 'cached_BOX_P_live_proprio_approach_only',
        'seed': 1, 'init_state_id': 0, 'max_actions': 40, 'wall_limit_s': 900},
        {'run_id': Path(args.output).name, **frozen})
    (recorder.output / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (recorder.output / 'review.txt').write_bytes(Path(args.review).read_bytes())
    backend, passive, completed, attempted, step = None, None, 0, 0, -1
    previous_handlers = {}
    def interrupted(sig, _frame):
        raise TimeoutError('wall_or_signal_limit:' + str(sig))
    try:
        for sig in (signal.SIGALRM, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, interrupted)
        remaining = 900 - (time.monotonic() - wall_start)
        if remaining <= 0:
            raise TimeoutError('wall budget exhausted during preflight')
        signal.setitimer(signal.ITIMER_REAL, remaining)
        backend = WineBottleBottomDrawerAdapter().make_backend(args, render=True)
        world, executor = backend.world, AtomicExecutor(backend)
        if float(world.model.opt.timestep) != .002 or int(world.model.opt.integrator) != 0:
            raise ValueError('Native Euler2ms required')
        camera, measurements = LiberoRgbdSource(world), Measurements(world)
        groups = {'robot': measurements.ids({'group': 'robot'}), 'gripper': set(world.gripper_geoms),
                  'bottle': set(world.scene.geoms)}
        groups['pads'] = {g for g in groups['gripper'] if (world.env.sim.model.geom_id2name(g) or '').endswith('_pad_collision')}
        if len(groups['pads']) != 2:
            raise ValueError('Two registered gripper pad geoms required')
        with read_only_measurement(world):
            frame, initial = camera.capture(), contact_snapshot(world, groups)
            proprio = backend.proprioception()
        recorder.capture(frame)
        checks = require_exact_frame(frame, original_frame)
        if proprio['gripper_command'] != 'OPEN' or backend._grip_cmd != -1:
            raise ValueError('Initial open jaw command required')
        passive = PassiveContactRecorder(recorder, groups, initial)
        recorder.record('initial_frame_gate', {'array_bytes_exact': checks, 'source_sha256': SOURCE_FILES,
            'fresh_capture_sim_time_s': frame['capture_sim_time'], 'cached_point': point,
            'new_model_calls': 0, 'groups_evaluator_only': {k: sorted(v) for k, v in groups.items()},
            'initial_contact_snapshot_evaluator_only': initial, 'initial_proprioception': proprio,
            'initial_own_observations': {key: np.asarray(world.obs[key]).tolist() for key in OBS_KEYS},
            'initial_above_threshold_robot_pairs': [list(pair) for pair in sorted(passive.baseline)]})
        source_time, history, reason = float(frame['capture_sim_time']), (), 'action_budget'
        for step in range(40):
            with read_only_measurement(world):
                proprio = backend.proprioception()
            view = decision(point, proprio, source_time, world.data.time, step, history)
            token = view.rule_token()
            recorder.record('decision', {'step': step, 'canonical': asdict(view), 'selected': token,
                'live_tcp_to_fixed_proxy_m': float(np.linalg.norm(np.asarray(proprio['tcp_pos_world_m']) - point['position_world_m']))})
            if token == 'STOP':
                reason = 'rule_no_strict_nominal_improvement'
                break
            attempted += 1
            recorder.record('action_started', {'step': step, 'token': token})
            tracking = {'control': None}
            with observe_controls(world, recorder, step, tracking) as controls:
                with native_observer(world, passive, 'approach', step, tracking, groups) as native:
                    result = executor.execute(token)
            completed += 1
            action_pairs = sorted(set().union(*(above_threshold_robot_pairs(row[stage], groups['robot'])
                                  for row in native for stage in ('before', 'after'))) - passive.baseline)
            recorder.record('action_completed', {'step': step, 'token': token, 'result': result,
                'controls': len(controls), 'native_integrations': len(native),
                'new_contact_observed': passive.first is not None,
                'new_pairs_through_action_evaluator_only': [
                    {'geom_ids': list(pair), 'class': contact_class(pair, groups)} for pair in action_pairs]})
            if len(controls) != 8 or len(native) != 200 or any(sum(r['control'] == c for r in native) != 25 for c in range(8)):
                raise RuntimeError('Unexpected native action/control counts')
            with read_only_measurement(world):
                frame = camera.capture()
                proprio = backend.proprioception()
            recorder.capture(frame)
            recorder.record('endpoint', {'step': step, 'proprioception': proprio,
                'own_observations': {key: np.asarray(world.obs[key]).tolist() for key in OBS_KEYS},
                'live_tcp_to_fixed_proxy_m': float(np.linalg.norm(np.asarray(proprio['tcp_pos_world_m']) - point['position_world_m'])),
                'capture_seq': frame['capture_seq']})
            if passive.first is not None or result['execution_contract_violation']:
                reason = 'new_robot_contact' if passive.first is not None else 'execution_contract_violation'
                break
            history = ({'action': token, 'tcp_delta_m': result['delta_m'],
                'elapsed_sim_s': result['execution_after']['sim_time'] - result['execution_before']['sim_time'],
                'gripper_command': proprio['gripper_command'], 'source': 'proprioception'},)
            print(json.dumps({'step': step, 'token': token, 'completed': completed}), flush=True)
        recorder.record('termination', {'reason': reason, 'attempted_actions': attempted, 'completed_actions': completed,
            'last_step': step, 'first_contact_evaluator_only': passive.first, 'new_model_calls': 0,
            'grasp_attempted': False, 'task_success_claim': False})
    except BaseException as exc:
        recorder.record('failure', {'type': type(exc).__name__, 'error': str(exc), 'step': step,
            'attempted_actions': attempted, 'completed_actions': completed, 'no_retry': True})
        recorder.record('termination', {'reason': 'wall_limit' if isinstance(exc, TimeoutError) else 'runtime_or_admission_failure',
            'attempted_actions': attempted, 'completed_actions': completed, 'first_contact_evaluator_only': None if passive is None else passive.first})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        try:
            if backend is not None:
                backend.close()
        finally:
            recorder.close()


class NativeReplayVerifier:
    """Compare saved native snapshots while replaying only recorded controls."""
    def __init__(self, records):
        self.expected = {(r['kind'], r['data']['step'], r['data']['control'], r['data']['index']): r['data']
                         for r in records if r['kind'] in ('native_before', 'native_after')}
        self.states = []
        self.mismatch = None

    def record(self, kind, row):
        key = (kind, row['step'], row['control'], row['index'])
        expected = self.expected.pop(key, None)
        if row != expected:
            self.mismatch = {'kind': 'native_snapshot', 'source_key': list(key), 'actual_snapshot': row}
            raise ValueError('Exact native replay snapshot mismatch: ' + str(key))
        self.states.append({'stage': kind, **{name: row[name] for name in
            ('step', 'control', 'index', 'time_s', 'qpos', 'qvel', 'integration_fingerprint')},
            'entire_snapshot_exact': True})


def replay(args):
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    from ..adapters.libero_rgbd import LiberoRgbdSource

    source = Path(args.source)
    records, errors = load_records(source / 'episodes.jsonl')
    if errors or any(r['kind'] == 'failure' for r in records):
        raise ValueError('Completed source without partial runtime failure required')
    def rows(kind):
        return [r['data'] for r in records if r['kind'] == kind]
    if len(rows('termination')) != 1 or len(rows('initial_frame_gate')) != 1:
        raise ValueError('One complete source condition required')
    frozen = rows('run_start')[0]['manifest']
    actual, _, _ = preflight(args)
    for name in ('code', 'source_sha256', 'unchanged_source_sha256', 'point', 'protocol_sha256',
                 'versions', 'stepping_sources', 'jev', 'environment'):
        if actual[name] != frozen[name]:
            raise ValueError('Exact replay provenance mismatch: ' + name)
    if file_hash(source / 'review.txt') != frozen['review_sha256']:
        raise ValueError('Archived review receipt changed')
    starts, afters, actions, captures = rows('control_started'), rows('control_completed'), rows('action_completed'), rows('vision_capture')
    if not (len(starts) == len(afters) == 8 * len(actions) <= 320 and len(captures) == len(actions) + 1):
        raise ValueError('Complete fixed-budget controls/captures required')
    for capture in captures:
        if file_hash(source / capture['artifact']) != capture['artifact_sha256']:
            raise ValueError('Source capture artifact changed')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    backend, controls, frames, mismatch = None, [], [], None
    verifier = NativeReplayVerifier(records)
    try:
        backend = WineBottleBottomDrawerAdapter().make_backend(args, render=True)
        world, camera = backend.world, LiberoRgbdSource(backend.world)
        groups = {key: set(value) for key, value in rows('initial_frame_gate')[0]['groups_evaluator_only'].items()}
        def capture(index):
            nonlocal mismatch
            with read_only_measurement(world):
                frame = camera.capture()
            try:
                with np.load(source / captures[index]['artifact'], allow_pickle=False) as archive:
                    checks = require_exact_frame(frame, archive)
                if frame['capture_sim_time'] != captures[index]['capture_sim_time']:
                    raise ValueError('Exact replay capture time mismatch')
            except ValueError:
                name = f'mismatched-capture-{index:04d}.npz'
                np.savez_compressed(output / name, **{key: frame[key] for key in FRAME_KEYS})
                mismatch = {'kind': 'capture', 'source_artifact': captures[index]['artifact'],
                    'actual_artifact': name, 'actual_artifact_sha256': file_hash(output / name),
                    'actual_capture_sim_time': frame['capture_sim_time'],
                    'expected_capture_sim_time': captures[index]['capture_sim_time']}
                raise
            frames.append({'capture_seq': frame['capture_seq'], 'array_bytes_exact': checks})
        capture(0)
        for action_index, action in enumerate(actions):
            step, tracking = action['step'], {'control': None}
            with native_observer(world, verifier, 'approach', step, tracking, groups):
                for control in range(8):
                    before, after = starts[8 * action_index + control], afters[8 * action_index + control]
                    if before['step'] != step or before['control'] != control or after['step'] != step or after['control'] != control:
                        raise ValueError('Source control order mismatch')
                    state = world.env.sim.get_state().flatten().tolist()
                    if state != before['state_before']:
                        mismatch = {'kind': 'control_before', 'step': step, 'control': control, 'actual_state': state}
                        raise ValueError('Exact control-before state mismatch')
                    previous_obs = {key: np.asarray(world.obs[key]).tolist() for key in OBS_KEYS}
                    if previous_obs != before['previous_returned_own_observations']:
                        mismatch = {'kind': 'control_before_observation', 'step': step, 'control': control,
                                    'actual_own_observations': previous_obs}
                        raise ValueError('Exact previous own-observation mismatch')
                    tracking['control'] = control
                    world.obs, _, _, _ = world.env.step(before['command'])
                    tracking['control'] = None
                    state_after = world.env.sim.get_state().flatten().tolist()
                    if state_after != after['state_after']:
                        mismatch = {'kind': 'control_after', 'step': step, 'control': control, 'actual_state': state_after}
                        raise ValueError('Exact control-after state mismatch')
                    returned_obs = {key: np.asarray(world.obs[key]).tolist() for key in OBS_KEYS}
                    if returned_obs != after['returned_own_observations']:
                        mismatch = {'kind': 'control_after_observation', 'step': step, 'control': control,
                                    'actual_own_observations': returned_obs}
                        raise ValueError('Exact returned own-observation mismatch')
                    controls.append({'step': step, 'control': control, 'state_before': state,
                                     'state_after': state_after, 'exact': True})
            capture(action_index + 1)
        if verifier.expected:
            raise ValueError('Unmatched native source snapshots')
        result = {'status': 'passed', 'source_journal_sha256': file_hash(source / 'episodes.jsonl'),
            'code': actual['code'], 'exact_controls': len(controls), 'exact_native_snapshots': len(verifier.states),
            'exact_captures': len(frames), 'control_states': controls, 'frame_checks': frames,
            'native_states': verifier.states, 'policy_or_model_rerun': False,
            'scope': 'recorded control/state/image reproduction; observer remains installed, not an observer-removal intervention'}
        with (output / 'result.json').open('x') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write('\n')
        print(json.dumps({key: result[key] for key in ('status', 'exact_controls', 'exact_native_snapshots', 'exact_captures')}))
    except BaseException as exc:
        with (output / 'failure.json').open('x') as stream:
            json.dump({'error': str(exc), 'exact_controls_before_failure': len(controls),
                       'exact_native_snapshots_before_failure': len(verifier.states), 'no_retry': True,
                       'first_mismatch_evidence': verifier.mismatch or mismatch}, stream, indent=2, allow_nan=False)
        raise
    finally:
        if backend is not None:
            backend.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--review')
    parser.add_argument('--mode', choices=('collect', 'replay'), default='collect')
    parser.add_argument('--source')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.preflight:
        frozen, _, _ = preflight(args)
        with Path(args.output).open('x') as stream:
            json.dump(frozen, stream, indent=2, allow_nan=False)
            stream.write('\n')
        print(json.dumps({'preflight': 'passed', 'output': args.output}))
    else:
        (collect if args.mode == 'collect' else replay)(args)
