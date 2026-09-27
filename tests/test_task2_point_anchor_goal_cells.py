from copy import deepcopy
from itertools import product

import numpy as np
import pytest

from embodied_runtime.experiments import task2_point_anchor_goal_cells as matched


def synthetic_pair():
    # Two distant anchor cells share geometry/support but have distinct witnesses.
    points = np.asarray([[0., 0., 0.], [10., 0., 0.]])
    positions = np.stack([matched.cell.axis_stop_cell(p)[0] for p in points])
    cube = np.asarray(list(product((-1., 1.), repeat=3)))
    vertices, inside = [], np.zeros((2, 9, 2, 5), bool)
    for anchor in range(2):
        rows = []
        for index, tcp in enumerate(positions[anchor]):
            proxies = {}
            for column, name in enumerate(matched.cell.geometry.GEOMS):
                shift = np.array([0., column*10., 0.])
                proxies[name] = (cube+shift+tcp).tolist()
                inside[anchor, index, :, column] = (np.abs(points-tcp-shift) <= 1.).all(axis=1)
            rows.append(proxies)
        vertices.append(rows)
    return points, positions, vertices, inside


def test_matched_fixed_facets_preserve_each_anchor_witness_and_all_corner_order():
    points, positions, vertices, inside = synthetic_pair()
    result = matched.fixed_facet_check(points, positions, vertices, inside)
    assert result['tensor_entries_checked'] == 180
    assert result['fixed_facet_memberships_match_all_entries']
    assert result['maximum_proxy_translation_residual_m'] < 1e-12
    for anchor, row in enumerate(result['conditions']):
        assert row['condition'] == matched.CONDITIONS[anchor]
        assert len(row['common_pair_checks']) == 1
        witness = row['common_pair_checks'][0]
        assert witness['full_support_index'] == anchor
        assert witness['proxy'] == matched.cell.geometry.GEOMS[0]
        assert witness['center_minimum_signed_facet_slack_m'] == 1.
        assert np.allclose(witness['corner_minimum_signed_facet_slacks_m'], .995, rtol=0, atol=1e-14)
        assert row['all_common_pairs_strictly_inside']


def test_fixed_facet_check_rejects_one_changed_membership_and_nontranslation():
    points, positions, vertices, inside = synthetic_pair()
    corrupt = inside.copy()
    corrupt[1, 8, 1, 0] = False
    with pytest.raises(ValueError, match='disagree'):
        matched.fixed_facet_check(points, positions, vertices, corrupt)
    moved = deepcopy(vertices)
    moved[1][4][matched.cell.geometry.GEOMS[3]][0][0] += .01
    with pytest.raises(ValueError, match='fixed translated'):
        matched.fixed_facet_check(points, positions, moved, inside)


def test_no_common_pair_is_empty_and_inconclusive_not_a_selected_pose():
    points, positions, vertices, inside = synthetic_pair()
    points += [0., 4., 0.]
    inside[:] = False
    result = matched.fixed_facet_check(points, positions, vertices, inside)
    for row in result['conditions']:
        assert row['common_pair_checks'] == []
        assert row['all_common_pairs_strictly_inside'] is False
        assert row['minimum_common_pair_corner_slack_m'] is None
        assert row['maximum_common_pair_corner_slack_m'] is None


@pytest.mark.parametrize('missing', [1, 8])
def test_original_common_pair_helper_requires_first_and_last_corner_for_each_anchor(missing):
    inside = np.zeros((9, 2, 5), bool)
    inside[:, 1, 3] = True
    inside[missing, 1, 3] = False
    assert matched.cell.common_corner_witnesses(inside).shape == (0, 2)
    inside[missing, 1, 3] = True
    inside[0, 1, 3] = False  # Center is a separate measured row, never a corner.
    assert matched.cell.common_corner_witnesses(inside).tolist() == [[1, 3]]


def source_fixture():
    frame = {'depth_m': np.ones((3, 3)), 'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    parsed = {'status': 'single_point', 'points': [{'sample_pixel_xy': [1, 2]}]}
    audit = {'complete_generation': True, 'terminal_eos_observed': True, 'length_limit_reached': False}
    sensor = {'status': 'admitted_sensor_point', 'reason': None, 'parsed': parsed, 'generation_audit': audit,
        'source_frame_sha256': matched.cell.SOURCES['interaction-observability-paired-01/close/0000.npz'],
        'resolved_depth_ownership': None, 'semantic_confidence': None, 'grasp_quality': None,
        'semantic_target_identity_verified': False, 'point': matched.admit_point(parsed, audit, frame)}
    return sensor, frame


def test_anchor_reader_preserves_containing_pixel_center_projection_and_unknowns():
    sensor, frame = source_fixture()
    assert matched.admitted_anchor(sensor, frame) == [1.5, 2.5, 1.]
    sensor['point']['position_world_m'][0] = 1.
    with pytest.raises(ValueError, match='pixel-center'):
        matched.admitted_anchor(sensor, frame)


@pytest.mark.parametrize('field,value', [('terminal_eos_observed', False), ('length_limit_reached', True), ('complete_generation', False)])
def test_anchor_reader_rejects_incomplete_native_source(field, value):
    sensor, frame = source_fixture()
    sensor['generation_audit'][field] = value
    with pytest.raises(ValueError, match='completed native POINT'):
        matched.admitted_anchor(sensor, frame)


def test_worker_rejects_missing_reordered_or_extra_anchor_fields_before_output(tmp_path):
    request = {'calibration': {}, 'full_support': [], 'terminal_own_packet': {}, 'nominal_step_m': .01,
        'anchors': [{'condition': c, 'point_P_world_m': [0, 0, 0]} for c in matched.CONDITIONS]}
    for anchors in (request['anchors'][:1], request['anchors'][::-1],
                    [{**request['anchors'][0], 'mask': True}, request['anchors'][1]]):
        with pytest.raises(ValueError, match='Both fixed anchors'):
            matched.compute({**request, 'anchors': anchors}, tmp_path/'forbidden')
        assert not (tmp_path/'forbidden').exists()
