import numpy as np
import pytest

from embodied_runtime.pixel_footprint import (
    camera_vertices, flipped_sample_locations, optical_rays,
    own_gripper_footprint, triangle_sample_depths,
)
from embodied_runtime.experiments.pixel_footprint_measurement import VISUAL_SHA256, measure, validate_topology, worker

SAMPLES = [[.375, .125], [.875, .375], [.125, .625], [.625, .875]]


def test_gl_vertical_flip_uses_pixel_edges_and_preserves_sample_order():
    # Independently convert GL row 7 in a height-12 viewport to array row 4.
    gl_locations = np.array([[3 + sx, 7 + sy] for sx, sy in SAMPLES])
    expected = np.column_stack((gl_locations[:, 0], 12 - gl_locations[:, 1]))
    np.testing.assert_array_equal(flipped_sample_locations([3, 4], SAMPLES), expected)
    np.testing.assert_array_equal(flipped_sample_locations([3, 4], [[.5, .5]]), [[3.5, 4.5]])


def test_edge_coordinate_intrinsics_and_optical_not_unit_ray_depth():
    k = np.array([[4., 0, 3], [0, 6, 2], [0, 0, 1]])
    rays = optical_rays([[3, 2], [5, 5]], k)
    np.testing.assert_allclose(rays, [[0, 0, 1], [.5, .5, 1]])
    np.testing.assert_allclose(rays * 2, [[0, 0, 2], [1, 1, 2]])
    assert np.linalg.norm(rays[1]) > 1


def test_mixed_coverage_is_geometry_at_each_sample_not_pixel_center():
    # Projected triangle x>=0, y>=0, x+y<=1 covers exactly the last two samples.
    vertices = np.array([[0, 0, 2], [2, 0, 2], [0, 2, 2]])
    result = triangle_sample_depths(vertices, [[0, 1, 2]], np.eye(3), (1, 1), SAMPLES)
    np.testing.assert_array_equal(result['potential_coverage'][0, 0], [False, False, True, True])
    np.testing.assert_array_equal(result['potential_depth_m'][0, 0, 2:], [2, 2])
    assert np.isnan(result['potential_depth_m'][0, 0, :2]).all()


def test_sloped_plane_uses_perspective_correct_optical_depth():
    # Plane z=2+x: ray (u,v,1) intersects at z=2/(1-u), not linear vertex z.
    vertices = np.array([[0, 0, 2], [2, 0, 4], [0, 2, 2]])
    result = triangle_sample_depths(vertices, [[0, 1, 2]], np.eye(3), (1, 1), [[.25, .75]])
    assert result['potential_coverage'][0, 0, 0]
    assert result['potential_depth_m'][0, 0, 0] == pytest.approx(8 / 3)


def test_nearest_positive_surface_independent_of_triangle_order_or_winding():
    vertices = np.array([[0, 0, 4], [8, 0, 4], [0, 8, 4],
                         [0, 0, 2], [4, 0, 2], [0, 4, 2]])
    a = triangle_sample_depths(vertices, [[0, 1, 2], [5, 4, 3]], np.eye(3), (1, 1), SAMPLES)
    b = triangle_sample_depths(vertices, [[3, 4, 5], [2, 1, 0]], np.eye(3), (1, 1), SAMPLES)
    np.testing.assert_array_equal(a['potential_depth_m'], np.full((1, 1, 4), 2))
    np.testing.assert_array_equal(a['potential_depth_m'], b['potential_depth_m'])


