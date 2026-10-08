"""Prospective CPU flow fixtures, no real experiment frames or human labels."""
from hashlib import sha256

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.perception.surface_association import sensor_view_identity
from embodied_runtime.perception.sparse_mask_tracker import SparseMaskTracker

cv2 = pytest.importorskip('cv2')


def frame(seq=0, *, shift=0, depth=.5, occluded=False):
    source = np.random.default_rng(2).integers(0,255,(96,128,3),dtype=np.uint8)
    rgb = cv2.warpAffine(source,np.array([[1.,0,shift],[0,1.,0]]),(128,96))
    if occluded:
        rgb[:] = 127
    return dict(episode_id='unit',camera_id='frontview',frame_id=f'unit/{seq}',frame_seq=seq,
        capture_sim_time_s=seq*.1,capture_monotonic_ns=seq*100_000_000,calibration_version='cal',
        frame='robot_base',rgb=rgb,depth_m=np.full((96,128),depth,dtype=np.float32),
        intrinsics_K=np.array([[100.,0,64],[0,100.,48],[0,0,1.]]),T_base_camera=np.eye(4))


def initialize(view=None):
    view = frame() if view is None else view
    mask = np.zeros((96,128),bool)
    mask[20:76,20:108] = True
    tracker = SparseMaskTracker('unit')
    args = dict(source_identity_sha256=content_hash(sensor_view_identity(view)),
        native_mask_sha256=sha256(mask.tobytes()).hexdigest(),native_mask_ordinal=2,
        now_sim_time_s=view['capture_sim_time_s'],now_monotonic_ns=view['capture_monotonic_ns'])
    result = tracker.initialize(view,mask,(24,24,104,72),**args)
    assert result.status == 'TRACKED',result.to_dict()
    return tracker,result,mask,args


def update(tracker,view):
    return tracker.update(view,now_sim_time_s=view['capture_sim_time_s'],now_monotonic_ns=view['capture_monotonic_ns'])


def test_shift_keeps_full_source_mask_lineage_and_uses_current_depth():
    original = frame()
    tracker,seed,mask,_ = initialize(original)
    original['rgb'][:] = 0
    mask[:] = False
    with pytest.raises(ValueError):
        seed.support_mask.setflags(write=True)
    for seq in (1,2,3):
        result = update(tracker,frame(seq,shift=seq*2))
        assert result.status == 'TRACKED',result.to_dict()
        assert result.native_mask_sha256 == seed.native_mask_sha256
        assert result.native_mask_ordinal == 2 and result.track_generation == seed.track_generation
        assert result.support_mask.sum() >= seed.support_mask.sum()*.98
        assert result.capture_monotonic_ns == seq*100_000_000
        np.testing.assert_allclose(result.current_roi_xyxy_px,[24+seq*2,24,104+seq*2,72],atol=.1)
        np.testing.assert_allclose(np.array(result.transform_seed_to_current)[:2,2],[seq*2,0],atol=.1)
        assert result.to_dict()['support_measurement'] == 'tracked-native-support/1'
    # New observed depth contradicts the old support; old depth cannot rescue it.
    failed = update(tracker,frame(4,shift=8,depth=.8))
    assert failed.status == 'LOST' and failed.reason_codes == ('FEATURE_DEPTH_INCONSISTENT',)
    assert failed.support_mask is None


def test_occlusion_lost_is_terminal_no_reseed():
    tracker,_,_,_ = initialize()
    failed = update(tracker,frame(1,occluded=True))
    assert failed.status == 'LOST'
    assert failed.reason_codes == ('INSUFFICIENT_FORWARD_BACKWARD_FLOW',)
    restored = update(tracker,frame(2))
    assert restored.status == 'LOST' and restored.reason_codes == ('RESEED_REQUIRED',)


def test_exact_native_source_and_camera_boundary():
    tracker,_,mask,args = initialize()
    bad = frame()
    bad['rgb'][0,0,0] ^= 1
    with pytest.raises(ProtocolError,match='exact frame source'):
        SparseMaskTracker('unit').initialize(bad,mask,(24,24,104,72),**args)
    bad_mask = mask.copy()
    bad_mask[30,30] = False
    with pytest.raises(ProtocolError,match='native pixels'):
        SparseMaskTracker('unit').initialize(frame(),bad_mask,(24,24,104,72),**args)
    result = update(tracker,dict(frame(1),camera_id='wrist'))
    assert result.reason_codes == ('SOURCE_CHANGED_RESEED_REQUIRED',)


def test_gap_and_stale_frames_never_refresh_source_clocks():
    tracker,_,_,_ = initialize()
    view = dict(frame(1),capture_monotonic_ns=400_000_000)
    result = update(tracker,view)
    assert result.reason_codes == ('TRACKING_GAP',)
    tracker,_,_,_ = initialize()
    result = tracker.update(frame(1),now_sim_time_s=1.,now_monotonic_ns=1_000_000_000)
    assert result.reason_codes == ('FRAME_STALE',)
    assert result.capture_monotonic_ns == 100_000_000


def test_textureless_support_rejected_without_inventing_features():
    view = frame(occluded=True)
    mask = np.ones(view['depth_m'].shape,bool)
    result = SparseMaskTracker('unit').initialize(view,mask,(24,24,104,72),
        source_identity_sha256=content_hash(sensor_view_identity(view)),
        native_mask_sha256=sha256(mask.tobytes()).hexdigest(),native_mask_ordinal=0,
        now_sim_time_s=0.,now_monotonic_ns=0)
    assert result.reason_codes == ('INSUFFICIENT_SEED_FEATURES',)
    assert result.support_mask is None


def test_competing_observed_motions_do_not_warp_whole_mask_as_one_surface():
    tracker,_,_,_ = initialize()
    view = frame(1,shift=2)
    view['rgb'][:,64:] = frame(1,shift=-2)['rgb'][:,64:]
    result = update(tracker,view)
    assert result.status == 'AMBIGUOUS',result.to_dict()
    assert result.reason_codes[0] in ('INCONSISTENT_3D_MOTION','COMPETING_FLOW_MOTIONS')
    assert result.support_mask is None


def test_intrinsics_change_requires_new_source_instead_of_native_flow_call():
    tracker,_,_,_ = initialize()
    view = frame(1)
    view['intrinsics_K'][0,0] += 1
    result = update(tracker,view)
    assert result.reason_codes == ('SOURCE_CHANGED_RESEED_REQUIRED',)


def test_invalid_flow_coordinate_preserved_unknown_and_not_given_to_opencv(monkeypatch):
    tracker,_,_,_ = initialize()
    native = cv2.calcOpticalFlowPyrLK
    calls = []
    def injected(*args,**kwargs):
        assert np.isfinite(args[2]).all()
        new,status,error = native(*args,**kwargs)
        if not calls:
            new[0,0] = np.nan
        calls.append(1)
        return new,status,error
    monkeypatch.setattr(cv2,'calcOpticalFlowPyrLK',injected)
    result = update(tracker,frame(1,shift=2))
    assert result.status == 'TRACKED'
    assert result.metrics['feature_pairs']['current_xy'][0] == (None,None)
    assert result.metrics['feature_pairs']['flow_admitted'][0] is False
