"""Complete candidate representation with auditable hard evidence.

This module is not a collision checker. The P0 producer supplies synthetic hard
evidence explicitly; later sensor validators supply measured/derived evidence.
Geometric effect estimates never determine admission.
"""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Mapping

from ..contracts import ProtocolError, canonical_json, freeze, thaw
from .action_catalog import (
    ACTION_IDS, CATALOG, CATALOG_REVISION, MAX_SEGMENT_DURATION_S,
    MAX_SEGMENT_ROTATION_RAD, MAX_SEGMENT_TRANSLATION_M, ActionSpec,
)

EXECUTION_STATUSES = frozenset({"ALLOWED", "BLOCKED", "UNKNOWN"})
HARD_REASON_CODES = frozenset({
    "JOINT_LIMIT", "WORKSPACE_LIMIT", "OBSERVED_COLLISION", "SWEEP_COLLISION",
    "SPACE_UNKNOWN", "GEOMETRY_STALE", "SENSOR_INVALID", "EXECUTOR_UNSUPPORTED",
    "DEADLINE_EXPIRED", "HARD_CONSTRAINTS_SATISFIED", "SAFETY_STOP",
})
HARD_PROVENANCES = frozenset({
    "sensor-derived", "proprioceptive", "deterministic_geometry", "synthetic", "unknown",
})


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be a nonempty string")


@dataclass(frozen=True)
class ContextIdentity:
    episode_id: str
    episode_generation: int
    goal_generation: int
    intent_id: str
    intent_generation: int
    target_track_id: str
    target_track_generation: int
    feature_id: str
    feature_generation: int
    calibration_versions: tuple[str, ...]

    def __post_init__(self) -> None:
        for key in ("episode_id", "intent_id", "target_track_id", "feature_id"):
            _identifier(getattr(self, key), key)
        for key in ("episode_generation", "goal_generation", "intent_generation",
                    "target_track_generation", "feature_generation"):
            value = getattr(self, key)
            if type(value) is not int or value < 0:
                raise ProtocolError("INVALID_SCHEMA", f"{key} must be a nonnegative int")
        versions = tuple(self.calibration_versions)
        if not versions or len(set(versions)) != len(versions):
            raise ProtocolError("INVALID_SCHEMA", "calibration_versions must be nonempty and unique")
        for version in versions:
            _identifier(version, "calibration_version")
        object.__setattr__(self, "calibration_versions", tuple(sorted(versions)))


@dataclass(frozen=True)
class HardEvidence:
    status: str
    reason_codes: tuple[str, ...]
    source_ids: tuple[str, ...]
    provenance: str

    def __post_init__(self) -> None:
        if self.status not in EXECUTION_STATUSES or self.provenance not in HARD_PROVENANCES:
            raise ProtocolError("INVALID_SCHEMA", "invalid hard evidence status/provenance")
        reasons = tuple(self.reason_codes)
        sources = tuple(self.source_ids)
        if not reasons or set(reasons) - HARD_REASON_CODES:
            raise ProtocolError("INVALID_SCHEMA", "only declared hard constraint reasons may gate candidates")
        if not sources:
            raise ProtocolError("INVALID_SCHEMA", "hard evidence requires source identity")
        for source in sources:
            _identifier(source, "hard evidence source")
        if self.status == "ALLOWED" and (
            self.provenance == "unknown" or set(reasons) != {"HARD_CONSTRAINTS_SATISFIED"}
        ):
            raise ProtocolError("INVALID_SCHEMA", "ALLOWED needs affirmative hard evidence")
        if self.status != "ALLOWED" and "HARD_CONSTRAINTS_SATISFIED" in reasons:
            raise ProtocolError("INVALID_SCHEMA", "non-allowed evidence contradicts hard satisfaction")
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "source_ids", sources)


