"""Evaluator-only official success channel, isolated from policy subscriptions."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from .contracts import ProtocolError


@dataclass(frozen=True)
class EvaluationRecord:
    evaluation_id: str
    episode_id: str
    episode_generation: int
    reference_sim_time_s: float
    evaluated_monotonic_ns: int
    official_success: bool
    evaluator_revision: str
    provenance: str = "simulator_oracle"

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in (
                self.evaluation_id, self.episode_id, self.evaluator_revision)):
            raise ProtocolError("INVALID_SCHEMA", "evaluation identity is required")
        if type(self.episode_generation) is not int or self.episode_generation < 0:
            raise ProtocolError("INVALID_SCHEMA", "invalid episode generation")
        if type(self.evaluated_monotonic_ns) is not int or self.evaluated_monotonic_ns < 0:
            raise ProtocolError("INVALID_SCHEMA", "invalid evaluation wall time")
        if not isinstance(self.reference_sim_time_s, (int, float)) or isinstance(self.reference_sim_time_s, bool) \
                or not isfinite(self.reference_sim_time_s) or self.reference_sim_time_s < 0:
            raise ProtocolError("INVALID_SCHEMA", "invalid evaluation sim time")
        if type(self.official_success) is not bool or self.provenance != "simulator_oracle":
            raise ProtocolError("INVALID_SCHEMA", "evaluation must preserve oracle provenance")


@dataclass(frozen=True)
class EvaluationStop:
    """Scheduler-only stop signal; never evidence of a perceptual stage result."""
    episode_id: str
    episode_generation: int
    evaluation_id: str
    reason_code: str = "OFFICIAL_SUCCESS"


class IndependentEvaluator:
    """The only injected check with simulator truth; writes its own record sink.

    There is deliberately no policy observer or candidate callback. Scheduler
    cancellation may consume on_stop, but cannot put its result in model state.
    """
    def __init__(self, *, check_success: Callable[[], bool],
                 record_sink: Callable[[EvaluationRecord], None],
                 on_stop: Callable[[EvaluationStop], None], evaluator_revision: str):
        self._check_success, self._record_sink = check_success, record_sink
        self._on_stop, self._revision = on_stop, evaluator_revision

    def evaluate(self, *, evaluation_id: str, episode_id: str, episode_generation: int,
                 reference_sim_time_s: float, evaluated_monotonic_ns: int) -> None:
        success = self._check_success()
        record = EvaluationRecord(evaluation_id, episode_id, episode_generation,
                                  reference_sim_time_s, evaluated_monotonic_ns, success, self._revision)
        self._record_sink(record)
        if success:
            self._on_stop(EvaluationStop(episode_id, episode_generation, evaluation_id))
