"""Jev-LIBERO physics preview candidates for the Laya decision layer."""
from __future__ import annotations

from typing import Any

from ..runtime_core import DESCRIPTIONS, Candidate

TOKEN_TO_JEV = {
    "MV_FWD": "x+10mm", "MV_BACK": "x-10mm",
    "MV_LEFT": "y+10mm", "MV_RIGHT": "y-10mm",
    "MV_UP": "z+10mm", "MV_DOWN": "z-10mm",
    "ROTATE_CW": "rotate_z-10deg", "ROTATE_CCW": "rotate_z+10deg",
    "GRASP": "close", "RELEASE": "open", "STOP": "hold",
}


class PhysicsPreviewCandidateBuilder:
    """Run Jev's reversible one-step predictions and expose only feasible tokens."""

    def __init__(self, world: Any, *, collision_aware: bool = True):
        self.world = world
        self.collision_aware = collision_aware
        self.last_preview: dict[str, Any] | None = None

    def build(self, belief):
        from jev_libero.policy import contracts

        before, predictions = self.world.predict_all(getattr(self.world, "_grip", -1.0))
        pools, rejected = contracts(before, predictions, collision_aware=self.collision_aware, task_config=self.world.config)
        eligible = {name for pool in pools.values() for name in pool}
        by_token: dict[str, list[str]] = {}
        for token, action in TOKEN_TO_JEV.items():
            by_token.setdefault(action, []).append(token)
        candidates = []
        for token, action in TOKEN_TO_JEV.items():
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
        if before.get("success"):
            candidates.append(Candidate("DONE", "finish only after the real LIBERO success predicate is true", True))
        if not any(c.feasible for c in candidates):
            candidates.append(Candidate("STOP", "hold because no physics-preview candidate satisfies the task contract", True, ("no_feasible_candidate",), 0.0))
        self.last_preview = {"before": before, "predictions": predictions, "pools": pools, "rejected": rejected}
        return tuple(candidates)