@dataclass(frozen=True)
class Candidate:
    spec: ActionSpec
    hard_evidence: HardEvidence
    geometric_effect_estimate: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "geometric_effect_estimate", freeze(self.geometric_effect_estimate))
        canonical_json(self.to_dict())  # Reject nonfinite effects, not negative utility.

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def execution_status(self) -> str:
        return self.hard_evidence.status

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self.spec),
            "execution_status": self.execution_status,
            "hard_reason_codes": list(self.hard_evidence.reason_codes),
            "hard_evidence": asdict(self.hard_evidence),
            "geometric_effect_estimate": thaw(self.geometric_effect_estimate),
            "max_segment_duration_s": MAX_SEGMENT_DURATION_S,
            "max_segment_translation_m": MAX_SEGMENT_TRANSLATION_M,
            "max_segment_rotation_rad": MAX_SEGMENT_ROTATION_RAD,
        }


@dataclass(frozen=True)
class CandidateSet:
    candidate_set_id: str
    identity: ContextIdentity
    source_snapshot_id: str
    candidates: tuple[Candidate, ...]
    generated_monotonic_ns: int
    proposal_deadline_monotonic_ns: int
    catalog_revision: str = CATALOG_REVISION

    def __post_init__(self) -> None:
        _identifier(self.candidate_set_id, "candidate_set_id")
        _identifier(self.source_snapshot_id, "source_snapshot_id")
        object.__setattr__(self, "candidates", tuple(self.candidates))
        if self.catalog_revision != CATALOG_REVISION:
            raise ProtocolError("INVALID_SCHEMA", "unsupported catalog revision")
        if tuple(c.id for c in self.candidates) != ACTION_IDS:
            raise ProtocolError("INVALID_SCHEMA", "all 27 candidates must be in canonical order")
        if tuple(c.spec for c in self.candidates) != CATALOG:
            raise ProtocolError("ACTION_SEMANTICS_CHANGED", "catalog parameters were modified")
        for name in ("generated_monotonic_ns", "proposal_deadline_monotonic_ns"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ProtocolError("INVALID_SCHEMA", f"{name} must be a nonnegative int")
        if self.proposal_deadline_monotonic_ns <= self.generated_monotonic_ns:
            raise ProtocolError("INVALID_SCHEMA", "candidate deadline must follow generation")

    @property
    def presentation_order(self) -> tuple[str, ...]:
        return ACTION_IDS

    @property
    def allowed_ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.candidates if c.execution_status == "ALLOWED")

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "candidate_set_id": self.candidate_set_id,
            "catalog_revision": self.catalog_revision,
            "identity": asdict(self.identity),
            "source_snapshot_id": self.source_snapshot_id,
            "candidates": [c.to_dict() for c in self.candidates],
            "presentation_order": list(self.presentation_order),
            # Deadline changes authorize different behavior; it is not a pure log time.
            "proposal_deadline_monotonic_ns": self.proposal_deadline_monotonic_ns,
        }

    @property
    def candidate_hash(self) -> str:
        encoded = canonical_json(self.semantic_payload())
        return sha256(encoded.encode("utf-8") if isinstance(encoded, str) else encoded).hexdigest()

    def candidate(self, action_id: str) -> Candidate:
        for candidate in self.candidates:
            if candidate.id == action_id:
                return candidate
        raise ProtocolError("INVALID_CHOICE", f"unknown action ID {action_id!r}")


def build_candidate_set(
    *, candidate_set_id: str, identity: ContextIdentity, source_snapshot_id: str,
    hard_evidence: Mapping[str, HardEvidence], generated_monotonic_ns: int,
    proposal_deadline_monotonic_ns: int,
    geometric_effects: Mapping[str, Mapping[str, Any]] | None = None,
) -> CandidateSet:
    """Missing hard evidence stays UNKNOWN. Soft estimates cannot filter actions."""
    effects = geometric_effects or {}
    if (set(hard_evidence) | set(effects)) - set(ACTION_IDS):
        raise ProtocolError("INVALID_SCHEMA", "candidate input contains unknown action IDs")
    missing = HardEvidence("UNKNOWN", ("SENSOR_INVALID",), (source_snapshot_id,), "unknown")
    candidates = tuple(
        Candidate(spec, hard_evidence.get(spec.id, missing), effects.get(spec.id, {}))
        for spec in CATALOG
    )
    return CandidateSet(candidate_set_id, identity, source_snapshot_id, candidates,
                        generated_monotonic_ns, proposal_deadline_monotonic_ns)
