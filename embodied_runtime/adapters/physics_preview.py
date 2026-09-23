"""Jev-LIBERO physics preview candidates for the Laya decision layer."""
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

from ..runtime_core import DESCRIPTIONS, MOVE, Candidate

TOKEN_TO_JEV = {
    "MV_FWD": "x+10mm", "MV_BACK": "x-10mm",
    "MV_LEFT": "y+10mm", "MV_RIGHT": "y-10mm",
    "MV_UP": "z+10mm", "MV_DOWN": "z-10mm",
    "ROTATE_CW": "rotate_z-10deg", "ROTATE_CCW": "rotate_z+10deg",
    "GRASP": "close", "RELEASE": "open", "STOP": "hold",
}


class PhysicsPreviewCandidateBuilder:
    """Run Jev's reversible one-step predictions and expose only feasible tokens."""

    def __init__(self, world: Any, *, collision_aware: bool = True, grip_command=None,
                 action_map=None):
        self.version = "physics-preview-candidates-v1"
        self.oracle = True
        self.tracking_active = False
        self.world = world
        self.grip_command = grip_command
        self.collision_aware = collision_aware
        # Explicit mappings opt into a native vocabulary without legacy STOP/DONE
        # additions. Callers own empty-set handling; no synthetic alternatives.
        self.action_map = dict(TOKEN_TO_JEV if action_map is None else action_map)
        self.legacy_vocabulary = action_map is None
        self.last_preview: dict[str, Any] | None = None

    def build(self, belief):
        from jev_libero.policy import contracts

        grip = self.grip_command() if self.grip_command else -1.0
        before, predictions = self.world.predict_all(grip)
        pools, rejected = contracts(before, predictions, collision_aware=self.collision_aware, task_config=self.world.config)
        eligible = {name for pool in pools.values() for name in pool}
        by_token: dict[str, list[str]] = {}
        for token, action in self.action_map.items():
            by_token.setdefault(action, []).append(token)
        candidates = []
        for token, action in self.action_map.items():
            p = predictions.get(action)
            reasons = []
            feasible = action in eligible
            if not feasible:
                reasons.append(rejected.get(action, "no_feasible_contract"))
            description = DESCRIPTIONS.get(token, token.lower().replace("_", " "))
            if p is not None:
                after = p.get("after", {})
                description = (
                    f"{description}; predicted task_success={bool(after.get('success'))}, "
                    f"target_contact={bool(after.get('moving_contact'))}, "
                    f"approach_mm={float(p.get('geometry_approach_mm', 0.0)):.2f}, "
                    f"obstacle_peak_N={float(p.get('peak_obstacle_force_N', 0.0)):.2f}"
                )
            risk = min(1.0, float(p.get("peak_obstacle_force_N", 0.0)) / 20.0) if p else 1.0
            candidates.append(Candidate(token, description, feasible, tuple(reasons), risk))
        if self.legacy_vocabulary and before.get("success"):
            candidates.append(Candidate("DONE", "finish only after the real LIBERO success predicate is true", True))
        if self.legacy_vocabulary and not any(c.feasible for c in candidates):
            candidates.append(Candidate("STOP", "hold because no physics-preview candidate satisfies the task contract", True, ("no_feasible_candidate",), 0.0))
        self.last_preview = {"before": before, "predictions": predictions, "pools": pools, "rejected": rejected}
        self.last_diagnostics = {
            "builder_version": self.version, "oracle": True,
            "privileged_state_used": True, "tracking_active": self.tracking_active,
            "candidate_count": len(candidates),
            "candidate_veto_count": sum(not c.feasible for c in candidates),
            "veto_reason_histogram": dict(Counter(reason for c in candidates for reason in c.reason_codes)),
        }
        return tuple(candidates)


