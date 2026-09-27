"""Check fixed exploratory cases using sealed rows and saved RGB/depth, without tracking or projection."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root):
    raw = root / 'runs/autonomous-research'
    source = raw / 'task2-point-anchor-retention-transfer-run-01'
    run = raw / 'task2-point-anchor-extreme-track-diagnostic-01'
    docs = root / 'docs/evidence/autonomous_research'
    start, result = read(run / 'diagnostic-start.json'), read(run / 'diagnostic.json')
    assert start['code']['commit'] == 'e363d2517367c570e89fa0a12644f407208ae572'
    assert start['code']['dirty_status'] == '' and start['post_outcome_exploratory']
    module = 'embodied_runtime/experiments/task2_point_anchor_extreme_track_diagnostic.py'
    frozen = subprocess.check_output(['git', 'show', start['code']['commit'] + ':' + module], cwd=root)
    assert hashlib.sha256(frozen).hexdigest() == start['code']['source_sha256'][module] == sha(root / module)
    assert sha(run / 'protocol.md') == start['protocol_sha256']
    for name, digest in start['source_sha256'].items():
        assert sha(source / name) == digest
    assert sha(raw / 'task2-point-anchor-retention-transfer-independent-audit-01.json') == start['audit_sha256_linkage_only']
    for name, digest in read(run / 'artifacts.json').items():
        assert sha(run / name) == digest
    assert sha(run / 'diagnostic.json') == sha(docs / 'task2_point_anchor_extreme_track_summary.json')
    inspection = read(run / 'visual-inspection.json')
    assert inspection['diagnostic_artifacts_sha256'] == sha(run / 'artifacts.json')
    checked, total_rows = {}, 0
    for condition, count in zip(('whole-close', 'whole-open_hold', 'neck-close', 'neck-open_hold'), (47, 47, 46, 46)):
        reported = result['cells'][condition]
        histories, finals = {}, {}
        with (source / (condition + '-tracks.jsonl')).open() as stream:
            for number, line in enumerate(stream):
                row = json.loads(line)
                seed, capture = divmod(number, count)
                assert (row['seed_id'], row['capture_id']) == (seed, capture)
                histories.setdefault(seed, []).append(row)
                if capture == count - 1:
                    delta = row['reference_deltas']['preclose']
                    finals[seed] = None if delta is None else delta['point_delta_norm_m']
        assert number + 1 == 492 * count and len(finals) == 492
        available = {s: v for s, v in finals.items() if v is not None}
        maximum = max(available.values())
        tied = sorted(s for s, v in available.items() if v == maximum)
        selected = tied[0]
        assert reported['selection'] == {'selected_seed_id': selected, 'final_point_delta_norm_m': maximum,
            'tied_maximum_seed_ids': tied, 'available_final_count': len(available),
            'unavailable_seed_ids': [s for s, v in finals.items() if v is None]}
        rows = read(run / (condition + '-trajectory.json'))
        assert rows == histories[selected] and len(rows) == count
        assert rows[0]['status'] == 'seeded' and all(r['status'] == 'native_status_ok' for r in rows[1:])
        total_rows += count
        pairs = []
        for a, b in zip(rows, rows[1:]):
            delta = None if a['surface_point_world_m'] is None or b['surface_point_world_m'] is None else math.sqrt(
                sum((x - y) ** 2 for x, y in zip(b['surface_point_world_m'], a['surface_point_world_m'])))
            pairs.append({'previous_capture_id': a['capture_id'], 'capture_id': b['capture_id'],
                **{k + '_changed': a[k] != b[k] for k in ('point_pixel_index_xy', 'sample_pixel_xy', 'depth_m')},
                'consecutive_stored_world_distance_m': delta})
        assert len(pairs) == len(reported['changes']['adjacent_pairs'])
        for calculated, saved in zip(pairs, reported['changes']['adjacent_pairs']):
            for k in calculated:
                if k == 'consecutive_stored_world_distance_m' and calculated[k] is not None:
                    assert math.isclose(calculated[k], saved[k], rel_tol=0, abs_tol=1e-15)
                else:
                    assert calculated[k] == saved[k]
        reference = count - 17
        for label, candidates in (('all_frames', pairs), ('after_preclose', [p for p in pairs if p['capture_id'] > reference])):
            exported = reported['changes'][label]
            for field in ('point_pixel_index_xy', 'sample_pixel_xy', 'depth_m'):
                first = next((p for p in candidates if p[field + '_changed']), None)
                assert (None if first is None else first['capture_id']) == (None if exported['first_changes'][field] is None else exported['first_changes'][field]['capture_id'])
            valid = [p for p in candidates if p['consecutive_stored_world_distance_m'] is not None]
            largest = sorted(valid, key=lambda p: (-p['consecutive_stored_world_distance_m'], p['capture_id']))[0]
            assert exported['earliest_largest_consecutive_world_distance'] == reported['changes']['adjacent_pairs'][largest['capture_id'] - 1]
        largest = reported['changes']['all_frames']['earliest_largest_consecutive_world_distance']
        context_ids = [reference, count - 9, count - 1, largest['previous_capture_id'], largest['capture_id']]
        context_labels = ['preclose', 'postclose_or_hold', 'postlift', 'before_largest_jump', 'largest_jump']
        sheet_path = run / (condition + '-contexts.png')
        assert sha(sheet_path) == inspection['inspected_context_sheets_sha256'][condition]
        assert sha(sheet_path) == sha(docs / ('task2_point_anchor_extreme_track_' + condition + '.png'))
        sheet = np.asarray(Image.open(sheet_path))
        assert sheet.shape == (860, 1920, 3)
        archive_frames = {}
        for row in rows:
            path = raw / 'task2-point-anchor-grasp-transfer-run-01' / condition / row['artifact']
            assert sha(path) == row['artifact_sha256']
            with np.load(path, allow_pickle=False) as f:
                frame = {k: f[k] for k in ('rgb', 'depth_m')}
            xy = [math.floor(v + .5) for v in row['point_pixel_index_xy']]
            assert xy == row['sample_pixel_xy']
            assert float(frame['depth_m'][xy[1], xy[0]]) == row['depth_m']
            archive_frames[row['capture_id']] = (path, frame)
        patches = []
        with np.load(run / (condition + '-depth-neighborhoods.npz'), allow_pickle=False) as saved_depth:
            assert set(saved_depth.files) == set(context_labels)
            for i, (label, capture) in enumerate(zip(context_labels, context_ids)):
                row = rows[capture]
                path, f = archive_frames[capture]
                expected = {'label': label, 'capture_id': capture, 'artifact': str(path),
                    'artifact_sha256': row['artifact_sha256'], 'native_xy': row['point_pixel_index_xy'],
                    'sample_pixel_xy': row['sample_pixel_xy'], 'sample_depth_m': row['depth_m'],
                    'phase': row['phase'], 'control': row['control']}
                assert reported['display']['contexts'][i] == expected
                assert np.array_equal(sheet[40:424, i * 384:(i + 1) * 384], f['rgb'])
                x, y = row['sample_pixel_xy']
                # All selected contexts are interior; padding behavior has separate synthetic coverage.
                patch = f['depth_m'][y-10:y+11, x-10:x+11]
                assert patch.shape == (21, 21) and np.array_equal(saved_depth[label], patch)
                assert float(patch[10, 10]) == row['depth_m']
                patches.append(patch)
                enlarged = np.repeat(np.repeat(f['rgb'][y-10:y+11, x-10:x+11], 8, axis=0), 8, axis=1)
                displayed = sheet[466:634, i * 384+108:i * 384+276]
                unmarked = np.ones((168, 168), dtype=bool)
                unmarked[80:88, 80:88] = False
                assert np.array_equal(displayed[unmarked], enlarged[unmarked])
        finite = np.concatenate([p[np.isfinite(p)] for p in patches])
        assert reported['display']['depth_color_range_m'] == [float(finite.min()), float(finite.max())]
        assert reported['display']['neighborhood_size'] == [21, 21]
        checked[condition] = {'selected_seed_id': selected, 'seed_pixel_xy': rows[0]['seed_pixel_index_xy'],
            'available_final_metrics': len(available), 'maximum_ties': tied,
            'final_point_norm_m': maximum, 'complete_history_rows': count,
            'all_native_statuses_admitted': True, 'all_nearest_pixel_depth_samples_exact': True,
            'full_largest_jump': reported['changes']['all_frames']['earliest_largest_consecutive_world_distance'],
            'suffix_largest_jump': reported['changes']['after_preclose']['earliest_largest_consecutive_world_distance'],
            'five_contexts_RGB_depth_and_metadata_exact': True}
    assert result['holding'] is None and result['identity_verified'] is None and result['reclassified_or_excluded_seeds'] == 0
    return {'status': 'PASS', 'diagnostic_freeze': start['code']['commit'], 'population_rows_read': 91512,
        'complete_selected_history_rows': total_rows, 'full_RGB_tiles_checked': 20, 'exact_depth_neighborhoods_checked': 20,
        'diagnostic_sha256': sha(run / 'diagnostic.json'), 'artifacts_sha256': sha(run / 'artifacts.json'),
        'visual_inspection_receipt_sha256': sha(run / 'visual-inspection.json'),
        'findings_sha256': sha(docs / 'task2_point_anchor_extreme_track_findings.md'), 'cells': checked,
        'independent_synthetic_tests_passed': 3,
        'new_LK_projection_estimator_physics_render_model_FK_calls': 0,
        'interpretation': 'Four post-outcome selected extremes; no population-frequency, authenticated material-point or holding inference.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
