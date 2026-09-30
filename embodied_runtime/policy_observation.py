"""Explicit model-facing projection for the new sensor-only decision path.

Legacy privileged prompts are intentionally not accepted. This is an interface
boundary, not a sandbox against malicious Python reflection; callers inject only
sensor capabilities, never a simulator world object.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import Any

from .contracts import ProtocolError, freeze, thaw
from .sensor_api import Proprioception, _finite, _vector


FORBIDDEN_FIELDS = frozenset({
    "world", "features", "predict_all", "oracle", "oracle_state", "oracle_branch",
    "official_success", "success", "goal", "satisfied", "goal_satisfied",
    "object_pose", "object_pose_world", "target_body_pose", "target_geom_pose",
    "target_site_pose", "target_joint", "target_joint_position", "joint_axis",
    "true_joint_axis", "segmentation", "object_id_segmentation", "contacts",
    "contact_list", "contact_identity", "body_id", "geom_id", "site_id",
    "target_contact", "obstacle_contact", "closure_mm", "drawer_opening_mm",
    "effect_source_oracle", "privileged",
})
ALLOWED_PROVENANCE = frozenset({
    "sensor-derived", "sensor_derived", "proprioceptive", "deterministic_geometry",
    "learned_estimate", "unknown",
})
POLICY_FIELDS = frozenset({
    "request_id", "intent_id", "intent_generation", "candidate_set_id", "candidate_hash",
    "source_snapshot_id", "target_track_id", "target_track_generation", "feature_id",
    "feature_generation", "stage", "operation", "relative_error", "geometry_age",
    "quality", "covariance_summary", "proprio", "recent_feedback", "candidates",
    "deadline_monotonic_ns",
})
CANDIDATE_FIELDS = frozenset({
    "id", "primitive", "reference_frame", "nominal_delta", "execution_status",
    "hard_reason_codes", "geometric_effect_estimate", "max_segment_duration_s", "gripper_command",
    "max_segment_translation_m", "max_segment_rotation_rad",
})
EFFECT_FIELDS = frozenset({
    "delta_position_m", "delta_rotation_rad", "predicted_error_m", "error_reduction_m", "progress_m",
    "effect_source", "provenance", "valid", "reason_codes", "uncertainty_m",
})
FEEDBACK_FIELDS = frozenset({
    "contract_id", "decision_id", "status", "started_sim_time_s", "finished_sim_time_s",
    "started_monotonic_ns", "finished_monotonic_ns", "measured_eef_delta_m",
    "measured_gripper_state", "remaining_requested_magnitude", "reason_codes",
})
GRIPPER_FEEDBACK_FIELDS = frozenset({
    "gripper_width_m", "gripper_width_calibration_id", "gripper_joint_position_rad",
    "gripper_command", "valid", "reason_codes", "source_ids", "holding",
})
QUALITY_FIELDS = frozenset({
    "status", "support_ratio", "edge_margin_m", "plane_residual_m", "reason_codes",
    "geometry_valid", "semantic_binding_valid", "calibrated_confidence",
    "confidence_calibration_id",
})
COVARIANCE_FIELDS = frozenset({
    "position_covariance_m2", "normal_covariance", "position_std_m", "normal_std_rad",
    "calibrated", "source", "reason_codes",
})


def assert_sensor_only(value: Any, *, path: str = "policy") -> None:
    """Defense in depth against oracle payloads and mislabeled effect sources."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ProtocolError("INVALID_SCHEMA", f"non-string key at {path}")
            if key in FORBIDDEN_FIELDS or key.startswith("oracle_"):
                raise ProtocolError("INFORMATION_BOUNDARY", f"forbidden field {path}.{key}")
            if key in {"provenance", "effect_source"} and (not isinstance(child, str)
                    or child not in ALLOWED_PROVENANCE):
                raise ProtocolError("INFORMATION_BOUNDARY", f"unapproved source at {path}.{key}")
            if key == "holding" and child is not None:
                raise ProtocolError("INFORMATION_BOUNDARY", "holding needs a separate sensor relation")
            assert_sensor_only(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            assert_sensor_only(child, path=f"{path}[{i}]")
    elif isinstance(value, str) and value in {"oracle_sim", "simulator_oracle", "oracle"}:
        raise ProtocolError("INFORMATION_BOUNDARY", f"oracle source at {path}")
    elif isinstance(value, float) and not isfinite(value):
        raise ProtocolError("INVALID_SCHEMA", f"non-finite value at {path}")


def _keys(value: Any, allowed: frozenset[str], name: str) -> None:
    if not isinstance(value, Mapping):
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be an object")
    extra = set(value) - allowed
    if extra:
        raise ProtocolError("INFORMATION_BOUNDARY", f"unlisted {name} fields: {sorted(extra)}")


def project_candidate(candidate, *, synthetic_condition: bool = False) -> dict[str, Any]:
    """Project a validated candidate, retaining its full raw evidence elsewhere.

    HardEvidence is already validated by its own type. It stays in CandidateSet
    evidence/hash; the model receives canonical action semantics, hard status and
    reason codes, and geometric effects. Synthetic hard evidence is allowed only
    for an explicitly declared P0 condition, never by default.
    """
    from .control.local_candidates import Candidate
    if not isinstance(candidate, Candidate):
        raise ProtocolError("INVALID_SCHEMA", "projection needs a validated Candidate")
    if candidate.hard_evidence.provenance == "synthetic" and not synthetic_condition:
        raise ProtocolError("INFORMATION_BOUNDARY", "synthetic evidence requires declared P0 condition")
    raw = candidate.to_dict()
    _keys(raw, CANDIDATE_FIELDS | {"hard_evidence"}, "raw candidate")
    projected = {key: value for key, value in raw.items() if key != "hard_evidence"}
    assert_sensor_only(projected)
    return projected


@dataclass(frozen=True)
class PolicyObservation:
    payload: Mapping[str, Any]

    def __post_init__(self):
        _keys(self.payload, POLICY_FIELDS, "policy")
        payload = dict(self.payload)
        if "proprio" not in payload or "source_snapshot_id" not in payload:
            raise ProtocolError("INVALID_SCHEMA", "policy needs proprioception and source snapshot")
        proprio = payload["proprio"]
        if not isinstance(proprio, Proprioception):
            proprio = Proprioception.from_mapping(proprio)
        payload["proprio"] = proprio.to_dict()
        if not isinstance(payload["source_snapshot_id"], str) or not payload["source_snapshot_id"]:
            raise ProtocolError("INVALID_SCHEMA", "source snapshot identity required")
        if payload.get("relative_error") is not None:
            _vector(payload["relative_error"], "relative_error", 3)
        if payload.get("geometry_age") is not None:
            _finite(payload["geometry_age"], "geometry_age", nonnegative=True)
        for name in ("request_id", "intent_id", "candidate_set_id", "candidate_hash", "target_track_id",
                     "feature_id", "operation"):
            if name in payload and (not isinstance(payload[name], str) or not payload[name]):
                raise ProtocolError("INVALID_SCHEMA", f"invalid {name}")
        for name in ("intent_generation", "target_track_generation", "feature_generation", "deadline_monotonic_ns"):
            if name in payload and (type(payload[name]) is not int or payload[name] < 0):
                raise ProtocolError("INVALID_SCHEMA", f"invalid {name}")
        if "stage" in payload and payload["stage"] not in {
                "OBSERVE", "APPROACH", "ALIGN", "INTERACT", "RETREAT", "VERIFY"}:
            raise ProtocolError("INVALID_SCHEMA", "unknown stage")
        for name, allowed in (("quality", QUALITY_FIELDS), ("covariance_summary", COVARIANCE_FIELDS)):
            if payload.get(name) is not None:
                _keys(payload[name], allowed, name)
        quality = payload.get("quality") or {}
        confidence = quality.get("calibrated_confidence")
        if confidence is not None and (not quality.get("confidence_calibration_id")
                or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1):
            raise ProtocolError("INVALID_SCHEMA", "calibrated confidence requires provenance")
        feedback = payload.get("recent_feedback")
        if feedback is not None:
            _keys(feedback, FEEDBACK_FIELDS, "feedback")
            if feedback.get("measured_gripper_state") is not None:
                _keys(feedback["measured_gripper_state"], GRIPPER_FEEDBACK_FIELDS, "gripper feedback")
        if "candidates" in payload:
            if not isinstance(payload["candidates"], (list, tuple)):
                raise ProtocolError("INVALID_SCHEMA", "candidates must be a sequence")
            for candidate in payload["candidates"]:
                _keys(candidate, CANDIDATE_FIELDS, "candidate")
                if candidate.get("reference_frame") != "robot_base":
                    raise ProtocolError("INVALID_SCHEMA", "candidate frame must be robot_base")
                effect = candidate.get("geometric_effect_estimate")
                if effect is not None:
                    _keys(effect, EFFECT_FIELDS, "geometric effect")
                    for key in ("delta_position_m", "delta_rotation_rad", "predicted_error_m"):
                        if effect.get(key) is not None:
                            _vector(effect[key], key, 3)
                    for key in ("error_reduction_m", "progress_m", "uncertainty_m"):
                        if effect.get(key) is not None:
                            _finite(effect[key], key)

                nominal = candidate.get("nominal_delta")
                if isinstance(nominal, Mapping):
                    _keys(nominal, frozenset({"delta_position_m", "delta_rotation_rad", "gripper_command"}),
                          "nominal delta")
                elif nominal is not None:
                    _vector(nominal, "nominal_delta", 3)
        assert_sensor_only(payload)
        object.__setattr__(self, "payload", freeze(payload))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> PolicyObservation:
        return cls(value)

    def to_dict(self) -> dict[str, Any]:
        return thaw(self.payload)
