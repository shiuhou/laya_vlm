"""Capture-time fusion with posterior-preserving fixed lag and control validity.

Sequence identifies capture, not arrival order. Unseen earlier sequences are accepted
within the lag if capture and sequence order agree. Identity ledgers are episode-local.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from math import exp, isfinite, log
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TemporalConfig:
    version: str = "temporal-stage1-v1"
    lag_s: float = 1.0
    geometry_max_age_s: float = 0.75
    geometry_max_position_trace_m2: float = 0.03
    semantic_ttl_s: float = 0.75
    semantic_half_life_s: float = 0.75
    consistency_max_gap_s: float = 0.05
    process_noise_mps2: float = 1.0
    gate_sigma: float = 4.0
    initial_position_var: float = 0.25
    initial_velocity_var: float = 1.0
    fallback_measurement_variance_m2: float = 0.01
    max_events: int = 128

    def __post_init__(self):
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("temporal config version must be a nonempty string")
        for key, value in asdict(self).items():
            if key != "version" and (not isfinite(value) or value <= 0):
                raise ValueError(f"{key} must be positive and finite")
        if not isinstance(self.max_events, int):
            raise ValueError("max_events must be an integer")


@dataclass
class FusionStats:
    accepted: int = 0
    accepted_delayed: int = 0
    accepted_out_of_order: int = 0
    rejected_gate: int = 0
    dropped_too_late: int = 0
    dropped_duplicate: int = 0
    dropped_out_of_order: int = 0
    dropped_capacity: int = 0
    dropped_quality: int = 0
    replay_count: int = 0
    max_observation_age_s: float = 0.0
    queue_replacements: int = 0


class EventAdmission:
    """Shared capture/sequence contract; retained identity history is episode-local."""

    def __init__(self, lag_s=1.0):
        if not isfinite(lag_s) or lag_s <= 0:
            raise ValueError("lag must be positive and finite")
        self.lag_s = lag_s
        self.stats = FusionStats()
        self.seen: dict[str, dict[int, float]] = {}
        self.last_reason = "empty"
        self.reference_time = 0.0

    def check(self, source, seq, captured, now):
        if not source or not isinstance(seq, int) or seq < 0:
            raise ValueError("invalid source/sequence")
        if not isfinite(captured) or not isfinite(now) or captured < 0 or now < self.reference_time:
            raise ValueError("invalid or regressing reference time")
        if captured > now:
            raise ValueError("capture time cannot be in the future of reference time")
        seen = self.seen.get(source, {})
        if seq in seen:
            return "duplicate"
        if captured < now - self.lag_s:
            return "too_late"
        if any((s < seq and t > captured) or (s > seq and t < captured) for s, t in seen.items()):
            return "sequence_regression"
        return None

    def reject(self, reason):
        self.last_reason = reason
        counter = {"duplicate": "dropped_duplicate", "too_late": "dropped_too_late",
                   "sequence_regression": "dropped_out_of_order", "capacity": "dropped_capacity",
                   "zero_quality": "dropped_quality"}.get(reason)
        if counter:
            setattr(self.stats, counter, getattr(self.stats, counter) + 1)
        return False

    def admit(self, source, seq, captured, now):
        reason = self.check(source, seq, captured, now)
        if reason:
            return self.reject(reason)
        seen = self.seen.setdefault(source, {})
        out_of_order = bool(seen) and captured < max(seen.values())
        self.last_reason = "accepted_out_of_order" if out_of_order else "accepted_delayed" if captured < now else "accepted"
        self.stats.accepted += 1
        self.stats.accepted_delayed += int(captured < now)
        self.stats.accepted_out_of_order += int(out_of_order)
        self.stats.max_observation_age_s = max(self.stats.max_observation_age_s, now - captured)
        seen[seq] = captured
        self.reference_time = now
        return True


@dataclass(frozen=True)
class PositionMeasurement:
    source: str
    source_seq: int
    capture_time: float
    position_m: np.ndarray
    covariance_m2: np.ndarray
    quality: float = 1.0

    def validate(self):
        p, r = np.asarray(self.position_m), np.asarray(self.covariance_m2)
        if p.shape != (3,) or r.shape != (3, 3):
            raise ValueError("position and covariance must be 3D and 3x3")
        if not np.isfinite(p).all() or not np.isfinite(r).all():
            raise ValueError("measurement must be finite")
        if not isfinite(self.capture_time) or self.capture_time < 0 or not 0 <= self.quality <= 1:
            raise ValueError("invalid timestamp or quality")
        if not np.allclose(r, r.T, rtol=0, atol=1e-12) or np.any(np.linalg.eigvalsh(r) <= 0):
            raise ValueError("covariance must be symmetric positive definite")


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


class ConstantVelocityFusion3D:
    """Replay retained observations from a posterior advanced to the lag boundary.

    Innovation gates are recomputed in capture order. Admission and gate outcome
    are separate: retained observations can change gate outcome after an earlier
    measurement arrives. Reads never increment event rejection counters.
    """

    def __init__(self, *, lag_s=1.0, process_noise_mps2=1.0, gate_sigma=4.0,
                 initial_position_var=0.25, initial_velocity_var=1.0, max_events=128):
        self.config = TemporalConfig(lag_s=lag_s, process_noise_mps2=process_noise_mps2,
                                     gate_sigma=gate_sigma, initial_position_var=initial_position_var,
                                     initial_velocity_var=initial_velocity_var, max_events=max_events)
        self.lag_s = lag_s
        self.admission = EventAdmission(lag_s)
        self.stats = self.admission.stats
        self.last_reason = "empty"
        self._events: list[PositionMeasurement] = []
        self._anchor = None
        self._anchor_ids: set[tuple[str, int]] = set()
        self.used_ids: set[tuple[str, int]] = set()
        self._ever_gated: set[tuple[str, int]] = set()
        self._state = None
        self._reference_time = 0.0

    @property
    def pending_count(self):
        return len(self._events)

    @property
    def anchor_time(self):
        return None if self._anchor is None else self._anchor[2]

    def _initial(self):
        if self._anchor is not None:
            x, p, t, capture, seq, count = self._anchor
            return x.copy(), p.copy(), t, capture, seq, count
        first = self._events[0]
        return (np.r_[first.position_m, np.zeros(3)],
                np.diag([self.config.initial_position_var] * 3 + [self.config.initial_velocity_var] * 3),
                first.capture_time, first.capture_time, None, 0)

    def _filter(self, events, initial):
        x, p, t, capture, seq, count = initial
        used, gated = set(), set()
        for m in events:
            x, p = self._predict(x, p, m.capture_time - t)
            t = m.capture_time
            r = m.covariance_m2 / max(m.quality, 0.05)
            innovation = m.position_m - x[:3]
            s = p[:3, :3] + r
            d2 = float(innovation @ np.linalg.solve(s, innovation))
            identity = (m.source, m.source_seq)
            if m.quality == 0 or (count and d2 > self.config.gate_sigma ** 2):
                gated.add(identity)
                continue
            k = np.linalg.solve(s, p[:3, :]).T
            x = x + k @ innovation
            kh = np.zeros((6, 6))
            kh[:, :3] = k
            residual = np.eye(6) - kh
            p = residual @ p @ residual.T + k @ r @ k.T
            p = (p + p.T) / 2
            capture, seq, count = m.capture_time, m.source_seq, count + 1
            used.add(identity)
        return (x, p, t, capture, seq, count), used, gated

    def _advance(self, now):
        old = [m for m in self._events if m.capture_time < now - self.lag_s]
        if not old:
            return False
        posterior, used, _ = self._filter(old, self._initial())
        x, p, t, capture, seq, count = posterior
        boundary = now - self.lag_s
        x, p = self._predict(x, p, boundary - t)
        self._anchor = (x, p, boundary, capture, seq, count)
        self._anchor_ids.update(used)
        self._events = [m for m in self._events if m.capture_time >= boundary]
        return True

    def ingest(self, measurement, *, reference_time):
        measurement.validate()
        now = float(reference_time)
        if now < self._reference_time:
            raise ValueError("reference time cannot regress")
        m = measurement
        if m.quality == 0:
            self.last_reason = "zero_quality"
            return self.admission.reject("zero_quality")
        reason = self.admission.check(m.source, m.source_seq, m.capture_time, now)
        if reason:
            self.last_reason = reason
            return self.admission.reject(reason)
        self._advance(now)
        if len(self._events) >= self.config.max_events:
            self.last_reason = "capacity"
            return self.admission.reject("capacity")
        self.admission.admit(m.source, m.source_seq, m.capture_time, now)
        self._events.append(PositionMeasurement(m.source, m.source_seq, m.capture_time,
                                               np.array(m.position_m, copy=True), np.array(m.covariance_m2, copy=True), m.quality))
        self._events.sort(key=lambda e: (e.capture_time, e.source, e.source_seq))
        gated = self._replay(now)
        self.stats.replay_count += 1
        self._ever_gated.update(gated)
        self.stats.rejected_gate = len(self._ever_gated)
        self.last_reason = "innovation_gate" if (m.source, m.source_seq) in gated else self.admission.last_reason
        return self.last_reason != "innovation_gate"

    def estimate(self, reference_time):
        now = float(reference_time)
        if not isfinite(now) or now < self._reference_time:
            raise ValueError("invalid or regressing reference time")
        if not self._events and self._anchor is None:
            return None
        if self._advance(now):
            self.stats.replay_count += 1
        self._replay(now)
        return self._state

    def _replay(self, now):
        posterior, used, gated = self._filter(self._events, self._initial())
        x, p, t, captured, seq, count = posterior
        x, p = self._predict(x, p, now - t)
        self.used_ids = self._anchor_ids | used
        self._state = FusedState(captured, now, x[:3].copy(), x[3:].copy(), p.copy(), now - captured, count, seq)
        self._reference_time = now
        return gated

    def _predict(self, x, p, dt):
        if dt < -1e-12:
            raise ValueError("cannot predict backward from committed anchor")
        if dt <= 0:
            return x, p
        f = np.eye(6)
        f[:3, 3:] = np.eye(3) * dt
        q = np.zeros((6, 6))
        q[:3, :3] = np.eye(3) * dt ** 3 / 3
        q[:3, 3:] = q[3:, :3] = np.eye(3) * dt ** 2 / 2
        q[3:, 3:] = np.eye(3) * dt
        return f @ x, f @ p @ f.T + q * self.config.process_noise_mps2 ** 2


@dataclass
class SemanticTrack:
    evidence: dict[str, float] = field(default_factory=dict)
    last_capture_time: float = 0.0
    source_seq: int = -1
    valid_until_sim: float = 0.0
    used_ids: set[tuple[str, int]] = field(default_factory=set)
    latest_key: tuple[float, str, int] = (-1.0, "", -1)

    def distribution(self, now, half_life_s):
        decay = exp(-log(2) * max(0.0, now - self.last_capture_time) / half_life_s)
        values = {k: v * decay for k, v in self.evidence.items()}
        values["unknown"] = values.get("unknown", 0.0) + 0.1
        total = sum(values.values())
        return {k: v / total for k, v in values.items()}


class SemanticEvidenceFusion:
    """Add capture-decayed evidence; delayed contributions commute with arrival order."""

    def __init__(self, *, half_life_s=0.75, lag_s=1.0, ttl_s=0.75):
        if any(not isfinite(v) or v <= 0 for v in (half_life_s, lag_s, ttl_s)):
            raise ValueError("semantic time configuration must be positive and finite")
        self.half_life_s, self.ttl_s = half_life_s, ttl_s
        self.tracks: dict[str, SemanticTrack] = {}
        self._admission: dict[str, EventAdmission] = {}
        self.lag_s = lag_s
        self.rejected_out_of_order = 0
        self.last_reason = "empty"

    def ingest(self, track_id, probabilities, *, capture_time, source_seq, quality=1.0,
               source="semantic", reference_time=None, valid_until_sim=None):
        clean = {str(k): float(v) for k, v in probabilities.items()}
        if any(not isfinite(v) or v < 0 for v in clean.values()) or sum(clean.values()) <= 0:
            raise ValueError("invalid semantic probabilities")
        if not 0 <= quality <= 1:
            raise ValueError("invalid semantic quality")
        if valid_until_sim is not None and (not isfinite(valid_until_sim) or valid_until_sim < capture_time):
            raise ValueError("invalid semantic TTL")
        if quality == 0:
            self.last_reason = "zero_quality"
            return False
        now = capture_time if reference_time is None else reference_time
        admission = self._admission.setdefault(track_id, EventAdmission(self.lag_s))
        if not admission.admit(source, source_seq, capture_time, now):
            self.last_reason = admission.last_reason
            self.rejected_out_of_order += int(self.last_reason in {"duplicate", "sequence_regression"})
            return False
        track = self.tracks.setdefault(track_id, SemanticTrack())
        new_time = max(track.last_capture_time, capture_time)
        decay = exp(-log(2) * (new_time - track.last_capture_time) / self.half_life_s)
        track.evidence = {k: v * decay for k, v in track.evidence.items()}
        weight = quality * exp(-log(2) * (new_time - capture_time) / self.half_life_s)
        total = sum(clean.values())
        for label, probability in clean.items():
            track.evidence[label] = track.evidence.get(label, 0.0) + weight * probability / total
        latest_key = (capture_time, source, source_seq)
        if latest_key >= track.latest_key:
            track.last_capture_time, track.source_seq = capture_time, source_seq
            track.valid_until_sim = capture_time + self.ttl_s if valid_until_sim is None else valid_until_sim
            track.latest_key = latest_key
        track.used_ids.add((source, source_seq))
        self.last_reason = admission.last_reason
        return True

    def distribution(self, track_id, *, reference_time):
        track = self.tracks.get(track_id)
        if not isfinite(reference_time) or reference_time < 0 or (track is not None and reference_time < track.last_capture_time):
            raise ValueError("semantic reference time precedes capture")
        return {"unknown": 1.0} if track is None else track.distribution(reference_time, self.half_life_s)


class MultiRateFusion:
    def __init__(self, *, lag_s=None, config: TemporalConfig | None = None):
        self.config = config or TemporalConfig(**({} if lag_s is None else {"lag_s": lag_s}))
        if config is not None and lag_s is not None and lag_s != config.lag_s:
            raise ValueError("conflicting lag configuration")
        self.lag_s = self.config.lag_s
        self.geometry: dict[str, ConstantVelocityFusion3D] = {}
        self.semantic = SemanticEvidenceFusion(half_life_s=self.config.semantic_half_life_s,
                                              lag_s=self.lag_s, ttl_s=self.config.semantic_ttl_s)
        self.admission = EventAdmission(self.lag_s)
        self.provenance: dict[str, dict[tuple[str, int], dict[str, Any]]] = {}
        self.last_reason = "empty"
        self.reference_time = 0.0
        self.episode_id = None

    def validate_event(self, event, reference_time=None):
        event.validate()
        if reference_time is not None and (not isfinite(reference_time) or reference_time < self.reference_time or event.capture_sim_time > reference_time):
            raise ValueError("invalid or regressing reference time")
        value = event.value
        if "position_world_m" in value:
            self._measurement(event).validate()
        probs = value.get("probabilities") or value.get("hypotheses")
        if probs and (any(not isfinite(v) or v < 0 for v in probs.values()) or sum(probs.values()) <= 0):
            raise ValueError("invalid semantic probabilities")

    def _measurement(self, event):
        covariance = event.value.get("position_covariance_m2", np.eye(3) * self.config.fallback_measurement_variance_m2)
        return PositionMeasurement(event.source, event.source_seq, event.capture_sim_time,
                                   np.asarray(event.value["position_world_m"], dtype=float), np.asarray(covariance, dtype=float), event.quality)

    def ingest_event(self, event, *, reference_time):
        self.validate_event(event, reference_time)
        if self.episode_id is not None and event.episode_id != self.episode_id:
            self.last_reason = "episode_mismatch"
            return False
        if event.quality == 0:
            self.last_reason = "zero_quality"
            return self.admission.reject("zero_quality")
        value = event.value
        track = event.track_id or str(value.get("track_id") or "scene")
        identity_source = repr((event.source, track))
        if not self.admission.admit(identity_source, event.source_seq, event.capture_sim_time, reference_time):
            self.last_reason = self.admission.last_reason
            return False
        self.last_reason = self.admission.last_reason
        self.episode_id = event.episode_id
        self.reference_time = reference_time
        if "position_world_m" in value:
            config = asdict(self.config)
            keys = ("lag_s", "process_noise_mps2", "gate_sigma", "initial_position_var", "initial_velocity_var", "max_events")
            filter_ = self.geometry.setdefault(track, ConstantVelocityFusion3D(**{k: config[k] for k in keys}))
            filter_.ingest(self._measurement(event), reference_time=reference_time)
        probabilities = value.get("probabilities") or value.get("hypotheses")
        if probabilities:
            self.semantic.ingest(track, probabilities, capture_time=event.capture_sim_time,
                                 source_seq=event.source_seq, quality=event.quality, source=event.source,
                                 reference_time=reference_time, valid_until_sim=event.valid_until_sim)
        self.provenance.setdefault(track, {})[(event.source, event.source_seq)] = {
            "source": event.source, "source_seq": event.source_seq, "episode_id": event.episode_id,
            "capture_sim_time": event.capture_sim_time, "received_wall_time": event.received_wall_time,
            "quality": event.quality, "frame_id": event.frame_id, "valid_until_sim": event.valid_until_sim,
            "measurement_covariance_source": "provided" if "position_covariance_m2" in value else "configured_fallback",
            "position_covariance_source": value.get("position_covariance_source", "unknown"),
            "position_covariance_calibrated": value.get("position_covariance_calibrated"),
            "position_world_m": self._measurement(event).position_m.tolist() if "position_world_m" in value else None,
            "position_covariance_m2": self._measurement(event).covariance_m2.tolist() if "position_world_m" in value else None,
            "semantic_probabilities": deepcopy(value.get("probabilities") or value.get("hypotheses")),
        }
        return True

    def snapshot(self, *, reference_time):
        if not isfinite(reference_time) or reference_time < self.reference_time:
            raise ValueError("invalid or regressing reference time")
        self.reference_time = reference_time
        geometry, semantic, validity = {}, {}, {}
        for track in sorted(set(self.geometry) | set(self.semantic.tracks)):
            state = self.geometry[track].estimate(reference_time) if track in self.geometry else None
            sem = self.semantic.tracks.get(track)
            reasons = []
            summary = None
            geometry_ttl = None
            if state is None or not state.accepted_measurements:
                reasons.append("geometry_missing")
            else:
                geometry[track] = state
                trace = float(np.trace(state.covariance[:3, :3]))
                summary = {"position_trace_m2": trace, "position_max_std_m": float(np.sqrt(np.linalg.eigvalsh(state.covariance[:3, :3]).max()))}
                if state.age_s > self.config.geometry_max_age_s:
                    reasons.append("geometry_too_old")
                if trace > self.config.geometry_max_position_trace_m2:
                    reasons.append("geometry_uncertain")
                if any(self.provenance[track][identity]["measurement_covariance_source"] != "provided" for identity in self.geometry[track].used_ids):
                    reasons.append("measurement_covariance_unverified")
                latest = max((self.provenance[track][identity] for identity in self.geometry[track].used_ids),
                             key=lambda p: (p["capture_sim_time"], p["source"], p["source_seq"]))
                geometry_ttl = latest["valid_until_sim"]
                if geometry_ttl is not None and reference_time > geometry_ttl:
                    reasons.append("geometry_ttl_expired")
            sem_time = None if sem is None else sem.last_capture_time
            geom_time = None if state is None else state.capture_time
            gap = None if sem_time is None or geom_time is None else abs(geom_time - sem_time)
            ids_match = state is not None and sem is not None and self.geometry[track].used_ids == sem.used_ids
            semantic[track] = self.semantic.distribution(track, reference_time=reference_time)
            validity[track] = {
                "geometry_reference_time": None if state is None else state.reference_time,
                "geometry_capture_time": geom_time,
                "geometry_age_s": None if state is None else state.age_s,
                "geometry_valid_until_sim": geometry_ttl,
                "geometry_valid": not reasons, "geometry_invalid_reasons": reasons,
                "position_covariance": None if state is None else state.covariance[:3, :3].tolist(),
                "covariance_summary": summary,
                "semantic_reference_time": sem_time,
                "semantic_age_s": None if sem is None else reference_time - sem_time,
                "semantic_valid_until_sim": None if sem is None else sem.valid_until_sim,
                "semantic_valid": sem is not None and reference_time <= sem.valid_until_sim,
                "semantic_invalid_reasons": ["semantic_missing"] if sem is None else ["semantic_ttl_expired"] if reference_time > sem.valid_until_sim else [],
                "temporal_consistency_gap_s": gap,
                "temporal_consistency_ok": bool(ids_match and gap <= self.config.consistency_max_gap_s),
                "temporal_consistency_reasons": ([] if ids_match else ["evidence_history_mismatch"]) +
                    (["capture_time_gap"] if gap is not None and gap > self.config.consistency_max_gap_s else []),
                "provenance": deepcopy(list(self.provenance.get(track, {}).values())),
                "geometry_evidence_ids": sorted(self.geometry[track].used_ids) if track in self.geometry else [],
                "semantic_evidence_ids": sorted(sem.used_ids) if sem else [],
            }
        return {"geometry": geometry, "semantic": semantic, "validity": validity,
                "temporal_config": asdict(self.config)}

    def diagnostics(self):
        return {
            "admission": asdict(self.admission.stats),
            "geometry": {track: {"counters": asdict(f.stats), "last_reason": f.last_reason,
                                  "anchor_time": f.anchor_time, "retained_events": f.pending_count}
                         for track, f in self.geometry.items()},
            "semantic": {track: {"counters": asdict(a.stats), "last_reason": a.last_reason}
                         for track, a in self.semantic._admission.items()},
        }
