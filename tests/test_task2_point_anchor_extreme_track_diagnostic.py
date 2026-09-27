import numpy as np
import pytest

from embodied_runtime.experiments import task2_point_anchor_extreme_track_diagnostic as diagnostic


def test_maximum_final_value_ties_use_lowest_seed_and_keep_complete_trajectory():
    rows = [{'seed_id': seed, 'capture_id': capture,
        'reference_deltas': {'preclose': {'point_delta_norm_m':
            None if seed == 22 else 9. if seed in (7, 10) else 1.}}}
        for seed in range(492) for capture in range(3)]
    selected, receipt = diagnostic.select_seed(rows, 3)
    assert selected == rows[21:24]
    assert receipt == {'selected_seed_id': 7, 'final_point_delta_norm_m': 9.,
        'tied_maximum_seed_ids': [7, 10], 'available_final_count': 491, 'unavailable_seed_ids': [22]}
    with pytest.raises(ValueError, match='complete original'):
        diagnostic.select_seed(rows[:-1], 3)


def test_exact_change_flags_first_tied_jump_and_unknown_pairs():
    rows = [{'capture_id': i, 'point_pixel_index_xy': [i*1e-12, 0.],
        'sample_pixel_xy': [0 if i < 2 else 1, 0], 'depth_m': 1. if i < 3 else None,
        'surface_point_world_m': point} for i, point in
        enumerate(([0., 0., 0.], [0., 0., 1.], [0., 0., 0.], None))]
    report = diagnostic.describe_changes(rows, 1)
    assert report['all_frames']['earliest_largest_consecutive_world_distance']['capture_id'] == 1
    assert report['after_preclose']['earliest_largest_consecutive_world_distance']['capture_id'] == 2
    assert report['all_frames']['first_changes']['point_pixel_index_xy']['capture_id'] == 1
    assert report['all_frames']['first_changes']['sample_pixel_xy']['capture_id'] == 2
    assert report['all_frames']['first_changes']['depth_m']['capture_id'] == 3
    assert report['adjacent_pairs'][-1]['consecutive_stored_world_distance_m'] is None


def test_neighborhood_keeps_exact_saved_depth_and_explicit_padding():
    depth = np.arange(16, dtype=float).reshape(4, 4)
    crop = diagnostic.neighborhood(depth, [1, 1])
    assert crop.shape == (21, 21) and crop[10, 10] == depth[1, 1]
    assert np.array_equal(crop[9:13, 9:13], depth) and np.isnan(crop[0, 0])
    assert np.isnan(diagnostic.neighborhood(depth, None)).all()
