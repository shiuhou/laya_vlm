"""Fresh POINT -> canonical geometric rule -> native atomic executor diagnostic.

No fusion, confidence fabrication, model motor decision, preview or task policy.
Oracle measurements are evaluation/external abort only.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import random
import signal
import sys
import time

import numpy as np

from ..decision_interface import (CanonicalDecisionInput, CanonicalDecisionState,
    Evidence, FIELD_NAMES, derive_relations, evidence, geometric_effects, shared_atomic_candidates)
from ..runtime_core import AtomicExecutor, MOVE
from ..vision import camera_to_world, pixel_to_camera
from .point_grounding_probe import QUERY, SETTINGS, generation_audit, parse_grounding, serialize_model_config
from .records import (RunRecorder, code_identity, file_hash, model_identity, versions,
                      repository_identity, package_directory, load_records)

PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/coarse_point_probe_protocol.md'
VERSION = 'fresh-point-coarse-approach-v1'
EXPECTED_MODEL_CONTENT_ID = '4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f'


def admit_point(parsed, audit, frame):
    if parsed['status'] != 'single_point':
        raise ValueError(f"point_admission:{parsed['status']}")
    if not audit['terminal_eos_observed'] or audit['length_limit_reached']:
        raise ValueError('point_admission:incomplete_or_length_limited')
    x, y = parsed['points'][0]['sample_pixel_xy']
    z = float(frame['depth_m'][y, x])
    if not np.isfinite(z) or not .01 <= z <= 5:
        raise ValueError('point_admission:invalid_depth')
    point = camera_to_world(pixel_to_camera(x+.5, y+.5, z, frame['intrinsics']), frame['camera_to_world'])
    if not np.isfinite(point).all():
        raise ValueError('point_admission:invalid_projection')
    return {'position_world_m': point.tolist(), 'sample_pixel_xy': [x, y],
            'sample_pixel_center_xy': [x+.5, y+.5], 'depth_m': z,
            'admission': 'fresh_single_POINT_EOS_finite_depth_not_identity_or_safety_verification'}


def decision_input(admitted, proprio, frame, history=()):
    f = {key: Evidence() for key in FIELD_NAMES}
    f['task.instruction'] = evidence('Approach the reported target point.', 'task', 'coarse approach diagnostic')
    f['task.target_identity'] = evidence(QUERY, 'task', 'requested identity; not verified')
    for dest, source in [('tcp_position_m','tcp_pos_world_m'), ('gripper_width_m','gripper_width_m'),
                         ('gripper_command','gripper_command')]:
        f[f'robot.{dest}'] = evidence(proprio[source], 'proprioception', 'robot sensor/retained command')
    f['target.position_m'] = evidence(admitted['position_world_m'], 'sensor', 'fresh POINT pixel-center RGB-D projection')
    f['target.position_definition'] = evidence('reported_POINT_containing_pixel_center_depth', 'sensor', 'no box or oracle correction')
    f['quality.geometry_valid'] = evidence(True, 'derived', admitted['admission'])
    f['quality.geometry_age_s'] = evidence(0., 'sensor', 'simulation paused since capture')
    derive_relations(f)
    state = CanonicalDecisionState(f, {'revision': frame['capture_seq'], 'asof_sim_time': frame['capture_sim_time'],
                                      'tracking_active': False, 'admission_policy': VERSION})
    candidates = tuple(c for c in shared_atomic_candidates() if c.token in {*MOVE, 'STOP'})
    return CanonicalDecisionInput(state, candidates, geometric_effects(state, candidates), history)


def point_call(worker, frame, recorder):
    from PIL import Image
    question = f'Point to: {QUERY}.'
    messages = [{'role':'user', 'content':[{'type':'image','image':Image.fromarray(frame['rgb']).convert('RGB')},
                                         {'type':'text','text':question}]}]
    text = worker.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos = worker.processor.process_vision_info(messages)
    inputs = worker.processor(text=[text], images=images, videos=videos, return_tensors='pt').to(worker.device)
    ids = inputs['input_ids'].detach().cpu().tolist()[0]
    grid = inputs.get('image_grid_hws')
    grid = None if grid is None else grid.detach().cpu().tolist() if hasattr(grid, 'detach') else np.asarray(grid).tolist()
    pixel_values = inputs['pixel_values'].to(worker.dtype)
    relative = Path('model-inputs') / f"capture-{frame['capture_seq']:06d}.npz"
    (recorder.output / relative).parent.mkdir(exist_ok=True)
    with (recorder.output / relative).open('xb') as stream:
        np.savez_compressed(stream, pixel_values_float32=pixel_values.detach().float().cpu().numpy())
    recorder.record('point_call_started', {'capture_seq':frame['capture_seq'], 'question':question,
        'formatted_text':text, 'input_token_ids':ids, 'input_token_count':len(ids), 'image_grid_hws':grid,
        'pixel_values_artifact':str(relative), 'pixel_values_sha256':file_hash(recorder.output / relative),
        'pixel_values_original_dtype':str(pixel_values.dtype), 'storage':'float32 exact representation of bfloat16 values',
        'attention_mask':inputs['attention_mask'].detach().cpu().tolist()})
    original, observed = worker.tokenizer.batch_decode, []
    def decode(sequences, *args, **kwargs):
        observed.append(sequences.detach().cpu().tolist())
        return original(sequences, *args, **kwargs)
    worker.tokenizer.batch_decode = decode
    started = time.perf_counter()
    try:
        with worker.torch.no_grad():
            raw = worker.model.generate(pixel_values=pixel_values,
                input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'],
                image_grid_hws=inputs.get('image_grid_hws'), tokenizer=worker.tokenizer, **SETTINGS)
    finally:
        worker.tokenizer.batch_decode = original
    if len(observed) != 1 or len(observed[0]) != 1:
        raise ValueError('actual_generated_tokens_unavailable')
    raw = raw[0] if isinstance(raw, tuple) else raw
    parsed = parse_grounding(raw, frame['rgb'].shape[1], frame['rgb'].shape[0])
    audit = generation_audit(observed[0][0], len(ids), worker.tokenizer.model_max_length,
                              worker.tokenizer.convert_tokens_to_ids('<|im_end|>'))
    recorder.record('point_call_completed', {'capture_seq':frame['capture_seq'], 'raw_output':raw,
        'parsed':parsed, 'generation_audit':audit, 'latency_s':time.perf_counter()-started})
    return parsed, audit


def contact_rows(measurements):
    """Every MuJoCo contact involving any robot collision geom; no hidden force filter."""
    measurements._reset()
    w = measurements.world
    robot = measurements.ids({'group':'robot'})
    rows = []
    for i, (a, b, force) in enumerate(measurements.contacts()):
        if a not in robot and b not in robot:
            continue
        c = w.data.contact[i]
        rows.append({'geom_ids': sorted([a,b]), 'geom_names':[w.env.sim.model.geom_id2name(g) for g in (a,b)],
            'robot_sides':[a in robot,b in robot], 'normal_force_N':force,
            'position_world_m':np.asarray(c.pos).tolist(), 'distance_m':float(c.dist)})
    return rows


def force_pairs(rows, threshold):
    return {tuple(row['geom_ids']) for row in rows if row['normal_force_N'] > threshold}


@contextmanager
def observe_controls(world, measurements, recorder, step):
    original, controls = world.env.step, []
    def observed(command):
        before = world.env.sim.get_state().flatten().copy()
        recorder.record('control_started', {'step':step, 'control':len(controls),
            'command':np.asarray(command).tolist(), 'state_before':before})
        result = original(command)
        row = {'step':step, 'control':len(controls), 'command':np.asarray(command).tolist(),
               'state_before':before.tolist(), 'state_after':world.env.sim.get_state().flatten().tolist(),
               'sim_time_s':float(world.data.time), 'contacts':contact_rows(measurements)}
        controls.append(row)
        recorder.record('control_observation', row)
        return result
    world.env.step = observed
    try:
        yield controls
    finally:
        world.env.step = original


def oracle_evaluation(backend, gap, measurements):
    f = backend.world.features()
    handle = np.asarray(f['handle_center_mm']) / 1000
    return {'privileged':True, 'purpose':'evaluation_and_external_abort_only',
        'tcp_to_designated_handle_center_m':float(np.linalg.norm(backend.tcp_pos()-handle)),
        'gripper_to_designated_handle_surface_mm':gap.minimum_mm(backend.world.data),
        'handle_center_m':handle.tolist(), 'remaining_open_mm':f['remaining_open_mm'],
        'valid_handle_contact':f['valid_handle_contact'], 'official_success':f['success'],
        'contacts':contact_rows(measurements)}


def run(args, *, protocol=PROTOCOL, experiment_profile=None):
    from ..adapters.libero_rgbd import LiberoRgbdSource
    from ..adapters.locateanything import LocateAnythingWorker
    from .engineering_demo import RecordingBackend, save_trajectory
    from .collect_pairs import initial_state_inventory
    import torch
    out = Path(args.output)
    protocol = Path(protocol)
    profile_metadata = {} if experiment_profile is None else {'experiment_profile':experiment_profile}
    recorder = RunRecorder(out, {**vars(args), 'version':VERSION, 'settings':SETTINGS,
        'protocol_sha256':file_hash(protocol), 'query':QUERY, 'oracle_in_decision':False,
        'external_oracle_contact_abort':True, 'no_manipulation_claim':True, **profile_metadata},
        {'run_id':out.name, 'code':code_identity(), 'versions':versions()})
    (out/'protocol.md').write_bytes(protocol.read_bytes())
    backend, executed, step, reason, history = None, 0, None, 'runtime_failure', ()
    previous_handlers = {}
    def interrupted(sig, _frame):
        raise TimeoutError(f'wall_or_signal_limit:{sig}')
    try:
        for sig in (signal.SIGALRM, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, args.timeout_s)
        random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
        recorder.record('invocation', {'argv':sys.argv, 'python':sys.executable, 'cwd':str(Path.cwd()),
            'environment':{k:os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE')}})
        identity = model_identity(args.locateanything_path)
        recorder.manifest_update({'model':identity, 'expected_model_content_id':EXPECTED_MODEL_CONTENT_ID})
        if identity['content_id'] != EXPECTED_MODEL_CONTENT_ID:
            raise ValueError('LocateAnything checkpoint differs from frozen POINT probe')
        inventory = initial_state_inventory('top_drawer', args.libero_root, args.config_dir)
        recorder.record('initial_identity', {'task':'top_drawer', 'init_state_id':0, 'seed':1,
            'binding':inventory['binding'], 'benchmark_state_id':inventory['state_ids'][0]})
        backend = RecordingBackend.from_task('top_drawer', seed=1, init_state_id=0, render=True,
            libero_root=args.libero_root, config_dir=args.config_dir)
        w = backend.world
        from jev_libero.measurements import Measurements
        from jev_libero.geometry import GeometryGap
        import jev_libero.world
        import libero
        measurements = Measurements(w)
        handle_ids = measurements.ids(w.config['measurements']['handle_center_mm']['entity'])
        gap = GeometryGap(w.model, w.gripper_geoms, handle_ids)
        threshold = w.config['contact']['min_normal_force_N']
        initial_contacts = contact_rows(measurements)
        initial_pairs = force_pairs(initial_contacts, threshold)
        recorder.manifest_update({'environment_repositories':{
            'jev':repository_identity(package_directory(jev_libero.world)),
            'libero':repository_identity(package_directory(libero))}})
        recorder.record('environment', {'task_config':w.config, 'sim_state':w.env.sim.get_state().flatten(),
            'initial_state':backend.execution_state(), 'robot_contact_geom_ids':sorted(measurements.ids({'group':'robot'})),
            'initial_contacts':initial_contacts, 'new_contact_force_threshold_N':threshold})
        locator = LocateAnythingWorker(args.locateanything_path, device=args.device)
        recorder.manifest_update({'model_config':serialize_model_config(locator.model.config.to_dict()),
            'dtype':str(locator.dtype), 'tokenizer_model_max_length':locator.tokenizer.model_max_length})
        source, executor = LiberoRgbdSource(w), AtomicExecutor(backend)
        for step in range(args.steps+1):
            state_before_sensing = w.env.sim.get_state().flatten().copy()
            before_eval = oracle_evaluation(backend, gap, measurements)
            recorder.record('oracle_boundary', {'step':step, **before_eval})
            frame = source.capture()
            recorder.capture(frame)
            parsed, audit = point_call(locator, frame, recorder)
            unchanged = np.array_equal(state_before_sensing, w.env.sim.get_state().flatten())
            recorder.record('paused_state_check', {'step':step, 'unchanged':bool(unchanged),
                'scope':'flattened simulator time/qpos/qvel only; excludes controller and solver caches',
                'read_render_noninterference_test':'independent actual-control replay',
                'before':state_before_sensing, 'after':w.env.sim.get_state().flatten()})
            if not unchanged:
                raise RuntimeError('state_changed_during_capture_or_inference')
            admitted = admit_point(parsed, audit, frame)
            view = decision_input(admitted, backend.proprioception(), frame, history)
            recommended = view.rule_token()
            token = recommended if args.condition == 'rule' else 'STOP'
            recorder.record('decision_boundary', {'step':step, 'capture_seq':frame['capture_seq'],
                'canonical':asdict(view), 'admitted':admitted, 'rule_recommendation':recommended,
                'selected':token, 'choice_source':'deterministic_'+args.condition, 'terminal_observation':step==args.steps})
            if step == args.steps:
                reason = 'action_budget'; break
            # Rule STOP is an explicit terminal coarse-approach result, not a grasp command.
            if args.condition == 'rule' and token == 'STOP':
                reason = 'no_strict_nominal_improvement'; break
            recorder.record('execution_started', {'step':step, 'token':token})
            with observe_controls(w, measurements, recorder, step) as controls:
                result = executor.execute(token)
            executed += 1
            save_trajectory(backend, out, step, recorder)
            after_eval = oracle_evaluation(backend, gap, measurements)
            point = np.asarray(admitted['position_world_m'])
            new_contacts = sorted(set().union(*(force_pairs(c['contacts'], threshold) for c in controls))-initial_pairs)
            recorder.record('action', {'step':step, 'token':token, 'result':result,
                'sensor_fixed_point_distance_before_m':float(np.linalg.norm(np.asarray(result['before'])-point)),
                'sensor_fixed_point_distance_after_m':float(np.linalg.norm(np.asarray(result['after'])-point)),
                'oracle_before':before_eval, 'oracle_after':after_eval, 'new_robot_contact_pairs':new_contacts,
                'contact_abort_is_external_oracle':True})
            history = ({'action':token, 'tcp_delta_m':result['delta_m'],
                'elapsed_sim_s':result['execution_after']['sim_time']-result['execution_before']['sim_time'],
                'gripper_command':backend.proprioception()['gripper_command'], 'source':'proprioception'},)
            if result['execution_contract_violation'] or new_contacts:
                reason = 'execution_contract_violation' if result['execution_contract_violation'] else 'external_oracle_new_robot_contact'
                break
        recorder.record('termination', {'reason':reason, 'executed_primitives':executed, 'boundary':step,
            'laya_decisions':0, 'manipulation_success_claim':False})
    except BaseException as exc:
        recorder.record('failure', {'boundary':step, 'executed_primitives':executed, 'reason':repr(exc), 'retries':0})
        recorder.record('termination', {'reason':'wall_limit' if isinstance(exc, TimeoutError) else 'runtime_or_admission_failure',
            'executed_primitives':executed, 'boundary':step, 'laya_decisions':0})
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
    return out


def control_endpoints(actions, controls):
    endpoints, cumulative = {}, 0
    initial_time = actions[0]['result']['execution_before']['sim_time'] if actions else None
    for i, action in enumerate(actions):
        n = sum(c['step'] == action['step'] for c in controls)
        if n <= 0 or n != action['result']['environment_step_count']:
            raise ValueError('actual control count differs from execution evidence')
        cumulative += n
        endpoints[cumulative] = {'action_count':i+1, 'cumulative_actual_controls':cumulative,
            'cumulative_sim_elapsed_s':action['result']['execution_after']['sim_time']-initial_time,
            'oracle_after':action['oracle_after']}
    return endpoints


def compare(rule, hold, output):
    arms, configs, initial_states, models, provenance = [], [], [], [], []
    for label, path in zip(('rule','hold'), (rule, hold)):
        records, errors = load_records(Path(path)/'episodes.jsonl')
        if errors:
            raise ValueError('incomplete evidence chain')
        start = next(r['data'] for r in records if r['kind']=='run_start')
        config = start['resolved_config']
        if config['condition'] != label:
            raise ValueError('comparison arm order must be rule, hold')
        configs.append({k:v for k,v in config.items() if k not in ('output','condition')})
        environment = next(r['data'] for r in records if r['kind']=='environment')
        initial_states.append(environment['sim_state'])
        provenance.append({'code_commit':start['manifest']['code']['commit'],
            'code_source_sha256':start['manifest']['code']['source_sha256'],
            'task_config':environment['task_config'],
            'initial_identity':next(r['data'] for r in records if r['kind']=='initial_identity'),
            'environment_repositories':next(r['data']['environment_repositories'] for r in records
                if r['kind']=='manifest_update' and 'environment_repositories' in r['data'])})
        models.append(next(r['data']['model']['content_id'] for r in records
                           if r['kind']=='manifest_update' and 'model' in r['data']))
        actions = [r['data'] for r in records if r['kind']=='action']
        controls = [r['data'] for r in records if r['kind']=='control_observation']
        arms.append({'source':str(path), 'source_sha256':file_hash(Path(path)/'episodes.jsonl'),
            'control_endpoints':control_endpoints(actions, controls),
            'actions':actions, 'termination':[r['data'] for r in records if r['kind']=='termination']})
    if (configs[0] != configs[1] or initial_states[0] != initial_states[1]
            or models[0] != models[1] or provenance[0] != provenance[1]):
        raise ValueError('same-condition comparison provenance mismatch')
    common = min(len(a['actions']) for a in arms)
    shared_counts = sorted(set(arms[0]['control_endpoints']) & set(arms[1]['control_endpoints']))
    matched = []
    for count in shared_counts:
        r, h = [a['control_endpoints'][count] for a in arms]
        matched.append({'cumulative_actual_controls':count, 'rule':r, 'hold':h,
            'sim_elapsed_matched':abs(r['cumulative_sim_elapsed_s']-h['cumulative_sim_elapsed_s']) <= 1e-12,
            'tcp_to_handle_distance_rule_minus_hold_m':r['oracle_after']['tcp_to_designated_handle_center_m']-h['oracle_after']['tcp_to_designated_handle_center_m'],
            'gripper_to_handle_gap_rule_minus_hold_mm':r['oracle_after']['gripper_to_designated_handle_surface_mm']-h['oracle_after']['gripper_to_designated_handle_surface_mm']})
    result = {'comparison':'common_actual_control_count_endpoints_with_sim_elapsed_audit', 'common_actions':common,
        'same_condition_provenance_verified':True, 'matched_provenance':provenance[0],
        'common_control_endpoints':matched, 'common_cumulative_actual_control_counts':shared_counts,
        'unequal_horizon_censoring':len(arms[0]['actions'])!=len(arms[1]['actions']), 'arms':arms,
        'common_prefix':[{ 'action_count':i+1, **{label:arm['actions'][i]['oracle_after']
            for label,arm in zip(('rule','hold'),arms)}} for i in range(common)]}
    Path(output).write_text(json.dumps(result, indent=2)+'\n')
    return result


def replay_check(directory, backend_factory=None):
    """Every observed actual control, including any incomplete atomic primitive."""
    from ..adapters.libero import LiberoWorldBackend
    directory = Path(directory)
    records, errors = load_records(directory/'episodes.jsonl')
    if errors:
        raise ValueError('incomplete evidence chain')
    config = next(r['data']['resolved_config'] for r in records if r['kind']=='run_start')
    controls = [r['data'] for r in records if r['kind']=='control_observation']
    starts = [r['data'] for r in records if r['kind']=='control_started']
    if len(starts) != len(controls):
        raise ValueError('unacknowledged control: exact replay cannot certify completion')
    backend = backend_factory(config) if backend_factory else LiberoWorldBackend.from_task(
        'top_drawer', seed=1, init_state_id=0, render=False,
        libero_root=config['libero_root'], config_dir=config['config_dir'])
    checks = []
    try:
        w = backend.world
        initial = next(r['data']['sim_state'] for r in records if r['kind']=='environment')
        checks.append({'boundary':'initial', 'max_error':float(np.max(np.abs(w.env.sim.get_state().flatten()-initial)))})
        for start, row in zip(starts, controls, strict=True):
            if any(start[key] != row[key] for key in ('step','control','command','state_before')):
                raise ValueError('control start/completion mismatch')
            for phase in ('before','after'):
                if phase == 'after':
                    w.obs, _, _, _ = w.env.step(row['command'])
                checks.append({'boundary':f"{row['step']}:{row['control']}:{phase}",
                    'max_error':float(np.max(np.abs(w.env.sim.get_state().flatten()-row[f'state_{phase}'])))})
        result = {'kind':'actual_controls_replay_not_independent_policy_run', 'tolerance':1e-8,
            'controls':len(controls), 'checks':checks, 'passed':bool(controls) and all(c['max_error'] <= 1e-8 for c in checks),
            'raw_source_sha256':file_hash(directory/'episodes.jsonl')}
        (directory/'replay-check.json').write_text(json.dumps(result, indent=2)+'\n')
        return result
    finally:
        backend.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--condition', choices=('rule','hold'), default='rule')
    p.add_argument('--steps', type=int, default=20)
    p.add_argument('--seed', type=int, default=1)
    p.add_argument('--init-state-id', type=int, default=0)
    p.add_argument('--device', default='cuda')
    p.add_argument('--locateanything-path', default='/home/junhongli/models/huggingface/LocateAnything-3B')
    p.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    p.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    p.add_argument('--timeout-s', type=float, default=900.)
    p.add_argument('--replay-check', action='store_true')
    p.add_argument('--compare', nargs=2, metavar=('RULE','HOLD'))
    args = p.parse_args()
    if args.replay_check:
        result = replay_check(args.output)
        print(json.dumps(result, indent=2))
        if not result['passed']:
            raise SystemExit(1)
    elif args.compare:
        compare(*args.compare, args.output)
    else:
        if not 1 <= args.steps <= 20 or args.seed != 1 or args.init_state_id != 0 or not 0 < args.timeout_s <= 900:
            raise ValueError('frozen task/init/seed and bounded budget required')
        print(run(args))


if __name__ == '__main__':
    main()
