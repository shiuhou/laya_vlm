"""Read-only metrics for the fixed cached/refreshed two-action physical pair.

Consumes separately released, hash-bound journals/receipts; never runs a policy,
replay, simulator, model, geometry computation or repair.
"""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from .records import file_hash, load_records

ORDER = ('cached', 'refreshed')
NORMAL = {'retarget_two_move_budget', 'rule_no_strict_nominal_improvement'}


def distance(tcp, point):
    tcp, point = np.asarray(tcp, float), np.asarray(point, float)
    if tcp.shape != (3,) or point.shape != (3,) or not np.isfinite([tcp, point]).all():
        raise ValueError('Finite three-coordinate sensor/own point required')
    return float(np.linalg.norm(tcp-point))


def analyze_records(records, diagnostics, *, own_goal, common_goal):
    """Derive metrics from every retained record, including partial runs."""
    def rows(kind, suffix=False):
        return [r['data'] for r in records if r['kind'] == kind
                and (not suffix or r['data'].get('step', -1) >= 29)]
    issues = deepcopy(diagnostics)
    decisions = [r for r in rows('decision', True) if r.get('native_phase') == 'retarget']
    if any(d['canonical']['state']['fields']['target.position_m']['value'] != own_goal for d in decisions):
        issues.append({'category': 'decision_goal_differs_from_bound_own_goal'})
    started, completed = rows('action_started', True), rows('action_completed', True)
    native_before, native_after = rows('native_before', True), rows('native_after', True)
    controls_before, controls_after = rows('control_started', True), rows('control_completed', True)
    endpoints = [r for r in rows('endpoint', True) if r.get('native_phase') == 'retarget']
    after = [r for r in rows('scene_boundary') if r.get('scene_boundary') == 'after']
    terminations = rows('termination')
    termination = terminations[0] if len(terminations) == 1 else None
    failures = [{'kind': r['kind'], 'data': r['data']} for r in records
                if r['kind'] in ('failure', 'retarget_failure')]

    def sample(tcp, *, source, step, read_time=None):
        return {'source': source, 'step': step, 'tcp_world_m': deepcopy(tcp),
                'read_time_s': read_time, 'exact_own_sample_time_s': None,
                'distance_to_common_fresh_sensor_point_m': distance(tcp, common_goal),
                'distance_to_own_goal_m': distance(tcp, own_goal)}
    trajectory = []
    if len(after) == 1:
        trajectory.append(sample(after[0]['own_observations']['robot0_eef_pos'],
            source='scene_boundary.after.own_observations', step=29,
            read_time=after[0]['capture_read_sim_time_s']))
    elif len(after) > 1:
        issues.append({'category': 'multiple_postevent_initial_samples'})
    for endpoint in endpoints:
        tcp = endpoint['own_observations']['robot0_eef_pos']
        if tcp != endpoint['proprioception']['tcp_pos_world_m']:
            issues.append({'category': 'endpoint_own_proprioception_mismatch', 'step': endpoint['step']})
        matching = [a for a in completed if a['step'] == endpoint['step']]
        read_time = matching[0]['result']['execution_after']['sim_time'] if len(matching) == 1 else None
        measured = sample(tcp, source='endpoint.own_observations', step=endpoint['step'], read_time=read_time)
        for key in ('distance_to_common_fresh_sensor_point_m', 'distance_to_own_goal_m'):
            if endpoint.get(key) != measured[key]:
                issues.append({'category': 'stored_distance_mismatch', 'step': endpoint['step'], 'field': key,
                               'stored': endpoint.get(key), 'derived': measured[key]})
        trajectory.append(measured)
    control_trajectory = [dict(sample(r['returned_own_observations']['robot0_eef_pos'],
        source='control_completed.returned_own_observations', step=r['step']), control=r['control'])
        for r in controls_after]

    gates = rows('initial_frame_gate')
    baseline, robot = None, None
    if len(gates) == 1:
        robot = set(gates[0]['groups_evaluator_only']['robot'])
        baseline = {tuple(sorted(c['geom_ids'])) for c in gates[0]['initial_contact_snapshot_evaluator_only']['contacts']
                    if c['normal_force_N'] > .05 and robot.intersection(c['geom_ids'])}
        if baseline != {tuple(sorted(p)) for p in gates[0]['initial_above_threshold_robot_pairs']}:
            issues.append({'category': 'initial_contact_baseline_mismatch'})
    contact_samples, maximum, new_pairs = [], None, set()
    for record in records:
        row = record['data']
        if (record['kind'] not in ('native_before', 'native_after') or row.get('step', -1) < 29
                or robot is None):
            continue
        relevant = [c for c in row['contacts'] if robot.intersection(c['geom_ids'])]
        if relevant:
            value = max(c['normal_force_N'] for c in relevant)
            maximum = value if maximum is None else max(maximum, value)
        pairs = {tuple(sorted(c['geom_ids'])) for c in relevant if c['normal_force_N'] > .05}-baseline
        new_pairs |= pairs
        if pairs:
            contact_samples.append({'kind': record['kind'], 'record_id': record['record_id'],
                'step': row['step'], 'control': row['control'], 'index': row['index'],
                'native_buffer_time_s': row['time_s'], 'new_pairs': [list(p) for p in sorted(pairs)]})
    if robot is not None and native_before + native_after and maximum is None:
        maximum = 0.
    counts = {'actions_started': len(started), 'actions_completed': len(completed),
        'controls_started': len(controls_before), 'controls_completed': len(controls_after),
        'native_before': len(native_before), 'native_after': len(native_after),
        'endpoints': len(endpoints), 'decision_boundaries': len(decisions)}
    if len(started) != len(completed) or len(controls_before) != len(controls_after) or len(native_before) != len(native_after):
        issues.append({'category': 'incomplete_action_control_or_native_pair'})
    for action in completed:
        step = action['step']
        actual = [sum(r['step'] == step for r in population) for population in
                  (controls_after, native_before, native_after)]
        if actual != [8, 200, 200] or action['controls'] != 8 or action['native_integrations'] != 200:
            issues.append({'category': 'completed_primitive_count_mismatch', 'step': step, 'actual': actual})
    if termination is not None:
        for key, value in [('retarget_attempted_actions', len(started)), ('retarget_completed_actions', len(completed))]:
            if termination.get(key) != value:
                issues.append({'category': 'termination_count_mismatch', 'field': key})
    equivalence = rows('retarget_input_equivalence')
    shape_ok = (1 <= len(decisions) <= 2 and [d['boundary'] for d in decisions] == list(range(len(decisions)))
        and [d['selected'] for d in decisions if d['selected'] != 'STOP'] == [a['token'] for a in completed]
        and all(a.get('native_phase') == 'retarget' for a in started + completed)
        and (termination is not None and (
            termination.get('reason') == 'retarget_two_move_budget' and len(completed) == 2
            or termination.get('reason') == 'rule_no_strict_nominal_improvement' and decisions[-1]['selected'] == 'STOP')))
    normal = (not issues and not failures and termination is not None and termination.get('reason') in NORMAL
              and len(equivalence) == 1 and len(after) == 1 and len(endpoints) == len(completed)
              and len(completed) <= 2 and not new_pairs and robot is not None and shape_ok
              and records[-1]['kind'] == 'termination' and not rows('first_new_robot_contact')
              and all(not a['result']['execution_contract_violation'] for a in completed))
    return {'status': 'normally_completed' if normal else 'incomplete_or_adverse',
        'termination': termination, 'failures': failures, 'issues': issues, 'counts': counts,
        'decisions': [{'boundary': d['boundary'], 'step': d['step'], 'selected': d['selected'],
                       'recorded_goal': d['canonical']['state']['fields']['target.position_m']['value']}
                      for d in decisions],
        'started_tokens': [r['token'] for r in started], 'completed_tokens': [r['token'] for r in completed],
        'initial_and_endpoint_trajectory': trajectory, 'returned_control_trajectory': control_trajectory,
        'executor_results': [{'step': a['step'], 'token': a['token'], 'result': a['result']} for a in completed],
        'max_observed_robot_normal_force_N': maximum,
        'original_initial_contact_baseline': None if baseline is None else [list(p) for p in sorted(baseline)],
        'new_robot_pairs_over_0p05N': None if baseline is None else [list(p) for p in sorted(new_pairs)],
        'all_new_pair_native_observations': contact_samples,
        'reported_first_new_robot_contacts': rows('first_new_robot_contact'),
        'input_equivalence': equivalence, 'replay_status': 'not_supplied',
        'own_goal_world_m': deepcopy(own_goal), 'common_goal_world_m': deepcopy(common_goal),
        'common_target_is_fixed_sensor_point_not_current_material_truth': True}


