import inspect
import ast
from types import SimpleNamespace

import numpy as np

from embodied_runtime.experiments.point_temporal_probe import (
    CONDITIONS,LK_SETTINGS,condition_frames,evaluate_rows,patch_slices,track_lk,translate_rgb,
)


def test_integer_shift_no_wrapping_interpolation_or_seed_frame_change():
    rgb=np.arange(10*10*3,dtype=np.uint8).reshape(10,10,3)
    out=translate_rgb(rgb,(2,-3))
    assert np.array_equal(out[:7,2:],rgb[3:,:8])
    assert np.all(out[:,0:2]==127) and np.all(out[7:]==127)
    frames=np.stack([rgb,rgb])
    condition={**CONDITIONS[1],'shift':(2,-3)}
    transformed,seed,labels=condition_frames(frames,[4,5],condition)
    assert np.array_equal(transformed[0],rgb) and np.array_equal(transformed[1],out)
    assert labels[1]['primary_reference_pixel_index_xy']==[6.,2.]


def test_target_occlusion_offtarget_control_and_distractor_are_exact():
    rng=np.random.default_rng(1)
    frames=rng.integers(0,256,(3,100,140,3),dtype=np.uint8)
    seed=[60,60]
    target,_,labels=condition_frames(frames,seed,CONDITIONS[4])
    assert np.array_equal(target[0],frames[0])
    assert np.all(target[1][patch_slices(seed,frames[0].shape)]==127)
    assert not labels[1]['primary_local_correspondence_visible']
    control,_,labels=condition_frames(frames,seed,CONDITIONS[5])
    assert np.array_equal(control[1][patch_slices(seed,frames[0].shape)],frames[1][patch_slices(seed,frames[0].shape)])
    assert labels[1]['primary_local_correspondence_visible']
    distractor,_,_=condition_frames(frames,seed,CONDITIONS[6])
    assert np.array_equal(distractor[1][patch_slices([100,60],frames[0].shape)],frames[0][patch_slices(seed,frames[0].shape)])


def test_wrong_seed_is_geometry_only_not_an_identity_claim():
    frames=np.zeros((2,100,140,3),np.uint8)
    out,seed,labels=condition_frames(frames,[60,60],CONDITIONS[7])
    assert np.array_equal(out,frames) and np.array_equal(seed,[35,50])
    assert all(not l['seed_is_primary_reference'] and not l['semantic_identity_verified_by_tracker'] for l in labels)


def test_native_failure_keeps_remaining_unknown_rows_without_retry():
    calls=[]
    def flow(previous,current,point,unused,**settings):
        calls.append(settings)
        return point+1,np.array([[0]],np.uint8),np.array([[123.]],np.float32)
    cv2=SimpleNamespace(COLOR_RGB2GRAY=7,cvtColor=lambda frame,_:frame[:,:,0],calcOpticalFlowPyrLK=flow)
    rows=track_lk(np.zeros((4,10,10,3),np.uint8),[4,4],cv2)
    assert len(calls)==1 and calls[0]==LK_SETTINGS and len(rows)==4
    assert rows[1]['status']=='native_failure' and rows[1]['forward_patch_error'] is None
    assert rows[2]['status']==rows[3]['status']=='unknown_after_native_failure'


def test_successful_native_status_during_occlusion_is_not_scored_as_success():
    observed=[{'frame':0,'status':'seeded','point_pixel_index_xy':[4.,4.]},
              {'frame':1,'status':'native_status_ok','point_pixel_index_xy':[4.,4.]}]
    labels=[{'primary_reference_pixel_index_xy':[4.,4.],'primary_local_correspondence_visible':visible,
             'seed_is_primary_reference':True} for visible in (True,False)]
    result=evaluate_rows(observed,[4,4],labels)
    assert result[1]['tracked_distance_to_primary_reference_px']==0.
    assert result[1]['visible_primary_correspondence_error_px'] is None
    assert result[1]['native_ok_while_target_occluded']


def test_failed_reverse_attempt_is_preserved_without_propagation():
    calls=[]
    def flow(previous,current,point,unused,**settings):
        calls.append(point.copy())
        return point+2,np.array([[1 if len(calls)==1 else 0]],np.uint8),np.array([[123.]],np.float32)
    cv2=SimpleNamespace(COLOR_RGB2GRAY=7,cvtColor=lambda frame,_:frame[:,:,0],calcOpticalFlowPyrLK=flow)
    rows=track_lk(np.zeros((4,10,10,3),np.uint8),[4,4],cv2)
    assert len(calls)==2
    assert rows[1]['point_pixel_index_xy']==[6.,6.]
    assert rows[1]['attempted_backward_point_pixel_index_xy']==[8.,8.]
    assert rows[1]['forward_status']==1 and rows[1]['backward_status']==0
    assert rows[1]['status']=='native_failure'
    assert rows[1]['forward_backward_residual_px'] is None
    assert rows[1]['backward_patch_error'] is None
    assert rows[2]['status']=='unknown_after_native_failure'
    assert rows[2]['attempted_backward_point_pixel_index_xy'] is None


def test_tracker_has_no_geometry_or_evaluator_inputs():
    assert list(inspect.signature(track_lk).parameters)==['frames','seed','cv2']
    names={node.id for node in ast.walk(ast.parse(inspect.getsource(track_lk))) if isinstance(node,ast.Name)}
    assert not names & {'labels','oracle','depth','world'}
