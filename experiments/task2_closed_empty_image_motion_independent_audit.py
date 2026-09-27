"""Stored-only complete post-event A/B row audit; never executes LK or physics."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

import task2_image_motion_independent_audit as old
from task2_point_anchor_approach_evidence_audit import load_journal, canonical

read, sha, near = old.read, old.sha, old.near
SEEDS = [[x, y] for y in range(169, 210) for x in range(212, 224)]
ENDPOINTS = {'postevent_preclose': 0, 'close1': 8, 'close2_prelift': 16, 'postlift': 24}


def native_audit(row, previous, seed):
    if row['frame'] == 0:
        assert row['status'] == 'seeded' and row['point_pixel_index_xy'] == seed
        assert all(row[k] is None for k in old.NATIVE if k not in ('frame', 'status', 'point_pixel_index_xy'))
        return
    if previous['status'] in ('native_failure', 'unknown_after_native_failure'):
        assert row['status'] == 'unknown_after_native_failure'
        assert all(row[k] is None for k in old.NATIVE if k not in ('frame', 'status'))
        return
    xy, back = row['point_pixel_index_xy'], row['attempted_backward_point_pixel_index_xy']
    for point in (xy, back):
        assert point is None or len(point) == 2 and all(map(math.isfinite, point))
    fs, bs = row['forward_status'], row['backward_status']
    assert fs in (None, 0, 1) and bs in (None, 0, 1)
    if fs != 1 or xy is None:
        assert bs is None and back is None and row['backward_patch_error'] is None
    alive = xy is not None and back is not None and fs == bs == 1
    assert row['status'] == ('native_status_ok' if alive else 'native_failure')
    residual = (float(np.linalg.norm(np.asarray(back, np.float32) - np.asarray(previous['point_pixel_index_xy'], np.float32)))
                if back is not None and bs == 1 else None)
    near(row['forward_backward_residual_px'], residual)
    for status, key in ((fs, 'forward_patch_error'), (bs, 'backward_patch_error')):
        if status != 1:
            assert row[key] is None
        assert row[key] is None or math.isfinite(row[key])


def audit(run):
    manifest, config, seal = [read(run / name) for name in ('manifest.json', 'resolved_config.yaml', 'sensor-seal.json')]
    assert manifest['code']['commit'] == '9891aa5ced02cf7b9924f582c221faeb8f400fa8' and manifest['code']['dirty_status'] == ''
    expected_hashes = {'review.json': '7cf3c5fe4ad415fad2a786fa0ff81269362a4e5c75db3ca3f7d5b779d25e867a',
        'binding.json': '49dbc6e182a6e516e43142537005234c7559264fd69c9f051a10e1b7b4f4d04f',
        'preflight.json': 'a2c641097eead7c51a8b992461b593abe10ca4cb8bcc07bc169ed7b8c531f8a8',
        'protocol.md': '94f6fb26b633665d77c7ffdec7863dfab5d31a6c9d285167f39b315523f31232'}
    assert all(sha(run / name) == digest for name, digest in expected_hashes.items())
    assert manifest['review_sha256'] == expected_hashes['review.json'] and manifest['binding_sha256'] == expected_hashes['binding.json']
    assert manifest['preflight_sha256'] == expected_hashes['preflight.json']
    assert config == {'protocol_sha256': expected_hashes['protocol.md'], 'reference': 0, 'seeds': SEEDS,
        'captures_per_cell': 25, 'lk_settings': {'winSize': [21, 21], 'maxLevel': 3, 'criteria': [3, 30, .01], 'flags': 0, 'minEigThreshold': .0001},
        'endpoints': ENDPOINTS}
    preflight, binding, admission = [read(run / name) for name in ('preflight.json', 'binding.json', 'admission.json')]
    assert admission == preflight['admission'] and admission['binding'] == binding
    assert manifest['code'] == preflight['code'] and manifest['runtime'] == preflight['environment']
    assert binding['source_admission_status'] == 'observational-source-qualified' and binding['original_matrix_status'] == 'interrupted_incomplete'
    for key in ('source_admission', 'source_review'):
        assert sha(Path(binding[key]['path'])) == binding[key]['sha256']
    source = Path(binding['source_root'])
    assert sha(source / 'episodes.jsonl') == binding['matrix_journal_sha256']
    artifact_hashes = read(run / 'artifacts.json')
    assert set(artifact_hashes) == {p.name for p in run.iterdir() if p.is_file() and p.name != 'artifacts.json'}
    assert all(sha(run / name) == digest for name, digest in artifact_hashes.items())
    assert set(seal['sha256']) == set(artifact_hashes) - {'episodes.jsonl', 'sensor-seal.json'}
    assert all(sha(run / name) == digest for name, digest in seal['sha256'].items())
    assert seal == {'sha256': seal['sha256'], 'complete': True, 'tracks': 984, 'rows': 24600,
                    'measured_scene_depth_read': False, 'evaluator_read': False}
    journal = load_journal(run / 'episodes.jsonl')
    assert all(r['config_hash'] == canonical(config) for r in journal)
    assert journal[0]['data'] == {'manifest': manifest, 'resolved_config': config}
    assert [r['kind'] for r in journal] == ['run_start', 'cell_complete', 'cell_complete', 'termination']
    assert journal[-1]['data'] == {'reason': 'all_postevent_image_motion_rows_sealed', 'tracks': 984, 'rows': 24600,
                                 'sensor_seal_sha256': sha(run / 'sensor-seal.json'), 'retries': 0}
    summary = read(run / 'sensor-summary.json')
    assert summary['reference_capture_id'] == 0 and summary['endpoints'] == ENDPOINTS
    assert summary['holding'] is summary['identity_verified'] is None and summary['mechanical_labels_joined'] is False
    assert set(summary['cells']) == {'present', 'away'}
    totals, cells = Counter(), {}
    for cell_index, role in enumerate(('present', 'away')):
        spec = binding['cells'][role]
        directory = source / spec['directory']
        assert all(sha(directory / name) == digest for name, digest in spec['sha256'].items())
        saved = read(directory / 'sensor-captures.json')[31:56]
        assert len(saved) == 25 and saved == admission['captures'][role]
        assert [r['capture_id'] for r in saved] == list(range(31, 56))
        assert saved[0]['phase'] == 'scene_after' and [r['source_capture_seq'] for r in saved] == [2, *range(1, 25)]
        rows = [json.loads(line) for line in (run / (role + '-tracks.jsonl')).read_text().splitlines()]
        assert len(rows) == 12300
        assert journal[cell_index + 1]['data'] == {'role': role, 'tracks': 492, 'rows': 12300}
        for i, meta in enumerate(saved):
            path = directory / meta['artifact']
            assert sha(path) == meta['artifact_sha256']
            with np.load(path, allow_pickle=False) as frame:
                old.projection_check(rows[i], {k: frame[k] for k in ('intrinsics', 'camera_to_world')}, rows[i]['own_tcp_image_projection'])
            totals['saved_projection_checks'] += 1
        values = [{k: [] for k in old.METRICS} for _ in range(25)]
        availability = [Counter() for _ in range(25)]
        for number, row in enumerate(rows):
            seed, capture = divmod(number, 25)
            assert (row['seed_id'], row['capture_id'], row['frame']) == (seed, capture, capture)
            assert row['seed_pixel_index_xy'] == SEEDS[seed]
            assert set(row) == set(old.KEYS) | {'own_tcp_image_projection', 'image_motion', 'identity_verified', 'holding'}
            assert {k: row[k] for k in old.FRAME} == {**{k: saved[capture][k] for k in old.FRAME}, 'capture_id': capture}
            assert row['own_tcp_image_projection'] == rows[capture]['own_tcp_image_projection']
            assert row['identity_verified'] is row['holding'] is None
            native_audit(row, rows[number - 1] if capture else None, SEEDS[seed])
            ref = rows[seed * 25]
            xy, base_xy = old.valid_xy(row), old.valid_xy(ref)
            dp = [x - y for x, y in zip(xy, base_xy)] if xy is not None and base_xy is not None else None
            q, q0 = row['own_tcp_image_projection']['index_xy'], ref['own_tcp_image_projection']['index_xy']
            dq = [x - y for x, y in zip(q, q0)] if q is not None and q0 is not None else None
            residual = [x - y for x, y in zip(dp, dq)] if dp is not None and dq is not None else None
            status_a = 'available' if dp is not None else 'native_current_or_reference_unavailable'
            status_b = status_a if dp is None else 'own_projection_current_or_reference_unavailable' if dq is None else 'available'
            motion = row['image_motion']
            assert motion['reference_capture_id'] == 0 and motion['status_A'] == status_a and motion['status_B'] == status_b
            assert motion['rgb_delta_xy_px'] == dp and motion['tcp_delta_xy_px'] == dq and motion['rgb_minus_tcp_delta_xy_px'] == residual
            expected = [None if dp is None else dp[1], None if dp is None else math.hypot(*dp),
                        None if residual is None else residual[1], None if residual is None else math.hypot(*residual)]
            for metric, value in zip(old.METRICS, expected):
                near(motion['metrics'][metric], value)
                if value is not None:
                    values[capture][metric].append(motion['metrics'][metric])
            for key, value in (('native_admitted_count', xy is not None), ('A_available_count', status_a == 'available'),
                               ('B_available_count', status_b == 'available'), ('native_failure_count', row['status'] == 'native_failure'),
                               ('unknown_after_failure_count', row['status'] == 'unknown_after_native_failure')):
                availability[capture][key] += value
            totals['rows_checked'] += 1
            totals['A_available_rows'] += status_a == 'available'
            totals['B_available_rows'] += status_b == 'available'
        assert len(summary['cells'][role]) == 25
        for i, exported in enumerate(summary['cells'][role]):
            assert exported['capture_id'] == i and exported['reference_capture_id'] == 0 and exported['denominator'] == 492
            assert all(exported[key] == value for key, value in availability[i].items())
            for metric, vals in values[i].items():
                expected = {'count': len(vals), 'missing_count': 492 - len(vals), 'median': None, 'q25': None, 'q75': None,
                            'min': min(vals) if vals else None, 'max': max(vals) if vals else None}
                if vals:
                    q25, median, q75 = np.percentile(vals, [25, 50, 75]).tolist()
                    expected.update(q25=q25, median=median, q75=q75)
                assert exported['metrics'][metric] == expected
            totals['capture_summaries_checked'] += 1
        cells[role] = {'tracks': 492, 'rows': len(rows), 'all_native_status_and_failure_carry_forward_checked': True,
            'all_bound_sensor_fields_exact': True, 'all_A_B_vectors_nulls_and_metrics_checked': True,
            'all_fixed_population_summaries_exact': True,
            'checkpoints': {label: summary['cells'][role][i] for label, i in ENDPOINTS.items()}}
    return {'status': 'PASS', 'freeze': manifest['code']['commit'], 'raw_directory': str(run),
        'sensor_seal_sha256': sha(run / 'sensor-seal.json'), 'journal_sha256': sha(run / 'episodes.jsonl'),
        'summary_sha256': sha(run / 'sensor-summary.json'), 'artifacts_sha256': sha(run / 'artifacts.json'),
        'totals': dict(totals), 'cells': cells, 'metric_check_absolute_tolerance_px': 1e-12,
        'independent_saved_projection_check_absolute_tolerance_px': 1e-10,
        'new_LK_FK_physics_render_model_calls': 0, 'independent_saved_scalar_projection_checks': 50,
        'limits': 'Stored numerical audit; native LK correspondence is not rerun. All original rows and failures retained. A is RGB displacement; B also uses calibrated own TCP. No identity, holding, classifier or task-success claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cells'}, indent=2))
