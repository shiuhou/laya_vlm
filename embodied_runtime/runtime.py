"""Single-process runtime loop shared by fake, MuJoCo and LIBERO backends."""
from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from .fusion import MultiRateFusion
from .runtime_core import (
    AtomicExecutor,
    BeliefStore,
    CandidateBuilder,
    Decision,
    DecisionProvider,
    ObservationEvent,
)


class Runtime:
    def __init__(self, episode_id: str, provider: DecisionProvider, backend: Any,
                 candidate_builder: CandidateBuilder | None = None,
                 fusion: MultiRateFusion | None = None):
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

    def ingest(self, event: ObservationEvent, now_sim: float | None = None) -> bool:
        if self.fusion is not None:
            self.fusion.validate_event(event, event.capture_sim_time if now_sim is None else now_sim)
        accepted = self.store.ingest(event, now_sim=now_sim)
        if self.fusion is not None and accepted:
            reference = event.capture_sim_time if now_sim is None else float(now_sim)
            self.fusion.ingest_event(event, reference_time=reference)
            self.store.apply_fused_snapshot(self.fusion.snapshot(reference_time=reference), reference)
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
        decision = self.provider.decide(snapshot)
        allowed = snapshot.allowed()
        if decision.token not in allowed:
            fallback = "STOP" if "STOP" in allowed else next(iter(allowed), "STOP")
            decision = Decision(
                token=fallback, probabilities={fallback: 1.0}, confidence=0.0,
                source="fallback", input_revision=snapshot.revision,
                input_sim_time=sim_time, completed_wall_time=time.time(),
                valid_until_sim=sim_time + 0.1, status="invalid",
            )
        result = self.executor.execute(decision.token)
        return {"snapshot": snapshot, "decision": decision, "result": result,
                "temporal_diagnostics": {
                    "store": asdict(self.store.admission.stats),
                    "store_last_reason": self.store.last_ingest_reason,
                    "fusion": self.fusion.diagnostics() if self.fusion else None,
                }}
