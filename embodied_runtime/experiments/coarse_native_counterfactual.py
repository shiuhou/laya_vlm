"""Seven evaluator-only native options after exact archived 200-control replay."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path

import numpy as np

from ..runtime_core import AtomicExecutor, MOVE
from ..decision_interface import shared_atomic_candidates
from . import coarse_point_probe as base
from .records import (RunRecorder, code_identity, file_hash, load_records, versions,
                      repository_identity, package_directory)

SOURCE = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-initial-point-02')
SOURCE_SHA256 = 'e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf'
PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/coarse_native_counterfactual_protocol.md'
ARMS = ('MV_FWD', 'MV_BACK', 'MV_LEFT', 'MV_RIGHT', 'MV_UP', 'MV_DOWN', 'STOP')
PREFIX_CONTROLS = 200
SOURCE_BOUNDARY = 25
VERSION = 'coarse-native-counterfactual-v1'


def data(rows, kind):
    return [r['data'] for r in rows if r['kind'] == kind]


def one(rows, kind):
    values = data(rows, kind)
    if len(values) != 1:
        raise ValueError(f'exactly one {kind} required')
    return values[0]


def load_source():
    if file_hash(SOURCE/'episodes.jsonl') != SOURCE_SHA256:
        raise ValueError('frozen diagnostic source changed')
    rows, errors = load_records(SOURCE/'episodes.jsonl')
    if errors or data(rows, 'failure'):
        raise ValueError('complete successful source evidence required')
    controls, starts = data(rows, 'control_observation'), data(rows, 'control_started')
    boundaries, actions = data(rows, 'decision_boundary'), data(rows, 'action')
    if len(controls) != 208 or len(starts) != 208 or len(boundaries) != 26 or len(actions) != 26:
        raise ValueError('source counts differ')
    environment = one(rows, 'environment')
    expected = environment['sim_state']
    for i, (intent, control) in enumerate(zip(starts, controls)):
        if (control['step'] != i//8 or control['control'] != i%8 or control['state_before'] != expected
                or any(control[key] != value for key, value in intent.items())):
            raise ValueError('source control chain changed')
        expected = control['state_after']
    boundary = boundaries[SOURCE_BOUNDARY]
    candidates = json.loads(json.dumps([asdict(c) for c in shared_atomic_candidates() if c.token in ARMS]))
    frozen = one(rows, 'initial_target_frozen')
    if (boundary['step'] != SOURCE_BOUNDARY or boundary['canonical']['candidates'] != candidates
            or [c['token'] for c in candidates] != list(ARMS) or boundary['selected'] != 'MV_RIGHT'
            or boundary['admitted'] != frozen['admitted'] or environment['initial_contacts']
            or environment['new_contact_force_threshold_N'] != 1.
            or environment['task_config']['contact']['min_normal_force_N'] != 1.):
        raise ValueError('same-point/candidates/threshold source conditions differ')
    source_code = one(rows, 'run_start')['manifest']['code']['source_sha256']
    root = Path(__file__).resolve().parents[2]
    names = ('embodied_runtime/runtime_core.py', 'embodied_runtime/decision_interface.py',
             'embodied_runtime/adapters/libero.py', 'embodied_runtime/adapters/libero_rgbd.py',
             'embodied_runtime/experiments/coarse_point_probe.py',
             'embodied_runtime/experiments/engineering_demo.py')
    if any(file_hash(root/name) != source_code[name] for name in names):
        raise ValueError('native executor/controller-facing/source helper code changed')
    return rows


def frozen_inputs(rows):
    from .collect_pairs import initial_state_inventory
    import jev_libero.world
    code = code_identity()
    if code['dirty_status']:
        raise ValueError('clean committed source required before preflight/execution')
    start = one(rows, 'run_start')
    if versions() != start['manifest']['versions']:
        raise ValueError('source software environment changed')
    config = start['resolved_config']
    inventory = initial_state_inventory('top_drawer', config['libero_root'], config['config_dir'])
    import libero  # configured loader above establishes the explicit LIBERO repository path
    identity = {'task': 'top_drawer', 'init_state_id': 0, 'seed': 1,
        'binding': inventory['binding'], 'benchmark_state_id': inventory['state_ids'][0]}
    if identity != one(rows, 'initial_identity'):
        raise ValueError('benchmark reset identity changed')
    repositories = {'jev': repository_identity(package_directory(jev_libero.world)),
                    'libero': repository_identity(package_directory(libero))}
    original_repos = next(x['environment_repositories'] for x in data(rows, 'manifest_update')
                          if 'environment_repositories' in x)
    if repositories != original_repos:
        raise ValueError('simulator/controller repositories changed')
    environment = {k: os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID')}
    if environment != {'CUDA_VISIBLE_DEVICES':'6','MUJOCO_GL':'egl','MUJOCO_EGL_DEVICE_ID':'6'}:
        raise ValueError('registered GPU6 EGL assignment required')
    return {'version': VERSION, 'source': str(SOURCE), 'source_sha256': SOURCE_SHA256,
        'source_boundary': SOURCE_BOUNDARY, 'prefix_controls_per_arm': PREFIX_CONTROLS,
        'arms': list(ARMS), 'protocol_sha256': file_hash(PROTOCOL), 'code': code,
        'versions': versions(), 'initial_identity': identity, 'environment_repositories': repositories,
        'execution_environment': environment, 'point_source': one(rows, 'initial_target_frozen'),
        'source_boundary_record': data(rows, 'decision_boundary')[SOURCE_BOUNDARY],
        'source_preboundary_state': data(rows, 'control_observation')[PREFIX_CONTROLS]['state_before'],
        'source_task_config': one(rows, 'environment')['task_config'], 'contact_threshold_N': 1.,
        'native_source_sha256': {name: file_hash(Path(__file__).resolve().parents[2]/name)
            for name in ('embodied_runtime/runtime_core.py','embodied_runtime/adapters/libero.py',
                         'embodied_runtime/experiments/coarse_point_probe.py')},
        'oracle_evaluation_only': True, 'fresh_autonomous_policy': False, 'model_calls': 0}


def exact_state(world, expected, context):
    current = world.env.sim.get_state().flatten().tolist()
    if current != expected:
        raise ValueError(f'exact simulator state mismatch: {context}')
    return current


def replay_prefix(world, prefix, recorder, arm):
    for i, original in enumerate(prefix):
        before = exact_state(world, original['state_before'], f'{arm} prefix {i} before')
        recorder.record('prefix_control_started', {'arm':arm, 'ordinal':i, 'source_step':original['step'],
            'source_control':original['control'], 'command':original['command'], 'state_before':before})
        world.obs, _, _, _ = world.env.step(original['command'])
        after = exact_state(world, original['state_after'], f'{arm} prefix {i} after')
        recorder.record('prefix_control_completed', {'arm':arm, 'ordinal':i, 'command':original['command'],
            'state_before':before, 'state_after':after, 'exact_source_match':True})


@contextmanager
def observe_arm(world, measurements, gap, recorder, arm):
    original, controls = world.env.step, []
    def observed(command):
        before = world.env.sim.get_state().flatten().tolist()
        recorder.record('arm_control_started', {'arm':arm, 'control':len(controls),
            'command':np.asarray(command).tolist(), 'state_before':before})
        returned = original(command)
        # Read returned observations without assigning world.obs before native World.execute does.
        row = {'arm':arm, 'control':len(controls), 'command':np.asarray(command).tolist(),
            'state_before':before, 'state_after':world.env.sim.get_state().flatten().tolist(),
            'sim_time_s':float(world.data.time), 'contacts':base.contact_rows(measurements),
            'gripper_to_designated_handle_surface_mm':gap.minimum_mm(world.data),
            'drawer_joint_qpos_m':float(world.data.qpos[world.qindex]),
            'returned_robot_tcp_m':np.asarray(returned[0]['robot0_eef_pos']).tolist(),
            'returned_gripper_qpos':np.asarray(returned[0]['robot0_gripper_qpos']).tolist(),
            'robot_observation_exact_sample_time_s':None}
        controls.append(row)
        recorder.record('arm_control_completed', row)
        return returned
    world.env.step = observed
    try:
        yield controls
    finally:
        world.env.step = original


def classify(controls, handle_names, before_gap, after_gap, threshold=1.):
    contacts = [c for row in controls for c in row['contacts']]
    nonhandle = [c for c in contacts if not any(name in handle_names for name in c['geom_names'])]
    gain = float(before_gap-after_gap)
    return {'observed_robot_contact_rows':len(contacts), 'observed_nonhandle_contact_rows':len(nonhandle),
        'robot_contact_above_1N':any(c['normal_force_N'] > threshold for c in contacts),
        'nonhandle_contact_above_1N':any(c['normal_force_N'] > threshold for c in nonhandle),
        'max_robot_normal_force_N':max((c['normal_force_N'] for c in contacts), default=0.),
        'max_nonhandle_normal_force_N':max((c['normal_force_N'] for c in nonhandle), default=0.),
        'measured_handle_surface_gap_gain_mm':gain,
        'positive_measured_handle_approach':gain > 0.,
        'no_observed_robot_contact_and_positive_approach':not contacts and gain > 0.,
        'no_observed_nonhandle_contact_and_positive_approach':not nonhandle and gain > 0.,
        'no_robot_contact_above_1N_and_positive_approach':not any(c['normal_force_N'] > threshold for c in contacts) and gain > 0.}


def capture(backend, recorder, arm, phase):
    from ..adapters.libero_rgbd import LiberoRgbdSource
    before = backend.world.env.sim.get_state().flatten().tolist()
    frame = LiberoRgbdSource(backend.world).capture()
    exact_state(backend.world, before, f'{arm} {phase} capture')
    relative = Path('frames')/f'{arm}-{phase}.npz'
    (recorder.output/'frames').mkdir(exist_ok=True)
    with (recorder.output/relative).open('xb') as stream:
        np.savez_compressed(stream, **{k:frame[k] for k in ('rgb','depth_m','intrinsics','camera_to_world')})
    recorder.record('capture', {'arm':arm,'phase':phase,'artifact':str(relative),
        'sha256':file_hash(recorder.output/relative),'sim_time_s':frame['capture_sim_time'],
        'state_unchanged':True})


def run(args):
    recorder = RunRecorder(args.output, {'mode':args.mode, 'source':str(SOURCE),
        'source_sha256':SOURCE_SHA256, 'preflight':args.preflight, 'oracle_evaluator_only':True,
        'no_policy_selection':True, 'planned_arms':ARMS, 'model_calls':0, 'retries':0},
        {'run_id':Path(args.output).name, 'code':code_identity(), 'versions':versions()})
    completed, current = [], None
    try:
        rows = load_source()
        frozen = frozen_inputs(rows)
        recorder.record('frozen_inputs', frozen)
        (recorder.output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        if args.mode == 'preflight':
            recorder.record('termination', {'reason':'preflight_complete','planned_arms':list(ARMS),'executed_arms':[]})
            return
        prior, errors = load_records(Path(args.preflight)/'episodes.jsonl')
        if (errors or one(prior, 'frozen_inputs') != frozen or one(prior, 'termination') !=
                {'reason':'preflight_complete','planned_arms':list(ARMS),'executed_arms':[]}):
            raise ValueError('frozen preflight changed')
        from .engineering_demo import RecordingBackend, save_trajectory
        from jev_libero.measurements import Measurements
        from jev_libero.geometry import GeometryGap
        config = one(rows, 'run_start')['resolved_config']
        initial = one(rows, 'environment')
        source_controls = data(rows, 'control_observation')
        source_action = data(rows, 'action')[SOURCE_BOUNDARY]
        boundary = frozen['source_boundary_record']
        point = np.asarray(boundary['admitted']['position_world_m'])
        handle_names = initial['task_config']['measurements']['gripper_handle_contacts']['right']['geoms']
        for index, current in enumerate(ARMS):
            recorder.record('arm_started', {'arm':current,'arm_index':index,'fresh_reset':True,
                'diagnostic_archived_control_replay':True,'prefix_controls':PREFIX_CONTROLS})
            backend = RecordingBackend.from_task('top_drawer',seed=1,init_state_id=0,render=True,
                libero_root=config['libero_root'],config_dir=config['config_dir'])
            try:
                world = backend.world
                if world.config != initial['task_config'] or backend.execution_state() != initial['initial_state']:
                    raise ValueError('fresh reset task/robot state mismatch')
                exact_state(world, initial['sim_state'], f'{current} fresh reset')
                recorder.record('arm_initial_state', {'arm':current,'state':initial['sim_state'],
                    'execution_state':backend.execution_state(),'exact_source_match':True})
                replay_prefix(world, source_controls[:PREFIX_CONTROLS], recorder, current)
                before_state = exact_state(world, frozen['source_preboundary_state'], f'{current} preboundary')
                if backend.execution_state() != source_action['result']['execution_before']:
                    raise ValueError('preboundary controller-facing execution state differs')
                proprio = backend.proprioception()
                fields = boundary['canonical']['state']['fields']
                if (proprio['tcp_pos_world_m'] != fields['robot.tcp_position_m']['value']
                        or proprio['gripper_width_m'] != fields['robot.gripper_width_m']['value']
                        or proprio['gripper_command'] != fields['robot.gripper_command']['value']):
                    raise ValueError('robot observation timing/value differs')
                measurements = Measurements(world)
                handle_ids = measurements.ids(world.config['measurements']['handle_center_mm']['entity'])
                gap = GeometryGap(world.model, world.gripper_geoms, handle_ids)
                before = base.oracle_evaluation(backend, gap, measurements)
                if before != source_action['oracle_before']:
                    raise ValueError('preboundary evaluator state differs')
                capture(backend, recorder, current, 'before')
                direction = np.asarray(MOVE.get(current, (0.,0.,0.)))
                tcp = np.asarray(proprio['tcp_pos_world_m'])
                nominal_gain = float((np.linalg.norm(point-tcp)-np.linalg.norm(point-(tcp+.01*direction)))*1000)
                original_effect = boundary['canonical']['effects']['effects'][current]
                if current in MOVE and abs(nominal_gain+1000*original_effect['values']['distance_change_m']) > 1e-12:
                    raise ValueError('nominal same-point effect reconstruction differs')
                recorder.record('preboundary', {'arm':current,'state':before_state,'proprioception':proprio,
                    'oracle_before':before,'drawer_joint_qpos_m':float(world.data.qpos[world.qindex]),
                    'drawer_joint_qpos_index':world.qindex,
                    'fixed_point_world_m':point.tolist(),'original_candidate':boundary['canonical']['candidates'][index],
                    'original_effect':original_effect,'nominal_fixed_point_gain_mm':nominal_gain,
                    'no_selector_called':True})
                recorder.record('execution_started', {'arm':current,'token':current,'native_executor':'AtomicExecutor'})
                with observe_arm(world, measurements, gap, recorder, current) as controls:
                    result = AtomicExecutor(backend).execute(current)
                after_state = world.env.sim.get_state().flatten().tolist()
                if len(controls) != 8 or result['environment_step_count'] != 8 or result['low_level_commands'] != [r['command'] for r in controls]:
                    raise ValueError('native primitive control lineage differs')
                if any(r['command'][6] != -1. for r in controls):
                    raise ValueError('retained native gripper command changed')
                save_trajectory(backend, recorder.output, index, recorder)
                after = base.oracle_evaluation(backend, gap, measurements)
                capture(backend, recorder, current, 'after')
                source_match = None
                if current == 'MV_RIGHT':
                    source_match = (result == source_action['result'] and after == source_action['oracle_after']
                        and all(all(row[k] == old[k] for k in ('command','state_before','state_after','contacts'))
                            for row,old in zip(controls,source_controls[PREFIX_CONTROLS:])) )
                    if not source_match:
                        raise ValueError('original MV_RIGHT continuation did not reproduce exactly')
                outcome = {'arm':current,'arm_index':index,'result':result,'oracle_before':before,'oracle_after':after,
                    'state_before':before_state,'state_after':after_state,
                    'drawer_joint_delta_m':float(after_state[1+world.qindex]-before_state[1+world.qindex]),
                    'handle_center_displacement_mm':float(np.linalg.norm(np.asarray(after['handle_center_m'])-before['handle_center_m'])*1000),
                    'nominal_fixed_point_gain_mm':nominal_gain,
                    'actual_fixed_point_gain_mm':float((np.linalg.norm(np.asarray(result['before'])-point)-np.linalg.norm(np.asarray(result['after'])-point))*1000),
                    'original_selected_continuation_exact':source_match,
                    **classify(controls, handle_names, before['gripper_to_designated_handle_surface_mm'], after['gripper_to_designated_handle_surface_mm'])}
                recorder.record('arm_completed', outcome)
                completed.append(current)
            finally:
                backend.close()
        recorder.record('termination', {'reason':'seven_arms_complete','executed_arms':completed,
            'missing_arms':[],'diagnostic_prefix_controls':PREFIX_CONTROLS*len(completed),
            'counterfactual_primitives':len(completed),'counterfactual_controls':8*len(completed),'model_calls':0})
    except BaseException as exc:
        recorder.record('failure', {'arm':current,'reason':repr(exc),'retries':0})
        recorder.record('termination', {'reason':'failure','executed_arms':completed,
            'missing_arms':[x for x in ARMS if x not in completed]})
        raise
    finally:
        recorder.close()


def audit(directory):
    directory = Path(directory)
    source = load_source()
    rows, errors = load_records(directory/'episodes.jsonl')
    if errors or data(rows, 'failure') or one(rows,'termination')['reason'] != 'seven_arms_complete':
        raise ValueError('complete failure-free seven-arm evidence required')
    frozen = one(rows,'frozen_inputs')
    start = one(rows,'run_start')
    prior, prior_errors = load_records(Path(start['resolved_config']['preflight'])/'episodes.jsonl')
    if (prior_errors or one(prior,'frozen_inputs') != frozen
            or start['manifest']['code'] != frozen['code'] or frozen['code']['dirty_status']
            or code_identity()['source_sha256'] != frozen['code']['source_sha256']
            or file_hash(PROTOCOL) != frozen['protocol_sha256']
            or file_hash(directory/'protocol.md') != frozen['protocol_sha256']):
        raise ValueError('preflight/code/protocol identity changed')
    if frozen['source_sha256'] != SOURCE_SHA256 or frozen['arms'] != list(ARMS):
        raise ValueError('frozen diagnostic changed')
    outcomes = data(rows,'arm_completed')
    if [x['arm'] for x in outcomes] != list(ARMS):
        raise ValueError('seven original options in fixed order required')
    handle_names = frozen['source_task_config']['measurements']['gripper_handle_contacts']['right']['geoms']
    prefix = data(source,'control_observation')[:PREFIX_CONTROLS]
    checks = 0
    for arm, outcome in zip(ARMS,outcomes):
        initial = [x for x in data(rows,'arm_initial_state') if x['arm']==arm]
        boundary = [x for x in data(rows,'preboundary') if x['arm']==arm]
        if (len(initial) != 1 or initial[0]['state'] != one(source,'environment')['sim_state']
                or len(boundary) != 1 or boundary[0]['state'] != frozen['source_preboundary_state']
                or boundary[0]['fixed_point_world_m'] != frozen['point_source']['admitted']['position_world_m']
                or boundary[0]['original_candidate'] != frozen['source_boundary_record']['canonical']['candidates'][ARMS.index(arm)]
                or boundary[0]['original_effect'] != frozen['source_boundary_record']['canonical']['effects']['effects'][arm]):
            raise ValueError('reset/point/candidate boundary changed')
        starts = [x for x in data(rows,'prefix_control_started') if x['arm']==arm]
        done = [x for x in data(rows,'prefix_control_completed') if x['arm']==arm]
        if len(starts) != PREFIX_CONTROLS or len(done) != PREFIX_CONTROLS:
            raise ValueError('incomplete prefix')
        for i,(start,completion,old) in enumerate(zip(starts,done,prefix)):
            if start['ordinal'] != i or completion['ordinal'] != i or any(completion[k] != old[k] or start[k] != old[k] for k in ('command','state_before')) or completion['state_after'] != old['state_after']:
                raise ValueError('recorded actual prefix differs')
            checks += 1
        controls = [x for x in data(rows,'arm_control_completed') if x['arm']==arm]
        intents = [x for x in data(rows,'arm_control_started') if x['arm']==arm]
        expected = frozen['source_preboundary_state']
        if len(controls) != 8 or len(intents) != 8:
            raise ValueError('incomplete native arm')
        for i,(intent,control) in enumerate(zip(intents,controls)):
            if control['control'] != i or any(control[k] != v for k,v in intent.items()) or control['state_before'] != expected:
                raise ValueError('native arm control chain changed')
            expected = control['state_after'];checks += 1
        if (outcome['state_before'] != frozen['source_preboundary_state'] or outcome['state_after'] != expected
                or outcome['result']['low_level_commands'] != [x['command'] for x in controls]):
            raise ValueError('arm result/control mismatch')
        qindex = boundary[0]['drawer_joint_qpos_index']
        if outcome['drawer_joint_delta_m'] != outcome['state_after'][1+qindex]-outcome['state_before'][1+qindex]:
            raise ValueError('direct drawer motion differs')
        if arm == 'MV_RIGHT':
            reference = data(source,'action')[SOURCE_BOUNDARY]
            if (outcome['result'] != reference['result'] or outcome['oracle_after'] != reference['oracle_after']
                    or outcome['original_selected_continuation_exact'] is not True
                    or any(any(row[k] != old[k] for k in ('command','state_before','state_after','contacts'))
                           for row,old in zip(controls,data(source,'control_observation')[PREFIX_CONTROLS:]))):
                raise ValueError('MV_RIGHT native continuation differs from original')
        computed = classify(controls,handle_names,outcome['oracle_before']['gripper_to_designated_handle_surface_mm'],outcome['oracle_after']['gripper_to_designated_handle_surface_mm'])
        if any(outcome[k] != v for k,v in computed.items()):
            raise ValueError('outcome differs from raw contacts/gaps')
    captures, trajectories = data(rows,'capture'), data(rows,'demo_trajectory')
    if len(captures) != 14 or len(trajectories) != 7:
        raise ValueError('incomplete rendered evidence')
    for arm, trajectory, outcome in zip(ARMS, trajectories, outcomes):
        controls = [x for x in data(rows,'arm_control_completed') if x['arm']==arm]
        with np.load(directory/trajectory['artifact'],allow_pickle=False) as arrays:
            if (arrays['commands'].tolist() != [x['command'] for x in controls]
                    or arrays['states_before'].tolist() != [x['state_before'] for x in controls]
                    or arrays['state_after'].tolist() != outcome['state_after'] or len(arrays['frames']) != 8):
                raise ValueError('native trajectory/control lineage differs')
    for row in captures+trajectories:
        if file_hash(directory/row['artifact']) != row['sha256']:
            raise ValueError('rendered artifact changed')
    return {'raw_sha256':file_hash(directory/'episodes.jsonl'),'source_sha256':SOURCE_SHA256,
        'prefix_and_arm_control_checks':checks,'arms':outcomes,'native_arms':7,'counterfactual_controls':56,
        'diagnostic_replay_controls':1400,'model_calls':0,
        'no_observed_robot_contact_positive_approach_arms':[x['arm'] for x in outcomes if x['no_observed_robot_contact_and_positive_approach']],
        'contract_valid_no_observed_robot_contact_positive_approach_arms':[x['arm'] for x in outcomes if x['no_observed_robot_contact_and_positive_approach'] and not x['result']['execution_contract_violation']],
        'no_observed_nonhandle_contact_positive_approach_arms':[x['arm'] for x in outcomes if x['no_observed_nonhandle_contact_and_positive_approach']],
        'scope':'one-step evaluator-only feasibility at one archived state; no policy or global reachability claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['preflight','run','audit'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--preflight')
    args = parser.parse_args()
    if args.mode == 'audit':
        print(json.dumps(audit(args.output),indent=2))
    elif args.mode == 'run' and not args.preflight:
        parser.error('frozen preflight required')
    else:
        run(args)


if __name__ == '__main__':
    main()
