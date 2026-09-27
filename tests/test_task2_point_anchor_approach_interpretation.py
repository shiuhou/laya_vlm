import pytest

from embodied_runtime.experiments.task2_point_anchor_approach_interpretation import exact_capture, first_comparable_divergence


def decisions(tokens):
    return [{'data': {'step': step, 'selected': token}} for step, token in enumerate(tokens)]


def test_first_cross_arm_divergence_includes_stop_and_does_not_invent_missing_decisions():
    assert first_comparable_divergence([decisions(['DOWN', 'STOP']), decisions(['DOWN', 'FWD'])]) == 1
    assert first_comparable_divergence([decisions(['DOWN']), decisions(['DOWN', 'FWD'])]) is None
    assert first_comparable_divergence([decisions(['LEFT']), decisions(['DOWN'])]) == 0


def test_capture_selection_requires_actual_one_based_sequence_and_exact_boundary_time():
    captures = [{'data': {'capture_seq': 23, 'capture_sim_time': 9.3}},
                {'data': {'capture_seq': 24, 'capture_sim_time': 9.7}}]
    assert exact_capture(captures, 23, 9.3) is captures[0]
    with pytest.raises(ValueError, match='sequence/time'):
        exact_capture(captures, 22, 9.3)
    with pytest.raises(ValueError, match='sequence/time'):
        exact_capture(captures, 23, 9.7)
