"""Deterministic 2D+3D association for query-local visual tracks."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np


def box_iou(a: Iterable[float], b: Iterable[float]) -> float:
    ax1, ay1, ax2, ay2 = map(float, a)
    bx1, by1, bx2, by2 = map(float, b)
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return 0.0 if union <= 0 else inter / union


@dataclass
class Track:
    track_id: str
    query: str
    box_xyxy: tuple[float, float, float, float]
    position_world_m: np.ndarray | None
    capture_time: float
    hits: int = 1
    missed: int = 0


class QueryTrackManager:
    """Associate only within a semantic query using IoU and 3D distance gates."""

    def __init__(self, *, max_distance_m: float = 0.20, min_iou: float = 0.05, max_missed: int = 5):
        self.max_distance_m = float(max_distance_m)
        self.min_iou = float(min_iou)
        self.max_missed = int(max_missed)
        self._next_id = 1
        self._tracks: dict[str, Track] = {}

    def update(self, query: str, boxes_xyxy: list[Iterable[float]], positions_world_m: list[np.ndarray | None], capture_time: float) -> list[Track]:
        detections = []
        for box, position in zip(boxes_xyxy, positions_world_m):
            detections.append((tuple(map(float, box)), None if position is None else np.asarray(position, dtype=float).reshape(3)))
        candidates = [track for track in self._tracks.values() if track.query == query]
        used: set[str] = set()
        updated: list[Track] = []
        for box, position in detections:
            best = None
            best_score = -1.0
            for track in candidates:
                if track.track_id in used:
                    continue
                iou = box_iou(box, track.box_xyxy)
                distance = float(np.linalg.norm(position - track.position_world_m)) if position is not None and track.position_world_m is not None else None
                if iou < self.min_iou and (distance is None or distance > self.max_distance_m):
                    continue
                score = iou + (0.5 if distance is not None and distance <= self.max_distance_m else 0.0)
                if score > best_score:
                    best, best_score = track, score
            if best is None:
                best = Track(f"{query}:{self._next_id}", query, box, position, float(capture_time))
                self._next_id += 1
                self._tracks[best.track_id] = best
            else:
                best.box_xyxy = box
                best.position_world_m = position
                best.capture_time = float(capture_time)
                best.hits += 1
                best.missed = 0
            used.add(best.track_id)
            updated.append(best)
        for track in candidates:
            if track.track_id not in used:
                track.missed += 1
        self._tracks = {key: value for key, value in self._tracks.items() if value.missed <= self.max_missed}
        return updated

    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks.values())