def inspect_arm(directory, journal_sha256, *, own_goal, common_goal, replay_receipts):
    """Read only explicitly hash-bound journal and existing replay receipts."""
    directory = Path(directory)
    path = directory/'episodes.jsonl'
    if file_hash(path) != journal_sha256:
        raise ValueError('Bound episode journal changed')
    records, diagnostics = load_records(path)
    result = analyze_records(records, diagnostics, own_goal=own_goal, common_goal=common_goal)
    receipts = {}
    for path, digest in replay_receipts.items():
        path = Path(path)
        if file_hash(path) != digest:
            raise ValueError('Bound replay receipt changed')
        if path.name in receipts:
            raise ValueError('Duplicate replay receipt name')
        receipts[path.name] = {'path': str(path), 'sha256': digest, 'data': json.loads(path.read_text())}
    passed = (set(receipts) == {'result.json', 'scene-result.json'} and all(
        r['data'].get('status') == 'passed' and r['data'].get('source_journal_sha256') == journal_sha256
        for r in receipts.values()))
    if passed:
        replay = receipts['result.json']['data']
        passed = (replay['exact_controls'] == sum(r['kind'] == 'control_completed' for r in records)
            and replay['exact_native_snapshots'] == sum(r['kind'] in ('native_before', 'native_after') for r in records)
            and replay['exact_captures'] == sum(r['kind'] == 'vision_capture' for r in records)
            and receipts['scene-result.json']['data'].get('events') == 1)
    result.update(journal_sha256=journal_sha256, replay_receipts=receipts,
                  replay_status='passed_bound_receipts' if passed else 'missing_failed_or_mismatched_receipts')
    return result


