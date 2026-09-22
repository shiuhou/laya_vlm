"""Small, dependency-light embodied decision runtime.

The module keeps the model-facing token contract compatible with Show-Harness while
leaving environment-specific action layouts behind AtomicBackend.
"""
from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import exp, isfinite, log
from typing import Any

import numpy as np

from .fusion import EventAdmission

MOVE = {
    "MV_FWD": (1.0, 0.0, 0.0), "MV_BACK": (-1.0, 0.0, 0.0),
    "MV_LEFT": (0.0, 1.0, 0.0), "MV_RIGHT": (0.0, -1.0, 0.0),
    "MV_UP": (0.0, 0.0, 1.0), "MV_DOWN": (0.0, 0.0, -1.0),
}
ATOMIC_ACTIONS = tuple(MOVE) + ("ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP", "RELEASE", "DONE")
DESCRIPTIONS = {k: k.lower().replace("_", " ") for k in ATOMIC_ACTIONS}


def _finite(value: Any) -> bool:
    if value is None or isinstance(value, (bool, str)):
        return True
    if isinstance(value, (int, float)):
        return isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_finite(k) and _finite(v) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return all(_finite(v) for v in value)
    if isinstance(value, np.ndarray):
        return bool(np.isfinite(value).all())
    return True


@dataclass(frozen=True)
class ObservationEvent:
    source: str
    episode_id: str
    source_seq: int
    capture_sim_time: float
    received_wall_time: float
    value: Mapping[str, Any]
    frame_id: str = "world"
    track_id: str | None = None
    quality: float = 1.0
    valid_until_sim: float | None = None

    def validate(self) -> None:
        if not self.source or not self.episode_id or not isinstance(self.source_seq, int) or self.source_seq < 0:
            raise ValueError("invalid observation identity")
        if not isfinite(self.capture_sim_time) or self.capture_sim_time < 0 or not isfinite(self.received_wall_time):
            raise ValueError("timestamps must be finite")
        if not 0.0 <= self.quality <= 1.0 or not _finite(self.value):
            raise ValueError("invalid observation quality or value")
        if self.valid_until_sim is not None and (not isfinite(self.valid_until_sim) or self.valid_until_sim < self.capture_sim_time):
            raise ValueError("validity interval is invalid")


