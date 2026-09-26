from itertools import product

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from embodied_runtime.experiments.task2_finite_gap_control import PADS, finite_gap
from embodied_runtime.experiments.task2_finite_gap_target_region import common_pairs, target_region_corners
from embodied_runtime.experiments.sensor_gripper_proximity import proxy_distance


def cube(low, high):
    return np.asarray(list(product(*zip(low, high))), float)


def test_rotated_asymmetric_calibrated_gap_gives_exact_eight_target_corners():
    q1, q2 = .02, -.03
    half = np.array([.004, .008, .008])
    centers = [np.array([-q1-.0035, 0, -.0036]), np.array([-q2+.0035, 0, -.0036])]
    low, high = finite_gap({name: cube(center-half, center+half) for name, center in zip(PADS, centers)})
    rotation = Rotation.from_euler('xyz', [20, 30, -40], degrees=True).as_matrix()
    point = np.array([.2, -.3, .7])
    positions, corners, choices = target_region_corners(point, rotation, low, high)
    assert choices.tolist() == [list(bits) for bits in product((0, 1), repeat=3)]
    assert positions.shape == corners.shape == (8, 3)
    assert np.unique(positions, axis=0).shape == (8, 3)
    np.testing.assert_allclose(corners[0], [-q1+.0005, -.008, -.0116], atol=1e-15)
    np.testing.assert_allclose(corners[-1], [-q2-.0005, .008, .0044], atol=1e-15)
    np.testing.assert_allclose((point-positions)@rotation, corners, rtol=0, atol=2e-16)
    # Any gap point maps to a TCP translation with P in that same finite gap.
    gap_point = low+.37*(high-low)
    tcp = point-rotation@gap_point
    np.testing.assert_allclose(rotation.T@(point-tcp), gap_point, rtol=0, atol=2e-16)
    assert np.all(gap_point >= low) and np.all(gap_point <= high)
    outside = high+np.array([.001, 0, 0])
    outside_tcp = point-rotation@outside
    assert (rotation.T@(point-outside_tcp))[0] > high[0]


def test_empty_invalid_and_degenerate_regions_keep_distinct_meanings():
    positions, corners, _ = target_region_corners([0, 0, 0], np.eye(3), [0, -1, -2], [0, 1, 2])
    assert positions.shape == (8, 3) and len(np.unique(positions, axis=0)) == 4
    np.testing.assert_array_equal(positions, -corners)
    for rotation, low, high in ((np.eye(3), [1, 0, 0], [0, 1, 1]),
                                (np.diag([-1., 1., 1.]), [0, 0, 0], [1, 1, 1]),
                                (np.eye(3), [np.nan, 0, 0], [1, 1, 1])):
        with pytest.raises(ValueError):
            target_region_corners([0, 0, 0], rotation, low, high)


def test_all_eight_rows_including_first_are_required_for_same_pair():
    inside = np.zeros((8, 2, 5), bool)
    inside[:, 1, 4] = True
    assert common_pairs(inside).tolist() == [[1, 4]]
    inside[0, 1, 4] = False
    assert common_pairs(inside).shape == (0, 2)
    inside[0, 1, 4], inside[-1, 1, 4] = True, False
    assert not len(common_pairs(inside))
    with pytest.raises(ValueError):
        common_pairs(np.ones((9, 2, 5), bool))
    with pytest.raises(ValueError):
        common_pairs(np.ones((8, 2, 5), float))


def test_positive_unions_are_not_a_common_witness_certificate():
    inside = np.zeros((8, 8, 5), bool)
    for corner in range(8):
        inside[corner, corner, 0] = True
    assert inside.any(axis=(1, 2)).all() and not len(common_pairs(inside))
    inside[:] = False
    for corner in range(8):
        inside[corner, 0, corner % 2] = True
    assert inside.any(axis=(1, 2)).all() and not len(common_pairs(inside))


def test_same_pair_on_rotated_region_corners_extends_to_convex_combinations():
    rotation = Rotation.from_euler('xyz', [20, -10, 35], degrees=True).as_matrix()
    positions, _, _ = target_region_corners([0, 0, 0], rotation, [-.1, -.2, -.3], [.2, .1, .2])
    vertices, point = cube([-1, -1, -1], [1, 1, 1]), np.array([[0., 0., 0.]])
    inside = np.zeros((8, 1, 5), bool)
    for index, tcp in enumerate(positions):
        inside[index, :, 2] = proxy_distance(point, vertices+tcp)[2]
    assert common_pairs(inside).tolist() == [[0, 2]]
    weights = np.arange(1, 9, dtype=float)
    weights /= weights.sum()
    assert proxy_distance(point, vertices+weights@positions)[2].all()
