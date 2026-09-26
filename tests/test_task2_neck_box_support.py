import numpy as np
import pytest

from embodied_runtime.experiments import task2_box_support as baseline
from embodied_runtime.experiments.task2_neck_box_support import fixed_condition


def test_condition_restores_baseline_on_failure_and_preserves_geometry():
    original = baseline.QUERY, baseline.QUESTION, baseline.PROTOCOL
    depth = np.linspace(.9, 1.1, 100, dtype=np.float32).reshape(10, 10)
    frame = {'rgb': np.zeros((10, 10, 3), np.uint8), 'depth_m': depth,
             'intrinsics': np.array([[10., 0., 5.], [0., 10., 5.], [0., 0., 1.]]),
             'camera_to_world': np.eye(4)}
    before = baseline.sensor_representation(frame, [1, 1, 9, 9])
    with pytest.raises(RuntimeError, match='preserved failure'):
        with fixed_condition():
            assert baseline.QUESTION == ('Locate a single instance that matches the following '
                                         'description: the neck of the wine bottle.')
            assert baseline.sensor_representation(frame, [1, 1, 9, 9]) == before
            raise RuntimeError('preserved failure')
    assert (baseline.QUERY, baseline.QUESTION, baseline.PROTOCOL) == original
