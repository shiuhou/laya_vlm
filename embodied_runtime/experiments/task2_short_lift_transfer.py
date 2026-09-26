"""Frozen offline BOX-track transfer to the archived visual executor 10 mm lift."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from . import task2_box_temporal_probe as base
from . import task2_track_coordinate_association as association
from .records import RunRecorder, code_identity, file_hash, jsonable

SOURCE = base.RAW/'local-grasp-interface-run-02'
PROTOCOL = base.ROOT/'docs/research/task2_short_lift_transfer_protocol.md'
SOURCE_HASHES = {
    'captures.json': '1fa0469493a2b61f9c4a304fb323470680b5b1369ab501a14410bf76d6859b52',
    'sensors.json': 'f3eead6a1556e2bbb64ea095aca6c251c6df7e95797099510d5aeb52fe662b58',
    'sensor-seal.json': '2ac164126dcd9ca32e851c97da90db29657c0a7f0c6bf4a464cdd68862fd1326',
    'episodes.jsonl': '9347eab2f1b48fe3799ccfbc3164f60406b6451bd194819ef66632df7d6464bb',
}
ASSOCIATION_SHA = 'b95245bab639fac6a54359dd51020b2b40d0fd5e23f71fb7d1b7020b2590c855'
INITIAL_FRAME_SHA = '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969'
REFERENCES = {'preclose': 13}
FRAME_COUNT = 30
PREFIX_COUNT = 14
NATIVE_FIELDS = ('frame', 'status', 'point_pixel_index_xy', 'attempted_backward_point_pixel_index_xy',
                 'forward_status', 'backward_status', 'forward_backward_residual_px',
                 'forward_patch_error', 'backward_patch_error')


def frame_from_capture(source, capture, seal):
    path = source/capture['artifact']
    if file_hash(path) != capture['artifact_sha256'] or seal[capture['artifact']] != capture['artifact_sha256']:
        raise ValueError('source frame hash differs')
    with np.load(path, allow_pickle=False) as data:
        frame = {k: data[k].copy() for k in ('rgb', 'depth_m', 'intrinsics', 'camera_to_world')}
    if (frame['rgb'].shape != (384, 384, 3) or frame['rgb'].dtype != np.uint8
            or frame['depth_m'].shape != (384, 384) or frame['intrinsics'].shape != (3, 3)
            or frame['camera_to_world'].shape != (4, 4)
            or not np.isfinite(frame['intrinsics']).all() or not np.isfinite(frame['camera_to_world']).all()):
        raise ValueError('RGB-D/calibration schema differs')
    return frame


def tcp_for_capture(capture, sensors):
    """Initial own TCP is absent; never read evaluator state or old endpoints."""
    if capture['capture_id'] == 0:
        return None, {'tcp_read_sim_time_s': None, 'tcp_source_field': None,
                      'tcp_status': 'unknown_initial_own_sensor_absent'}
    matches = [r['sensor'] for r in sensors if r['arm'] == capture['arm']
               and r['step'] == capture['after_step'] and r['control'] == capture['control']]
    if len(matches) != 1:
        raise ValueError('ambiguous saved own TCP source')
    own = matches[0]
    tcp = np.asarray(own['tcp_fk_world_m'], float)
    if tcp.shape != (3,) or not np.isfinite(tcp).all():
        raise ValueError('saved own TCP invalid')
    return tcp, {'tcp_read_sim_time_s': own['read_sim_time_s'],
                 'tcp_source_field': 'sensors.json.sensor.tcp_fk_world_m', 'tcp_status': 'saved_own_sensor'}


def load_inputs():
    for path, digest in ((base.lk.__file__, base.LK_SHA), (base.__file__, association.BASE_SHA),
                         (association.__file__, ASSOCIATION_SHA), (base.SEEDS, base.SEED_SHA)):
        if file_hash(path) != digest:
            raise ValueError('frozen helper or seed population changed')
    for name, digest in SOURCE_HASHES.items():
        if file_hash(SOURCE/name) != digest:
            raise ValueError('short-lift source receipt differs: '+name)
    for name in ('captures.json', 'sensor-seal.json'):
        if file_hash(base.SOURCE/name) != base.HASHES[name]:
            raise ValueError('historical source receipt differs')
    support = json.loads(base.SEEDS.read_text())
    seeds = [r['pixel_xy'] for r in support['support_G']]
    if support['crop_xyxy'] != [212, 169, 224, 210] or seeds != [[x, y] for y in range(169, 210) for x in range(212, 224)]:
        raise ValueError('all 492 original ordered BOX seeds required')
    captures = json.loads((SOURCE/'captures.json').read_text())
    sensors = json.loads((SOURCE/'sensors.json').read_text())
    seal = json.loads((SOURCE/'sensor-seal.json').read_text())['sha256']
    for name in ('captures.json', 'sensors.json'):
        if seal[name] != SOURCE_HASHES[name]:
            raise ValueError('source sensor seal differs')
    historical = json.loads((base.SOURCE/'captures.json').read_text())
    old_seal = json.loads((base.SOURCE/'sensor-seal.json').read_text())['sha256']
    schedule = [(-1, None)]+[(i, 7) for i in range(13)]+[(i, j) for i in (13, 14) for j in range(8)]
    if len(captures) != 60 or len(sensors) != 240:
        raise ValueError('complete short-lift source required')
    packets, receipts = {}, {}
    for arm in base.ARMS:
        selected = [c for c in captures if c['arm'] == arm]
        if ([c['capture_id'] for c in selected] != list(range(FRAME_COUNT))
                or [(c['after_step'], c['control']) for c in selected] != schedule
                or selected[0]['artifact_sha256'] != INITIAL_FRAME_SHA):
            raise ValueError('fixed short-lift capture schedule or initial BOX frame differs')
        frames, tcps, meta = [], [], []
        old = [c for c in historical if c['arm'] == arm]
        for c in selected:
            frame = frame_from_capture(SOURCE, c, seal)
            if c['capture_id'] < PREFIX_COUNT:
                reference = frame_from_capture(base.SOURCE, old[c['capture_id']], old_seal)
                if any(not np.array_equal(frame[k], reference[k]) for k in frame):
                    raise ValueError('historical 14-frame RGB-D/calibration prefix differs')
            tcp, tcp_meta = tcp_for_capture(c, sensors)
            frames.append(frame)
            tcps.append(tcp)
            meta.append({k: c[k] for k in ('capture_id', 'after_step', 'control', 'artifact',
                'artifact_sha256', 'capture_read_sim_time_s', 'cached_geometry_sample_time_s')}
                | tcp_meta | {'exact_observation_sample_time_s': None})
        if any(not np.isfinite(frames[0]['depth_m'][y, x]) or not .01 <= frames[0]['depth_m'][y, x] <= 5.
               for x, y in seeds):
            raise ValueError('initial seed validity differs')
        packets[arm] = {'frames': frames, 'tcps': tcps, 'meta': meta}
        receipts[arm] = {'captures': meta, 'frame_count': FRAME_COUNT, 'seed_count': 492,
                         'historical_prefix_sensor_fields_equal': True}
    for i in range(PREFIX_COUNT):
        if any(not np.array_equal(packets['close']['frames'][i][k], packets['open_hold']['frames'][i][k])
               for k in packets['close']['frames'][i]):
            raise ValueError('paired common-prefix sensor fields differ')
    for name, digest in association.SOURCE_HASHES.items():
        if file_hash(association.SOURCE/name) != digest:
            raise ValueError('sealed native-track baseline changed')
    original = base.sealed_tracks(association.SOURCE)
    for arm in base.ARMS:
        if [(r['seed_id'], r['capture_id']) for r in original[arm]] != [(s, i) for s in range(492) for i in range(46)]:
            raise ValueError('complete original native tracks required')
        if any(r['seed_pixel_index_xy'] != seeds[r['seed_id']] for r in original[arm]):
            raise ValueError('historical seed identity differs')
    return seeds, packets, original, {'source_sha256': SOURCE_HASHES, 'seed_sha256': base.SEED_SHA,
        'lk_source_sha256': base.LK_SHA, 'association_source_sha256': ASSOCIATION_SHA,
        'original_track_source_sha256': association.SOURCE_HASHES, 'arms': receipts,
        'seed_pixel_index_xy': seeds, 'historical_prefix_frames': PREFIX_COUNT,
        'initial_own_tcp_world_m': None, 'initial_own_tcp_status': 'unknown_not_archived',
        'paired_prefix_sensor_fields_equal': True, 'evaluator_read': False}


def enrich_track(tracked, packet, seed_id, seed):
    sampled = [association.nearest_surface_sample(t, f) for t, f in zip(tracked, packet['frames'], strict=True)]
    rows = []
    for i, (track, sample, meta, tcp) in enumerate(zip(tracked, sampled, packet['meta'], packet['tcps'], strict=True)):
        delta = base.reference_delta(sample['surface_point_world_m'], sampled[13]['surface_point_world_m'],
                                     tcp, packet['tcps'][13]) if i >= 13 else None
        rows.append({**track, **sample, **meta, 'seed_id': seed_id, 'seed_pixel_index_xy': seed,
                     'own_tcp_world_m': None if tcp is None else list(tcp),
                     'sampling_convention': association.CONVENTION, 'reference_deltas': {'preclose': delta},
                     'identity_verified': None, 'holding': None})
    return rows


def summarize_tracks(tracks, denominator):
    if len(tracks) != denominator or any(len(t) != FRAME_COUNT for t in tracks):
        raise ValueError('all initialized trajectories and frames required')
    frames = []
    for i in range(FRAME_COUNT):
        rows = [t[i] for t in tracks]
        metrics = {}
        for key in base.METRICS:
            values = [r['reference_deltas']['preclose'][key] for r in rows
                      if r['reference_deltas']['preclose'] is not None and r['reference_deltas']['preclose'][key] is not None]
            metrics[key] = base.describe(values) | {'missing_count': denominator-len(values)}
        frames.append({'capture_id': i, 'denominator': denominator,
            'native_surviving_count': sum(r['status'] in base.ACCEPTED for r in rows),
            'native_failure_count': sum(r['status'] == 'native_failure' for r in rows),
            'unknown_after_failure_count': sum(r['status'] == 'unknown_after_native_failure' for r in rows),
            'valid_surface_count': sum(r['surface_point_world_m'] is not None for r in rows),
            'references': {'preclose': {'reference_capture_id': 13, 'available': i >= 13,
                'reference_surface_valid_count': sum(t[13]['surface_point_world_m'] is not None for t in tracks) if i >= 13 else None,
                'metrics': metrics}}})
    return frames


def prefix_disagreements(rows, original):
    return [{'seed_id': r['seed_id'], 'capture_id': i,
             'fields': [k for k in NATIVE_FIELDS if r[k] != original[i][k]]}
            for i, r in enumerate(rows[:PREFIX_COUNT]) if any(r[k] != original[i][k] for k in NATIVE_FIELDS)]


def preflight(output):
    import cv2
    if cv2.__version__ != base.lk.CV2_VERSION:
        raise ValueError('OpenCV version differs')
    check = association.convention_check(cv2)
    _, _, _, admission = load_inputs()
    base.write_json(output, {'status': 'pass', 'code': code_identity(), 'python': sys.executable,
        'cv2_version': cv2.__version__, 'cv2_threads': cv2.getNumThreads(),
        'lk_settings': base.lk.LK_SETTINGS, 'protocol_sha256': file_hash(PROTOCOL),
        'convention_check': check, 'admission': admission, 'total_tracks': 984, 'total_track_rows': 29520,
        'archived_transfer_outcomes_computed': False, 'LK_model_physics_render_calls': 0})
    print('PASS: source and synthetic-coordinate preflight; no transfer tracking or evaluator reads.')


def run(output, preflight_path, review):
    import cv2
    identity = code_identity()
    receipt = json.loads(Path(preflight_path).read_text())
    review_text = Path(review).read_text()
    if identity['dirty_status'] or identity != receipt['code'] or identity['commit'] not in review_text or 'PASS' not in review_text:
        raise ValueError('clean matching freeze, preflight and independent PASS required')
    if receipt['protocol_sha256'] != file_hash(PROTOCOL) or cv2.__version__ != base.lk.CV2_VERSION:
        raise ValueError('protocol or OpenCV differs')
    seeds, packets, original, admission = load_inputs()
    if admission != receipt['admission']:
        raise ValueError('admission differs from preflight')
    recorder = RunRecorder(output, {'protocol_sha256': file_hash(PROTOCOL), 'lk_settings': base.lk.LK_SETTINGS,
        'seed_count': 492, 'captures_per_arm': FRAME_COUNT, 'references': REFERENCES,
        'sampling_convention': association.CONVENTION, 'model_physics_render_calls': 0},
        {'run_id': Path(output).name, 'code': identity, 'python': sys.executable,
         'cv2_version': cv2.__version__, 'cv2_threads': cv2.getNumThreads(),
         'preflight_sha256': file_hash(preflight_path), 'review_sha256': file_hash(review)})
    output = Path(output)
    completed = 0
    try:
        (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        (output/'review.md').write_bytes(Path(review).read_bytes())
        base.write_json(output/'admission.json', admission)
        recorder.record('input_admitted', {'sha256': file_hash(output/'admission.json')})
        summaries, prefix = {}, {}
        for arm in base.ARMS:
            trajectories, mismatches = [], []
            rgbs = np.stack([f['rgb'] for f in packets[arm]['frames']])
            with (output/f'{arm}-tracks.jsonl').open('x') as stream:
                for seed_id, seed in enumerate(seeds):
                    tracked = base.lk.track_lk(rgbs, seed, cv2)
                    rows = enrich_track(tracked, packets[arm], seed_id, seed)
                    if len(rows) != FRAME_COUNT:
                        raise ValueError('tracker omitted capture rows')
                    for row in rows:
                        stream.write(json.dumps(jsonable(row), allow_nan=False)+'\n')
                    stream.flush()
                    mismatches.extend(prefix_disagreements(rows, original[arm][seed_id*46:(seed_id+1)*46]))
                    trajectories.append(rows)
                    completed += 1
                    if (seed_id+1) % 64 == 0:
                        print(f'{arm}: {seed_id+1}/492 complete', flush=True)
            summaries[arm] = summarize_tracks(trajectories, 492)
            prefix[arm] = {'expected_rows': 492*PREFIX_COUNT, 'compared_native_fields': NATIVE_FIELDS,
                           'exact_agreement': not mismatches, 'disagreements': mismatches}
            recorder.record('arm_tracks_complete', {'arm': arm, 'tracks': 492, 'rows': 14760})
        base.write_json(output/'sensor-summary.json', {'holding': None, 'initial_own_tcp_world_m': None,
            'initial_reference_metrics': None, 'references': REFERENCES, 'arms': summaries})
        base.write_json(output/'prefix-agreement.json', {'arms': prefix, 'comparison_uses_masks': False})
        artifacts = {name: file_hash(output/name) for name in ('close-tracks.jsonl', 'open_hold-tracks.jsonl',
                                                               'sensor-summary.json', 'prefix-agreement.json')}
        base.write_json(output/'sensor-seal.json', {'sha256': artifacts, 'evaluator_read': False})
        recorder.record('sensor_outputs_sealed', {'sha256': file_hash(output/'sensor-seal.json')})
        if any(not p['exact_agreement'] for p in prefix.values()):
            raise ValueError('unexpected causal native-prefix disagreement; retained complete sensor batch; no evaluator/retry')
        recorder.record('termination', {'reason': 'all_tracks_sealed', 'tracks': completed, 'rows': 29520,
                                       'model_physics_render_calls': 0, 'retries': 0})
    except Exception as exc:
        recorder.record('failure', {'reason': repr(exc), 'completed_tracks': completed, 'retries': 0})
        raise
    finally:
        recorder.close()


def sealed_tracks(output):
    tracks = base.sealed_tracks(output)
    expected = [(s, i) for s in range(492) for i in range(FRAME_COUNT)]
    for arm in base.ARMS:
        if [(r['seed_id'], r['capture_id']) for r in tracks[arm]] != expected:
            raise ValueError('all 29,520 rows required before evaluator')
    return tracks


def evaluate(output):
    output = Path(output)
    tracks = sealed_tracks(output)
    target = output/'evaluation'
    target.mkdir(exist_ok=False)
    base.write_json(target/'evaluation-start.json', {'sensor_seal_sha256': file_hash(output/'sensor-seal.json'),
        'journal_sha256': file_hash(output/'episodes.jsonl'), 'evaluator_read': False})
    results, hashes = {}, {}
    for arm in base.ARMS:
        masks = []
        for i in range(FRAME_COUNT):
            path = SOURCE/f'evaluator-only/{arm}-{i:04d}-bottle-mask.npy'
            hashes[str(path)] = file_hash(path)
            mask = np.load(path, allow_pickle=False)
            if mask.shape != (384, 384) or mask.dtype != np.bool_:
                raise ValueError('archived proxy schema differs')
            masks.append(mask)
        results[arm] = base.proxy_membership(tracks[arm], masks)
    base.write_json(target/'proxy-membership.json', {'arms': results, 'mask_sha256': hashes})
    base.write_json(target/'artifacts.json', {p.name: file_hash(p) for p in target.iterdir() if p.is_file()})
    print('All 60 archived masks evaluated after complete sensor seal; tracks unchanged.')


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
            parser.error('run requires --preflight and --review')
        run(args.output, args.preflight, args.review)
    else:
        evaluate(args.output)
