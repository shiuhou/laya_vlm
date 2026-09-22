"""Small, dependency-light embodied decision runtime.

The module keeps the model-facing token contract compatible with Show-Harness while
leaving environment-specific action layouts behind AtomicBackend.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import exp, isfinite, log
from typing import Any

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
        if not self.source or not self.episode_id or self.source_seq < 0:
            raise ValueError("invalid observation identity")
        if not isfinite(self.capture_sim_time) or not isfinite(self.received_wall_time):
            raise ValueError("timestamps must be finite")
        if not 0.0 <= self.quality <= 1.0 or not _finite(self.value):
            raise ValueError("invalid observation quality or value")
        if self.valid_until_sim is not None and self.valid_until_sim < self.capture_sim_time:
            raise ValueError("validity interval is invalid")


@dataclass(frozen=True)
class Candidate:
    token: str
    description: str
    feasible: bool = True
    reason_codes: tuple[str, ...] = ()
    risk: float = 0.0


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

    def canonical_json(self) -> str:
        return json.dumps({
            "episode_id": self.episode_id, "revision": self.revision,
            "asof_sim_time": self.asof_sim_time, "continuous": self.continuous,
            "semantic": self.semantic, "goal": self.goal,
            "candidates": [c.__dict__ for c in self.candidates],
            "ages": self.ages, "flags": self.flags,
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def allowed(self) -> set[str]:
        return {c.token for c in self.candidates if c.feasible}


class BeliefStore:
    """Late-fusion store for asynchronous geometry and semantic events."""

    def __init__(self, episode_id: str, history_s: float = 1.0):
        self.episode_id = episode_id
        self.history_s = float(history_s)
        self.revision = 0
        self._latest: dict[tuple[str, str | None], ObservationEvent] = {}
        self._events: deque[ObservationEvent] = deque()
        self._continuous: dict[str, Any] = {}
        self._semantic: dict[str, dict[str, float]] = {}
        self._semantic_meta: dict[str, tuple[float, float]] = {}
        self._goal: dict[str, Any] = {}
        self.dropped_late = 0
        self.dropped_out_of_order = 0

    def ingest(self, event: ObservationEvent, now_sim: float | None = None) -> bool:
        event.validate()
        now = event.capture_sim_time if now_sim is None else float(now_sim)
        if event.capture_sim_time < now - self.history_s:
            self.dropped_late += 1
            return False
        key = (event.source, event.track_id)
        old = self._latest.get(key)
        if old and event.source_seq <= old.source_seq:
            self.dropped_out_of_order += 1
            return False
        self._latest[key] = event
        self._events.append(event)
        value = dict(event.value)
        if event.source in {"oracle", "geometry", "proprio"}:
            self._continuous.update(value)
            if isinstance(value.get("goal"), Mapping):
                self._goal.update(value["goal"])
        if event.source in {"semantic", "vision_semantic"}:
            track = event.track_id or str(value.get("track_id") or "scene")
            probs = dict(value.get("probabilities") or value.get("hypotheses") or {})
            if not probs and value.get("label"):
                probs = {str(value["label"]): 1.0, "unknown": 0.0}
            self._update_semantic(track, probs, event, now)
        self.revision += 1
        cutoff = now - self.history_s
        while self._events and self._events[0].capture_sim_time < cutoff:
            self._events.popleft()
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
        self._semantic_meta[track] = (event.valid_until_sim or now + 0.75, event.capture_sim_time)

    def snapshot(self, now_sim: float, candidates: tuple[Candidate, ...] = (), goal: Mapping[str, Any] | None = None) -> BeliefSnapshot:
        semantic = json.loads(json.dumps(self._semantic))
        ages: dict[str, float] = {}
        flags: dict[str, bool] = {}
        for track, (valid_until, captured) in self._semantic_meta.items():
            age = max(0.0, now_sim - captured)
            ages[f"semantic:{track}"] = age
            if now_sim > valid_until:
                flags[f"semantic_stale:{track}"] = True
                semantic[track]["unknown"] = max(semantic[track].get("unknown", 0.0), 0.5)
        merged_goal = dict(self._goal)
        if goal:
            merged_goal.update(goal)
        return BeliefSnapshot(self.episode_id, self.revision, float(now_sim),
                              dict(self._continuous), semantic, merged_goal, candidates, ages, flags)


class DecisionProvider(ABC):
    @abstractmethod
    def decide(self, snapshot: BeliefSnapshot) -> Decision: ...


class RuleProvider(DecisionProvider):
    def decide(self, snapshot: BeliefSnapshot) -> Decision:
        allowed = list(snapshot.allowed())
        priority = ("DONE", "GRASP", "RELEASE", "MV_FWD", "MV_BACK", "MV_LEFT", "MV_RIGHT", "MV_UP", "MV_DOWN", "ROTATE_CW", "ROTATE_CCW", "STOP")
        token = next((item for item in priority if item in allowed), "STOP")
        if snapshot.goal.get("satisfied") and "DONE" in allowed:
            token = "DONE"
        elif snapshot.continuous.get("aligned") and snapshot.continuous.get("holding") is None and "GRASP" in allowed:
            token = "GRASP"
        probs = {k: float(k == token) for k in allowed}
        return Decision(token, probs, 1.0, "rule", snapshot.revision, snapshot.asof_sim_time,
                        time.time(), snapshot.asof_sim_time + .5)


class ReplayProvider(DecisionProvider):
    def __init__(self, decisions: Mapping[int, str]):
        self.decisions = dict(decisions)
    def decide(self, snapshot: BeliefSnapshot) -> Decision:
        allowed = snapshot.allowed()
        token = self.decisions.get(snapshot.revision, "STOP")
        if token not in allowed:
            token = "STOP" if "STOP" in allowed else next(iter(allowed), "STOP")
        return Decision(token, {k: float(k == token) for k in allowed}, 1.0, "replay",
                        snapshot.revision, snapshot.asof_sim_time, time.time(), snapshot.asof_sim_time + .5)


class LayaProvider(DecisionProvider):
    def __init__(self, agent: Any, model_name: str = "typed-decisions"):
        self.agent, self.model_name = agent, model_name
    def decide(self, snapshot: BeliefSnapshot) -> Decision:
        criteria = {c.token: c.description for c in snapshot.candidates if c.feasible}
        if not criteria:
            return Decision("STOP", {"STOP": 1.0}, 1.0, "laya", snapshot.revision,
                            snapshot.asof_sim_time, time.time(), snapshot.asof_sim_time + .2, "invalid")
        questions = {"action": {"type": "choice",
            "instructions": "Choose exactly one physically feasible atomic action.",
            "criteria": criteria}}
        state = {"episode_id": snapshot.episode_id, "belief_revision": snapshot.revision,
                 "asof_sim_time": snapshot.asof_sim_time, "continuous": snapshot.continuous,
                 "semantic": snapshot.semantic, "goal": snapshot.goal,
                 "candidate_tokens": list(criteria)}
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
        if status != "valid":
            token = "STOP" if "STOP" in criteria else next(iter(criteria))
        return Decision(token, probs, float(answer.get("confidence", 0.0)), "laya",
                        snapshot.revision, snapshot.asof_sim_time, time.time(),
                        snapshot.asof_sim_time + .5, status, latency_ms=latency)


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
    def apply_delta(self, delta, grip_cmd): ...
    @abstractmethod
    def gripper_width(self): ...
    @abstractmethod
    def success(self): ...
    def rotate(self, token): pass
    def open_gripper(self): pass
    def close_gripper(self): pass
    def hold(self): pass


class AtomicExecutor:
    def __init__(self, backend: AtomicBackend, step_m: float | None = None):
        backend_step = getattr(backend, "step_m", None)
        self.backend = backend
        self.step_m = float(backend_step if step_m is None and backend_step is not None else (.02 if step_m is None else step_m))
        self.grip_cmd = 1.0
    def execute(self, token: str) -> dict[str, Any]:
        import numpy as np
        token = str(token).upper()
        move = {k: np.asarray(v) for k, v in MOVE.items()}
        before = np.asarray(self.backend.tcp_pos()).copy()
        if token in move:
            self.backend.apply_delta(move[token] * self.step_m, self.grip_cmd)
        elif token in ("ROTATE_CW", "ROTATE_CCW"):
            self.backend.rotate(token)
        elif token == "GRASP":
            self.grip_cmd = -1.0; self.backend.close_gripper()
        elif token == "RELEASE":
            self.grip_cmd = 1.0; self.backend.open_gripper()
        elif token == "STOP":
            self.backend.hold()
        elif token == "DONE":
            if not self.backend.success():
                raise RuntimeError("DONE rejected before success predicate")
        else:
            raise ValueError(f"unknown token {token}")
        after = np.asarray(self.backend.tcp_pos()).copy()
        return {"token": token, "before": before.tolist(), "after": after.tolist(),
                "delta_m": (after - before).tolist(), "success": bool(self.backend.success())}


class FakeBackend(AtomicBackend):
    def __init__(self):
        import numpy as np
        self.pos, self.width, self.done = np.zeros(3), .08, False
    def tcp_pos(self): return self.pos.copy()
    def apply_delta(self, delta, grip_cmd): self.pos += delta
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
