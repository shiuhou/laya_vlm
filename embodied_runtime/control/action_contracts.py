"""Validate model proposals and authorize exactly one interruptible segment."""

from dataclasses import asdict, dataclass, field
from math import cos, isclose, isfinite, sin, sqrt
from typing import Any, Mapping

from ..contracts import ProtocolError, canonical_json, freeze
from .action_catalog import (
    ACTION_IDS, MAX_CONTACT_TRANSLATION_M, MAX_SEGMENT_DURATION_S,
    MAX_SEGMENT_ROTATION_RAD, MAX_SEGMENT_TRANSLATION_M, REFERENCE_FRAME,
    action_spec,
)
from .local_candidates import Candidate, CandidateSet, ContextIdentity, EXECUTION_STATUSES


def _finite(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be finite")


def _vector(value: tuple[float, ...], size: int, name: str) -> tuple[float, ...]:
    result = tuple(value)
    if len(result) != size:
        raise ProtocolError("INVALID_SCHEMA", f"{name} must have {size} components")
    for component in result:
        _finite(component, name)
    return result


def _ns(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be a nonnegative int")


def _nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be nonempty")


@dataclass(frozen=True)
class EefPose:
    position_m: tuple[float, float, float]
    quaternion_xyzw: tuple[float, float, float, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "position_m", _vector(self.position_m, 3, "position_m"))
        quat = _vector(self.quaternion_xyzw, 4, "quaternion_xyzw")
        if not isclose(sum(x*x for x in quat), 1.0, abs_tol=1e-6):
            raise ProtocolError("INVALID_SCHEMA", "EEF quaternion must be unit xyzw")
        object.__setattr__(self, "quaternion_xyzw", quat)


@dataclass(frozen=True)
class LayaRequest:
    request_id: str
    candidate_set: CandidateSet
    deadline_monotonic_ns: int
    structured_context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.request_id, "request_id")
        _ns(self.deadline_monotonic_ns, "deadline_monotonic_ns")
        if not (self.candidate_set.generated_monotonic_ns < self.deadline_monotonic_ns
                <= self.candidate_set.proposal_deadline_monotonic_ns):
            raise ProtocolError("INVALID_SCHEMA", "request cannot renew candidate deadline")
        canonical_json(self.structured_context)
        object.__setattr__(self, "structured_context", freeze(self.structured_context))

    @property
    def option_order(self) -> tuple[str, ...]:
        return self.candidate_set.allowed_ids


@dataclass(frozen=True)
class ActionProposal:
    request_id: str
    decision_id: str
    candidate_set_id: str
    candidate_hash: str
    identity: ContextIdentity
    source_snapshot_id: str
    selected_action_id: str
    probabilities_by_action: Mapping[str, float]
    model_revision: str
    inference_ms: float
    raw_confidence: float | None = None
    calibrated_confidence: float | None = None

    def __post_init__(self) -> None:
        for name in ("request_id", "decision_id", "candidate_set_id", "candidate_hash",
                     "source_snapshot_id", "selected_action_id", "model_revision"):
            _nonempty(getattr(self, name), name)
        _finite(self.inference_ms, "inference_ms")
        if self.inference_ms < 0:
            raise ProtocolError("INVALID_SCHEMA", "inference_ms must be nonnegative")
        for name in ("raw_confidence", "calibrated_confidence"):
            if getattr(self, name) is not None:
                _finite(getattr(self, name), name)
        if self.calibrated_confidence is not None and not 0 <= self.calibrated_confidence <= 1:
            raise ProtocolError("INVALID_SCHEMA", "calibrated_confidence outside [0,1]")
        for value in self.probabilities_by_action.values():
            _finite(value, "probability")
            if value < 0:
                raise ProtocolError("INVALID_OUTPUT", "negative probability")
        object.__setattr__(self, "probabilities_by_action", freeze(self.probabilities_by_action))


@dataclass(frozen=True)
class ValidationContext:
    identity: ContextIdentity
    snapshot_id: str
    lineage_source_ids: tuple[str, ...]
    geometry_valid: bool
    proprio_valid: bool
    semantics_unchanged: bool
    action_statuses: Mapping[str, str]
    measured_eef_pose: EefPose

    def __post_init__(self) -> None:
        _nonempty(self.snapshot_id, "snapshot_id")
        object.__setattr__(self, "lineage_source_ids", tuple(self.lineage_source_ids))
        for name in ("geometry_valid", "proprio_valid", "semantics_unchanged"):
            if type(getattr(self, name)) is not bool:
                raise ProtocolError("INVALID_SCHEMA", f"{name} must be bool")
        if set(self.action_statuses) - set(ACTION_IDS) or any(
            value not in EXECUTION_STATUSES for value in self.action_statuses.values()
        ):
            raise ProtocolError("INVALID_SCHEMA", "invalid current hard statuses")
        object.__setattr__(self, "action_statuses", freeze(self.action_statuses))


@dataclass(frozen=True)
class ActionContract:
    contract_id: str
    decision_id: str
    identity: ContextIdentity
    source_snapshot_id: str
    validated_snapshot_id: str
    action_id: str
    reference_frame: str
    delta_position_m: tuple[float, float, float]
    delta_rotation_rad: tuple[float, float, float]
    gripper_command: str
    target_eef_pose: EefPose
    issued_sim_time_s: float
    valid_until_sim_s: float
    issued_monotonic_ns: int
    expires_monotonic_ns: int
    controller_config_id: str
    requested_magnitude: float
    segment_magnitude: float
    remaining_requested_magnitude: float
    magnitude_unit: str

    def __post_init__(self) -> None:
        for name in ("contract_id", "decision_id", "source_snapshot_id", "validated_snapshot_id", "controller_config_id"):
            _nonempty(getattr(self, name), name)
        if self.reference_frame != REFERENCE_FRAME or self.action_id not in ACTION_IDS:
            raise ProtocolError("ACTION_SEMANTICS_CHANGED", "contract has unknown frame/action")
        position = _vector(self.delta_position_m, 3, "delta_position_m")
        rotation = _vector(self.delta_rotation_rad, 3, "delta_rotation_rad")
        object.__setattr__(self, "delta_position_m", position)
        object.__setattr__(self, "delta_rotation_rad", rotation)
        for name in ("issued_sim_time_s", "valid_until_sim_s", "requested_magnitude",
                     "segment_magnitude", "remaining_requested_magnitude"):
            _finite(getattr(self, name), name)
            if getattr(self, name) < 0:
                raise ProtocolError("INVALID_SCHEMA", f"{name} must be nonnegative")
        for name in ("issued_monotonic_ns", "expires_monotonic_ns"):
            _ns(getattr(self, name), name)
        sim_duration = self.valid_until_sim_s - self.issued_sim_time_s
        wall_duration = (self.expires_monotonic_ns - self.issued_monotonic_ns) / 1e9
        if not 0 < sim_duration <= MAX_SEGMENT_DURATION_S + 1e-12 or not 0 < wall_duration <= MAX_SEGMENT_DURATION_S:
            raise ProtocolError("INVALID_SCHEMA", "contract must have positive deadlines <=100ms")
        spec = action_spec(self.action_id)
        if self.gripper_command != spec.gripper_command:
            raise ProtocolError("ACTION_SEMANTICS_CHANGED", "gripper command differs from action")
        nominal = sqrt(sum(x*x for x in spec.nominal_delta))
        active = position if spec.primitive == "TRANSLATE" else rotation
        unit = "m" if spec.primitive == "TRANSLATE" else "rad" if spec.primitive == "ROTATE" else "none"
        cap = MAX_SEGMENT_TRANSLATION_M if unit == "m" else MAX_SEGMENT_ROTATION_RAD
        if unit == "none" and (any(position) or any(rotation)):
            raise ProtocolError("ACTION_SEMANTICS_CHANGED", "gripper/HOLD cannot move the EEF")
        if spec.primitive == "TRANSLATE" and any(rotation) or spec.primitive == "ROTATE" and any(position):
            raise ProtocolError("ACTION_SEMANTICS_CHANGED", "contract changed action category")
        magnitude = sqrt(sum(x*x for x in active))
        if nominal:
            if not 0 < magnitude <= min(nominal, cap) + 1e-12:
                raise ProtocolError("ACTION_SEMANTICS_CHANGED", "contract exceeds action segment bound")
            expected = tuple(x * magnitude / nominal for x in spec.nominal_delta)
            if any(not isclose(a, b, abs_tol=1e-12) for a, b in zip(active, expected)):
                raise ProtocolError("ACTION_SEMANTICS_CHANGED", "contract changed action direction")
        if self.magnitude_unit != unit or any(not isclose(a, b, abs_tol=1e-12) for a, b in (
            (self.requested_magnitude, nominal), (self.segment_magnitude, magnitude),
            (self.remaining_requested_magnitude, nominal - magnitude),
        )):
            raise ProtocolError("INVALID_SCHEMA", "requested/segment/remaining magnitude is inconsistent")
        if not isinstance(self.target_eef_pose, EefPose):
            raise ProtocolError("INVALID_SCHEMA", "contract needs validated EEF pose")

    def expired(self, *, sim_time_s: float, monotonic_ns: int) -> bool:
        return sim_time_s >= self.valid_until_sim_s or monotonic_ns >= self.expires_monotonic_ns

    @property
    def nominal_completion_status(self) -> str:
        """Expected geometric completion only; servo feedback must use measurements."""
        return "PARTIAL" if self.remaining_requested_magnitude > 1e-12 else "COMPLETED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_identity(expected: ContextIdentity, actual: ContextIdentity) -> None:
    if (expected.episode_id, expected.episode_generation) != (actual.episode_id, actual.episode_generation):
        raise ProtocolError("WRONG_EPISODE")
    if expected.goal_generation != actual.goal_generation:
        raise ProtocolError("WRONG_GOAL")
    if (expected.intent_id, expected.intent_generation) != (actual.intent_id, actual.intent_generation):
        raise ProtocolError("INTENT_REPLACED")
    if (expected.target_track_id, expected.target_track_generation) != (actual.target_track_id, actual.target_track_generation):
        raise ProtocolError("TARGET_LOST")
    if (expected.feature_id, expected.feature_generation) != (actual.feature_id, actual.feature_generation):
        raise ProtocolError("ACTION_SEMANTICS_CHANGED", "feature changed")
    if expected.calibration_versions != actual.calibration_versions:
        raise ProtocolError("CALIBRATION_CHANGED")


def validate_proposal(request: LayaRequest, proposal: ActionProposal, *, now_monotonic_ns: int) -> Candidate:
    _ns(now_monotonic_ns, "now_monotonic_ns")
    candidates = request.candidate_set
    if now_monotonic_ns >= request.deadline_monotonic_ns:
        raise ProtocolError("PROPOSAL_EXPIRED")
    if now_monotonic_ns < candidates.generated_monotonic_ns:
        raise ProtocolError("INVALID_CLOCK", "proposal precedes candidate generation")
    if proposal.request_id != request.request_id or proposal.candidate_set_id != candidates.candidate_set_id:
        raise ProtocolError("INVALID_OUTPUT", "request/candidate identity mismatch")
    if proposal.candidate_hash != candidates.candidate_hash:
        raise ProtocolError("CANDIDATE_HASH_MISMATCH")
    validate_identity(candidates.identity, proposal.identity)
    if proposal.source_snapshot_id != candidates.source_snapshot_id:
        raise ProtocolError("HISTORY_MISSING", "proposal source differs from request")
    selected = candidates.candidate(proposal.selected_action_id)
    if selected.execution_status != "ALLOWED":
        raise ProtocolError("ACTION_BLOCKED", selected.execution_status)
    if set(proposal.probabilities_by_action) != set(request.option_order):
        raise ProtocolError("INVALID_OUTPUT", "probabilities must cover exactly the ALLOWED IDs")
    if not isclose(sum(proposal.probabilities_by_action.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ProtocolError("INVALID_OUTPUT", "probabilities must sum to 1")
    return selected


def validate_latest(identity: ContextIdentity, source_snapshot_id: str, action_id: str,
                    latest: ValidationContext) -> None:
    validate_identity(identity, latest.identity)
    if latest.snapshot_id != source_snapshot_id and source_snapshot_id not in latest.lineage_source_ids:
        raise ProtocolError("HISTORY_MISSING", "no reliable lineage from original snapshot")
    if not latest.geometry_valid or not latest.proprio_valid:
        raise ProtocolError("SENSOR_INVALID")
    if not latest.semantics_unchanged:
        raise ProtocolError("ACTION_SEMANTICS_CHANGED")
    if latest.action_statuses.get(action_id, "UNKNOWN") != "ALLOWED":
        raise ProtocolError("ACTION_BLOCKED", "latest hard validation did not allow this action")


def _rotate_base(quaternion: tuple[float, ...], rotation: tuple[float, ...]) -> tuple[float, ...]:
    angle = sqrt(sum(x*x for x in rotation))
    if angle == 0:
        return quaternion
    factor = sin(angle / 2) / angle
    ax, ay, az = (x * factor for x in rotation)
    aw = cos(angle / 2)
    bx, by, bz, bw = quaternion
    # Left multiplication applies a robot-base rotation, not a tool-frame one.
    return (aw*bx + ax*bw + ay*bz - az*by,
            aw*by - ax*bz + ay*bw + az*bx,
            aw*bz + ax*by - ay*bx + az*bw,
            aw*bw - ax*bx - ay*by - az*bz)


def instantiate_contract(
    request: LayaRequest, proposal: ActionProposal, *, latest: ValidationContext,
    contract_id: str, now_sim_time_s: float, now_monotonic_ns: int,
    controller_config_id: str, contact: bool = False,
    contact_translation_limit_m: float = MAX_CONTACT_TRANSLATION_M,
    segment_translation_limit_m: float = MAX_SEGMENT_TRANSLATION_M,
    segment_rotation_limit_rad: float = MAX_SEGMENT_ROTATION_RAD,
    segment_duration_s: float = MAX_SEGMENT_DURATION_S,
) -> ActionContract:
    """No action substitution and no continuation authorization are possible here."""
    candidate = validate_proposal(request, proposal, now_monotonic_ns=now_monotonic_ns)
    validate_latest(proposal.identity, proposal.source_snapshot_id, candidate.id, latest)
    _nonempty(contract_id, "contract_id")
    _nonempty(controller_config_id, "controller_config_id")
    _finite(now_sim_time_s, "now_sim_time_s")
    _finite(segment_duration_s, "segment_duration_s")
    _finite(contact_translation_limit_m, "contact_translation_limit_m")
    _finite(segment_translation_limit_m, "segment_translation_limit_m")
    _finite(segment_rotation_limit_rad, "segment_rotation_limit_rad")
    if type(contact) is not bool:
        raise ProtocolError("INVALID_SCHEMA", "contact must be bool")
    if now_sim_time_s < 0 or not 0 < segment_duration_s <= MAX_SEGMENT_DURATION_S:
        raise ProtocolError("INVALID_SCHEMA", "invalid segment duration/sim time")
    if not 0.001 <= contact_translation_limit_m <= MAX_CONTACT_TRANSLATION_M:
        raise ProtocolError("INVALID_SCHEMA", "contact translation limit must be 1–2 mm")
    if not 0 < segment_translation_limit_m <= MAX_SEGMENT_TRANSLATION_M:
        raise ProtocolError("INVALID_SCHEMA", "translation segment limit must be positive and <=5 mm")
    if not 0 < segment_rotation_limit_rad <= MAX_SEGMENT_ROTATION_RAD:
        raise ProtocolError("INVALID_SCHEMA", "rotation segment limit must be positive and <=2 degrees")
    spec = candidate.spec
    nominal = sqrt(sum(x*x for x in spec.nominal_delta))
    position = (0.0, 0.0, 0.0)
    rotation = (0.0, 0.0, 0.0)
    segment = nominal
    unit = "none"
    if spec.primitive == "TRANSLATE":
        translation_cap = min(segment_translation_limit_m, contact_translation_limit_m) if contact else segment_translation_limit_m
        segment = min(nominal, translation_cap)
        position = tuple(x * segment / nominal for x in spec.nominal_delta)
        unit = "m"
    elif spec.primitive == "ROTATE":
        segment = min(nominal, segment_rotation_limit_rad)
        rotation = tuple(x * segment / nominal for x in spec.nominal_delta)
        unit = "rad"
    target = EefPose(
        tuple(x + dx for x, dx in zip(latest.measured_eef_pose.position_m, position)),
        _rotate_base(latest.measured_eef_pose.quaternion_xyzw, rotation),
    )
    # Conservative: a segment cannot outlive the request that authorized it.
    expires = min(request.deadline_monotonic_ns,
                  now_monotonic_ns + round(segment_duration_s * 1_000_000_000))
    duration = min(segment_duration_s, (expires - now_monotonic_ns) / 1_000_000_000)
    return ActionContract(
        contract_id, proposal.decision_id, proposal.identity, proposal.source_snapshot_id,
        latest.snapshot_id, spec.id, REFERENCE_FRAME, position, rotation, spec.gripper_command,
        target, now_sim_time_s, now_sim_time_s + duration, now_monotonic_ns, expires,
        controller_config_id, nominal, segment, max(0.0, nominal - segment), unit,
    )
