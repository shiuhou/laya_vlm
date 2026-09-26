import numpy as np
import pytest

from embodied_runtime.experiments.coarse_point_grounding_audit import pixel_ray, ray_measurement, unique_rows


def test_single_ray_uses_exact_pixel_center_and_optical_depth():
    k=np.array([[2.,0.,1.],[0.,2.,1.],[0.,0.,1.]])
    t=np.eye(4); t[:3,3]=[1.,2.,3.]
    origin,direction,norm=pixel_ray([1,1],k,t)
    assert np.array_equal(origin,[1,2,3])
    assert direction==pytest.approx(np.array([.25,.25,1.])/norm)
    r=ray_measurement(origin,direction,norm,2*norm,7,7,2.001,{'mesh_name':'target'})
    assert r['target_member'] and r['ray_optical_depth_m']==pytest.approx(2.)
    assert r['ray_surface_world_m']==pytest.approx([1.5,2.5,5.])
    assert r['sensor_minus_ray_optical_depth_mm']==pytest.approx(1.)


def test_no_hit_is_unknown_not_negative_identity():
    r=ray_measurement(np.zeros(3),np.array([0.,0.,1.]),1.,-1.,-1,7,1.,{})
    assert r['target_member'] is None and r['membership']=='unknown_no_ray_hit'
    assert r['ray_surface_world_m'] is None and r['absolute_depth_residual_mm'] is None


def test_other_cabinet_handle_distinguished_without_promoting_to_target():
    r=ray_measurement(np.zeros(3),np.array([0.,0.,1.]),1.,1.,8,7,1.,
        {'mesh_name':'wooden_cabinet_bottom_handle_vis','body_name':'wooden_cabinet_1_cabinet_bottom'})
    assert r['target_member'] is False and r['membership']=='other_cabinet_handle'
    r=ray_measurement(np.zeros(3),np.array([0.,0.,1.]),1.,1.,8,7,1.,
        {'mesh_name':'cabinet_panel','body_name':'wooden_cabinet_1_cabinet_bottom'})
    assert r['membership']=='other_visual_geom'


def test_duplicate_source_ids_rejected():
    row={'kind':'vision_capture','data':{'capture_seq':1}}
    with pytest.raises(ValueError,match='duplicate'):
        unique_rows([row,row],'vision_capture','capture_seq')
