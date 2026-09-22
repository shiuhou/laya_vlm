"""Single-process runtime loop shared by fake, MuJoCo and LIBERO backends."""
from __future__ import annotations

import time
import json
from copy import deepcopy
from math import isfinite
from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from .fusion import MultiRateFusion
from .runtime_core import (
    AtomicExecutor,
    BeliefStore,
    CandidateBuilder,
    DecisionProvider,
    ObservationEvent,
    _decision,
)


class Runtime:
    def __init__(self, episode_id: str, provider: DecisionProvider, backend: Any,
                 candidate_builder: CandidateBuilder | None = None,
                 fusion: MultiRateFusion | None = None, *, event_sink=None,
                 sim_clock=None, oracle: bool | None = None):
        if fusion is not None:
            if fusion.episode_id not in (None, episode_id):
                raise ValueError("fusion belongs to a different episode")
            fusion.episode_id = episode_id
        self.store = BeliefStore(episode_id, history_s=fusion.lag_s if fusion else 1.0,
                                 allow_delayed=fusion is not None)
        self.provider = provider
        self.backend = backend
        self.candidate_builder = candidate_builder or CandidateBuilder()
        self.fusion = fusion
        self.executor = AtomicExecutor(backend)
        self.source_seq = 0
        self.event_sink = event_sink
        self.sim_clock = sim_clock
        self.oracle = oracle
        self.step_index = 0
        if oracle is False and getattr(self.candidate_builder, "oracle", None) is not False:
            raise ValueError("non-oracle runtime requires a visual candidate builder")

    def emit(self, kind, data):
        if self.event_sink:
            self.event_sink(kind, data)

    def diagnostics(self):
        return {"store": asdict(self.store.admission.stats),
                "store_last_reason": self.store.last_ingest_reason,
                "fusion": self.fusion.diagnostics() if self.fusion else None}

    def ingest(self, event: ObservationEvent, now_sim: float | None = None) -> bool:
        if self.oracle is False:
            from .adapters.physics_preview import PROPRIO_KEYS
            if event.source == "proprio":
                if set(event.value) - PROPRIO_KEYS:
                    raise ValueError("unknown proprioception input")
            elif event.source != "locateanything+depth":
                raise ValueError("non-visual observation source forbidden")
        if self.fusion is not None:
            self.fusion.validate_event(event, event.capture_sim_time if now_sim is None else now_sim)
        accepted = self.store.ingest(event, now_sim=now_sim)
        if self.fusion is not None and accepted:
            reference = event.capture_sim_time if now_sim is None else float(now_sim)
            self.fusion.ingest_event(event, reference_time=reference)
            self.store.apply_fused_snapshot(self.fusion.snapshot(reference_time=reference), reference)
        self.emit("observation", {"event": asdict(event), "accepted": accepted,
                                 "now_sim": now_sim, "diagnostics": self.diagnostics()})
        return accepted

    def observe(self, source: str, sim_time: float, value: Mapping[str, Any], *,
                track_id: str | None = None, quality: float = 1.0,
                valid_until_sim: float | None = None) -> bool:
        self.source_seq += 1
        return self.ingest(ObservationEvent(
            source=source, episode_id=self.store.episode_id, source_seq=self.source_seq,
            capture_sim_time=float(sim_time), received_wall_time=time.time(),
            value=dict(value), track_id=track_id, quality=quality,
            valid_until_sim=valid_until_sim,
        ), now_sim=sim_time)

    def step(self, sim_time: float, goal: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if self.fusion is not None:
            self.store.apply_fused_snapshot(self.fusion.snapshot(reference_time=sim_time), sim_time)
        # Snapshot twice so candidate generation sees the latest fused state.
        snapshot = self.store.snapshot(sim_time, goal=goal)
        candidates = self.candidate_builder.build(snapshot)
        snapshot = self.store.snapshot(sim_time, candidates=candidates, goal=goal)
        candidate_diagnostics = deepcopy(getattr(self.candidate_builder, "last_diagnostics", {}))
        identity = {"belief_id": snapshot.belief_id(), "candidate_set_id": snapshot.candidate_set_id(),
                    "snapshot_id": snapshot.snapshot_id()}
        step = self.step_index
        self.step_index += 1
        self.emit("snapshot", {"step": step, **identity, "snapshot": json.loads(snapshot.canonical_json()),
                               "candidate_diagnostics": candidate_diagnostics,
                               "temporal_diagnostics": self.diagnostics()})
        started = time.perf_counter()
        try:
            decision = self.provider.decide(deepcopy(snapshot))
        except Exception as exc:
            self.emit("failure", {"step": step, "category": "model_error", "phase": "decision",
                                  **identity, "exception": repr(exc)})
            raise
        latency = (time.perf_counter() - started) * 1000
        self.emit("decision", {"step": step, **identity, "decision": asdict(decision),
                               "provider": type(self.provider).__name__, "decision_latency_ms": latency})
        allowed = snapshot.allowed()
        decision_invalid_reason = None
        execution_time = float(self.sim_clock()) if self.sim_clock else sim_time
        if decision.token not in allowed:
            decision_invalid_reason = "decision_not_allowed"
        elif not isfinite(decision.valid_until_sim) or decision.valid_until_sim < execution_time:
            decision_invalid_reason = "decision_expired"
        elif (decision.input_revision != snapshot.revision or decision.input_sim_time != sim_time
              or decision.input_snapshot_id != identity["snapshot_id"]
              or decision.input_belief_id != identity["belief_id"]
              or decision.candidate_set_id != identity["candidate_set_id"]
              or decision.status != "valid"):
            decision_invalid_reason = "decision_invalid"
        raw_decision = decision
        if decision_invalid_reason:
            self.emit("failure", {"step": step, "category": decision_invalid_reason, **identity})
            # Never substitute an arbitrary movement when the provider fails.
            if "STOP" not in allowed:
                raise RuntimeError("invalid decision and no feasible STOP")
            decision = _decision(snapshot, token="STOP", probabilities={"STOP": 1.0}, confidence=0.0,
                                 source="fallback", input_revision=snapshot.revision,
                                 input_sim_time=sim_time, completed_wall_time=time.time(),
                                 valid_until_sim=execution_time + 0.1, status="fallback")
        self.emit("execution_started", {"step": step, **identity, "execution_sim_time": execution_time,
                                        "decision": asdict(decision), "fallback_reason": decision_invalid_reason})
        try:
            result = self.executor.execute(decision.token)
        except Exception as exc:
            self.emit("failure", {"step": step, "category": "environment_error", "phase": "execution",
                                  **identity, "exception": repr(exc)})
            raise
        self.emit("action", {"step": step, **identity, "execution": result})
        if result.get("execution_contract_violation"):
            self.emit("failure", {"step": step, "category": "execution_contract_violation",
                                  "reasons": result["execution_contract_reason"]})
        return {"snapshot": snapshot, "decision": decision, "raw_decision": raw_decision, "result": result,
                **identity, "candidate_diagnostics": candidate_diagnostics,
                "decision_invalid_reason": decision_invalid_reason,
                "temporal_diagnostics": self.diagnostics()}
