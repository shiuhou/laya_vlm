"""Sensor-only diagnostic views; pictures never certify contact or safety.

Rendering preserves the full candidate list in metadata, including candidates
that cannot be drawn. A serialized plane permits a residual-compatibility view,
not reconstruction of the original connectivity/RANSAC membership mask.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

import numpy as np

from ..contracts import ProtocolError, canonical_json, content_hash
from .rgbd_geometry import GeometryConfig, _camera, _roi, project_depth


UNKNOWN_COLOR = (255, 190, 0)
PLANE_COMPATIBLE_COLOR = (70, 150, 255)
INVALID_DEPTH_COLOR = (180, 0, 180)


def project_candidate_dots(candidates, K, T_base_camera, *, image_shape, roi_xyxy):
    """Return one record per input candidate in original order, without pruning."""
    k, transform = _camera(K, T_base_camera)
    h, w = image_shape
    x0, y0, x1, y1 = _roi(roi_xyxy, w, h)
    seen = set()
    records = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ProtocolError("INVALID_SCHEMA", "serialized candidate must be a mapping")
        point_id = candidate.get("point_id")
        if not isinstance(point_id, str) or not point_id or point_id in seen:
            raise ProtocolError("INVALID_SCHEMA", "candidate IDs must be present and unique")
        seen.add(point_id)
        point = np.asarray(candidate.get("position_base_m"), dtype=float)
        if point.shape != (3,) or not np.isfinite(point).all():
            raise ProtocolError("INVALID_SCHEMA", "candidate position must be finite base XYZ")
        camera = transform[:3, :3].T @ (point-transform[:3, 3])
        uv = None
        reason = None
        if camera[2] <= 0:
            reason = "BEHIND_CAMERA"
        else:
            projected = k @ camera
            uv = projected[:2]/projected[2]
            if not (0 <= uv[0] < w and 0 <= uv[1] < h):
                reason = "OUTSIDE_IMAGE"
            elif not (x0 <= uv[0] < x1 and y0 <= uv[1] < y1):
                reason = "OUTSIDE_ROI"
        records.append({
            "point_id": point_id,
            "position_base_m": point.tolist(),
            "pixel_uv": None if uv is None else uv.tolist(),
            "crop_pixel_uv": None if uv is None else (uv-[x0, y0]).tolist(),
            "drawn": reason is None,
            "not_drawn_reason": reason,
            "display_status": "UNKNOWN",
            "reported_usable_status": candidate.get("usable_status", "UNKNOWN"),
            "reported_geometry_valid": candidate.get("geometry_valid"),
        })
    return records


def _disk(image, center, radius, color):
    x, y = (int(round(value)) for value in center)
    h, w = image.shape[:2]
    x0, x1 = max(0, x-radius), min(w, x+radius+1)
    y0, y1 = max(0, y-radius), min(h, y+radius+1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.ogrid[y0:y1, x0:x1]
    selection = (xx-x)**2+(yy-y)**2 <= radius**2
    image[y0:y1, x0:x1][selection] = color


def build_patch_diagnostics(rgb, depth_m, K, T_base_camera, *, roi_xyxy, patch,
                            geometry_config=None, source_frame_id=None):
    """Build NumPy image panels and complete JSON-safe projection metadata.

    Depth uses the config's fixed metric range, never per-image percentile
    normalization. Cyan means distance-compatible with an observed fitted plane;
    amber always means execution usability UNKNOWN.
    """
    config = geometry_config or GeometryConfig()
    image = np.asarray(rgb)
    depth = np.asarray(depth_m)
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or depth.shape != image.shape[:2]:
        raise ProtocolError("INVALID_SCHEMA", "RGB/depth dimensions or RGB dtype invalid")
    if not isinstance(patch, Mapping):
        raise ProtocolError("INVALID_SCHEMA", "patch must be serialized geometry")
    config_hash = content_hash(config.to_dict())
    recorded_config_hash = patch.get("metrics", {}).get("config_sha256")
    if recorded_config_hash is not None and recorded_config_hash != config_hash:
        raise ProtocolError("CONFIG_MISMATCH", "overlay geometry config differs from estimated patch")
    if source_frame_id is not None and source_frame_id != patch.get("source_frame_id"):
        raise ProtocolError("FRAME_MISMATCH", "overlay frame differs from estimated plane")
    h, w = depth.shape
    roi = _roi(roi_xyxy, w, h)
    if "source_roi_xyxy" in patch and tuple(patch["source_roi_xyxy"]) != roi:
        raise ProtocolError("ROI_MISMATCH", "overlay must use estimated ROI")
    x0, y0, x1, y1 = roi
    if x0 == x1 or y0 == y1:
        raise ProtocolError("INVALID_SCHEMA", "ROI contains no pixel centres")
    cloud = project_depth(depth, K, T_base_camera, roi_xyxy=roi,
                          source_frame_id=patch.get("source_frame_id", ""),
                          calibration_version=patch.get("calibration_version", ""), config=config)
    crop = image[y0:y1, x0:x1].copy()
    crop_depth = depth[y0:y1, x0:x1]
    valid = cloud.valid_mask[y0:y1, x0:x1]
    normalized = np.zeros(crop_depth.shape, dtype=float)
    normalized[valid] = (crop_depth[valid]-config.min_depth_m)/(config.max_depth_m-config.min_depth_m)
    near_intensity = np.round(255*(1-normalized)).astype(np.uint8)
    depth_view = np.repeat(near_intensity[:, :, None], 3, axis=2)
    depth_view[~valid] = INVALID_DEPTH_COLOR
    support_view = crop.copy()
    support_count = None
    support_status = "NOT_AVAILABLE"
    normal, centroid = patch.get("normal_base"), patch.get("centroid_base_m")
    if patch.get("geometry_status") == "VALID" and normal is not None and centroid is not None:
        normal, centroid = np.asarray(normal, dtype=float), np.asarray(centroid, dtype=float)
        if normal.shape != (3,) or centroid.shape != (3,) or not np.isfinite(normal).all() or not np.isfinite(centroid).all() or not np.isclose(np.linalg.norm(normal), 1, atol=1e-6):
            raise ProtocolError("INVALID_SCHEMA", "invalid serialized fitted plane")
        residual = np.abs((cloud.points_base_m-centroid) @ normal)
        compatible = residual <= config.plane_inlier_distance_m
        pixels = cloud.pixels_uv[compatible]-[x0, y0]
        if len(pixels):
            original = support_view[pixels[:, 1], pixels[:, 0]].astype(float)
            support_view[pixels[:, 1], pixels[:, 0]] = np.round(.55*original+.45*np.asarray(PLANE_COMPATIBLE_COLOR)).astype(np.uint8)
        support_count = int(compatible.sum())
        support_status = "RECONSTRUCTED_PLANE_DISTANCE_COMPATIBILITY"
    dots = project_candidate_dots(patch.get("candidates", ()), K, T_base_camera,
                                 image_shape=depth.shape, roi_xyxy=roi)
    candidate_view = crop.copy()
    for record in dots:
        if record["drawn"]:
            _disk(candidate_view, record["crop_pixel_uv"], 3, (0, 0, 0))
            _disk(candidate_view, record["crop_pixel_uv"], 2, UNKNOWN_COLOR)
    metadata = {
        "source_frame_id": patch.get("source_frame_id"),
        "calibration_version": patch.get("calibration_version"),
        "roi_xyxy": list(roi),
        "image_shape_hw": [h, w],
        "geometry_status": patch.get("geometry_status"),
        "geometry_reason_codes": list(patch.get("reason_codes", ())),
        "geometry_config_hash": config_hash,
        "semantic_identity_verified": False,
        "visualization_does_not_certify_execution": True,
        "depth_units": "m", "depth_display_range_m": [config.min_depth_m, config.max_depth_m],
        "invalid_depth_color_rgb": list(INVALID_DEPTH_COLOR),
        "plane_support_status": support_status,
        "plane_support_is_original_fit_membership": False,
        "plane_support_excludes_robot_or_other_components": False,
        "plane_compatible_pixel_count": support_count,
        "plane_distance_threshold_m": config.plane_inlier_distance_m,
        "candidate_count": len(dots), "drawn_candidate_count": sum(record["drawn"] for record in dots),
        "candidate_display_status": "UNKNOWN", "candidate_color_rgb": list(UNKNOWN_COLOR),
        "candidate_projections": dots,
        "provenance": "sensor-derived-diagnostic",
    }
    canonical_json(metadata)
    return {"images": {"rgb_crop": crop, "metric_depth": depth_view,
                       "plane_support": support_view, "candidates": candidate_view},
            "metadata": metadata}


def write_patch_diagnostics(directory, **kwargs):
    """Write non-overwriting PNG panels plus metadata. Pillow loads only here."""
    from PIL import Image, ImageDraw

    result = build_patch_diagnostics(**kwargs)
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    metadata = result["metadata"]
    lo, hi = metadata["depth_display_range_m"]
    labels = {
        "rgb_crop": "Observed ROI; identity unverified",
        "metric_depth": f"Depth {lo:g}..{hi:g} m; magenta invalid",
        "plane_support": "Plane-compatible depth; not fit membership",
        "candidates": "All point candidates; usability UNKNOWN",
    }
    paths = {}
    for name, array in result["images"].items():
        # Labels remain readable even when the observed ROI is a narrow sliver.
        panel = Image.new("RGB", (max(320, array.shape[1]), array.shape[0]+24), (30, 30, 30))
        panel.paste(Image.fromarray(array), (0, 24))
        ImageDraw.Draw(panel).text((4, 5), labels[name], fill=(255, 255, 255))
        path = root/f"{name}.png"
        panel.save(path)
        paths[name] = path.name
    metadata = dict(metadata, image_paths=paths, image_content_origin_px=[0, 24])
    (root/"metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False)+"\n")
    return metadata
