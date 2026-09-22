import numpy as np

from embodied_runtime.association import QueryTrackManager, box_iou


def test_query_track_manager_uses_iou_and_3d_gate():
    assert box_iou((0, 0, 10, 10), (5, 5, 15, 15)) > 0
    manager = QueryTrackManager()
    first = manager.update("drawer", [(0, 0, 100, 100)], [np.array([0, 0, 1])], 0.0)
    second = manager.update("drawer", [(2, 1, 102, 101)], [np.array([0.02, 0, 1])], 0.1)
    assert first[0].track_id == second[0].track_id
    other = manager.update("drawer", [(300, 300, 350, 350)], [np.array([1, 1, 1])], 0.2)
    assert other[0].track_id != first[0].track_id
