import copy
import json

import numpy as np

from embodied_runtime.experiments.point_temporal_probe import track_lk
from embodied_runtime.experiments.task2_box_temporal_probe import (
    enrich_track, proxy_membership, reference_delta, summarize_tracks, surface_sample,
)


def frame(depth=1.):
    return {'rgb': np.zeros((4, 4, 3), np.uint8), 'depth_m': np.full((4, 4), depth),
            'intrinsics': np.array([[2., 0., 1.], [0., 2., 1.], [0., 0., 1.]]),
            'camera_to_world': np.eye(4)}


def track(status='native_status_ok', point=(1.9, 2.1), capture_id=0, seed_id=0):
    return {'status': status, 'point_pixel_index_xy': list(point), 'capture_id': capture_id, 'seed_id': seed_id}


def test_depth_unknowns_preserve_track_and_floor_halfpixel_convention():
    row = track()
    sampled = surface_sample(row, frame())
    assert sampled['sample_pixel_xy'] == [1, 2]
    assert sampled['surface_point_world_m'] == [.25, .75, 1.]
    for z, status in ((float('nan'), 'nonfinite'), (float('inf'), 'nonfinite'), (6., 'outside_valid_range')):
        result = surface_sample(row, frame(z))
        assert result['surface_point_world_m'] is None and result['depth_status'] == status
        json.dumps(result, allow_nan=False)
    assert row['status'] == 'native_status_ok'
    assert surface_sample(row, frame())['surface_point_world_m'] is not None
    assert surface_sample(track(point=(-.1, 1.)), frame())['depth_status'] == 'outside_image'
    assert surface_sample(track(status='native_failure'), frame())['sample_pixel_xy'] is None


def test_original_tracker_native_failure_is_permanent_without_recovery():
    class FakeCV:
        COLOR_RGB2GRAY = 0
        calls = 0
        def cvtColor(self, image, code):
            return image[..., 0]
        def calcOpticalFlowPyrLK(self, previous, current, point, ignored, **settings):
            self.calls += 1
            return point+1, np.array([[0]], np.uint8), np.array([[float('nan')]])
    cv = FakeCV()
    rows = track_lk(np.zeros((4, 4, 4, 3), np.uint8), [1, 2], cv)
    assert cv.calls == 1
    assert [r['status'] for r in rows] == ['seeded', 'native_failure', 'unknown_after_native_failure', 'unknown_after_native_failure']
    assert rows[1]['point_pixel_index_xy'] == [2., 3.]
    assert rows[1]['forward_patch_error'] is None


def test_known_translation_cancels_tcp_and_missing_does_not_become_zero():
    delta = reference_delta([.1, .2, .3], [0., 0., 0.], [.1, .2, .3], [0., 0., 0.])
    assert delta['point_minus_tcp_delta_norm_m'] == 0
    missing = reference_delta(None, [0., 0., 0.], [.1, .2, .3], [0., 0., 0.])
    assert missing['point_delta_norm_m'] is None and missing['point_minus_tcp_delta_norm_m'] is None


def test_reference_cohort_does_not_select_prefix_or_drop_failures():
    packet = {'frames': [frame() for _ in range(15)], 'meta': [{'capture_id': i} for i in range(15)],
              'tcps': [[0., 0., 0.] for _ in range(15)]}
    live = [track(capture_id=i) for i in range(15)]
    a = enrich_track(live, packet, 0, [1, 2])
    failed = copy.deepcopy(live)
    for i in range(13, 15):
        failed[i]['status'] = 'native_failure' if i == 13 else 'unknown_after_native_failure'
    b = enrich_track(failed, packet, 1, [1, 2])
    summaries = summarize_tracks([a, b], 2)
    assert summaries[12]['native_surviving_count'] == 2
    assert summaries[12]['references']['preclose']['reference_surface_valid_count'] is None
    assert summaries[13]['references']['preclose']['reference_surface_valid_count'] == 1
    assert summaries[14]['denominator'] == 2 and summaries[14]['unknown_after_failure_count'] == 1
    assert summaries[14]['references']['initial']['metrics']['point_delta_norm_m']['count'] == 1
    assert summaries[14]['references']['preclose']['metrics']['point_delta_norm_m']['count'] == 1
    assert all(r['reference_deltas']['preclose'] is None for r in a[:13])


def test_proxy_initial_outside_is_not_departure_and_cannot_change_sensor():
    masks = [np.array([[v]], bool) for v in (False, True, False)]
    rows = [{'seed_id': 0, 'capture_id': i, 'status': 'native_status_ok', 'sample_pixel_xy': [0, 0]}
            for i in range(3)]
    before = copy.deepcopy(rows)
    result = proxy_membership(rows, masks)
    assert result['first_observed_departure_after_proxy_true'][0]['capture_id'] == 2
    assert result['counts'][0]['proxy_false'] == 1
    assert rows == before
    assert result['resolved_depth_ownership'] is None
