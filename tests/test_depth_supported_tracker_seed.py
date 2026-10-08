import numpy as np

from embodied_runtime.perception.tracker_seed import depth_supported_rectangle
from embodied_runtime.perception.visual_tracker import TrackerConfig, VisualTracker


def view():
    return dict(rgb=np.random.default_rng(3).integers(0, 256, (64, 64, 3), dtype=np.uint8),
                depth_m=np.broadcast_to(.5 + np.arange(64)[:, None] * .002, (64, 64)).copy(),
                intrinsics_K=np.array([[100., 0, 32], [0, 100., 32], [0, 0, 1]]),
                T_base_camera=np.eye(4), camera_id='front', frame_id='f1', frame_seq=1,
                episode_id='test', calibration_version='cal1', frame='robot_base',
                capture_sim_time_s=1., capture_monotonic_ns=1000000000)


def test_proposal_passes_unchanged_tracker_without_moving_semantic_point():
    v = view()
    mask = np.zeros((64, 64), bool)
    mask[8:56, 8:56] = True
    roi, receipt = depth_supported_rectangle(v, mask, [32., 32.])
    assert roi is not None and receipt['depth_spread_m'] <= TrackerConfig().max_depth_spread_m
    assert receipt['depth_admitted_rectangles'] < receipt['support_rectangles']
    assert np.array_equal((np.array(roi[:2]) + roi[2:]) / 2, [32.5, 32.5])
    track = VisualTracker('test').initialize(v, roi, query='front', seed_source='semantic_query',
                                           now_sim_time_s=1., now_monotonic_ns=1000000000)
    assert track.status == 'TRACKED'


def test_missing_depth_and_support_holes_are_not_filled():
    v = view()
    mask = np.ones((64, 64), bool)
    v['depth_m'][:] = np.nan
    roi, receipt = depth_supported_rectangle(v, mask, [32., 32.])
    assert roi is None and receipt['reason'] == 'NO_DEPTH_SUPPORTED_RECTANGLE'
    mask[32, 32] = False
    roi, receipt = depth_supported_rectangle(v, mask, [32., 32.])
    assert roi is None and receipt['reason'] == 'POINT_OUTSIDE_SUPPORT'
