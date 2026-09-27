"""Prepare one additional fixed GRASP interval at both original POINT approaches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import task2_point_anchor_grasp_transfer as prior
from .records import file_hash, load_records

VERSION = 'task2-fixed-additional-stationary-grasp-v1'
MODULE = 'embodied_runtime.experiments.task2_additional_stationary_grasp'
PROTOCOL = prior.base.ROOT / 'docs/research/task2_additional_stationary_grasp_protocol.md'
ORDER = ('whole-close', 'neck-close')
SCHEDULE = (('close_or_hold', 'GRASP'), ('additional_close', 'GRASP'), ('lift', 'MV_UP'))
SOURCE = prior.base.RAW / 'task2-point-anchor-grasp-transfer-run-01'
AUDIT = Path('/home/junhongli/projects/laya-embodied-runtime/docs/evidence/autonomous_research/task2_point_anchor_grasp_transfer_independent_audit.json')
AUDIT_SHA = '6051e9a498f73e8399b232a2d64b9a0174e8e0ab8d3187cffdb69a4c31a9a018'
SOURCE_FREEZE = '1702cb2739bfdb2817a329c8047e16bcb7836657'


def closed_source():
    if file_hash(AUDIT) != AUDIT_SHA:
        raise ValueError('Exact independent four-cell source audit required')
    audit = prior.base.read(AUDIT)
    if (audit['status'] != 'PASS' or audit['freeze'] != SOURCE_FREEZE or audit['matrix_outcome'] != 'all_four_complete'
            or audit['matrix_journal_sha256'] != file_hash(SOURCE / 'episodes.jsonl')
            or [row['condition'] for row in audit['conditions']] != list(prior.ORDER)):
        raise ValueError('All four closed one-GRASP/open control cells required')
    hashes = {'episodes.jsonl': audit['matrix_journal_sha256']}
    for row in audit['conditions']:
        name = row['condition']
        hashes.update({name + '/episodes.jsonl': row['journal_sha256'],
            name + '/evaluator-only/labels.json': row['sensor_evidence']['labels_sha256'],
            name + '/sensor-seal.json': row['sensor_evidence']['sensor_seal_sha256'],
            name + '-replay/result.json': row['replay']['result_sha256'],
            name + '-replay/auxiliary-result.json': row['replay']['auxiliary_result_sha256']})
    for name, expected in hashes.items():
        if file_hash(SOURCE / name) != expected:
            raise ValueError('Closed one-GRASP comparison source changed: ' + name)
    return {'audit_path': str(AUDIT), 'audit_sha256': AUDIT_SHA, 'directory': str(SOURCE),
        'sha256': hashes, 'source_freeze': SOURCE_FREEZE, 'comparators_retained': list(prior.ORDER)}


def prepare(args):
    if args.condition not in ORDER:
        raise ValueError('Both fixed close anchors only; no extra open-control dynamics')
    frozen, point, frame = prior.prepare(args)
    frozen['transfer'] = {**frozen['transfer'], 'version': VERSION, 'order': list(ORDER),
        'base_transfer_protocol_sha256': frozen['protocol_sha256'], 'scripted_tokens': [x[1] for x in SCHEDULE],
        'scripted_phases': [x[0] for x in SCHEDULE], 'scripted_control_count': 24, 'auxiliary_control_captures': 24,
        'extra_GRASP_intervals': 1, 'first_GRASP_prefix_is_verification_only': True,
        'source_admission': {**frozen['transfer']['source_admission'], 'one_GRASP_comparison': closed_source()}}
    frozen['protocol_sha256'] = file_hash(PROTOCOL)
    return frozen, point, frame


def verify_first_grasp(recorder, condition, offset, step):
    """No source control is executed: compare completed first GRASP, then permit fixed continuation."""
    if offset != 0:
        return
    source = SOURCE / condition
    actual, errors = load_records(recorder.output / 'episodes.jsonl')
    original, old_errors = load_records(source / 'episodes.jsonl')
    if errors or old_errors or any(row['kind'] in ('failure', 'intervention_failure') for row in actual + original):
        raise ValueError('Clean current and closed first-GRASP prefix required')
    boundary = next((i for i, row in enumerate(original) if row['kind'] == 'endpoint'
        and row['data'].get('native_phase') == 'close_or_hold'), None)
    if boundary is None:
        raise ValueError('Closed source first-GRASP endpoint missing')
    expected = original[:boundary + 1]
    a = [row for row in actual if row['kind'] != 'run_start']
    b = [row for row in expected if row['kind'] != 'run_start']
    if (len(a) != len(b) or not a or a[-1]['kind'] != 'endpoint'
            or a[-1]['data'].get('step') != step or a[-1]['data'].get('native_phase') != 'close_or_hold'):
        raise ValueError('Complete exact first-GRASP prefix boundary required')
    image_count = 0
    for new, old in zip(a, b):
        if new['kind'] != old['kind']:
            raise ValueError('First-GRASP prefix kind mismatch')
        left, right = new['data'], old['data']
        if new['kind'] in ('vision_capture', 'auxiliary_capture'):
            for directory, row in ((recorder.output, left), (source, right)):
                if file_hash(directory / row['artifact']) != row['artifact_sha256']:
                    raise ValueError('First-GRASP prefix image hash mismatch')
            with np.load(recorder.output / left['artifact'], allow_pickle=False) as frame:
                with np.load(source / right['artifact'], allow_pickle=False) as reference:
                    prior.base.require_exact_frame(frame, reference)
            left = {k: v for k, v in left.items() if k != 'artifact_sha256'}
            right = {k: v for k, v in right.items() if k != 'artifact_sha256'}
            image_count += 1
        if left != right:
            raise ValueError('First-GRASP prefix data mismatch: ' + new['kind'])
    recorder.record('first_GRASP_prefix_verified', {'condition': condition, 'source_journal_sha256': file_hash(source / 'episodes.jsonl'),
        'exact_records': len(a), 'exact_image_captures': image_count, 'completed_first_GRASP_step': step,
        'source_state_restored': False, 'archived_controls_used': False,
        'next_token': 'GRASP', 'selection': 'prospectively_fixed_additional_interval'})


def intervention(condition):
    if condition not in ORDER:
        raise ValueError('Only both fixed close anchors are registered')
    return prior.Intervention(condition, schedule=SCHEDULE,
        after_primitive=lambda recorder, offset, step: verify_first_grasp(recorder, condition, offset, step))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--review')
    parser.add_argument('--preflight-receipt')
    parser.add_argument('--run-matrix', action='store_true')
    parser.add_argument('--worker-stage', choices=('collect', 'replay'))
    parser.add_argument('--matrix')
    parser.add_argument('--condition', choices=ORDER, default=ORDER[0])
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.worker_stage:
        if not args.matrix:
            parser.error('worker requires matrix')
        prior.worker(args, preflight_fn=prepare, protocol=PROTOCOL, intervention_factory=intervention, auxiliary_count=24)
    elif args.run_matrix:
        if not all((args.output, args.review, args.preflight_receipt)):
            parser.error('matrix requires output, reviewed preflight receipt and prospective review')
        prior.run_matrix(args, preflight_fn=prepare, protocol=PROTOCOL, module=MODULE, order=ORDER, version=VERSION,
            scripted_action_count=3, completion_reason='both_fixed_additional_GRASP_cells_and_replays_complete')
    else:
        if not args.output:
            parser.error('no-world preflight requires output')
        frozen, _, _ = prepare(args)
        prior.approach.write(args.output, {**frozen, 'physics_calls': 0, 'physical_execution_admitted': False,
            'pending_gate': 'prospective_review_of_exact_freeze_and_this_preflight_receipt'})
        print(json.dumps({'preflight': 'passed', 'world_constructed': False, 'physical_execution_admitted': False}))


if __name__ == '__main__':
    main()
