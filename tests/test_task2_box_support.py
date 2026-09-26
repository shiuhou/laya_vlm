import numpy as np
import pytest

from embodied_runtime.experiments.task2_box_support import (
    admitted_box, evaluate_proxy, interior_bounds, proxy_strata, sensor_representation,
)
from embodied_runtime.vision import LocateAnythingProvider


def frame(depth):
    h, w = depth.shape
    return {'rgb': np.zeros((h, w, 3), np.uint8), 'depth_m': depth,
            'intrinsics': np.array([[2., 0., 1.], [0., 2., 1.], [0., 0., 1.]]),
            'camera_to_world': np.array([[0., -1., 0., 1.], [1., 0., 0., 2.],
                                         [0., 0., 1., 3.], [0., 0., 0., 1.]])}


@pytest.mark.parametrize('box', [[0, 0, 10, 8], [-2, -3, 12, 9], [2.9, 1.8, 9.5, 7.2], [0, 0, 2, 2]])
def test_exact_provider_parity_and_support(box):
    f = frame(np.linspace(.1, 1., 80, dtype=np.float32).reshape(8, 10))
    f['depth_m'][2, 2] = np.nan
    f['depth_m'][3, 3] = 8.
    result = sensor_representation(f, box)
    event = LocateAnythingProvider(lambda *_: None, f['intrinsics']).observe(
        f['rgb'], f['depth_m'], 'the wine bottle', episode_id='x', source_seq=0,
        capture_sim_time=.5, camera_to_world_matrix=f['camera_to_world'],
        inference_result={'boxes_xyxy': [box]})
    if event is None:
        assert result['point_P'] is None
        assert not result['support_G']
        return
    assert result['point_P']['position_world_m'] == event.value['position_world_m']
    assert result['point_P']['position_camera_m'] == event.value['position_camera_m']
    x1, y1, x2, y2 = interior_bounds(f['depth_m'].shape, box)
    selected = [(x, y) for y in range(y1, y2) for x in range(x1, x2)
                if np.isfinite(f['depth_m'][y, x]) and .01 <= f['depth_m'][y, x] <= 5.]
    assert [tuple(row['pixel_xy']) for row in result['support_G']] == selected


def test_median_ties_retained_and_pixel_center_projection():
    f = frame(np.ones((6, 6), np.float32))
    f['depth_m'][1:5, 1:5] = np.array([1., 1., 2., 2.] * 4).reshape(4, 4)
    result = sensor_representation(f, [0, 0, 6, 6])
    assert result['depth_statistics']['median_m'] == 1.5
    groups = result['median_contributor_indices']
    assert len(groups['lower']) == len(groups['upper']) == 8
    assert set(groups['lower']).isdisjoint(groups['upper'])
    # Pixel(1,1), z1, offset+.5, K focal2/principal1 -> (.25,.25,1).
    # Known transform -> (.75,2.25,4). Provider's ray convention stays separate.
    assert result['support_G'][0]['position_world_m'] == [.75, 2.25, 4.]
    assert result['point_P']['position_world_m'] == [-.5, 3.5, 4.5]


def test_single_box_eos_budget_and_malformed_admission():
    ok = {'complete_generation': True, 'actual_generated_token_count': 12}
    box, _ = admitted_box('<box><100><200><300><400></box>', ok, 10, 20)
    assert box == [1., 4., 3., 8.]
    cases = ['<box><100><200></box>', '<box><100><200><300></box>',
             '<box><100><200><300><400></box>' * 2,
             '<box><100><200><300><400></box><box>none</box>',
             '<box><100><200><300><400>']
    for raw in cases:
        assert admitted_box(raw, ok, 10, 20)[0] is None
    assert admitted_box('<box><1><2><3><4></box>', {**ok, 'complete_generation': False}, 10, 20)[0] is None
    assert admitted_box('<box><1><2><3><4></box>', {**ok, 'actual_generated_token_count': 257}, 10, 20)[0] is None


def test_proxy_strata_are_exhaustive_and_do_not_clean_sensor():
    mask = np.zeros((7, 7), bool)
    mask[2:5, 2:5] = True
    strata = proxy_strata(mask)
    assert [int(strata[k].sum()) for k in strata] == [1, 24, 24]
    assert np.array_equal(sum(v.astype(int) for v in strata.values()), np.ones((7, 7), int))
    sensor = sensor_representation(frame(np.ones((7, 7), np.float32)), [0, 0, 7, 7])
    before = repr(sensor)
    outcome = evaluate_proxy(sensor, mask)
    assert repr(sensor) == before
    assert outcome['selected_count'] == 25
    assert outcome['selected_proxy_overlap_count'] == 9
    assert outcome['selected_strata_counts'] == {'proxy_interior': 1, 'proxy_boundary_band': 24, 'proxy_exterior': 0}
    assert outcome['resolved_depth_ownership'] is None
    assert outcome['semantic_confidence'] is None


def test_sensor_schema_rejects_gold_and_empty_depth_stays_unknown():
    f = frame(np.full((5, 5), np.nan, np.float32))
    with pytest.raises(ValueError, match='unexpected sensor'):
        sensor_representation({**f, 'bottle_mask': np.ones((5, 5), bool)}, [0, 0, 5, 5])
    assert sensor_representation(f, [0, 0, 5, 5])['status'] == 'unknown_empty_valid_crop'
