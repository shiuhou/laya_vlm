"""LocateAnything RGB-D adapter.

The model callback is intentionally injected: this module never downloads weights and
does not assume a particular local serving stack. A callback receives RGB plus a query
and returns boxes/points in pixel coordinates. Depth and calibration turn those 2-D
measurements into timestamped semantic events for BeliefStore.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from .runtime_core import ObservationEvent


def robust_depth(depth: np.ndarray, box_xyxy: tuple[int, int, int, int], *,
                 min_depth: float = 0.01, max_depth: float = 5.0) -> tuple[float | None, float]:
    x1, y1, x2, y2 = [int(v) for v in box_xyxy]
    arr = np.asarray(depth)
    h, w = arr.shape[:2]
    x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
    y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return None, 0.0
    # Interior pixels reduce edge mixing and depth discontinuity outliers.
    pad_x, pad_y = max(1, (x2 - x1) // 5), max(1, (y2 - y1) // 5)
    crop = arr[y1 + pad_y:min(y2 - pad_y, y2), x1 + pad_x:min(x2 - pad_x, x2)]
    valid = crop[np.isfinite(crop) & (crop >= min_depth) & (crop <= max_depth)]
    if valid.size == 0:
        return None, 0.0
    return float(np.median(valid)), float(valid.size / max(crop.size, 1))


def depth_statistics(depth: np.ndarray, box_xyxy: tuple[int, int, int, int], *,
                     min_depth: float = 0.01, max_depth: float = 5.0) -> dict[str, float | None]:
    x1, y1, x2, y2 = [int(v) for v in box_xyxy]
    arr = np.asarray(depth)
    h, w = arr.shape[:2]
    x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
    y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return {"median_m": None, "mad_m": None, "std_m": None, "valid_ratio": 0.0}
    pad_x, pad_y = max(1, (x2 - x1) // 5), max(1, (y2 - y1) // 5)
    crop = arr[y1 + pad_y:min(y2 - pad_y, y2), x1 + pad_x:min(x2 - pad_x, x2)]
    valid = crop[np.isfinite(crop) & (crop >= min_depth) & (crop <= max_depth)]
    if valid.size == 0:
        return {"median_m": None, "mad_m": None, "std_m": None, "valid_ratio": 0.0}
    median = float(np.median(valid))
    mad = float(np.median(np.abs(valid - median)))
    return {"median_m": median, "mad_m": mad, "std_m": float(np.std(valid)),
            "valid_ratio": float(valid.size / max(crop.size, 1))}


def pixel_to_camera(u: float, v: float, z: float, intrinsics: Mapping[str, float]) -> np.ndarray:
    if hasattr(intrinsics, "shape"):
        fx, fy = float(intrinsics[0, 0]), float(intrinsics[1, 1])
        cx, cy = float(intrinsics[0, 2]), float(intrinsics[1, 2])
    else:
        fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
        cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
    return np.asarray([(u - cx) * z / fx, (v - cy) * z / fy, z], dtype=float)


def camera_to_world(point_camera: np.ndarray, camera_to_world_matrix: np.ndarray) -> np.ndarray:
    point = np.asarray(point_camera, dtype=float).reshape(3)
    transform = np.asarray(camera_to_world_matrix, dtype=float)
    if transform.shape != (4, 4):
        raise ValueError("camera_to_world_matrix must be 4x4")
    return (transform @ np.r_[point, 1.0])[:3]


def position_covariance_from_depth(u: float, v: float, z: float,
                                   box_xyxy: tuple[int, int, int, int],
                                   stats: Mapping[str, float | None],
                                   intrinsics: Mapping[str, float]) -> np.ndarray:
    """Heuristic first-order RGB-D position covariance estimate.

    This is a measurement-quality estimate, not a calibrated sensor model. It
    combines the observed depth spread with a 5% box-size localization error and
    records its heuristic provenance in the event payload.
    """
    if hasattr(intrinsics, "shape"):
        fx, fy = float(intrinsics[0, 0]), float(intrinsics[1, 1])
        cx, cy = float(intrinsics[0, 2]), float(intrinsics[1, 2])
    else:
        fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
        cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
    sigma_z = max(float(stats.get("std_m") or 0.0), float(stats.get("mad_m") or 0.0) * 1.4826, 0.002)
    sigma_u = max(1.0, abs(float(box_xyxy[2]) - float(box_xyxy[0])) * 0.05)
    sigma_v = max(1.0, abs(float(box_xyxy[3]) - float(box_xyxy[1])) * 0.05)
    jacobian = np.array([[z / fx, 0.0, (u - cx) / fx],
                         [0.0, z / fy, (v - cy) / fy],
                         [0.0, 0.0, 1.0]])
    covariance = jacobian @ np.diag([sigma_u ** 2, sigma_v ** 2, sigma_z ** 2]) @ jacobian.T
    return (covariance + covariance.T) / 2.0


class LocateAnythingProvider:
    """Convert model localization results plus depth into ObservationEvents."""

    def __init__(self, infer: Callable[[np.ndarray, str], Mapping[str, Any]],
                 intrinsics: Mapping[str, float], *, source: str = "locateanything+depth"):
        self.infer = infer
        self.intrinsics = intrinsics.copy() if hasattr(intrinsics, "copy") else dict(intrinsics)
        self.source = source

    def observe(self, rgb: np.ndarray, depth: np.ndarray, query: str, *,
                episode_id: str, source_seq: int, capture_sim_time: float,
                track_id: str | None = None, camera_to_world_matrix: np.ndarray | None = None,
                inference_result: Mapping[str, Any] | None = None) -> ObservationEvent | None:
        result = dict(self.infer(rgb, query) if inference_result is None else inference_result)
        boxes = result.get("boxes_xyxy") or result.get("boxes") or []
        if not boxes:
            return None
        box = tuple(int(v) for v in boxes[0])
        x1, y1, x2, y2 = box
        stats = depth_statistics(depth, box)
        z = stats["median_m"]
        valid_ratio = float(stats["valid_ratio"] or 0.0)
        if z is None:
            return None
        u, v = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        point = pixel_to_camera(u, v, z, self.intrinsics)
        covariance_camera = position_covariance_from_depth(u, v, z, box, stats, self.intrinsics)
        confidence = float(result.get("score", result.get("confidence", 0.0)))
        payload = {
            "label": query,
            "probabilities": {query: max(0.0, min(1.0, confidence)), "unknown": max(0.0, 1.0 - confidence)},
            "position_camera_m": point.tolist(),
            "box_xyxy": list(box),
            "depth_valid_ratio": valid_ratio,
            "depth_mad_m": stats["mad_m"],
            "depth_std_m": stats["std_m"],
            "position_covariance_m2": covariance_camera.tolist(),
            "position_covariance_source": "heuristic_depth_projection_v1",
            "position_covariance_calibrated": False,
            "model_latency_ms": result.get("model_latency_ms"),
            "raw_response": result.get("raw_response"),
        }
        if camera_to_world_matrix is not None:
            payload["position_world_m"] = camera_to_world(point, camera_to_world_matrix).tolist()
            rotation = np.asarray(camera_to_world_matrix, dtype=float)[:3, :3]
            payload["position_covariance_m2"] = (rotation @ covariance_camera @ rotation.T).tolist()
        return ObservationEvent(
            source=self.source, episode_id=episode_id, source_seq=source_seq,
            capture_sim_time=capture_sim_time, received_wall_time=__import__("time").time(),
            frame_id="camera", track_id=track_id or query, value=payload,
            quality=min(confidence, valid_ratio), valid_until_sim=capture_sim_time + 0.75,
        )
