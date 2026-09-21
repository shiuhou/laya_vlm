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
    crop = np.asarray(depth)[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
    valid = crop[np.isfinite(crop) & (crop >= min_depth) & (crop <= max_depth)]
    if valid.size == 0:
        return None, 0.0
    return float(np.median(valid)), float(valid.size / max(crop.size, 1))


def pixel_to_camera(u: float, v: float, z: float, intrinsics: Mapping[str, float]) -> np.ndarray:
    fx, fy = float(intrinsics["fx"]), float(intrinsics["fy"])
    cx, cy = float(intrinsics["cx"]), float(intrinsics["cy"])
    return np.asarray([(u - cx) * z / fx, (v - cy) * z / fy, z], dtype=float)


class LocateAnythingProvider:
    """Convert model localization results plus depth into ObservationEvents."""

    def __init__(self, infer: Callable[[np.ndarray, str], Mapping[str, Any]],
                 intrinsics: Mapping[str, float], *, source: str = "locateanything+depth"):
        self.infer = infer
        self.intrinsics = dict(intrinsics)
        self.source = source

    def observe(self, rgb: np.ndarray, depth: np.ndarray, query: str, *,
                episode_id: str, source_seq: int, capture_sim_time: float,
                track_id: str | None = None) -> ObservationEvent | None:
        result = dict(self.infer(rgb, query))
        boxes = result.get("boxes_xyxy") or result.get("boxes") or []
        if not boxes:
            return None
        box = tuple(int(v) for v in boxes[0])
        x1, y1, x2, y2 = box
        z, valid_ratio = robust_depth(depth, box)
        if z is None:
            return None
        u, v = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        point = pixel_to_camera(u, v, z, self.intrinsics)
        confidence = float(result.get("score", result.get("confidence", 0.0)))
        payload = {
            "label": query,
            "probabilities": {query: max(0.0, min(1.0, confidence)), "unknown": max(0.0, 1.0 - confidence)},
            "position_camera_m": point.tolist(),
            "box_xyxy": list(box),
            "depth_valid_ratio": valid_ratio,
        }
        return ObservationEvent(
            source=self.source, episode_id=episode_id, source_seq=source_seq,
            capture_sim_time=capture_sim_time, received_wall_time=__import__("time").time(),
            frame_id="camera", track_id=track_id or query, value=payload,
            quality=min(confidence, valid_ratio), valid_until_sim=capture_sim_time + 0.75,
        )
