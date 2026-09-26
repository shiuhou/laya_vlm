from itertools import product

import numpy as np
import pytest

from embodied_runtime.experiments.sensor_gripper_proximity import (
    depth_cloud, measure, projected_proxy_mask, proxy_distance)
from embodied_runtime.experiments.robot_only_geometry import VERSION


def cube():
    return np.asarray(list(product((-1.,1.),repeat=3)))


def test_analytic_box_distances_include_faces_edges_corners_and_interior():
    points = np.array([[2,0,0],[2,3,1],[2,3,4],[0,0,0],[1,1,1]],dtype=float)
    distance, nearest, inside = proxy_distance(points,cube())
    np.testing.assert_allclose(distance,[1,np.sqrt(5),np.sqrt(14),0,0],atol=1e-13)
    np.testing.assert_allclose(nearest,np.clip(points,-1,1),atol=1e-13)
    assert inside.tolist() == [False,False,False,True,True]


def test_rotated_translated_box_preserves_analytic_distance_and_nearest_point():
    angle = .713
    rotation = np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]])
    translation = np.array([3,-2,5])
    points = np.array([[2,3,4],[-2,.5,.2],[0,0,0]],dtype=float)
    distance, nearest, _ = proxy_distance(points@rotation.T+translation,cube()@rotation.T+translation)
    np.testing.assert_allclose(distance,[np.sqrt(14),1,0],atol=1e-13)
    np.testing.assert_allclose(nearest,np.clip(points,-1,1)@rotation.T+translation,atol=1e-13)


def test_positive_optical_depth_and_half_pixel_centers_only():
    depth = np.array([[2,np.nan,0],[-1,np.inf,3]])
    points,valid,pixels = depth_cloud(depth,np.eye(3),np.eye(4))
    assert valid.tolist() == [True,False,False,False,False,True]
    np.testing.assert_allclose(points,[[1,1,2],[7.5,4.5,3]])
    np.testing.assert_allclose(pixels[[0,5]],[[.5,.5],[2.5,1.5]])


def test_partial_silhouette_pixel_centers_and_offscreen_behavior():
    k = np.array([[4,0,2],[0,4,2],[0,0,1.]])
    mask,projection = projected_proxy_mask(cube()+[0,0,5],k,np.eye(4),(4,4))
    expected = np.zeros((4,4),dtype=bool);expected[1:3,1:3] = True
    np.testing.assert_array_equal(mask,expected)
    assert projection['status'] == 'overlaps_pixel_centers'
    mask,projection = projected_proxy_mask(cube()+[20,0,5],k,np.eye(4),(4,4))
    assert not mask.any() and projection['status'] == 'outside_pixel_centers'
    mask,projection = projected_proxy_mask(cube()+[0,0,-5],k,np.eye(4),(4,4))
    assert not mask.any() and projection['status'] == 'behind_camera'
    mask,projection = projected_proxy_mask(cube(),k,np.eye(4),(4,4))
    assert mask.all() and projection['status'] == 'crosses_camera_plane_exclude_all'


def test_camera_schema_rejects_nonoptical_intrinsics_and_reflection():
    k = np.eye(3);k[2,2] = 2
    with pytest.raises(ValueError,match='optical-depth'):
        depth_cloud(np.ones((2,2)),k,np.eye(4))
    transform = np.eye(4);transform[0,0] = -1
    with pytest.raises(ValueError,match='Proper'):
        depth_cloud(np.ones((2,2)),np.eye(3),transform)


def test_all_invalid_depth_yields_unknown_not_infinite_clearance():
    calibration = {'version':VERSION,'bodies':[{'name':'base','parent':None,'position_parent_m':[0,0,5],
                   'quaternion_parent_wxyz':[1,0,0,0],'joints':[]}], 'sites':[],
                   'geometries':[{'name':'proxy','body':'base','position_body_m':[0,0,0],
                   'quaternion_body_wxyz':[1,0,0,0],'vertices_local_m':cube().tolist(),
                   'shape_representation':'analytic_test_box'}]}
    result,arrays = measure(calibration,{},np.zeros((4,4)),np.eye(3),np.eye(4))
    assert result['valid_depth_pixels'] == 0
    for group in result['groups'].values():
        assert group['union']['nearest'] is None and group['union']['quantiles_m'] is None
    assert np.isnan(arrays['distance_to_proxy_m']).all()
