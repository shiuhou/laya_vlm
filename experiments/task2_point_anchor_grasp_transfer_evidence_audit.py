"""Stored-only fixed 2x2 audit; closed approach proofs are reused by exact equality."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np

from task2_point_anchor_approach_evidence_audit import (
    FRAME_KEYS, canonical, load_journal, near, read, require, sha,
)

ORDER = ('whole-close', 'whole-open_hold', 'neck-close', 'neck-open_hold')
SOURCE_SHA = {'whole': '690f81aef2fe5b3d2b5aee09d72f269dfbf7f37ee24c1f9a83c061f7ce4b4541',
              'neck': '3e335ff3d4791f43b74750216fd928470145ea0d34d5a03fbeaba3f2ff492ae8'}
AUDIT_SHA = '0cd47a1433ac25d14b45aa942a17d7322e19865804c33b3adb2fee25a2d2d56e'
OBS_KEYS = ('robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos', 'robot0_gripper_qvel')
TOLERANCES = {'hold_rotation_deg': 1., 'hold_translation_m': .0015,
              'rotation_error_deg': 2., 'translation_error_m': .002}


def grouped(rows):
    result = defaultdict(list)
    for row in rows:
        result[row['kind']].append(row)
    return result


def one(rows, kind):
    selected = [r['data'] for r in rows if r['kind'] == kind]
    require(len(selected) == 1, 'one ' + kind)
    return selected[0]


def arrays_equal(a, b):
    with np.load(a, allow_pickle=False) as x, np.load(b, allow_pickle=False) as y:
        require(set(x.files) == set(y.files) == set(FRAME_KEYS), 'exact RGB-D array schema')
        for key in FRAME_KEYS:
            require(x[key].dtype == y[key].dtype and x[key].shape == y[key].shape
                    and x[key].tobytes() == y[key].tobytes(), 'exact RGB-D bytes: ' + key)


def check_image(directory, row):
    require(sha(directory / row['artifact']) == row['artifact_sha256'], 'image artifact hash')
    with np.load(directory / row['artifact'], allow_pickle=False) as frame:
        require(set(frame.files) == set(FRAME_KEYS), 'four image arrays')
        require(frame['rgb'].shape == (384, 384, 3) and frame['rgb'].dtype == np.uint8
                and frame['depth_m'].shape == (384, 384) and frame['depth_m'].dtype == np.float32
                and frame['intrinsics'].shape == (3, 3) and frame['camera_to_world'].shape == (4, 4),
                'image/calibration schema')


def exact_prefix(run, rows, source, anchor, closed_audit):
    require(sha(source / anchor / 'episodes.jsonl') == SOURCE_SHA[anchor], 'closed source journal')
    old = load_journal(source / anchor / 'episodes.jsonl')
    require(one(old, 'run_start')['manifest'] == read(source / anchor / 'manifest.json'), 'source manifest bound to closed journal')
    expected = [r for r in old if r['kind'] not in ('run_start', 'termination')]
    gates = [i for i, r in enumerate(rows) if r['kind'] == 'approach_prefix_verified']
    require(len(gates) == 1, 'one verified fresh approach prefix')
    actual = rows[1:gates[0]]
    require(len(actual) == len(expected), 'entire approach prefix count')
    for a, b in zip(actual, expected):
        require(a['kind'] == b['kind'], 'approach record kind/order')
        x, y = a['data'], b['data']
        if a['kind'] == 'vision_capture':
            check_image(run, x)
            require(sha(source / anchor / y['artifact']) == y['artifact_sha256'], 'closed prefix frame hash')
            arrays_equal(run / x['artifact'], source / anchor / y['artifact'])
            x = {k: v for k, v in x.items() if k != 'artifact_sha256'}
            y = {k: v for k, v in y.items() if k != 'artifact_sha256'}
        require(x == y, 'exact closed scientific prefix: ' + a['kind'])
    terminal = one(old, 'termination')
    require(actual[-1]['kind'] == 'decision' and actual[-1]['data']['selected'] == 'STOP'
            and terminal['reason'] == 'rule_no_strict_nominal_improvement', 'original STOP executes no hold')
    receipt = rows[gates[0]]['data']
    require(receipt == {'anchor': anchor, 'source_journal_sha256': SOURCE_SHA[anchor],
        'exact_records': len(actual), 'exact_primary_captures': terminal['completed_actions'] + 1,
        'source_state_restored': False, 'archived_controls_used': False, 'approach_STOP_executed': False},
        'prefix receipt independently verified')
    prior = next(c for c in closed_audit['conditions'] if c['condition'] == anchor)
    require(prior['journal_sha256'] == SOURCE_SHA[anchor] and prior['actions'] == terminal['completed_actions'],
            'closed full-audit bulk proof')
    return terminal, rows[gates[0] + 1:], {'records': len(actual),
        'actions': terminal['completed_actions'], 'primary_captures': terminal['completed_actions'] + 1,
        'closed_source_journal_sha256': SOURCE_SHA[anchor], 'closed_audit_sha256': AUDIT_SHA,
        'candidate_memberships_recomputed': 0, 'all_scientific_records_and_image_arrays_exact': True}


def contact_evidence(snapshot, groups):
    raw, strong, support, pads = [], [], [], set()
    for c in snapshot['contacts']:
        a, b = c['geom_ids']
        force = c['normal_force_N']
        require(len(c['force_contact_frame']) == 6 and force == c['force_contact_frame'][0]
                and np.isfinite(c['force_contact_frame']).all(), 'raw contact force components')
        allowed = ((a in groups['gripper'] and b in groups['bottle'])
                   or (b in groups['gripper'] and a in groups['bottle']))
        robot = a in groups['robot'] or b in groups['robot']
        require(c['unexpected_robot_contact'] == bool(robot and not allowed and force > .05),
                'unchanged strict unexpected-contact predicate')
        if a in groups['bottle'] or b in groups['bottle']:
            other = b if a in groups['bottle'] else a
            names = dict(zip(c['geom_ids'], c['geom_names']))
            if other in groups['robot']:
                name = names[other]
                family = ('pads' if other in groups['pads'] else 'fingers' if 'finger' in name
                          else 'hand' if 'hand' in name else 'other_robot')
                item = {'family': family, 'geom_ids': c['geom_ids'], 'geom_names': c['geom_names'],
                        'normal_force_N': force}
                raw.append(item)
                if force > .05:
                    strong.append(item)
                    if other in groups['pads']:
                        pads.add(other)
            elif other not in groups['bottle']:
                support.append({'geom_ids': c['geom_ids'], 'geom_names': c['geom_names'],
                    'normal_force_N': force, 'above_0_05N': force > .05})
    return {'raw_robot_bottle': raw, 'strong_robot_bottle': strong,
            'bilateral_pads': pads == groups['pads'], 'bottle_scene_contacts': support,
            'unexpected_robot_contact': any(c['unexpected_robot_contact'] for c in snapshot['contacts'])}


def suffix_audit(rows, suffix, groups, approach_end, arm):
    all_by = grouped(rows)
    by = grouped(suffix)
    actions = [r['data'] for r in by['action_completed']]
    starts = {(r['data']['step'], r['data']['control']): r['data'] for r in by['control_started']}
    ends = {(r['data']['step'], r['data']['control']): r['data'] for r in by['control_completed']}
    require(len(starts) == len(by['control_started']) and len(ends) == len(by['control_completed']), 'unique suffix controls')
    tokens = ('GRASP' if arm == 'close' else 'STOP', 'MV_UP')
    first_step = approach_end['completed_actions']
    expected_grip = 1 if arm == 'close' else -1
    action_starts = [r['data'] for r in by['action_started']]
    require(len(action_starts) <= 2 and len(actions) <= len(action_starts), 'bounded suffix attempts')
    for offset, a in enumerate(action_starts):
        require(a == {'step': first_step + offset, 'token': tokens[offset],
            'native_phase': ('close_or_hold', 'lift')[offset], 'selection': 'registered_scripted_intervention', 'arm': arm},
            'fixed suffix intent')
    previous_state = all_by['control_completed'][first_step * 8 - 1]['data']['state_after']
    previous_own = all_by['control_completed'][first_step * 8 - 1]['data']['returned_own_observations']
    command_count = 0
    for offset, action in enumerate(action_starts):
        step = first_step + offset
        target = np.asarray(previous_own['robot0_eef_pos']).copy()
        if offset == 1:
            target[2] += .01
        for control in range(8):
            key = step, control
            if key not in starts:
                break
            before = starts[key]
            require(before['state_before'] == previous_state
                    and before['previous_returned_own_observations'] == previous_own, 'suffix state/own handoff')
            command = np.r_[np.clip((target - previous_own['robot0_eef_pos']) / .05, -1, 1), np.zeros(3), expected_grip].tolist()
            require(before['command'] == command, 'independent suffix command arithmetic')
            command_count += 1
            if key not in ends:
                break
            require(ends[key]['command'] == command, 'completed command identity')
            previous_state, previous_own = ends[key]['state_after'], ends[key]['returned_own_observations']
    require(command_count == len(starts), 'all observed suffix commands accounted')
    native = [r for r in suffix if r['kind'] in ('native_before', 'native_after')]
    summaries = []
    previous_native = None
    for i, r in enumerate(native):
        s = r['data']
        offset, within = divmod(i, 400)
        integration, stage = divmod(within, 2)
        step, control = first_step + offset, integration // 25
        require(offset < len(action_starts) and r['kind'] == ('native_before', 'native_after')[stage]
                and (s['step'], s['control'], s['index'], s['arm']) ==
                    (step, control, integration, ('close_or_hold', 'lift')[offset]), 'native suffix ordering')
        state = [s['time_s'], *s['qpos'], *s['qvel']]
        if not stage:
            if previous_native is not None:
                require(state == previous_native, 'native integration state continuity')
            if integration % 25 == 0:
                require(state == starts[(step, control)]['state_before'], 'native/control before equality')
        else:
            near(s['time_s'] - native[i - 1]['data']['time_s'], .002, 'native 2 ms', 2e-15)
            if integration % 25 == 24 and (step, control) in ends:
                require(state == ends[(step, control)]['state_after'], 'native/control after equality')
            previous_native = state
        measured = contact_evidence(s, groups)
        summaries.append({'kind': r['kind'], 'step': step, 'control': control, 'index': integration,
                          'time_s': s['time_s'], 'record_id': r['record_id'], **measured})
    endpoints = {r['data']['step']: r['data'] for r in by['endpoint']}
    validated = []
    for offset, a in enumerate(actions):
        step = first_step + offset
        result, endpoint = a['result'], endpoints[step]
        control_count = sum(k[0] == step for k in ends)
        integrations = sum(s['step'] == step and s['kind'] == 'native_after' for s in summaries)
        require(0 < control_count <= 8, 'observed completed primitive controls')
        last_control = control_count - 1
        require(a['token'] == result['token'] == tokens[offset] and a['step'] == step
                and a['native_phase'] == ('close_or_hold', 'lift')[offset], 'completed suffix identity')
        measured = np.asarray(result['after']) - result['before']
        require(result['delta_m'] == measured.tolist(), 'suffix TCP delta')
        require(result['before'] == starts[(step, 0)]['previous_returned_own_observations']['robot0_eef_pos']
                and result['after'] == ends[(step, last_control)]['returned_own_observations']['robot0_eef_pos'], 'suffix returned TCP endpoints')
        require(endpoint['own_observations'] == ends[(step, last_control)]['returned_own_observations']
                and endpoint['proprioception']['tcp_pos_world_m'] == result['after']
                and endpoint['proprioception']['gripper_command'] == ('CLOSED' if arm == 'close' else 'OPEN'), 'suffix endpoint own packet')
        require(result['low_level_commands'] == [starts[(step, c)]['command'] for c in range(control_count)], 'all result commands')
        before, after = result['execution_before'], result['execution_after']
        require(before['tcp_xyz'] == result['before'] and after['tcp_xyz'] == result['after'], 'validator TCP bindings')
        require(before['sim_time'] == starts[(step, 0)]['state_before'][0]
                and after['sim_time'] == ends[(step, last_control)]['state_after'][0], 'validator boundary times')
        rotation = np.asarray(after['orientation']) @ np.asarray(before['orientation']).T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1, 1))))
        residual = float(np.linalg.norm(measured - ([0, 0, .01] if offset else [0, 0, 0])))
        reasons = []
        if after['gripper_command'] != expected_grip:
            reasons.append('gripper_command_changed_unexpectedly')
        if residual > (.002 if offset else .0015):
            reasons.append('translation_error' if offset else 'unintended_translation')
        if angle > 1:
            reasons.append('unintended_rotation')
        require(result['execution_contract_tolerances'] == TOLERANCES
                and result['execution_contract_reason'] == reasons
                and result['execution_contract_violation'] == bool(reasons), 'unchanged validator recomputation')
        near(result['rotation_delta'], rotation, 'rotation delta')
        near(result['rotation_angle_deg'], angle, 'rotation angle')
        require(result['finger_gap_delta'] == after['finger_gap_m'] - before['finger_gap_m'], 'finite-gap delta')
        require(a['controls'] == result['environment_step_count'] == control_count
                and a['native_integrations'] == result['low_level_step_count'] == integrations, 'completed suffix counts')
        require(before['gripper_command'] == (-1 if offset == 0 else expected_grip), 'retained/changed jaw boundary')
        invalid = any(s['unexpected_robot_contact'] for s in summaries if s['step'] == step)
        count_failure = control_count != 8 or integrations != 200
        if reasons or invalid or count_failure:
            require(offset == len(action_starts) - 1 and bool(by['intervention_failure']), 'failed action cannot continue')
        validated.append({'step': step, 'token': a['token'], 'translation_residual_mm': residual * 1000,
            'rotation_change_deg': angle, 'validator_reasons': reasons, 'unexpected_robot_contact': invalid,
            'control_count': control_count, 'native_integrations': integrations, 'count_failure': count_failure,
            'official_success': result['success']})
    return {'attempted_actions': len(action_starts), 'completed_actions': len(actions),
            'controls_started': len(starts), 'controls_completed': len(ends), 'native_snapshots': len(native),
            'actions': validated}, summaries


def sensor_and_labels(run, rows, groups):
    by = grouped(rows)
    captures = [r['data'] for r in by['vision_capture']]
    aux = [r['data'] for r in by['auxiliary_capture']]
    endpoints = {r['data']['capture_seq']: r for r in by['endpoint']}
    controls = {(r['data']['step'], r['data']['control']): r for r in by['control_completed']}
    gate = one(rows, 'initial_frame_gate')
    condition = run.name
    anchor, arm = condition.split('-', 1)
    for c in captures:
        check_image(run, c)
    require([c['capture_seq'] for c in captures] == list(range(1, len(captures) + 1)), 'primary camera IDs unchanged')
    require([c['source_capture_seq'] for c in aux] == list(range(1, len(aux) + 1)) and len(aux) <= 16,
            'separate sequential auxiliary IDs')
    require(len({(c['after_step'], c['control']) for c in aux}) == len(aux), 'unique auxiliary controls')
    for c in aux:
        check_image(run, c)
        require((c['condition'], c['anchor'], c['arm']) == (condition, anchor, arm), 'auxiliary condition identity')
        control = controls[(c['after_step'], c['control'])]
        require(c['own_observations'] == control['data']['returned_own_observations']
                and c['own_tcp_world_m'] == c['own_observations']['robot0_eef_pos'], 'auxiliary explicit returned packet')
        require(c['capture_sim_time'] == c['capture_read_sim_time_s'] == c['tcp_read_sim_time_s']
                == control['data']['state_after'][0], 'auxiliary read/control boundary')
        require(c['exact_observation_sample_time_s'] is None and c['cached_geometry_sample_time_s'] is None
                and c['source_capture_stream'] == 'auxiliary' and c['render_preserves_state_and_caches'], 'auxiliary measurement scope')
        require(c['own_source'] == {'journal': 'episodes.jsonl', 'kind': 'control_completed',
                'step': c['after_step'], 'control': c['control']}
                and c['tcp_source_field'] == 'control_completed.returned_own_observations.robot0_eef_pos', 'auxiliary linkage')
        require(control['seq'] < next(r['seq'] for r in by['auxiliary_capture'] if r['data'] == c), 'own record precedes auxiliary capture')
    sensor = read(run / 'sensor-captures.json')
    expected_prefix = [r for r in by['vision_capture']
                       if r['data']['capture_seq'] not in endpoints
                       or 'native_phase' not in endpoints[r['data']['capture_seq']]['data']]
    require(len(sensor) == len(expected_prefix) + len(aux)
            and [c['capture_id'] for c in sensor] == list(range(len(sensor))), 'complete deduplicated chronological sensor export')
    for exported, record in zip(sensor, expected_prefix):
        source = record['data']
        endpoint = endpoints.get(source['capture_seq'])
        reset = source['capture_seq'] == 1
        own = gate['initial_own_observations'] if reset else None if endpoint is None else endpoint['data']['own_observations']
        require((exported['condition'], exported['anchor'], exported['arm']) == (condition, anchor, arm), 'primary condition identity')
        require(exported['own_observations'] == own
                and exported['own_tcp_world_m'] == (None if own is None else own['robot0_eef_pos']), 'primary exported own packet')
        require(exported['capture_record_id'] == record['record_id'] and exported['artifact'] == source['artifact']
                and exported['artifact_sha256'] == source['artifact_sha256']
                and exported['source_capture_seq'] == source['capture_seq'] and exported['source_capture_stream'] == 'primary', 'primary source identity')
        require(exported['phase'] == ('reset' if reset else 'approach')
                and exported['capture_sim_time'] == source['capture_sim_time']
                and exported['exact_observation_sample_time_s'] is None
                and exported['cached_geometry_sample_time_s'] is None, 'primary phase/time limits')
        require(exported['after_step'] == (-1 if reset else None if endpoint is None else endpoint['data']['step'])
                and exported['control'] == (None if endpoint is None else 7)
                and exported['own_packet_status'] == ('recorded' if own is not None else 'missing_endpoint_in_partial_run'), 'primary boundary and partial-packet status')
        require(exported['capture_read_sim_time_s'] == source['capture_sim_time']
                and exported['tcp_read_sim_time_s'] == (source['capture_sim_time'] if own is not None else None)
                and exported['render_preserves_state_and_caches'], 'primary read-time/invariance declaration')
        require(exported['own_source'] == {'journal': 'episodes.jsonl', 'kind': 'initial_frame_gate' if reset else 'endpoint',
                'step': None if endpoint is None else endpoint['data']['step']}, 'primary own-packet source linkage')
        field = ('initial_frame_gate.initial_own_observations.robot0_eef_pos' if reset
                 else 'endpoint.own_observations.robot0_eef_pos') if own is not None else None
        require(exported['tcp_source_field'] == field, 'primary exact TCP field provenance')
    for index, (exported, source) in enumerate(zip(sensor[len(expected_prefix):], aux), len(expected_prefix)):
        require(exported == {**source, 'capture_id': index}, 'all auxiliary manifest fields preserved')
    seal = read(run / 'sensor-seal.json')
    expected_hashes = {'sensor-captures.json': sha(run / 'sensor-captures.json'),
                       **{c['artifact']: c['artifact_sha256'] for c in sensor}}
    require(seal['sha256'] == expected_hashes
            and all(sha(run / path) == digest for path, digest in expected_hashes.items()), 'sensor seal exact complete artifacts')
    require(seal['journal_sha256_linkage_only'] == sha(run / 'episodes.jsonl')
            and seal['journal_parse_errors'] == [] and seal['holding'] is None, 'sensor seal boundary and unknown holding')
    require(all(not {'label', 'contacts', 'bottle_center_mm', 'valid_grasp_relation'} & c.keys() for c in sensor), 'no evaluator fields in sensor export')
    labels = read(run / 'evaluator-only/labels.json')
    require(len(labels) == len(aux), 'every auxiliary endpoint has one buffered evaluator record')
    measured = []
    for auxiliary_index, (source, c) in enumerate(zip(labels, aux)):
        require((source['phase'], source['step'], source['control']) == (c['phase'], c['after_step'], c['control']), 'label/capture ordering')
        label, snapshot = source['label'], source['raw_contact_snapshot']
        state = controls[(source['step'], source['control'])]['data']['state_after']
        require(label['state'] == state == [snapshot['time_s'], *snapshot['qpos'], *snapshot['qvel']]
                and label['sim_time_s'] == c['capture_sim_time'] == snapshot['time_s']
                and label['privileged'] is True, 'evaluator endpoint state/time binding')
        contact = contact_evidence(snapshot, groups)
        require(label['valid_grasp_relation'] == contact['bilateral_pads'], 'independent strict bilateral endpoint relation')
        raw_strong = []
        for item in snapshot['contacts']:
            a, b = item['geom_ids']
            if item['normal_force_N'] <= .05 or a in groups['gripper'] and b in groups['gripper']:
                continue
            hand = a if a in groups['gripper'] else b if b in groups['gripper'] else None
            if hand is not None:
                names = dict(zip(item['geom_ids'], item['geom_names']))
                raw_strong.append((names[hand], names[b if hand == a else a], item['normal_force_N']))
        require(Counter(raw_strong) == Counter((item['hand'], item['other'], item['normal_force_N'])
                for item in label['contacts']), 'thresholded evaluator contacts match raw snapshot')
        require(np.asarray(label['bottle_center_mm']).shape == (3,) and np.isfinite(label['bottle_center_mm']).all()
                and np.isfinite(label['bottle_bottom_mm']), 'finite evaluator center/bottom')
        measured.append({'phase': source['phase'], 'step': source['step'], 'control': source['control'],
            'auxiliary_capture_seq': c['source_capture_seq'], 'sensor_capture_id': len(expected_prefix) + auxiliary_index,
            'time_s': c['capture_sim_time'],
            'bottle_center_mm': label['bottle_center_mm'], 'bottle_bottom_mm': label['bottle_bottom_mm'],
            'bottle_rotation': None, 'rotation_status': 'unknown_no_archived_quaternion_address_mapping',
            'official_success': label['official_success'], **contact})
    ordering = {'sensor_manifest_mtime_ns': (run / 'sensor-captures.json').stat().st_mtime_ns,
                'sensor_seal_mtime_ns': (run / 'sensor-seal.json').stat().st_mtime_ns,
                'labels_mtime_ns': (run / 'evaluator-only/labels.json').stat().st_mtime_ns}
    require(ordering['sensor_manifest_mtime_ns'] <= ordering['sensor_seal_mtime_ns'] <= ordering['labels_mtime_ns'], 'observed file-write order')
    return {'sensor_manifest_sha256': sha(run / 'sensor-captures.json'), 'sensor_seal_sha256': sha(run / 'sensor-seal.json'),
            'labels_sha256': sha(run / 'evaluator-only/labels.json'), 'primary_captures': len(captures),
            'auxiliary_captures': len(aux), 'sensor_chronology_captures': len(sensor),
            'write_order': ordering, 'write_order_basis': 'reviewed seal-before-label code and filesystem mtimes; no dedicated journal seal timestamp'}, measured


def replay_audit(run, rows, replay_directory):
    by = grouped(rows)
    result = read(replay_directory / 'result.json')
    auxiliary = read(replay_directory / 'auxiliary-result.json')
    starts = [r['data'] for r in by['control_started']]
    ends = [r['data'] for r in by['control_completed']]
    native = [r for r in rows if r['kind'] in ('native_before', 'native_after')]
    captures = [r['data'] for r in by['vision_capture']]
    require(result['status'] == 'passed' and result['source_journal_sha256'] == sha(run / 'episodes.jsonl')
            and result['code'] == one(rows, 'run_start')['manifest']['code'] and result['policy_or_model_rerun'] is False,
            'replay source and code identity')
    require(result['exact_controls'] == len(starts) == len(ends) == len(result['control_states'])
            and result['exact_native_snapshots'] == len(native) == len(result['native_states'])
            and result['exact_captures'] == len(captures) == len(result['frame_checks']), 'complete primary replay coverage')
    for a, b, replayed in zip(starts, ends, result['control_states']):
        require(replayed == {'step': a['step'], 'control': a['control'], 'state_before': a['state_before'],
                'state_after': b['state_after'], 'exact': True}, 'reexported replay state identity')
    for source, replayed in zip(native, result['native_states']):
        expected = {'stage': source['kind'], **{k: source['data'][k] for k in
            ('step', 'control', 'index', 'time_s', 'qpos', 'qvel', 'integration_fingerprint')}, 'entire_snapshot_exact': True}
        require(replayed == expected, 'reexported replay native evidence')
    for source, replayed in zip(captures, result['frame_checks']):
        require(replayed == {'capture_seq': source['capture_seq'], 'array_bytes_exact': {k: True for k in FRAME_KEYS}}, 'primary replay byte gates')
    aux = [r['data'] for r in by['auxiliary_capture']]
    require(auxiliary['status'] == 'passed' and auxiliary['source_sensor_seal_sha256'] == sha(run / 'sensor-seal.json')
            and len(aux) == len(auxiliary['captures']) == 16, 'all auxiliary replay captures')
    require(auxiliary['captures'] == [{'step': c['after_step'], 'control': c['control'],
            'array_bytes_exact': {k: True for k in FRAME_KEYS}} for c in aux], 'auxiliary replay complete ordered gates')
    return {'result_sha256': sha(replay_directory / 'result.json'), 'auxiliary_result_sha256': sha(replay_directory / 'auxiliary-result.json'),
            'controls': len(starts), 'native_snapshots': len(native), 'primary_captures': len(captures), 'auxiliary_captures': len(aux),
            'limit': 'full replay contacts/images compared by reviewed verifier, not separately reexported; exported states/fingerprints/gates independently checked'}


def summarize_contacts(samples):
    result = {}
    for phase in ('close_or_hold', 'lift'):
        phase_steps = sorted({s['step'] for s in samples})
        step = phase_steps[0] + (phase == 'lift') if phase_steps else None
        for stage in ('native_before', 'native_after'):
            selected = [s for s in samples if s['step'] == step and s['kind'] == stage]
            key = phase + '/' + stage
            result[key] = {'samples': len(selected), 'bilateral_pad_samples': sum(s['bilateral_pads'] for s in selected),
                'raw_robot_bottle_rows_by_family': dict(Counter(c['family'] for s in selected for c in s['raw_robot_bottle'])),
                'strong_robot_bottle_rows_by_family': dict(Counter(c['family'] for s in selected for c in s['strong_robot_bottle'])),
                'bilateral_with_raw_nonpad_samples': sum(s['bilateral_pads'] and any(c['family'] != 'pads' for c in s['raw_robot_bottle']) for s in selected),
                'bilateral_with_strong_nonpad_samples': sum(s['bilateral_pads'] and any(c['family'] != 'pads' for c in s['strong_robot_bottle']) for s in selected),
                'bottle_scene_raw_contact_samples': sum(bool(s['bottle_scene_contacts']) for s in selected),
                'bottle_scene_strong_contact_samples': sum(any(c['above_0_05N'] for c in s['bottle_scene_contacts']) for s in selected),
                'unexpected_contact_samples': sum(s['unexpected_robot_contact'] for s in selected)}
    pairs = {}
    for s in samples:
        for family in ('raw_robot_bottle', 'bottle_scene_contacts'):
            for c in s[family]:
                pair = tuple(sorted(zip(c['geom_ids'], c['geom_names'])))
                if pair not in pairs:
                    pairs[pair] = {'geom_ids': [p[0] for p in pair], 'geom_names': [p[1] for p in pair],
                        'family': c.get('family', 'bottle_scene'), 'raw_rows': 0, 'strong_rows': 0,
                        'maximum_normal_force_N': c['normal_force_N']}
                entry = pairs[pair]
                entry['raw_rows'] += 1
                entry['strong_rows'] += c['normal_force_N'] > .05
                entry['maximum_normal_force_N'] = max(entry['maximum_normal_force_N'], c['normal_force_N'])
    return {'by_phase_and_stage': result, 'pairs': list(pairs.values()),
            'first_raw_robot_bottle': next((s for s in samples if s['raw_robot_bottle']), None),
            'first_strong_robot_bottle': next((s for s in samples if s['strong_robot_bottle']), None),
            'first_unexpected': next((s for s in samples if s['unexpected_robot_contact']), None)}


def audit_cell(matrix, condition, preflight, source, closed_audit):
    run = matrix / condition
    rows = load_journal(run / 'episodes.jsonl')
    by = grouped(rows)
    manifest, config = read(run / 'manifest.json'), read(run / 'resolved_config.yaml')
    require(one(rows, 'run_start') == {'manifest': manifest, 'resolved_config': config}, 'cell manifest/config binding')
    require(all(r['config_hash'] == canonical(config) for r in rows), 'cell configuration hashes')
    require(config == {'condition': condition, 'seed': 1, 'init_state_id': 0, 'max_actions': 40, 'wall_limit_s': 900}, 'fixed cell configuration')
    require(manifest['code'] == preflight['code'] and manifest['code']['dirty_status'] == '', 'exact clean cell freeze')
    for key in ('source_sha256', 'unchanged_source_sha256', 'versions', 'stepping_sources', 'jev', 'environment',
                'endpoint_guard', 'common', 'anchors', 'baseline_protocol_sha256', 'protocol_sha256'):
        require(manifest[key] == preflight[key], 'cell/preflight identity: ' + key)
    anchor, arm = condition.split('-', 1)
    original_manifest = read(source / anchor / 'manifest.json')
    for key in ('versions', 'stepping_sources', 'jev', 'environment', 'endpoint_guard', 'common', 'anchors',
                'source_sha256', 'unchanged_source_sha256', 'baseline_protocol_sha256'):
        require(manifest[key] == original_manifest[key], 'literal closed-source runtime/support identity: ' + key)
    require(manifest['condition'] == anchor and manifest['point'] == preflight['anchors'][anchor]
            and manifest['goal_anchor'] == manifest['point']['provenance'], 'fixed anchor provenance')
    transfer = manifest['transfer']
    require(transfer['condition'] == condition and transfer['anchor'] == anchor and transfer['arm'] == arm
            and transfer['order'] == list(ORDER) and transfer['scripted_tokens'] == ['GRASP' if arm == 'close' else 'STOP', 'MV_UP']
            and transfer['scripted_control_count'] == transfer['auxiliary_control_captures'] == 16
            and transfer['source_prefix_is_verification_only'] and transfer['archived_controls_in_collection'] is False,
            'fixed transfer settings')
    require(manifest['source_state_restored'] is False and manifest['archived_controls_used'] is False
            and manifest['new_model_calls'] == 0, 'fresh collection declarations')
    require(sha(run / 'review.txt') == manifest['review_sha256'] == sha(matrix / 'review.txt')
            and sha(run / 'protocol.md') == preflight['protocol_sha256'], 'exact prospective/protocol copies')
    require('--worker-stage' in manifest['argv'] and '--condition' in manifest['argv']
            and manifest['argv'][manifest['argv'].index('--condition') + 1] == condition, 'dedicated worker invocation')
    termination = one(rows, 'termination')
    if not by['approach_prefix_verified']:
        require(bool(by['failure']) and not any('native_phase' in r['data'] for r in by['action_started']), 'failure before intervention')
        return {'status': 'PASS', 'condition': condition, 'outcome': 'failed_before_verified_prefix',
                'journal_sha256': sha(run / 'episodes.jsonl'), 'termination': termination,
                'failures': [r for r in rows if r['kind'] in ('failure', 'intervention_failure')],
                'collection_wall_times': [rows[0]['wall_time'], rows[-1]['wall_time']],
                'prefix_bulk_proof_claimed': False, 'suffix_executed': False}
    original_end, suffix, prefix = exact_prefix(run, rows, source, anchor, closed_audit)
    gate = one(rows, 'initial_frame_gate')
    groups = {k: set(v) for k, v in gate['groups_evaluator_only'].items()}
    require(groups['pads'] == {78, 81}, 'original designated pads')
    mechanical, native = suffix_audit(rows, suffix, groups, original_end, arm)
    sensor, endpoints = sensor_and_labels(run, rows, groups)
    failures = [r for r in rows if r['kind'] in ('failure', 'intervention_failure')]
    normal = not failures
    if normal:
        require(mechanical['attempted_actions'] == mechanical['completed_actions'] == 2
                and mechanical['controls_started'] == mechanical['controls_completed'] == 16
                and mechanical['native_snapshots'] == 800 and sensor['auxiliary_captures'] == 16, 'complete normal suffix')
        require(termination['reason'] == 'fixed_approach_and_scripted_suffix_complete'
                and termination['approach_termination'] == original_end
                and termination['attempted_actions'] == termination['completed_actions'] == original_end['completed_actions'] + 2
                and termination['scripted_attempted_actions'] == termination['scripted_completed_actions'] == 2
                and termination['grasp_attempted'] == (arm == 'close') and not termination['winner_selected']
                and not termination['task_success_claim'], 'complete bounded termination')
    else:
        require(termination['reason'] in ('runtime_or_admission_failure', 'wall_limit'), 'failed cell termination')
        require(termination['approach_attempted_actions'] == original_end['attempted_actions']
                and termination['approach_completed_actions'] == original_end['completed_actions']
                and termination['approach_step'] == original_end['last_step'], 'qualified failure counters')
        failure = one(rows, 'intervention_failure')
        require(failure['scripted_attempted_actions'] == mechanical['attempted_actions']
                and failure['scripted_completed_actions'] == mechanical['completed_actions']
                and failure['total_attempted_actions'] == original_end['attempted_actions'] + mechanical['attempted_actions']
                and failure['total_completed_actions'] == original_end['completed_actions'] + mechanical['completed_actions'], 'failure totals')
    replay = replay_audit(run, rows, matrix / (condition + '-replay')) if normal and (matrix / (condition + '-replay/result.json')).exists() else None
    lift = [e for e in endpoints if e['phase'] == 'lift']
    prelift = next((e for e in endpoints if e['phase'] == 'close_or_hold' and e['control'] == 7), None)
    final = next((e for e in lift if e['control'] == 7), None)
    motion = None
    if prelift is not None and final is not None:
        motion = {'bottle_center_delta_mm': (np.asarray(final['bottle_center_mm']) - prelift['bottle_center_mm']).tolist(),
                  'bottle_bottom_delta_mm': final['bottle_bottom_mm'] - prelift['bottle_bottom_mm'],
                  'prelift_center_mm': prelift['bottle_center_mm'], 'final_center_mm': final['bottle_center_mm'],
                  'prelift_bottom_mm': prelift['bottle_bottom_mm'], 'final_bottom_mm': final['bottle_bottom_mm'],
                  'bottle_rotation': None, 'rotation_status': 'unknown_no_source_specific_qpos_address_mapping'}
    return {'status': 'PASS', 'condition': condition, 'outcome': 'normal_complete' if normal else 'failed_suffix',
            'journal_sha256': sha(run / 'episodes.jsonl'), 'journal_records': len(rows), 'prefix': prefix,
            'collection_wall_times': [rows[0]['wall_time'], rows[-1]['wall_time']],
            'suffix': mechanical, 'sensor_evidence': sensor, 'replay': replay, 'termination': termination,
            'failures': failures, 'native_contacts': summarize_contacts(native), 'endpoint_measurements': endpoints,
            'lift_bilateral_endpoints': sum(e['bilateral_pads'] for e in lift), 'lift_endpoint_count': len(lift),
            'lift_motion': motion}


def local_witnesses(cells):
    by = {c['condition']: c for c in cells}
    witnesses = {}
    for anchor in ('whole', 'neck'):
        pair = [by.get(anchor + '-' + arm) for arm in ('close', 'open_hold')]
        if any(c is None or c['outcome'] != 'normal_complete' or c['replay'] is None for c in pair):
            witnesses[anchor] = {'sampled_endpoint_witness': None, 'status': 'incomplete_matched_pair'}
            continue
        close, opened = pair
        close_z, open_z = [c['lift_motion']['bottle_center_delta_mm'][2] for c in pair]
        validations = all(not a['validator_reasons'] for c in pair for a in c['suffix']['actions'])
        witness = validations and close_z > max(0, open_z) and close['lift_bilateral_endpoints'] == 8 and opened['lift_bilateral_endpoints'] == 0
        witnesses[anchor] = {'sampled_endpoint_witness': witness, 'all_four_validators_pass': validations,
            'close_center_rise_mm': close_z, 'open_center_rise_mm': open_z,
            'close_bottom_rise_mm': close['lift_motion']['bottle_bottom_delta_mm'],
            'open_bottom_rise_mm': opened['lift_motion']['bottle_bottom_delta_mm'],
            'close_bilateral_lift_endpoints': close['lift_bilateral_endpoints'],
            'open_bilateral_lift_endpoints': opened['lift_bilateral_endpoints'],
            'close_native_bilateral_by_stage': {s: close['native_contacts']['by_phase_and_stage']['lift/' + s]['bilateral_pad_samples'] for s in ('native_before', 'native_after')},
            'support_free_retention': None, 'clean_interaction_valid_grasp': None, 'task_success_claim': False}
    return witnesses


def audit_matrix(matrix, conditions=None):
    preflight = read(matrix / 'preflight.json')
    request, manifest, config = read(matrix / 'request.json'), read(matrix / 'manifest.json'), read(matrix / 'resolved_config.yaml')
    require(config == request and request['condition_order'] == list(ORDER) and request['fresh_policy_episodes'] == 4
            and request['new_model_calls'] == request['retries'] == 0, 'registered fixed matrix')
    require(sha(matrix / 'preflight.json') == request['preflight_sha256'] and manifest['code'] == preflight['code']
            and preflight['code']['dirty_status'] == '' and preflight['physics_calls'] == 0
            and preflight['world_constructed_during_preflight'] is False, 'exact no-world preflight')
    require(sha(matrix / 'review.txt') == request['review_sha256'], 'review identity')
    review = (matrix / 'review.txt').read_text()
    require('PASS' in review and preflight['code']['commit'] in review and request['preflight_sha256'] in review, 'root prospective binds exact freeze/preflight')
    source = Path(request['source_admission']['source_directory'])
    ref = request['source_admission']['approach_audit']
    require(ref['sha256'] == sha(Path(ref['path'])) == AUDIT_SHA, 'closed immutable source audit')
    closed = read(ref['path'])
    require(closed['status'] == 'PASS', 'closed source integrity')
    batch = load_journal(matrix / 'episodes.jsonl')
    require(batch[0]['data'] == {'manifest': manifest, 'resolved_config': config}
            and all(r['config_hash'] == canonical(config) for r in batch), 'matrix journal identity')
    stages = [(c, s) for c in ORDER for s in ('collect', 'replay')]
    completed, intended, intervals, index = [], [], {}, 1
    for condition, stage in stages:
        if index >= len(batch) or batch[index]['kind'] != 'stage_intent':
            break
        expected = {'condition': condition, 'stage': stage}
        require(batch[index]['data'] == expected, 'fixed matrix intent order')
        require((matrix / (condition + '-' + stage + '.log')).is_file(), 'worker output retained')
        intended.append(expected)
        started_at = batch[index]['wall_time']
        index += 1
        if index < len(batch) and batch[index]['kind'] == 'stage_complete':
            require(batch[index]['data'] == expected, 'fixed matrix completion order')
            intervals[(condition, stage)] = started_at, batch[index]['wall_time']
            completed.append(expected)
            index += 1
        else:
            break
    tail = batch[index:]
    require(not tail or len(tail) == 1 and tail[0]['kind'] in ('failure', 'termination'), 'no retry or extra matrix stage')
    successful = bool(tail and tail[0]['kind'] == 'termination')
    if successful:
        require(len(completed) == 8 and tail[0]['data'] == {'reason': 'all_four_fixed_cells_and_replays_complete',
            'fresh_policy_episodes': 4, 'verification_replays': 4, 'winner_selected': False, 'task_success_claim': False}, 'complete fixed matrix')
    if conditions is None:
        require(bool(tail), 'matrix must be closed for final audit')
        conditions = [c for c in ORDER if (matrix / c / 'episodes.jsonl').exists()]
    cells = [audit_cell(matrix, c, preflight, source, closed) for c in conditions]
    for cell in cells:
        interval = intervals.get((cell['condition'], 'collect'))
        if interval is not None:
            start, end = cell['collection_wall_times']
            require(interval[0] <= start <= end <= interval[1], 'collection enclosed in its fresh worker stage')
    launch_path = matrix.with_name(matrix.name + '-launch.json')
    exit_path = matrix.with_name(matrix.name + '-exit.json')
    launcher = None
    if launch_path.exists():
        launched = read(launch_path)
        require(launched['code'] == preflight['code'] and launched['preflight_sha256'] == request['preflight_sha256']
                and launched['review_sha256'] == request['review_sha256'] and launched['no_retry'], 'launch identity')
        require(launched['command'][0] == '/home/junhongli/miniforge3/envs/laya-embodied/bin/python'
                and launched['environment'] == {**preflight['environment'], 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'},
                'literal archived runtime launcher')
        launcher = {'launch_sha256': sha(launch_path), 'interpreter': launched['command'][0], 'started_utc': launched['started_utc']}
        if exit_path.exists():
            exited = read(exit_path)
            require(exited['code'] == preflight['code'] and exited['no_retry'], 'driver exit identity')
            if successful:
                require(exited['returncode'] == 0, 'completed matrix driver return code')
            launcher.update(exit_sha256=sha(exit_path), driver_returncode=exited['returncode'], completed_utc=exited['completed_utc'])
    closeout_path = matrix.with_name(matrix.name + '-execution-closeout.json')
    if closeout_path.exists():
        closeout = read(closeout_path)
        require(closeout['code_commit'] == preflight['code']['commit'] and closeout['code_dirty_status'] == ''
                and closeout['physics_retried'] is False, 'execution closeout code/no-retry identity')
        require(closeout['matrix_termination'] == batch[-1]['data'] and closeout['matrix_subprocess_returncode'] == 0,
                'closed matrix/driver agreement')
        for name, digest in closeout['artifacts'].items():
            require(sha(matrix / name) == digest, 'closeout matrix artifact hash')
        for condition in closeout['conditions']:
            for name, digest in condition['sha256'].items():
                require(sha(matrix / name) == digest, 'closeout condition artifact hash')
            audited = next((c for c in cells if c['condition'] == condition['condition']), None)
            if audited is not None:
                require(condition['descriptive_stored_labels_not_independent_audit'] == {
                    'bottle_center_rise_mm': audited['lift_motion']['bottle_center_delta_mm'][2],
                    'bottle_bottom_rise_mm': audited['lift_motion']['bottle_bottom_delta_mm'],
                    'endpoint_lift_bilateral_count': audited['lift_bilateral_endpoints']}, 'closeout descriptive values')
        launcher.update(execution_closeout_sha256=sha(closeout_path),
                        outer_tool_session_final_exit_code=closeout['outer_tool_session_final_exit_code'],
                        outer_tool_session_stdout_driver_returncode=closeout['outer_tool_session_stdout_driver_returncode'],
                        launcher_status_discrepancy_retained=closeout['launcher_status_discrepancy_retained'])
    return {'status': 'PASS', 'freeze': preflight['code']['commit'], 'raw_directory': str(matrix),
            'request_sha256': sha(matrix / 'request.json'), 'matrix_journal_sha256': sha(matrix / 'episodes.jsonl'),
            'preflight_sha256': request['preflight_sha256'], 'review_sha256': request['review_sha256'],
            'source_audit_sha256': AUDIT_SHA, 'matrix_outcome': 'all_four_complete' if successful else 'failed' if tail else 'in_progress',
            'launcher': launcher,
            'intended_stages': intended, 'completed_stages': completed,
            'first_matrix_failure': tail[0] if tail and tail[0]['kind'] == 'failure' else None,
            'unstarted_conditions': [c for c in ORDER if not any(s['condition'] == c for s in intended)],
            'conditions': cells, 'local_witnesses': local_witnesses(cells),
            'limits': ['stored journal/array/scalar checks only; no physics, rendering, model, FK or projection',
                       'approach evidence reused by byte-exact full scientific prefix and closed independent audit; zero membership recomputation',
                       'fresh child processes supported by reviewed subprocess code, worker argv and stage ordering; no standalone PID records',
                       'raw contact and strict >0.05 N samples are distinct; cached native time is not continuous contact onset',
                       'center/bottom are evaluator fields; bottle rotation remains unknown without a recorded source-specific qpos mapping',
                       'bilateral contact plus center rise does not establish clean mechanism, support-free retention or full task success']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--condition', choices=ORDER, action='append')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt = audit_matrix(args.matrix, args.condition)
    args.output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': receipt['status'], 'matrix_outcome': receipt['matrix_outcome'],
        'conditions': [{k: c.get(k) for k in ('condition', 'outcome', 'suffix', 'lift_motion', 'lift_bilateral_endpoints')}
                       for c in receipt['conditions']], 'local_witnesses': receipt['local_witnesses']}, indent=2))
