import numpy as np

from embodied_runtime.experiments.first_contact_observability import (
    backproject,local_point,nearest_box_surface,project_world,world_point)


def test_optical_depth_and_pixel_center_roundtrip_under_rotated_camera():
    k=np.array([[300.,0,192.],[0,300.,192.],[0,0,1.]])
    t=np.array([[0.,0.,1.,.3],[1.,0.,0.,-.2],[0.,1.,0.,1.],[0.,0.,0.,1.]])
    uv=np.array([151.5,234.5]);depth=.8
    p=backproject(uv,depth,k,t)
    actual,z=project_world(p,k,t)
    np.testing.assert_allclose(actual,uv,rtol=0,atol=1e-12)
    np.testing.assert_allclose(z,depth,rtol=0,atol=1e-12)
    assert np.linalg.norm(p-t[:3,3])>depth  # Optical depth is not ray range.


def test_rigid_contact_correspondence_does_not_freeze_moving_world_coordinate():
    post={'position':np.array([.1,.2,.3]),'rotation':np.array([[0.,-1,0],[1.,0,0],[0,0,1.]])}
    pre={'position':np.array([.1,.19,.3]),'rotation':post['rotation']}
    p=np.array([.12,.21,.3]);local=local_point(p,post)
    np.testing.assert_allclose(world_point(local,post),p)
    np.testing.assert_allclose(world_point(local,pre),p-np.array([0,.01,0]))


def test_box_surface_inside_and_outside_are_surface_points_not_volume_clamps():
    size=np.array([.1,.2,.3])
    np.testing.assert_array_equal(nearest_box_surface(np.array([.09,0.,0.]),size),[.1,0.,0.])
    np.testing.assert_array_equal(nearest_box_surface(np.array([.11,.21,0.]),size),[.1,.2,0.])
    np.testing.assert_array_equal(nearest_box_surface(np.array([-.09,0.,0.]),size),[-.1,0.,0.])
