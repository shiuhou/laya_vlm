"""Frozen full-population image motion from native tracks and saved own TCP/K/T."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np

from .. import pixel_footprint
from . import task2_point_anchor_retention_transfer as prior
from .records import RunRecorder, code_identity, file_hash, jsonable

SOURCE = prior.OUTPUT
OUTPUT = prior.base.RAW/'task2-point-anchor-image-motion-run-01'
PROTOCOL = prior.base.ROOT/'docs/research/task2_point_anchor_image_motion_comparison_proposal.md'
HASHES = {
    'sensor-seal.json': '39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60',
    'episodes.jsonl': 'd58bd52625e01a89299cce9581c1d9684ee0467c6a0aaffbd043976147558f4c',
    'whole-close-tracks.jsonl': 'f37c9bd9688175980f0037612b6a5523587b4b207e0f8dd35ded54da032b7010',
    'whole-open_hold-tracks.jsonl': '381847c255d67c65fa34675d14d2e4d82afa1c622dc0ab90296b286900dcd4c5',
    'neck-close-tracks.jsonl': '78e5b4d04697e65cca776266040de2543a3f71cce487822ec189efceb948f8c7',
    'neck-open_hold-tracks.jsonl': '604c025e814aeb7b51a657746863a7a3d3d06d7bc25317fb774e392a806db1a0',
}
FRAME_KEYS = ('condition', 'anchor', 'arm', 'capture_id', 'phase', 'after_step', 'control',
    'source_capture_stream', 'source_capture_seq', 'artifact', 'artifact_sha256',
    'capture_read_sim_time_s', 'cached_geometry_sample_time_s', 'exact_observation_sample_time_s',
    'tcp_read_sim_time_s', 'tcp_source_field', 'own_source', 'own_tcp_world_m')
NATIVE_KEYS = prior.adapter.prior.NATIVE_FIELDS
INPUT_KEYS = (*NATIVE_KEYS, *FRAME_KEYS, 'seed_id', 'seed_pixel_index_xy')
METRICS = ('rgb_delta_v_px', 'rgb_delta_norm_px', 'rgb_minus_tcp_delta_v_px', 'rgb_minus_tcp_delta_norm_px')
SEEDS = 492


def native_point(native):
    """Branch A's only input is the frozen native RGB tracker record."""
    xy = native['point_pixel_index_xy']
    if native['status'] not in prior.base.ACCEPTED or xy is None:
        return None
    point = np.asarray(xy, float)
    return point if point.shape == (2,) and np.isfinite(point).all() else None


def rgb_delta(current_native, reference_native):
    current, reference = native_point(current_native), native_point(reference_native)
    return None if current is None or reference is None else current-reference


def project_own_tcp(tcp, calibration):
    """Branch B adds saved own position/calibration; no sampled scene depth."""
    if tcp is None:
        return {'index_xy': None, 'status': 'missing_own_tcp'}
    point = np.asarray(tcp, float)
    if point.shape != (3,) or not np.isfinite(point).all():
        return {'index_xy': None, 'status': 'nonfinite_or_invalid_own_tcp'}
    camera = pixel_footprint.camera_vertices(point[None, :], calibration['camera_to_world'])[0]
    if camera[2] <= 0:
        return {'index_xy': None, 'status': 'nonpositive_camera_z'}
    homogeneous = calibration['intrinsics'] @ camera
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        xy = homogeneous[:2]/homogeneous[2]-.5
    return {'index_xy': xy.tolist() if np.isfinite(xy).all() else None,
            'status': 'available' if np.isfinite(xy).all() else 'nonfinite_projection'}


