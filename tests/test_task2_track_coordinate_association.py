import copy
import json

import cv2
import numpy as np

from embodied_runtime.experiments.task2_track_coordinate_association import (
    convention_check, nearest_index, nearest_surface_sample, reassociate_track,
)


def frame(depth=1.):
    return {'depth_m': np.full((5, 5), depth), 'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}


def test_integer_centers_epsilon_symmetry_half_boundaries_and_native_opencv():
    assert convention_check(cv2)['status'] == 'pass'
    assert nearest_index([2.-1e-6, 2.+1e-6]).tolist() == [2, 2]
    assert np.floor([2.-1e-6, 2.+1e-6]).astype(int).tolist() == [1, 2]
    assert nearest_index([2.-.50001, 2.+.50001]).tolist() == [1, 3]


def test_projection_keeps_halfpixel_separate_and_does_not_interpolate_depth():
    f = frame()
    f['depth_m'][2, 2] = 2.
    f['depth_m'][2, 1] = 4.
    row = {'status': 'native_status_ok', 'point_pixel_index_xy': [1.99999, 2.00001]}
    result = nearest_surface_sample(row, f)
    assert result['sample_pixel_xy'] == [2, 2] and result['depth_m'] == 2.
    assert result['surface_point_world_m'] == [5., 5., 2.]


def test_unknowns_edges_and_native_failure_preserved():
    r = {'status': 'native_status_ok', 'point_pixel_index_xy': [-.5001, 2.]}
    assert nearest_surface_sample(r, frame())['depth_status'] == 'outside_image'
    r['point_pixel_index_xy'] = [2., 2.]
    result = nearest_surface_sample(r, frame(float('nan')))
    assert result['depth_status'] == 'nonfinite' and result['surface_point_world_m'] is None
    json.dumps(result, allow_nan=False)
    r['status'] = 'native_failure'
    assert nearest_surface_sample(r, frame())['depth_status'] == 'RGB_track_not_admitted'


def test_reassociation_copies_native_rows_and_keeps_missing_preclose_cohort():
    rows = [{'status': 'native_status_ok', 'point_pixel_index_xy': [1.9999, 2.],
             'capture_id': i, 'forward_backward_residual_px': .123} for i in range(15)]
    rows[13]['status'] = 'native_failure'
    rows[14]['status'] = 'unknown_after_native_failure'
    original = copy.deepcopy(rows)
    packet = {'frames': [frame() for _ in rows], 'tcps': [[0., 0., 0.] for _ in rows]}
    result = reassociate_track(rows, packet)
    assert rows == original
    for a, b in zip(original, result):
        assert all(a[k] == b[k] for k in a)
    assert result[12]['reference_deltas']['preclose'] is None
    assert result[14]['reference_deltas']['preclose']['point_delta_norm_m'] is None
    assert result[14]['surface_point_world_m'] is None
