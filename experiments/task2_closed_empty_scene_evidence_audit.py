"""Stored-only scene-event, prefix, sensor, contact and exact replay audit."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

import task2_point_anchor_grasp_transfer_evidence_audit as prior

read, sha, require, one = prior.read, prior.sha, prior.require, prior.one
FREEZE = 'cf00088824f4b74bd121cb6e8b3c89cc702fe9ab'
PREFLIGHT = 'ed641f604e596eca418efa1b036a749c911af98183687d9b1dc3f0f0392dae8b'
REVIEW = '9bd4f40b6ed643ca8b5141bb81ee302aa0f05ba8a57db635e654eea8830782e7'
ORDER = ('neck-present', 'neck-away')
SCHEDULE = (('close_or_hold', 'GRASP'), ('additional_close', 'GRASP'), ('lift', 'MV_UP'))
EVENT_ORDER = ('scene_intervention_intent', 'scene_state', 'scene_boundary', 'scene_state',
               'scene_state', 'scene_state', 'scene_geometry_admission', 'scene_boundary',
               'scene_intervention_completed')


def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        return [v for key in a for v in differences(a[key], b[key], path + '/' + key)]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [v for i, (x, y) in enumerate(zip(a, b)) for v in differences(x, y, path + '/' + str(i))]
    return [] if a == b else [{'path': path, 'before': a, 'after': b}]


def changes_by_path(changes):
    require(len({c['path'] for c in changes}) == len(changes), 'unique changed-leaf paths')
    return sorted(changes, key=lambda c: c['path'])


def flat_state(snapshot):
    return [snapshot['sim_time_s'], *snapshot['state']['qpos'], *snapshot['state']['qvel']]


def event_audit(run, rows, static):
    by = prior.grouped(rows)
    events = [r for r in rows if r['kind'].startswith('scene_')]
    require(tuple(r['kind'] for r in events) == EVENT_ORDER, 'one complete known ordered event')
    require(by['approach_prefix_verified'][0]['seq'] + 1 == events[0]['seq']
            and events[-1]['seq'] + 1 == next(r['seq'] for r in by['action_started'] if r['data']['step'] == 29),
            'event exactly between verified prefix and first suffix action')
    snapshots = [r['data'] for r in events if r['kind'] == 'scene_state']
    require([s['stage'] for s in snapshots] == ['before', 'after_write', 'after_forward', 'after_refresh'], 'four event stages')
    before, written, forwarded, refreshed = [s['audit'] for s in snapshots]
    before_control = next(r['data'] for r in by['control_completed'] if (r['data']['step'], r['data']['control']) == (28, 7))
    require(flat_state(before) == before_control['state_after']
            and before['own_observations'] == before_control['returned_own_observations'], 'untouched prefix/event state and own boundary')
    require(before['state']['qpos'] == static['qpos'], 'actual pre-event qpos equals static source')
    delta = .35 if run.name == 'neck-away' else 0.
    expected = deepcopy(before)
    expected['state']['qpos'][16] += delta
    expected['integration_fingerprint'] = written['integration_fingerprint']
    require(expected == written, 'explicit write changed only bottle X')
    invariants = ('sim_time_s', 'controller', 'robot_recent', 'gripper_current_action',
                  'retained_gripper_command', 'environment_clock', 'numpy_rng', 'python_rng')
    for first, last, record in zip((before, written, forwarded), (written, forwarded, refreshed), snapshots[1:]):
        require(changes_by_path(record['changes']) == changes_by_path(differences(first, last)),
                'complete recorded changed-leaf inventory')
    for first, last in ((written, forwarded), (forwarded, refreshed)):
        require(all(first[k] == last[k] for k in invariants), 'synchronization clock/controller/robot/RNG invariants')
        require(all(first['state'][k] == last['state'][k] for k in first['state'] if k != 'qacc_warmstart'), 'synchronization primary state invariants')
    intent, completed = one(events, 'scene_intervention_intent'), one(events, 'scene_intervention_completed')
    require(sha(Path(static['static_model_journal'])) == static['static_model_journal_sha256'], 'closed compiled model source')
    model_rows = prior.load_journal(Path(static['static_model_journal']))
    model = model_rows[static['static_model_identity_record_seq']]['data']['current_model_identity']
    require(intent == {'version': 'task2-neck-matched-closed-empty-scene-v1', 'condition': run.name,
        'privileged_scene_intervention': True, 'before_action_step': 29, 'joint': 'wine_bottle_1_joint0',
        'qpos_address': 16, 'delta_world_m': [delta, 0., 0.], 'compiled_model_array_sha256': model['model_array_sha256'],
        'forward_calls': 1, 'forced_observation_refresh_calls': 1, 'physics_controls': 0, 'archived_state_restored': False}, 'actual event intent/model identity')
    require(changes_by_path(completed['own_changes']) == changes_by_path(
            differences(before['own_observations'], refreshed['own_observations'])), 'event own changed-leaf inventory')
    require(completed == {'condition': run.name, 'before_action_step': 29, 'privileged_scene_intervention': True,
        'sim_time_before_s': before['sim_time_s'], 'sim_time_after_s': refreshed['sim_time_s'], 'physics_controls': 0,
        'forward_calls': 1, 'forced_observation_refresh_calls': 1,
        'own_changes': completed['own_changes'],
        'explicit_write_changed_qpos_indices': [16] if delta else []}, 'event completion and no time advance')
    immediate_contacts = []
    for stage, snapshot in zip(('before', 'after_write', 'after_forward', 'after_refresh'),
                               (before, written, forwarded, refreshed)):
        contact = snapshot['contact_solver']
        require(contact['ncon'] == len(contact['contacts']) and contact['nefc'] >= 0, 'immediate contact/constraint counts')
        require(set(contact['named_solver_buffers']) == {'qfrc_constraint', 'efc_force', 'efc_state'}, 'declared solver buffer scope')
        for name, buffer in contact['named_solver_buffers'].items():
            require(buffer['shape'] == [len(snapshot['state']['qvel']) if name == 'qfrc_constraint' else contact['nefc']]
                    and len(buffer['sha256']) == 64 and all(c in '0123456789abcdef' for c in buffer['sha256']),
                    'stored solver buffer shape and digest schema')
        raw_robot_bottle = []
        for i, c in enumerate(contact['contacts']):
            require(c['index'] == i and len(c['force_contact_frame']) == 6 and np.isfinite(c['force_contact_frame']).all()
                    and len(c['geom_ids']) == len(c['geom_names']) == 2 and len(c['position_m']) == 3
                    and len(c['frame']) == 9 and c['dimension'] in (1, 3, 4, 6)
                    and -1 <= c['efc_address'] < contact['nefc']
                    and np.isfinite([c['distance_m'], *c['position_m'], *c['frame']]).all(), 'stored immediate contact rows')
            names = c['geom_names']
            if (any(n.startswith(('robot0_', 'gripper0_', 'mount0_')) for n in names)
                    and any(n.startswith('wine_bottle_1_') for n in names)):
                raw_robot_bottle.append(c)
        if delta and stage in ('after_forward', 'after_refresh'):
            require(not raw_robot_bottle, 'away immediate synchronized event has no raw robot/bottle contact')
        immediate_contacts.append({'stage': stage, 'ncon': contact['ncon'], 'nefc': contact['nefc'],
            'raw_robot_bottle': raw_robot_bottle, 'named_solver_buffers': contact['named_solver_buffers']})
    geometry = one(events, 'scene_geometry_admission')
    bounds, bottle, table = geometry['bounds'], geometry['bounds']['bottle'], geometry['bounds']['table']
    require(geometry['geometry_count'] == {'robot': 16, 'bowl': 40, 'bottle': 21, 'cabinet': 36, 'rack': 9, 'table': 1, 'floor': 1}, 'actual finite/floor collision inventory')
    require(geometry['evaluator_only'] and not geometry['visibility_verified'] and not geometry['dynamic_stability_or_swept_clearance_verified'], 'setup interpretation retained')
    require(np.all(np.array(bottle['low'][:2]) > table['low'][:2]) and np.all(np.array(bottle['high'][:2]) < table['high'][:2]), 'actual supported table footprint')
    require(geometry['floor']['rotation'] == np.eye(3).flatten().tolist() and bottle['low'][2] > geometry['floor']['position'][2], 'actual floor separation')
    gaps = {key: bottle['low'][0] - bounds[key]['high'][0] for key in ('robot', 'bowl', 'cabinet', 'rack')}
    require(gaps == geometry['X_separation_lower_bounds_m'] and (not delta or all(v > 0 for v in gaps.values())), 'actual declared away static separation')
    scenes = [r['data'] for r in events if r['kind'] == 'scene_boundary']
    for index, (stage, c, state) in enumerate(zip(('before', 'after'), scenes, (before, refreshed)), 1):
        prior.check_image(run, c)
        require((c['condition'], c['anchor'], c['arm'], c['phase'], c['scene_boundary'], c['after_step'], c['control'], c['source_capture_stream'], c['source_capture_seq']) ==
                (run.name, 'neck', 'close', 'scene_' + stage, stage, 29, None, 'scene', index), 'separate scene stream boundaries')
        require(c['own_observations'] == state['own_observations'] and set(c['own_observations']) == set(prior.OBS_KEYS)
                and c['own_tcp_world_m'] == state['own_observations']['robot0_eef_pos'], 'scene actual own-packet allowlist')
        require(c['capture_sim_time'] == c['capture_read_sim_time_s'] == c['tcp_read_sim_time_s'] == state['sim_time_s']
                and c['cached_geometry_sample_time_s'] is None and c['exact_observation_sample_time_s'] is None, 'scene read/unknown sample times')
        require(c['own_source'] == {'journal': 'episodes.jsonl', 'kind': 'scene_boundary', 'boundary': stage, 'step': 29}
                and c['tcp_source_field'] == 'scene_boundary.own_observations.robot0_eef_pos', 'scene own provenance')
    last_primary = next(r['data'] for r in by['vision_capture'] if r['data']['capture_seq'] == 30)
    prior.arrays_equal(run / last_primary['artifact'], run / scenes[0]['artifact'])
    result = {'event_records': len(events), 'all_recorded_change_inventories_exact': True,
        'explicit_changed_qpos_indices': [16] if delta else [], 'event_sim_time_s': before['sim_time_s'],
        'all_primary_controller_clock_RNG_invariants_preserved': True,
        'refresh_changes_only_observation_state': all(forwarded[k] == refreshed[k] for k in ('state', 'caches', 'contact_solver', 'integration_fingerprint')),
        'forward_changed_paths': [x['path'] for x in snapshots[2]['changes']],
        'refresh_changed_paths': [x['path'] for x in snapshots[3]['changes']],
        'own_changes': completed['own_changes'],
        'immediate_contact_solver_evidence': immediate_contacts,
        'observation_time_limit': 'Read times are recorded; exact sample times remain unknown. Forced refresh can change returned own packets without advancing physics time. The sham suffix is not assumed byte-equivalent to an older suffix.',
        'actual_geometry_admission': geometry, 'event_complete_record_id': events[-1]['record_id']}
    return result, scenes, (flat_state(refreshed), refreshed['own_observations'])


def audit_cell(matrix, condition, preflight, static, approach_audit, *, replay_complete):
    run = matrix / condition
    rows = prior.load_journal(run / 'episodes.jsonl')
    by = prior.grouped(rows)
    manifest, config = read(run / 'manifest.json'), read(run / 'resolved_config.yaml')
    require(one(rows, 'run_start') == {'manifest': manifest, 'resolved_config': config}, 'cell journal/manifest binding')
    require(all(r['config_hash'] == prior.canonical(config) for r in rows), 'cell config hash')
    require(config == {'condition': condition, 'seed': 1, 'init_state_id': 0, 'max_actions': 40, 'wall_limit_s': 900}, 'cell fixed configuration')
    require(manifest['code'] == preflight['code'] and manifest['condition'] == condition, 'actual exact frozen cell identity')
    for key in ('source_sha256', 'unchanged_source_sha256', 'source_frame_shapes', 'protocol_sha256',
                'versions', 'stepping_sources', 'jev', 'environment', 'common', 'anchors',
                'endpoint_guard', 'baseline_protocol_sha256', 'point', 'goal_anchor', 'support_guard_identity'):
        require(manifest[key] == preflight[key], 'cell/preflight identity: ' + key)
    expected_transfer = deepcopy(preflight['transfer'])
    expected_transfer['condition'] = condition
    expected_transfer['scene_intervention']['delta_world_m'] = [.35 if condition == 'neck-away' else 0., 0., 0.]
    require(manifest['transfer'] == expected_transfer, 'fixed scene and suffix configuration')
    require(sha(run / 'review.txt') == REVIEW and sha(run / 'protocol.md') == preflight['protocol_sha256'], 'cell prospective review/protocol')
    require(manifest['new_model_calls'] == 0 and manifest['source_state_restored'] is False and manifest['archived_controls_used'] is False, 'fresh collection scope')
    failures = [r for r in rows if 'failure' in r['kind']]
    require(not failures, 'completed source has no event or suffix failure')
    approach_source = matrix.parent / 'task2-point-anchor-approach-run-01'
    approach_end, suffix, prefix = prior.exact_prefix(run, rows, approach_source, 'neck', approach_audit)
    event, scenes, handoff = event_audit(run, rows, static)
    groups = {key: set(value) for key, value in one(rows, 'initial_frame_gate')['groups_evaluator_only'].items()}
    mechanical, native = prior.suffix_audit(rows, suffix, groups, approach_end, 'close', schedule=SCHEDULE, scene_handoff=handoff)
    require(mechanical['attempted_actions'] == mechanical['completed_actions'] == 3
            and mechanical['controls_started'] == mechanical['controls_completed'] == 24 and mechanical['native_snapshots'] == 1200, 'all fixed suffix controls/native stages')
    sensor, endpoints = prior.sensor_and_labels(run, rows, groups, auxiliary_count=24, scene_rows=scenes,
                                               actual_arm='close', extra_sensor_files=('own-controls.json',))
    image_files = {str(p.relative_to(run)) for sub in ('frames', 'scene', 'auxiliary') for p in (run / sub).glob('*.npz')}
    expected_images = {r['data']['artifact'] for r in rows if r['kind'] in ('vision_capture', 'scene_boundary', 'auxiliary_capture')}
    require(image_files == expected_images and len(image_files) == 59
            and sensor['primary_captures'] == 33 and sensor['sensor_chronology_captures'] == 56,
            'all 59 saved image archives and 56 merged captures accounted')
    sensor.update(scene_captures=2, total_saved_image_archives=59,
                  selected_suffix_merged_capture_ids=list(range(31, 56)))
    own_export = read(run / 'own-controls.json')
    controls = [r for r in by['control_completed'] if r['data']['step'] >= 29]
    require(len(own_export) == len(controls) == 24, 'all suffix own-control rows')
    for exported, record in zip(own_export, controls):
        d = record['data']
        expected = {'condition': condition, 'phase': SCHEDULE[d['step'] - 29][0], 'step': d['step'], 'control': d['control'],
            'command': d['command'], 'read_sim_time_s': d['state_after'][0], 'exact_observation_sample_time_s': None,
            'own_observations': d['returned_own_observations'], 'source': {'journal': 'episodes.jsonl', 'seq': record['seq'],
                'record_id': record['record_id'], 'own_field': 'data.returned_own_observations', 'clock_field': 'data.state_after[0]'}}
        require(exported == expected and set(exported['own_observations']) == set(prior.OBS_KEYS), 'exact sanitized own export and linkage')
    qualifications = [r['data'] for r in by['away_contact_qualification']]
    if condition == 'neck-away':
        require(len(qualifications) == 3 and all(not x['raw_robot_bottle'] for x in native + endpoints), 'away has no raw robot/bottle contact in any native or endpoint row')
        for offset, q in enumerate(qualifications):
            require(q == {'condition': condition, 'step': 29 + offset, 'primitive_offset': offset, 'native_snapshots': 400,
                'endpoint_snapshots': 8, 'raw_robot_bottle_contact_absent': True, 'violations': [],
                'zero_force_contacts_count': True, 'settled_empty_not_inferred': True, 'evaluator_only': True}, 'all three independent away qualification receipts')
    else:
        require(not qualifications, 'present not filtered by empty-contact gate')
    termination = one(rows, 'termination')
    require(termination['reason'] == 'fixed_approach_and_scripted_suffix_complete'
            and termination['approach_termination'] == approach_end
            and termination['attempted_actions'] == termination['completed_actions'] == 32
            and termination['scripted_attempted_actions'] == termination['scripted_completed_actions'] == 3
            and not termination['task_success_claim'], 'complete fixed source termination')
    replay_dir = matrix / (condition + '-replay')
    if replay_complete:
        replay = prior.replay_audit(run, rows, replay_dir, auxiliary_count=24)
        scene_replay = read(replay_dir / 'scene-result.json')
        require(scene_replay == {'status': 'passed', 'events': 1, 'exact_event_records': 9,
            'source_journal_sha256': sha(run / 'episodes.jsonl'), 'state_restore_used': False}, 'exact event replay completion and source')
        require(not (replay_dir / 'failure.json').exists() and not (replay_dir / 'scene-event-mismatch.json').exists(), 'no hidden replay mismatch')
        replay.update(status='PASS', scene_result_sha256=sha(replay_dir / 'scene-result.json'), exact_event_records=9)
    else:
        files = sorted(str(p.relative_to(replay_dir)) for p in replay_dir.rglob('*') if p.is_file())
        require(files == [], 'interrupted replay has no retained result or mismatch files')
        replay = {'status': 'INCOMPLETE', 'result_files': files, 'exact_event_replay_verified': False}
    return {'status': 'PASS' if replay_complete else 'COLLECTION_PASS_REPLAY_INCOMPLETE',
        'collection_status': 'PASS', 'condition': condition, 'journal_sha256': sha(run / 'episodes.jsonl'),
        'journal_records': len(rows), 'prefix': prefix, 'event': event, 'suffix': mechanical,
        'sensor_evidence': sensor, 'own_controls_sha256': sha(run / 'own-controls.json'),
        'replay': replay, 'away_qualifications': qualifications,
        'native_contacts': prior.summarize_contacts(native, phases=[p for p, _ in SCHEDULE]),
        'endpoint_measurements': endpoints, 'termination': termination}


def audit(matrix, producer):
    preflight = read(matrix / 'preflight.json')
    require(sha(matrix / 'preflight.json') == PREFLIGHT and sha(matrix / 'review.txt') == REVIEW
            and preflight['code']['commit'] == FREEZE and preflight['code']['dirty_status'] == '', 'exact frozen admission')
    static = read(producer / 'docs/evidence/autonomous_research/task2_closed_empty_static_bounds.json')
    require(sha(producer / 'docs/evidence/autonomous_research/task2_closed_empty_static_bounds.json') ==
            '5c9a6702516a73d0c577e7c4de64a52a209b5d5a9c821470f36adec9d4e89790', 'reviewed static source')
    closed_path = Path(preflight['transfer']['source_admission']['approach_audit']['path'])
    require(sha(closed_path) == prior.AUDIT_SHA, 'closed full approach audit reused')
    matrix_rows = prior.load_journal(matrix / 'episodes.jsonl')
    request, config, manifest = [read(matrix / f) for f in ('request.json', 'resolved_config.yaml', 'manifest.json')]
    require(config == request and request['condition_order'] == list(ORDER)
            and request['fresh_policy_episodes'] == 2 and request['new_model_calls'] == request['retries'] == 0,
            'registered fixed matrix')
    require(request['preflight_sha256'] == PREFLIGHT and request['review_sha256'] == REVIEW,
            'matrix prospective input hashes')
    require(matrix_rows[0]['data'] == {'manifest': manifest, 'resolved_config': config}
            and all(r['config_hash'] == prior.canonical(config) for r in matrix_rows), 'matrix journal/config binding')
    require(manifest['code'] == preflight['code'] and preflight['physics_calls'] == 0
            and preflight['world_constructed_during_preflight'] is False, 'matrix exact no-world preflight')
    failures = [r for r in matrix_rows if 'failure' in r['kind']]
    require(not failures, 'no recorded matrix scientific/worker failure')
    stages = [(r['kind'], r['data']['condition'], r['data']['stage']) for r in matrix_rows if r['kind'] in ('stage_intent', 'stage_complete')]
    expected_stages = [(kind, condition, stage) for condition in ORDER for stage in ('collect', 'replay')
                       for kind in ('stage_intent', 'stage_complete')]
    require(stages == expected_stages[:len(stages)], 'exact single fixed matrix stage order')
    complete = matrix_rows[-1]['kind'] == 'termination'
    if complete:
        require(stages == expected_stages and len(matrix_rows) == 10 and matrix_rows[-1]['data'] == {
            'reason': 'fixed_neck_scene_pair_and_replays_complete', 'fresh_policy_episodes': 2,
            'verification_replays': 2, 'winner_selected': False, 'task_success_claim': False}, 'closed complete matrix')
        interruption = None
    else:
        require(stages == expected_stages[:-1] and len(matrix_rows) == 8, 'interrupted at first uncompleted away replay')
        sidecar = matrix.with_name(matrix.name + '-outer-exit.json')
        observed = read(sidecar)
        require(observed['observed_tool_session_exit_code'] == 143 and observed['driver_returncode'] is None
                and observed['matrix_termination_record_present'] is False and observed['away_replay_result_files'] == []
                and observed['last_matrix_record'] == {'seq': 7, 'kind': 'stage_intent', 'condition': 'neck-away', 'stage': 'replay'},
                'external interruption observation consistent with retained matrix')
        interruption = {'observation_path': str(sidecar), 'observation_sha256': sha(sidecar),
            'observed_outer_exit_code': 143, 'driver_returncode': None, 'termination_origin': 'not established',
            'first_uncompleted_stage': {'condition': 'neck-away', 'stage': 'replay'},
            'missing_evidence': ['away exact base replay', 'away exact auxiliary replay', 'away exact scene event replay', 'matrix termination'],
            'not_a_scientific_failure_claim': True}
    cells = [audit_cell(matrix, condition, preflight, static, read(closed_path),
                        replay_complete=('stage_complete', condition, 'replay') in stages) for condition in ORDER]
    return {'status': 'PASS' if complete else 'PARTIAL_SOURCE_VERIFIED_NOT_ADMITTED',
        'source_admitted': complete, 'extraction_binding_created': False,
        'freeze': FREEZE, 'raw_directory': str(matrix), 'interruption': interruption,
        'matrix_stages': stages,
        'matrix_journal_sha256': sha(matrix / 'episodes.jsonl'), 'preflight_sha256': PREFLIGHT,
        'prospective_review_sha256': REVIEW, 'conditions': cells,
        'new_physics_render_model_LK_FK_calls': 0,
        'scope': 'Stored source and replay audit. Closed exact prefixes reuse the earlier bulk audit; exogenous event and suffix evidence checked independently. No holding or settled-empty inference; RGB/qvel/trajectory interpretation remains separate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.matrix, args.producer)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'conditions'}, indent=2))
