"""Source/lineage admission without learned inference or evaluation annotation."""
from hashlib import sha256
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.perception import tracked_mask_geometry as measurement
from embodied_runtime.perception.rgbd_geometry import GeometryConfig
from embodied_runtime.perception.surface_association import sensor_view_identity


def sample(seq=0,parent=None):
    v=dict(episode_id='episode',camera_id='frontview',frame_id=f'f{seq}',frame_seq=seq,
        capture_sim_time_s=seq*.1,capture_monotonic_ns=seq*100_000_000,calibration_version='cal',
        frame='robot_base',rgb=np.zeros((8,12,3),np.uint8),depth_m=np.full((8,12),.5,np.float32),
        intrinsics_K=np.array([[100.,0,6],[0,100.,4],[0,0,1]]),T_base_camera=np.eye(4))
    mask=np.zeros((8,12),bool)
    mask[2:6,3:9]=True
    source=sensor_view_identity(v)
    b=dict(source_identity=source,seed_source_identity_sha256=content_hash(source) if parent is None else parent['seed_source_identity_sha256'],
        mask_sha256=sha256(mask.tobytes()).hexdigest(),generation=1,lineage_id='native2',native_mask_ordinal=2,
        tracker_condition='sam2-video-singlemask/1',model_input_rgb_sha256=source['rgb_sha256'],
        parent_source_identity=None if parent is None else parent['source_identity'],status='TRACKED',reason_codes=[],
        current_domain_xyxy_px=[0,0,12,8],domain_kind='full-frame-masked-depth/1',evaluation_labels_used=False,oracle_inputs=False)
    return v,mask,b


def evaluate(v,m,b,**kwargs):
    return measurement.evaluate_tracked_mask(v,m,b,geometry_config=GeometryConfig(),eef_position_base_m=None,
                                           track_id='native2',feature_id='video-mask',**kwargs)


def test_exact_fresh_measurement_and_native_depth_denominator(monkeypatch):
    seen={}
    def estimate(depth,k,t,**kwargs):
        seen.update(depth=depth,**kwargs)
        return SimpleNamespace(to_dict=lambda:dict(geometry_status='UNKNOWN',reason_codes=['FROZEN_GATE_REJECTION']))
    monkeypatch.setattr(measurement,'estimate_visible_patch',estimate)
    _,_,seed=sample()
    v,m,b=sample(1,seed)
    result=evaluate(v,m,b,previous_binding=seed)
    assert result['admission']['admitted'] and result['geometry_evaluation']=='EVALUATED'
    assert result['patch']['reason_codes']==['FROZEN_GATE_REJECTION']
    assert np.isnan(seen['depth'][~m]).all() and np.all(seen['depth'][m]==.5)
    assert np.array_equal(seen['depth_availability_mask'],m)
    assert seen['source_frame_id']=='f1' and seen['capture_monotonic_ns']==100_000_000
    assert seen['roi_xyxy']==[0,0,12,8] and seen['config']==GeometryConfig()
    assert np.all(v['depth_m']==.5)


def test_stale_receipt_and_mask_pixel_tampering_never_reaches_geometry(monkeypatch):
    monkeypatch.setattr(measurement,'estimate_visible_patch',lambda *a,**k:pytest.fail('source not admitted'))
    v,m,b=sample()
    changed=m.copy()
    changed[0,0]=True
    with pytest.raises(ProtocolError,match='mask bytes'):
        evaluate(v,changed,b)
    later,_,_=sample(1,b)
    with pytest.raises(ProtocolError,match='current RGB-D'):
        evaluate(later,m,b)
    with pytest.raises(ProtocolError,match='labels and oracle'):
        evaluate(v,m,dict(b,evaluation_labels_used=True))
    with pytest.raises(ProtocolError,match='full-frame domain'):
        evaluate(v,m,dict(b,current_domain_xyxy_px=[3,2,9,6]))


def test_gap_lost_and_missing_history_stay_not_evaluated(monkeypatch):
    monkeypatch.setattr(measurement,'estimate_visible_patch',lambda *a,**k:pytest.fail('lineage not admitted'))
    _,_,seed=sample()
    v,m,b=sample(4,seed)
    result=evaluate(v,m,b,previous_binding=seed)
    assert result['admission']['reason']=='TRACKING_GAP' and result['patch'] is None
    v,m,b=sample(1,seed)
    result=evaluate(v,m,b)
    assert result['admission']['reason']=='LINEAGE_HISTORY_MISSING'
    result=evaluate(v,m,b,previous_binding=dict(seed,status='LOST'))
    assert result['admission']['reason']=='RESEED_REQUIRED'
    result=evaluate(v,None,dict(b,status='LOST',reason_codes=['OBJECT_SCORE_REJECTED']),previous_binding=seed)
    assert result['geometry_evaluation']=='NOT_EVALUATED' and result['patch'] is None
