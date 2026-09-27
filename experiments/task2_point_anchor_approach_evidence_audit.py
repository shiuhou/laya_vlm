"""Independent stored paired POINT endpoint-veto/replay audit; no simulation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull


MOVE = {'MV_FWD': [1., 0., 0.], 'MV_BACK': [-1., 0., 0.], 'MV_LEFT': [0., 1., 0.],
        'MV_RIGHT': [0., -1., 0.], 'MV_UP': [0., 0., 1.], 'MV_DOWN': [0., 0., -1.]}
FRAME_KEYS = ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, description):
    if not condition:
        raise AssertionError(description)


def near(a, b, description, tolerance=1e-12):
    require(np.allclose(a, b, rtol=0, atol=tolerance), description)


def contact_class(pair, groups):
    a, b = pair
    if a in groups['robot'] and b in groups['robot']:
        return 'self'
    for family, label in [('pads', 'pad/bottle'), ('gripper', 'other_gripper/bottle')]:
        if (a in groups[family] and b in groups['bottle']) or (b in groups[family] and a in groups['bottle']):
            return label
    return 'gripper/other_scene' if a in groups['gripper'] or b in groups['gripper'] else 'arm/scene'


def strong(snapshot, robot):
    return {tuple(sorted(c['geom_ids'])) for c in snapshot['contacts']
            if c['normal_force_N'] > .05 and any(g in robot for g in c['geom_ids'])}


def audit_guard(decisions, starts, endpoints, gate, manifest, sources):
    packet = manifest['endpoint_guard']
    require(sha(sources/'task2-observed-surface-sweep-run-01/request.json') == 'b1e815e896c4059163cc367deb0c84abfa960f3146f829278fdaadebd61183ed', 'sealed geometry request')
    request = read(sources/'task2-observed-surface-sweep-run-01/request.json')
    require(packet['full_support'] == request['full_support'] and packet['calibration'] == request['calibration'], 'exact sealed original support/calibration')
    require(packet['containment_halfspace_numeric_tolerance'] == 1e-12 and packet['physical_margin_m'] == 0 and packet['sweep_computed'] is False and packet['support_refreshed'] is False and packet['mask_cleanup'] is False, 'registered no-margin endpoint-only intervention')
    points = np.asarray([r['position_world_m'] for r in packet['full_support']])
    require(len(points) == 1340, 'all original observed points')
    geoms = [g['name'] for g in packet['calibration']['geometries']]
    own_keys = ('robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos')
    first, report = None, []
    for step, decision in enumerate(decisions):
        require(decision['step'] == step, 'every decision including terminal STOP')
        view, selection = decision['canonical'], decision['experiment_selection']
        fields = view['state']['fields']
        own = (starts[step*8]['previous_returned_own_observations'] if step*8 < len(starts) else
               endpoints[-1]['own_observations'] if endpoints else gate['initial_own_observations'])
        require(selection['own_packet'] == {k: own[k] for k in own_keys}, 'exact sanitized own packet')
        require(fields['robot.tcp_position_m']['value'] == own['robot0_eef_pos'] and fields['robot.gripper_width_m']['value'] == float(np.abs(own['robot0_gripper_qpos']).sum()), 'point rule and placement use same returned own data')
        require(selection['own_sample_time_s'] is None and selection['STOP_semantics'] == 'termination_before_execute', 'unknown timing and original STOP semantics')
        vertices = selection['current_proxy_vertices_world_m']
        require(set(vertices) == set(geoms), 'five separate saved solids')
        for name,v in vertices.items():
            require(np.asarray(v).shape == (len(next(g for g in packet['calibration']['geometries'] if g['name'] == name)['vertices_local_m']),3) and np.isfinite(v).all(), 'saved proxy vertex schema')
        delta = np.asarray(fields['relations.tcp_target_delta_m']['value'])
        require(delta.tolist() == (np.asarray(manifest['point']['position_world_m'])-own['robot0_eef_pos']).tolist(), 'guard uses original cached P delta')
        require(all(not field['privileged'] for field in fields.values()), 'no privileged decision field')
        require(fields['task.target_identity']['value'] == 'the wine bottle'
                and fields['target.position_m']['value'] == manifest['point']['position_world_m']
                and fields['target.position_definition']['value'] == manifest['point']['definition'], 'fixed POINT goal, canonical object identity')
        require('native POINT pixel-center' in fields['target.position_m']['basis']
                and 'BOX median-ray' not in fields['target.position_m']['basis'], 'POINT provenance corrected')
        require(view['state']['meta']['goal_anchor'] == manifest['goal_anchor']
                and view['state']['meta']['guard_support_role'] == 'separate_original_full_BOX_observed_depth_support', 'separate goal/support roles')
        for key in ('quality.semantic_valid', 'quality.semantic_confidence', 'quality.temporal_consistency_ok', 'interaction.holding'):
            require(fields[key]['value'] is None, 'unknown semantic/interaction evidence')
        require([candidate['token'] for candidate in view['candidates']] == [*MOVE, 'STOP'], 'all canonical candidates in fixed order')
        require(view['effects']['candidate_set_id'] == canonical({'candidates': view['candidates']}), 'original candidate identity')
        require(fields['relations.distance_m']['value'] == decision['live_tcp_to_fixed_proxy_m'] == float(np.linalg.norm(delta)), 'every decision distance')
        require(fields['relations.xy_error_m']['value'] == float(np.linalg.norm(delta[:2]))
                and fields['relations.height_error_m']['value'] == float(delta[2]), 'every decision relative geometry')
        effects = view['effects']['effects']
        require(effects['STOP'] == {'source': 'unknown', 'privileged': False, 'values': {}}, 'STOP has no invented effect')
        for token, vector in MOVE.items():
            moved = delta - np.asarray(vector) * .01
            require(effects[token] == {'source': 'geometry', 'privileged': False, 'state_id': canonical(view['state']),
                'geometry_valid': True, 'assumptions': 'stationary target; nominal 10 mm world translation; no contact/dynamics',
                'values': {'distance_change_m': float(np.linalg.norm(moved) - np.linalg.norm(delta)),
                           'xy_error_change_m': float(np.linalg.norm(moved[:2]) - np.linalg.norm(delta[:2]))}}, 'every nominal effect and state identity')
        exclusion = selection['all_seven_candidates']
        require(set(exclusion) == {*MOVE,'STOP'}, 'all seven candidates retained')
        blocked, scored, diagnostics = [], [], {}
        for token in [*MOVE,'STOP']:
            move = np.asarray(MOVE.get(token,[0,0,0]))*.01
            entry, union = exclusion[token], set()
            require(entry['nominal_delta_m'] == move.tolist() and set(entry['proxies']) == set(geoms), 'fixed endpoint delta and separate proxy rows')
            for name in geoms:
                hull = ConvexHull(np.asarray(vertices[name])+move)
                equations = hull.equations
                inside = np.all(points@equations[:,:3].T+equations[:,3] <= 1e-12,axis=1)
                indices = np.flatnonzero(inside).tolist()
                require(entry['proxies'][name] == {'contained_point_count':len(indices),'full_support_indices':indices}, 'independent saved-vertex halfspace containment')
                union.update(indices)
            excluded = token != 'STOP' and bool(union)
            reason = 'terminal_option_no_primitive' if token == 'STOP' else 'observed_point_inside_nominal_endpoint' if excluded else 'no_observed_endpoint_containment'
            require(entry['excluded'] == excluded and entry['reason'] == reason and entry['contained_point_count'] == len(union), 'OR of separate solids and STOP exception')
            distance = float(np.linalg.norm(delta-move))
            require(entry['nominal_tcp_to_P_m'] == distance, 'all point scores')
            if excluded:
                blocked.append(token)
            elif token in MOVE:
                scored.append((distance,token))
            diagnostics[token] = {'contained_point_count':len(union),'excluded':excluded,'nominal_distance_mm':distance*1000,'nominal_reduction_mm':float((np.linalg.norm(delta)-distance)*1000),'support_indices':sorted(union)}
        expected_candidates = [c for c in view['candidates'] if c['token'] not in blocked]
        eligible = selection['eligible_canonical']
        require(eligible['candidates'] == expected_candidates and eligible['state'] == view['state'] and eligible['history'] == view['history'] and eligible['diagnostic_only'] is False, 'eligible exact original-order subset without state/history changes')
        require(eligible['effects']['candidate_set_id'] == canonical({'candidates':expected_candidates}) and eligible['effects']['effects'] == {c['token']:view['effects']['effects'][c['token']] for c in expected_candidates}, 'eligible effects preserve original nominal scores')
        selected = min(scored)[1] if scored and min(scored)[0] < np.linalg.norm(delta) else 'STOP'
        unguarded_scores = [(float(np.linalg.norm(delta-np.asarray(v)*.01)),token) for token,v in MOVE.items()]
        unguarded = min(unguarded_scores)[1] if min(unguarded_scores)[0] < np.linalg.norm(delta) else 'STOP'
        require(decision['selected'] == selected and selection['unguarded_rule_token_at_same_state'] == unguarded, 'independent filtered/original rule and tuple tie-break')
        if first is None and selected != unguarded:
            first = {'step':step,'unguarded_token':unguarded,'guarded_token':selected}
        require(selection['first_policy_divergence'] == first, 'actual first divergence latch')
        report.append({'step':step,'selected':selected,'unguarded':unguarded,'excluded':blocked,'candidate_diagnostics':diagnostics})
    return report


def audit_condition(sources, pair, condition, preflight):
    run, replay_path = pair / condition, pair / (condition + '-replay') / 'result.json'
    journal = run / 'episodes.jsonl'
    rows, by_kind, previous = [], defaultdict(list), None
    for index, line in enumerate(journal.read_bytes().splitlines(keepends=True)):
        require(line.endswith(b'\n'), 'complete journal line')
        row = json.loads(line)
        require(row['seq'] == index and row['previous_record_id'] == previous, 'journal order/link')
        require(row['record_id'] == canonical({k: v for k, v in row.items() if k != 'record_id'}), 'record content identity')
        previous = row['record_id']
        rows.append(row)
        by_kind[row['kind']].append(row)
    def data(kind):
        return [row['data'] for row in by_kind[kind]]
    def one(kind):
        require(len(by_kind[kind]) == 1, 'one ' + kind)
        return data(kind)[0]
    require(rows[-1]['kind'] == 'termination' and not by_kind['failure'], 'normal sealed termination')
    manifest, config = read(run / 'manifest.json'), read(run / 'resolved_config.yaml')
    require(one('run_start') == {'manifest': manifest, 'resolved_config': config}, 'manifest/config journal identity')
    require(all(row['config_hash'] == canonical(config) for row in rows), 'common frozen config')
    require(manifest['code'] == preflight['code'] and manifest['code']['dirty_status'] == '', 'reviewed clean freeze')
    require(sha(run / 'protocol.md') == manifest['protocol_sha256'] == preflight['protocol_sha256'], 'protocol seal')
    require(sha(run / 'review.txt') == manifest['review_sha256'], 'prospective receipt seal')
    require(config == {'condition': condition + '_native_POINT_original_full_BOX_endpoint_veto', 'seed': 1, 'init_state_id': 0, 'max_actions': 40, 'wall_limit_s': 900}, 'registered condition')
    require(manifest['new_model_calls'] == 0 and manifest['source_state_restored'] is False and manifest['archived_controls_used'] is False, 'no new model or restored prefix')
    for name, digest in manifest['source_sha256'].items():
        require(sha(sources / name) == digest, 'pinned source artifact')
    for name in ('code', 'source_sha256', 'unchanged_source_sha256', 'protocol_sha256', 'versions', 'stepping_sources', 'jev', 'environment', 'endpoint_guard', 'common', 'anchors', 'baseline_protocol_sha256'):
        require(manifest[name] == preflight[name], 'actual clean preflight identity')
    require(manifest['condition'] == condition and manifest['point'] == preflight['anchors'][condition]
            and manifest['goal_anchor'] == manifest['point']['provenance']
            and manifest['support_guard_identity'] == manifest['common'], 'POINT/support role and condition binding')
    for name, digest in manifest['common']['point_source_sha256'].items():
        require(sha(sources / 'task2-point-region-control-run-01' / name) == digest, 'fixed POINT source')
    gate = one('initial_frame_gate')
    captures = data('vision_capture')
    require(all(gate['array_bytes_exact'][k] for k in FRAME_KEYS), 'recorded initial gate')
    require(gate['cached_point'] == manifest['point'] and gate['new_model_calls'] == 0, 'cached perception declaration')
    point = np.asarray(read(sources / 'task2-point-region-control-run-01' / condition / 'sensor-result.json')['point']['position_world_m'])
    require(gate['cached_point']['position_world_m'] == point.tolist(), 'unchanged point source')
    for capture in captures:
        require(sha(run / capture['artifact']) == capture['artifact_sha256'], 'capture hash')
    with np.load(run / captures[0]['artifact'], allow_pickle=False) as fresh, np.load(sources / 'interaction-observability-paired-01/close/0000.npz', allow_pickle=False) as original:
        for key in FRAME_KEYS:
            require(fresh[key].dtype == original[key].dtype and fresh[key].shape == original[key].shape and fresh[key].tobytes() == original[key].tobytes(), 'independent initial array-byte gate')
    groups = {k: set(v) for k, v in gate['groups_evaluator_only'].items()}
    require(groups['pads'] == {78, 81} and groups['gripper'] <= groups['robot'] and not groups['robot'] & groups['bottle'], 'geometry group separation')
    baseline = strong(gate['initial_contact_snapshot_evaluator_only'], groups['robot'])
    require(baseline == set() and gate['initial_above_threshold_robot_pairs'] == [], 'empty strong robot baseline')
    require(not any(groups['robot'].intersection(c['geom_ids']) for c in gate['initial_contact_snapshot_evaluator_only']['contacts']), 'empty raw robot initial baseline')
    decisions, actions, endpoints = data('decision'), data('action_completed'), data('endpoint')
    starts, finishes = data('control_started'), data('control_completed')
    native_rows = [row for row in rows if row['kind'] in ('native_before', 'native_after')]
    termination = one('termination')
    stopped_by_rule = termination['reason'] in ('rule_no_strict_nominal_improvement', 'endpoint_veto_zero_remaining_pool')
    require(0 <= len(actions) <= 40 and len(actions) == len(endpoints) and len(captures) == len(actions) + 1
            and len(decisions) == len(actions) + int(stopped_by_rule), 'all movements and optional terminal decision')
    require(len(starts) == len(finishes) == 8 * len(actions) and len(native_rows) == 400 * len(actions), 'control/native counts')
    require(len(data('action_started')) == len(actions) and all(row['token'] in MOVE for row in data('action_started')), 'no STOP primitive')
    guard_report = audit_guard(decisions, starts, endpoints, gate, manifest, sources)
    source_time = gate['fresh_capture_sim_time_s']
    known = {'task.instruction', 'task.target_identity', 'robot.tcp_position_m', 'robot.gripper_width_m', 'robot.gripper_command',
             'target.position_m', 'target.position_definition', 'quality.geometry_valid', 'quality.geometry_age_s', 'quality.semantic_age_s',
             'relations.tcp_target_delta_m', 'relations.distance_m', 'relations.xy_error_m', 'relations.height_error_m'}
    trajectory, previous_end, previous_observation = [], None, None
    max_residual, max_rotation = 0., 0.
    for step, (choice, action, endpoint) in enumerate(zip(decisions, actions, endpoints)):
        require(choice['step'] == action['step'] == endpoint['step'] == step, 'contiguous action sequence')
        view, result = choice['canonical'], action['result']
        fields = view['state']['fields']
        require(all(not f['privileged'] for f in fields.values()), 'no privileged selector fields')
        require({k for k, f in fields.items() if f['value'] is not None} == known, 'only registered known selector fields')
        require(fields['target.position_m']['value'] == point.tolist() and fields['target.position_definition']['value'] == gate['cached_point']['definition'], 'point never refreshed or offset')
        require(fields['robot.gripper_command']['value'] == 'OPEN', 'open selector grip')
        tcp = np.asarray(fields['robot.tcp_position_m']['value'])
        delta = point - tcp
        require(fields['relations.tcp_target_delta_m']['value'] == delta.tolist(), 'target delta arithmetic')
        require(fields['relations.distance_m']['value'] == float(np.linalg.norm(delta)) == choice['live_tcp_to_fixed_proxy_m'], 'decision distance arithmetic')
        require(fields['relations.xy_error_m']['value'] == float(np.linalg.norm(delta[:2])) and fields['relations.height_error_m']['value'] == float(delta[2]), 'relation arithmetic')
        meta = view['state']['meta']
        require(meta['stationarity_assumption_verified'] is None and meta['current_visibility_verified'] is None and meta['new_model_calls'] == 0, 'unknown stationarity/visibility')
        require(meta['target_refreshed'] is False and meta['robot_observation_exact_sample_time_s'] is None, 'explicit age and own timing limit')
        require(fields['quality.geometry_age_s']['value'] == fields['quality.semantic_age_s']['value'] == meta['asof_sim_time'] - source_time, 'explicit point age')
        candidates = view['candidates']
        require([c['token'] for c in candidates] == [*MOVE, 'STOP'] and all(c['feasible'] and not c['reason_codes'] and c['risk'] == 0 and not c['metadata'] for c in candidates), 'unchanged seven admitted choices')
        scored = [(float(np.linalg.norm(delta - np.asarray(vector) * .01)), token) for token, vector in MOVE.items()]
        unguarded = min(scored)[1] if min(scored)[0] < np.linalg.norm(delta) else 'STOP'
        require(unguarded == choice['experiment_selection']['unguarded_rule_token_at_same_state'], 'original rule at same state')
        selected = guard_report[step]['selected']
        require(choice['selected'] == action['token'] == result['token'] == selected and selected in MOVE, 'independent rule and tie-break')
        effect = view['effects']['effects']
        require(effect['STOP'] == {'source': 'unknown', 'privileged': False, 'values': {}}, 'STOP unknown effect')
        for token, vector in MOVE.items():
            after = delta - np.asarray(vector) * .01
            require(effect[token]['source'] == 'geometry' and effect[token]['privileged'] is False, 'nominal effects only')
            require(effect[token]['state_id'] == canonical(view['state']), 'effect state identity')
            require(effect[token]['values'] == {'distance_change_m': float(np.linalg.norm(after) - np.linalg.norm(delta)),
                    'xy_error_change_m': float(np.linalg.norm(after[:2]) - np.linalg.norm(delta[:2]))}, 'effect arithmetic')
        history = [] if step == 0 else [{'action': actions[step-1]['token'], 'tcp_delta_m': actions[step-1]['result']['delta_m'],
            'elapsed_sim_s': actions[step-1]['result']['execution_after']['sim_time'] - actions[step-1]['result']['execution_before']['sim_time'],
            'gripper_command': 'OPEN', 'source': 'proprioception'}]
        require(view['history'] == history, 'sensor-only single-step history')
        require(result['before'] == tcp.tolist(), 'executor uses decision TCP')
        target = tcp.copy()
        axis = next(i for i, x in enumerate(MOVE[selected]) if x)
        target[axis] += MOVE[selected][axis] * .01
        for control in range(8):
            before, after = starts[step * 8 + control], finishes[step * 8 + control]
            require(before['step'] == after['step'] == step and before['control'] == after['control'] == control, 'control order')
            if previous_end is not None:
                require(before['state_before'] == previous_end and before['previous_returned_own_observations'] == previous_observation, 'continuous state and observation handoff')
            obs = before['previous_returned_own_observations']
            command = np.r_[np.clip((target - obs['robot0_eef_pos']) / .05, -1, 1), np.zeros(3), -1.].tolist()
            require(before['command'] == after['command'] == result['low_level_commands'][control] == command, 'raw command from recorded own observation')
            if control == 0:
                require(obs['robot0_eef_pos'] == tcp.tolist() and float(np.abs(obs['robot0_gripper_qpos']).sum()) == fields['robot.gripper_width_m']['value'], 'live own selector values')
            previous_end, previous_observation = after['state_after'], after['returned_own_observations']
        require(result['after'] == previous_observation['robot0_eef_pos'] == endpoint['proprioception']['tcp_pos_world_m'], 'final returned TCP')
        require(endpoint['own_observations'] == previous_observation and endpoint['proprioception']['gripper_command'] == 'OPEN', 'endpoint own observation retention')
        end_distance = float(np.linalg.norm(np.asarray(result['after']) - point))
        require(endpoint['live_tcp_to_fixed_proxy_m'] == end_distance, 'endpoint point distance')
        measured_delta = np.asarray(result['after']) - result['before']
        require(result['delta_m'] == measured_delta.tolist(), 'measured TCP delta')
        residual = float(np.linalg.norm(measured_delta - np.asarray(MOVE[selected]) * .01))
        a, b = result['execution_before'], result['execution_after']
        rotation = np.asarray(b['orientation']) @ np.asarray(a['orientation']).T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1, 1))))
        require(result['execution_contract_tolerances'] == {'hold_rotation_deg': 1., 'hold_translation_m': .0015, 'rotation_error_deg': 2., 'translation_error_m': .002}, 'unchanged validator limits')
        require(residual <= .002 and angle <= 1. and a['gripper_command'] == b['gripper_command'] == -1., 'independent translation/orientation/grip validation')
        require(not result['execution_contract_violation'] and result['execution_contract_reason'] == [], 'all validator outcomes')
        near(result['rotation_delta'], rotation, 'recorded rotation delta')
        near(result['rotation_angle_deg'], angle, 'recorded rotation angle')
        require(action['controls'] == result['environment_step_count'] == 8 and action['native_integrations'] == result['low_level_step_count'] == 200, 'full primitive counts')
        max_residual, max_rotation = max(max_residual, residual), max(max_rotation, angle)
        trajectory.append({'step': step, 'token': selected, 'before_distance_mm': float(np.linalg.norm(delta)) * 1000,
                           'after_distance_mm': end_distance * 1000, 'translation_residual_mm': residual * 1000, 'rotation_change_deg': angle})
    first, preceding = None, {'stage': 'initial', 'time_s': gate['initial_contact_snapshot_evaluator_only']['time_s']}
    raw_class_counts, raw_action_counts, pair_summary, action_pairs = Counter(), Counter(), {}, defaultdict(set)
    first_raw_robot_contact = None
    native_by_key = {}
    previous_native_state = None
    for position, row in enumerate(native_rows):
        kind, snapshot = row['kind'], row['data']
        step, local_stage = divmod(position, 400)
        integration, stage = divmod(local_stage, 2)
        require(kind == ('native_before', 'native_after')[stage] and snapshot['step'] == step and snapshot['index'] == integration and snapshot['control'] == integration // 25, 'native stage order/count')
        state = [snapshot['time_s'], *snapshot['qpos'], *snapshot['qvel']]
        if stage == 0:
            if previous_native_state is not None:
                require(state == previous_native_state, 'native state handoff before next integration')
            if integration % 25 == 0:
                require(state == starts[step * 8 + integration // 25]['state_before'], 'native state matches control before')
        else:
            near(snapshot['time_s'] - native_rows[position-1]['data']['time_s'], .002, 'native two-millisecond integration', 2e-15)
            if integration % 25 == 24:
                require(state == finishes[step * 8 + integration // 25]['state_after'], 'native state matches control after')
            previous_native_state = state
        current = {k: snapshot[k] for k in ('step', 'control', 'index', 'time_s')}
        current.update(stage=kind, raw_record_id=row['record_id'])
        new = strong(snapshot, groups['robot']) - baseline
        if new and first is None:
            first = {'previous_observed_sample': preceding, 'first_observed_sample': current,
                     'new_pairs': [{'geom_ids': list(p), 'class': contact_class(p, groups)} for p in sorted(new)],
                     'stop_granularity': 'after already-started atomic primitive',
                     'cache_semantics': 'native derived buffers; timestamps need not identify contact solve time'}
        action_pairs[step].update(new)
        for contact in snapshot['contacts']:
            require(contact['normal_force_N'] == contact['force_contact_frame'][0], 'normal force component')
            pair = tuple(sorted(contact['geom_ids']))
            if not any(g in groups['robot'] for g in pair):
                continue
            label = contact_class(pair, groups)
            raw_class_counts[(label, kind)] += 1
            raw_action_counts[(step, kind)] += 1
            if first_raw_robot_contact is None:
                first_raw_robot_contact = {**current, 'contact': contact}
            expected_invalid = label in ('self', 'arm/scene', 'gripper/other_scene') and contact['normal_force_N'] > .05
            require(contact['unexpected_robot_contact'] == expected_invalid, 'raw invalid-contact classification')
            if contact['normal_force_N'] > .05:
                key = str(pair)
                if key not in pair_summary:
                    names = dict(zip(contact['geom_ids'], contact['geom_names']))
                    pair_summary[key] = {'geom_ids': list(pair), 'geom_names': [names[g] for g in pair], 'class': label,
                                         'rows_by_stage': {'native_before': 0, 'native_after': 0}, 'maximum_normal_force_N': 0.,
                                         'unique_stage_keys': set()}
                pair_summary[key]['rows_by_stage'][kind] += 1
                pair_summary[key]['maximum_normal_force_N'] = max(pair_summary[key]['maximum_normal_force_N'], contact['normal_force_N'])
                pair_summary[key]['unique_stage_keys'].add((kind, step, snapshot['control'], integration))
        native_by_key[(kind, step, snapshot['control'], integration)] = snapshot
        preceding = current
    require(data('first_new_robot_contact') == ([] if first is None else [first]), 'exact first strict-contact latch')
    for step, action in enumerate(actions):
        expected_pairs = [{'geom_ids': list(p), 'class': contact_class(p, groups)} for p in sorted(action_pairs[step])]
        require(action['new_pairs_through_action_evaluator_only'] == expected_pairs and action['new_contact_observed'] == bool(expected_pairs), 'all final-action pair classes retained')
    termination = one('termination')
    require(termination['reason'] in ('rule_no_strict_nominal_improvement', 'endpoint_veto_zero_remaining_pool', 'new_robot_contact', 'action_budget'), 'registered normal termination')
    require(termination['first_contact_evaluator_only'] == first and termination['last_step'] == len(decisions) - 1, 'terminal first-contact and decision identity')
    require(termination['attempted_actions'] == termination['completed_actions'] == len(actions)
            and not termination['grasp_attempted'] and not termination['task_success_claim'] and termination['new_model_calls'] == 0, 'bounded no-grasp record')
    if stopped_by_rule:
        require(decisions[-1]['selected'] == 'STOP' and first is None, 'STOP without contact boundary')
        require(by_kind['vision_capture'][-1]['seq'] < by_kind['decision'][-1]['seq'] < by_kind['termination'][0]['seq'], 'terminal STOP after last capture with no hold')
    elif termination['reason'] == 'new_robot_contact':
        require(first is not None and first['first_observed_sample']['step'] == len(actions) - 1, 'finish already-started primitive then stop')
    else:
        require(len(actions) == 40 and first is None, 'bounded action exhaustion')
    replay = read(replay_path)
    require(replay['status'] == 'passed' and replay['source_journal_sha256'] == sha(journal) and replay['code'] == manifest['code'] and not replay['policy_or_model_rerun'], 'replay identity')
    require(replay['exact_controls'] == len(replay['control_states']) == len(starts) and replay['exact_native_snapshots'] == len(replay['native_states']) == len(native_rows) and replay['exact_captures'] == len(replay['frame_checks']) == len(captures), 'replay coverage')
    for index, replayed in enumerate(replay['control_states']):
        require(replayed == {'step': starts[index]['step'], 'control': starts[index]['control'], 'state_before': starts[index]['state_before'], 'state_after': finishes[index]['state_after'], 'exact': True}, 'stored replay control states')
    for replayed in replay['native_states']:
        key = (replayed['stage'], replayed['step'], replayed['control'], replayed['index'])
        original = native_by_key[key]
        require(replayed['entire_snapshot_exact'] and all(replayed[k] == original[k] for k in ('time_s', 'qpos', 'qvel', 'integration_fingerprint')), 'stored replay native state/fingerprint')
    for original, replayed in zip(captures, replay['frame_checks']):
        require(replayed['capture_seq'] == original['capture_seq'] and replayed['array_bytes_exact'] == {k: True for k in FRAME_KEYS}, 'recorded replay array-byte gates')
    for summary in pair_summary.values():
        keys = summary.pop('unique_stage_keys')
        summary['samples_by_stage'] = {kind: sum(k[0] == kind for k in keys) for kind in ('native_before', 'native_after')}
        summary['samples_by_control'] = {str(control): {kind: sum(k[0] == kind and k[2] == control for k in keys)
                                        for kind in ('native_before', 'native_after')} for control in range(8)}
    return {'status': 'pass', 'condition': condition, 'freeze': manifest['code']['commit'], 'journal_sha256': sha(journal), 'journal_records': len(rows),
            'point_world_m': point.tolist(), 'goal_anchor': manifest['goal_anchor'],
            'initial_own_observations': gate['initial_own_observations'],
            'final_own_observations': endpoints[-1]['own_observations'] if endpoints else gate['initial_own_observations'],
            'all_seven_candidate_point_proxy_memberships_checked': len(decisions) * 7 * 1340 * 5,
            'replay_sha256': sha(replay_path), 'actions': len(actions), 'controls': len(starts), 'native_integrations': len(native_rows) // 2,
            'native_stage_samples': len(native_rows), 'captures': len(captures), 'exact_initial_array_gate': True,
            'initial_tcp_to_proxy_mm': decisions[0]['live_tcp_to_fixed_proxy_m'] * 1000,
            'final_tcp_to_proxy_mm': (trajectory[-1]['after_distance_mm'] if trajectory else decisions[0]['live_tcp_to_fixed_proxy_m'] * 1000),
            'max_translation_residual_mm': max_residual * 1000, 'max_rotation_change_deg': max_rotation,
            'first_contact': first, 'strong_robot_pairs': list(pair_summary.values()), 'trajectory': trajectory,
            'guard_decisions': guard_report, 'termination': termination,
            'official_executor_success_flags': [action['result']['success'] for action in actions],
            'first_raw_robot_contact': first_raw_robot_contact,
            'raw_robot_contact_rows_by_action': {str(step): {kind: raw_action_counts[(step, kind)] for kind in ('native_before', 'native_after')}
                for step in range(len(actions)) if any(raw_action_counts[(step, kind)] for kind in ('native_before', 'native_after'))},
            'final_native_after_raw_robot_contacts': [c for c in (native_rows[-1]['data']['contacts'] if native_rows else gate['initial_contact_snapshot_evaluator_only']['contacts']) if any(g in groups['robot'] for g in c['geom_ids'])],
            'raw_robot_contact_rows_by_class_and_stage': {label: {kind: raw_class_counts[(label, kind)] for kind in ('native_before', 'native_after')}
                for label in ('pad/bottle', 'other_gripper/bottle', 'gripper/other_scene', 'arm/scene', 'self')},
            'limits': ['stored arrays, journal and arithmetic only; reviewer performed no dynamics, rendering, FK, projection or inference',
                       'replay exports states/fingerprints and full-snapshot/image equality assertions; full replay contacts/images were compared by reviewed producer, not separately reexported',
                       'counts cover instrumented approach only; fresh reset and ten standard settling controls also occurred',
                       'first observed native contact is not continuous-time onset; native cached force/pose times remain unknown',
                       'point distance does not establish bottle center, clearance, jaw fit, grasp readiness or holding']}


def load_journal(path):
    rows, previous = [], None
    for index, line in enumerate(path.read_bytes().splitlines(keepends=True)):
        require(line.endswith(b'\n'), 'complete paired journal line')
        row = json.loads(line)
        require(row['seq'] == index and row['previous_record_id'] == previous
                and row['record_id'] == canonical({k: v for k, v in row.items() if k != 'record_id'}), 'paired journal chain/hash')
        require(not rows or rows[-1]['wall_time'] <= row['wall_time'], 'paired journal wall time order')
        rows.append(row)
        previous = row['record_id']
    return rows


def audit_pair(sources):
    pair = sources / 'task2-point-anchor-approach-run-01'
    preflight_path = sources / 'task2-point-anchor-approach-preflight-02.json'
    admission_path = sources / 'task2-point-anchor-approach-admission-01.json'
    require(sha(preflight_path) == 'dba534d9a685cdf027af6241b02b52618f32cd2f8dd6ada4f9fff3e80d8ed248', 'final no-world source preflight')
    require(sha(admission_path) == '753fd32754c67265956c845db0d689f7ca41e2ad1aa1155cb75ee6aecdb14fef', 'final admitted packet')
    preflight, admission = read(preflight_path), read(admission_path)
    require(preflight['code']['commit'] == 'fb7899bef22e6473aed30e7dd0051568bd7db7f7'
            and preflight['code']['dirty_status'] == '' and preflight['physical_execution_admitted'] is False
            and preflight['physics_calls'] == 0, 'clean source-only preparation')
    expected_admission = {'point_audit': 'c083504fe4574f01a472c4cf957a61ff016055ebc069b4fcb23f752d8bc467d1',
                          'geometry_seal': '2e849dd465a93c6f41a72a3bec31ba1ae5a63b2c3f39345db326daf19fe9c0e5',
                          'geometry_audit': 'bf1ce72a79fd50c796b68e3d41d6b73b474184a8c89501cc3b93d4af1861627c'}
    for key, digest in expected_admission.items():
        require(admission[key]['sha256'] == sha(Path(admission[key]['path'])) == digest, 'immutable admission evidence')
    geometry_audit = read(admission['geometry_audit']['path'])
    require(geometry_audit['status'] == 'PASS' and geometry_audit['conditions'][1]['condition'] == 'neck'
            and geometry_audit['conditions'][1]['exact_P_any_containment'] is False, 'named neck exact-center prerequisite')
    request, manifest, config = read(pair / 'request.json'), read(pair / 'manifest.json'), read(pair / 'resolved_config.yaml')
    require(config == request, 'paired request/config identity')
    require(request['condition_order'] == ['whole', 'neck'] and request['fresh_policy_episodes'] == 2
            and request['separate_verification_replays_per_normally_terminated_condition'] == 1
            and request['new_model_calls'] == request['retries'] == 0, 'registered stage budget/order')
    require(Path(request['admission_path']).resolve() == admission_path.resolve(), 'registered admission path')
    physical = request['physical_admission']
    require(physical == {'admission_sha256': sha(admission_path), 'artifacts': admission, 'status': 'pass',
        'neck_exact_P_observed_solid_containment': False, 'absence_is_physical_clearance': False,
        'conditions_retained': ['whole', 'neck'], 'support_guard_identity': preflight['common']}, 'physical gate record independent of policy')
    require(sha(pair / 'review.txt') == request['review_sha256'] and preflight['code']['commit'] in (pair / 'review.txt').read_text()
            and sha(admission_path) in (pair / 'review.txt').read_text() and 'PASS' in (pair / 'review.txt').read_text(), 'root prospective binding to freeze/admission')
    require(sha(pair / 'protocol.md') == preflight['protocol_sha256'], 'paired protocol identity')
    for key in ('code', 'source_sha256', 'unchanged_source_sha256', 'source_frame_shapes', 'protocol_sha256',
                'versions', 'stepping_sources', 'jev', 'environment', 'common', 'anchors', 'endpoint_guard', 'baseline_protocol_sha256'):
        require(manifest[key] == preflight[key], 'pair manifest/preflight ' + key)
    rows = load_journal(pair / 'episodes.jsonl')
    require(rows[0]['data'] == {'manifest': manifest, 'resolved_config': config}, 'paired initial manifest/config')
    require(all(row['config_hash'] == canonical(config) for row in rows), 'pair record configuration')
    stages = [(name, stage) for name in ('whole', 'neck') for stage in ('collect', 'replay')]
    require([row['kind'] for row in rows] == ['run_start', *[kind for _ in stages for kind in ('stage_intent', 'stage_complete')], 'termination'], 'exact four completed stages')
    for index, (condition, stage) in enumerate(stages):
        expected = {'condition': condition, 'stage': stage}
        require(rows[1 + index * 2]['data'] == rows[2 + index * 2]['data'] == expected, 'fixed registered stage order')
        require((pair / f'{condition}-{stage}.log').is_file(), 'stage output retained')
    require(rows[-1]['data'] == {'reason': 'both_fixed_conditions_and_replays_complete', 'fresh_policy_episodes': 2,
        'verification_replays': 2, 'new_model_calls': 0, 'grasp_attempted': False,
        'task_success_claim': False, 'winner_selected': False}, 'complete bounded pair')
    conditions = []
    logs = []
    for index, name in enumerate(('whole', 'neck')):
        child = load_journal(pair / name / 'episodes.jsonl')
        require(rows[1 + index * 4]['wall_time'] <= child[0]['wall_time'] <= child[-1]['wall_time']
                <= rows[2 + index * 4]['wall_time'], 'fresh collection enclosed by own stage')
        require(sha(pair / name / 'review.txt') == request['review_sha256'], 'same prospective receipt for each collection')
        conditions.append(audit_condition(sources, pair, name, preflight))
        grouped = defaultdict(list)
        for row in child:
            grouped[row['kind']].append(row['data'])
        logs.append(grouped)
    common_actions = 0
    initial_whole, initial_neck = [log['initial_frame_gate'][0] for log in logs]
    for key in ('initial_own_observations', 'initial_proprioception', 'groups_evaluator_only',
                'initial_contact_snapshot_evaluator_only', 'initial_above_threshold_robot_pairs', 'fresh_capture_sim_time_s'):
        require(initial_whole[key] == initial_neck[key], 'matched initial own/native/contact state ' + key)
    whole_actions = [row['token'] for row in logs[0]['action_completed']]
    neck_actions = [row['token'] for row in logs[1]['action_completed']]
    for whole, neck in zip(whole_actions, neck_actions):
        if whole != neck:
            break
        common_actions += 1
    for kind in ('control_started', 'control_completed', 'native_before', 'native_after', 'action_started', 'action_completed'):
        require([row for row in logs[0][kind] if row['step'] < common_actions]
                == [row for row in logs[1][kind] if row['step'] < common_actions], 'exact paired physical common prefix ' + kind)
    for step in range(common_actions):
        require({k: v for k, v in logs[0]['endpoint'][step].items() if k != 'live_tcp_to_fixed_proxy_m'}
                == {k: v for k, v in logs[1]['endpoint'][step].items() if k != 'live_tcp_to_fixed_proxy_m'}, 'same prefix returned own/endpoints')
    for index in range(common_actions + 1):
        captures = [log['vision_capture'][index] for log in logs]
        require(captures[0]['capture_seq'] == captures[1]['capture_seq']
                and captures[0]['capture_sim_time'] == captures[1]['capture_sim_time'], 'paired prefix capture boundary')
        with np.load(pair / 'whole' / captures[0]['artifact'], allow_pickle=False) as a, np.load(pair / 'neck' / captures[1]['artifact'], allow_pickle=False) as b:
            require(all(a[k].shape == b[k].shape and a[k].dtype == b[k].dtype and a[k].tobytes() == b[k].tobytes() for k in FRAME_KEYS), 'paired prefix full RGB-D bytes')
    whole_selected = [row['selected'] for row in logs[0]['decision']]
    neck_selected = [row['selected'] for row in logs[1]['decision']]
    first_divergence = next(({'step': i, 'whole': whole, 'neck': neck}
                            for i, (whole, neck) in enumerate(zip(whole_selected, neck_selected)) if whole != neck), None)
    if first_divergence is not None:
        selections = [log['decision'][first_divergence['step']]['experiment_selection'] for log in logs]
        require(selections[0]['own_packet'] == selections[1]['own_packet']
                and selections[0]['current_proxy_vertices_world_m'] == selections[1]['current_proxy_vertices_world_m'], 'same live own geometry at first anchor divergence')
        stripped = [{token: {k: v for k, v in row.items() if k != 'nominal_tcp_to_P_m'}
                     for token, row in selection['all_seven_candidates'].items()} for selection in selections]
        require(stripped[0] == stripped[1], 'same endpoint exclusions at first anchor divergence')
    return {'status': 'PASS', 'freeze': preflight['code']['commit'], 'raw_directory': str(pair),
        'pair_journal_sha256': sha(pair / 'episodes.jsonl'), 'request_sha256': sha(pair / 'request.json'),
        'preflight_sha256': sha(preflight_path), 'admission_sha256': sha(admission_path),
        'source_POINT_audit_sha256': expected_admission['point_audit'], 'geometry_audit_sha256': expected_admission['geometry_audit'],
        'final_integrity_delta_review': 'fb7899b explicitly binds geometry producer/source/count/order/results and combined tensors; checked before root prospective1c884d2',
        'conditions': conditions, 'action_sequences': {'whole': whole_actions, 'neck': neck_actions},
        'first_between_anchor_policy_divergence': first_divergence,
        'exact_common_physical_prefix_actions': common_actions,
        'exact_common_physical_prefix_captures': common_actions + 1,
        'limits': ['stored evidence audit only; no new policy, physics, rendering, model, FK or projection calls',
                   'two fixed sensor anchors on one fixture do not establish general accuracy, physical safety, grasp readiness, holding or task success',
                   'geometry prerequisite uses prior terminal orientation/jaws; each live episode uses its own returned state',
                   'replay exports full states/fingerprints and equality assertions; full replay contact/image comparisons were executed by the reviewed verifier, not separately reexported']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit_pair(args.sources)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({**result, 'conditions': [{k: v for k, v in row.items() if k not in ('trajectory', 'guard_decisions')} for row in result['conditions']]}, indent=2))
