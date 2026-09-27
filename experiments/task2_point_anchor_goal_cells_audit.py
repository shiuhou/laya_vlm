"""Independent stored 18-placement audit from historical fixed proxy facets."""
from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

from task2_box_evidence_audit import read, require, sha

FREEZE = '77523e59b2a66dd13665a15e996048198526ad4f'
SOURCE_AUDIT = 'c083504fe4574f01a472c4cf957a61ff016055ebc069b4fcb23f752d8bc467d1'
GEOMS = ['gripper0_hand_collision', 'gripper0_finger1_collision', 'gripper0_finger1_pad_collision',
         'gripper0_finger2_collision', 'gripper0_finger2_pad_collision']
CONDITIONS = ['whole', 'neck']
SENSORS = {'whole': '87fb2c2b9587ae1cd08f85d4bf331288c20b4b50b65aa6f0132b78294eb3cef5',
           'neck': 'fd6edea327618a8bb86a52dafe48fe2d857a2e71fa7677bdcadb89d65657fd0d'}


def arrays(path):
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == {'inside', 'hypothetical_TCP_world_m'}, 'complete tensor schema')
        return saved['inside'].copy(), saved['hypothetical_TCP_world_m'].copy()


def audit(sources):
    run = sources / 'task2-point-anchor-goal-cells-run-01'
    old = sources / 'task2-point-goal-cell-run-01'
    point_source = sources / 'task2-point-region-control-run-01'
    manifest, request = read(run / 'manifest.json'), read(run / 'request.json')
    preflight_path = sources / 'task2-point-anchor-goal-cells-preflight-01.json'
    require(sha(preflight_path) == manifest['preflight_sha256']
            == '05880a632bb46b5ca9e8d08fc839f794acc41594c35e6476481b5bc0d3d5bb8c', 'reviewed preflight')
    preflight = read(preflight_path)
    require(all(manifest[k] == v for k, v in preflight.items() if k != 'python'), 'all preflight provenance')
    require(manifest['code']['commit'] == FREEZE and not manifest['code']['dirty_status'], 'clean exact freeze')
    require(manifest['code']['source_sha256']['embodied_runtime/experiments/task2_point_anchor_goal_cells.py']
            == 'c7daa7bdf491e340854084ac5ddefeebe83e4cb93931fcead6867f79e64770ec', 'reviewed worker')
    require(sha(run / 'protocol.md') == manifest['protocol_sha256']
            == '18ef17b66d529cb8d4c828af1a55cb8277f6b98aa2f7e28212b0c83dea094da1', 'protocol identity')
    require(sha(run / 'review.md') == manifest['review_sha256'] and FREEZE in (run / 'review.md').read_text()
            and 'Prospective PASS' in (run / 'review.md').read_text(), 'prior exact-freeze PASS')
    require(not (run / 'failure.json').exists(), 'no ignored failure')
    require(sha(run / 'source-admission-audit.json') == manifest['source_admission_audit_sha256'] == SOURCE_AUDIT, 'source admission closure')
    source_audit = read(run / 'source-admission-audit.json')
    require(source_audit['status'] == source_audit['source_admission'] == 'pass'
            and source_audit['sensor_sha256'] == SENSORS, 'immutable lowercase source gate')
    for field, base in [('sources_sha256', sources), ('anchor_source_sha256', point_source),
                        ('original_BOX_cell_secondary_reference_sha256', old)]:
        for name, digest in manifest[field].items():
            require(sha(base / name) == digest, 'source unchanged: ' + name)
    for field in ('helpers_sha256', 'anchor_helper_sha256'):
        require(all(manifest['code']['source_sha256'][name] == digest for name, digest in manifest[field].items()), 'helper identities')
    require(manifest['source_point_request_sha256'] == sha(point_source / 'request.json')
            == '762de6e4a955882fb987988cf561eba36cc5edb9f7dbd6e873e3dcd965db7b9e', 'source POINT request')
    old_request, old_result = read(old / 'request.json'), read(old / 'features/result.json')
    anchors = []
    for index, condition in enumerate(CONDITIONS):
        sensor_path = point_source / condition / 'sensor-result.json'
        require(sha(sensor_path) == SENSORS[condition], 'exact admitted source sensor')
        sensor, closure = read(sensor_path), source_audit['conditions'][index]
        require(closure['condition'] == condition and closure['point'] == sensor['point']
                and closure['status'] == sensor['status'] == 'admitted_sensor_point', 'ordered admitted point binding')
        require(manifest['anchor_provenance'][index]['condition'] == condition
                and manifest['anchor_provenance'][index]['point'] == sensor['point']
                and manifest['anchor_provenance'][index]['sensor_result_sha256'] == SENSORS[condition], 'anchor provenance')
        anchors.append({'condition': condition, 'point_P_world_m': sensor['point']['position_world_m']})
    shared = {k: old_request[k] for k in ('calibration', 'full_support', 'terminal_own_packet', 'nominal_step_m')}
    require(request == {**shared, 'anchors': anchors}, 'only registered point substitutions into exact historical request')
    require(sha(run / 'request.json') == manifest['request_sha256'], 'geometry request identity')
    require(manifest['new_placements'] == 18 and manifest['original_BOX_reference_recomputed'] is False
            and manifest['source_masks_or_visual_receipts_opened'] is False, 'offline bounded source scope')
    seal = read(run / 'feature-seal.json')
    expected_files = {'features/result.json', 'features/containment.npz',
                      'features/whole/result.json', 'features/whole/containment.npz',
                      'features/neck/result.json', 'features/neck/containment.npz'}
    require(set(seal) == expected_files == {str(p.relative_to(run)) for p in (run / 'features').rglob('*') if p.is_file()}, 'recursive complete seal')
    for name, digest in seal.items():
        require(sha(run / name) == digest, 'sealed feature ' + name)
    result = read(run / 'features/result.json')
    require(result['condition_order'] == CONDITIONS and result['tensor_shape'] == [2, 9, 1340, 5]
            and result['geometry_order'] == GEOMS, 'registered axes/order/shape')
    require(result['nominal_step_m'] == .01 and result['axis_stop_cell_half_width_m'] == .005
            and result['halfspace_numeric_tolerance'] == 1e-12 and result['physical_margin_m'] == 0.
            and result['terminal_own_packet'] == shared['terminal_own_packet'], 'fixed rule/own/tolerance')
    require(result['new_placements'] == 18 and result['original_BOX_reference_recomputed'] is False
            and result['new_model_physics_render_calls'] == 0 and result['no_selected_anchor_or_pose']
            and result['automatic_extension'] is False, 'bounded calculation')
    require(result['containment_artifact_sha256'] == sha(run / 'features/containment.npz'), 'combined tensor identity')
    inside, positions = arrays(run / 'features/containment.npz')
    require(inside.dtype == np.bool_ and inside.shape == (2, 9, 1340, 5)
            and positions.shape == (2, 9, 3) and np.isfinite(positions).all(), 'complete tensor')
    signs = np.asarray(list(product((-1, 1), repeat=3)))
    expected_positions = np.stack([np.vstack((anchor['point_P_world_m'], np.asarray(anchor['point_P_world_m']) + signs * .005)) for anchor in anchors])
    require(np.array_equal(positions, expected_positions), 'all 18 exact registered TCP placements')
    separate = []
    for index, condition in enumerate(CONDITIONS):
        directory = run / 'features' / condition
        single, saved_positions = arrays(directory / 'containment.npz')
        require(np.array_equal(single, inside[index]) and np.array_equal(saved_positions, positions[index]), 'combined/per-condition arrays identical')
        child = read(directory / 'result.json')
        require(child['containment_artifact_sha256'] == sha(directory / 'containment.npz')
                and child['array_shape'] == [9, 1340, 5] and child['geometry_order'] == GEOMS
                and child['point_P_world_m'] == anchors[index]['point_P_world_m']
                and child['terminal_own_packet'] == shared['terminal_own_packet'], 'child schema/source')
        require(child['nominal_step_m'] == .01 and child['axis_stop_cell_half_width_m'] == .005
                and child['halfspace_numeric_tolerance'] == 1e-12 and child['physical_margin_m'] == 0
                and child['no_pose_search'] and child['no_dynamics'] and child['new_model_calls'] == 0, 'unchanged child scope')
        require(len(child['placements']) == 9, 'all nine rows')
        separate.append(child)
    full = shared['full_support']
    points = np.asarray([row['position_world_m'] for row in full])
    require(points.shape == (1340, 3) and np.isfinite(points).all(), 'full unchanged observed support')
    historical = old_result['placements'][0]
    historical_tcp = np.asarray(historical['hypothetical_TCP_world_m'])
    require(historical['hypothetical_TCP_world_m'] == old_request['point_P_world_m'], 'sealed historical reference')
    checked, slack = np.zeros_like(inside), np.empty(inside.shape)
    producer_checked, producer_slack = np.zeros_like(inside), np.empty(inside.shape)
    numeric = result['fixed_facet_numerical_check']
    require(numeric['reference_condition'] == 'whole' and numeric['reference_placement_index'] == 0
            and numeric['tensor_entries_checked'] == 120600 and numeric['fixed_facet_memberships_match_all_entries']
            and numeric['numerical_slack_is_not_physical_margin_or_uncertainty'], 'fixed facet check scope')
    max_historical_residual, producer_translation_residual, facet_counts = 0., 0., {}
    for column, name in enumerate(GEOMS):
        base = np.asarray(historical['proxy_vertices_world_m'][name])
        equations = ConvexHull(base).equations  # Only one historical facet system per proxy.
        facet_counts[name] = len(equations)
        producer_base = np.asarray(separate[0]['placements'][0]['proxy_vertices_world_m'][name])
        producer_facets = np.asarray(numeric['fixed_facet_equations'][name])
        require(producer_facets.ndim == 2 and producer_facets.shape[1] == 4
                and np.isfinite(producer_facets).all(), 'saved producer facet schema')
        require(np.allclose(np.linalg.norm(producer_facets[:, :3], axis=1), 1., rtol=0, atol=1e-12), 'signed slack has normalized facets')
        vertex_eval = producer_base @ producer_facets[:, :3].T + producer_facets[:, 3]
        require(np.all(vertex_eval <= 1e-12) and np.all(np.abs(vertex_eval).min(axis=0) <= 1e-12), 'saved facets support original proxy')
        # Each producer facet must match a historical facet translated to the producer reference.
        translated = equations.copy()
        translated[:, 3] -= equations[:, :3] @ (positions[0, 0] - historical_tcp)
        require(all(np.min(np.max(np.abs(translated - facet), axis=1)) <= 1e-12 for facet in producer_facets), 'producer facets match historical solid')
        require(all(np.min(np.max(np.abs(producer_facets - facet), axis=1)) <= 1e-12 for facet in translated), 'no missing historical facet')
        for anchor in range(2):
            for index in range(9):
                moved = np.asarray(separate[anchor]['placements'][index]['proxy_vertices_world_m'][name])
                delta = positions[anchor, index] - historical_tcp
                residual = float(np.max(np.abs(moved - (base + delta))))
                max_historical_residual = max(max_historical_residual, residual)
                require(residual <= 1e-12, 'all new vertices translate audited historical proxy')
                signed = -((points - delta) @ equations[:, :3].T + equations[:, 3])
                checked[anchor, index, :, column] = np.all(signed >= -1e-12, axis=1)
                slack[anchor, index, :, column] = signed.min(axis=1)
                producer_delta = positions[anchor, index] - positions[0, 0]
                producer_translation_residual = max(producer_translation_residual,
                    float(np.max(np.abs(moved - (producer_base + producer_delta)))))
                saved_signed = -((points - producer_delta) @ producer_facets[:, :3].T + producer_facets[:, 3])
                producer_checked[anchor, index, :, column] = np.all(saved_signed >= -1e-12, axis=1)
                producer_slack[anchor, index, :, column] = saved_signed.min(axis=1)
    require(np.array_equal(checked, inside) and np.array_equal(producer_checked, inside), 'all120600 entries independently match')
    require(producer_translation_residual == numeric['maximum_proxy_translation_residual_m'], 'reported translation residual')
    require(np.allclose(slack, producer_slack, rtol=0, atol=1e-12), 'all minimum facet slacks agree across reference frames')
    conditions = []
    for anchor, condition in enumerate(CONDITIONS):
        child, combined = separate[anchor], result['conditions'][anchor]
        for index, placement in enumerate(child['placements']):
            require(placement['index'] == index and placement['kind'] == ('exact_P' if index == 0 else 'cell_corner')
                    and placement['corner_signs'] == (None if index == 0 else signs[index - 1].tolist())
                    and placement['hypothetical_TCP_world_m'] == positions[anchor, index].tolist(), 'every placement identity')
            require(placement['returned_orientation_and_jaws_unchanged'] and placement['mount'] == historical['mount'], 'unchanged orientation/mount/jaws')
            require(placement['any_containment'] == bool(inside[anchor, index].any())
                    and placement['contained_point_union_count'] == int(inside[anchor, index].any(axis=1).sum()), 'every union/count')
            require(set(placement['per_proxy']) == set(GEOMS) == set(placement['proxy_vertices_world_m']), 'all five separate solids')
            for column, name in enumerate(GEOMS):
                indices = np.flatnonzero(inside[anchor, index, :, column]).tolist()
                require(placement['per_proxy'][name] == {'contained_point_count': len(indices), 'full_support_indices': indices}, 'every point/proxy index')
        pairs = np.argwhere(inside[anchor, 1:].all(axis=0))
        witnesses = [{'full_support_index': int(point), 'proxy': GEOMS[column], **full[point]} for point, column in pairs]
        require(child['same_point_same_proxy_all_eight_corner_witnesses'] == witnesses, 'complete same-pair corner intersection per anchor')
        require(all(inside[anchor, 0, point, column] for point, column in pairs), 'all common witnesses contain exact center')
        exact = bool(inside[anchor, 0].any())
        unions = [int(row.any(axis=1).sum()) for row in inside[anchor, 1:]]
        all_unions = all(count > 0 for count in unions)
        require(child['exact_P_any_containment'] == exact and child['all_eight_corner_unions_positive'] == all_unions
                and child['entire_axis_stop_cell_excluded_at_fixed_orientation_jaws'] == bool(len(pairs)), 'child claims')
        certificate = 'entire_original_rule_goal_cell_excluded' if len(pairs) else 'no_common_witness_certificate'
        require(combined == {'condition': condition, 'point_P_world_m': anchors[anchor]['point_P_world_m'],
            'exact_center_status': 'contained' if exact else 'no_observed_point_containment', 'exact_P_any_containment': exact,
            'corner_union_counts': unions, 'all_eight_corner_unions_positive': all_unions,
            'common_same_point_same_proxy_count': len(pairs), 'certificate': certificate,
            'absence_of_common_witness_is_inconclusive': not bool(len(pairs)),
            'exact_center_noncontainment_is_not_clearance_or_feasibility': True,
            'complete_result': condition + '/result.json', 'complete_result_sha256': sha(run / 'features' / condition / 'result.json')}, 'combined condition fields')
        numeric_row = numeric['conditions'][anchor]
        require(numeric_row['condition'] == condition and len(numeric_row['common_pair_checks']) == len(pairs), 'all numeric witnesses')
        independent_witnesses, producer_minima = [], []
        for (point, column), saved in zip(pairs, numeric_row['common_pair_checks']):
            recorded = producer_slack[anchor, 1:, point, column]
            require(saved == {'full_support_index': int(point), 'proxy': GEOMS[column],
                'center_minimum_signed_facet_slack_m': float(producer_slack[anchor, 0, point, column]),
                'corner_minimum_signed_facet_slacks_m': recorded.tolist(), 'minimum_signed_corner_facet_slack_m': float(recorded.min()),
                'strictly_inside_all_corners': bool(np.all(recorded > 0.))}, 'every saved witness signed slack')
            producer_minima.append(float(recorded.min()))
            margins = slack[anchor, 1:, point, column]
            independent_witnesses.append({'full_support_index': int(point), 'pixel_xy': full[point]['pixel_xy'], 'proxy': GEOMS[column],
                'center_minimum_signed_facet_slack_m': float(slack[anchor, 0, point, column]),
                'corner_minimum_signed_facet_slacks_m': margins.tolist(), 'minimum_signed_corner_facet_slack_m': float(margins.min()),
                'strictly_inside_all_corners': bool(np.all(margins > 0.))})
        strict = bool(len(pairs)) and all(row['strictly_inside_all_corners'] for row in independent_witnesses)
        require(numeric_row['all_common_pairs_strictly_inside'] == strict
                and numeric_row['minimum_common_pair_corner_slack_m'] == min(producer_minima, default=None)
                and numeric_row['maximum_common_pair_corner_slack_m'] == max(producer_minima, default=None), 'strict slack summaries including null case')
        conditions.append({'condition': condition, 'point_P_world_m': anchors[anchor]['point_P_world_m'],
            'exact_P_any_containment': exact, 'exact_P_contained_point_union_count': int(inside[anchor, 0].any(axis=1).sum()),
            'per_placement_union_counts': [int(row.any(axis=1).sum()) for row in inside[anchor]],
            'per_placement_proxy_counts': [row.sum(axis=0).tolist() for row in inside[anchor]],
            'common_same_point_same_proxy_count': len(pairs), 'certificate': certificate,
            'all_common_pairs_strictly_inside': strict, 'common_pair_slacks': independent_witnesses,
            'minimum_common_pair_corner_slack_m': min((row['minimum_signed_corner_facet_slack_m'] for row in independent_witnesses), default=None),
            'maximum_common_pair_corner_slack_m': max((row['minimum_signed_corner_facet_slack_m'] for row in independent_witnesses), default=None)})
    return {'status': 'PASS', 'producer_commit': FREEZE, 'raw_directory': str(run),
        'request_sha256': sha(run / 'request.json'), 'feature_seal_sha256': sha(run / 'feature-seal.json'),
        'source_admission_audit_sha256': SOURCE_AUDIT, 'source_point_request_sha256': manifest['source_point_request_sha256'],
        'source_sensor_sha256': SENSORS, 'tensor_entries_checked': int(inside.size),
        'result_sha256': sha(run / 'features/result.json'), 'tensor_sha256': sha(run / 'features/containment.npz'),
        'condition_order': CONDITIONS, 'conditions': conditions, 'fixed_facets_per_proxy': facet_counts,
        'maximum_historical_proxy_translation_residual_m': max_historical_residual,
        'producer_maximum_proxy_translation_residual_m': producer_translation_residual,
        'maximum_independent_vs_producer_minimum_facet_slack_difference_m': float(np.max(np.abs(slack - producer_slack))),
        'limits': ['PASS concerns evidence integrity independently of either anchor outcome; no dynamics authorization',
                   'historical sealed original BOX exact-P geometry anchors one fixed facet system per proxy for all 18 translations',
                   'stored vertices, arrays and scalar equations only; no FK/projection/model/physics/render rerun or new placement',
                   'exact-center noncontainment is not physical clearance or feasibility; absent common witnesses are inconclusive about whole-cell exclusion',
                   'signed slacks characterize frozen geometric calculation and are not physical safety margins or uncertainty estimates']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, default=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sources)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({**result, 'conditions': [{k: v for k, v in row.items() if k != 'common_pair_slacks'} for row in result['conditions']]}, indent=2))
