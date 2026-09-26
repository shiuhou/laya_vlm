"""Independent sealed Task2 approach arithmetic audit; no scene or model calls."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np


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


def audit(sources):
    run, replay_path = sources / 'task2-box-point-boundary-run-01', sources / 'task2-box-point-boundary-replay-01/result.json'
    journal = run / 'episodes.jsonl'
    require(sha(journal) == 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771', 'sealed source journal identity')
    require(sha(replay_path) == '5c3a02fb731d3d8c120ec6f89327762b942d36ab62716a48552ebfc348faa5f9', 'sealed replay identity')
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
    require(manifest['code']['commit'] == '9de837c8a1348d8eac16bbe4616b40bcf0b0613f' and manifest['code']['dirty_status'] == '', 'reviewed clean freeze')
    require(sha(run / 'protocol.md') == manifest['protocol_sha256'] == 'c04c9b2cea516153ee03444d3d63f11fcd6cc633b647b6e256b2e3b86ae6bc47', 'protocol seal')
    require(sha(run / 'review.txt') == manifest['review_sha256'], 'prospective receipt seal')
    require(config == {'condition': 'cached_BOX_P_live_proprio_approach_only', 'seed': 1, 'init_state_id': 0, 'max_actions': 40, 'wall_limit_s': 900}, 'registered condition')
    require(manifest['new_model_calls'] == 0 and manifest['source_state_restored'] is False and manifest['archived_controls_used'] is False, 'no new model or restored prefix')
    for name, digest in manifest['source_sha256'].items():
        require(sha(sources / name) == digest, 'pinned source artifact')
    preflight = read(sources / 'task2-box-point-boundary-preflight-02.json')
    for name in ('code', 'source_sha256', 'unchanged_source_sha256', 'point', 'protocol_sha256', 'versions', 'stepping_sources', 'jev', 'environment'):
        require(manifest[name] == preflight[name], 'actual clean preflight identity')
    gate = one('initial_frame_gate')
    captures = data('vision_capture')
    require(all(gate['array_bytes_exact'][k] for k in FRAME_KEYS), 'recorded initial gate')
    require(gate['cached_point'] == manifest['point'] and gate['new_model_calls'] == 0, 'cached perception declaration')
    point = np.asarray(read(sources / 'task2-box-support-run-02/sensor-representation.json')['point_P']['position_world_m'])
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
    decisions, actions, endpoints = data('decision'), data('action_completed'), data('endpoint')
    starts, finishes = data('control_started'), data('control_completed')
    native_rows = [row for row in rows if row['kind'] in ('native_before', 'native_after')]
    require(len(decisions) == len(actions) == len(endpoints) == 25 and len(captures) == 26, 'fixed completed trajectory counts')
    require(len(starts) == len(finishes) == 200 and len(native_rows) == 10000, 'control/native counts')
    require(len(data('action_started')) == 25, 'no extra action intents')
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
        selected = min(scored)[1] if min(scored)[0] < np.linalg.norm(delta) else 'STOP'
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
        require(not result['success'] and not a['success'] and not b['success'], 'official success not reached')
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
    require(first == one('first_new_robot_contact'), 'independent first contact and preceding sample')
    for step, action in enumerate(actions):
        expected_pairs = [{'geom_ids': list(p), 'class': contact_class(p, groups)} for p in sorted(action_pairs[step])]
        require(action['new_pairs_through_action_evaluator_only'] == expected_pairs and action['new_contact_observed'] == bool(expected_pairs), 'all final-action pair classes retained')
    termination = one('termination')
    require(termination['reason'] == 'new_robot_contact' and termination['first_contact_evaluator_only'] == first and termination['last_step'] == first['first_observed_sample']['step'] == 24, 'stop after first-contact primitive')
    require(termination['attempted_actions'] == termination['completed_actions'] == 25 and not termination['grasp_attempted'] and not termination['task_success_claim'] and termination['new_model_calls'] == 0, 'bounded no-grasp terminal record')
    require(by_kind['first_new_robot_contact'][0]['seq'] < by_kind['action_completed'][-1]['seq'] < by_kind['vision_capture'][-1]['seq'] < by_kind['termination'][0]['seq'], 'complete primitive and final capture after contact')
    replay = read(replay_path)
    require(replay['status'] == 'passed' and replay['source_journal_sha256'] == sha(journal) and replay['code'] == manifest['code'] and not replay['policy_or_model_rerun'], 'replay identity')
    require(replay['exact_controls'] == len(replay['control_states']) == 200 and replay['exact_native_snapshots'] == len(replay['native_states']) == 10000 and replay['exact_captures'] == len(replay['frame_checks']) == 26, 'replay coverage')
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
    return {'status': 'pass', 'freeze': manifest['code']['commit'], 'journal_sha256': sha(journal), 'journal_records': len(rows),
            'replay_sha256': sha(replay_path), 'actions': len(actions), 'controls': len(starts), 'native_integrations': len(native_rows) // 2,
            'native_stage_samples': len(native_rows), 'captures': len(captures), 'exact_initial_array_gate': True,
            'initial_tcp_to_proxy_mm': trajectory[0]['before_distance_mm'], 'final_tcp_to_proxy_mm': trajectory[-1]['after_distance_mm'],
            'max_translation_residual_mm': max_residual * 1000, 'max_rotation_change_deg': max_rotation,
            'first_contact': first, 'strong_robot_pairs': list(pair_summary.values()), 'trajectory': trajectory,
            'first_raw_robot_contact': first_raw_robot_contact,
            'raw_robot_contact_rows_by_action': {str(step): {kind: raw_action_counts[(step, kind)] for kind in ('native_before', 'native_after')}
                for step in range(len(actions)) if any(raw_action_counts[(step, kind)] for kind in ('native_before', 'native_after'))},
            'final_native_after_raw_robot_contacts': [c for c in native_rows[-1]['data']['contacts'] if any(g in groups['robot'] for g in c['geom_ids'])],
            'raw_robot_contact_rows_by_class_and_stage': {label: {kind: raw_class_counts[(label, kind)] for kind in ('native_before', 'native_after')}
                for label in ('pad/bottle', 'other_gripper/bottle', 'gripper/other_scene', 'arm/scene', 'self')},
            'limits': ['stored arrays, journal and arithmetic only; reviewer performed no dynamics, rendering, FK, projection or inference',
                       'replay exports states/fingerprints and full-snapshot/image equality assertions; full replay contacts/images were compared by reviewed producer, not separately reexported',
                       'counts cover instrumented approach only; fresh reset and ten standard settling controls also occurred',
                       'first observed native contact is not continuous-time onset; native cached force/pose times remain unknown',
                       'point distance does not establish bottle center, clearance, jaw fit, grasp readiness or holding']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'trajectory'}, indent=2))
