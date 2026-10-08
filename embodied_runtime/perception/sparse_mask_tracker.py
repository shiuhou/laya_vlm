"""Development RGB sparse-flow mask lineage; independent of VisualTracker.

The native semantic support is a hypothesis, not a verified object identity.
Observed RGB features estimate bounded inter-frame similarity transforms. Each
current support is the original support warped once by the composed transform;
it is not a new SAM segmentation. Geometry must use the current observed depth.
LOST/AMBIGUOUS are terminal until an explicit fresh source-bound initialization.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from hashlib import sha256
from math import isfinite

import numpy as np

from ..contracts import content_hash, freeze, require, thaw
from .rgbd_geometry import _roi
from .surface_association import sensor_view_identity
from .visual_tracker import VisualTracker


@dataclass(frozen=True)
class FlowTrackerConfig:
    revision: str = 'p1-sparse-flow-native-support-dev/1'
    max_features: int = 128
    min_features: int = 8
    feature_quality: float = .01
    feature_min_distance_px: float = 3.
    feature_block_size: int = 3
    feature_mask_erosion_px: int = 1
    lk_window_px: int = 15
    lk_max_level: int = 2
    lk_iterations: int = 30
    lk_epsilon: float = .01
    max_fb_error_px: float = 1.
    max_lk_error_gray: float = 20.
    min_retained_feature_ratio: float = .60
    min_inlier_ratio: float = .75
    ransac_reprojection_px: float = 1.5
    ransac_iterations: int = 1000
    ransac_confidence: float = .99
    min_feature_hull_fraction: float = .10
    min_feature_covariance_eigenvalue_px2: float = 2.
    max_image_step_px: float = 24.
    max_scale_change: float = .10
    max_rotation_deg: float = 10.
    min_depth_support_ratio: float = .75
    min_depth_m: float = .05
    max_depth_m: float = 3.
    max_base_step_m: float = .06
    max_depth_change_m: float = .05
    max_displacement_residual_m: float = .015
    min_warped_area_ratio: float = .90
    max_frame_age_s: float = .30

    def __post_init__(self):
        for field in fields(self):
            if field.name == 'revision':
                require(isinstance(self.revision, str) and self.revision, 'flow revision required')
                continue
            value = getattr(self, field.name)
            require(isinstance(value, (int, float)) and not isinstance(value, bool)
                    and isfinite(value) and value > 0, 'positive finite flow config: '+field.name)
        for name in ('max_features', 'min_features', 'feature_block_size', 'feature_mask_erosion_px',
                     'lk_window_px', 'lk_max_level', 'lk_iterations', 'ransac_iterations'):
            require(type(getattr(self, name)) is int, 'integer flow config: '+name)
        require(self.max_features >= self.min_features >= 3 and self.feature_block_size % 2 == 1
                and self.lk_window_px % 2 == 1 and self.min_depth_m < self.max_depth_m,
                'inconsistent flow counts/depth/window')
        for name in ('feature_quality', 'min_retained_feature_ratio', 'min_inlier_ratio',
                     'ransac_confidence', 'min_feature_hull_fraction', 'min_depth_support_ratio',
                     'min_warped_area_ratio', 'max_scale_change'):
            require(getattr(self,name) < 1, 'flow ratio must be below one: '+name)

    def to_dict(self):
        return asdict(self)


def _owned(array):
    array = np.asarray(array)
    return np.frombuffer(array.tobytes(),dtype=array.dtype).reshape(array.shape)


def _finite_list(array):
    """Persist failed optical-flow outputs as unknown, never invented pixels."""
    value = np.asarray(array)
    return np.where(np.isfinite(value),value,None).tolist()


@dataclass(frozen=True)
class FlowTrackResult:
    episode_id: str
    track_id: str
    track_generation: int
    frame_id: str
    frame_seq: int
    camera_id: str
    calibration_version: str
    capture_sim_time_s: float
    capture_monotonic_ns: int
    source_identity: object
    seed_source_identity_sha256: str
    native_mask_sha256: str
    native_mask_ordinal: int
    initial_support_sha256: str
    status: str
    reason_codes: tuple
    support_mask: np.ndarray | None
    current_roi_xyxy_px: tuple | None
    transform_seed_to_current: tuple | None
    metrics: object
    semantic_identity_verified: bool = False
    calibrated_confidence: None = None
    provenance: str = 'sensor-derived'

    def __post_init__(self):
        if self.support_mask is not None:
            object.__setattr__(self, 'support_mask', _owned(self.support_mask))
        object.__setattr__(self,'source_identity',freeze(self.source_identity))
        object.__setattr__(self,'metrics',freeze(self.metrics))

    def to_dict(self):
        row = {f.name: thaw(getattr(self,f.name)) for f in fields(self) if f.name != 'support_mask'}
        row.update(support_mask_sha256=None if self.support_mask is None else sha256(self.support_mask.tobytes()).hexdigest(),
                   support_pixels=0 if self.support_mask is None else int(self.support_mask.sum()),
                   support_measurement='tracked-native-support/1')
        return row


class SparseMaskTracker:
    def __init__(self, episode_id, *, config=FlowTrackerConfig(), track_id='sparse-native-support'):
        import cv2
        self.cv = cv2
        self.episode_id, self.config, self.track_id = episode_id, config, track_id
        self._validator = VisualTracker(episode_id)
        self.current = None
        self.generation = 0
        self._last_now_sim, self._last_now_ns = 0., 0

    def _validate(self, view, now_sim, now_ns):
        require(now_sim >= self._last_now_sim and now_ns >= self._last_now_ns,
                'processing clocks must be monotonic', 'INVALID_CAPTURE_TIME')
        self._validator._frame(view, now_sim, now_ns)

    def _fresh(self, view, now_sim, now_ns):
        return (now_sim-view['capture_sim_time_s'] <= self.config.max_frame_age_s
                and (now_ns-view['capture_monotonic_ns'])/1e9 <= self.config.max_frame_age_s)

    def _result(self, view, now_sim, now_ns, status, reason=None, *, mask=None, roi=None, matrix=None, metrics=None):
        result = FlowTrackResult(self.episode_id,self.track_id,self.generation,view['frame_id'],view['frame_seq'],
            view['camera_id'],view['calibration_version'],view['capture_sim_time_s'],view['capture_monotonic_ns'],
            sensor_view_identity(view),self._seed_identity,self._native_hash,self._ordinal,self._support_hash,
            status,() if reason is None else (reason,),mask,None if roi is None else tuple(roi),
            None if matrix is None else tuple(map(tuple,matrix)),metrics or {})
        self.current = result
        self._last_now_sim,self._last_now_ns = now_sim,now_ns
        return result

    def _depth(self, view, points):
        points = np.asarray(points).reshape(-1,2)
        depth = np.asarray(view['depth_m'])
        finite = np.isfinite(points).all(1)
        safe_points = np.where(finite[:,None],points,0.)
        xy = np.rint(safe_points).astype(int)
        inside = finite & (xy >= 0).all(1) & (xy[:,0] < depth.shape[1]) & (xy[:,1] < depth.shape[0])
        xy[:,0] = np.clip(xy[:,0],0,depth.shape[1]-1)
        xy[:,1] = np.clip(xy[:,1],0,depth.shape[0]-1)
        z = depth[xy[:,1],xy[:,0]]
        valid = inside & np.isfinite(z) & (z >= self.config.min_depth_m) & (z <= self.config.max_depth_m)
        k,t = np.asarray(view['intrinsics_K']),np.asarray(view['T_base_camera'])
        camera = np.column_stack((safe_points,np.ones(len(points)))) @ np.linalg.inv(k).T * z[:,None]
        base = camera @ t[:3,:3].T + t[:3,3]
        return valid,base,z

    def _coverage(self, points, mask):
        points = np.asarray(points).reshape(-1,2)
        hull = self.cv.contourArea(self.cv.convexHull(points.astype(np.float32)))
        eigen = float(np.linalg.eigvalsh(np.cov(points.T)).min()) if len(points) >= 3 else 0.
        return float(hull/max(1,int(mask.sum()))), eigen

    def initialize(self, view, native_mask, box_xyxy_px, *, source_identity_sha256,
                   native_mask_sha256, native_mask_ordinal, now_sim_time_s, now_monotonic_ns):
        self._validate(view,now_sim_time_s,now_monotonic_ns)
        require(self._fresh(view,now_sim_time_s,now_monotonic_ns),'seed frame stale','FRAME_STALE')
        native = np.asarray(native_mask)
        require(native.dtype == bool and native.shape == view['depth_m'].shape,
                'native mask shape/dtype required','SOURCE_MISMATCH')
        require(content_hash(sensor_view_identity(view)) == source_identity_sha256
                and sha256(native.tobytes()).hexdigest() == native_mask_sha256,
                'native pixels and exact frame source required','SOURCE_MISMATCH')
        require(type(native_mask_ordinal) is int and native_mask_ordinal >= 0,'native ordinal required')
        x0,y0,x1,y1 = _roi(box_xyxy_px,native.shape[1],native.shape[0])
        support = np.zeros_like(native)
        support[y0:y1,x0:x1] = native[y0:y1,x0:x1]
        self._seed_identity,self._native_hash,self._ordinal = source_identity_sha256,native_mask_sha256,native_mask_ordinal
        self._support_hash = sha256(support.tobytes()).hexdigest()
        self.generation += 1
        self._seed_support = _owned(support)
        self._seed_box = np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]],dtype=float)
        self._matrix = np.eye(3)
        gray = self.cv.cvtColor(view['rgb'],self.cv.COLOR_RGB2GRAY)
        valid_depth = np.isfinite(view['depth_m']) & (view['depth_m'] >= self.config.min_depth_m) & (view['depth_m'] <= self.config.max_depth_m)
        support_ratio = float((valid_depth & support).sum()/max(1,int(support.sum())))
        metrics = dict(depth_support_ratio=support_ratio,original_support_pixels=int(support.sum()))
        if not support.any() or support_ratio < self.config.min_depth_support_ratio:
            return self._result(view,now_sim_time_s,now_monotonic_ns,'LOST','SEED_DEPTH_SUPPORT_INSUFFICIENT',metrics=metrics)
        width = self.config.feature_mask_erosion_px*2+1
        feature_mask = self.cv.erode((support & valid_depth).astype(np.uint8),np.ones((width,width),np.uint8))
        points = self.cv.goodFeaturesToTrack(gray,maxCorners=self.config.max_features,
            qualityLevel=self.config.feature_quality,minDistance=self.config.feature_min_distance_px,
            mask=feature_mask,blockSize=self.config.feature_block_size)
        count = 0 if points is None else len(points)
        metrics['seed_features'] = count
        if count < self.config.min_features:
            return self._result(view,now_sim_time_s,now_monotonic_ns,'LOST','INSUFFICIENT_SEED_FEATURES',metrics=metrics)
        points = points.reshape(-1,2)
        valid,base,z = self._depth(view,points)
        points,base,z = points[valid],base[valid],z[valid]
        metrics['seed_feature_pixels_xy'] = points.tolist()
        metrics.update(zip(('feature_hull_fraction','feature_covariance_min_eigenvalue_px2'),self._coverage(points,support)))
        if (len(points) < self.config.min_features or metrics['feature_hull_fraction'] < self.config.min_feature_hull_fraction
                or metrics['feature_covariance_min_eigenvalue_px2'] < self.config.min_feature_covariance_eigenvalue_px2):
            return self._result(view,now_sim_time_s,now_monotonic_ns,'AMBIGUOUS','INSUFFICIENT_FEATURE_SPATIAL_SUPPORT',metrics=metrics)
        self._gray,self._points,self._base,self._z = _owned(gray),points,base,z
        return self._result(view,now_sim_time_s,now_monotonic_ns,'TRACKED',mask=support,
                            roi=(x0,y0,x1,y1),matrix=self._matrix,metrics=metrics)

    def update(self, view, *, now_sim_time_s, now_monotonic_ns):
        self._validate(view,now_sim_time_s,now_monotonic_ns)
        previous = self.current
        require(previous is not None,'explicit native seed required','TRACK_UNINITIALIZED')
        require(view['frame_seq'] > previous.frame_seq and view['frame_id'] != previous.frame_id
                and view['capture_sim_time_s'] >= previous.capture_sim_time_s
                and view['capture_monotonic_ns'] >= previous.capture_monotonic_ns,
                'capture frame order must increase','FRAME_OUT_OF_ORDER')
        def reject(reason, *, ambiguous=False, metrics=None):
            return self._result(view,now_sim_time_s,now_monotonic_ns,
                'AMBIGUOUS' if ambiguous else 'LOST',reason,metrics=metrics)
        if view['camera_id'] != previous.camera_id or view['calibration_version'] != previous.calibration_version:
            return reject('SOURCE_CHANGED_RESEED_REQUIRED')
        if previous.status != 'TRACKED':
            return reject('RESEED_REQUIRED')
        if not self._fresh(view,now_sim_time_s,now_monotonic_ns):
            return reject('FRAME_STALE')
        if (view['capture_sim_time_s']-previous.capture_sim_time_s > self.config.max_frame_age_s
                or (view['capture_monotonic_ns']-previous.capture_monotonic_ns)/1e9 > self.config.max_frame_age_s):
            return reject('TRACKING_GAP')
        gray = self.cv.cvtColor(view['rgb'],self.cv.COLOR_RGB2GRAY)
        old = self._points.astype(np.float32).reshape(-1,1,2)
        args = dict(winSize=(self.config.lk_window_px,)*2,maxLevel=self.config.lk_max_level,
            criteria=(self.cv.TERM_CRITERIA_EPS | self.cv.TERM_CRITERIA_COUNT,self.config.lk_iterations,self.config.lk_epsilon))
        new,forward,errors = self.cv.calcOpticalFlowPyrLK(self._gray,gray,old,None,**args)
        if new is None or forward is None:
            return reject('FLOW_NOT_FOUND')
        back,backward,_ = self.cv.calcOpticalFlowPyrLK(gray,self._gray,new,None,**args)
        if back is None or backward is None:
            return reject('BACKWARD_FLOW_NOT_FOUND')
        p,q,b = old.reshape(-1,2),new.reshape(-1,2),back.reshape(-1,2)
        fb = np.linalg.norm(b-p,axis=1)
        good = (forward.ravel() != 0) & (backward.ravel() != 0) & np.isfinite(q).all(1) & np.isfinite(b).all(1)
        good &= (fb <= self.config.max_fb_error_px) & (errors.ravel() <= self.config.max_lk_error_gray)
        good &= np.linalg.norm(q-p,axis=1) <= self.config.max_image_step_px
        metrics = dict(previous_features=len(p),flow_admitted_features=int(good.sum()),
                       retained_feature_ratio=float(good.mean()),
                       feature_pairs=dict(previous_xy=_finite_list(p),current_xy=_finite_list(q),
                           backward_xy=_finite_list(b),forward_valid=forward.ravel().astype(bool).tolist(),
                           backward_valid=backward.ravel().astype(bool).tolist(),
                           fb_error_px=_finite_list(fb),lk_error_gray=_finite_list(errors.ravel()),
                           flow_admitted=good.tolist()))
        if good.sum() < self.config.min_features or good.mean() < self.config.min_retained_feature_ratio:
            return reject('INSUFFICIENT_FORWARD_BACKWARD_FLOW',metrics=metrics)
        valid,base,z = self._depth(view,q)
        displacement = base-self._base
        good &= valid & (np.linalg.norm(displacement,axis=1) <= self.config.max_base_step_m)
        good &= np.abs(z-self._z) <= self.config.max_depth_change_m
        metrics['depth_consistent_features'] = int(good.sum())
        if good.sum() < self.config.min_features or good.mean() < self.config.min_retained_feature_ratio:
            return reject('FEATURE_DEPTH_INCONSISTENT',metrics=metrics)
        residual = np.linalg.norm(displacement-np.median(displacement[good],axis=0),axis=1)
        good &= residual <= self.config.max_displacement_residual_m
        metrics['coherent_3d_features'] = int(good.sum())
        if good.sum() < self.config.min_features or good.mean() < self.config.min_retained_feature_ratio:
            return reject('INCONSISTENT_3D_MOTION',ambiguous=True,metrics=metrics)
        self.cv.setRNGSeed(0)
        affine,inliers = self.cv.estimateAffinePartial2D(p[good],q[good],method=self.cv.RANSAC,
            ransacReprojThreshold=self.config.ransac_reprojection_px,maxIters=self.config.ransac_iterations,
            confidence=self.config.ransac_confidence,refineIters=10)
        if affine is None or inliers is None or not np.isfinite(affine).all():
            return reject('SIMILARITY_UNDETERMINED',ambiguous=True,metrics=metrics)
        selected = np.flatnonzero(good)[inliers.ravel().astype(bool)]
        metrics.update(inlier_features=len(selected),inlier_ratio=float(inliers.mean()),
                       inlier_original_indices=selected.tolist(),step_similarity_matrix=affine.tolist())
        if len(selected) < self.config.min_features or inliers.mean() < self.config.min_inlier_ratio:
            return reject('COMPETING_FLOW_MOTIONS',ambiguous=True,metrics=metrics)
        scale = float(np.hypot(affine[0,0],affine[1,0]))
        rotation = float(np.degrees(np.arctan2(affine[1,0],affine[0,0])))
        metrics.update(step_scale=scale,step_rotation_deg=rotation,
                       max_fb_error_px=float(fb[selected].max()),max_3d_displacement_m=float(np.linalg.norm(displacement[selected],axis=1).max()))
        if abs(scale-1) > self.config.max_scale_change or abs(rotation) > self.config.max_rotation_deg:
            return reject('TRANSFORM_OUT_OF_BOUNDS',metrics=metrics)
        matrix = np.vstack((affine,[0,0,1])) @ self._matrix
        support = self.cv.warpAffine(self._seed_support.astype(np.uint8),matrix[:2],(gray.shape[1],gray.shape[0]),
            flags=self.cv.INTER_NEAREST,borderMode=self.cv.BORDER_CONSTANT,borderValue=0).astype(bool)
        expected_area = int(self._seed_support.sum()) * abs(np.linalg.det(matrix[:2,:2]))
        area_ratio = float(support.sum()/max(1.,expected_area))
        valid_depth = np.isfinite(view['depth_m']) & (view['depth_m'] >= self.config.min_depth_m) & (view['depth_m'] <= self.config.max_depth_m)
        ratio = float((valid_depth & support).sum()/max(1,int(support.sum())))
        coverage,eigen = self._coverage(q[selected],support)
        metrics.update(warped_area_ratio=area_ratio,depth_support_ratio=ratio,
                       feature_hull_fraction=coverage,feature_covariance_min_eigenvalue_px2=eigen)
        if area_ratio < self.config.min_warped_area_ratio:
            return reject('SUPPORT_LEFT_VIEW',metrics=metrics)
        if ratio < self.config.min_depth_support_ratio:
            return reject('CURRENT_MASK_DEPTH_INSUFFICIENT',metrics=metrics)
        if coverage < self.config.min_feature_hull_fraction or eigen < self.config.min_feature_covariance_eigenvalue_px2:
            return reject('INSUFFICIENT_FEATURE_SPATIAL_SUPPORT',ambiguous=True,metrics=metrics)
        corners = np.column_stack((self._seed_box,np.ones(4))) @ matrix.T
        lo,hi = corners[:,:2].min(0),corners[:,:2].max(0)
        lo,hi = np.maximum(lo,0),np.minimum(hi,[gray.shape[1],gray.shape[0]])
        if not (lo < hi).all():
            return reject('SUPPORT_LEFT_VIEW',metrics=metrics)
        self._gray,self._points,self._base,self._z = _owned(gray),q[selected],base[selected],z[selected]
        self._matrix = matrix
        return self._result(view,now_sim_time_s,now_monotonic_ns,'TRACKED',mask=support,
                            roi=np.r_[lo,hi],matrix=matrix,metrics=metrics)