@dataclass(frozen=True)
class Candidate:
    token: str
    description: str
    feasible: bool = True
    reason_codes: tuple[str, ...] = ()
    risk: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def canonical(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "description": self.description,
            "feasible": self.feasible,
            "reason_codes": list(self.reason_codes),
            "risk": self.risk,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class Decision:
    token: str
    probabilities: Mapping[str, float]
    confidence: float
    source: str
    input_revision: int
    input_sim_time: float
    completed_wall_time: float
    valid_until_sim: float
    status: str = "valid"
    latency_ms: float | None = None
    max_hold_steps: int = 1
    input_belief_id: str | None = None
    candidate_set_id: str | None = None
    input_snapshot_id: str | None = None


@dataclass(frozen=True)
class BeliefSnapshot:
    episode_id: str
    revision: int
    asof_sim_time: float
    continuous: Mapping[str, Any]
    semantic: Mapping[str, Mapping[str, float]]
    goal: Mapping[str, Any]
    candidates: tuple[Candidate, ...] = ()
    ages: Mapping[str, float] = field(default_factory=dict)
    flags: Mapping[str, bool] = field(default_factory=dict)
    validity: Mapping[str, Any] = field(default_factory=dict)
    temporal_config: Mapping[str, Any] = field(default_factory=dict)

    def canonical_json(self) -> str:
        return json.dumps({
            "episode_id": self.episode_id, "revision": self.revision,
            "asof_sim_time": self.asof_sim_time, "continuous": self.continuous,
            "semantic": self.semantic, "goal": self.goal,
            "candidates": [c.canonical() for c in self.candidates],
            "ages": self.ages, "flags": self.flags,
            "validity": self.validity, "temporal_config": self.temporal_config,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def allowed(self) -> set[str]:
        return {c.token for c in self.candidates if c.feasible}

    def belief_id(self) -> str:
        return _sha256_json({
            "episode_id": self.episode_id, "revision": self.revision,
            "asof_sim_time": self.asof_sim_time, "continuous": self.continuous,
            "semantic": self.semantic, "goal": self.goal, "ages": self.ages,
            "flags": self.flags, "validity": self.validity,
            "temporal_config": self.temporal_config,
        })

    def candidate_set_id(self) -> str:
        return _sha256_json({"candidates": [c.canonical() for c in self.candidates]})

    def snapshot_id(self) -> str:
        return _sha256_json({"belief_id": self.belief_id(),
                             "candidate_set_id": self.candidate_set_id()})

    def provider_input(self) -> dict[str, Any]:
        state = json.loads(self.canonical_json())
        state.update({"belief_revision": self.revision, "belief_id": self.belief_id(),
                      "candidate_set_id": self.candidate_set_id(), "snapshot_id": self.snapshot_id(),
                      "candidate_tokens": [c.token for c in self.candidates if c.feasible]})
        return state


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _decision(snapshot: BeliefSnapshot, **kwargs: Any) -> Decision:
    kwargs.setdefault("input_belief_id", snapshot.belief_id())
    kwargs.setdefault("candidate_set_id", snapshot.candidate_set_id())
    kwargs.setdefault("input_snapshot_id", snapshot.snapshot_id())
    return Decision(**kwargs)


class BeliefStore:
    """Late-fusion store for asynchronous geometry and semantic events."""

    def __init__(self, episode_id: str, history_s: float = 1.0, *, allow_delayed: bool = False):
        self.episode_id = episode_id
        self.history_s = float(history_s)
        self.revision = 0
        self._latest: dict[tuple[str, str | None], ObservationEvent] = {}
        self._events: deque[ObservationEvent] = deque()
        self._continuous: dict[str, Any] = {}
        self._semantic: dict[str, dict[str, float]] = {}
        self._semantic_meta: dict[str, tuple[float, float]] = {}
        self._goal: dict[str, Any] = {}
        self._fused_meta: dict[str, tuple[float, float]] = {}
        self.dropped_late = 0
        self.dropped_out_of_order = 0
        self.dropped_duplicate = 0
        self.last_ingest_reason = "empty"
        self.allow_delayed = allow_delayed
        self.admission = EventAdmission(history_s)
        self._validity = {}
        self._temporal_config = {}
        self.reference_time = 0.0

    def ingest(self, event: ObservationEvent, now_sim: float | None = None) -> bool:
        event.validate()
        now = event.capture_sim_time if now_sim is None else float(now_sim)
        if not isfinite(now) or now < self.reference_time:
            raise ValueError("invalid or regressing belief reference time")
        if event.quality == 0:
            self.last_ingest_reason = "zero_quality"
            return self.admission.reject("zero_quality")
        if event.episode_id != self.episode_id:
            self.last_ingest_reason = "episode_mismatch"
            return False
        key = (event.source, event.track_id)
        old = self._latest.get(key)
        if not self.allow_delayed and old and event.source_seq < old.source_seq:
            self.last_ingest_reason = "sequence_regression"
            self.admission.reject("sequence_regression")
            self.dropped_out_of_order = self.admission.stats.dropped_out_of_order
            return False
        if not self.admission.admit(repr(key), event.source_seq, event.capture_sim_time, now):
            self.last_ingest_reason = self.admission.last_reason
            self.dropped_late = self.admission.stats.dropped_too_late
            self.dropped_duplicate = self.admission.stats.dropped_duplicate
            self.dropped_out_of_order = self.admission.stats.dropped_out_of_order
            return False
        self.last_ingest_reason = self.admission.last_reason
        self.reference_time = now
        latest = old is None or event.capture_sim_time >= old.capture_sim_time
        if latest:
            self._latest[key] = event
        self._events.append(event)
        value = dict(event.value)
        if latest and event.source in {"oracle", "geometry", "proprio"}:
            self._continuous.update(value)
            if isinstance(value.get("goal"), Mapping):
                self._goal.update(value["goal"])
        if not self.allow_delayed and event.source in {"semantic", "vision_semantic"}:
            track = event.track_id or str(value.get("track_id") or "scene")
            probs = dict(value.get("probabilities") or value.get("hypotheses") or {})
            if not probs and value.get("label"):
                probs = {str(value["label"]): 1.0, "unknown": 0.0}
            self._update_semantic(track, probs, event, now)
        self.revision += 1
        cutoff = now - self.history_s
        self._events = deque(e for e in self._events if e.capture_sim_time >= cutoff)
        return True

    def _update_semantic(self, track: str, probs: Mapping[str, float], event: ObservationEvent, now: float) -> None:
        clean = {str(k): max(0.0, float(v)) for k, v in probs.items()}
        total = sum(clean.values())
        if total <= 0:
            return
        clean = {k: v / total for k, v in clean.items()}
        prior = self._semantic.get(track, {})
        weight = max(0.05, event.quality) * exp(-max(0.0, now - event.capture_sim_time) / 0.75)
        labels = set(prior) | set(clean) | {"unknown"}
        fused = {
            label: exp((1 - weight) * log(max(prior.get(label, 1 / len(labels)), 1e-6))
                       + weight * log(max(clean.get(label, 0.0), 1e-6)))
            for label in labels
        }
        normalizer = sum(fused.values())
        self._semantic[track] = {k: v / normalizer for k, v in fused.items()}
        self._semantic_meta[track] = (event.valid_until_sim if event.valid_until_sim is not None else event.capture_sim_time + 0.75, event.capture_sim_time)

    def apply_fused_snapshot(self, fused: Mapping[str, Any], now_sim: float) -> None:
        """Publish timestamp-aware fusion output into the model-facing belief."""
        geometry = fused.get("geometry", {})
        for track, state in geometry.items():
            prefix = f"vision:{track}"
            self._continuous[f"{prefix}:position_world_m"] = list(map(float, state.position_m))
            self._continuous[f"{prefix}:velocity_mps"] = list(map(float, state.velocity_mps))
            self._continuous[f"{prefix}:covariance"] = np.asarray(state.covariance).tolist() if hasattr(state.covariance, "tolist") else state.covariance
            self._fused_meta[prefix] = (float(state.reference_time), float(state.age_s))
        for track, probabilities in fused.get("semantic", {}).items():
            self._semantic[track] = {str(k): float(v) for k, v in probabilities.items()}
            metadata = fused["validity"][track]
            if metadata["semantic_reference_time"] is not None:
                self._semantic_meta[track] = (metadata["semantic_valid_until_sim"], metadata["semantic_reference_time"])
        self._validity = json.loads(json.dumps(fused.get("validity", {})))
        self._temporal_config = dict(fused.get("temporal_config", {}))

    def snapshot(self, now_sim: float, candidates: tuple[Candidate, ...] = (), goal: Mapping[str, Any] | None = None) -> BeliefSnapshot:
        if not isfinite(now_sim) or now_sim < self.reference_time:
            raise ValueError("invalid or regressing belief reference time")
        self.reference_time = now_sim
        semantic = json.loads(json.dumps(self._semantic))
        ages: dict[str, float] = {}
        flags: dict[str, bool] = {}
        validity = json.loads(json.dumps(self._validity))
        for track, metadata in validity.items():
            captured = metadata["geometry_capture_time"]
            if captured is not None:
                metadata["geometry_age_s"] = now_sim - captured
                if now_sim - captured > self._temporal_config["geometry_max_age_s"]:
                    metadata["geometry_valid"] = False
                    if "geometry_too_old" not in metadata["geometry_invalid_reasons"]:
                        metadata["geometry_invalid_reasons"].append("geometry_too_old")
                ttl = metadata.get("geometry_valid_until_sim")
                if ttl is not None and now_sim > ttl:
                    metadata["geometry_valid"] = False
                    if "geometry_ttl_expired" not in metadata["geometry_invalid_reasons"]:
                        metadata["geometry_invalid_reasons"].append("geometry_ttl_expired")
            if metadata["semantic_reference_time"] is not None:
                metadata["semantic_age_s"] = now_sim - metadata["semantic_reference_time"]
                metadata["semantic_valid"] = now_sim <= metadata["semantic_valid_until_sim"]
                metadata["semantic_invalid_reasons"] = [] if metadata["semantic_valid"] else ["semantic_ttl_expired"]
            flags[f"geometry_invalid:{track}"] = not metadata["geometry_valid"]
            flags[f"temporal_inconsistency:{track}"] = not metadata["temporal_consistency_ok"]
        for key, (captured, age) in self._fused_meta.items():
            ages[f"{key}:age_s"] = max(0.0, float(age) + max(0.0, now_sim - captured))
        for track, (valid_until, captured) in self._semantic_meta.items():
            age = max(0.0, now_sim - captured)
            ages[f"semantic:{track}"] = age
            if now_sim > valid_until:
                flags[f"semantic_stale:{track}"] = True
                unknown = max(semantic[track].get("unknown", 0.0), 0.5)
                known_total = sum(v for k, v in semantic[track].items() if k != "unknown")
                semantic[track] = {k: v * (1 - unknown) / known_total for k, v in semantic[track].items() if k != "unknown"} if known_total else {}
                semantic[track]["unknown"] = unknown if known_total else 1.0
        merged_goal = dict(self._goal)
        if goal:
            merged_goal.update(goal)
        return BeliefSnapshot(self.episode_id, self.revision, float(now_sim),
                              json.loads(json.dumps(self._continuous)), semantic, merged_goal, candidates, ages, flags,
                              validity, dict(self._temporal_config))


class DecisionProvider(ABC):
    @abstractmethod
    def decide(self, snapshot: BeliefSnapshot) -> Decision: ...


class RuleProvider(DecisionProvider):
    version = "rule-greedy-distance-v1"

    def decide(self, snapshot: BeliefSnapshot) -> Decision:
        allowed = sorted(snapshot.allowed())
        priority = ("DONE", "GRASP", "RELEASE", "MV_FWD", "MV_BACK", "MV_LEFT", "MV_RIGHT", "MV_UP", "MV_DOWN", "ROTATE_CW", "ROTATE_CCW", "STOP")
        token = next((item for item in priority if item in allowed), "STOP")
        if snapshot.goal.get("satisfied") and "DONE" in allowed:
            token = "DONE"
        elif snapshot.continuous.get("aligned") and snapshot.continuous.get("holding") is None and "GRASP" in allowed:
            token = "GRASP"
        if any(c.metadata.get("builder_version") == "vision-candidates-v1" for c in snapshot.candidates):
            # A deliberately small approach baseline. Grasp/pull affordances are
            # not established by a box centroid, so no task planner is implied.
            moves = [c for c in snapshot.candidates if c.feasible and c.token in MOVE
                     and (c.metadata.get("distance_reduction_m") or 0) > 0]
            token = max(moves, key=lambda c: c.metadata["distance_reduction_m"]).token if moves else "STOP"
        probs = {k: float(k == token) for k in allowed}
        return _decision(snapshot, token=token, probabilities=probs, confidence=1.0,
                         source="rule", input_revision=snapshot.revision,
                         input_sim_time=snapshot.asof_sim_time, completed_wall_time=time.time(),
                         valid_until_sim=snapshot.asof_sim_time + .5)


class ReplayProvider(DecisionProvider):
    def __init__(self, decisions: Mapping[int, str]):
        self.decisions = dict(decisions)
    def decide(self, snapshot: BeliefSnapshot) -> Decision:
        allowed = snapshot.allowed()
        token = self.decisions.get(snapshot.revision, "STOP")
        if token not in allowed:
            token = "STOP" if "STOP" in allowed else next(iter(allowed), "STOP")
        return _decision(snapshot, token=token,
                         probabilities={k: float(k == token) for k in allowed}, confidence=1.0,
                         source="replay", input_revision=snapshot.revision,
                         input_sim_time=snapshot.asof_sim_time, completed_wall_time=time.time(),
                         valid_until_sim=snapshot.asof_sim_time + .5)


class LayaProvider(DecisionProvider):
    version = "laya-typed-choice-v2"
    def __init__(self, agent: Any, model_name: str = "typed-decisions"):
        self.agent, self.model_name = agent, model_name
    def decide(self, snapshot: BeliefSnapshot) -> Decision:
        criteria = {c.token: c.description for c in snapshot.candidates if c.feasible}
        if not criteria:
            return _decision(snapshot, token="STOP", probabilities={"STOP": 1.0}, confidence=1.0,
                             source="laya", input_revision=snapshot.revision,
                             input_sim_time=snapshot.asof_sim_time, completed_wall_time=time.time(),
                             valid_until_sim=snapshot.asof_sim_time + .2, status="invalid")
        if len(criteria) == 1:
            # laya 0.3.4 assumes topk(2). A singleton is a forced constraint
            # choice, not model evidence; do not fabricate a second option.
            token = next(iter(criteria))
            return _decision(snapshot, token=token, probabilities={token: 1.0}, confidence=1.0,
                             source="laya_single_candidate", input_revision=snapshot.revision,
                             input_sim_time=snapshot.asof_sim_time, completed_wall_time=time.time(),
                             valid_until_sim=snapshot.asof_sim_time + .5, latency_ms=0.0)
        questions = {"action": {"type": "choice",
            "instructions": "Choose exactly one allowed atomic action. Allowed means validity checks passed; collision freedom is not established.",
            "criteria": criteria}}
        state = snapshot.provider_input()
        started = time.perf_counter()
        if hasattr(self.agent, "system_one"):
            result = self.agent.system_one(state, questions)
        else:
            result = self.agent.predict(state, questions, model=self.model_name)
        latency = (time.perf_counter() - started) * 1000.0
        answer = result["answers"]["action"]
        token = str(answer["choice"])
        probs = {str(k): float(v) for k, v in answer.get("probabilities", {}).items()}
        status = "valid" if token in criteria else "invalid"
        return _decision(snapshot, token=token, probabilities=probs,
                         confidence=float(answer.get("confidence", 0.0)), source="laya",
                         input_revision=snapshot.revision, input_sim_time=snapshot.asof_sim_time,
                         completed_wall_time=time.time(), valid_until_sim=snapshot.asof_sim_time + .5,
                         status=status, latency_ms=latency)


def load_laya_provider(path_or_repo: str = "convaiinnovations/laya", *,
                       subfolder: str | None = "typed-decisions",
                       device: str | None = None) -> LayaProvider:
    """Load Laya from a local checkpoint or an explicitly selected repository.

    Local paths are always loaded offline.  The runtime never downloads weights as a
    side effect of importing or constructing a provider.
    """
    from pathlib import Path

    import laya
    path = Path(path_or_repo).expanduser()
    if path.exists():
        agent = laya.load(str(path), device=device, subfolder=None)
        model_name = path.name
    else:
        agent = laya.load(path_or_repo, device=device, subfolder=subfolder)
        model_name = subfolder or path_or_repo
    return LayaProvider(agent, model_name=model_name)


class AtomicBackend(ABC):
    @abstractmethod
    def tcp_pos(self): ...
    @abstractmethod
    def apply_delta(self, delta, grip_cmd=None):
        """Translate; None preserves the backend-owned gripper command."""
        ...
    @abstractmethod
    def gripper_width(self): ...
    @abstractmethod
    def success(self): ...
    def rotate(self, token): pass
    def open_gripper(self): pass
    def close_gripper(self): pass
    def hold(self): pass
    def execution_state(self): return None
    def execution_evidence(self, token, before):
        return {"execution_contract_violation": None,
                "execution_contract_reason": ["backend_contract_not_instrumented"]}


class AtomicExecutor:
    def __init__(self, backend: AtomicBackend, step_m: float | None = None):
        backend_step = getattr(backend, "step_m", None)
        self.backend = backend
        self.step_m = float(backend_step if step_m is None and backend_step is not None else (.02 if step_m is None else step_m))
    def execute(self, token: str) -> dict[str, Any]:
        import numpy as np
        token = str(token).upper()
        move = {k: np.asarray(v) for k, v in MOVE.items()}
        before = np.asarray(self.backend.tcp_pos()).copy()
        contract_before = self.backend.execution_state()
        if token in move:
            self.backend.apply_delta(move[token] * self.step_m)
        elif token in ("ROTATE_CW", "ROTATE_CCW"):
            self.backend.rotate(token)
        elif token == "GRASP":
            self.backend.close_gripper()
        elif token == "RELEASE":
            self.backend.open_gripper()
        elif token == "STOP":
            self.backend.hold()
        elif token == "DONE":
            if not self.backend.success():
                raise RuntimeError("DONE rejected before success predicate")
        else:
            raise ValueError(f"unknown token {token}")
        after = np.asarray(self.backend.tcp_pos()).copy()
        return {"token": token, "before": before.tolist(), "after": after.tolist(),
                "delta_m": (after - before).tolist(), "success": bool(self.backend.success()),
                **self.backend.execution_evidence(token, contract_before)}


class FakeBackend(AtomicBackend):
    def __init__(self):
        import numpy as np
        self.pos, self.width, self.done = np.zeros(3), .08, False
    def tcp_pos(self): return self.pos.copy()
    def apply_delta(self, delta, grip_cmd=None): self.pos += delta
    def gripper_width(self): return float(self.width)
    def close_gripper(self): self.width = 0.0
    def open_gripper(self): self.width = .08
    def success(self): return bool(self.done)
    def hold(self): pass


class CandidateBuilder:
    def build(self, belief: BeliefSnapshot) -> tuple[Candidate, ...]:
        c = []
        for token in MOVE:
            blocked = bool(belief.continuous.get("blocked_" + token.lower(), False))
            c.append(Candidate(token, DESCRIPTIONS[token], not blocked, ("blocked",) if blocked else (), .1))
        c.append(Candidate("STOP", DESCRIPTIONS["STOP"], True))
        if belief.continuous.get("aligned") and belief.continuous.get("holding") is None:
            c.append(Candidate("GRASP", DESCRIPTIONS["GRASP"], True, (), .4))
        if belief.continuous.get("gripper_command", "OPEN") == "CLOSED" or belief.continuous.get("holding"):
            c.append(Candidate("RELEASE", DESCRIPTIONS["RELEASE"], True, (), .3))
        if belief.goal.get("satisfied"):
            c.append(Candidate("DONE", DESCRIPTIONS["DONE"], True))
        return tuple(c)
