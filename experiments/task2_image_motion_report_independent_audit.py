"""Verify post-seal report copies and joins; do not recompute image-motion features."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


NATIVE = ('frame', 'status', 'point_pixel_index_xy', 'attempted_backward_point_pixel_index_xy',
          'forward_status', 'backward_status', 'forward_backward_residual_px',
          'forward_patch_error', 'backward_patch_error')
METADATA = ('phase', 'control', 'source_capture_stream', 'source_capture_seq',
            'capture_read_sim_time_s', 'tcp_read_sim_time_s',
            'cached_geometry_sample_time_s', 'exact_observation_sample_time_s')
CELLS = (('whole-close', 47, 3), ('whole-open_hold', 47, 11),
         ('neck-close', 46, 3), ('neck-open_hold', 46, 17))
REPORT_CODE_SHA = '455d58898bbe582bd3a43ba4f9b5a91897e37230f14bb1b376ab0f2c0f2e7f88'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_rows(path, count, seed):
    first, selected = [], []
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['seed_id'] == 0:
                first.append(row)
            if row['seed_id'] == seed:
                selected.append(row)
    assert len(first) == len(selected) == count
    assert [row['capture_id'] for row in first] == list(range(count))
    assert [row['capture_id'] for row in selected] == list(range(count))
    return first, selected


def audit(root, report_code):
    raw = root / 'runs/autonomous-research'
    new = raw / 'task2-point-anchor-image-motion-run-01'
    old = raw / 'task2-point-anchor-retention-transfer-run-01'
    report = new / 'report'
    assert sha(report_code) == REPORT_CODE_SHA
    assert sha(new / 'sensor-seal.json') == '6524ae13db399bed62e5c7fa66ec7bff65e88bf448b85778298ef5ecdb69d777'
    assert sha(old / 'sensor-seal.json') == '39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60'
    for directory in (new, old):
        for name, digest in read(directory / 'sensor-seal.json')['sha256'].items():
            assert sha(directory / name) == digest
    assert sha(old / 'sensor-summary.json') == 'ec4c112458ecd5ed84f90a45408f65eb8a43fe6c17b32174ad3596b76f6935d8'
    artifacts = read(report / 'artifacts.json')
    assert set(artifacts) == {'fixed-extreme-representation-traces.png', 'image-motion-curves.png',
                              'portable-comparison.json', 'report-start.json'}
    for name, digest in artifacts.items():
        assert sha(report / name) == digest
    assert read(report / 'report-start.json') == {
        'new_sensor_seal_sha256': sha(new / 'sensor-seal.json'),
        'source_journal_sha256': sha(new / 'episodes.jsonl'),
        'new_features_complete_before_old_3D_read': True,
        'report_code_sha256': REPORT_CODE_SHA}
    image_summary = read(new / 'image-motion-summary.json')
    old_summary = read(old / 'sensor-summary.json')
    portable = read(report / 'portable-comparison.json')
    assert set(portable) == {'source_path', 'new_sensor_seal_sha256', 'old_3D_sensor_seal_sha256',
        'old_3D_summary_sha256', 'post_seal_old_3D_join', 'feature_recomputation', 'cells',
        'identity_verified', 'holding', 'all_seeds_retained'}
    assert portable['source_path'] == str(new)
    assert portable['new_sensor_seal_sha256'] == sha(new / 'sensor-seal.json')
    assert portable['old_3D_sensor_seal_sha256'] == sha(old / 'sensor-seal.json')
    assert portable['old_3D_summary_sha256'] == sha(old / 'sensor-summary.json')
    assert portable['post_seal_old_3D_join'] and not portable['feature_recomputation']
    assert portable['all_seeds_retained'] and portable['identity_verified'] is None and portable['holding'] is None
    assert set(portable['cells']) == {cell for cell, _, _ in CELLS}
    checked = {}
    for condition, count, seed in CELLS:
        first, selected = selected_rows(new / (condition + '-features.jsonl'), count, seed)
        _, old_selected = selected_rows(old / (condition + '-tracks.jsonl'), count, seed)
        cell = portable['cells'][condition]
        assert set(cell) == {'image_motion_curves', 'stored_3D_curves', 'reference_capture_id',
                            'fixed_exploratory_seed', 'fixed_exploratory_trajectory', 'checkpoints'}
        assert cell['reference_capture_id'] == count - 17 and cell['fixed_exploratory_seed'] == seed
        assert len(cell['image_motion_curves']) == len(cell['fixed_exploratory_trajectory']) == count
        assert cell['stored_3D_curves'] == old_summary['cells'][condition]
        for i in range(count):
            expected = dict(image_summary['cells'][condition][i])
            expected.update({key: first[i][key] for key in METADATA})
            expected['own_tcp_image_projection'] = first[i]['own_tcp_image_projection']
            expected['tcp_image_delta_xy_px'] = first[i]['image_motion']['tcp_delta_xy_px']
            assert cell['image_motion_curves'][i] == expected
            current, prior = selected[i], old_selected[i]
            for key in ('seed_id', 'capture_id', *NATIVE):
                assert current[key] == prior[key]
            assert cell['fixed_exploratory_trajectory'][i] == {
                'seed_id': seed, 'capture_id': i, 'image_motion': current['image_motion'],
                'stored_3D_reference_delta': prior['reference_deltas']['preclose']}
        indices = {'initial': 0, 'preclose': count - 17, 'postclose_or_hold': count - 9, 'postlift': count - 1}
        assert set(cell['checkpoints']) == set(indices)
        for label, i in indices.items():
            assert cell['checkpoints'][label] == {'image': cell['image_motion_curves'][i],
                                                  'stored_3D': old_summary['cells'][condition][i]}
        checked[condition] = {'curves_and_metadata_checked': count, 'old_summary_rows_exact': count,
            'fixed_seed': seed, 'joined_history_rows_exact': count, 'four_checkpoints_exact': True,
            'final_metrics': cell['image_motion_curves'][-1]['metrics'],
            'final_tcp_image_delta_xy_px': cell['image_motion_curves'][-1]['tcp_image_delta_xy_px'],
            'final_exploratory_row': cell['fixed_exploratory_trajectory'][-1]}
    return {'status': 'PASS', 'report_code_sha256': REPORT_CODE_SHA,
        'report_artifacts_sha256': sha(report / 'artifacts.json'), 'report_artifacts': artifacts,
        'all_186_new_summary_rows_metadata_and_old_summary_rows_exact': True,
        'all_186_fixed_history_joins_exact': True, 'all_16_checkpoints_exact': True,
        'cells': checked, 'feature_recomputation': False,
        'scope': 'Exact report copies/joins plus artifact hashes. New feature arithmetic and old 3D estimator have separate closed audits. Code ordering and actual figures reviewed separately.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report-code', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.report_code)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'cells'}, indent=2))