def compare_pair(arms):
    """Keep a fixed population and withhold paired metrics after any failed arm."""
    if list(arms) != list(ORDER):
        raise ValueError('Both declared arms, cached then refreshed, must be retained')
    rows = {arm: value if value is not None else {'status': 'not_run'} for arm, value in arms.items()}
    first = None
    if all('decisions' in row for row in rows.values()):
        for a, b in zip(rows['cached']['decisions'], rows['refreshed']['decisions']):
            if a['boundary'] == b['boundary'] and a['selected'] != b['selected']:
                first = {'boundary': a['boundary'], 'cached': a['selected'], 'refreshed': b['selected']}
                break
    qualified = all(row['status'] == 'normally_completed' and row.get('replay_status') == 'passed_bound_receipts'
                    for row in rows.values())
    if qualified:
        qualified = (rows['cached']['common_goal_world_m'] == rows['refreshed']['common_goal_world_m']
            and rows['cached']['initial_and_endpoint_trajectory'][0]['tcp_world_m']
                == rows['refreshed']['initial_and_endpoint_trajectory'][0]['tcp_world_m']
            and rows['cached']['initial_and_endpoint_trajectory'][0]['read_time_s']
                == rows['refreshed']['initial_and_endpoint_trajectory'][0]['read_time_s'])
    difference = None
    action_difference = None
    if all('completed_tokens' in row for row in rows.values()):
        a, b = (rows[arm]['completed_tokens'] for arm in ORDER)
        for index, (left, right) in enumerate(zip(a, b)):
            if left != right:
                action_difference = {'completed_action_index': index, 'cached': left, 'refreshed': right}
                break
        if (action_difference is None and len(a) != len(b)
                and all(row['status'] == 'normally_completed' for row in rows.values())):
            index = min(len(a), len(b))
            action_difference = {'completed_action_index': index,
                'cached': a[index] if index < len(a) else None,
                'refreshed': b[index] if index < len(b) else None,
                'one_normally_terminated_sequence_ended': True}
    if qualified:
        finals = [rows[a]['initial_and_endpoint_trajectory'][-1]['distance_to_common_fresh_sensor_point_m'] for a in ORDER]
        difference = finals[1]-finals[0]
    return {'arms': rows, 'both_normal_and_replay_verified': qualified,
        'first_observed_decision_divergence': first,
        'first_observed_completed_action_divergence': action_difference,
        'refreshed_minus_cached_final_common_point_distance_m': difference,
        'winner': None, 'task_success_claim': False, 'new_model_physics_or_replay_calls': 0}
