"""One reviewed stored-only four-cell transfer of the frozen descriptive LK estimator."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np

from . import task2_point_anchor_retention_adapter as adapter
from .records import RunRecorder, code_identity, file_hash, jsonable

base, association = adapter.base, adapter.association
SOURCE = base.RAW/'task2-point-anchor-grasp-transfer-run-01'
OUTPUT = base.RAW/'task2-point-anchor-retention-transfer-run-01'
SOURCE_RECEIPT = base.RAW/'task2-point-anchor-grasp-rgb-inspection-01/source-admission.json'
SOURCE_RECEIPT_SHA = '6d283ad5d098ea1e532e82aaf95464df796a01a1cce05e96dd9dae1a9e969681'
RAW_REVIEW = Path('/home/junhongli/projects/laya-information-boundary-review/docs/evidence/autonomous_research/task2_point_anchor_grasp_transfer_independent_audit.json')
RAW_REVIEW_SHA = '6051e9a498f73e8399b232a2d64b9a0174e8e0ab8d3187cffdb69a4c31a9a018'
ADAPTER_SHA = '59c5c6bcb6198cbc3f7d94bfd09b91aa515a0f82ab14b82e53c2eb55483694f2'
PROTOCOL = base.ROOT/'docs/research/task2_point_anchor_retention_transfer_protocol.md'
ENVIRONMENT = {
    'executable': '/home/junhongli/miniforge3/envs/locateanything/bin/python',
    'python': '3.10.21 | packaged by conda-forge | (main, Aug 21 2026, 22:42:31) [GCC 14.4.0]',
    'opencv': '4.11.0', 'numpy': '1.26.4', 'opencv_threads': 256,
    'opencv_build_sha256': 'f3f58b60f58039df358dceb98f617583025ea7b080b4b3b5c84cc15ef13edf09',
}
FRAME_COUNTS = dict(zip(adapter.CONDITIONS, (47, 47, 46, 46)))
TOTAL_TRACKS, TOTAL_ROWS = 1968, 91512
PREFIXES = (('whole-close', 'whole-open_hold', 31),
            ('neck-close', 'neck-open_hold', 30), ('whole-close', 'neck-close', 6))


def environment(cv2):
    observed = {'executable': sys.executable, 'python': sys.version,
        'opencv': cv2.__version__, 'numpy': np.__version__, 'opencv_threads': cv2.getNumThreads(),
        'opencv_build_sha256': hashlib.sha256(cv2.getBuildInformation().encode()).hexdigest()}
    if observed != ENVIRONMENT:
        raise ValueError('frozen extraction interpreter/OpenCV/NumPy/thread provenance differs')
    return observed


def load_inputs():
    """Admit completed sensor sources; raw mechanical review is hash linkage only."""
    for path, digest in ((SOURCE_RECEIPT, SOURCE_RECEIPT_SHA), (RAW_REVIEW, RAW_REVIEW_SHA),
                         (adapter.__file__, ADAPTER_SHA)):
        if file_hash(path) != digest:
            raise ValueError('frozen source admission, raw closure or adapter changed')
    receipt = json.loads(SOURCE_RECEIPT.read_text())
    if (receipt['matrix'] != str(SOURCE)
            or file_hash(SOURCE/'episodes.jsonl') != receipt['matrix_journal_sha256']
            or receipt['matrix_termination'] != {'fresh_policy_episodes': 4,
                'reason': 'all_four_fixed_cells_and_replays_complete', 'task_success_claim': False,
                'verification_replays': 4, 'winner_selected': False}):
        raise ValueError('complete fixed matrix linkage required')
    seeds, packets, admission = adapter.load_inputs(SOURCE, receipt['admission']['source_sha256'])
    if (admission != receipt['admission']
            or {c: len(p['frames']) for c, p in packets.items()} != FRAME_COUNTS
            or sum(admission['rows_per_cell'].values()) != TOTAL_ROWS):
        raise ValueError('completed source admission or full schedule differs')
    admission = {**admission, 'source_receipt_sha256': SOURCE_RECEIPT_SHA,
        'matrix_journal_sha256': receipt['matrix_journal_sha256'],
        'raw_review_sha256_linkage_only': RAW_REVIEW_SHA}
    return seeds, packets, admission


def preflight(output):
    import cv2
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('clean committed extraction freeze required')
    runtime = environment(cv2)
    _, _, admission = load_inputs()
    base.write_json(output, {'status': 'pass', 'code': identity, 'environment': runtime,
        'protocol_sha256': file_hash(PROTOCOL), 'lk_settings': base.lk.LK_SETTINGS,
        'convention_check': association.convention_check(cv2), 'admission': admission,
        'total_tracks': TOTAL_TRACKS, 'total_track_rows': TOTAL_ROWS,
        'archived_tracking_projection_displacement_computed': False,
        'LK_model_physics_render_calls': 0})
    print('PASS: completed sensor sources and synthetic coordinates only; no archived features.')


def admit_run(preflight_path, review_path, cv2):
    identity, runtime = code_identity(), environment(cv2)
    receipt = json.loads(Path(preflight_path).read_text())
    review = json.loads(Path(review_path).read_text())
    if (identity['dirty_status'] or identity != receipt['code'] or receipt['status'] != 'pass'
            or receipt['environment'] != runtime or receipt['protocol_sha256'] != file_hash(PROTOCOL)
            or receipt['lk_settings'] != jsonable(base.lk.LK_SETTINGS)
            or receipt['total_tracks'] != TOTAL_TRACKS or receipt['total_track_rows'] != TOTAL_ROWS
            or receipt['archived_tracking_projection_displacement_computed'] is not False
            or receipt['LK_model_physics_render_calls'] != 0
            or review.get('status') != 'pass' or review.get('freeze_commit') != identity['commit']
            or review.get('preflight_sha256') != file_hash(preflight_path)
            or review.get('protocol_sha256') != file_hash(PROTOCOL)
            or review.get('authorized_batches') != 1):
        raise ValueError('clean exact freeze, source-only preflight and independent one-batch PASS required')
    seeds, packets, admission = load_inputs()
    if admission != receipt['admission']:
        raise ValueError('source admission differs from reviewed preflight')
    return identity, runtime, seeds, packets, admission


def write_prefixes(output, tracks):
    summaries = []
    with (output/'prefix-agreement.jsonl').open('x') as stream:
        for left, right, count in PREFIXES:
            disagreements = []
            for seed_id in range(adapter.SEED_COUNT):
                a, b = tracks[left][seed_id], tracks[right][seed_id]
                disagreements.extend(adapter.prefix_disagreements(a, b, count))
                for i in range(count):
                    equal = {k: a[i][k] == b[i][k] for k in adapter.prior.NATIVE_FIELDS}
                    stream.write(json.dumps({'left': left, 'right': right, 'seed_id': seed_id,
                        'capture_id': i, 'native_fields_equal': equal, 'exact_agreement': all(equal.values())})+'\n')
            summaries.append({'left': left, 'right': right, 'captures': count,
                'compared_rows': adapter.SEED_COUNT*count,
                'compared_native_fields': adapter.prior.NATIVE_FIELDS,
                'exact_agreement': not disagreements, 'disagreements': disagreements})
        stream.flush()
        os.fsync(stream.fileno())
    base.write_json(output/'prefix-summary.json', {'comparisons': summaries,
        'total_compared_rows': sum(p['compared_rows'] for p in summaries), 'uses_masks': False})
    return summaries


def execute(output, identity, runtime, seeds, packets, admission, preflight_path, review_path, cv2):
    """Production run after admission; tests replace only the source/tracker with synthetic data."""
    output = Path(output)
    recorder = RunRecorder(output, {'protocol_sha256': file_hash(PROTOCOL),
        'lk_settings': base.lk.LK_SETTINGS, 'seed_count': adapter.SEED_COUNT,
        'captures_per_cell': FRAME_COUNTS, 'reference': 'preclose',
        'sampling_convention': association.CONVENTION, 'holding': None},
        {'run_id': output.name, 'code': identity, 'environment': runtime,
         'preflight_sha256': file_hash(preflight_path), 'review_sha256': file_hash(review_path)})
    completed, row_count, active = 0, 0, None
    try:
        for source, name in ((PROTOCOL, 'protocol.md'), (preflight_path, 'preflight.json'),
                             (review_path, 'review.json'), (SOURCE_RECEIPT, 'source-admission.json')):
            (output/name).write_bytes(Path(source).read_bytes())
        base.write_json(output/'admission.json', admission)
        recorder.record('input_admitted', {'sha256': file_hash(output/'admission.json')})
        all_tracks, summaries = {}, {}
        for condition in adapter.CONDITIONS:
            trajectories = []
            active = condition
            with (output/f'{condition}-tracks.jsonl').open('x') as stream:
                for rows in adapter.iter_cell_tracks(packets[condition], seeds, cv2):
                    seed_id = len(trajectories)
                    if (seed_id >= adapter.SEED_COUNT or len(rows) != FRAME_COUNTS[condition]
                            or [(r['seed_id'], r['capture_id']) for r in rows]
                            != [(seed_id, i) for i in range(FRAME_COUNTS[condition])]):
                        raise ValueError('complete ordered fixed seed/capture rows required')
                    for row in rows:
                        stream.write(json.dumps(jsonable(row), allow_nan=False)+'\n')
                        row_count += 1
                    stream.flush()
                    os.fsync(stream.fileno())
                    trajectories.append(rows)
                    completed += 1
                    if len(trajectories) % 64 == 0:
                        print(f'{condition}: {len(trajectories)}/492 tracks complete', flush=True)
            summaries[condition] = adapter.summarize_tracks(trajectories, packets[condition])
            all_tracks[condition] = trajectories
            recorder.record('cell_tracks_complete', {'condition': condition,
                'tracks': len(trajectories), 'rows': sum(map(len, trajectories))})
        if completed != TOTAL_TRACKS or row_count != TOTAL_ROWS:
            raise ValueError('complete four-cell population required')
        base.write_json(output/'sensor-summary.json', {'holding': None, 'identity_verified': None,
            'proxy_membership_available': False, 'reference': 'preclose', 'cells': summaries})
        prefix = write_prefixes(output, all_tracks)
        artifacts = {p.name: file_hash(p) for p in sorted(output.iterdir())
                     if p.is_file() and p.name != 'episodes.jsonl'}
        base.write_json(output/'sensor-seal.json', {'sha256': artifacts, 'complete': True,
            'tracks': completed, 'rows': row_count, 'evaluator_read': False})
        recorder.record('sensor_outputs_sealed', {'sha256': file_hash(output/'sensor-seal.json')})
        if any(not p['exact_agreement'] for p in prefix):
            raise ValueError('causal native-prefix disagreement; complete batch retained; no repair/retry')
        recorder.record('termination', {'reason': 'all_four_cells_sealed', 'tracks': completed,
            'rows': row_count, 'model_physics_render_calls': 0, 'retries': 0, 'holding': None})
    except BaseException as exc:
        # The context manager has closed/flushed any partially written track file.
        partial = {p.name: file_hash(p) for p in sorted(output.iterdir())
                   if p.is_file() and p.name != 'episodes.jsonl'}
        base.write_json(output/'failure.json', {'reason': repr(exc), 'active_condition': active,
            'completed_tracks': completed, 'written_rows': row_count, 'retained_sha256': partial,
            'complete_sensor_seal_present': (output/'sensor-seal.json').exists(), 'retries': 0})
        recorder.record('failure', {'receipt_sha256': file_hash(output/'failure.json'),
            'completed_tracks': completed, 'written_rows': row_count, 'retries': 0})
        raise
    finally:
        recorder.close()
        base.write_json(output/'artifacts.json', {p.name: file_hash(p)
            for p in sorted(output.iterdir()) if p.is_file() and p.name != 'artifacts.json'})


def run(output, preflight_path, review_path):
    import cv2
    if Path(output).resolve() != OUTPUT or OUTPUT.exists():
        raise ValueError('one new registered output directory required; no retry/resume')
    admitted = admit_run(preflight_path, review_path, cv2)
    execute(output, *admitted, preflight_path, review_path, cv2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'run'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight')
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.mode == 'preflight':
        preflight(args.output)
    else:
        if not args.preflight or not args.review:
            parser.error('run requires --preflight and --review')
        run(args.output, args.preflight, args.review)
