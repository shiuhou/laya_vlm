"""Observed RGB-D surface geometry, without simulator state or action authority.

The ROI is a semantic hypothesis, not an object mask. Ambiguous sizeable depth
components fail closed. All estimates from one frame share one evidence source;
points, centroid and normal are not independent Kalman measurements. Defaults
are prospective engineering values, not calibrated sensor confidence.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, fields, replace
import json
from pathlib import Path
from typing import Callable, Mapping

import numpy as np

from ..contracts import ProtocolError, canonical_json, content_hash, freeze, thaw


@dataclass(frozen=True)
class GeometryConfig:
    revision: str = "p1-geometry-v1"
    min_depth_m: float = .05
    max_depth_m: float = 3.0
    min_depth_valid_ratio: float = .50
    connectivity_distance_m: float = .015
    component_ambiguity_ratio: float = .50
    min_component_points: int = 32
    target_voxel_m: float = .0025
    scene_voxel_m: float = .005
    max_target_points: int = 5000
    max_scene_points: int = 20000
    ransac_iterations: int = 128
    plane_inlier_distance_m: float = .004
    min_plane_support_ratio: float = .70
    max_plane_rms_m: float = .0025
    min_plane_tangent_spread_m: float = .005
    grid_spacing_m: float = .012
    max_grid_cells: int = 20000
    tool_contact_radius_m: float = .008
    edge_margin_m: float = .002
    pixel_sigma_px: float = .5
    depth_sigma_m: float = .0015
    calibration_covariance_floor_m2: tuple[tuple[float, ...], ...] = (
        (.000004, 0., 0.), (0., .000004, 0.), (0., 0., .000004),
    )
    normal_calibration_sigma_rad: float = .017453292519943295
    max_position_sigma_m: float = .010
    local_density_radius_m: float = .015
    uncertainty_calibrated: bool = False
    covariance_model_id: str = "engineering-floor-v1-not-calibrated"

    def __post_init__(self):
        if not self.revision or not self.covariance_model_id:
            raise ProtocolError("INVALID_SCHEMA", "geometry revision/model ID required")
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name in {"revision", "covariance_model_id", "calibration_covariance_floor_m2", "uncertainty_calibrated"}:
                continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not np.isfinite(value) or value <= 0:
                raise ProtocolError("INVALID_SCHEMA", f"positive finite {field.name} required")
        for name in ("min_component_points", "max_target_points", "max_scene_points", "ransac_iterations", "max_grid_cells"):
            if type(getattr(self, name)) is not int:
                raise ProtocolError("INVALID_SCHEMA", f"{name} must be integer")
        if type(self.uncertainty_calibrated) is not bool:
            raise ProtocolError("INVALID_SCHEMA", "uncertainty_calibrated must be bool")
        if self.min_depth_m >= self.max_depth_m or self.min_component_points < 3 or self.max_target_points < self.min_component_points:
            raise ProtocolError("INVALID_SCHEMA", "inconsistent depth/count limits")
        for name in ("min_depth_valid_ratio", "component_ambiguity_ratio", "min_plane_support_ratio"):
            if getattr(self, name) > 1:
                raise ProtocolError("INVALID_SCHEMA", f"{name} must be <=1")
        covariance = _matrix(self.calibration_covariance_floor_m2, (3, 3), "calibration covariance")
        if not np.allclose(covariance, covariance.T, atol=1e-12) or np.linalg.eigvalsh(covariance).min() <= 0:
            raise ProtocolError("INVALID_SCHEMA", "calibration floor must be positive definite")
        object.__setattr__(self, "calibration_covariance_floor_m2", tuple(map(tuple, covariance.tolist())))

    @classmethod
    def from_mapping(cls, value: Mapping) -> GeometryConfig:
        if set(value) != {field.name for field in fields(cls)}:
            raise ProtocolError("INVALID_SCHEMA", "unknown or missing geometry config fields")
        return cls(**value)

    @classmethod
    def load(cls, path: str | Path) -> GeometryConfig:
        return cls.from_mapping(json.loads(Path(path).read_text()))

    def to_dict(self):
        return asdict(self)


def _matrix(value, shape, name):
    try:
        result = np.asarray(value, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ProtocolError("INVALID_SCHEMA", f"invalid {name}") from exc
    if result.shape != shape or not np.isfinite(result).all():
        raise ProtocolError("INVALID_SCHEMA", f"invalid {name}")
    return result


def _readonly(array):
    array = np.ascontiguousarray(array)
    # bytes-backed arrays cannot be made writable by callers.
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


def _camera(K, T_base_camera):
    k = _matrix(K, (3, 3), "K")
    t = _matrix(T_base_camera, (4, 4), "T_base_camera")
    if k[0, 0] <= 0 or k[1, 1] <= 0 or not np.allclose(k[2], [0, 0, 1]) or abs(k[1, 0]) > 1e-12:
        raise ProtocolError("INVALID_SCHEMA", "invalid pinhole intrinsics")
    r = t[:3, :3]
    if not np.allclose(t[3], [0, 0, 0, 1]) or not np.allclose(r.T @ r, np.eye(3), atol=1e-7) or not np.isclose(np.linalg.det(r), 1):
        raise ProtocolError("INVALID_SCHEMA", "camera transform must be rigid and proper")
    return k, t


def _roi(roi_xyxy, width, height):
    if roi_xyxy is None:
        return (0, 0, width, height)
    roi = np.asarray(roi_xyxy, dtype=float)
    if roi.shape != (4,) or not np.isfinite(roi).all():
        raise ProtocolError("INVALID_SCHEMA", "ROI must be finite xyxy")
    if not (0 <= roi[0] < roi[2] <= width and 0 <= roi[1] < roi[3] <= height):
        raise ProtocolError("INVALID_SCHEMA", "ROI outside image or degenerate")
    # Include pixel centres inside the half-open box; never expand a supplied ROI.
    return tuple(int(np.ceil(x)) for x in roi)


@dataclass(frozen=True)
class ProjectedCloud:
    points_base_m: np.ndarray
    pixels_uv: np.ndarray
    depth_m: np.ndarray
    covariance_m2: np.ndarray
    valid_mask: np.ndarray
    source_frame_id: str
    calibration_version: str
    provenance: str = "sensor-derived"

    def __post_init__(self):
        for name in ("points_base_m", "pixels_uv", "depth_m", "covariance_m2", "valid_mask"):
            object.__setattr__(self, name, _readonly(getattr(self, name)))


def _point_covariance(u, v, z, k, r, config):
    # Jacobian of inverse K times [u,v,1]*z supports calibrated skew as well.
    inv = np.linalg.inv(k)
    u, v, z = np.broadcast_arrays(u, v, z)
    rays = np.stack((u, v, np.ones_like(z)), axis=-1) @ inv.T
    jacobian = np.stack((z[..., None] * inv[:, 0], z[..., None] * inv[:, 1], rays), axis=-1)
    noise = np.diag([config.pixel_sigma_px**2, config.pixel_sigma_px**2, config.depth_sigma_m**2])
    camera_cov = jacobian @ noise @ np.swapaxes(jacobian, -1, -2)
    return r @ camera_cov @ r.T + np.asarray(config.calibration_covariance_floor_m2)


def project_depth(depth_m, K, T_base_camera, *, source_frame_id: str,
                  calibration_version: str, config: GeometryConfig | None = None,
                  roi_xyxy=None) -> ProjectedCloud:
    """Project top-left-origin metric depth. No unit or orientation guessing."""
    config = config or GeometryConfig()
    depth = np.asarray(depth_m)
    if depth.ndim != 2 or depth.dtype.kind != "f" or min(depth.shape) <= 0:
        raise ProtocolError("INVALID_SCHEMA", "metric depth must be a nonempty float HW array")
    if not isinstance(source_frame_id, str) or not source_frame_id or not isinstance(calibration_version, str) or not calibration_version:
        raise ProtocolError("INVALID_SCHEMA", "frame and calibration identity required")
    k, t = _camera(K, T_base_camera)
    h, w = depth.shape
    x0, y0, x1, y1 = _roi(roi_xyxy, w, h)
    valid = np.isfinite(depth) & (depth >= config.min_depth_m) & (depth <= config.max_depth_m)
    roi_mask = np.zeros_like(valid)
    roi_mask[y0:y1, x0:x1] = True
    valid &= roi_mask
    v, u = np.nonzero(valid)
    z = depth[v, u].astype(float)
    camera_points = np.column_stack((u, v, np.ones_like(u))) @ np.linalg.inv(k).T * z[:, None]
    points = camera_points @ t[:3, :3].T + t[:3, 3]
    covariance = _point_covariance(u, v, z, k, t[:3, :3], config)
    return ProjectedCloud(points, np.column_stack((u, v)), z, covariance, valid,
                          source_frame_id, calibration_version)


def voxel_downsample(points_base_m, *, voxel_m: float, max_points: int) -> np.ndarray:
    """Deterministic centroid voxels and evenly spaced lexicographic cap.

    This is perception resolution/cost control, never action candidate pruning.
    """
    points = np.asarray(points_base_m, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all() or not np.isfinite(voxel_m) or voxel_m <= 0 or type(max_points) is not int or max_points < 1:
        raise ProtocolError("INVALID_SCHEMA", "invalid voxel inputs")
    if not len(points):
        return _readonly(points)
    keys = np.floor(points / voxel_m).astype(np.int64)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    centroids = np.zeros((len(counts), 3))
    np.add.at(centroids, inverse, points)
    centroids /= counts[:, None]
    if len(centroids) > max_points:
        centroids = centroids[np.linspace(0, len(centroids) - 1, max_points, dtype=int)]
    return _readonly(centroids)


@dataclass(frozen=True)
class FeasibilityEvidence:
    reachable: bool | None
    swept_clear: bool | None
    fresh: bool | None
    validator_id: str
    source_ids: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if any(value is not None and type(value) is not bool for value in (self.reachable, self.swept_clear, self.fresh)):
            raise ProtocolError("INVALID_SCHEMA", "feasibility predicates require bool or unknown")
        if not self.validator_id or not self.source_ids:
            raise ProtocolError("INVALID_SCHEMA", "feasibility evidence requires validator/source IDs")
        object.__setattr__(self, "source_ids", tuple(self.source_ids))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))


@dataclass(frozen=True)
class TargetPointCandidate:
    point_id: str
    track_id: str
    feature_id: str
    position_base_m: tuple[float, float, float]
    normal_base: tuple[float, float, float]
    covariance_m2: tuple[tuple[float, ...], ...]
    edge_margin_m: float
    required_edge_margin_m: float
    local_density_per_m2: float
    eef_distance_m: float | None
    eef_normal_distance_m: float | None
    eef_tangent_error_m: float | None
    geometry_valid: bool
    usable_status: str
    reason_codes: tuple[str, ...]
    source_frame_id: str
    calibration_version: str
    uncertainty_calibrated: bool
    covariance_model_id: str
    feasibility_evidence: FeasibilityEvidence | None = None
    normal_alignment_deg: float | None = None
    visible_clearance_m: float | None = None
    provenance: str = "sensor-derived"

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class PatchEstimate:
    geometry_status: str
    reason_codes: tuple[str, ...]
    centroid_base_m: tuple[float, float, float] | None
    normal_base: tuple[float, float, float] | None
    covariance_m2: tuple[tuple[float, ...], ...] | None
    normal_covariance: tuple[tuple[float, ...], ...] | None
    candidates: tuple[TargetPointCandidate, ...]
    metrics: Mapping
    source_frame_id: str
    calibration_version: str
    track_id: str
    feature_id: str
    capture_sim_time_s: float
    capture_monotonic_ns: int
    source_roi_xyxy: tuple[int, int, int, int]
    config_revision: str
    provenance: str = "sensor-derived"

    def __post_init__(self):
        object.__setattr__(self, "metrics", freeze(self.metrics))

    def to_dict(self):
        return {field.name: thaw(getattr(self, field.name)) for field in fields(self)}


def _components(cloud, valid_mask, threshold):
    h, w = valid_mask.shape
    index = np.full((h, w), -1, dtype=int)
    index[cloud.pixels_uv[:, 1], cloud.pixels_uv[:, 0]] = np.arange(len(cloud.points_base_m))
    seen = np.zeros((h, w), dtype=bool)
    components = []
    threshold2 = threshold**2
    for u, v in cloud.pixels_uv:
        if seen[v, u] or not valid_mask[v, u]:
            continue
        seen[v, u] = True
        pending = deque([(int(u), int(v))])
        members = []
        while pending:
            x, y = pending.popleft()
            i = index[y, x]
            members.append(i)
            for nx, ny in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if not (0 <= nx < w and 0 <= ny < h) or seen[ny, nx] or not valid_mask[ny, nx]:
                    continue
                j = index[ny, nx]
                delta = cloud.points_base_m[i] - cloud.points_base_m[j]
                if delta @ delta <= threshold2:
                    seen[ny, nx] = True
                    pending.append((nx, ny))
        components.append(np.asarray(members, dtype=int))
    return sorted(components, key=lambda ids: (-len(ids), int(ids[0])))


def _svd_plane(points, camera_position, config):
    centroid = points.mean(axis=0)
    _, singular, vt = np.linalg.svd(points - centroid, full_matrices=False)
    spread = singular / np.sqrt(len(points))
    if len(spread) < 3 or spread[1] < config.min_plane_tangent_spread_m:
        return None
    normal = vt[-1]
    if normal @ (camera_position - centroid) < 0:
        normal = -normal
    residual = (points-centroid) @ normal
    rms = float(np.sqrt(np.mean(residual**2)))
    # Conservative floor persists even on perfect synthetic planes and large N.
    angle_variance = max(config.normal_calibration_sigma_rad**2,
                         (max(rms, config.depth_sigma_m) / spread[1])**2)
    normal_cov = (np.eye(3) - np.outer(normal, normal)) * angle_variance
    return centroid, normal, rms, normal_cov, spread


def _boundary(mask):
    padded = np.pad(mask, 1, constant_values=False)
    interior = (padded[:-2, 1:-1] & padded[2:, 1:-1]
                & padded[1:-1, :-2] & padded[1:-1, 2:])
    return mask & ~interior


def _nearest_distance(points, boundary_points):
    result = np.full(len(points), np.inf)
    for start in range(0, len(points), 128):
        batch = points[start:start+128]
        distances = np.sum((batch[:, None, :] - boundary_points[None, :, :])**2, axis=2)
        result[start:start+len(batch)] = np.sqrt(distances.min(axis=1))
    return result


def estimate_visible_patch(
    depth_m, K, T_base_camera, *, roi_xyxy, source_frame_id: str,
    calibration_version: str, track_id: str, feature_id: str,
    capture_sim_time_s: float, capture_monotonic_ns: int,
    config: GeometryConfig | None = None, seed: int = 0,
    eef_position_base_m=None, robot_self_mask=None,
    robot_self_mask_source_ids: tuple[str, ...] = (),
    feasibility: Callable[[TargetPointCandidate], FeasibilityEvidence] | None = None,
    depth_availability_mask=None,
) -> PatchEstimate:
    """Fit only the observed ROI; no target axis, closed state, or hidden extent.

    ``robot_self_mask`` may only come from declared robot geometry/proprioception,
    not object-ID segmentation. Its use is explicitly recorded. A fixed-cabinet
    ROI can be processed with exactly this function; static identity and closure
    verification remain upstream measurement hypotheses.
    """
    config = config or GeometryConfig()
    if depth_availability_mask is not None:
        availability_mask = np.asarray(depth_availability_mask)
        availability_depth = np.asarray(depth_m)
        if availability_mask.dtype != bool or availability_mask.shape != availability_depth.shape:
            raise ProtocolError("INVALID_SCHEMA", "depth availability mask must be bool HW")
        if np.any(np.isfinite(availability_depth) & ~availability_mask):
            raise ProtocolError("INVALID_SCHEMA", "outside-support depth must remain UNKNOWN")
    k, t = _camera(K, T_base_camera)
    cloud = project_depth(depth_m, k, t, source_frame_id=source_frame_id,
                          calibration_version=calibration_version, config=config, roi_xyxy=roi_xyxy)
    for name, value in (("track_id", track_id), ("feature_id", feature_id)):
        if not isinstance(value, str) or not value:
            raise ProtocolError("INVALID_SCHEMA", f"{name} required")
    if isinstance(capture_sim_time_s, bool) or not np.isfinite(capture_sim_time_s) or capture_sim_time_s < 0 or type(capture_monotonic_ns) is not int or capture_monotonic_ns < 0 or type(seed) is not int or seed < 0:
        raise ProtocolError("INVALID_SCHEMA", "invalid capture time or seed")
    h, w = cloud.valid_mask.shape
    roi = _roi(roi_xyxy, w, h)
    x0, y0, x1, y1 = roi
    valid = cloud.valid_mask.copy()
    excluded = 0
    if robot_self_mask is not None:
        mask = np.asarray(robot_self_mask)
        if mask.shape != valid.shape or mask.dtype != bool:
            raise ProtocolError("INVALID_SCHEMA", "robot self mask must be bool HW")
        if not robot_self_mask_source_ids or any(not isinstance(source, str) or not source for source in robot_self_mask_source_ids):
            raise ProtocolError("INFORMATION_BOUNDARY", "robot self mask requires robot-model/proprioception source IDs")
        excluded = int(np.count_nonzero(valid & mask))
        valid &= ~mask
    roi_size = (x1-x0) * (y1-y0)
    metrics = {
        "roi_pixel_count": roi_size, "valid_depth_count": int(valid.sum()),
        "depth_valid_ratio": float(valid.sum()/max(1, roi_size)),
        "robot_self_excluded_count": excluded, "seed": seed,
        "robot_self_mask_source_ids": list(robot_self_mask_source_ids),
        "config_sha256": content_hash(config.to_dict()),
        "uncertainty_calibrated": config.uncertainty_calibrated,
        "covariance_model_id": config.covariance_model_id,
        "same_frame_evidence_group": source_frame_id,
        "component_selection": "dominant_3d_connected_component_or_abstain",
        "reachability_verified": False, "sweep_verified": False,
    }
    if depth_availability_mask is not None:
        observed = (availability_mask & np.isfinite(availability_depth)
                    & (availability_depth >= config.min_depth_m) & (availability_depth <= config.max_depth_m))
        if robot_self_mask is not None:
            observed &= ~mask
        mask_count = int(availability_mask.sum())
        mask_valid = int(observed.sum())
        in_roi = int(availability_mask[y0:y1, x0:x1].sum())
        metrics.update(depth_availability_domain="full_native_mask",
            mask_pixel_count=mask_count, valid_depth_inside_mask=mask_valid,
            depth_availability=None if mask_count == 0 else mask_valid/mask_count,
            original_roi_depth_valid_ratio=metrics["depth_valid_ratio"],
            mask_pixels_inside_original_roi=in_roi,
            mask_pixels_outside_original_roi=mask_count-in_roi,
            mask_original_box_coverage=in_roi/max(1, roi_size),
            depth_availability_inside_original_roi=None if in_roi == 0 else int(valid.sum())/in_roi)
        metrics["depth_valid_ratio"] = metrics["depth_availability"]
    common = dict(source_frame_id=source_frame_id, calibration_version=calibration_version,
                  track_id=track_id, feature_id=feature_id, capture_sim_time_s=float(capture_sim_time_s),
                  capture_monotonic_ns=capture_monotonic_ns, source_roi_xyxy=roi,
                  config_revision=config.revision)

    def unknown(reason, status="UNKNOWN"):
        return PatchEstimate(status, (reason,), None, None, None, None, (), metrics, **common)

    if depth_availability_mask is not None and mask_count == 0:
        return unknown("EMPTY_DEPTH_AVAILABILITY_MASK")
    if metrics["depth_valid_ratio"] < config.min_depth_valid_ratio:
        return unknown("INSUFFICIENT_VALID_DEPTH")
    components = _components(cloud, valid, config.connectivity_distance_m)
    metrics["component_sizes"] = [len(ids) for ids in components]
    if not components or len(components[0]) < config.min_component_points:
        return unknown("INSUFFICIENT_CONNECTED_SUPPORT")
    if len(components) > 1 and len(components[1]) >= config.min_component_points and len(components[1])/len(components[0]) >= config.component_ambiguity_ratio:
        return unknown("AMBIGUOUS_DEPTH_COMPONENTS", "AMBIGUOUS")
    component_ids = components[0]
    raw_points = cloud.points_base_m[component_ids]
    points = voxel_downsample(raw_points, voxel_m=config.target_voxel_m, max_points=config.max_target_points)
    metrics["selected_component_count"] = len(raw_points)
    metrics["fitted_point_count"] = len(points)
    if len(points) < config.min_component_points:
        return unknown("INSUFFICIENT_VOXEL_SUPPORT")
    rng = np.random.default_rng(seed)
    best = None
    best_score = (-1, -np.inf)
    for _ in range(config.ransac_iterations):
        a, b, c = points[rng.choice(len(points), 3, replace=False)]
        normal = np.cross(b-a, c-a)
        norm = np.linalg.norm(normal)
        if norm < 1e-12:
            continue
        normal /= norm
        residual = np.abs((points-a) @ normal)
        support = residual <= config.plane_inlier_distance_m
        score = (int(support.sum()), -float(residual[support].sum()))
        if score > best_score:
            best, best_score = support, score
    if best is None or best.sum() < config.min_component_points:
        return unknown("PLANE_DEGENERATE")
    fit = _svd_plane(points[best], t[:3, 3], config)
    if fit is None:
        return unknown("PLANE_DEGENERATE")
    centroid, normal, rms, normal_cov, spread = fit
    raw_residual = np.abs((raw_points-centroid) @ normal)
    raw_support = raw_residual <= config.plane_inlier_distance_m
    support_ratio = float(raw_support.mean())
    metrics.update(plane_support_ratio=support_ratio, plane_rms_m=rms,
                   tangent_spread_m=spread[:2].tolist())
    if support_ratio < config.min_plane_support_ratio:
        return unknown("INSUFFICIENT_PLANE_SUPPORT")
    if rms > config.max_plane_rms_m:
        return unknown("PLANE_RESIDUAL_TOO_LARGE")
    support_mask = np.zeros_like(valid)
    pixels = cloud.pixels_uv[component_ids[raw_support]]
    support_mask[pixels[:, 1], pixels[:, 0]] = True
    boundary_mask = _boundary(support_mask)
    index_map = np.full(valid.shape, -1, dtype=int)
    index_map[cloud.pixels_uv[:, 1], cloud.pixels_uv[:, 0]] = np.arange(len(cloud.points_base_m))
    boundary_points = cloud.points_base_m[index_map[boundary_mask]]
    # Out-of-plane sensor error cannot manufacture extra in-plane clearance.
    boundary_points = boundary_points - np.outer((boundary_points-centroid) @ normal, normal)
    supported_points = raw_points[raw_support]
    covs = cloud.covariance_m2[component_ids[raw_support]]
    # Do not divide same-frame or calibration uncertainty by the point count.
    covariance = covs.mean(axis=0)
    sigma = float(np.sqrt(np.linalg.eigvalsh(covariance).max()))
    erosion = config.tool_contact_radius_m + 2*sigma + config.edge_margin_m
    sampling_margin = float(np.max(cloud.depth_m[component_ids]) * np.sqrt(1/k[0, 0]**2 + 1/k[1, 1]**2))
    interior_distances = _nearest_distance(supported_points, boundary_points) - sampling_margin
    interior = supported_points[interior_distances >= erosion]
    metrics.update(position_sigma_m=sigma, erosion_m=erosion, sampling_margin_m=sampling_margin,
                   boundary_point_count=len(boundary_points), eroded_support_count=len(interior))
    if len(interior) >= config.min_component_points:
        interior_fit = _svd_plane(interior, t[:3, 3], config)
        if interior_fit is not None:
            centroid, normal, rms, normal_cov, spread = interior_fit
            metrics["plane_rms_m"] = rms
            metrics["fit_support"] = "tool_eroded_interior"
            if rms > config.max_plane_rms_m:
                return unknown("ERODED_PLANE_RESIDUAL_TOO_LARGE")
        else:
            return unknown("ERODED_PLANE_DEGENERATE")
    else:
        metrics["fit_support"] = "visible_surface_no_tool_interior"
    if sigma > config.max_position_sigma_m:
        return unknown("POSITION_UNCERTAINTY_TOO_LARGE")
    # Prefer a fixed chart; choosing the least-aligned axis would switch X/Y
    # on arbitrarily small noise around a camera-facing Z-normal plane.
    chart = "base_y" if abs(normal[0]) > .9 else "base_x"
    basis_axis = np.array([0., 1., 0.]) if chart == "base_y" else np.array([1., 0., 0.])
    axis_u = basis_axis - normal * (basis_axis @ normal)
    axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(normal, axis_u)
    metrics.update(grid_chart=chart, grid_axis_u_base=axis_u.tolist(), grid_axis_v_base=axis_v.tolist())
    # Global base-frame tangent grid: IDs encode grid cells, never candidate rank.
    uv = supported_points @ np.column_stack((axis_u, axis_v))
    low = np.ceil(uv.min(axis=0)/config.grid_spacing_m).astype(int)
    high = np.floor(uv.max(axis=0)/config.grid_spacing_m).astype(int)
    cells = int(np.maximum(high-low+1, 0).prod())
    metrics["grid_cell_count"] = cells
    if cells > config.max_grid_cells:
        return unknown("GEOMETRY_GRID_BUDGET_EXCEEDED")
    grid_ids = [(i, j) for i in range(low[0], high[0]+1) for j in range(low[1], high[1]+1)]
    plane_offset = float(centroid @ normal)
    grid_points = np.array([i*config.grid_spacing_m*axis_u + j*config.grid_spacing_m*axis_v + plane_offset*normal for i, j in grid_ids]).reshape(-1, 3)
    distances = _nearest_distance(grid_points, boundary_points)-sampling_margin
    camera_points = (grid_points-t[:3, 3]) @ t[:3, :3]
    image_h = camera_points @ k.T
    candidate_list = []
    rejected = {"outside_visible_support": 0, "insufficient_edge_margin": 0, "position_uncertainty": 0}
    eef = None if eef_position_base_m is None else _matrix(eef_position_base_m, (3,), "EEF position")
    for (i, j), point, camera_point, image, edge in zip(grid_ids, grid_points, camera_points, image_h, distances):
        if camera_point[2] <= 0:
            rejected["outside_visible_support"] += 1
            continue
        pu, pv = image[:2]/image[2]
        x, y = int(round(pu)), int(round(pv))
        if not (0 <= x < w and 0 <= y < h) or not support_mask[y, x] or abs(float(depth_m[y, x])-camera_point[2]) > config.plane_inlier_distance_m:
            rejected["outside_visible_support"] += 1
            continue
        point_cov = _point_covariance(pu, pv, camera_point[2], k, t[:3, :3], config)
        point_sigma = float(np.sqrt(np.linalg.eigvalsh(point_cov).max()))
        required = config.tool_contact_radius_m + 2*point_sigma + config.edge_margin_m
        if point_sigma > config.max_position_sigma_m:
            rejected["position_uncertainty"] += 1
            continue
        if edge < required:
            rejected["insufficient_edge_margin"] += 1
            continue
        density = float(np.count_nonzero(np.linalg.norm(supported_points-point, axis=1) <= config.local_density_radius_m)/(np.pi*config.local_density_radius_m**2))
        eef_delta = None if eef is None else eef-point
        normal_distance = None if eef_delta is None else float(eef_delta @ normal)
        reasons = ("FEASIBILITY_NOT_EVALUATED",) + (() if config.uncertainty_calibrated else ("UNCALIBRATED_UNCERTAINTY",))
        candidate = TargetPointCandidate(
            f"{track_id}:{feature_id}:grid:{chart}:{i}:{j}", track_id, feature_id,
            tuple(point.tolist()), tuple(normal.tolist()), tuple(map(tuple, point_cov.tolist())),
            float(edge), required, density,
            None if eef_delta is None else float(np.linalg.norm(eef_delta)), normal_distance,
            None if eef_delta is None else float(np.linalg.norm(eef_delta-normal_distance*normal)),
            True, "UNKNOWN", reasons, source_frame_id, calibration_version,
            config.uncertainty_calibrated, config.covariance_model_id,
        )
        if feasibility is not None:
            evidence = feasibility(candidate)
            if not isinstance(evidence, FeasibilityEvidence):
                raise ProtocolError("INVALID_SCHEMA", "feasibility callback must return typed evidence")
            checks = (evidence.reachable, evidence.swept_clear, evidence.fresh)
            status = "BLOCKED" if False in checks else "USABLE" if all(value is True for value in checks) and config.uncertainty_calibrated else "UNKNOWN"
            reason_codes = evidence.reason_codes + (() if config.uncertainty_calibrated else ("UNCALIBRATED_UNCERTAINTY",))
            if None in checks:
                reason_codes += ("FEASIBILITY_UNKNOWN",)
            candidate = replace(candidate, usable_status=status, reason_codes=reason_codes, feasibility_evidence=evidence)
        candidate_list.append(candidate)
    metrics["candidate_rejection_counts"] = rejected
    metrics["candidate_count"] = len(candidate_list)
    metrics["point_order"] = "lexicographic_plane_grid_no_utility_pruning"
    canonical_json(metrics)
    return PatchEstimate(
        "VALID", () if candidate_list else ("NO_TOOL_INTERIOR_CANDIDATE",),
        tuple(centroid.tolist()), tuple(normal.tolist()), tuple(map(tuple, covariance.tolist())),
        tuple(map(tuple, normal_cov.tolist())), tuple(candidate_list), metrics, **common,
    )
