"""Audit all archived short-lift transfer rows without LK, projection or FK."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from task2_box_evidence_audit import canonical, read, require, sha

FREEZE = '4e661c7b1649b887d585a6bb3b016afc414effc1'
ARMS = ('close', 'open_hold')
ACCEPTED = ('seeded', 'native_status_ok')
REFERENCES = {'preclose': 13}
METRICS = ('point_delta_z_m', 'point_delta_norm_m', 'point_minus_tcp_delta_z_m', 'point_minus_tcp_delta_norm_m')
RAW_FIELDS = ('point_pixel_index_xy', 'attempted_backward_point_pixel_index_xy', 'forward_status', 'backward_status',
              'forward_backward_residual_px', 'forward_patch_error', 'backward_patch_error')


def same(actual, expected, description):
    if isinstance(expected, dict):
        require(set(actual) == set(expected), description + ' keys')
        for key in expected:
            same(actual[key], expected[key], description + '.' + str(key))
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), description + ' length')
        for a, e in zip(actual, expected):
            same(a, e, description)
    elif isinstance(expected, (float, np.floating)):
        require(np.isclose(actual, expected, rtol=0, atol=1e-14), description)
    else:
        require(actual == expected, description)


def audit(sources, run_name):
    run, source = sources / run_name, sources / 'local-grasp-interface-run-02'
    manifest, config = read(run / 'manifest.json'), read(run / 'resolved_config.yaml')
    require(manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'reviewed clean freeze')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_short_lift_transfer.py'] == '71973b2f6f6e1f6d1500881250b2ac7740ee796cbd38ac38f191f449c45c9e63', 'reviewed adapter')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/point_temporal_probe.py'] == '86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36', 'unchanged LK helper')
    require(sha(run / 'protocol.md') == config['protocol_sha256'] == 'df80676a3628ffd1b22b9276740cce17c3f8adfaa3978054d6a458ed8bd5c8a3', 'protocol identity')
    require(sha(run / 'review.md') == manifest['review_sha256'] and FREEZE in (run / 'review.md').read_text(), 'prospective receipt')
    preflight_path = sources / 'task2-short-lift-transfer-preflight-01.json'
    require(sha(preflight_path) == manifest['preflight_sha256'] == 'ae08cc80cbc3938a3cca39ce9781a78fadf57be78f923ab1f36543b7972b23d7', 'actual preflight identity')
    preflight = read(preflight_path)
    require(manifest['code'] == preflight['code'] and manifest['python'] == preflight['python'] and manifest['cv2_version'] == '4.11.0' and manifest['cv2_threads'] == preflight['cv2_threads'], 'recorded code and environment unchanged')
    require(config['lk_settings'] == preflight['lk_settings'] and config['seed_count'] == 492 and config['captures_per_arm'] == 30 and config['references'] == REFERENCES and config['sampling_convention'] == 'nearest_center_index_floor_xy_plus_half' and config['model_physics_render_calls'] == 0, 'registered settings and full denominator')
    rows, previous = [], None
    for i, line in enumerate((run / 'episodes.jsonl').read_bytes().splitlines(keepends=True)):
        require(line.endswith(b'\n'), 'complete journal line')
        row = json.loads(line)
        require(row['seq'] == i and row['previous_record_id'] == previous and row['config_hash'] == canonical(config), 'journal links and configuration')
        require(row['record_id'] == canonical({k: v for k, v in row.items() if k != 'record_id'}), 'record hash')
        rows.append(row)
        previous = row['record_id']
    require([r['kind'] for r in rows] == ['run_start', 'input_admitted', 'arm_tracks_complete', 'arm_tracks_complete', 'sensor_outputs_sealed', 'termination'], 'complete batch and sensor seal before termination')
    for r in (rows[1], rows[4]):
        require(sha(run / ('admission.json' if r['kind'] == 'input_admitted' else 'sensor-seal.json')) == r['data']['sha256'], 'journal artifact seals')
    require([r['data'] for r in rows[2:4]] == [{'arm': a, 'tracks': 492, 'rows': 14760} for a in ARMS], 'every initialized track retained')
    require(rows[-1]['data'] == {'reason': 'all_tracks_sealed', 'tracks': 984, 'rows': 29520, 'model_physics_render_calls': 0, 'retries': 0}, 'one complete condition without retries')
    admission = read(run / 'admission.json')
    require(admission == preflight['admission'], 'exact actual inputs match reviewed preflight')
    for relative, expected in admission['source_sha256'].items():
        require(sha(source / relative) == expected, 'source receipts unchanged')
    seeds = admission['seed_pixel_index_xy']
    require(seeds == [[x, y] for y in range(169, 210) for x in range(212, 224)], 'all 492 integer seeds in row-major order')
    seed_source = sources / 'task2-box-support-run-02/sensor-representation.json'
    require(sha(seed_source) == admission['seed_sha256'], 'sealed initial support')
    initial_support = read(seed_source)['support_G']
    controls = read(source / 'sensors.json')
    original = sources/'task2-box-temporal-run-01'
    for name, digest in admission['original_track_source_sha256'].items():
        require(sha(original/name) == digest, 'original native-track source unchanged')
    prefix = read(run/'prefix-agreement.json')
    require(prefix['comparison_uses_masks'] is False, 'causal prefix check excludes masks')
    require(admission['initial_own_tcp_world_m'] is None and admission['initial_own_tcp_status'] == 'unknown_not_archived', 'initial own TCP remains unknown')
    source_seal = read(source / 'sensor-seal.json')['sha256']
    sensor_seal = read(run / 'sensor-seal.json')
    require(sensor_seal['evaluator_read'] is False and set(sensor_seal['sha256']) == {'close-tracks.jsonl', 'open_hold-tracks.jsonl', 'sensor-summary.json', 'prefix-agreement.json'}, 'sensor-only output seal')
    require(all(sha(run / name) == digest for name, digest in sensor_seal['sha256'].items()), 'all sensor artifact hashes')
    summaries = read(run / 'sensor-summary.json')
    require(summaries['holding'] is None and summaries['references'] == REFERENCES and summaries['initial_own_tcp_world_m'] is None and summaries['initial_reference_metrics'] is None, 'preclose-only reference, unknown initial TCP, no holding label')
    all_tracks, report, flow_calls = {}, {}, {}
    for arm in ARMS:
        metadata = admission['arms'][arm]['captures']
        depths, tcps = [], []
        for meta in metadata:
            path = source / meta['artifact']
            require(sha(path) == meta['artifact_sha256'] == source_seal[meta['artifact']], 'every admitted RGB-D source')
            with np.load(path, allow_pickle=False) as frame:
                depths.append(frame['depth_m'])
            if meta['capture_id'] == 0:
                require(meta['tcp_read_sim_time_s'] is None and meta['tcp_source_field'] is None and meta['tcp_status'] == 'unknown_initial_own_sensor_absent', 'no borrowed initial own packet')
                tcps.append(None)
            else:
                matches = [r for r in controls if r['arm'] == arm and r['step'] == meta['after_step'] and r['control'] == meta['control']]
                require(len(matches) == 1 and matches[0]['sensor']['read_sim_time_s'] == meta['tcp_read_sim_time_s'] == meta['capture_read_sim_time_s'], 'exact saved own TCP/read boundary')
                tcps.append(np.asarray(matches[0]['sensor']['tcp_fk_world_m']))
        tracks_flat = [json.loads(line) for line in (run / f'{arm}-tracks.jsonl').read_text().splitlines()]
        require(len(tracks_flat) == 492 * 30, 'complete rows including unknowns')
        tracks = [tracks_flat[i*30:(i+1)*30] for i in range(492)]
        all_tracks[arm] = tracks
        old = [json.loads(line) for line in (original/f'{arm}-tracks.jsonl').read_text().splitlines()]
        native_fields = ('frame', 'status', *RAW_FIELDS)
        expected_prefix = {'expected_rows': 6888, 'compared_native_fields': list(native_fields), 'exact_agreement': True, 'disagreements': []}
        require(prefix['arms'][arm] == expected_prefix, 'recorded complete native prefix agreement')
        for seed in range(492):
            for i in range(14):
                require({k: tracks[seed][i][k] for k in native_fields} == {k: old[seed*46+i][k] for k in native_fields}, 'all original causal native prefix fields exact')
        first_failures, calls = {}, 0
        for seed_id, track in enumerate(tracks):
            alive = True
            for i, row in enumerate(track):
                require(row['seed_id'] == seed_id and row['seed_pixel_index_xy'] == seeds[seed_id] and row['frame'] == row['capture_id'] == i, 'stable trajectory/capture identity')
                require(all(row[key] == value for key, value in metadata[i].items()), 'source metadata preserved')
                require(row['holding'] is None and row['identity_verified'] is None, 'no sensor holding/identity claim')
                require(row['own_tcp_world_m'] == (None if i == 0 else tcps[i].tolist()), 'exact own TCP or explicit initial unknown')
                require(row['sampling_convention'] == 'nearest_center_index_floor_xy_plus_half' and set(row['reference_deltas']) == {'preclose'}, 'fixed association and no initial-relative metrics')
                point, backward = row['point_pixel_index_xy'], row['attempted_backward_point_pixel_index_xy']
                if i == 0:
                    require(row['status'] == 'seeded' and point == seeds[seed_id] and all(row[k] is None for k in RAW_FIELDS if k != 'point_pixel_index_xy'), 'integer initialization without native quality claim')
                elif not alive:
                    require(row['status'] == 'unknown_after_native_failure' and all(row[k] is None for k in RAW_FIELDS), 'permanent native failure, no recovery or raw attempt')
                else:
                    calls += 1
                    if point is not None and row['forward_status'] == 1:
                        calls += 1
                    expected_alive = point is not None and backward is not None and row['forward_status'] == row['backward_status'] == 1
                    require(row['status'] == ('native_status_ok' if expected_alive else 'native_failure'), 'native admission only, no residual threshold')
                    if not expected_alive:
                        first_failures[seed_id] = i
                        alive = False
                    if row['forward_status'] != 1:
                        require(row['forward_patch_error'] is None, 'undefined forward error omitted')
                    if row['backward_status'] != 1:
                        require(row['backward_patch_error'] is None and row['forward_backward_residual_px'] is None, 'undefined backward error/residual omitted')
                    elif backward is not None:
                        expected_residual = float(np.linalg.norm(np.asarray(backward, np.float32) - np.asarray(track[i-1]['point_pixel_index_xy'], np.float32)))
                        require(np.isclose(row['forward_backward_residual_px'], expected_residual, rtol=1e-6, atol=1e-7), 'saved float32 backward residual arithmetic')
                for coordinate in (point, backward):
                    require(coordinate is None or (np.asarray(coordinate).shape == (2,) and np.isfinite(coordinate).all()), 'finite raw attempted coordinate schema')
                expected_pixel, expected_depth, valid = None, None, False
                reason = 'RGB_track_not_admitted'
                if row['status'] in ACCEPTED:
                    x, y = np.floor(np.asarray(point)+.5).astype(int)
                    reason = 'outside_image'
                    if 0 <= x < 384 and 0 <= y < 384:
                        expected_pixel = [int(x), int(y)]
                        z = float(depths[i][y, x])
                        expected_depth = z if np.isfinite(z) else None
                        valid = bool(np.isfinite(z) and .01 <= z <= 5.)
                        reason = 'valid' if valid else 'outside_valid_range' if np.isfinite(z) else 'nonfinite'
                require(row['sample_pixel_xy'] == expected_pixel and row['depth_m'] == expected_depth and row['depth_status'] == reason, 'nearest-center/bounds/original depth/validity and null semantics')
                xyz = row['surface_point_world_m']
                require((xyz is not None) == valid, 'surface admission follows depth independently of RGB lifetime')
                if valid:
                    require(np.asarray(xyz).shape == (3,) and np.isfinite(xyz).all(), 'stored world point schema; projection not rerun')
                if i == 0:
                    require(np.allclose(xyz, initial_support[seed_id]['position_world_m'], rtol=0, atol=1e-15), 'initial scalar-projected points agree with original stored support')
                for name, j in REFERENCES.items():
                    if i < j:
                        require(row['reference_deltas'][name] is None, 'no future survivor reference in approach summaries')
                        continue
                    tcp_delta = tcps[i] - tcps[j]
                    base = track[j]['surface_point_world_m']
                    expected = {'tcp_delta_m': tcp_delta.tolist(), 'point_delta_m': None, 'point_minus_tcp_delta_m': None, **{k: None for k in METRICS}}
                    if xyz is not None and base is not None:
                        delta = np.asarray(xyz) - base
                        residual = delta - tcp_delta
                        expected.update(point_delta_m=delta.tolist(), point_minus_tcp_delta_m=residual.tolist(),
                            point_delta_z_m=float(delta[2]), point_delta_norm_m=float(np.linalg.norm(delta)),
                            point_minus_tcp_delta_z_m=float(residual[2]), point_minus_tcp_delta_norm_m=float(np.linalg.norm(residual)))
                    same(row['reference_deltas'][name], expected, 'stored point/TCP displacement arithmetic')
        expected_summary = []
        for i in range(30):
            current = [t[i] for t in tracks]
            refs = {}
            for name, j in REFERENCES.items():
                metrics = {}
                for key in METRICS:
                    values = [r['reference_deltas'][name][key] for r in current if r['reference_deltas'][name] is not None and r['reference_deltas'][name][key] is not None]
                    q = np.percentile(values, [25, 50, 75], method='linear') if values else [None] * 3
                    metrics[key] = {'count': len(values), 'q25': q[0], 'median': q[1], 'q75': q[2], 'missing_count': 492-len(values)}
                refs[name] = {'reference_capture_id': j, 'available': i >= j, 'reference_surface_valid_count': sum(t[j]['surface_point_world_m'] is not None for t in tracks) if i >= j else None, 'metrics': metrics}
            expected_summary.append({'capture_id': i, 'denominator': 492,
                'native_surviving_count': sum(r['status'] in ACCEPTED for r in current),
                'valid_surface_count': sum(r['surface_point_world_m'] is not None for r in current),
                'native_failure_count': sum(r['status'] == 'native_failure' for r in current),
                'unknown_after_failure_count': sum(r['status'] == 'unknown_after_native_failure' for r in current), 'references': refs})
        same(summaries['arms'][arm], expected_summary, 'complete denominators/cohorts/fixed summaries')
        flow_calls[arm] = calls
        report[arm] = {'native_surviving_counts': [r['native_surviving_count'] for r in expected_summary],
                       'surface_valid_counts': [r['valid_surface_count'] for r in expected_summary],
                       'first_native_failure_count': len(first_failures), 'fixed_boundaries': {str(i): summaries['arms'][arm][i] for i in (0, 1, 13, 21, 22, 29)}}
    for a, b in zip(all_tracks['close'], all_tracks['open_hold']):
        require([{k: r[k] for k in RAW_FIELDS + ('status',)} for r in a[:14]] == [{k: r[k] for k in RAW_FIELDS + ('status',)} for r in b[:14]], 'identical raw LK outputs through common RGB prefix')
    evaluation = run / 'evaluation'
    for name, digest in read(evaluation / 'artifacts.json').items():
        require(sha(evaluation / name) == digest, 'evaluation artifact hashes')
    start = read(evaluation / 'evaluation-start.json')
    require(start == {'sensor_seal_sha256': sha(run / 'sensor-seal.json'), 'journal_sha256': sha(run / 'episodes.jsonl'), 'evaluator_read': False}, 'evaluator references complete sensor seal and journal')
    proxy = read(evaluation / 'proxy-membership.json')
    for path, digest in proxy['mask_sha256'].items():
        require(sha(path) == digest, 'evaluated mask bytes match postseal receipt')
    for arm in ARMS:
        masks = [np.load(source / f'evaluator-only/{arm}-{i:04d}-bottle-mask.npy', allow_pickle=False) for i in range(30)]
        memberships, departures, seen_inside = [], {}, set()
        for track in all_tracks[arm]:
            for row in track:
                pixel = row['sample_pixel_xy']
                value = None if pixel is None or row['status'] not in ACCEPTED else bool(masks[row['capture_id']][pixel[1], pixel[0]])
                item = {'seed_id': row['seed_id'], 'capture_id': row['capture_id'], 'proxy_membership': value, 'tracker_status': row['status'], 'sample_pixel_xy': pixel}
                memberships.append(item)
                seed_id = str(row['seed_id'])
                if value is False and seed_id in seen_inside and seed_id not in departures:
                    departures[seed_id] = item
                if value is True:
                    seen_inside.add(seed_id)
        counts = [{'capture_id': i, 'denominator': 492, 'proxy_true': sum(r['proxy_membership'] is True for r in memberships if r['capture_id'] == i),
                   'proxy_false': sum(r['proxy_membership'] is False for r in memberships if r['capture_id'] == i),
                   'proxy_unknown': sum(r['proxy_membership'] is None for r in memberships if r['capture_id'] == i)} for i in range(30)]
        require(proxy['arms'][arm] == {'rows': memberships, 'counts': counts, 'first_observed_departure_after_proxy_true': departures, 'resolved_depth_ownership': None, 'semantic_confidence': None}, 'all postseal mask memberships/unknowns and first departure semantics')
        report[arm]['proxy_counts'] = counts
        report[arm]['observed_departure_seed_count'] = len(departures)
        report[arm]['first_observed_departure'] = min(departures.values(), key=lambda r: (r['capture_id'], r['seed_id'])) if departures else None
        adjacent = [memberships[seed*30+i] for seed in range(492) for i in range(22,30)
                    if memberships[seed*30+i-1]['proxy_membership'] is True and memberships[seed*30+i]['proxy_membership'] is False]
        first_lift = min(adjacent, key=lambda r: (r['capture_id'], r['seed_id'])) if adjacent else None
        report[arm]['first_adjacent_lift_departure'] = first_lift
        report[arm]['first_adjacent_lift_departure_context'] = ([] if first_lift is None else
            all_tracks[arm][first_lift['seed_id']][first_lift['capture_id']-1:first_lift['capture_id']+2])
        report[arm]['final_saved_tcp_delta_m'] = all_tracks[arm][0][29]['reference_deltas']['preclose']['tcp_delta_m']
    return {'status': 'pass', 'freeze': FREEZE, 'journal_records': len(rows), 'journal_sha256': sha(run / 'episodes.jsonl'),
            'sensor_seal_sha256': sha(run / 'sensor-seal.json'), 'sensor_summary_sha256': sha(run / 'sensor-summary.json'),
            'proxy_sha256': sha(evaluation / 'proxy-membership.json'), 'tracks': 984, 'track_rows': 29520,
            'native_flow_calls_implied_by_saved_statuses': flow_calls, 'arms': report,
            'limits': ['all saved rows, source hashes, sample pixels/depths, displacements, summaries and proxy memberships independently checked',
                       'no LK, projection, FK, inference, physics or rendering rerun; world-coordinate generation source-reviewed',
                       'mask hashes record evaluated bytes after sensor seal, not historical ownership truth',
                       'sensor-before-evaluator ordering source-reviewed and complete seal/journal referenced; evaluator start lacks independent wall timestamp',
                       'one dependent paired trajectory; no identity/holding classifier, selected-survivor success or independent-trial claim']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--run', default='task2-short-lift-transfer-run-01')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources, args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'arms'}, indent=2))