def enrich_track(rows, projections, reference):
    if any(set(row)-set(INPUT_KEYS) for row in rows):
        raise ValueError('feature inputs must be whitelisted before enrichment')
    result = []
    native_reference = {k: rows[reference][k] for k in NATIVE_KEYS}
    projected_reference = projections[reference]['index_xy']
    for i, row in enumerate(rows):
        point_delta = tcp_delta = residual = None
        status_a = status_b = 'before_preclose'
        if i >= reference:
            point_delta = rgb_delta({k: row[k] for k in NATIVE_KEYS}, native_reference)
            status_a = 'available' if point_delta is not None else 'native_current_or_reference_unavailable'
            current = projections[i]['index_xy']
            if current is not None and projected_reference is not None:
                tcp_delta = np.asarray(current)-projected_reference
            status_b = status_a if point_delta is None else 'own_projection_current_or_reference_unavailable'
            if point_delta is not None and tcp_delta is not None:
                residual, status_b = point_delta-tcp_delta, 'available'
        metrics = dict.fromkeys(METRICS)
        if point_delta is not None:
            metrics.update(rgb_delta_v_px=float(point_delta[1]), rgb_delta_norm_px=float(np.linalg.norm(point_delta)))
        if residual is not None:
            metrics.update(rgb_minus_tcp_delta_v_px=float(residual[1]), rgb_minus_tcp_delta_norm_px=float(np.linalg.norm(residual)))
        result.append({**row, 'own_tcp_image_projection': projections[i], 'image_motion': {
            'reference_capture_id': reference, 'status_A': status_a, 'status_B': status_b,
            'rgb_delta_xy_px': point_delta, 'tcp_delta_xy_px': tcp_delta,
            'rgb_minus_tcp_delta_xy_px': residual, 'metrics': metrics}, 'identity_verified': None, 'holding': None})
    return result


def summarize(tracks, count, reference):
    if (len(tracks) != SEEDS or any(len(t) != count for t in tracks)
            or any([(r['seed_id'], r['capture_id']) for r in t] != [(s, i) for i in range(count)] for s, t in enumerate(tracks))):
        raise ValueError('complete ordered full-population rows required')
    summaries = []
    for i in range(count):
        rows, metrics = [t[i] for t in tracks], {}
        for key in METRICS:
            values = [r['image_motion']['metrics'][key] for r in rows if r['image_motion']['metrics'][key] is not None]
            metrics[key] = prior.base.describe(values) | {'missing_count': SEEDS-len(values),
                'min': min(values) if values else None, 'max': max(values) if values else None}
        summaries.append({'capture_id': i, 'denominator': SEEDS, 'reference_capture_id': reference,
            'native_admitted_count': sum(native_point(r) is not None for r in rows),
            'A_available_count': sum(r['image_motion']['status_A'] == 'available' for r in rows),
            'B_available_count': sum(r['image_motion']['status_B'] == 'available' for r in rows),
            'metrics': metrics})
    return summaries


def whitelisted(raw):
    return {k: raw[k] for k in INPUT_KEYS}


def load_cell(condition):
    count = prior.FRAME_COUNTS[condition]
    with (SOURCE/f'{condition}-tracks.jsonl').open() as stream:
        rows = [whitelisted(json.loads(line)) for line in stream]
    if [(r['seed_id'], r['capture_id']) for r in rows] != [(s, i) for s in range(SEEDS) for i in range(count)]:
        raise ValueError('complete source row order required')
    metadata = [{k: r[k] for k in FRAME_KEYS} for r in rows[:count]]
    if any({k: r[k] for k in FRAME_KEYS} != metadata[r['capture_id']] for r in rows):
        raise ValueError('saved own/frame metadata must agree across seeds')
    calibrations = []
    for row in rows[:count]:
        path = prior.SOURCE/condition/row['artifact']
        if file_hash(path) != row['artifact_sha256']:
            raise ValueError('bound original calibration source changed')
        with np.load(path, allow_pickle=False) as archive:
            calibrations.append({k: archive[k].copy() for k in ('intrinsics', 'camera_to_world')})
    return [rows[s*count:(s+1)*count] for s in range(SEEDS)], calibrations


