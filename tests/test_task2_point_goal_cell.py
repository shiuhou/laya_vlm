from itertools import product

import numpy as np
import pytest

from embodied_runtime.experiments.task2_point_goal_cell import axis_stop_cell, common_corner_witnesses
from embodied_runtime.experiments.sensor_gripper_proximity import proxy_distance


def cube(radius):
    return np.asarray(list(product((-radius, radius), repeat=3)), float)


def test_axis_cell_half_width_follows_exact_strict_improvement_inequality():
    positions, signs, half = axis_stop_cell([0., 0., 0.])
    assert half == .005 and positions.shape == (9, 3)
    assert np.array_equal(positions[1:], signs*.005)
    assert signs.tolist() == [list(row) for row in product((-1, 1), repeat=3)]
    # With h=2, all integer/half-cell arithmetic here is exact binary arithmetic.
    moves = np.concatenate((np.eye(3)*2, -np.eye(3)*2))
    for delta in np.asarray(list(product((-1., 0., 1.), repeat=3))):
        assert not (np.sum((delta-moves)**2, axis=1) < np.sum(delta**2)).any()
    for axis in range(3):
        for sign in (-1, 1):
            outside = np.zeros(3)
            outside[axis] = sign*1.25
            assert (np.sum((outside-moves)**2, axis=1) < np.sum(outside**2)).any()
    for point, step in (([np.nan, 0, 0], .01), ([0, 0], .01), ([0, 0, 0], 0)):
        with pytest.raises(ValueError):
            axis_stop_cell(point, step)


def test_same_point_same_proxy_at_all_corners_certifies_convex_combinations():
    positions, _, _ = axis_stop_cell([0, 0, 0], 2.)
    point = np.array([[0., 0., 0.]])
    inside = np.zeros((9, 1, 5), bool)
    for index, tcp in enumerate(positions):
        inside[index, :, 0] = proxy_distance(point, cube(2)+tcp)[2]
    assert common_corner_witnesses(inside).tolist() == [[0, 0]]
    rng = np.random.default_rng(41)
    for weights in rng.dirichlet(np.ones(8), 12):
        tcp = weights@positions[1:]
        assert proxy_distance(point, cube(2)+tcp)[2].all()


def test_eight_positive_unions_with_different_points_do_not_certify_cell():
    positions, _, _ = axis_stop_cell([0, 0, 0], 2.)
    points = positions[1:]
    inside = np.zeros((9, 8, 5), bool)
    for index, tcp in enumerate(positions):
        inside[index, :, 0] = proxy_distance(points, cube(.125)+tcp)[2]
    assert inside[1:].any(axis=(1, 2)).all()
    assert not inside[0].any()  # The cell center actually remains outside every point.
    assert common_corner_witnesses(inside).shape == (0, 2)


def test_different_proxies_and_exact_P_only_are_weaker_than_common_corner_witness():
    inside = np.zeros((9, 1, 5), bool)
    for corner in range(1, 9):
        inside[corner, 0, corner % 2] = True
    assert inside[1:].any(axis=(1, 2)).all()
    assert not len(common_corner_witnesses(inside))
    inside[:] = False
    inside[0, 0, 0] = True
    assert not len(common_corner_witnesses(inside))
    with pytest.raises(ValueError):
        common_corner_witnesses(inside.astype(float))
    with pytest.raises(ValueError):
        common_corner_witnesses(inside[:, :, :1])