def test_camera_pose_and_resolved_depth_are_kept_separate():
    transform = np.eye(4)
    transform[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    transform[:3, 3] = [1, 2, 3]
    local = np.array([[0, 0, 2], [4, 0, 2], [0, 4, 2]])
    world = local @ transform[:3, :3].T + transform[:3, 3]
    np.testing.assert_array_equal(camera_vertices(world, transform), local)
    observed = np.array([[7.25]], dtype=np.float32)
    result = own_gripper_footprint(observed, np.eye(3), transform,
                                  [(world, [[0, 1, 2]])], SAMPLES)
    assert result['resolved_depth_m'].tobytes() == observed.tobytes()
    assert result['resolved_depth_m'].dtype == observed.dtype
    assert not np.shares_memory(result['resolved_depth_m'], observed)
    np.testing.assert_array_equal(result['potential_own_depth_m'], np.full((1, 1, 4), 2))
    assert result['observed_ownership'] == 'unknown'


def test_nonsquare_viewport_uses_height_width_and_edge_coordinate_principal_point():
    k = np.array([[2., 0, 2], [0, 2, 1], [0, 0, 1]])  # width=4, height=2
    vertices = [[0, -1, 2], [4, -1, 2], [0, 3, 2]]
    result = triangle_sample_depths(vertices, [[0, 1, 2]], k, (2, 4), SAMPLES)
    expected = np.zeros((2, 4, 4), dtype=bool)
    expected[:, 2:, :] = True
    np.testing.assert_array_equal(result['potential_coverage'], expected)


def test_exact_edges_and_degenerate_triangles_are_explicit():
    vertices = [[0, 0, 2], [2, 0, 2], [0, 2, 2]]
    result = triangle_sample_depths(vertices, [[0, 1, 2], [0, 0, 0]], np.eye(3), (1, 1), [[.5, .5]])
    assert result['geometric_edge_hit'][0, 0, 0]
    assert result['degenerate_projected_triangles'] == 1


def test_coplanar_mesh_ties_preserve_edge_metadata_in_both_orders():
    interior = ([[0, 0, 2], [4, 0, 2], [0, 4, 2]], [[0, 1, 2]])
    edge = ([[0, 0, 2], [2, 0, 2], [0, 2, 2]], [[0, 1, 2]])
    for meshes in ([interior, edge], [edge, interior]):
        result = own_gripper_footprint(np.ones((1, 1)), np.eye(3), np.eye(4),
                                      meshes, [[.5, .5]])
        assert result['potential_own_depth_m'][0, 0, 0] == 2
        assert result['geometric_edge_hit'][0, 0, 0]
        assert result['nearest_own_geometry_tie'][0, 0, 0]
        assert result['nearest_own_geometry_index'][0, 0, 0] == 0


def test_unknown_space_and_invalid_depth_do_not_become_free_space():
    observed = np.array([[np.nan, 0.]], dtype=np.float32)
    vertices = [[10, 10, 2], [12, 10, 2], [10, 12, 2]]
    result = own_gripper_footprint(observed, np.eye(3), np.eye(4),
                                  [(vertices, [[0, 1, 2]])], SAMPLES)
    assert not result['potential_own_coverage'].any()
    assert np.isnan(result['potential_own_depth_m']).all()
    assert result['unmodeled_or_occluded_space'] == 'unknown'
    assert result['resolved_depth_m'].tobytes() == observed.tobytes()


@pytest.mark.parametrize('samples', [[[1, .5]], [[.5, -.01]], [[np.nan, .5]]])
def test_invalid_sample_calibration_rejected(samples):
    with pytest.raises(ValueError):
        flipped_sample_locations([0, 0], samples)


def test_camera_plane_crossing_rejected_without_inventing_clip_calibration():
    with pytest.raises(ValueError, match='camera plane'):
        triangle_sample_depths([[0, 0, -1], [2, 0, 2], [0, 2, 2]],
                               [[0, 1, 2]], np.eye(3), (2, 2), SAMPLES)


def test_sensor_worker_rejects_extra_scene_fields_before_geometry(tmp_path):
    import json
    source = tmp_path / 'input'
    source.mkdir()
    (source / 'request.json').write_text(json.dumps({'cached_poses': {}}))
    with pytest.raises(ValueError, match='boundary'):
        worker(source, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()
    with pytest.raises(ValueError, match='Only resolved depth'):
        measure({}, {}, {'depth_m': np.ones((1, 1)), 'intrinsics': np.eye(3),
                         'camera_to_world': np.eye(4), 'scene_segmentation': np.zeros((1, 1))}, SAMPLES, {})


def test_fk_calibration_without_faces_requires_separate_index_checked_topology():
    calibration = {'geometries': [{'name': 'own_visual', 'vertices_local_m':
                                   [[0, 0, 2], [2, 0, 2], [0, 2, 2]]}]}
    topology = {'parent_visual_calibration_sha256': VISUAL_SHA256,
                'triangle_faces': {'own_visual': [[0, 1, 2]]}}
    validate_topology(calibration, topology)
    assert 'faces' not in calibration['geometries'][0]
    with pytest.raises(ValueError, match='reference'):
        validate_topology(calibration, {})
    topology['triangle_faces']['own_visual'] = [[0, 1, 3]]
    with pytest.raises(ValueError, match='index'):
        validate_topology(calibration, topology)
