import pytest

from embodied_runtime.experiments.task2_pre22_counterfactual_report import capture_at_execution_boundary


def test_endpoint_uses_executor_time_and_checks_one_based_camera_sequence():
    captures = [{'branch': 'MV_FWD', 'capture_seq': 22, 'capture_sim_time': 8.9},
                {'branch': 'MV_FWD', 'capture_seq': 23, 'capture_sim_time': 9.3},
                {'branch': 'MV_FWD', 'capture_seq': 24, 'capture_sim_time': 9.7}]
    assert capture_at_execution_boundary(captures, 'MV_FWD', {'sim_time': 9.3}, 23) == captures[1]
    assert capture_at_execution_boundary(captures, 'MV_FWD', {'sim_time': 9.7}, 24) == captures[2]
    with pytest.raises(ValueError, match='time/sequence'):
        capture_at_execution_boundary(captures, 'MV_FWD', {'sim_time': 9.7}, 23)
    with pytest.raises(ValueError, match='time/sequence'):
        capture_at_execution_boundary(captures+[captures[2]], 'MV_FWD', {'sim_time': 9.7}, 24)
