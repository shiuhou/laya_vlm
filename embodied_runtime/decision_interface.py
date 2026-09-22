"""Compact decision evidence, independent of temporal storage and simulator APIs.

v0.1 is a research interface, not a claim of sufficient state or safe control.
Audit identities are not model features. Unknown is None, never an oracle fill.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from typing import Any

import numpy as np

from .adapters.physics_preview import assert_visual_snapshot
from .runtime_core import MOVE, Candidate, _sha256_json

STATE_VERSION = "canonical-decision-state-v0.1"
EFFECT_VERSION = "candidate-effects-v0.1"
FIELD_NAMES = (
    "task.instruction", "task.target_identity", "robot.tcp_position_m",
    "robot.gripper_width_m", "robot.gripper_command", "target.position_m",
    "target.position_definition", "target.velocity_mps", "target.visible_now",
    "relations.tcp_target_delta_m", "relations.distance_m", "relations.xy_error_m",
    "relations.height_error_m", "interaction.target_contact", "interaction.holding",
    "progress.remaining_open_mm", "quality.geometry_age_s", "quality.geometry_valid",
    "quality.position_covariance_m2", "quality.covariance_calibrated",
    "quality.semantic_age_s", "quality.semantic_valid", "quality.semantic_confidence",
    "quality.temporal_consistency_ok",
)


@dataclass(frozen=True)
class Evidence:
    value: Any = None
    source: str = "unknown"
    basis: str = "unavailable"
    privileged: bool = False

    def __post_init__(self):
        if self.source not in {"unknown", "sensor", "proprioception", "task", "derived", "oracle_sim"}:
            raise ValueError("unsupported evidence source")
        if (self.source == "unknown") != (self.value is None):
            raise ValueError("unknown evidence must be explicit None")
        if self.source == "oracle_sim" and not self.privileged:
            raise ValueError("oracle evidence must carry privilege")
        _sha256_json(asdict(self))  # reject non-JSON/nonfinite evidence


def evidence(value, source, basis, privileged=False):
    return Evidence(basis=basis) if value is None else Evidence(deepcopy(value), source, basis, privileged)


@dataclass(frozen=True)
class CanonicalDecisionState:
    fields: dict[str, Evidence]
    meta: dict = field(default_factory=dict)
    version: str = STATE_VERSION

    def __post_init__(self):
        if self.version != STATE_VERSION or set(self.fields) != set(FIELD_NAMES):
            raise ValueError("canonical state schema mismatch")
        for key in ("robot.tcp_position_m", "target.position_m", "target.velocity_mps", "relations.tcp_target_delta_m"):
            value = self.fields[key].value
            if value is not None and np.asarray(value).shape != (3,):
                raise ValueError(f"{key} must have three world coordinates")
        covariance = self.fields["quality.position_covariance_m2"].value
        if covariance is not None:
            matrix = np.asarray(covariance)
            if matrix.shape != (3, 3) or not np.allclose(matrix, matrix.T) or np.linalg.eigvalsh(matrix).min() < 0:
                raise ValueError("invalid position covariance")

    @property
    def privileged(self):
        return any(value.privileged for value in self.fields.values())

    def model_state(self):
        return {"version": self.version, "fields": {k: asdict(v) for k, v in self.fields.items()}}

    def identity(self):
        return _sha256_json(asdict(self))

    def intervene(self, replacements: dict[str, Evidence], *, label: str):
        """Literal intervention: relations are NOT silently recomputed.

        Replace a whole family for a coherent position intervention, or retain
        inconsistent fields deliberately for a labeled counterfactual test.
        """
        if not label or set(replacements) - set(self.fields):
            raise ValueError("named intervention with known fields required")
        return replace(self, fields={**deepcopy(self.fields), **deepcopy(replacements)},
                       meta={**self.meta, "intervention": {"parent_id": self.identity(), "label": label,
                                                          "replaced_fields": sorted(replacements)}})

    @classmethod
    def from_dict(cls, data):
        return cls(**{**data, "fields": {k: Evidence(**v) for k, v in data["fields"].items()}})


def derive_relations(fields):
    tcp, target = fields["robot.tcp_position_m"], fields["target.position_m"]
    if tcp.value is None or target.value is None:
        return
    delta = np.asarray(target.value) - tcp.value
    for name, value in {"tcp_target_delta_m": delta.tolist(), "distance_m": float(np.linalg.norm(delta)),
                        "xy_error_m": float(np.linalg.norm(delta[:2])), "height_error_m": float(delta[2])}.items():
        fields[f"relations.{name}"] = evidence(value, "derived", "target.position_m - robot.tcp_position_m; world axes",
                                               target.privileged or tcp.privileged)


def project_belief(snapshot, target_track: str):
    """Pure perceptual projection: no world/backend or oracle argument exists."""
    assert_visual_snapshot(snapshot)
    f = {key: Evidence() for key in FIELD_NAMES}
    values, validity = snapshot.continuous, snapshot.validity.get(target_track, {})
    f["task.instruction"] = evidence(snapshot.goal.get("instruction"), "task", "provided task context")
    f["task.target_identity"] = evidence(target_track, "task", "query identity; tracking inactive")
    for dest, key in (("tcp_position_m", "tcp_pos_world_m"), ("gripper_width_m", "gripper_width_m"),
                      ("gripper_command", "gripper_command")):
        f[f"robot.{dest}"] = evidence(values.get(key), "proprioception", "robot observation / retained command")
    f["interaction.holding"] = evidence(values.get("holding"), "proprioception", "holding sensor; closed command is not holding")
    for dest, suffix in (("position_m", "position_world_m"), ("velocity_mps", "velocity_mps")):
        f[f"target.{dest}"] = evidence(values.get(f"vision:{target_track}:{suffix}"), "sensor", "capture-time RGB-D fusion")
    if f["target.position_m"].value is not None:
        f["target.position_definition"] = evidence("query_box_center_with_interior_median_depth", "sensor", "LocateAnything RGB-D v1")
    # A historic detection does not establish current visibility or contact.
    for dest, key in (("geometry_age_s", "geometry_age_s"), ("geometry_valid", "geometry_valid"),
                      ("position_covariance_m2", "position_covariance"), ("semantic_age_s", "semantic_age_s"),
                      ("semantic_valid", "semantic_valid"), ("temporal_consistency_ok", "temporal_consistency_ok")):
        f[f"quality.{dest}"] = evidence(validity.get(key), "sensor", "temporal belief validity")
    provenance = validity.get("provenance", [])
    calibrated = [p.get("position_covariance_calibrated") for p in provenance if p.get("position_world_m") is not None]
    f["quality.covariance_calibrated"] = evidence(all(calibrated) if calibrated and None not in calibrated else None,
                                                  "sensor", "input covariance provenance; not posterior coverage")
    probs = snapshot.semantic.get(target_track)
    f["quality.semantic_confidence"] = evidence(max((v for k, v in probs.items() if k != "unknown"), default=0.) if probs else None,
                                                "sensor", "semantic evidence score; not calibrated probability")
    derive_relations(f)
    state = CanonicalDecisionState(f, {"branch": "perceptual", "belief_id": snapshot.belief_id(),
                                       "revision": snapshot.revision, "asof_sim_time": snapshot.asof_sim_time,
                                       "tracking_active": False})
    if state.privileged:
        raise ValueError("privileged perceptual projection")
    return state


def project_oracle(perceptual: CanonicalDecisionState, oracle: dict):
    """Diagnostic-only enrichment; robot/task inputs are held exactly matched."""
    f = deepcopy(perceptual.fields)
    # No confidence/covariance is invented for a simulator reading. Exact reading
    # is not a calibrated visual measurement, and visibility is still unknown.
    for key in FIELD_NAMES:
        if key.startswith(("target.", "relations.", "interaction.", "progress.", "quality.")):
            f[key] = Evidence()
    f["interaction.holding"] = perceptual.fields["interaction.holding"]
    for key, value in {"target.position_m": oracle.get("target_position_m"),
                       "target.position_definition": oracle.get("position_definition"),
                       "interaction.target_contact": oracle.get("moving_contact"),
                       "progress.remaining_open_mm": oracle.get("remaining_open_mm"),
                       "quality.geometry_age_s": 0. if oracle.get("target_position_m") is not None else None,
                       "quality.geometry_valid": oracle.get("target_position_m") is not None}.items():
        f[key] = evidence(value, "oracle_sim", "current simulator evaluator", True)
    derive_relations(f)
    return CanonicalDecisionState(f, {**perceptual.meta, "branch": "oracle", "oracle_source": oracle["source_id"]})


def shared_atomic_candidates():
    """Offline probe vocabulary, NOT execution authorization or safety filtering."""
    candidates = [Candidate(k, f"translate 0.01 m along world direction {v}; retain gripper command") for k, v in MOVE.items()]
    candidates.extend(Candidate(k, description) for k, description in (
        ("ROTATE_CW", "rotate -10 degrees about world Z; retain gripper command"),
        ("ROTATE_CCW", "rotate +10 degrees about world Z; retain gripper command"),
        ("STOP", "hold pose and retained gripper command; simulation continues"),
        ("GRASP", "close gripper; hold pose; grasp success not guaranteed"),
        ("RELEASE", "open gripper; hold pose")))
    return tuple(candidates)


@dataclass(frozen=True)
class CandidateEffectBundle:
    candidate_set_id: str
    effects: dict = field(default_factory=dict)
    version: str = EFFECT_VERSION

    def __post_init__(self):
        if self.version != EFFECT_VERSION:
            raise ValueError("effect version mismatch")
        for effect in self.effects.values():
            if effect["source"] not in {"geometry", "oracle_sim", "learned", "unknown"}:
                raise ValueError("invalid effect source")
            if effect["source"] == "oracle_sim" and not effect["privileged"]:
                raise ValueError("oracle effects must carry privilege")
        _sha256_json(asdict(self))

    @property
    def privileged(self):
        return any(e["privileged"] for e in self.effects.values())

    def identity(self):
        return _sha256_json(asdict(self))


def candidate_id(candidates):
    return _sha256_json({"candidates": [c.canonical() for c in candidates]})


def geometric_effects(state, candidates):
    """Tier 0: stationary target / exact nominal displacement, not dynamics."""
    effects = {}
    delta = state.fields["relations.tcp_target_delta_m"]
    for c in candidates:
        if c.token not in MOVE or delta.value is None:
            effects[c.token] = {"source": "unknown", "privileged": False, "values": {}}
            continue
        before = np.asarray(delta.value)
        after = before - np.asarray(MOVE[c.token]) * .01
        effects[c.token] = {"source": "geometry", "privileged": delta.privileged,
                            "assumptions": "stationary target; nominal 10 mm world translation; no contact/dynamics",
                            "state_id": state.identity(), "geometry_valid": state.fields["quality.geometry_valid"].value,
                            "values": {"distance_change_m": float(np.linalg.norm(after) - np.linalg.norm(before)),
                                       "xy_error_change_m": float(np.linalg.norm(after[:2]) - np.linalg.norm(before[:2]))}}
    return CandidateEffectBundle(candidate_id(candidates), effects)


def oracle_effects(candidates, predictions):
    from .adapters.physics_preview import TOKEN_TO_JEV
    effects = {}
    for c in candidates:
        p = predictions.get(TOKEN_TO_JEV[c.token])
        if p is None:
            effects[c.token] = {"source": "unknown", "privileged": False, "values": {}}
        else:
            effects[c.token] = {"source": "oracle_sim", "privileged": True,
                               "values": {"closing_mm": p.get("closing_mm"),
                                          "surface_gap_reduction_mm": p.get("geometry_approach_mm"),
                                          "target_contact": p.get("after", {}).get("moving_contact"),
                                          "peak_obstacle_force_N": p.get("peak_obstacle_force_N")}}
    return CandidateEffectBundle(candidate_id(candidates), effects)


@dataclass(frozen=True)
class CanonicalDecisionInput:
    state: CanonicalDecisionState
    candidates: tuple[Candidate, ...]
    effects: CandidateEffectBundle
    history: tuple = ()
    diagnostic_only: bool = False

    def __post_init__(self):
        if len({c.token for c in self.candidates}) != len(self.candidates):
            raise ValueError("duplicate candidate identity")
        if any(c.metadata for c in self.candidates):
            raise ValueError("canonical candidates must not embed state/effect metadata; use the effect bundle")
        # v0.1 supports semantics-only offline probes. Legacy oracle builders
        # encode preview effects in free text/risk, not just metadata.
        semantics = {c.token: c.canonical() for c in shared_atomic_candidates()}
        if any(c.canonical() != semantics.get(c.token) for c in self.candidates):
            raise ValueError("canonical v0.1 requires shared semantics-only probe candidates")
        if self.effects.candidate_set_id != self.candidate_set_id() or set(self.effects.effects) - {c.token for c in self.candidates}:
            raise ValueError("effects refer to different candidates")
        if (self.state.privileged or self.effects.privileged) and not self.diagnostic_only:
            raise ValueError("privileged input forbidden outside diagnostics")
        if len(self.history) > 1:
            raise ValueError("v0.1 history is one previous actual outcome")
        # Prevent an arbitrary raw execution/object-state payload entering history.
        for item in self.history:
            if set(item) - {"action", "tcp_delta_m", "elapsed_sim_s", "gripper_command", "source"}:
                raise ValueError("unsupported recent outcome")
            if item.get("source") != "proprioception":
                raise ValueError("recent outcomes must be shared proprioception")

    @property
    def revision(self):
        return self.state.meta["revision"]

    @property
    def asof_sim_time(self):
        return self.state.meta["asof_sim_time"]

    def allowed(self):
        return {c.token for c in self.candidates if c.feasible}

    def belief_id(self):
        return self.state.identity()

    def candidate_set_id(self):
        return candidate_id(self.candidates)

    def snapshot_id(self):
        return _sha256_json({"state_id": self.state.identity(), "candidates": self.candidate_set_id(),
                             "effects": self.effects.identity(), "history": self.history,
                             "question": self.questions(), "diagnostic_only": self.diagnostic_only})

    def provider_input(self):
        # Audit IDs, collection phase, branch label, and source file paths are not
        # model features. Evidence sources/quality are intentional state fields.
        effects = deepcopy(self.effects.effects)
        for effect in effects.values():
            effect.pop("state_id", None)
        return {"decision_state": self.state.model_state(),
                "candidates": [c.canonical() for c in self.candidates],
                "candidate_effects": effects, "recent_actual_outcomes": deepcopy(self.history)}

    def questions(self):
        return {"action": {"type": "choice", "instructions":
                "Choose one listed atomic action for the task. This is an offline decision probe, not execution authorization. "
                "Unknown fields provide no evidence. Do not assume contact, task progress or unprovided effects.",
                "criteria": {c.token: c.description for c in self.candidates if c.feasible}}}

    def rule_token(self):
        delta = self.state.fields["relations.tcp_target_delta_m"].value
        if delta is None or self.state.fields["quality.geometry_valid"].value is not True:
            return "STOP"
        distances = [(float(np.linalg.norm(np.asarray(delta) - np.asarray(MOVE[c.token]) * .01)), c.token)
                     for c in self.candidates if c.feasible and c.token in MOVE]
        return min(distances)[1] if distances and min(distances)[0] < np.linalg.norm(delta) else "STOP"
