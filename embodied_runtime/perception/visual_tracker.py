"""Bounded RGB-D feature association, independent of semantic model inference.

A declared ROI seeds a *visible feature*, not a verified object identity. Fixed
RGB appearance, metric depth, and capture-time camera pose gate subsequent
association. A lost/ambiguous chain is never silently reacquired; an explicit
new seed creates a new generation. No simulator IDs, motion extrapolation,
contact inference, plane fitting, or probabilistic model confidence is used.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite

import numpy as np

from ..contracts import ProtocolError, canonical_json, freeze


def _require(condition, code, detail=""):
    if not condition:
        raise ProtocolError(code, detail)


@dataclass(frozen=True)
class TrackerConfig:
    search_radius_px: int = 16
    search_stride_px: int = 2
    template_side: int = 16
    template_context_scale: float = 1.2
    scale_factors: tuple = (.95, 1., 1.05)
    max_appearance_error: float = .15
    min_competing_error_gap: float = .015
    competing_separation_fraction: float = .3
    min_depth_support_ratio: float = .75
    min_depth_m: float = .05
    max_depth_m: float = 3.
    max_depth_spread_m: float = .03
    max_depth_change_m: float = .05
    max_base_step_m: float = .06
    max_frame_age_s: float = .3
    history_s: float = 5.
    max_history_frames: int = 64

    def __post_init__(self):
        for name in ("search_radius_px", "search_stride_px", "template_side", "max_history_frames"):
            _require(type(getattr(self, name)) is int and getattr(self, name) > 0, "INVALID_TRACKER_CONFIG")
        _require(self.template_side >= 4 and self.search_stride_px <= self.search_radius_px,
                 "INVALID_TRACKER_CONFIG")
        for name in ("template_context_scale", "max_appearance_error", "min_competing_error_gap",
                     "competing_separation_fraction", "min_depth_support_ratio", "min_depth_m",
                     "max_depth_m", "max_depth_spread_m", "max_depth_change_m", "max_base_step_m",
                     "max_frame_age_s", "history_s"):
            value = getattr(self, name)
            _require(isinstance(value, (float, int)) and not isinstance(value, bool)
                     and isfinite(value) and value > 0, "INVALID_TRACKER_CONFIG")
        _require(self.template_context_scale >= 1 and self.min_depth_support_ratio <= 1
                 and self.competing_separation_fraction <= 1 and self.max_depth_m > self.min_depth_m,
                 "INVALID_TRACKER_CONFIG")
        _require(bool(self.scale_factors) and all(isfinite(s) and 0 < s <= 2 for s in self.scale_factors),
                 "INVALID_TRACKER_CONFIG")


@dataclass(frozen=True)
class TrackResult:
    episode_id: str
    track_id: str
    track_generation: int
    feature_id: str
    feature_generation: int
    camera_id: str
    frame_id: str
    frame_seq: int
    calibration_version: str
    capture_sim_time_s: float
    capture_monotonic_ns: int
    status: str
    roi_xyxy_px: tuple | None
    position_base_m: tuple | None
    age_s: float
    reason_codes: tuple
    metrics: Mapping
    seed_source: str
    seed_query: str
    semantic_binding: Mapping | None = None
    calibrated_confidence: None = None
    semantic_identity_verified: bool = False
    provenance: str = "sensor-derived"

    def __post_init__(self):
        object.__setattr__(self, "metrics", freeze(self.metrics))
        if self.semantic_binding is not None:
            object.__setattr__(self, "semantic_binding", freeze(self.semantic_binding))


class VisualTracker:
    """Single-camera feature chain with bounded frame metadata history.

    `initialize` requires an explicit declared seed. The query is seed context,
    not a verified semantic label. A late semantic result may bind only to an
    already reliable chain and a historical ROI; it cannot seed an unobserved
    current position using a two-second-old box. Callers estimate visible plane
    geometry separately from the returned ROI, once per depth observation.
    """

    def __init__(self, episode_id, *, config=TrackerConfig(), track_id="visual-target", feature_id="visible-roi"):
        _require(isinstance(episode_id, str) and episode_id, "INVALID_EPISODE")
        _require(all(isinstance(v, str) and v for v in (track_id, feature_id)), "INVALID_TRACK_ID")
        self.episode_id, self.config = episode_id, config
        self.track_id, self.feature_id = track_id, feature_id
        self.generation = 0
        self._template = None
        self._current = None
        self._history = OrderedDict()
        self._requests = {}
        self._semantic_results = {}
        self._binding = None
        self._query_generation = -1
        self._seed_source, self._query = "uninitialized", ""
        self._last_now_sim, self._last_now_ns = 0., 0

    @property
    def current(self):
        return self._current

    def reset(self, episode_id):
        _require(isinstance(episode_id, str) and episode_id, "INVALID_EPISODE")
        self.episode_id = episode_id
        self.generation += 1
        self._template = self._current = self._binding = None
        self._history.clear()
        self._requests.clear()
        self._semantic_results.clear()
        self._query_generation = -1
        self._seed_source, self._query = "uninitialized", ""
        self._last_now_sim, self._last_now_ns = 0., 0

    def _frame(self, frame, now_sim, now_ns):
        _require(isinstance(frame, Mapping), "INVALID_FRAME")
        needed = ("rgb", "depth_m", "intrinsics_K", "T_base_camera", "camera_id", "frame_seq",
                  "frame_id", "calibration_version", "capture_sim_time_s", "capture_monotonic_ns", "frame")
        _require(all(k in frame for k in needed), "INVALID_FRAME")
        _require(frame["frame"] == "robot_base", "FRAME_MISMATCH")
        _require(frame.get("episode_id", self.episode_id) == self.episode_id, "WRONG_EPISODE")
        _require(all(isinstance(frame[k], str) and frame[k] for k in ("camera_id", "frame_id", "calibration_version")),
                 "INVALID_FRAME_IDENTITY")
        _require(type(frame["frame_seq"]) is int and frame["frame_seq"] >= 0, "INVALID_FRAME_IDENTITY")
        captured, captured_ns = frame["capture_sim_time_s"], frame["capture_monotonic_ns"]
        _require(isinstance(now_sim, (float, int)) and isfinite(now_sim)
                 and isinstance(captured, (float, int)) and isfinite(captured)
                 and 0 <= captured <= now_sim and now_sim >= self._last_now_sim,
                 "INVALID_CAPTURE_TIME")
        _require(type(now_ns) is int and type(captured_ns) is int
                 and 0 <= captured_ns <= now_ns and now_ns >= self._last_now_ns, "INVALID_CAPTURE_TIME")
        rgb, depth = np.asarray(frame["rgb"]), np.asarray(frame["depth_m"])
        k, transform = np.asarray(frame["intrinsics_K"], dtype=float), np.asarray(frame["T_base_camera"], dtype=float)
        _require(rgb.ndim == 3 and rgb.shape[2] == 3 and rgb.dtype == np.uint8
                 and depth.shape == rgb.shape[:2] and np.issubdtype(depth.dtype, np.floating), "INVALID_IMAGE")
        _require(k.shape == (3, 3) and transform.shape == (4, 4) and np.isfinite(k).all()
                 and np.isfinite(transform).all(), "INVALID_CALIBRATION")
        _require(k[0, 0] > 0 and k[1, 1] > 0 and abs(k[0, 1]) < 1e-12 and abs(k[1, 0]) < 1e-12
                 and np.allclose(k[2], [0, 0, 1])
                 and np.allclose(transform[3], [0, 0, 0, 1])
                 and np.allclose(transform[:3, :3].T @ transform[:3, :3], np.eye(3), atol=1e-6)
                 and np.isclose(np.linalg.det(transform[:3, :3]), 1., atol=1e-6), "INVALID_CALIBRATION")
        digest = sha256()
        digest.update(canonical_json({key: frame[key] for key in needed if key not in
                                     ("rgb", "depth_m", "intrinsics_K", "T_base_camera")}).encode())
        for array in (rgb, depth, k, transform):
            digest.update(str((array.dtype.str, array.shape)).encode())
            digest.update(np.ascontiguousarray(array).tobytes())
        return rgb, depth, k, transform, digest.hexdigest()

    def _fresh(self, frame, now_sim, now_ns):
        return (now_sim-frame["capture_sim_time_s"] <= self.config.max_frame_age_s
                and (now_ns-frame["capture_monotonic_ns"])/1e9 <= self.config.max_frame_age_s)

    def _sample(self, image, centers, sizes, *, side, context=1.):
        # Vectorized, bounded nearest-neighbor sampling; no new OpenCV dependency.
        unit = (np.arange(side)+.5)/side-.5
        x = np.rint(centers[:, 0, None] + unit[None, :]*sizes[:, 0, None]*context).astype(int)
        y = np.rint(centers[:, 1, None] + unit[None, :]*sizes[:, 1, None]*context).astype(int)
        h, w = image.shape[:2]
        valid = (x.min(1) >= 0) & (x.max(1) < w) & (y.min(1) >= 0) & (y.max(1) < h)
        values = image[np.clip(y, 0, h-1)[:, :, None], np.clip(x, 0, w-1)[:, None, :]]
        return values, valid

    def _geometry(self, depth, centers, sizes, k, transform):
        patches, in_view = self._sample(depth, centers, sizes, side=8)
        valid = np.isfinite(patches) & (patches >= self.config.min_depth_m) & (patches <= self.config.max_depth_m)
        count = valid.sum((1, 2))
        support = count/64
        # Sorting finite samples avoids all-NaN median warnings for occlusion.
        values = np.sort(np.where(valid, patches, np.inf).reshape(len(centers), -1), axis=1)
        indices = np.maximum(count-1, 0)
        med = values[np.arange(len(centers)), indices//2]
        lo = values[np.arange(len(centers)), (indices*.1).astype(int)]
        hi = values[np.arange(len(centers)), (indices*.9).astype(int)]
        spread = np.full(len(centers), np.inf)
        np.subtract(hi, lo, out=spread, where=count > 0)
        good = in_view & (support >= self.config.min_depth_support_ratio) & (spread <= self.config.max_depth_spread_m)
        safe_depth = np.where(np.isfinite(med), med, 0.)
        camera_points = np.column_stack(((centers[:, 0]-k[0, 2])*safe_depth/k[0, 0],
                                         (centers[:, 1]-k[1, 2])*safe_depth/k[1, 1], safe_depth))
        points = camera_points @ transform[:3, :3].T + transform[:3, 3]
        return good, points, med, support, spread

    def _result(self, frame, now_sim, now_ns, *, status, roi=None, point=None, reasons=(), metrics=None, digest):
        metrics = dict(metrics or {}, frame_shape_px=list(frame["rgb"].shape[:2]))
        result = TrackResult(self.episode_id, self.track_id, self.generation, self.feature_id, self.generation,
                             frame["camera_id"], frame["frame_id"], frame["frame_seq"], frame["calibration_version"],
                             frame["capture_sim_time_s"], frame["capture_monotonic_ns"], status,
                             None if roi is None else tuple(float(x) for x in roi),
                             None if point is None else tuple(float(x) for x in point),
                             now_sim-frame["capture_sim_time_s"], tuple(reasons), metrics,
                             self._seed_source, self._query, self._binding if status == "TRACKED" else None)
        self._current = result
        self._last_now_sim, self._last_now_ns = now_sim, now_ns
        self._history[frame["frame_id"]] = (result, digest)
        cutoff = now_sim-self.config.history_s
        while self._history and (len(self._history) > self.config.max_history_frames
                                 or next(iter(self._history.values()))[0].capture_sim_time_s < cutoff):
            self._history.popitem(last=False)
        if status != "TRACKED":
            self._binding = None
        return result

    def initialize(self, frame, roi_xyxy_px, *, query, seed_source="manual_seed",
                   now_sim_time_s, now_monotonic_ns):
        rgb, depth, k, transform, digest = self._frame(frame, now_sim_time_s, now_monotonic_ns)
        _require(seed_source in ("manual_seed", "semantic_query", "sensor_geometry") and isinstance(query, str) and query,
                 "EXPLICIT_SEED_REQUIRED")
        roi = np.asarray(roi_xyxy_px, dtype=float)
        _require(roi.shape == (4,) and np.isfinite(roi).all() and 0 <= roi[0] < roi[2] <= rgb.shape[1]
                 and 0 <= roi[1] < roi[3] <= rgb.shape[0] and min(roi[2:]-roi[:2]) >= 4,
                 "INVALID_ROI")
        _require(self._fresh(frame, now_sim_time_s, now_monotonic_ns), "FRAME_STALE")
        self.generation += 1
        self._seed_source, self._query = seed_source, query
        self._binding = self._template = None
        center, size = (roi[:2]+roi[2:])/2, roi[2:]-roi[:2]
        appearance, in_view = self._sample(rgb, center[None, :], size[None, :],
                                           side=self.config.template_side, context=self.config.template_context_scale)
        good, point, distance, support, spread = self._geometry(depth, center[None, :], size[None, :], k, transform)
        if not good[0] or not in_view[0]:
            return self._result(frame, now_sim_time_s, now_monotonic_ns, status="LOST", digest=digest,
                                reasons=("SEED_DEPTH_OR_CONTEXT_INVALID",),
                                metrics={"depth_support_ratio": float(support[0])})
        self._template = appearance[0].astype(np.float32)/255
        self._seed_size = size.copy()
        self._seed_camera_depth = float(distance[0])
        self._seed_focal = np.array([k[0, 0], k[1, 1]])
        return self._result(frame, now_sim_time_s, now_monotonic_ns, status="TRACKED", roi=roi, point=point[0],
                            digest=digest, metrics={"depth_support_ratio": float(support[0]),
                                                    "depth_spread_m": float(spread[0]), "seed_declared": True})

    def update(self, frame, *, now_sim_time_s, now_monotonic_ns):
        rgb, depth, k, transform, digest = self._frame(frame, now_sim_time_s, now_monotonic_ns)
        previous = self._current
        _require(previous is not None, "TRACK_UNINITIALIZED")
        old = self._history.get(frame["frame_id"])
        if old:
            _require(old[1] == digest, "FRAME_ID_CONFLICT")
            _require(old[0] is previous and self._fresh(frame, now_sim_time_s, now_monotonic_ns),
                     "FRAME_STALE")
            return previous
        _require(frame["frame_seq"] > previous.frame_seq
                 and frame["capture_sim_time_s"] >= previous.capture_sim_time_s
                 and frame["capture_monotonic_ns"] >= previous.capture_monotonic_ns, "FRAME_OUT_OF_ORDER")

        def reject(reason, status="LOST", metrics=None):
            return self._result(frame, now_sim_time_s, now_monotonic_ns, status=status,
                                reasons=(reason,), metrics=metrics, digest=digest)

        if frame["camera_id"] != previous.camera_id:
            return reject("CAMERA_CHANGED_RESEED_REQUIRED")
        if frame["calibration_version"] != previous.calibration_version:
            return reject("CALIBRATION_CHANGED_RESEED_REQUIRED")
        if not self._fresh(frame, now_sim_time_s, now_monotonic_ns):
            return reject("FRAME_STALE")
        if previous.status != "TRACKED" or self._template is None:
            return reject("RESEED_REQUIRED")
        if (frame["capture_sim_time_s"]-previous.capture_sim_time_s > self.config.max_frame_age_s
                or (frame["capture_monotonic_ns"]-previous.capture_monotonic_ns)/1e9 > self.config.max_frame_age_s):
            return reject("TRACKING_GAP")
        previous_base = np.asarray(previous.position_base_m)
        camera_point = transform[:3, :3].T @ (previous_base-transform[:3, 3])
        if camera_point[2] <= self.config.min_depth_m:
            return reject("PROJECTED_FEATURE_NOT_VISIBLE")
        center = np.array([k[0, 0]*camera_point[0]/camera_point[2]+k[0, 2],
                           k[1, 1]*camera_point[1]/camera_point[2]+k[1, 2]])
        offsets = np.arange(-self.config.search_radius_px, self.config.search_radius_px+1,
                            self.config.search_stride_px)
        xx, yy = np.meshgrid(offsets, offsets)
        centers = center+np.column_stack((xx.ravel(), yy.ravel()))
        base_size = self._seed_size*self._seed_camera_depth/camera_point[2]*np.array([k[0, 0], k[1, 1]])/self._seed_focal
        sizes = np.repeat(base_size[None, :]*np.asarray(self.config.scale_factors)[:, None], len(centers), axis=0)
        centers = np.tile(centers, (len(self.config.scale_factors), 1))
        appearance, in_view = self._sample(rgb, centers, sizes, side=self.config.template_side,
                                           context=self.config.template_context_scale)
        in_view &= ((centers-sizes/2 >= 0).all(1)
                    & (centers+sizes/2 <= np.array([rgb.shape[1], rgb.shape[0]])).all(1))
        errors = np.mean(np.abs(appearance.astype(np.float32)/255-self._template), axis=(1, 2, 3))
        good, points, distances, support, spread = self._geometry(depth, centers, sizes, k, transform)
        displacement = np.linalg.norm(points-previous_base, axis=1)
        eligible = (in_view & good & (displacement <= self.config.max_base_step_m)
                    & (np.abs(distances-camera_point[2]) <= self.config.max_depth_change_m))
        if not eligible.any():
            return reject("DEPTH_OR_GEOMETRY_INCONSISTENT", metrics={"search_candidates": len(centers)})
        eligible_errors = np.where(eligible, errors, np.inf)
        winner = int(np.argmin(eligible_errors))
        score = float(errors[winner])
        if score > self.config.max_appearance_error:
            return reject("APPEARANCE_MISMATCH", metrics={"appearance_error": score})
        separation = max(self.config.search_stride_px*2, float(min(sizes[winner])*self.config.competing_separation_fraction))
        rivals = eligible & (np.linalg.norm(centers-centers[winner], axis=1) >= separation)
        second = float(np.min(errors[rivals])) if rivals.any() else None
        metrics = {"appearance_error": score, "competing_appearance_error": second,
                   "appearance_margin": None if second is None else second-score,
                   "search_candidates": len(centers), "eligible_candidates": int(eligible.sum()),
                   "depth_support_ratio": float(support[winner]), "depth_spread_m": float(spread[winner]),
                   "base_displacement_m": float(displacement[winner]),
                   "projected_center_px": center.tolist(), "matched_center_px": centers[winner].tolist()}
        if second is not None and second-score < self.config.min_competing_error_gap:
            return reject("COMPETING_APPEARANCE_MATCHES", status="AMBIGUOUS", metrics=metrics)
        roi = np.r_[centers[winner]-sizes[winner]/2, centers[winner]+sizes[winner]/2]
        return self._result(frame, now_sim_time_s, now_monotonic_ns, status="TRACKED", roi=roi,
                            point=points[winner], digest=digest, metrics=metrics)

    def register_semantic_request(self, request_id, *, source_frame_id, query, query_generation,
                                  deadline_monotonic_ns):
        _require(isinstance(request_id, str) and request_id and isinstance(query, str) and query
                 and type(query_generation) is int and query_generation >= 0, "INVALID_SEMANTIC_REQUEST")
        source = self._history.get(source_frame_id)
        _require(source is not None and source[0].status == "TRACKED", "HISTORY_MISSING")
        _require(type(deadline_monotonic_ns) is int and deadline_monotonic_ns > self._last_now_ns,
                 "PROPOSAL_EXPIRED")
        _require(query_generation >= self._query_generation, "QUERY_GENERATION_STALE")
        record = freeze(dict(episode_id=self.episode_id, generation=source[0].track_generation,
                             source_frame_id=source_frame_id, query=query, query_generation=query_generation,
                             deadline_monotonic_ns=deadline_monotonic_ns))
        _require(request_id not in self._requests or self._requests[request_id] == record, "REQUEST_ID_CONFLICT")
        self._requests[request_id] = record
        self._query_generation = query_generation

    def bind_semantic(self, observation, *, now_monotonic_ns):
        """Validate R4 semantic result against its historical tracked ROI.

        This updates only categorical binding metadata. It never invokes depth
        estimation, modifies the template, or refreshes geometry capture time.
        Multiple overlapping detections are ambiguous, never highest-score wins.
        """
        _require(isinstance(observation, Mapping), "INVALID_SEMANTIC")
        request = self._requests.get(observation.get("request_id"))
        _require(request is not None and request["episode_id"] == self.episode_id, "REQUEST_CANCELLED")
        _require(type(now_monotonic_ns) is int and now_monotonic_ns >= self._last_now_ns
                 and now_monotonic_ns < request["deadline_monotonic_ns"], "PROPOSAL_EXPIRED")
        required = ("request_id", "query_generation", "camera_id", "frame_seq", "calibration_version",
                    "capture_sim_time_s", "boxes_xyxy_px", "detection_present", "calibrated_confidence",
                    "raw_output_ref", "model_revision", "latency_ms")
        _require(all(key in observation for key in required), "INVALID_SEMANTIC")
        _require(observation["calibrated_confidence"] is None, "UNCALIBRATED_BINDING_ONLY")
        _require(observation["query_generation"] == request["query_generation"], "QUERY_GENERATION_MISMATCH")
        _require(request["query_generation"] == self._query_generation, "QUERY_GENERATION_STALE")
        entry = self._history.get(request["source_frame_id"])
        _require(entry is not None, "HISTORY_MISSING")
        source = entry[0]
        current = self._current
        _require(current is not None and current.status == "TRACKED"
                 and current.track_generation == request["generation"], "LINEAGE_BROKEN")
        _require(now_monotonic_ns-current.capture_monotonic_ns <= int(self.config.max_frame_age_s*1e9),
                 "GEOMETRY_STALE")
        _require(observation["camera_id"] == source.camera_id and observation["frame_seq"] == source.frame_seq
                 and observation["capture_sim_time_s"] == source.capture_sim_time_s, "SOURCE_MISMATCH")
        _require(observation["calibration_version"] == source.calibration_version == current.calibration_version,
                 "CALIBRATION_CHANGED")
        _require(observation["detection_present"] is True, "DETECTION_ABSENT")
        roi = np.asarray(source.roi_xyxy_px)
        height, width = source.metrics["frame_shape_px"]
        matches = 0
        for box in observation["boxes_xyxy_px"]:
            box = np.asarray(box, dtype=float)
            _require(box.shape == (4,) and np.isfinite(box).all() and np.all(box[:2] >= 0)
                     and np.all(box[2:] > box[:2]) and box[2] <= width and box[3] <= height,
                     "INVALID_SEMANTIC_BOX")
            intersection = np.prod(np.maximum(0., np.minimum(box[2:], roi[2:])-np.maximum(box[:2], roi[:2])))
            union = np.prod(box[2:]-box[:2])+np.prod(roi[2:]-roi[:2])-intersection
            matches += int(intersection/union >= .5)
        _require(matches == 1, "SEMANTIC_ASSOCIATION_AMBIGUOUS" if matches > 1 else "SEMANTIC_ROI_MISMATCH")
        fingerprint = canonical_json(observation)
        request_id = observation["request_id"]
        if request_id in self._semantic_results:
            previous_fingerprint, previous_binding = self._semantic_results[request_id]
            _require(previous_fingerprint == fingerprint, "SEMANTIC_ID_CONFLICT")
            return previous_binding
        binding = freeze(dict(request_id=request_id, query=request["query"],
                              query_generation=request["query_generation"], source_frame_id=source.frame_id,
                              current_frame_id=current.frame_id, source_capture_sim_time_s=source.capture_sim_time_s,
                              bound_monotonic_ns=now_monotonic_ns, calibrated_confidence=None,
                              semantic_identity_verified=False, evidence_kind="categorical_binding",
                              model_revision=observation["model_revision"], raw_output_ref=observation["raw_output_ref"]))
        self._semantic_results[request_id] = (fingerprint, binding)
        self._binding = binding
        return binding