class VisionCandidateBuilder:
    """State-dependent validity layer for non-oracle visual experiments.

    Geometry and robot proprioception are used for hard validity. Direction,
    alignment, uncertainty and age are attached as soft evidence; this builder
    never chooses a preferred action.
    """

    VERSION = "vision-candidates-v1"
    oracle = False

    def __init__(self, *, target_track: str | None = None, include_gripper: bool = True,
                 step_m: float = 0.01, closed_width_m: float = 0.03,
                 allow_unverified_covariance: bool = False,
                 workspace_bounds_m: tuple[tuple[float, float], ...] | None = None):
        self.version = self.VERSION
        self.target_track = target_track
        self.include_gripper = include_gripper
        self.step_m = float(step_m)
        self.closed_width_m = float(closed_width_m)
        self.allow_unverified_covariance = bool(allow_unverified_covariance)
        self.workspace_bounds_m = workspace_bounds_m
        self.last_preview = None
        self.last_diagnostics = {}
        if not np.isfinite(self.step_m) or self.step_m <= 0 or not np.isfinite(self.closed_width_m) or self.closed_width_m <= 0:
            raise ValueError("candidate scales must be finite and positive")
        if workspace_bounds_m is not None:
            bounds = np.asarray(workspace_bounds_m, dtype=float)
            if bounds.shape != (3, 2) or not np.isfinite(bounds).all() or np.any(bounds[:, 0] >= bounds[:, 1]):
                raise ValueError("workspace bounds must be three finite increasing pairs")

    def resolved_config(self):
        return {"version": self.version, "target_track": self.target_track,
                "include_gripper": self.include_gripper, "step_m": self.step_m,
                "closed_width_m": self.closed_width_m,
                "allow_unverified_covariance": self.allow_unverified_covariance,
                "workspace_bounds_m": self.workspace_bounds_m}

    def _track(self, belief):
        if self.target_track:
            return self.target_track
        if len(belief.validity) == 1:
            return next(iter(belief.validity))
        tracks = [key[len("vision:"):-len(":position_world_m")] for key in belief.continuous if key.startswith("vision:") and key.endswith(":position_world_m")]
        return tracks[0] if len(tracks) == 1 else self.target_track

    def _evidence(self, belief):
        track = self._track(belief)
        validity = dict(belief.validity.get(track, {})) if track else {}
        position = belief.continuous.get(f"vision:{track}:position_world_m") if track else None
        covariance = validity.get("position_covariance")
        semantic = dict(belief.semantic.get(track, {})) if track else {}
        if position is not None:
            position = np.asarray(position, dtype=float).reshape(3)
        if covariance is not None:
            covariance = np.asarray(covariance, dtype=float).reshape(3, 3)
        return track, validity, position, covariance, semantic

    def _geometry_reasons(self, validity, position, covariance):
        original_reasons = list(validity.get("geometry_invalid_reasons", ()))
        reasons = list(original_reasons)
        if position is None:
            reasons.append("geometry_missing")
        elif not np.isfinite(position).all():
            reasons.append("geometry_nonfinite")
        if covariance is None:
            reasons.append("geometry_covariance_missing")
        elif not np.isfinite(covariance).all() or np.linalg.eigvalsh(covariance).min() <= 0:
            reasons.append("geometry_covariance_invalid")
        if self.allow_unverified_covariance:
            reasons = [reason for reason in reasons if reason != "measurement_covariance_unverified"]
        only_unverified = original_reasons and set(original_reasons) <= {"measurement_covariance_unverified"}
        if not validity.get("geometry_valid", False) and not (self.allow_unverified_covariance and only_unverified):
            reasons.extend(reason for reason in ("geometry_invalid",) if reason not in reasons)
        return tuple(dict.fromkeys(reasons))

    def _metadata(self, token, belief, track, validity, position, covariance, semantic):
        tcp = belief.continuous.get("tcp_pos_world_m")
        tcp = None if tcp is None else np.asarray(tcp, dtype=float).reshape(3)
        direction = np.asarray(MOVE[token], dtype=float) if token in MOVE else None
        target_vector = None if position is None or tcp is None else position - tcp
        norm = None if target_vector is None else float(np.linalg.norm(target_vector))
        cosine = None if direction is None or not norm else float(direction @ target_vector / norm)
        trace = None if covariance is None else float(np.trace(covariance))
        return {
            "builder_version": self.version, "belief_revision": belief.revision,
            "target_track": track, "tracking_active": False,
            "geometry_age_s": validity.get("geometry_age_s"),
            "geometry_valid": validity.get("geometry_valid", False),
            "semantic_age_s": validity.get("semantic_age_s"),
            "semantic_valid": validity.get("semantic_valid", False),
            "temporal_consistency_ok": validity.get("temporal_consistency_ok", False),
            "position_covariance_trace_m2": trace,
            "semantic_confidence": max((v for k, v in semantic.items() if k != "unknown"), default=0.0),
            "target_position_world_m": None if position is None else position.tolist(),
            "tcp_pos_world_m": None if tcp is None else tcp.tolist(),
            "direction_cosine": cosine,
            "target_distance_m": norm,
            "distance_reduction_m": None if direction is None or norm is None else norm - float(np.linalg.norm(target_vector - direction * self.step_m)),
            "moves_toward_target": None if cosine is None else cosine > 0,
            "decision_evidence_available": cosine is not None,
            "gripper_width_m": belief.continuous.get("gripper_width_m"),
        }

    def build(self, belief):
        assert_visual_snapshot(belief)
        track, validity, position, covariance, semantic = self._evidence(belief)
        geometry_reasons = self._geometry_reasons(validity, position, covariance)
        if "tcp_pos_world_m" not in belief.continuous:
            geometry_reasons += ("proprioception_missing",)
        geometry_usable = not geometry_reasons
        candidates = []
        tokens = ("MV_FWD", "MV_BACK", "MV_LEFT", "MV_RIGHT", "MV_UP", "MV_DOWN",
                  "ROTATE_CW", "ROTATE_CCW", "STOP")
        for token in tokens:
            reasons = [] if token == "STOP" else list(geometry_reasons)
            metadata = self._metadata(token, belief, track, validity, position, covariance, semantic)
            if token in MOVE and self.workspace_bounds_m and geometry_usable:
                tcp = metadata["tcp_pos_world_m"]
                if tcp is not None:
                    proposed = np.asarray(tcp) + np.asarray(MOVE[token]) * self.step_m
                    if any(proposed[i] < bounds[0] or proposed[i] > bounds[1]
                           for i, bounds in enumerate(self.workspace_bounds_m)):
                        reasons.append("workspace_limit")
            description = DESCRIPTIONS[token]
            if token in MOVE:
                description = f"translate {self.step_m:g} m along world direction {MOVE[token]}; preserve gripper command"
            elif token.startswith("ROTATE_"):
                description = f"rotate {'-10' if token == 'ROTATE_CW' else '+10'} degrees about world Z; preserve gripper command"
            elif token == "STOP":
                description = "active pose hold; preserve commanded gripper state; simulation continues"
            candidates.append(Candidate(token, description, not reasons,
                                        tuple(dict.fromkeys(reasons)), metadata=metadata))
        if self.include_gripper:
            width = belief.continuous.get("gripper_width_m")
            grasp_reasons = list(geometry_reasons)
            if not validity.get("semantic_valid", False):
                grasp_reasons.append("semantic_invalid")
            if not validity.get("temporal_consistency_ok", False):
                grasp_reasons.append("temporal_inconsistency")
            if width is None:
                grasp_reasons.append("gripper_state_unknown")
            elif float(width) <= self.closed_width_m:
                grasp_reasons.append("gripper_already_closed")
            candidates.append(Candidate("GRASP", DESCRIPTIONS["GRASP"], not grasp_reasons,
                                        tuple(dict.fromkeys(grasp_reasons)), risk=.4,
                                        metadata=self._metadata("GRASP", belief, track, validity, position, covariance, semantic)))
            release_reasons = []
            holding = belief.continuous.get("holding")
            if holding is not True and belief.continuous.get("gripper_command") != "CLOSED":
                release_reasons.append("holding_state_unknown")
            candidates.append(Candidate("RELEASE", DESCRIPTIONS["RELEASE"], not release_reasons,
                                        tuple(release_reasons), risk=.3,
                                        metadata=self._metadata("RELEASE", belief, track, validity, position, covariance, semantic)))
        if belief.goal.get("satisfied"):
            candidates.append(Candidate("DONE", "finish only after the real success predicate is true", True))
        self.last_preview = None
        self.last_diagnostics = {
            "builder_version": self.version, "oracle": False,
            "privileged_state_used": False, "tracking_active": False,
            "target_track": track, "candidate_count": len(candidates),
            "candidate_veto_count": sum(not c.feasible for c in candidates),
            "veto_reason_histogram": dict(Counter(reason for c in candidates for reason in c.reason_codes)),
            "geometry_usable": geometry_usable,
            "geometry_reasons": list(geometry_reasons),
        }
        return tuple(candidates)


PROPRIO_KEYS = {"tcp_pos_world_m", "gripper_width_m", "gripper_joint_positions",
               "gripper_command", "holding", "proprioception_source"}


def assert_visual_snapshot(belief):
    """Fail closed on unexpected object-state channels before policy/candidates."""
    for key in belief.continuous:
        if key in PROPRIO_KEYS:
            continue
        if key.startswith("vision:") and key.endswith((":position_world_m", ":velocity_mps", ":covariance")):
            continue
        raise ValueError(f"privileged or unknown visual decision field: {key}")
    if set(belief.goal) - {"task", "instruction", "target_query", "satisfied"}:
        raise ValueError("unknown visual task context")
