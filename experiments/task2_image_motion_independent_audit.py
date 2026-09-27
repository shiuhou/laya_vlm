"""Independent saved-row/image-motion arithmetic audit; no tracker or physical execution."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

NATIVE = ('frame', 'status', 'point_pixel_index_xy', 'attempted_backward_point_pixel_index_xy',
          'forward_status', 'backward_status', 'forward_backward_residual_px', 'forward_patch_error', 'backward_patch_error')
FRAME = ('condition', 'anchor', 'arm', 'capture_id', 'phase', 'after_step', 'control',
         'source_capture_stream', 'source_capture_seq', 'artifact', 'artifact_sha256',
         'capture_read_sim_time_s', 'cached_geometry_sample_time_s', 'exact_observation_sample_time_s',
         'tcp_read_sim_time_s', 'tcp_source_field', 'own_source', 'own_tcp_world_m')
KEYS = (*NATIVE, *FRAME, 'seed_id', 'seed_pixel_index_xy')
METRICS = ('rgb_delta_v_px', 'rgb_delta_norm_px', 'rgb_minus_tcp_delta_v_px', 'rgb_minus_tcp_delta_norm_px')
ORDER = ('whole-close', 'whole-open_hold', 'neck-close', 'neck-open_hold')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def near(a, b, tolerance=1e-12):
    if a is None or b is None:
        assert a is None and b is None
    else:
        assert np.allclose(a, b, rtol=0, atol=tolerance)


def valid_xy(row):
    xy = row['point_pixel_index_xy']
    return xy if row['status'] in ('seeded', 'native_status_ok') and xy is not None and len(xy) == 2 and all(map(math.isfinite, xy)) else None


def projection_check(row, frame, saved):
    """Independent scalar check of the saved own-TCP projection, not a feature extraction run."""
    tcp = row['own_tcp_world_m']
    if tcp is None:
        expected = 'missing_own_tcp'
    elif len(tcp) != 3 or not all(map(math.isfinite, tcp)):
        expected = 'nonfinite_or_invalid_own_tcp'
    else:
        k, t = frame['intrinsics'], frame['camera_to_world']
        camera = [sum(t[j, i] * (tcp[j] - t[j, 3]) for j in range(3)) for i in range(3)]
        if camera[2] <= 0:
            expected = 'nonpositive_camera_z'
        else:
            h = [sum(k[i, j] * camera[j] for j in range(3)) for i in range(3)]
            xy = [h[0] / h[2] - .5, h[1] / h[2] - .5]
            expected = 'available' if all(map(math.isfinite, xy)) else 'nonfinite_projection'
            if expected == 'available':
                near(xy, saved['index_xy'], 1e-10)
    assert saved['status'] == expected
    if expected != 'available':
        assert saved['index_xy'] is None


def audit(root):
    raw = root / 'runs/autonomous-research'
    run = raw / 'task2-point-anchor-image-motion-run-01'
    source = raw / 'task2-point-anchor-retention-transfer-run-01'
    manifest, config, seal = read(run / 'manifest.json'), read(run / 'resolved_config.yaml'), read(run / 'sensor-seal.json')
    assert manifest['code']['commit'] == '6e379ce604e9cb7b026ff7b3cc910d1bcdd7534a' and manifest['code']['dirty_status'] == ''
    assert sha(run / 'review.json') == manifest['review_sha256'] == '528705d65ddf1fc1ea2b772984a2b8d10fd7c09ee85ad6f518ad839d6445dbe5'
    assert sha(run / 'protocol.md') == config['protocol_sha256'] == 'c14a1d0f33c52de4aefb57cce370ee71bcdc6ad604dc951e17a5140237a79bd4'
    assert config['input_whitelist'] == list(KEYS) and config['seed_count'] == 492 and config['metrics'] == list(METRICS)
    assert manifest['runtime']['executable'] == '/home/junhongli/miniforge3/envs/locateanything/bin/python'
    for name, digest in config['source_sha256'].items():
        assert sha(source / name) == digest
    for name, digest in seal['sha256'].items():
        assert sha(run / name) == digest
    artifacts = read(run / 'artifacts.json')
    for name, digest in artifacts.items():
        assert sha(run / name) == digest
    journal = [json.loads(line) for line in (run / 'episodes.jsonl').read_text().splitlines()]
    assert journal[0]['kind'] == 'run_start' and journal[0]['data'] == {'manifest': manifest, 'resolved_config': config}
    assert [r['kind'] for r in journal] == ['run_start'] + ['cell_complete'] * 4 + ['termination']
    assert journal[-1]['data'] == {'reason': 'all_image_motion_rows_sealed', 'retries': 0, 'rows': 91512,
                                 'tracks': 1968, 'sensor_seal_sha256': sha(run / 'sensor-seal.json')}
    assert seal['complete'] and seal['rows'] == 91512 and seal['tracks'] == 1968
    assert not seal['measured_scene_depth_used'] and not seal['old_3D_joined'] and not seal['evaluator_read']
    summary = read(run / 'image-motion-summary.json')
    assert summary['holding'] is None and summary['identity_verified'] is None
    assert not summary['measured_scene_depth_used'] and not summary['old_3D_joined']
    totals, checked = Counter(), {}
    for cell_index, (condition, count) in enumerate(zip(ORDER, (47, 47, 46, 46))):
        reference = count - 17
        assert config['frame_counts'][condition] == count
        assert journal[cell_index + 1]['data'] == {'condition': condition, 'rows': 492 * count, 'tracks': 492}
        with (source / (condition + '-tracks.jsonl')).open() as stream:
            originals = [json.loads(line) for line in stream]
        with (run / (condition + '-features.jsonl')).open() as stream:
            features = [json.loads(line) for line in stream]
        assert len(originals) == len(features) == count * 492
        for i, row in enumerate(features[:count]):
            path = raw / 'task2-point-anchor-grasp-transfer-run-01' / condition / row['artifact']
            assert sha(path) == row['artifact_sha256']
            with np.load(path, allow_pickle=False) as f:
                projection_check(row, {k: f[k] for k in ('intrinsics', 'camera_to_world')}, row['own_tcp_image_projection'])
            totals['saved_projection_checks'] += 1
        values = [{k: [] for k in METRICS} for _ in range(count)]
        availability = [Counter() for _ in range(count)]
        for number, (original, row) in enumerate(zip(originals, features)):
            seed, capture = divmod(number, count)
            assert (row['seed_id'], row['capture_id']) == (seed, capture)
            assert set(row) == set(KEYS) | {'own_tcp_image_projection', 'image_motion', 'identity_verified', 'holding'}
            assert {k: row[k] for k in KEYS} == {k: original[k] for k in KEYS}
            assert row['own_tcp_image_projection'] == features[capture]['own_tcp_image_projection']
            assert {k: row[k] for k in FRAME} == {k: features[capture][k] for k in FRAME}
            assert row['identity_verified'] is None and row['holding'] is None
            ref = features[seed * count + reference]
            dp = dq = residual = None
            status_a = status_b = 'before_preclose'
            xy, base_xy = valid_xy(row), valid_xy(ref)
            if xy is not None:
                availability[capture]['native_admitted_count'] += 1
            if capture >= reference:
                if xy is not None and base_xy is not None:
                    dp = [x - y for x, y in zip(xy, base_xy)]
                status_a = 'available' if dp is not None else 'native_current_or_reference_unavailable'
                q, q0 = row['own_tcp_image_projection']['index_xy'], ref['own_tcp_image_projection']['index_xy']
                if q is not None and q0 is not None:
                    dq = [x - y for x, y in zip(q, q0)]
                status_b = status_a if dp is None else 'own_projection_current_or_reference_unavailable'
                if dp is not None and dq is not None:
                    residual = [x - y for x, y in zip(dp, dq)]
                    status_b = 'available'
            motion = row['image_motion']
            assert motion['reference_capture_id'] == reference and motion['status_A'] == status_a and motion['status_B'] == status_b
            assert motion['rgb_delta_xy_px'] == dp and motion['tcp_delta_xy_px'] == dq and motion['rgb_minus_tcp_delta_xy_px'] == residual
            expected = [None if dp is None else dp[1], None if dp is None else math.hypot(*dp),
                        None if residual is None else residual[1], None if residual is None else math.hypot(*residual)]
            for metric, val in zip(METRICS, expected):
                near(motion['metrics'][metric], val)
                if val is not None:
                    values[capture][metric].append(motion['metrics'][metric])
            availability[capture]['A_available_count'] += status_a == 'available'
            availability[capture]['B_available_count'] += status_b == 'available'
            totals['rows_checked'] += 1
            totals['A_available_rows'] += status_a == 'available'
            totals['B_available_rows'] += status_b == 'available'
        assert len(summary['cells'][condition]) == count
        for i, exported in enumerate(summary['cells'][condition]):
            assert exported['capture_id'] == i and exported['reference_capture_id'] == reference and exported['denominator'] == 492
            for key in ('native_admitted_count', 'A_available_count', 'B_available_count'):
                assert exported[key] == availability[i][key]
            for metric, vals in values[i].items():
                expected = {'count': len(vals), 'missing_count': 492 - len(vals), 'median': None, 'q25': None, 'q75': None,
                            'min': min(vals) if vals else None, 'max': max(vals) if vals else None}
                if vals:
                    q25, median, q75 = np.percentile(vals, [25, 50, 75]).tolist()
                    expected.update(q25=q25, median=median, q75=q75)
                assert exported['metrics'][metric] == expected
            totals['capture_summaries_checked'] += 1
        checked[condition] = {'rows': len(features), 'tracks': 492, 'reference_capture_id': reference,
            'all_whitelisted_source_fields_exact': True, 'all_A_B_vectors_nulls_and_metrics_checked': True,
            'all_fixed_denominator_summaries_exact': True,
            'checkpoints': {label: summary['cells'][condition][i] for label, i in
                (('initial', 0), ('preclose', reference), ('postclose_or_hold', count - 9), ('postlift', count - 1))}}
    return {'status': 'PASS', 'freeze': manifest['code']['commit'], 'raw_directory': str(run),
        'sensor_seal_sha256': sha(run / 'sensor-seal.json'), 'journal_sha256': sha(run / 'episodes.jsonl'),
        'artifacts_sha256': sha(run / 'artifacts.json'), 'summary_sha256': sha(run / 'image-motion-summary.json'),
        'totals': dict(totals), 'cells': checked, 'metric_check_absolute_tolerance_px': 1e-12,
        'independent_saved_projection_check_absolute_tolerance_px': 1e-10,
        'old_3D_joined_in_feature_outputs': False, 'new_LK_FK_physics_render_model_calls': 0,
        'interpretation': 'All conditions and rows retained. B uses calibrated own state; pixels are not metres or world vertical; no holding or identity claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cells'}, indent=2))