def run(review_path):
    identity = code_identity()
    runtime = {'executable': sys.executable, 'python': sys.version, 'numpy': np.__version__}
    review = json.loads(Path(review_path).read_text())
    if (identity['dirty_status'] or review.get('status') != 'pass' or review.get('freeze_commit') != identity['commit']
            or review.get('protocol_sha256') != file_hash(PROTOCOL) or review.get('authorized_batches') != 1
            or runtime != {k: prior.ENVIRONMENT[k] for k in runtime}):
        raise ValueError('clean reviewed one-batch freeze and pinned Python/NumPy runtime required')
    for name, digest in HASHES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('sealed track source changed')
    for path, digest in ((prior.SOURCE_RECEIPT, prior.SOURCE_RECEIPT_SHA),
            (prior.base.RAW/'task2-point-anchor-retention-transfer-independent-audit-01.json',
             'e188710d477c16ce0bd09d61004293015fe15633c12995abdd9252e9dba21b86'),
            (pixel_footprint.__file__, '5559a4ee170e50f45295252b3db2b08553b3ba0a2b886e8bbe6cdbc50b15da8c'),
            (prior.base.__file__, '655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50')):
        if file_hash(path) != digest:
            raise ValueError('source admission/audit or pure helper changed')
    recorder = RunRecorder(OUTPUT, {'protocol_sha256': file_hash(PROTOCOL), 'seed_count': SEEDS,
        'frame_counts': prior.FRAME_COUNTS, 'reference': 'preclose', 'metrics': METRICS,
        'source_sha256': HASHES, 'input_whitelist': INPUT_KEYS},
        {'run_id': OUTPUT.name, 'code': identity, 'runtime': runtime, 'review_sha256': file_hash(review_path)})
    written, completed, summaries = 0, 0, {}
    try:
        (OUTPUT/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        (OUTPUT/'review.json').write_bytes(Path(review_path).read_bytes())
        for condition, count in prior.FRAME_COUNTS.items():
            tracks, calibration = load_cell(condition)
            projections = [project_own_tcp(row['own_tcp_world_m'], cal) for row, cal in zip(tracks[0], calibration, strict=True)]
            enriched = []
            with (OUTPUT/f'{condition}-features.jsonl').open('x') as stream:
                for track in tracks:
                    rows = enrich_track(track, projections, count-17)
                    for row in rows:
                        stream.write(json.dumps(jsonable(row), allow_nan=False)+'\n')
                        written += 1
                    stream.flush()
                    os.fsync(stream.fileno())
                    enriched.append(rows)
                    completed += 1
            summaries[condition] = summarize(enriched, count, count-17)
            recorder.record('cell_complete', {'condition': condition, 'rows': count*SEEDS, 'tracks': SEEDS})
            print(condition+' complete', flush=True)
        if (completed, written) != (1968, 91512):
            raise ValueError('complete fixed population required')
        prior.base.write_json(OUTPUT/'image-motion-summary.json', {'cells': summaries, 'holding': None,
            'identity_verified': None, 'measured_scene_depth_used': False, 'old_3D_joined': False})
        prior.base.write_json(OUTPUT/'sensor-seal.json', {'sha256': {p.name: file_hash(p) for p in sorted(OUTPUT.iterdir())
            if p.is_file() and p.name != 'episodes.jsonl'}, 'complete': True, 'rows': written, 'tracks': completed,
            'measured_scene_depth_used': False, 'old_3D_joined': False, 'evaluator_read': False})
        recorder.record('termination', {'reason': 'all_image_motion_rows_sealed', 'rows': written, 'tracks': completed,
            'sensor_seal_sha256': file_hash(OUTPUT/'sensor-seal.json'), 'retries': 0})
    except BaseException as exc:
        recorder.record('failure', {'reason': repr(exc), 'written_rows': written, 'completed_tracks': completed, 'retries': 0})
        raise
    finally:
        recorder.close()
        prior.base.write_json(OUTPUT/'artifacts.json', {p.name: file_hash(p) for p in sorted(OUTPUT.iterdir()) if p.is_file()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', required=True)
    run(parser.parse_args().review)
