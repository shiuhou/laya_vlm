"""Timestamp-aware multi-rate fusion for RGB-D geometry and semantic evidence.

Measurements are ordered by capture time inside a fixed lag window. Delayed
measurements are inserted and the constant-velocity filter is replayed, so arrival
order does not become state order. Semantic labels use decayed evidence separately
because they are discrete probabilities rather than Gaussian geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PositionMeasurement:
    source: str
    source_seq: int
    capture_time: float
    position_m: np.ndarray
    covariance_m2: np.ndarray
    quality: float = 1.0

    def validate(self) -> None:
        p = np.asarray(self.position_m, dtype=float).reshape(-1)
        r = np.asarray(self.covariance_m2, dtype=float)
        if p.shape != (3,) or r.shape != (3, 3):
            raise ValueError("position and covariance must be 3D and 3x3")
        if not np.isfinite(p).all() or not np.isfinite(r).all():
            raise ValueError("measurement must be finite")
        if self.capture_time < 0 or not 0.0 <= self.quality <= 1.0:
            raise ValueError("invalid timestamp or quality")
        if np.any(np.linalg.eigvalsh((r + r.T) * 0.5) <= 0):
            raise ValueError("covariance must be positive definite")


@dataclass(frozen=True)
class FusedState:
    capture_time: float
    reference_time: float
    position_m: np.ndarray
    velocity_mps: np.ndarray
    covariance: np.ndarray
    age_s: float
    accepted_measurements: int
    source_seq: int | None


@dataclass
class FusionStats:
    accepted: int = 0
    rejected_gate: int = 0
    dropped_too_late: int = 0
    dropped_out_of_order: int = 0
    replay_count: int = 0
    max_observation_age_s: float = 0.0
    queue_replacements: int = 0


@dataclass
class _Event:
    measurement: PositionMeasurement
    order: int


class ConstantVelocityFusion3D:
    """Fixed-lag, out-of-sequence capable 3D position filter.

    The reference time is supplied by the caller, normally the latest robot
    control/proprioception timestamp. The filter never uses wall-clock arrival time
    as a substitute for capture time.
    """

    def __init__(self, *, lag_s: float = 1.0, process_noise_mps2: float = 1.0,
                 gate_sigma: float = 4.0, initial_position_var: float = 0.25,
                 initial_velocity_var: float = 1.0, max_events: int = 128):
        self.lag_s = float(lag_s)
        self.process_noise_mps2 = float(process_noise_mps2)
        self.gate_sq = float(gate_sigma) ** 2
        self.initial_position_var = float(initial_position_var)
        self.initial_velocity_var = float(initial_velocity_var)
        self.max_events = int(max_events)
        self.stats = FusionStats()
        self._events: list[_Event] = []
        self._counter = 0
        self._anchor_time: float | None = None
        self._anchor_x: np.ndarray | None = None
        self._anchor_p: np.ndarray | None = None
        self._state: FusedState | None = None

    @property
    def pending_count(self) -> int:
        return len(self._events)

    def ingest(self, measurement: PositionMeasurement, *, reference_time: float) -> bool:
        measurement.validate()
        now = float(reference_time)
        if measurement.capture_time > now + 1e-6:
            raise ValueError("capture time cannot be in the future of reference time")
        if self._anchor_time is None:
            self._anchor_time = measurement.capture_time
            self._anchor_x = np.r_[np.asarray(measurement.position_m, dtype=float), np.zeros(3)]
            self._anchor_p = np.diag([self.initial_position_var] * 3 + [self.initial_velocity_var] * 3)
        if measurement.capture_time < now - self.lag_s:
            self.stats.dropped_too_late += 1
            return False
        if any(
            measurement.source == event.measurement.source
            and measurement.source_seq == event.measurement.source_seq
            for event in self._events
        ):
            self.stats.dropped_out_of_order += 1
            return False
        self._counter += 1
        self._events.append(_Event(measurement, self._counter))
        self._events.sort(key=lambda e: (e.measurement.capture_time, e.order))
        cutoff = now - self.lag_s
        self._events = [e for e in self._events if e.measurement.capture_time >= cutoff]
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
        self._replay(now)
        self.stats.accepted += 1
        self.stats.max_observation_age_s = max(
            self.stats.max_observation_age_s, max(0.0, now - measurement.capture_time)
        )
        return True

    def estimate(self, reference_time: float) -> FusedState | None:
        if self._anchor_time is None:
            return None
        self._replay(float(reference_time))
        return self._state

    def _replay(self, now: float) -> None:
        assert self._anchor_time is not None and self._anchor_x is not None and self._anchor_p is not None
        x, p, t = self._anchor_x.copy(), self._anchor_p.copy(), self._anchor_time
        accepted = 0
        last_seq = None
        for event in self._events:
            m = event.measurement
            if m.capture_time < t - 1e-9:
                continue
            x, p = self._predict(x, p, m.capture_time - t)
            z = np.asarray(m.position_m, dtype=float)
            h = np.zeros((3, 6))
            h[:, :3] = np.eye(3)
            r = np.asarray(m.covariance_m2, dtype=float) / max(m.quality, 0.05)
            innovation = z - h @ x
            s = h @ p @ h.T + r
            d2 = float(innovation.T @ np.linalg.solve(s, innovation))
            if d2 > self.gate_sq and accepted:
                self.stats.rejected_gate += 1
                t = m.capture_time
                continue
            k = p @ h.T @ np.linalg.inv(s)
            x = x + k @ innovation
            p = (np.eye(6) - k @ h) @ p
            p = (p + p.T) * 0.5
            accepted += 1
            last_seq = m.source_seq
            t = m.capture_time
        x, p = self._predict(x, p, max(0.0, now - t))
        self._state = FusedState(t, now, x[:3].copy(), x[3:].copy(), p.copy(), max(0.0, now - t), accepted, last_seq)
        self.stats.replay_count += 1

    def _predict(self, x: np.ndarray, p: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
        if dt <= 0:
            return x, p
        f = np.eye(6)
        f[:3, 3:] = np.eye(3) * dt
        q = self.process_noise_mps2 ** 2
        qmat = np.zeros((6, 6))
        qmat[:3, :3] = np.eye(3) * dt ** 3 / 3.0 * q
        qmat[:3, 3:] = np.eye(3) * dt ** 2 / 2.0 * q
        qmat[3:, :3] = np.eye(3) * dt ** 2 / 2.0 * q
        qmat[3:, 3:] = np.eye(3) * dt * q
        return f @ x, f @ p @ f.T + qmat


@dataclass
class SemanticTrack:
    evidence: dict[str, float] = field(default_factory=dict)
    last_capture_time: float = 0.0
    source_seq: int = -1

    def distribution(self, now: float, half_life_s: float) -> dict[str, float]:
        decay = exp(-max(0.0, now - self.last_capture_time) / max(half_life_s, 1e-6))
        values = {k: max(1e-6, v * decay) for k, v in self.evidence.items()}
        values.setdefault("unknown", 1.0)
        total = sum(values.values())
        return {k: v / total for k, v in values.items()}


class SemanticEvidenceFusion:
    """Decayed probability/evidence fusion for labels and task states."""

    def __init__(self, *, half_life_s: float = 0.75):
        self.half_life_s = float(half_life_s)
        self.tracks: dict[str, SemanticTrack] = {}
        self.rejected_out_of_order = 0

    def ingest(self, track_id: str, probabilities: dict[str, float], *, capture_time: float,
               source_seq: int, quality: float = 1.0) -> bool:
        track = self.tracks.setdefault(track_id, SemanticTrack())
        if source_seq <= track.source_seq:
            self.rejected_out_of_order += 1
            return False
        clean = {str(k): max(0.0, float(v)) for k, v in probabilities.items()}
        total = sum(clean.values())
        if total <= 0:
            return False
        weight = max(0.05, min(1.0, float(quality)))
        for label, probability in clean.items():
            track.evidence[label] = track.evidence.get(label, 0.0) * 0.9 + weight * probability / total
        track.last_capture_time = float(capture_time)
        track.source_seq = int(source_seq)
        return True

    def distribution(self, track_id: str, *, reference_time: float) -> dict[str, float]:
        track = self.tracks.get(track_id)
        return {"unknown": 1.0} if track is None else track.distribution(reference_time, self.half_life_s)


class MultiRateFusion:
    """Convenience container joining geometry and semantic fusion with diagnostics."""

    def __init__(self, *, lag_s: float = 1.0):
        self.geometry: dict[str, ConstantVelocityFusion3D] = {}
        self.semantic = SemanticEvidenceFusion()
        self.lag_s = float(lag_s)

    def ingest_event(self, event: Any, *, reference_time: float) -> bool:
        value = dict(event.value)
        track = event.track_id or str(value.get("track_id") or "scene")
        accepted = False
        position = value.get("position_world_m")
        if position is not None:
            covariance = np.asarray(value.get("position_covariance_m2", np.eye(3) * 0.01), dtype=float)
            filter_ = self.geometry.setdefault(track, ConstantVelocityFusion3D(lag_s=self.lag_s))
            accepted = filter_.ingest(PositionMeasurement(event.source, event.source_seq, event.capture_sim_time, np.asarray(position), covariance, event.quality), reference_time=reference_time) or accepted
        probabilities = value.get("probabilities") or value.get("hypotheses")
        if probabilities:
            accepted = self.semantic.ingest(track, probabilities, capture_time=event.capture_sim_time, source_seq=event.source_seq, quality=event.quality) or accepted
        return accepted

    def snapshot(self, *, reference_time: float) -> dict[str, Any]:
        geometry = {}
        for track, filter_ in self.geometry.items():
            state = filter_.estimate(reference_time)
            if state is not None:
                geometry[track] = state
        semantic = {track: self.semantic.distribution(track, reference_time=reference_time) for track in self.semantic.tracks}
        return {"geometry": geometry, "semantic": semantic}


