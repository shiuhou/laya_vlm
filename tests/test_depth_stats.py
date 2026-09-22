import numpy as np

from embodied_runtime.vision import depth_statistics


def test_depth_statistics_reports_uncertainty():
    depth = np.ones((20, 20), dtype=float)
    depth[8, 8] = 3.0
    stats = depth_statistics(depth, (2, 2, 18, 18))
    assert stats["median_m"] == 1.0
    assert stats["mad_m"] == 0.0
    assert stats["std_m"] >= 0.0
    assert 0.0 < stats["valid_ratio"] <= 1.0
