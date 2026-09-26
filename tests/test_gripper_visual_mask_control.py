import numpy as np

from embodied_runtime.experiments.gripper_visual_mask_control import summarize


def test_mask_reselects_fixed_distances_without_changing_them():
    distance=np.array([[[.1,.8],[.2,.4]],[[.3,.2],[.4,.1]]]);before=distance.copy()
    mask=np.array([[False,True],[True,True]])
    result=summarize(distance,mask,['a','b'],np.ones((2,2)),np.eye(3),np.eye(4))
    assert result['union']['nearest']['pixel_xy']==[1,1]
    assert result['union']['nearest']['distance_m']==.1
    assert result['per_proxy']['a']['nearest']['pixel_xy']==[1,0]
    np.testing.assert_array_equal(distance,before)


def test_complete_visual_exclusion_returns_unknown():
    result=summarize(np.ones((2,2,2)),np.zeros((2,2),dtype=bool),['a','b'],np.ones((2,2)),np.eye(3),np.eye(4))
    assert result['union']['nearest'] is None and result['union']['point_count']==0
    assert all(stats['nearest'] is None for stats in result['per_proxy'].values())
