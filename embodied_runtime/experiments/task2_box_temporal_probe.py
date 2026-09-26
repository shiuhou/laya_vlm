"""One offline initial-BOX population; unchanged single-seed LK, no recovery."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from ..vision import camera_to_world, pixel_to_camera
from . import point_temporal_probe as lk
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records

ROOT = Path(__file__).resolve().parents[2]
RAW = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
SOURCE = RAW / 'interaction-observability-paired-01'
SEEDS = RAW / 'task2-box-support-run-02/sensor-representation.json'
PROTOCOL = ROOT / 'docs/research/task2_initial_box_temporal_probe_proposal.md'
ARMS = ('close', 'open_hold')
HASHES = {
    'captures.json': 'e632b67471cf4b3b7bb924201a884d43339e677140a64522b4ef63f349fb2650',
    'sensors.jsonl': '59a38821e165393d607be1b3ec9100f093fcc52718282173fe8b28c556174bbe',
    'endpoints.json': 'c28136d9e0e67b359491a3d270b0566e49a7f5939287363a18cdd8192ab7abe5',
    'sensor-seal.json': '77752c151c979e234607942a46674f25f3e6664eb66844e4411cff1def076013',
}
SEED_SHA = 'be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead'
LK_SHA = '86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36'
ACCEPTED = ('seeded', 'native_status_ok')
REFERENCES = {'initial': 0, 'preclose': 13}
METRICS = ('point_delta_z_m', 'point_delta_norm_m', 'point_minus_tcp_delta_z_m',
           'point_minus_tcp_delta_norm_m')


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(jsonable(value), stream, indent=2, allow_nan=False)
        stream.write('\n')


def load_inputs():
    """Read admitted sensor sources only; never the old seeds or evaluator."""
    if file_hash(lk.__file__) != LK_SHA or file_hash(SEEDS) != SEED_SHA:
        raise ValueError('sealed seed population or LK source differs')
    for name, digest in HASHES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('source receipt differs: '+name)
    captures = json.loads((SOURCE/'captures.json').read_text())
    controls = [json.loads(line) for line in (SOURCE/'sensors.jsonl').read_text().splitlines()]
    endpoints = json.loads((SOURCE/'endpoints.json').read_text())
    sensor_seal = json.loads((SOURCE/'sensor-seal.json').read_text())['sha256']
    support = json.loads(SEEDS.read_text())
    seeds = [row['pixel_xy'] for row in support['support_G']]
    if (support['crop_xyxy'] != [212, 169, 224, 210]
            or seeds != [[x, y] for y in range(169, 210) for x in range(212, 224)]):
        raise ValueError('all 492 original ordered seeds required')
    result, receipts = {}, {}
    schedule = [(-1, None)]+[(i, 7) for i in range(13)]+[(i, j) for i in range(13, 17) for j in range(8)]
    for arm in ARMS:
        selected = [c for c in captures if c['arm'] == arm]
        if ([c['capture_id'] for c in selected] != list(range(46))
                or [(c['after_step'], c['control']) for c in selected] != schedule):
            raise ValueError('fixed full capture schedule differs')
        frames, tcps, meta = [], [], []
        for c in selected:
            path = SOURCE/c['artifact']
            if file_hash(path) != c['artifact_sha256'] or sensor_seal[c['artifact']] != c['artifact_sha256']:
                raise ValueError('source frame changed')
            with np.load(path, allow_pickle=False) as z:
                f = {k: z[k].copy() for k in ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')}
            if (f['rgb'].shape != (384, 384, 3) or f['rgb'].dtype != np.uint8
                    or f['depth_m'].shape != (384, 384) or f['intrinsics'].shape != (3, 3)
                    or f['camera_to_world'].shape != (4, 4)
                    or not np.isfinite(f['intrinsics']).all() or not np.isfinite(f['camera_to_world']).all()):
                raise ValueError('RGB-D/calibration schema differs')
            pool = endpoints if c['capture_id'] == 0 else controls
            matches = [r for r in pool if r['arm'] == arm and
                       r.get('after_step', r.get('step')) == c['after_step'] and
                       (c['capture_id'] == 0 or r['control'] == c['control'])]
            if len(matches) != 1:
                raise ValueError('ambiguous saved TCP source')
            own = matches[0]['sensor']
            tcp = np.asarray(own['tcp_fk_world_m'], float)
            if tcp.shape != (3,) or not np.isfinite(tcp).all():
                raise ValueError('saved own TCP invalid')
            frames.append(f)
            tcps.append(tcp)
            meta.append({k: c[k] for k in ('capture_id', 'after_step', 'control', 'artifact',
                         'artifact_sha256', 'capture_read_sim_time_s', 'cached_geometry_sample_time_s')}
                        | {'tcp_read_sim_time_s': own['read_sim_time_s'],
                           'tcp_source_field': 'saved_sensor.tcp_fk_world_m',
                           'exact_observation_sample_time_s': None})
        result[arm] = {'frames': frames, 'tcps': tcps, 'meta': meta}
        receipts[arm] = {'captures': meta, 'frame_count': len(frames), 'seed_count': len(seeds)}
    for i in range(14):
        if not np.array_equal(result['close']['frames'][i]['rgb'], result['open_hold']['frames'][i]['rgb']):
            raise ValueError('paired common-prefix RGB differs')
    for key in ('rgb', 'depth_m', 'intrinsics', 'camera_to_world'):
        if not np.array_equal(result['close']['frames'][0][key], result['open_hold']['frames'][0][key]):
            raise ValueError('paired initial sensor frames differ')
    for arm in ARMS:
        d = result[arm]['frames'][0]['depth_m']
        if any(not np.isfinite(d[y, x]) or not .01 <= d[y, x] <= 5. for x, y in seeds):
            raise ValueError('initial seed validity differs')
    return seeds, result, {'source_sha256': HASHES, 'seed_sha256': SEED_SHA,
                         'lk_source_sha256': LK_SHA, 'arms': receipts,
                         'seed_pixel_index_xy': seeds, 'common_prefix_rgb_equal': True,
                         'paired_initial_sensor_fields_equal': True}


def surface_sample(track, frame):
    """Same floor, validity and half-pixel projection as original analysis."""
    if track['status'] not in ACCEPTED:
        return {'sample_pixel_xy': None, 'depth_m': None, 'surface_point_world_m': None,
                'depth_status': 'RGB_track_not_admitted'}
    x, y = np.floor(track['point_pixel_index_xy']).astype(int)
    h, w = frame['depth_m'].shape
    if not (0 <= x < w and 0 <= y < h):
        return {'sample_pixel_xy': None, 'depth_m': None, 'surface_point_world_m': None,
                'depth_status': 'outside_image'}
    z = float(frame['depth_m'][y, x])
    valid = np.isfinite(z) and .01 <= z <= 5.
    xyz = camera_to_world(pixel_to_camera(x+.5, y+.5, z, frame['intrinsics']),
                          frame['camera_to_world']) if valid else None
    return {'sample_pixel_xy': [int(x), int(y)], 'depth_m': z if np.isfinite(z) else None,
            'surface_point_world_m': None if xyz is None else xyz.tolist(),
            'depth_status': 'valid' if valid else 'outside_valid_range' if np.isfinite(z) else 'nonfinite'}


def reference_delta(xyz, base_xyz, tcp, base_tcp):
    tcp_delta = np.asarray(tcp)-base_tcp
    if xyz is None or base_xyz is None:
        return {'tcp_delta_m': tcp_delta.tolist(), 'point_delta_m': None,
                'point_minus_tcp_delta_m': None, **{k: None for k in METRICS}}
    delta = np.asarray(xyz)-base_xyz
    residual = delta-tcp_delta
    return {'tcp_delta_m': tcp_delta.tolist(), 'point_delta_m': delta.tolist(),
            'point_minus_tcp_delta_m': residual.tolist(), 'point_delta_z_m': float(delta[2]),
            'point_delta_norm_m': float(np.linalg.norm(delta)),
            'point_minus_tcp_delta_z_m': float(residual[2]),
            'point_minus_tcp_delta_norm_m': float(np.linalg.norm(residual))}


def enrich_track(tracked, packet, seed_id, seed):
    sampled = [surface_sample(t, f) for t, f in zip(tracked, packet['frames'], strict=True)]
    rows = []
    for i, (track, sample, meta, tcp) in enumerate(zip(tracked, sampled, packet['meta'], packet['tcps'], strict=True)):
        references = {name: reference_delta(sample['surface_point_world_m'], sampled[j]['surface_point_world_m'],
                                           tcp, packet['tcps'][j]) if i >= j else None
                      for name, j in REFERENCES.items()}
        rows.append({**track, **sample, **meta, 'seed_id': seed_id, 'seed_pixel_index_xy': seed,
                     'reference_deltas': references, 'identity_verified': None, 'holding': None})
    return rows


def describe(values):
    if not values:
        return {'count': 0, 'median': None, 'q25': None, 'q75': None}
    q25, median, q75 = np.percentile(values, [25, 50, 75], method='linear')
    return {'count': len(values), 'median': float(median), 'q25': float(q25), 'q75': float(q75)}


def summarize_tracks(tracks, denominator):
    if len(tracks) != denominator or len({len(t) for t in tracks}) != 1:
        raise ValueError('every initialized trajectory must be retained')
    frames = []
    for i in range(len(tracks[0])):
        rows = [t[i] for t in tracks]
        refs = {}
        for name, j in REFERENCES.items():
            refs[name] = {'reference_capture_id': j,
                'reference_surface_valid_count': sum(t[j]['surface_point_world_m'] is not None for t in tracks) if i >= j else None,
                'metrics': {key: describe([r['reference_deltas'][name][key] for r in rows
                            if r['reference_deltas'][name] is not None and r['reference_deltas'][name][key] is not None])
                            for key in METRICS}}
        frames.append({'capture_id': i, 'denominator': denominator,
                       'native_surviving_count': sum(r['status'] in ACCEPTED for r in rows),
                       'valid_surface_count': sum(r['surface_point_world_m'] is not None for r in rows),
                       'native_failure_count': sum(r['status'] == 'native_failure' for r in rows),
                       'unknown_after_failure_count': sum(r['status'] == 'unknown_after_native_failure' for r in rows),
                       'references': refs})
    return frames


def preflight(output):
    import cv2
    if cv2.__version__ != lk.CV2_VERSION:
        raise ValueError('frozen OpenCV version differs')
    seeds, _, admission = load_inputs()
    result = {'status': 'pass', 'code': code_identity(), 'python': sys.executable,
              'cv2_version': cv2.__version__, 'cv2_threads': cv2.getNumThreads(),
              'lk_settings': lk.LK_SETTINGS, 'protocol_sha256': file_hash(PROTOCOL),
              'admission': admission, 'total_tracks': len(seeds)*2,
              'total_track_rows': len(seeds)*2*46, 'LK_calls': 0,
              'model_physics_render_calls': 0, 'evaluator_read': False}
    write_json(output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('code', 'admission')}, indent=2))


def run(output, preflight_path, review):
    import cv2
    identity = code_identity()
    p = json.loads(Path(preflight_path).read_text())
    if identity['dirty_status'] or identity != p['code'] or identity['commit'] not in Path(review).read_text() or 'PASS' not in Path(review).read_text():
        raise ValueError('clean frozen source, matching preflight and independent PASS required')
    if cv2.__version__ != lk.CV2_VERSION or p['protocol_sha256'] != file_hash(PROTOCOL):
        raise ValueError('protocol or OpenCV changed')
    seeds, inputs, admission = load_inputs()
    if admission != p['admission']:
        raise ValueError('source preflight changed')
    recorder = RunRecorder(output, {'protocol_sha256': file_hash(PROTOCOL), 'lk_settings': lk.LK_SETTINGS,
        'seed_count': 492, 'captures_per_arm': 46, 'model_physics_render_calls': 0},
        {'run_id': Path(output).name, 'code': identity, 'python': sys.executable,
         'cv2_version': cv2.__version__, 'cv2_threads': cv2.getNumThreads(),
         'preflight_sha256': file_hash(preflight_path), 'review_sha256': file_hash(review)})
    output = Path(output)
    completed = 0
    try:
        (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        (output/'review.md').write_bytes(Path(review).read_bytes())
        write_json(output/'admission.json', admission)
        recorder.record('input_admitted', {'artifact': 'admission.json', 'sha256': file_hash(output/'admission.json')})
        summaries = {}
        for arm in ARMS:
            tracks = []
            rgbs = np.stack([f['rgb'] for f in inputs[arm]['frames']])
            with (output/f'{arm}-tracks.jsonl').open('x') as stream:
                for seed_id, seed in enumerate(seeds):
                    tracked = lk.track_lk(rgbs, seed, cv2)
                    rows = enrich_track(tracked, inputs[arm], seed_id, seed)
                    for row in rows:
                        stream.write(json.dumps(jsonable(row), allow_nan=False)+'\n')
                    stream.flush()
                    tracks.append(rows)
                    completed += 1
                    if (seed_id+1) % 64 == 0:
                        print(f'{arm}: {seed_id+1}/492 complete', flush=True)
            summaries[arm] = summarize_tracks(tracks, len(seeds))
            recorder.record('arm_tracks_complete', {'arm': arm, 'tracks': len(tracks), 'rows': len(tracks)*46})
        write_json(output/'sensor-summary.json', {'holding': None, 'references': REFERENCES, 'arms': summaries})
        artifacts = {f: file_hash(output/f) for f in ('close-tracks.jsonl', 'open_hold-tracks.jsonl', 'sensor-summary.json')}
        write_json(output/'sensor-seal.json', {'sha256': artifacts, 'evaluator_read': False})
        recorder.record('sensor_outputs_sealed', {'artifact': 'sensor-seal.json', 'sha256': file_hash(output/'sensor-seal.json')})
        recorder.record('termination', {'reason': 'all_tracks_sealed', 'tracks': completed,
                                       'model_physics_render_calls': 0, 'retries': 0})
    except Exception as exc:
        recorder.record('failure', {'reason': repr(exc), 'completed_tracks': completed, 'retries': 0})
        raise
    finally:
        recorder.close()


def sealed_tracks(output):
    output = Path(output)
    records, errors = load_records(output/'episodes.jsonl')
    if errors or records[-1]['kind'] != 'termination' or records[-1]['data']['tracks'] != 984:
        raise ValueError('complete sealed batch required')
    seal_record = next(r['data'] for r in records if r['kind'] == 'sensor_outputs_sealed')
    if file_hash(output/'sensor-seal.json') != seal_record['sha256']:
        raise ValueError('sensor seal changed')
    seal = json.loads((output/'sensor-seal.json').read_text())
    if seal['evaluator_read'] is not False or any(file_hash(output/k) != v for k, v in seal['sha256'].items()):
        raise ValueError('sealed sensors changed')
    return {arm: [json.loads(line) for line in (output/f'{arm}-tracks.jsonl').read_text().splitlines()] for arm in ARMS}


def proxy_membership(rows, masks):
    membership, first_departure = [], {}
    # A departure requires an observed earlier True; initially outside is distinct.
    seen_inside = set()
    for r in rows:
        pixel = r['sample_pixel_xy']
        value = None if pixel is None or r['status'] not in ACCEPTED else bool(masks[r['capture_id']][pixel[1], pixel[0]])
        row = {'seed_id': r['seed_id'], 'capture_id': r['capture_id'], 'proxy_membership': value,
               'tracker_status': r['status'], 'sample_pixel_xy': pixel}
        membership.append(row)
        if value is False and r['seed_id'] in seen_inside and r['seed_id'] not in first_departure:
            first_departure[r['seed_id']] = row
        if value is True:
            seen_inside.add(r['seed_id'])
    counts = [{'capture_id': i, 'denominator': 492,
               'proxy_true': sum(r['proxy_membership'] is True for r in membership if r['capture_id'] == i),
               'proxy_false': sum(r['proxy_membership'] is False for r in membership if r['capture_id'] == i),
               'proxy_unknown': sum(r['proxy_membership'] is None for r in membership if r['capture_id'] == i)} for i in range(len(masks))]
    return {'rows': membership, 'counts': counts, 'first_observed_departure_after_proxy_true': first_departure,
            'resolved_depth_ownership': None, 'semantic_confidence': None}


def evaluate(output):
    output = Path(output)
    tracks = sealed_tracks(output)
    target = output/'evaluation'
    target.mkdir(exist_ok=False)
    write_json(target/'evaluation-start.json', {'sensor_seal_sha256': file_hash(output/'sensor-seal.json'),
        'journal_sha256': file_hash(output/'episodes.jsonl'), 'evaluator_read': False})
    results, hashes = {}, {}
    for arm in ARMS:
        masks = []
        for i in range(46):
            path = SOURCE/f'evaluator-only/{arm}-{i:04d}-bottle-mask.npy'
            hashes[str(path)] = file_hash(path)
            mask = np.load(path, allow_pickle=False)
            if mask.shape != (384, 384) or mask.dtype != np.bool_:
                raise ValueError('archived proxy schema differs')
            masks.append(mask)
        results[arm] = proxy_membership(tracks[arm], masks)
    write_json(target/'proxy-membership.json', {'arms': results, 'mask_sha256': hashes})
    write_json(target/'artifacts.json', {p.name: file_hash(p) for p in target.iterdir() if p.is_file()})
    print('Proxy-only evaluator complete; tracks unchanged.')


def main():
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
            parser.error('run requires --preflight and --review')
        run(args.output, args.preflight, args.review)
    else:
        evaluate(args.output)


if __name__ == '__main__':
    main()
