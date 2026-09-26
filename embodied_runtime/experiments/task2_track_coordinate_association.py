"""One same-track pixel-association comparison; no tracking or sensor repair."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

import numpy as np

from ..vision import camera_to_world, pixel_to_camera
from . import task2_box_temporal_probe as base
from .records import RunRecorder, code_identity, file_hash

SOURCE = base.RAW/'task2-box-temporal-run-01'
PROTOCOL = base.ROOT/'docs/research/task2_track_coordinate_association_protocol.md'
BASE_SHA = '655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50'
SOURCE_HASHES = {
    'episodes.jsonl': '0e7bd76d3f6b11244729bc767ec1b1f9a2625aa6069e494adf9743ea5900cf05',
    'sensor-seal.json': 'bae9793115ededab12b6b5bca242af9cdb0c2ed8c1e8d62219af3bbce65cc30b',
    'close-tracks.jsonl': '158e2d376d30450e1e2903a0abf793bb71a3a9a2327055b58aabf49965721f37',
    'open_hold-tracks.jsonl': '5c80ab6500b0ccc7ce7009fff9b364c76c4a7fcc3534aef454704f67f83c41d0',
    'sensor-summary.json': '4b46a6bddaa87b545de1f6d5f31e1aa6f77836e9b904fe5e71877cd47d6ce933',
}
CONVENTION = 'nearest_center_index_floor_xy_plus_half'


def nearest_index(xy):
    """Integer array-index centers; exact +half ties choose the higher index."""
    return np.floor(np.asarray(xy, dtype=float)+.5).astype(int)


def convention_check(cv2):
    """Synthetic coordinates only: no archived track/image or LK invocation."""
    grid = np.arange(25, dtype=np.float32).reshape(5, 5)
    observed = float(cv2.getRectSubPix(grid, (1, 1), (2., 2.))[0, 0])
    if observed != float(grid[2, 2]):
        raise ValueError('OpenCV integer-center premise contradicted')
    cases = [([2., 2.], [2, 2]), ([2.-1e-4, 2.+1e-4], [2, 2]),
             ([2.+1e-4, 2.-1e-4], [2, 2]), ([1.4999, 2.5001], [1, 3]),
             ([1.5001, 2.4999], [2, 2]), ([1.5, 2.5], [2, 3]),
             ([-.5001, -.4999], [-1, 0])]
    for coordinate, expected in cases:
        if nearest_index(coordinate).tolist() != expected:
            raise ValueError('analytic nearest-center symmetry failed')
    return {'status': 'pass', 'cv2_version': cv2.__version__, 'integer_center_value': observed,
            'array_index_value': float(grid[2, 2]), 'cases': cases,
            'installed_getRectSubPix_documentation': cv2.getRectSubPix.__doc__,
            'archived_features_computed': False, 'LK_calls': 0}


def nearest_surface_sample(row, frame):
    if row['status'] not in base.ACCEPTED:
        return {'sample_pixel_xy': None, 'depth_m': None, 'surface_point_world_m': None,
                'depth_status': 'RGB_track_not_admitted'}
    x, y = nearest_index(row['point_pixel_index_xy'])
    h, w = frame['depth_m'].shape
    if not (0 <= x < w and 0 <= y < h):
        return {'sample_pixel_xy': None, 'depth_m': None, 'surface_point_world_m': None,
                'depth_status': 'outside_image'}
    z = float(frame['depth_m'][y, x])
    valid = np.isfinite(z) and .01 <= z <= 5.
    xyz = camera_to_world(pixel_to_camera(x+.5, y+.5, z, frame['intrinsics']), frame['camera_to_world']) if valid else None
    return {'sample_pixel_xy': [int(x), int(y)], 'depth_m': z if np.isfinite(z) else None,
            'surface_point_world_m': None if xyz is None else xyz.tolist(),
            'depth_status': 'valid' if valid else 'outside_valid_range' if np.isfinite(z) else 'nonfinite'}


def reassociate_track(original, packet):
    """Copy all native fields/statuses unchanged, replace only association/deltas."""
    rows = copy.deepcopy(original)
    for row, frame in zip(rows, packet['frames'], strict=True):
        row.update(nearest_surface_sample(row, frame), sampling_convention=CONVENTION)
    for i, row in enumerate(rows):
        row['reference_deltas'] = {
            name: base.reference_delta(row['surface_point_world_m'], rows[j]['surface_point_world_m'],
                                       packet['tcps'][i], packet['tcps'][j]) if i >= j else None
            for name, j in base.REFERENCES.items()}
    return rows


def inputs():
    if file_hash(base.__file__) != BASE_SHA:
        raise ValueError('frozen original analysis helper changed')
    for name, digest in SOURCE_HASHES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('sealed original rows changed')
    tracks = base.sealed_tracks(SOURCE)
    seeds, packets, admission = base.load_inputs()
    for arm in base.ARMS:
        expected = [(s, i) for s in range(492) for i in range(46)]
        if [(r['seed_id'], r['capture_id']) for r in tracks[arm]] != expected:
            raise ValueError('complete ordered original rows required')
        if any(r['seed_pixel_index_xy'] != seeds[r['seed_id']] for r in tracks[arm]):
            raise ValueError('source seed identity differs')
    return tracks, packets, admission


def preflight(output):
    import cv2
    check = convention_check(cv2)
    if cv2.__version__ != base.lk.CV2_VERSION:
        raise ValueError('OpenCV version differs')
    _, _, admission = inputs()
    base.write_json(output, {'status': 'pass', 'code': code_identity(), 'python': sys.executable,
        'protocol_sha256': file_hash(PROTOCOL), 'convention_check': check,
        'source_hashes': SOURCE_HASHES, 'admission': admission, 'track_rows': 45264,
        'archived_association_outcomes_computed': False, 'LK_model_physics_render_calls': 0})
    print('PASS: synthetic coordinate contract and source-only preflight; no archived reassociation.')


def run(output, preflight_path, review):
    identity = code_identity()
    p = json.loads(Path(preflight_path).read_text())
    text = Path(review).read_text()
    if identity['dirty_status'] or identity != p['code'] or identity['commit'] not in text or 'PASS' not in text:
        raise ValueError('clean matching preflight and independent PASS required')
    if p['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('protocol changed')
    old, packets, admission = inputs()
    if admission != p['admission']:
        raise ValueError('input admission changed')
    recorder = RunRecorder(output, {'protocol_sha256': file_hash(PROTOCOL), 'convention': CONVENTION,
        'historical_baseline': 'unchanged sealed floor rows', 'source_hashes': SOURCE_HASHES},
        {'run_id': Path(output).name, 'code': identity, 'python': sys.executable,
         'preflight_sha256': file_hash(preflight_path), 'review_sha256': file_hash(review)})
    output = Path(output)
    completed = 0
    try:
        (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        (output/'review.md').write_bytes(Path(review).read_bytes())
        base.write_json(output/'admission.json', admission)
        summaries, changes = {}, {}
        for arm in base.ARMS:
            trajectories = []
            changes[arm] = [{'capture_id': i, 'denominator': 492, 'changed_sample_pixel_count': 0,
                             'changed_depth_value_count': 0} for i in range(46)]
            with (output/f'{arm}-tracks.jsonl').open('x') as stream:
                for seed_id in range(492):
                    original = old[arm][seed_id*46:(seed_id+1)*46]
                    for row, frame in zip(original, packets[arm]['frames'], strict=True):
                        baseline = base.surface_sample(row, frame)
                        if any(row[k] != v for k, v in baseline.items()):
                            raise ValueError('original floor association does not reproduce')
                    rows = reassociate_track(original, packets[arm])
                    for a, b in zip(original, rows, strict=True):
                        c = changes[arm][a['capture_id']]
                        c['changed_sample_pixel_count'] += a['sample_pixel_xy'] != b['sample_pixel_xy']
                        c['changed_depth_value_count'] += a['depth_m'] != b['depth_m']
                        stream.write(json.dumps(b, allow_nan=False)+'\n')
                    stream.flush()
                    trajectories.append(rows)
                    completed += 1
            summaries[arm] = base.summarize_tracks(trajectories, 492)
            recorder.record('arm_association_complete', {'arm': arm, 'rows': 22632, 'native_fields_unchanged': True})
        base.write_json(output/'sensor-summary.json', {'holding': None, 'references': base.REFERENCES, 'arms': summaries})
        base.write_json(output/'same-track-changes.json', {'arms': changes, 'LK_calls': 0,
            'source_floor_summary_sha256': SOURCE_HASHES['sensor-summary.json']})
        artifacts = {name: file_hash(output/name) for name in ('close-tracks.jsonl', 'open_hold-tracks.jsonl',
                                                              'sensor-summary.json', 'same-track-changes.json')}
        base.write_json(output/'sensor-seal.json', {'sha256': artifacts, 'evaluator_read': False})
        recorder.record('sensor_outputs_sealed', {'artifact': 'sensor-seal.json', 'sha256': file_hash(output/'sensor-seal.json')})
        recorder.record('termination', {'reason': 'all_associations_sealed', 'tracks': completed,
                                       'LK_model_physics_render_calls': 0, 'retries': 0})
    except Exception as exc:
        recorder.record('failure', {'reason': repr(exc), 'completed_tracks': completed, 'retries': 0})
        raise
    finally:
        recorder.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'run', 'evaluate'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight')
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.mode == 'preflight':
        preflight(args.output)
    elif args.mode == 'run':
        if not args.preflight or not args.review:
            parser.error('run requires preflight and review')
        run(args.output, args.preflight, args.review)
    else:
        base.evaluate(args.output)
