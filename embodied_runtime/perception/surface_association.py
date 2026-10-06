"""Sensor surface inventory and exact-pixel semantic hypothesis association.

A box bounds a search; neither largest component nor first plane is a target.
All sizeable plane supports and residual pixels survive. A unique model point
may bind a hypothesis, never prove semantic identity, fixedness or push safety.
Original patch/track gates are reused unchanged; no annotation input exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np

from ..contracts import content_hash, require
from .rgbd_geometry import GeometryConfig, _components, _svd_plane, project_depth, voxel_downsample


@dataclass(frozen=True)
class ObservedSurface:
    surface_id: str
    component_id: str
    support_mask: np.ndarray
    centroid_base_m: tuple
    normal_base: tuple
    rms_m: float
    tangent_spread_m: tuple
    plane_valid: bool

    def evidence(self):
        v, u = np.nonzero(self.support_mask)
        # Original pixel supports, compact row spans; no invented polygon.
        spans = []
        for row in np.unique(v):
            xs = u[v == row]
            breaks = np.flatnonzero(np.diff(xs) != 1)+1
            for part in np.split(xs, breaks):
                spans.append([int(row), int(part[0]), int(part[-1])+1])
        return dict(surface_id=self.surface_id, component_id=self.component_id,
                    support_pixel_count=len(v), support_row_spans=spans,
                    support_mask_sha256=hashlib.sha256(self.support_mask.tobytes()).hexdigest(),
                    centroid_base_m=list(self.centroid_base_m), normal_base=list(self.normal_base),
                    rms_m=self.rms_m, tangent_spread_m=list(self.tangent_spread_m),
                    plane_valid=self.plane_valid, provenance="sensor-derived", semantic_identity_verified=False)


@dataclass(frozen=True)
class SurfaceInventory:
    source: dict
    surfaces: tuple
    residual_mask: np.ndarray
    components: tuple

    def evidence(self):
        v, u = np.nonzero(self.residual_mask)
        return dict(source=self.source, surfaces=[s.evidence() for s in self.surfaces],
                    components=list(self.components), residual_pixels_uv=np.column_stack((u, v)).tolist(),
                    for_execution=False, geometric_inventory_is_not_semantic_selection=True)


def sensor_view_identity(view):
    """Request-side binding only; depth/pose never go to the semantic model."""
    return dict(frame_id=view.get("canonical_frame_id", view["frame_id"]),
                camera_id=view["camera_id"], calibration_version=view["calibration_version"],
                rgb_sha256=hashlib.sha256(view["rgb"].tobytes()).hexdigest(),
                depth_sha256=hashlib.sha256(view["depth_m"].tobytes()).hexdigest(),
                rgb_shape=list(view["rgb"].shape), depth_shape=list(view["depth_m"].shape),
                intrinsics_K=np.asarray(view["intrinsics_K"]).tolist(),
                T_base_camera=np.asarray(view["T_base_camera"]).tolist(),
                episode_id=view.get("episode_id"), frame_seq=view["frame_seq"],
                capture_sim_time_s=view["capture_sim_time_s"], capture_monotonic_ns=view["capture_monotonic_ns"],
                coordinate_frame=view["frame"])


def inventory_surfaces(view, roi_xyxy, *, config=None, seed=0):
    """Peel plane hypotheses, retain every support, canonically order by pixels.

    RANSAC scores concern sensor fitting only. Peeling does not preselect a motor
    action or a winning target. No new geometry thresholds are introduced.
    """
    config = config or GeometryConfig()
    require(type(seed) is int and seed >= 0, "nonnegative inventory seed")
    frame = view.get("canonical_frame_id", view["frame_id"])
    cloud = project_depth(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
                          source_frame_id=frame, calibration_version=view["calibration_version"],
                          config=config, roi_xyxy=roi_xyxy)
    components = _components(cloud, cloud.valid_mask, config.connectivity_distance_m)
    # Canonical raster ordering rather than the old dominant-component order.
    components.sort(key=lambda ids: int(ids.min()))
    identity = sensor_view_identity(view)
    source = dict(**identity, sensor_view_sha256=content_hash(identity),
                  geometry_config_sha256=content_hash(config.to_dict()), search_roi_xyxy=list(roi_xyxy),
                  inventory_seed=seed, provenance="sensor-derived", semantic_identity_verified=False)
    inventory_id = content_hash(source)
    records, supports = [], []
    residual = cloud.valid_mask.copy()
    rng = np.random.default_rng(seed)
    for index, ids in enumerate(components):
        component_id = f"{frame}/{inventory_id}/component-{index}"
        remaining = ids.copy()
        fitted = []
        while len(remaining) >= config.min_component_points:
            raw = cloud.points_base_m[remaining]
            points = voxel_downsample(raw, voxel_m=config.target_voxel_m, max_points=config.max_target_points)
            if len(points) < config.min_component_points:
                break
            best, score = None, (-1, -np.inf)
            for _ in range(config.ransac_iterations):
                a, b, c = points[rng.choice(len(points), 3, replace=False)]
                normal = np.cross(b-a, c-a)
                length = np.linalg.norm(normal)
                if length < 1e-12:
                    continue
                normal /= length
                errors = np.abs((points-a) @ normal)
                inliers = errors <= config.plane_inlier_distance_m
                rank = (int(inliers.sum()), -float(errors[inliers].sum()))
                if rank > score:
                    best, score = inliers, rank
            if best is None or best.sum() < config.min_component_points:
                break
            fit = _svd_plane(points[best], np.asarray(view["T_base_camera"])[:3, 3], config)
            if fit is None:
                break
            center, normal, rms, _, spread = fit
            members = np.abs((raw-center) @ normal) <= config.plane_inlier_distance_m
            if members.sum() < config.min_component_points:
                break
            fitted.append((center, normal, rms, spread))
            remaining = remaining[~members]
        # Evaluate each fitted plane on the ORIGINAL component, preserving
        # overlap/intersection ambiguity instead of claiming peeled exclusivity.
        for center, normal, rms, spread in fitted:
            members = ids[np.abs((cloud.points_base_m[ids]-center) @ normal) <= config.plane_inlier_distance_m]
            mask = np.zeros_like(cloud.valid_mask)
            uv = cloud.pixels_uv[members]
            mask[uv[:, 1], uv[:, 0]] = True
            # Disconnected coplanar patches are separate physical supports.
            for part in _components(cloud, mask, config.connectivity_distance_m):
                if len(part) < config.min_component_points:
                    continue
                support = np.zeros_like(mask)
                pixels = cloud.pixels_uv[part]
                support[pixels[:, 1], pixels[:, 0]] = True
                support.setflags(write=False)
                # A disconnected support cannot inherit another patch's gates.
                local_points = cloud.points_base_m[part]
                local_fit = _svd_plane(local_points, np.asarray(view["T_base_camera"])[:3, 3], config)
                local_valid = local_fit is not None
                if local_fit is not None:
                    local_center, local_normal, local_rms, _, local_spread = local_fit
                else:
                    local_center, local_normal = local_points.mean(axis=0), normal
                    local_rms = float(np.sqrt(np.mean(((local_points-local_center) @ normal)**2)))
                    local_spread = np.linalg.svd(local_points-local_center, compute_uv=False)/np.sqrt(len(part))
                supports.append((component_id, support, local_center, local_normal, local_rms, local_spread,
                                 local_valid and local_rms <= config.max_plane_rms_m))
                residual &= ~support
        records.append(dict(component_id=component_id, pixel_count=len(ids),
                            extracted_plane_count=len(fitted), peeled_remainder_count=len(remaining),
                            insufficient_support=len(ids) < config.min_component_points))
    supports.sort(key=lambda row: (int(np.flatnonzero(row[1])[0]), hashlib.sha256(row[1].tobytes()).hexdigest()))
    surfaces = tuple(ObservedSurface(f"{frame}/{inventory_id}/surface-{i}", comp, mask, tuple(center), tuple(normal),
                                    float(rms), tuple(spread[:2]), valid)
                     for i, (comp, mask, center, normal, rms, spread, valid) in enumerate(supports))
    residual.setflags(write=False)
    return SurfaceInventory(source, surfaces, residual, tuple(records))


def associate_point(inventory, semantic):
    """No snapping, nearest surface, largest plane, box-center or label fallback."""
    source = inventory.source
    for name in ("frame_id", "camera_id", "rgb_sha256", "calibration_version", "sensor_view_sha256"):
        require(semantic.get(name) == source[name], f"semantic source {name} mismatch", "SOURCE_MISMATCH")
    require(semantic.get("evaluation_labels_used") is False, "evaluation labels cannot select a surface", "INFORMATION_BOUNDARY")
    require(isinstance(semantic.get("query"), str) and bool(semantic["query"]), "explicit semantic query")
    require(isinstance(semantic.get("response_sha256"), str) and len(semantic["response_sha256"]) == 64,
            "raw semantic response artifact required")
    points = semantic.get("points_xy")
    result = dict(status="UNKNOWN", surface_id=None, matching_surface_ids=[], reason="NO_SINGLE_POINT",
                  source=source, query=semantic["query"], response_sha256=semantic["response_sha256"],
                  semantic_identity_verified=False, calibrated_confidence=None, for_execution=False)
    if (semantic.get("generation_complete") is not True or semantic.get("parsed_status") != "single_point"
            or not isinstance(points, list) or len(points) != 1):
        return result
    point = np.asarray(points[0], dtype=float)
    require(point.shape == (2,) and np.isfinite(point).all(), "finite point coordinates")
    h, w = inventory.residual_mask.shape
    if not (0 <= point[0] < w and 0 <= point[1] < h):
        return {**result, "reason": "POINT_OUT_OF_FRAME"}
    x, y = np.floor(point).astype(int)
    matches = [s.surface_id for s in inventory.surfaces if s.support_mask[y, x]]
    result.update(matching_surface_ids=matches, sampled_pixel_xy=[int(x), int(y)])
    if len(matches) != 1:
        return {**result, "status": "AMBIGUOUS" if matches else "UNKNOWN",
                "reason": "MULTIPLE_SURFACE_SUPPORTS" if matches else "POINT_HAS_NO_SURFACE_SUPPORT"}
    surface = next(s for s in inventory.surfaces if s.surface_id == matches[0])
    if not surface.plane_valid:
        return {**result, "reason": "SURFACE_PLANE_INVALID"}
    return {**result, "status": "BOUND_HYPOTHESIS", "surface_id": matches[0], "reason": None}


def tracker_seed_rectangle(surface, point_xy, *, tracker_config):
    """Largest centered observed rectangle including original context margin.

    This constructs a geometry-supported feature, not a model bounding box.
    The unchanged tracker still checks its template context and depth spread.
    """
    mask = surface.support_mask
    h, w = mask.shape
    point = np.asarray(point_xy, dtype=float)
    require(point.shape == (2,) and np.isfinite(point).all(), "finite seed point")
    if not (0 <= point[0] < w and 0 <= point[1] < h):
        return None
    x, y = np.floor(point).astype(int)
    if not mask[y, x]:
        return None
    center = np.array([x+.5, y+.5])
    integral = np.pad(np.cumsum(np.cumsum(~mask, axis=0), axis=1), ((1, 0), (1, 0)))
    best, area = None, 0
    for width in range(4, min(w, int(2*min(center[0], w-center[0])))+1):
        for height in range(4, min(h, int(2*min(center[1], h-center[1])))+1):
            size = np.array([width, height])
            lo = np.floor(center-size*tracker_config.template_context_scale/2).astype(int)
            hi = np.ceil(center+size*tracker_config.template_context_scale/2).astype(int)
            if (lo < 0).any() or hi[0] > w or hi[1] > h:
                continue
            bad = integral[hi[1], hi[0]]-integral[lo[1], hi[0]]-integral[hi[1], lo[0]]+integral[lo[1], lo[0]]
            if bad == 0 and width*height > area:
                best, area = np.r_[center-size/2, center+size/2].tolist(), width*height
    return best
