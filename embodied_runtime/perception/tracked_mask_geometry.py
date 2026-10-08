"""Fresh RGB-D measurement under a provenance-bound propagated mask.

Admission establishes source/lineage consistency, never semantic correctness.
Learned object scores are not calibrated probabilities and are not converted to
geometry confidence here. A current mask cannot provide missing/old depth.
"""
from __future__ import annotations

from hashlib import sha256

import numpy as np

from ..contracts import content_hash, require, thaw
from .rgbd_geometry import estimate_visible_patch, _roi
from .surface_association import sensor_view_identity


def fresh_mask_geometry(view, support, roi, *, geometry_config, eef_position_base_m,
                        track_id, feature_id):
    """Unchanged native-depth denominator and geometry gates, current depth only."""
    support = np.asarray(support)
    require(support.dtype == bool and support.shape == view['depth_m'].shape,
            'current bool mask and depth shapes must agree', 'SOURCE_MISMATCH')
    masked = np.asarray(view['depth_m']).copy()
    masked[~support] = np.nan
    return estimate_visible_patch(masked, view['intrinsics_K'], view['T_base_camera'],
        roi_xyxy=roi, source_frame_id=view['frame_id'], calibration_version=view['calibration_version'],
        track_id=track_id, feature_id=feature_id, capture_sim_time_s=view['capture_sim_time_s'],
        capture_monotonic_ns=view['capture_monotonic_ns'],config=geometry_config, seed=0,
        eef_position_base_m=eef_position_base_m, depth_availability_mask=support).to_dict()


def tracked_mask_admission(view, mask, binding, *, previous_binding=None, max_gap_s=.3):
    """Check exact source and declared consecutive lineage; no implicit reseed.

    The caller owns terminal lineage state and passes the previous admission's
    binding. A rejected frame cannot be omitted to bridge a failed association.
    Model execution receipts must separately establish how the mask was made;
    metadata alone cannot prove that learned propagation is physically correct.
    """
    require(isinstance(max_gap_s,(int,float)) and not isinstance(max_gap_s,bool)
            and np.isfinite(max_gap_s) and max_gap_s > 0,'positive finite max gap required')
    identity = sensor_view_identity(view)
    require(content_hash(binding['source_identity']) == content_hash(identity),
            'mask receipt does not bind the current RGB-D source','SOURCE_MISMATCH')
    require(binding['evaluation_labels_used'] is False and binding['oracle_inputs'] is False,
            'evaluation labels and oracle inputs prohibited','INFORMATION_BOUNDARY')
    for name in ('lineage_id','tracker_condition','seed_source_identity_sha256'):
        require(isinstance(binding[name],str) and binding[name], 'nonempty '+name+' required')
    require(type(binding['generation']) is int and binding['generation'] > 0
            and type(binding['native_mask_ordinal']) is int and binding['native_mask_ordinal'] >= 0,
            'positive generation and native ordinal required')
    if binding['status'] != 'TRACKED':
        return dict(admitted=False,reason='TRACK_NOT_ADMITTED',tracker_reason_codes=binding.get('reason_codes',[]))
    require(binding['model_input_rgb_sha256'] == identity['rgb_sha256'],
            'current mask must be tied to current RGB input','SOURCE_MISMATCH')
    mask = np.asarray(mask)
    require(mask.dtype == bool and mask.shape == view['depth_m'].shape
            and sha256(mask.tobytes()).hexdigest() == binding['mask_sha256'],
            'mask bytes differ from current frame receipt','SOURCE_MISMATCH')
    if not mask.any():
        return dict(admitted=False,reason='EMPTY_CURRENT_MASK')
    roi = binding['current_domain_xyxy_px']
    h,w = mask.shape
    _roi(roi,w,h)
    require(binding['domain_kind'] in ('full-frame-masked-depth/1','tracked-source-box/1'),
            'explicit supported search domain required')
    if binding['domain_kind'] == 'full-frame-masked-depth/1':
        require(np.array_equal(roi,[0,0,w,h]),'full-frame domain must equal sensor extent')
    if previous_binding is None:
        if binding.get('parent_source_identity') is not None:
            return dict(admitted=False,reason='LINEAGE_HISTORY_MISSING')
        require(binding['seed_source_identity_sha256'] == content_hash(identity),
                'first mask must bind its actual seed source','SOURCE_MISMATCH')
    else:
        for name in ('lineage_id','generation','native_mask_ordinal','tracker_condition','seed_source_identity_sha256'):
            require(binding[name] == previous_binding[name], 'lineage field changed: '+name,'LINEAGE_MISMATCH')
        if previous_binding['status'] != 'TRACKED':
            return dict(admitted=False,reason='RESEED_REQUIRED')
        previous = previous_binding['source_identity']
        require(content_hash(binding['parent_source_identity']) == content_hash(previous),
                'declared parent does not equal previous observed source','LINEAGE_MISMATCH')
        for name in ('episode_id','camera_id','calibration_version','rgb_shape','depth_shape','intrinsics_K','coordinate_frame'):
            if content_hash(identity[name]) != content_hash(previous[name]):
                return dict(admitted=False,reason='SOURCE_CHANGED_RESEED_REQUIRED')
        require(identity['frame_id'] != previous['frame_id'] and identity['frame_seq'] > previous['frame_seq']
                and identity['capture_sim_time_s'] >= previous['capture_sim_time_s']
                and identity['capture_monotonic_ns'] >= previous['capture_monotonic_ns'],
                'tracked source capture order must increase','FRAME_OUT_OF_ORDER')
        if (identity['capture_sim_time_s']-previous['capture_sim_time_s'] > max_gap_s
                or (identity['capture_monotonic_ns']-previous['capture_monotonic_ns'])/1e9 > max_gap_s):
            return dict(admitted=False,reason='TRACKING_GAP')
    return dict(admitted=True,reason=None,semantic_identity_verified=False,
                mask_current_rgb_binding_verified=True,online_freshness_evaluated=False)


def evaluate_tracked_mask(view, mask, binding, *, geometry_config, eef_position_base_m,
                          track_id, feature_id, previous_binding=None, max_gap_s=.3):
    """Evaluate only an admitted mask; keep geometry rejections distinct from loss."""
    admission = tracked_mask_admission(view,mask,binding,previous_binding=previous_binding,max_gap_s=max_gap_s)
    patch = None
    if admission['admitted']:
        patch = fresh_mask_geometry(view,mask,binding['current_domain_xyxy_px'],geometry_config=geometry_config,
            eef_position_base_m=eef_position_base_m,track_id=track_id,feature_id=feature_id)
    return dict(patch=patch,geometry_evaluation='EVALUATED' if patch is not None else 'NOT_EVALUATED',
                admission=admission,mask_binding=thaw(binding),measurement_contract='tracked-current-mask-depth/1')
