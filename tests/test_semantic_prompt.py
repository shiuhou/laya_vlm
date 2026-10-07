import hashlib
import numpy as np
import pytest
from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.semantic_prompt import point_prompt, mask_point_admission
from embodied_runtime.perception.rgbd_geometry import GeometryConfig
from embodied_runtime.perception.surface_association import sensor_view_identity
from embodied_runtime.experiments.point_grounding_probe import generation_audit


def fixture():
    view=dict(rgb=np.zeros((10,10,3),np.uint8),depth_m=np.full((10,10),.7),
        intrinsics_K=np.eye(3),T_base_camera=np.eye(4),frame_id='f',frame_seq=1,
        camera_id='c',frame='robot_base',episode_id='e',calibration_version='s',
        capture_sim_time_s=0.,capture_monotonic_ns=1)
    raw='<box><550><550></box><|im_end|>'
    record=dict(source_identity=sensor_view_identity(view),query='front',evaluation_labels_used=False,
        status='COMPLETE',raw_output=raw,audit=generation_audit([1,2],10,1000,2),
        response_sha256=hashlib.sha256(raw.encode()).hexdigest())
    return view,record


def test_continuous_prompt_retained_but_floor_must_be_in_ceil_geometry_roi():
    view,r=fixture()
    prompt=point_prompt(view,[0,0,10,10],r,query='front',config=GeometryConfig())
    assert prompt['admitted'] and prompt['point_xy']==[5.5,5.5] and prompt['sample_pixel_xy']==[5,5]
    rejected=point_prompt(view,[5.2,0,10,10],r,query='front',config=GeometryConfig())
    assert rejected['reason']=='POINT_SAMPLE_OUTSIDE_GEOMETRY_ROI'
    outside=point_prompt(view,[0,0,5.5,10],r,query='front',config=GeometryConfig())
    assert outside['reason']=='POINT_OUTSIDE_ORIGINAL_BOX'


def test_no_prefix_salvage_source_or_label_substitution_and_missing_depth():
    view,r=fixture()
    with pytest.raises(ProtocolError):
        point_prompt(view,[0,0,10,10],dict(r,evaluation_labels_used=True),query='front',config=GeometryConfig())
    with pytest.raises(ProtocolError):
        point_prompt(view,[0,0,10,10],dict(r,query='other'),query='front',config=GeometryConfig())
    incomplete=dict(r,audit=generation_audit([1,1],10,1000,2))
    assert point_prompt(view,[0,0,10,10],incomplete,query='front',config=GeometryConfig())['reason']=='INCOMPLETE_GENERATION'
    view['depth_m'][5,5]=np.nan; r['source_identity']=sensor_view_identity(view)
    assert point_prompt(view,[0,0,10,10],r,query='front',config=GeometryConfig())['reason']=='POINT_DEPTH_UNAVAILABLE'


def test_point_containment_is_admission_only_not_semantic_identity():
    view,r=fixture(); p=point_prompt(view,[0,0,10,10],r,query='front',config=GeometryConfig())
    native=np.zeros((10,10),bool)
    assert mask_point_admission(native,p,0)['reason']=='POINT_MASK_CONTRADICTION'
    native[5,5]=True
    a=mask_point_admission(native,p,2)
    assert a['admitted'] and not a['semantic_identity_verified'] and not a['for_execution']
