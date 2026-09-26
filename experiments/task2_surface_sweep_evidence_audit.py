"""Independent sealed-array audit; never invokes FK, projection, or hull distance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from task2_box_evidence_audit import read, require, sha

FREEZE = 'cb394fdaaa90f4dd0ba984f657130c70bcae9dad'
MOVES = {'MV_FWD': [.01, 0., 0.], 'MV_BACK': [-.01, 0., 0.], 'MV_LEFT': [0., .01, 0.],
         'MV_RIGHT': [0., -.01, 0.], 'MV_UP': [0., 0., .01], 'MV_DOWN': [0., 0., -.01], 'STOP': [0., 0., 0.]}
GEOMS = ['gripper0_hand_collision', 'gripper0_finger1_collision', 'gripper0_finger1_pad_collision',
         'gripper0_finger2_collision', 'gripper0_finger2_pad_collision']
MODES = ('current', 'endpoint', 'sweep')


def audit(sources, run_name):
    run = sources / run_name
    manifest, admission, request = [read(run / name) for name in ('manifest.json', 'admission.json', 'request.json')]
    require(manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'clean reviewed freeze')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_observed_surface_sweep.py'] == '5d12ce8cf3389746b8e44e3b08b34f6cc2475ae5ac5e0d134476594c440b3e7d', 'reviewed numerical source')
    require(sha(run / 'protocol.md') == manifest['protocol_sha256'] == 'd4c6fbee81c4979a113ee0fed2ea030c0f7152ecdb5c210f58af5ee32601ebfe', 'frozen protocol')
    require(sha(run / 'request.json') == manifest['request_sha256'] and sha(run / 'review.txt') == manifest['review_sha256'], 'sanitized input and prospective receipt hashes')
    require(FREEZE in (run / 'review.txt').read_text() and 'PASS' in (run / 'review.txt').read_text(), 'prospective review names freeze')
    preflight = read(sources / 'task2-observed-surface-sweep-preflight-01.json')
    require(admission == {k: v for k, v in preflight.items() if k != 'code'}, 'run admission exactly matches reviewed preflight')
    for relative, expected in admission['source_sha256'].items():
        require(sha(sources / relative) == expected, 'original source bytes')
    require(set(request) == {'calibration', 'own_packets', 'full_support', 'inner_indices'}, 'four-field sanitized request')
    require(list(request['own_packets']) == ['sample0', 'sample1'], 'opaque sample names')
    source_rows = [json.loads(line) for line in (sources / 'task2-box-point-boundary-run-01/episodes.jsonl').read_text().splitlines()]
    by_id = {row['record_id']: row for row in source_rows}
    for sample, selection in admission['selections'].items():
        obs = by_id[selection['record_id']]['data']['previous_returned_own_observations']
        expected = {k: obs[k] for k in ('robot0_eef_pos', 'robot0_eef_quat', 'robot0_gripper_qpos')}
        require(request['own_packets'][sample] == expected, 'unaltered paired returned own packet')
    original_calibration = read(sources / 'robot-geometry-observability-03/robot-calibration.json')
    calibration = request['calibration']
    require(set(calibration) == {'version', 'bodies', 'sites', 'geometries'}, 'own subtree schema')
    require(calibration['geometries'] == original_calibration['geometries'] and [g['name'] for g in calibration['geometries']] == GEOMS, 'all sealed proxy vertices retained in order')
    expected_bodies, descendants = [], {'robot0_right_hand'}
    for body in original_calibration['bodies']:
        if body['name'] == 'robot0_right_hand':
            expected_bodies.append({**body, 'parent': None, 'position_parent_m': [0., 0., 0.], 'quaternion_parent_wxyz': [1., 0., 0., 0.]})
        elif body['parent'] in descendants:
            descendants.add(body['name'])
            expected_bodies.append(body)
    require(calibration['bodies'] == expected_bodies and calibration['sites'] == [s for s in original_calibration['sites'] if s['name'] == 'gripper0_grip_site'], 'normalized hand subtree removes arm/base only')
    support = request['full_support']
    require(all(set(row) == {'pixel_xy', 'depth_m', 'position_world_m'} for row in support), 'no excluded fields in support')
    inner = np.asarray(request['inner_indices'], dtype=int)
    require(len(inner) == 492 and len(support) == 1340 and list(inner) == sorted(set(inner)), 'full support count and ordered exact inner indices')
    sensor = read(sources / 'task2-box-support-run-02/sensor-representation.json')
    require([support[i] for i in inner] == [{k: row[k] for k in ('pixel_xy', 'depth_m', 'position_world_m')} for row in sensor['support_G']], 'exact saved inner support values without projection')
    with np.load(sources / 'interaction-observability-paired-01/close/0000.npz', allow_pickle=False) as frame:
        depth = frame['depth_m']
    expected_pixels = [(x, y) for y in range(156, 223) for x in range(208, 228)
                       if np.isfinite(depth[y, x]) and .01 <= depth[y, x] <= 5]
    require([tuple(row['pixel_xy']) for row in support] == expected_pixels, 'all full-BOX valid source pixels in row-major order')
    require(all(row['depth_m'] == float(depth[y, x]) for row, (x, y) in zip(support, expected_pixels)), 'unaltered full-support depths')
    points = np.asarray([row['position_world_m'] for row in support])
    require(points.shape == (1340, 3) and np.isfinite(points).all(), 'stored world-point schema; no projection repeated')
    seal = read(run / 'feature-seal.json')
    require(set(seal) == {str(p.relative_to(run)) for p in (run / 'features').iterdir()} and len(seal) == 15, 'complete 14 arrays plus summary seal')
    require(all(sha(run / relative) == expected for relative, expected in seal.items()), 'all numerical artifacts sealed')
    result = read(run / 'features/features.json')
    require(result['candidate_order'] == list(MOVES) and result['geometry_order'] == GEOMS, 'registered candidate and proxy order')
    require(list(result['samples']) == ['sample0', 'sample1'], 'both samples retained')
    table, contained_pixels = {}, {}
    max_witness_residual = 0.
    for sample_name, sample in result['samples'].items():
        require(list(sample['candidates']) == list(MOVES) and list(sample['proxy_vertices_world_m']) == GEOMS, 'complete canonical outputs')
        table[sample_name], contained_pixels[sample_name] = {}, {}
        current_reference = None
        for token, candidate in sample['candidates'].items():
            require(candidate['nominal_delta_m'] == MOVES[token], 'unaltered nominal translation')
            array_path = run / 'features' / candidate['artifact']
            require(sha(array_path) == candidate['artifact_sha256'], 'array summary seal')
            with np.load(array_path, allow_pickle=False) as archive:
                arrays = {key: archive[key] for key in archive.files}
            require(set(arrays) == {mode+'_'+key for mode in MODES for key in ('distance', 'closest', 'inside')}, 'complete array schema')
            if current_reference is None:
                current_reference = {key: arrays['current_'+key] for key in ('distance', 'closest', 'inside')}
            require(all(np.array_equal(arrays['current_'+key], value) for key, value in current_reference.items()), 'same current solid arrays across every candidate')
            if token == 'STOP':
                require(all(np.array_equal(arrays[mode+'_'+key], arrays['current_'+key]) for mode in ('endpoint', 'sweep') for key in ('distance', 'closest', 'inside')), 'STOP equals current arrays exactly')
            table[sample_name][token] = {}
            contained_pixels[sample_name][token] = {}
            for mode in MODES:
                distance, closest, inside = [arrays[mode+'_'+key] for key in ('distance', 'closest', 'inside')]
                require(distance.shape == (1340, 5) and closest.shape == (1340, 5, 3) and inside.shape == (1340, 5), 'array shapes')
                require(inside.dtype == np.bool_ and np.isfinite(distance).all() and np.isfinite(closest).all() and (distance >= 0).all(), 'finite nonnegative distances and Boolean containment')
                residual = np.max(np.abs(np.linalg.norm(points[:, None, :] - closest, axis=2) - distance))
                max_witness_residual = max(max_witness_residual, float(residual))
                require(residual <= 1e-12, 'stored closest-point displacement norm agrees with stored distance')
                require((distance[inside] == 0).all() and np.array_equal(closest[inside], np.broadcast_to(points[:, None, :], closest.shape)[inside]), 'contained points have zero distance and self witness')
                for group, indices in (('inner', inner), ('full', np.arange(len(support)))):
                    summary = candidate['supports'][group][mode]
                    require(list(summary) == GEOMS + ['union'], 'complete proxy and union summaries')
                    for label, columns in [(name, [i]) for i, name in enumerate(GEOMS)] + [('union', list(range(5)))]:
                        values = distance[np.ix_(indices, columns)]
                        minimum = values.min()
                        winners = np.argwhere(values == minimum)
                        first_point, first_proxy = int(indices[winners[0, 0]]), columns[winners[0, 1]]
                        expected = {'point_count': len(indices), 'minimum_m': float(minimum),
                            'contained_point_count': int(np.count_nonzero(inside[np.ix_(indices, columns)].any(axis=1))),
                            'exact_minimizer_count': len(winners),
                            'nearest': {**support[first_point], 'full_support_index': first_point, 'proxy': GEOMS[first_proxy],
                                'closest_solid_point_world_m': closest[first_point, first_proxy].tolist(), 'inside': bool(inside[first_point, first_proxy])}}
                        require(summary[label] == expected, 'every summary, primary witness, and exact tie count independently recomputed from stored arrays')
                    table[sample_name][token].setdefault(group, {})[mode] = {key: summary['union'][key] for key in ('minimum_m', 'contained_point_count', 'exact_minimizer_count')}
                contained_pixels[sample_name][token][mode] = [support[i]['pixel_xy'] for i in np.flatnonzero(inside.any(axis=1))]
            require(np.all(arrays['sweep_distance'] <= arrays['current_distance'] + 1e-12) and np.all(arrays['sweep_distance'] <= arrays['endpoint_distance'] + 1e-12), 'sweep contains current and endpoint distance inequality')
            for mode in MODES:
                require(candidate['supports']['full'][mode]['union']['minimum_m'] <= candidate['supports']['inner'][mode]['union']['minimum_m'], 'full-support superset inequality')
    evaluator = read(run / 'evaluator-after-seal.json')
    robot = set(next(row['data'] for row in source_rows if row['kind'] == 'initial_frame_gate')['groups_evaluator_only']['robot'])
    for step, expected_token in ((21, 'MV_DOWN'), (22, 'MV_FWD')):
        observed = evaluator[str(step)]
        require(observed['executed'] == expected_token and observed['unexecuted_outcomes'] == {token: None for token in MOVES if token != expected_token}, 'only executed outcomes observed')
        contacts = [{'stage': row['kind'], 'record_id': row['record_id'], **{key: row['data'][key] for key in ('step', 'control', 'index', 'time_s')}, 'contact': contact}
                    for row in source_rows if row['kind'] in ('native_before', 'native_after') and row['data']['step'] == step
                    for contact in row['data']['contacts'] if robot.intersection(contact['geom_ids'])]
        require(observed['raw_robot_contacts'] == contacts, 'all actual contact rows retained separately from numerical features')
        require(len(contacts) == (0 if step == 21 else 26), 'registered no-raw versus first-raw boundary')
    return {'status': 'pass', 'freeze': FREEZE, 'request_sha256': sha(run / 'request.json'), 'feature_seal_sha256': sha(run / 'feature-seal.json'),
            'features_sha256': sha(run / 'features/features.json'), 'evaluator_sha256': sha(run / 'evaluator-after-seal.json'),
            'samples': 2, 'candidates_per_sample': 7, 'proxies': 5, 'modes': 3, 'full_points': 1340, 'inner_points': 492,
            'max_stored_closest_point_distance_residual_m': max_witness_residual, 'union_results': table, 'all_contained_pixels': contained_pixels,
            'limits': ['stored hashes, schemas, exact source values and array/scalar arithmetic only; no FK, projection or hull recomputation',
                       'seal-before-evaluator order source-reviewed; no wall-time journal in this adapter',
                       'conditional historic own calibration; exact asset-byte identity not established',
                       'all six unexecuted outcomes at each sample remain UNKNOWN; no clearance or policy claim']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources, args.run)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('union_results', 'all_contained_pixels')}, indent=2))
