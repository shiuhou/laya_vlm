"""Independent stored-row audit; does not rerun tracking or read oracle labels."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

CELLS = {'whole-close': 47, 'whole-open_hold': 47, 'neck-close': 46, 'neck-open_hold': 46}
NATIVE = ('frame', 'status', 'point_pixel_index_xy', 'attempted_backward_point_pixel_index_xy',
          'forward_status', 'backward_status', 'forward_backward_residual_px',
          'forward_patch_error', 'backward_patch_error')
METRICS = ('point_delta_z_m', 'point_delta_norm_m', 'point_minus_tcp_delta_z_m', 'point_minus_tcp_delta_norm_m')


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close(actual, expected):
    if expected is None:
        assert actual is None
        return 0.0
    assert actual is not None
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    assert a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
    error = float(np.max(np.abs(a-b)))
    assert error <= 1e-12, (actual, expected)
    return error


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values)-1)*fraction
    low, high = math.floor(index), math.ceil(index)
    return values[low] + (values[high]-values[low])*(index-low)


def audit(output, source):
    seal = read(output/'sensor-seal.json')
    assert seal['complete'] and seal['tracks'] == 1968 and seal['rows'] == 91512
    assert seal['evaluator_read'] is False
    for name, digest in read(output/'artifacts.json').items():
        assert sha(output/name) == digest, name
    for name, digest in seal['sha256'].items():
        assert sha(output/name) == digest, name
    journal = [json.loads(line) for line in (output/'episodes.jsonl').read_text().splitlines()]
    assert journal[-1]['kind'] == 'termination'
    assert journal[-1]['data']['reason'] == 'all_four_cells_sealed'
    assert not any(r['kind'] == 'failure' for r in journal)
    admission = read(output/'admission.json')
    summary = read(output/'sensor-summary.json')
    assert summary['holding'] is None and summary['identity_verified'] is None
    assert summary['proxy_membership_available'] is False
    tracks, cells, max_projection_error, max_delta_error = {}, {}, 0., 0.
    for cell, count in CELLS.items():
        directory = source/cell
        for name, digest in admission['source_sha256'][cell].items():
            assert sha(directory/name) == digest
        captures = read(directory/'sensor-captures.json')
        assert len(captures) == count
        frames = []
        for capture in captures:
            path = directory/capture['artifact']
            assert sha(path) == capture['artifact_sha256']
            with np.load(path, allow_pickle=False) as data:
                frames.append({k: data[k].copy() for k in ('depth_m', 'intrinsics', 'camera_to_world')})
        rows = [json.loads(line) for line in (output/f'{cell}-tracks.jsonl').read_text().splitlines()]
        assert len(rows) == 492*count
        tracks[cell] = rows
        reference = count-17
        for index, row in enumerate(rows):
            seed, i = divmod(index, count)
            assert (row['seed_id'], row['capture_id'], row['frame']) == (seed, i, i)
            assert row['seed_pixel_index_xy'] == [212+seed % 12, 169+seed//12]
            assert row['identity_verified'] is None and row['holding'] is None
            assert row['sampling_convention'] == 'nearest_center_index_floor_xy_plus_half'
            assert all(row[k] == v for k, v in captures[i].items())
            frame, xy = frames[i], row['point_pixel_index_xy']
            expected, pixel, depth, status = None, None, None, 'RGB_track_not_admitted'
            if row['status'] in ('seeded', 'native_status_ok'):
                x, y = [math.floor(v+.5) for v in xy]
                height, width = frame['depth_m'].shape
                status = 'outside_image'
                if 0 <= x < width and 0 <= y < height:
                    pixel = [x, y]
                    value = float(frame['depth_m'][y, x])
                    depth = value if math.isfinite(value) else None
                    status = 'nonfinite' if depth is None else 'outside_valid_range'
                    if depth is not None and .01 <= depth <= 5.:
                        k, t = frame['intrinsics'], frame['camera_to_world']
                        camera = [(x+.5-k[0, 2])*depth/k[0, 0],
                                  (y+.5-k[1, 2])*depth/k[1, 1], depth]
                        expected = [sum(t[a, b]*camera[b] for b in range(3))+t[a, 3] for a in range(3)]
                        status = 'valid'
            assert row['sample_pixel_xy'] == pixel and row['depth_status'] == status
            close(row['depth_m'], depth)
            max_projection_error = max(max_projection_error, close(row['surface_point_world_m'], expected))
            baseline = rows[seed*count+reference]
            delta = row['reference_deltas']['preclose']
            refstatus = 'before_preclose' if i < reference else (
                'missing_own_tcp' if row['own_tcp_world_m'] is None or baseline['own_tcp_world_m'] is None else 'available')
            assert row['reference_status'] == refstatus
            if refstatus != 'available':
                assert delta is None
            else:
                dt = [a-b for a, b in zip(row['own_tcp_world_m'], baseline['own_tcp_world_m'])]
                max_delta_error = max(max_delta_error, close(delta['tcp_delta_m'], dt))
                xyz, origin = row['surface_point_world_m'], baseline['surface_point_world_m']
                if xyz is None or origin is None:
                    assert all(delta[k] is None for k in ('point_delta_m', 'point_minus_tcp_delta_m', *METRICS))
                else:
                    dp = [a-b for a, b in zip(xyz, origin)]
                    residual = [a-b for a, b in zip(dp, dt)]
                    values = {'point_delta_m': dp, 'point_minus_tcp_delta_m': residual,
                              'point_delta_z_m': dp[2], 'point_delta_norm_m': math.sqrt(sum(v*v for v in dp)),
                              'point_minus_tcp_delta_z_m': residual[2],
                              'point_minus_tcp_delta_norm_m': math.sqrt(sum(v*v for v in residual))}
                    for key, value in values.items():
                        max_delta_error = max(max_delta_error, close(delta[key], value))
        assert len(summary['cells'][cell]) == count
        for i, stored in enumerate(summary['cells'][cell]):
            group = rows[i::count]
            assert stored['capture_id'] == i and stored['denominator'] == 492
            for key, predicate in (
                ('native_surviving_count', lambda r: r['status'] in ('seeded', 'native_status_ok')),
                ('native_failure_count', lambda r: r['status'] == 'native_failure'),
                ('unknown_after_failure_count', lambda r: r['status'] == 'unknown_after_native_failure'),
                ('valid_surface_count', lambda r: r['surface_point_world_m'] is not None)):
                assert stored[key] == sum(predicate(r) for r in group)
            ref = stored['references']['preclose']
            assert ref['reference_capture_id'] == reference and ref['available'] == (i >= reference)
            expected_count = sum(r['surface_point_world_m'] is not None for r in rows[reference::count]) if i >= reference else None
            assert ref['reference_surface_valid_count'] == expected_count
            assert ref['reference_own_tcp_available'] == (captures[reference]['own_tcp_world_m'] is not None if i >= reference else None)
            for key in METRICS:
                values = [r['reference_deltas']['preclose'][key] for r in group
                          if r['reference_deltas']['preclose'] is not None and r['reference_deltas']['preclose'][key] is not None]
                stats = ref['metrics'][key]
                assert stats['count'] == len(values) and stats['missing_count'] == 492-len(values)
                for name, fraction in (('q25', .25), ('median', .5), ('q75', .75)):
                    close(stats[name], percentile(values, fraction) if values else None)
        cells[cell] = {'rows': len(rows), 'captures': count, 'final_summary': summary['cells'][cell][-1]}
    prefixes = [json.loads(line) for line in (output/'prefix-agreement.jsonl').read_text().splitlines()]
    assert len(prefixes) == 32964
    offset = 0
    for left, right, count in (('whole-close', 'whole-open_hold', 31), ('neck-close', 'neck-open_hold', 30), ('whole-close', 'neck-close', 6)):
        for seed in range(492):
            for i in range(count):
                row = prefixes[offset]
                offset += 1
                a, b = tracks[left][seed*CELLS[left]+i], tracks[right][seed*CELLS[right]+i]
                assert (row['left'], row['right'], row['seed_id'], row['capture_id']) == (left, right, seed, i)
                expected = {key: a[key] == b[key] for key in NATIVE}
                assert row['native_fields_equal'] == expected and all(expected.values()) and row['exact_agreement']
    return {'status': 'PASS', 'source_output': str(output.resolve()), 'source_sensor_seal_sha256': sha(output/'sensor-seal.json'),
            'source_artifacts_sha256': sha(output/'artifacts.json'), 'audit_script_sha256': sha(__file__),
            'rows_checked': 91512, 'prefix_rows_checked': offset, 'native_fields_per_prefix_row': 9,
            'max_projection_abs_error_m': max_projection_error, 'max_delta_abs_error_m': max_delta_error,
            'numerical_tolerance_m': 1e-12, 'LK_reexecuted': False, 'oracle_labels_read': False, 'cells': cells}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('source', type=Path)
    parser.add_argument('audit_output', type=Path)
    args = parser.parse_args()
    result = audit(args.output, args.source)
    with args.audit_output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cells'}))
