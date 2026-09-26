import inspect

import numpy as np
import pytest

from embodied_runtime.experiments.perception_support_audit import median_proxy, support_diagnostic


def test_median_proxy_has_no_oracle_input_and_uses_boundary_coordinate_midpoint():
    assert not {'oracle_mask', 'world', 'ray_depths'} & set(inspect.signature(median_proxy).parameters)
    depth = np.ones((6, 6))
    assert median_proxy(depth, [0, 0, 4, 4], np.eye(3), np.eye(4)) == [2., 2., 1.]
    assert median_proxy(np.full((6, 6), np.nan), [0, 0, 4, 4], np.eye(3), np.eye(4)) is None


def test_support_contamination_decomposes_without_correcting_sensor_output():
    depth = np.ones((6, 6))
    depth[:, 3:] = 2.
    oracle = np.zeros((6, 6), bool)
    oracle[:, :3] = True
    result = support_diagnostic(depth, [0, 0, 6, 6], np.eye(3), np.eye(4), oracle, depth[oracle])
    assert result['purity'] == .5
    assert result['centroid_error_mm'] > 0
    assert result['support_component_mm'] == pytest.approx(result['centroid_error_mm'])
    assert result['ray_depth_component_mm'] == 0
    assert result['vector_decomposition_residual_mm'] < 1e-9
    changed = support_diagnostic(depth, [0, 0, 6, 6], np.eye(3), np.eye(4), ~oracle, depth[~oracle])
    assert result['sensor_centroid_m'] == changed['sensor_centroid_m']
    assert result['median_proxy_m'] == changed['median_proxy_m']
    assert result['median_to_surface_distance_is_accuracy'] is False


def test_same_support_depth_disagreement_is_separate_from_membership():
    depth = np.ones((6, 6))
    mask = np.ones((6, 6), bool)
    result = support_diagnostic(depth, [0, 0, 6, 6], np.eye(3), np.eye(4), mask, np.full(36, 1.1))
    assert result['purity'] == 1
    assert result['support_component_mm'] == 0
    assert result['ray_depth_component_mm'] == pytest.approx(result['centroid_error_mm'])


def test_no_valid_depth_is_missing_not_zero_error():
    depth = np.full((6, 6), np.nan)
    mask = np.ones((6, 6), bool)
    result = support_diagnostic(depth, [0, 0, 6, 6], np.eye(3), np.eye(4), mask, np.ones(36))
    assert result['sensor_centroid_m'] is None
    assert result['centroid_error_mm'] is None
    assert result['vector_decomposition_residual_mm'] is None
