from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.experiments.robot_only_geometry import VERSION, extract_own_positions, forward


def calibration():
    return {'version':VERSION,'bodies':[
        {'name':'fixed_base','parent':None,'position_parent_m':[1,2,3],
         'quaternion_parent_wxyz':[2**-.5,0,0,2**-.5],'joints':[]},
        {'name':'hinged_link','parent':'fixed_base','position_parent_m':[1,0,0],
         'quaternion_parent_wxyz':[1,0,0,0],'joints':[
             {'name':'hinge','kind':'hinge','qpos_reference':.2,'anchor_body_m':[.5,0,0],'axis_body':[0,0,1]}]},
        {'name':'slider','parent':'hinged_link','position_parent_m':[1,0,0],
         'quaternion_parent_wxyz':[1,0,0,0],'joints':[
             {'name':'slide','kind':'slide','qpos_reference':-.1,'anchor_body_m':[0,0,0],'axis_body':[0,1,0]}]}],
        'sites':[{'name':'tcp','body':'slider','position_body_m':[0,0,.2],'quaternion_body_wxyz':[1,0,0,0]}],
        'geometries':[{'name':'pad','body':'slider','position_body_m':[0,0,0],'quaternion_body_wxyz':[1,0,0,0],
            'vertices_local_m':[[-.1,-.2,-.3],[.1,.2,.3]],'shape_representation':'test_opposite_box_corners'}]}


def test_nonzero_base_hinge_anchor_reference_and_slide_sign():
    result = forward(calibration(),{'hinge':.2+np.pi/2,'slide':.2})
    np.testing.assert_allclose(result['bodies']['hinged_link']['position_world_m'],[1.5,3.5,3],atol=1e-14)
    np.testing.assert_allclose(result['bodies']['slider']['position_world_m'],[.5,3.2,3],atol=1e-14)
    np.testing.assert_allclose(result['sites']['tcp']['position_world_m'],[.5,3.2,3.2],atol=1e-14)
    np.testing.assert_allclose(result['geometries']['pad']['aabb_world_m'],[[.4,3,2.7],[.6,3.4,3.3]],atol=1e-14)


def test_reference_joint_positions_recover_static_chain():
    result = forward(calibration(),{'hinge':.2,'slide':-.1})
    np.testing.assert_allclose(result['bodies']['hinged_link']['position_world_m'],[1,3,3],atol=1e-14)
    np.testing.assert_allclose(result['sites']['tcp']['position_world_m'],[1,4,3.2],atol=1e-14)


@pytest.mark.parametrize('positions',[{'hinge':.2},{'hinge':.2,'slide':0,'drawer':1},
    {'hinge':np.nan,'slide':0},{'hinge':.2,'slide':np.inf}])
def test_unknown_missing_or_nonfinite_encoder_packets_rejected(positions):
    with pytest.raises(ValueError):
        forward(calibration(),positions)


def test_extractor_does_not_even_read_nonown_coordinates():
    class GuardedArchive:
        def __getitem__(self,index):
            if index not in {3,8}:
                raise AssertionError('A non-own state entry was accessed')
            return {3:.2,8:-.1}[index]
    packet = extract_own_positions(GuardedArchive(),{'hinge':3,'slide':8})
    assert packet == {'hinge':.2,'slide':-.1}
    assert forward(calibration(),packet) == forward(calibration(),{'hinge':.2,'slide':-.1})


def test_poisoning_object_positions_and_velocities_has_no_dependency():
    archive = np.arange(20,dtype=float)
    archive[[3,8]] = [.2,-.1]
    poisoned = archive.copy()
    poisoned[[i for i in range(20) if i not in {3,8}]] = np.nan
    mapping = {'hinge':3,'slide':8}
    assert forward(calibration(),extract_own_positions(archive,mapping)) == forward(
        calibration(),extract_own_positions(poisoned,mapping))


def test_no_task_specific_names_and_unclosed_chain_fails():
    model = calibration()
    renamed = deepcopy(model)
    renamed['bodies'][0]['name'] = 'arbitrary_mount'
    renamed['bodies'][1]['parent'] = 'arbitrary_mount'
    a = forward(model,{'hinge':.2,'slide':-.1})
    b = forward(renamed,{'hinge':.2,'slide':-.1})
    assert a['sites'] == b['sites'] and a['geometries'] == b['geometries']
    renamed['bodies'][1]['parent'] = 'unknown_scene_object'
    with pytest.raises(ValueError,match='self-contained'):
        forward(renamed,{'hinge':.2,'slide':-.1})
