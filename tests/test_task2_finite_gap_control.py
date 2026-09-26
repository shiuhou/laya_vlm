from itertools import product

import numpy as np
import pytest

from embodied_runtime.experiments.task2_finite_gap_control import (
    PADS, distance_to_gap, finite_gap, rank,
)


def box(low, high):
    return np.asarray(list(product(*zip(low, high))), float)


def test_calibrated_faces_keep_finite_overlap_and_do_not_fill_solids():
    pads = {PADS[0]: box([-.05, -.01, -.02], [-.04, .01, 0.]),
            PADS[1]: box([.03, -.005, -.015], [.04, .015, .005])}
    low, high = finite_gap(pads)
    np.testing.assert_array_equal(low, [-.04, -.005, -.015])
    np.testing.assert_array_equal(high, [.03, .01, 0.])
    assert distance_to_gap([0., 0., 0.], low, high) == 0.
    assert distance_to_gap([0., .014, .003], low, high) == pytest.approx(.005)
    assert distance_to_gap([-.045, 0., -.01], low, high) == pytest.approx(.005)


def test_degenerate_closed_boundary_kept_empty_or_nonfinite_rejected():
    assert distance_to_gap([1, 0, 0], [0, 0, 0], [0, 0, 0]) == 1
    with pytest.raises(ValueError):
        distance_to_gap([0, 0, 0], [1, 0, 0], [0, 1, 1])
    with pytest.raises(ValueError):
        distance_to_gap([float('nan'), 0, 0], [0, 0, 0], [1, 1, 1])
    with pytest.raises(ValueError, match='empty'):
        finite_gap({PADS[0]: box([-.01, 0, 0], [.01, 1, 1]),
                    PADS[1]: box([0., 2, 0], [.02, 3, 1])})


def test_rigid_world_transform_does_not_change_euclidean_region_distance():
    local = np.array([.04, .014, .003])
    rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
    origin = np.array([3., -2., 1.])
    world = rotation@local+origin
    low, high = [-.04, -.005, -.015], [.03, .01, 0.]
    assert distance_to_gap(rotation.T@(world-origin), low, high) == pytest.approx(distance_to_gap(local, low, high))


def test_vetoed_best_move_cannot_pass_and_no_strict_improvement_stays_stop():
    order = ['MV_FWD', 'MV_BACK', 'MV_LEFT', 'MV_RIGHT', 'MV_UP', 'MV_DOWN', 'STOP']
    candidates = {t: {'gap_distance_m': 1., 'excluded': False} for t in order}
    assert rank(1., candidates, order) == 'STOP'
    candidates['MV_FWD'] = {'gap_distance_m': 0., 'excluded': True}
    assert rank(1., candidates, order) == 'STOP'
    candidates['MV_LEFT']['gap_distance_m'] = .9
    assert rank(1., candidates, order) == 'MV_LEFT'
    assert rank(0., candidates, order) == 'STOP'


def test_distance_token_tie_matches_original_rule_without_new_priority():
    candidates = {t: {'gap_distance_m': .1, 'excluded': False} for t in ('MV_FWD', 'MV_BACK', 'STOP')}
    assert rank(.2, candidates, ['MV_FWD', 'MV_BACK', 'STOP']) == 'MV_BACK'
    candidates['MV_BACK']['excluded'] = True
    assert rank(.2, candidates, ['MV_FWD', 'MV_BACK', 'STOP']) == 'MV_FWD'
