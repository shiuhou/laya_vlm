"""Stored-only audit of the registered additional-GRASP pair; no dynamics or geometry recomputation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import task2_point_anchor_grasp_transfer_evidence_audit as prior

ORDER = ('whole-close', 'neck-close')
SCHEDULE = (('close_or_hold', 'GRASP'), ('additional_close', 'GRASP'), ('lift', 'MV_UP'))
FREEZE = '945c96d81916f7952d9b40565c52b00085363544'
PREFLIGHT_SHA = '5a3d0c770aa7c4dbcfd90cf2517e4484a1aea130aa70f7b99e180176e8b4082e'
REVIEW_SHA = '0c884a05084e7bfbdab36e50d61997c35bc6d06b60555e68df816055b210b037'
SOURCE_FREEZE = '1702cb2739bfdb2817a329c8047e16bcb7836657'
SOURCE_AUDIT_SHA = '6051e9a498f73e8399b232a2d64b9a0174e8e0ab8d3187cffdb69a4c31a9a018'
require, read, sha = prior.require, prior.read, prior.sha


def source_admission(matrix):
    request = read(matrix / 'request.json')
    ref = request['source_admission']['one_GRASP_comparison']
    require(ref['audit_sha256'] == SOURCE_AUDIT_SHA == sha(ref['audit_path']), 'closed four-cell independent audit')
    closed = read(ref['audit_path'])
    require(closed['status'] == 'PASS' and closed['freeze'] == ref['source_freeze'] == SOURCE_FREEZE
            and closed['matrix_outcome'] == 'all_four_complete'
            and ref['comparators_retained'] == list(prior.ORDER), 'complete four-cell comparison retained')
    source = Path(ref['directory'])
    require(sha(source / 'episodes.jsonl') == closed['matrix_journal_sha256'], 'closed matrix hash')
    for name, digest in ref['sha256'].items():
        require(sha(source / name) == digest, 'closed source identity: ' + name)
    return source, closed


def first_grasp_check(source, closed, run, rows, approach_end):
    gates = [i for i, row in enumerate(rows) if row['kind'] == 'first_GRASP_prefix_verified']
    require(len(gates) <= 1, 'at most one first-GRASP prefix gate')
    if not gates:
        require(any(r['kind'] in ('failure', 'intervention_failure') for r in rows)
                and not any(r['kind'] == 'action_started' and r['data'].get('native_phase') in
                            ('additional_close', 'lift') for r in rows), 'no continuation without first-GRASP gate')
        return {'verified': False, 'added_interval_executed': False}
    old_cell = next(c for c in closed['conditions'] if c['condition'] == run.name)
    directory = source / run.name
    require(sha(directory / 'episodes.jsonl') == old_cell['journal_sha256'], 'closed first-GRASP source journal')
    original = prior.load_journal(directory / 'episodes.jsonl')
    boundary = next(i for i, r in enumerate(original) if r['kind'] == 'endpoint'
                    and r['data'].get('native_phase') == 'close_or_hold')
    expected = [r for r in original[:boundary + 1] if r['kind'] != 'run_start']
    actual = [r for r in rows[:gates[0]] if r['kind'] != 'run_start']
    require(len(actual) == len(expected) and actual[-1]['kind'] == 'endpoint', 'entire original first-GRASP prefix')
    images = 0
    for new, old in zip(actual, expected):
        require(new['kind'] == old['kind'], 'exact first-GRASP scientific record kind')
        a, b = new['data'], old['data']
        if new['kind'] in ('vision_capture', 'auxiliary_capture'):
            require(sha(run / a['artifact']) == a['artifact_sha256']
                    and sha(directory / b['artifact']) == b['artifact_sha256'], 'prefix artifact hashes')
            prior.arrays_equal(run / a['artifact'], directory / b['artifact'])
            a = {k: v for k, v in a.items() if k != 'artifact_sha256'}
            b = {k: v for k, v in b.items() if k != 'artifact_sha256'}
            images += 1
        require(a == b, 'full first-GRASP prefix exact: ' + new['kind'])
    require(rows[gates[0]]['data'] == {'condition': run.name,
        'source_journal_sha256': old_cell['journal_sha256'], 'exact_records': len(actual),
        'exact_image_captures': images, 'completed_first_GRASP_step': approach_end['completed_actions'],
        'source_state_restored': False, 'archived_controls_used': False, 'next_token': 'GRASP',
        'selection': 'prospectively_fixed_additional_interval'}, 'independent first-GRASP receipt')
    new_sensor, old_sensor = read(run / 'sensor-captures.json'), read(directory / 'sensor-captures.json')
    count = approach_end['completed_actions'] + 1 + 8
    require(sha(directory / 'sensor-captures.json') == old_cell['sensor_evidence']['sensor_manifest_sha256'],
            'closed original sensor manifest')
    for a, b in zip(new_sensor[:count], old_sensor[:count]):
        # capture_record_id includes each run's journal envelope. The shared
        # sensor audit binds it to the current journal; the closed audit binds
        # the original. Scientific stream IDs, times and own fields stay exact.
        require({k: v for k, v in a.items() if k not in ('artifact_sha256', 'capture_record_id')} ==
                {k: v for k, v in b.items() if k not in ('artifact_sha256', 'capture_record_id')},
                'first-GRASP sensor metadata prefix')
    require(len(new_sensor) >= count and len(old_sensor) >= count, 'complete first-GRASP sensor prefix')
    return {'verified': True, 'scientific_records': len(actual), 'image_captures': images,
            'merged_sensor_rows': count, 'source_journal_sha256': old_cell['journal_sha256'],
            'source_audit_sha256': SOURCE_AUDIT_SHA, 'archived_controls_used': False,
            'membership_recomputation': 0,
            'journal_envelope_capture_record_ids_bound_separately': True}


def joint_row(own):
    qpos, qvel = own['robot0_gripper_qpos'], own['robot0_gripper_qvel']
    require(len(qpos) == len(qvel) == 2, 'two saved signed joint coordinates and velocities')
    return {'qpos_m': qpos, 'qvel_m_s': qvel, 'signed_joint_separation_mm': (qpos[0] - qpos[1]) * 1000,
            'signed_joint_separation_rate_mm_s': (qvel[0] - qvel[1]) * 1000,
            'physical_pad_gap': None}


def describe_own_motion(matrix, cell):
    rows = prior.load_journal(matrix / cell['condition'] / 'episodes.jsonl')
    by = prior.grouped(rows)
    controls = {(r['data']['step'], r['data']['control']): r['data'] for r in by['control_completed']}
    starts = {(r['data']['step'], r['data']['control']): r['data'] for r in by['control_started']}
    actions, trajectory = [], []
    for row in by['action_completed']:
        a = row['data']
        if 'native_phase' not in a:
            continue
        step, result = a['step'], a['result']
        before = starts[(step, 0)]['previous_returned_own_observations']
        after = controls[(step, a['controls'] - 1)]['returned_own_observations']
        actions.append({'phase': a['native_phase'], 'step': step, 'token': a['token'],
            'tcp_delta_mm': (np.asarray(result['delta_m']) * 1000).tolist(),
            'tcp_translation_norm_mm': float(np.linalg.norm(result['delta_m']) * 1000),
            'rotation_change_deg': result['rotation_angle_deg'],
            'before_joints': joint_row(before), 'after_joints': joint_row(after)})
    for row in read(matrix / cell['condition'] / 'sensor-captures.json'):
        if row['phase'] in dict(SCHEDULE):
            trajectory.append({k: row[k] for k in ('capture_id', 'phase', 'after_step', 'control',
                'capture_read_sim_time_s', 'exact_observation_sample_time_s', 'own_source')}
                | {'tcp_world_m': row['own_observations']['robot0_eef_pos'], **joint_row(row['own_observations'])})
    return {'primitive_endpoints': actions, 'all_suffix_own_rows': trajectory,
            'joint_separation_is_physical_pad_gap': False, 'holding_inferred': False}


def audit(matrix, conditions=None):
    preflight = read(matrix / 'preflight.json')
    require(preflight['code']['commit'] == FREEZE and sha(matrix / 'preflight.json') == PREFLIGHT_SHA
            and sha(matrix / 'review.txt') == REVIEW_SHA, 'exact registered additional-GRASP admission')
    source, closed = source_admission(matrix)
    result = prior.audit_matrix(matrix, conditions, order=ORDER, schedule=SCHEDULE,
        first_grasp_check=lambda run, rows, end: first_grasp_check(source, closed, run, rows, end),
        completion_reason='both_fixed_additional_GRASP_cells_and_replays_complete')
    result['closed_four_cell_audit_sha256'] = SOURCE_AUDIT_SHA
    result['new_matched_close_open_witness'] = None
    result['comparison_scope'] = 'Two close cells with an added interval; original open controls lack that interval.'
    for cell in result['conditions']:
        if not cell.get('suffix'):
            continue
        manifest = read(matrix / cell['condition'] / 'manifest.json')
        transfer = manifest['transfer']
        require(transfer['version'] == 'task2-fixed-additional-stationary-grasp-v1'
                and transfer['scripted_phases'] == [p for p, _ in SCHEDULE]
                and transfer['extra_GRASP_intervals'] == 1
                and transfer['first_GRASP_prefix_is_verification_only'], 'fixed single additional interval')
        cell['own_motion'] = describe_own_motion(matrix, cell)
        endpoints = cell['endpoint_measurements']
        first = next((e for e in endpoints if e['phase'] == 'close_or_hold' and e['control'] == 7), None)
        second = next((e for e in endpoints if e['phase'] == 'additional_close' and e['control'] == 7), None)
        native = cell['native_contacts']['by_phase_and_stage']
        complete = cell['outcome'] == 'normal_complete'
        stages = {stage: native['lift/' + stage]['bilateral_pad_samples'] for stage in ('native_before', 'native_after')}
        cell['registered_prediction'] = {'first_GRASP_endpoint_bilateral': None if first is None else first['bilateral_pads'],
            'additional_GRASP_endpoint_bilateral': None if second is None else second['bilateral_pads'],
            'lift_bilateral_by_native_stage': stages,
            'prediction_satisfied': bool(second['bilateral_pads'] and all(n == 200 for n in stages.values())) if complete else None,
            'is_holding_classifier': False, 'support_free_retention': None, 'clean_interaction_valid_grasp': None}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--condition', choices=ORDER, action='append')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.matrix, args.condition)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'matrix_outcome': result['matrix_outcome'],
        'conditions': [{k: c.get(k) for k in ('condition', 'outcome', 'first_GRASP_prefix', 'suffix',
            'registered_prediction', 'lift_motion', 'lift_bilateral_endpoints')} for c in result['conditions']]}, indent=2))
