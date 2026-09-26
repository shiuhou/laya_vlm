import pytest

from embodied_runtime.experiments.task2_endpoint_containment_veto_report import capture_at


def test_capture_boundary_requires_time_and_one_based_sequence_including_stop():
    captures = [{'capture_seq': 23, 'capture_sim_time': 9.3},
                {'capture_seq': 24, 'capture_sim_time': 9.7},
                {'capture_seq': 29, 'capture_sim_time': 11.7}]
    assert capture_at(captures, 9.3, 23) is captures[0]
    assert capture_at(captures, 11.7, 29) is captures[-1]
    with pytest.raises(ValueError):
        capture_at(captures, 9.3, 22)
    with pytest.raises(ValueError):
        capture_at(captures+captures[-1:], 11.7, 29)
