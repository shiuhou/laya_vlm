"""Seven physical counterfactual primitives after an explicit exact Task2 prefix."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import time

import numpy as np

from ..runtime_core import AtomicExecutor, MOVE
from . import task2_box_point_boundary as source
from .local_grasp_interface import contact_snapshot, native_observer, read_only_measurement
from .native_substep_observability import array_hash
from .records import RunRecorder, file_hash, load_records

RAW = source.RAW
SOURCE = RAW/'task2-box-point-boundary-run-01'
SOURCE_SHA = 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771'
PROTOCOL = source.ROOT/'docs/research/task2_pre22_counterfactual_protocol.md'
ARMS = (*MOVE, 'STOP')
BOUNDARY, PREFIX_CONTROLS = 22, 176
WALL_SECONDS = 3600
SURFACE_FILES = {
    'task2-observed-surface-sweep-run-01/feature-seal.json': '2272dd32051a5965b1188360c993bf89e0b1a77d9f569b053351b5e65c8e9601',
    'task2-observed-surface-sweep-run-01/features/features.json': '4468151c3cf9e9abecb199131189fab02752ebdd7bf179234d30725c7bc9a55b',
}
MODEL_ARRAYS = ('body_parentid', 'body_pos', 'body_quat', 'body_mass', 'body_inertia',
    'jnt_type', 'jnt_bodyid', 'jnt_pos', 'jnt_axis', 'jnt_qposadr', 'jnt_dofadr', 'jnt_range',
    'geom_type', 'geom_bodyid', 'geom_pos', 'geom_quat', 'geom_size', 'geom_dataid',
    'geom_contype', 'geom_conaffinity', 'geom_friction', 'geom_solref', 'geom_solimp',
    'mesh_vert', 'mesh_face', 'mesh_vertadr', 'mesh_vertnum', 'mesh_faceadr', 'mesh_facenum',
    'site_bodyid', 'site_pos', 'site_quat', 'actuator_trnid', 'actuator_gainprm',
    'actuator_biasprm', 'dof_damping', 'dof_armature', 'qpos0', 'cam_pos', 'cam_quat', 'cam_fovy')


def data(rows, kind):
    return [r['data'] for r in rows if r['kind'] == kind]


def own(world):
    return {key: np.asarray(world.obs[key]).tolist() for key in source.OBS_KEYS}


def exact(actual, expected, recorder, description):
    if actual != expected:
        recorder.record('first_mismatch', {'description': description, 'actual': actual, 'expected': expected})
        raise ValueError('Exact source mismatch: '+description)


def load_source():
    if file_hash(SOURCE/'episodes.jsonl') != SOURCE_SHA:
        raise ValueError('Sealed approach source differs')
    rows, errors = load_records(SOURCE/'episodes.jsonl')
    if errors or data(rows, 'failure') or len(data(rows, 'termination')) != 1:
        raise ValueError('Complete chained approach source required')
    starts, ends = data(rows, 'control_started'), data(rows, 'control_completed')
    if len(starts) != 200 or len(ends) != 200 or len(data(rows, 'vision_capture')) != 26:
        raise ValueError('Original source counts differ')
    if data(rows, 'decision')[BOUNDARY]['selected'] != 'MV_FWD':
        raise ValueError('FWD qualification source changed')
    for i, (before, after) in enumerate(zip(starts, ends)):
        if before['step'] != i//8 or before['control'] != i%8 or after['step'] != i//8 or after['control'] != i%8:
            raise ValueError('Source control order differs')
    for capture in data(rows, 'vision_capture'):
        if file_hash(SOURCE/capture['artifact']) != capture['artifact_sha256']:
            raise ValueError('Source capture changed')
    frozen = data(rows, 'run_start')[0]['manifest']
    for name in ('embodied_runtime/experiments/task2_box_point_boundary.py',
                 'embodied_runtime/experiments/privileged_multistage_task.py',
                 'embodied_runtime/experiments/native_substep_observability.py'):
        if file_hash(source.ROOT/name) != frozen['code']['source_sha256'][name]:
            raise ValueError('Existing source replay/task/observer helper changed')
    return rows


def preflight(args):
    rows = load_source()
    for name, expected in SURFACE_FILES.items():
        if file_hash(RAW/name) != expected:
            raise ValueError('Already sealed surface comparison changed')
    current, _, _ = source.preflight(args)
    original = data(rows, 'run_start')[0]['manifest']
    for key in ('source_sha256', 'unchanged_source_sha256', 'point', 'protocol_sha256',
                'versions', 'stepping_sources', 'jev', 'environment'):
        if current[key] != original[key]:
            raise ValueError('Original scientific identity changed: '+key)
    current.update(protocol_sha256=file_hash(PROTOCOL), approach_source_sha256=SOURCE_SHA,
                   original_approach_commit=original['code']['commit'], prefix_actions=22, prefix_controls=176,
                   branch_order=list(ARMS), wall_limit_s=WALL_SECONDS, fresh_reset_each_branch=True,
                   frozen_surface_comparison_sha256=SURFACE_FILES,
                   archived_prefix_replayed=True, archived_state_restored=False,
                   executed_STOP_is_hold_diagnostic=True, original_loop_STOP_is_termination=True)
    return current, rows


class BranchRecorder:
    """Persist actual samples first, then use original exact native verifier."""
    def __init__(self, recorder, branch, rows):
        self.recorder, self.branch = recorder, branch
        selected = [r for r in rows if r['data'].get('step', 999) < BOUNDARY
                    or (branch == 'MV_FWD' and r['data'].get('step') == BOUNDARY)]
        self.verifier = source.NativeReplayVerifier(selected)
        self.controls = {(r['kind'], r['data']['step'], r['data']['control']): r['data']
                         for r in selected if r['kind'] in ('control_started', 'control_completed')}

    def record(self, kind, row):
        record_id = self.recorder.record(kind, {'branch': self.branch, **row})
        checked = row.get('step', 999) < BOUNDARY or (self.branch == 'MV_FWD' and row.get('step') == BOUNDARY)
        if checked and kind in ('native_before', 'native_after'):
            try:
                self.verifier.record(kind, row)
            except ValueError:
                self.recorder.record('first_mismatch', {'branch': self.branch, **self.verifier.mismatch})
                raise
        elif checked and kind in ('control_started', 'control_completed'):
            key = (kind, row['step'], row['control'])
            exact(row, self.controls.pop(key, None), self, 'control packet '+str(key))
        return record_id


def require_prefix_complete(observer):
    if (len(observer.verifier.states) != PREFIX_CONTROLS*25*2
            or any(key[1] < BOUNDARY for key in observer.verifier.expected)
            or any(key[1] < BOUNDARY for key in observer.controls)):
        raise ValueError('Prefix source comparisons incomplete; no probe admitted')


def current_model_identity(world):
    xml = world.env.env.model.get_xml()
    model = world.model
    return {'xml_sha256': hashlib.sha256(xml.encode()).hexdigest(),
            'model_array_sha256': {key: array_hash(getattr(model, key)) for key in MODEL_ARRAYS},
            'dimensions': {key: int(getattr(model, key)) for key in ('nq', 'nv', 'nu', 'nbody', 'ngeom', 'nmesh', 'nsite')},
            'native_options': {'timestep': float(model.opt.timestep), 'integrator': int(model.opt.integrator),
                               'solver': int(model.opt.solver), 'iterations': int(model.opt.iterations),
                               'tolerance': float(model.opt.tolerance), 'gravity': model.opt.gravity.tolist()},
            'historical_model_byte_identity_claimed': False}, xml


def capture(world, camera, recorder, branch, expected=None):
    with read_only_measurement(world):
        frame = camera.capture()
    directory = recorder.output/branch
    directory.mkdir(exist_ok=True)
    path = directory/f'capture-{frame["capture_seq"]:04d}.npz'
    with path.open('xb') as stream:
        np.savez_compressed(stream, **{key: frame[key] for key in source.FRAME_KEYS})
    checks = None
    if expected is not None:
        try:
            with np.load(SOURCE/expected['artifact'], allow_pickle=False) as archive:
                checks = source.require_exact_frame(frame, archive)
            exact(frame['capture_sim_time'], expected['capture_sim_time'], recorder, 'capture time')
        except ValueError:
            recorder.record('first_mismatch', {'branch': branch, 'kind': 'capture',
                'actual_artifact': str(path.relative_to(recorder.output)), 'expected_source': expected})
            raise
    recorder.record('capture', {'branch': branch, 'capture_seq': frame['capture_seq'],
        'capture_sim_time': frame['capture_sim_time'], 'artifact': str(path.relative_to(recorder.output)),
        'sha256': file_hash(path), 'array_bytes_exact': checks})


def replay_prefix(world, recorder, rows, groups, camera, batch_recorder, branch):
    starts = data(rows, 'control_started')
    for step in range(BOUNDARY):
        tracking = {'control': None}
        with native_observer(world, recorder, 'approach', step, tracking, groups):
            for control in range(8):
                command = starts[step*8+control]['command']
                recorder.record('control_started', {'step': step, 'control': control, 'command': command,
                    'state_before': world.env.sim.get_state().flatten().tolist(),
                    'previous_returned_own_observations': own(world)})
                tracking['control'] = control
                world.obs, _, _, _ = world.env.step(command)
                tracking['control'] = None
                recorder.record('control_completed', {'step': step, 'control': control, 'command': command,
                    'state_after': world.env.sim.get_state().flatten().tolist(), 'returned_own_observations': own(world)})
        capture(world, camera, batch_recorder, branch, data(rows, 'vision_capture')[step+1])


def contact_summary(native, groups):
    result = {}
    for stage in ('before', 'after'):
        rows = [{'control': r['control'], 'index': i, 'time_s': r[stage]['time_s'],
                 **contact, 'class': source.contact_class(contact['geom_ids'], groups)}
                for i, r in enumerate(native) for contact in r[stage]['contacts']
                if groups['robot'].intersection(contact['geom_ids'])]
        strong = [row for row in rows if row['normal_force_N'] > .05]
        result[stage] = {'raw_robot_rows': len(rows), 'strict_above_005N_rows': len(strong),
            'first_raw': rows[0] if rows else None, 'first_strong': strong[0] if strong else None,
            'max_normal_force_N': max((r['normal_force_N'] for r in rows), default=0.),
            'all_raw_robot_pairs': sorted({tuple(sorted(r['geom_names'])) for r in rows}),
            'all_strong_robot_pairs': sorted({tuple(sorted(r['geom_names'])) for r in strong})}
    return result


def run(args):
    start = time.monotonic()
    frozen, rows = preflight(args)
    review = Path(args.review)
    if frozen['code']['commit'] not in review.read_text() or 'PASS' not in review.read_text():
        raise ValueError('Prospective PASS for exact freeze required')
    gpu = subprocess.check_output(['nvidia-smi', '--id=4', '--query-gpu=uuid,utilization.gpu,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    _, utilization, memory = [v.strip() for v in gpu.split(',')]
    if int(utilization) != 0 or int(memory) > 100:
        raise RuntimeError('GPU4 is occupied; no dynamics started')
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    from ..adapters.libero_rgbd import LiberoRgbdSource
    from jev_libero.measurements import Measurements
    recorder = RunRecorder(args.output, {'mode': 'declared_pre22_counterfactual', 'branches': list(ARMS),
        'seed': 1, 'init_state_id': 0, 'prefix_actions_per_branch': 22, 'retries': 0},
        {'run_id': Path(args.output).name, **frozen, 'review_sha256': file_hash(review), 'GPU4_before_batch': gpu})
    (recorder.output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    (recorder.output/'review.md').write_bytes(review.read_bytes())
    completed, backend, current, reference_model = [], None, None, None
    previous_handlers = {}
    def interrupted(sig, _frame):
        raise TimeoutError('wall_or_signal_limit:'+str(sig))
    try:
        for sig in (signal.SIGALRM, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, max(.001, WALL_SECONDS-(time.monotonic()-start)))
        initial = data(rows, 'initial_frame_gate')[0]
        source_action = data(rows, 'action_completed')[BOUNDARY]['result']
        for current in ARMS:
            recorder.record('branch_started', {'branch': current, 'fresh_reset': True, 'standard_settling_controls': 10,
                'archived_state_restored': False, 'prefix_controls': PREFIX_CONTROLS,
                'STOP_semantics': 'executed hold diagnostic; original loop STOP terminates without execution'})
            backend = WineBottleBottomDrawerAdapter().make_backend(args, render=True)
            world, executor = backend.world, AtomicExecutor(backend)
            camera, measurements = LiberoRgbdSource(world), Measurements(world)
            groups = {'robot': measurements.ids({'group': 'robot'}), 'gripper': set(world.gripper_geoms), 'bottle': set(world.scene.geoms)}
            groups['pads'] = {g for g in groups['gripper'] if (world.env.sim.model.geom_id2name(g) or '').endswith('_pad_collision')}
            exact({k: sorted(v) for k, v in groups.items()}, initial['groups_evaluator_only'], recorder, 'initial groups')
            exact(world.env.sim.get_state().flatten().tolist(), data(rows, 'control_started')[0]['state_before'], recorder, 'initial state')
            exact(own(world), initial['initial_own_observations'], recorder, 'initial own observations')
            capture(world, camera, recorder, current, data(rows, 'vision_capture')[0])
            with read_only_measurement(world):
                exact(contact_snapshot(world, groups), initial['initial_contact_snapshot_evaluator_only'], recorder, 'initial native snapshot')
                identity, xml = current_model_identity(world)
            if identity['native_options']['timestep'] != .002 or identity['native_options']['integrator'] != 0:
                raise ValueError('Registered native Euler2ms model required')
            if reference_model is None:
                reference_model = identity
                (recorder.output/'current-model.xml').write_text(xml)
            else:
                exact(identity, reference_model, recorder, 'current reset model identity across branches')
            recorder.record('initial_gates', {'branch': current, 'source_state_own_groups_native_exact': True,
                'current_model_identity': identity, 'backend_gripper_command': backend._grip_cmd,
                'initial_state': world.env.sim.get_state().flatten().tolist(), 'own_observations': own(world)})
            exact(backend._grip_cmd, -1., recorder, 'retained open command')
            observer = BranchRecorder(recorder, current, rows)
            replay_prefix(world, observer, rows, groups, camera, recorder, current)
            require_prefix_complete(observer)
            with read_only_measurement(world):
                before = backend.execution_state()
                proprio = backend.proprioception()
            exact(before, source_action['execution_before'], observer, 'pre22 execution state')
            exact(own(world), data(rows, 'control_started')[PREFIX_CONTROLS]['previous_returned_own_observations'], observer, 'pre22 own packet')
            recorder.record('prefix_qualified', {'branch': current, 'controls': 176, 'native_stage_samples': 8800,
                'captures': 23, 'execution_before': before, 'proprioception': proprio,
                'no_selector_or_model_called': True, 'raw_prefix_controls_not_recomputed': True})
            tracking = {'control': None}
            recorder.record('probe_started', {'branch': current, 'token': current, 'source_step': 22,
                'nominal_delta_m': (np.asarray(MOVE.get(current, (0., 0., 0.)))*.01).tolist(),
                'hold_or_translation_target_world_m': (np.asarray(before['tcp_xyz'])+np.asarray(MOVE.get(current, (0., 0., 0.)))*.01).tolist()})
            with source.observe_controls(world, observer, BOUNDARY, tracking) as controls:
                with native_observer(world, observer, 'approach', BOUNDARY, tracking, groups) as native:
                    result = executor.execute(current)
            recorder.record('probe_result', {'branch': current, 'result': result, 'contact_summary': contact_summary(native, groups),
                'controls': len(controls), 'native_integrations': len(native), 'endpoint_own_observations': own(world)})
            if (len(controls) != 8 or len(native) != 200 or result['environment_step_count'] != 8
                    or result['low_level_commands'] != [r['command'] for r in controls]
                    or any(sum(r['control'] == c for r in native) != 25 for c in range(8))):
                raise ValueError('Unexpected native counts; partial evidence retained')
            capture(world, camera, recorder, current, data(rows, 'vision_capture')[23] if current == 'MV_FWD' else None)
            if current == 'MV_FWD':
                exact(result, source_action, observer, 'FWD full original executor result')
            if observer.verifier.expected or observer.controls:
                raise ValueError('Missing exact source comparison rows')
            recorder.record('branch_completed', {'branch': current, 'completed_primitive': True,
                'source_FWD_qualification_exact': True if current == 'MV_FWD' else None,
                'execution_contract_violation': result['execution_contract_violation'],
                'no_subsequent_action': True})
            completed.append(current)
            backend.close()
            backend = None
        recorder.record('termination', {'reason': 'seven_branches_complete', 'completed': completed,
            'prefix_controls_total': 1232, 'probe_controls_total': 56, 'native_integrations_total': 32200,
            'original_loop_STOP_semantics': 'no further primitive; represented analytically, no eighth world',
            'policy_or_safety_filter_changed': False, 'new_model_calls': 0})
    except BaseException as exc:
        recorder.record('failure', {'error': str(exc), 'branch': current, 'completed': completed, 'no_retry': True})
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--review')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.preflight:
        frozen, _ = preflight(args)
        with Path(args.output).open('x') as stream:
            json.dump(frozen, stream, indent=2, allow_nan=False)
            stream.write('\n')
        print(json.dumps({'preflight': 'passed', 'no_world_constructed': True}))
    else:
        run(args)
