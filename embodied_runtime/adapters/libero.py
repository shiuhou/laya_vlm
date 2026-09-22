"""Adapter for the public jev-libero World implementation.

This is an oracle/state-based adapter: it deliberately reads simulator state for the
first executor and physics-preview validation. It must not be reported as visual
performance. A future RGB-D adapter can feed the same BeliefStore without changing this
execution boundary.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..runtime_core import MOVE, AtomicBackend

# Stage-1 top_drawer/reset calibration envelopes, not general safety thresholds.
CONTRACT_VERSION = "atomic-top-drawer-v1"
CONTRACT_TOLERANCES = {
    "translation_error_m": 0.002,
    "hold_translation_m": 0.0015,
    "hold_rotation_deg": 1.0,
    "rotation_error_deg": 2.0,
}


class LiberoWorldBackend(AtomicBackend):
    """Map Show-Harness-like atomic tokens onto jev-libero World actions."""

    def __init__(self, world: Any, step_mm: int = 10):
        self.world = world
        self.step_mm = int(step_mm)
        self.step_m = self.step_mm / 1000.0
        self._grip_cmd = -1.0  # robosuite convention: open/close is backend-owned
        self.last_execution = None

    @classmethod
    def from_task(cls, task: str = "top_drawer", *, seed: int = 1,
                  libero_root: str | None = None, config_dir: str | None = None,
                  render: bool = False) -> LiberoWorldBackend:
        from jev_libero.config import load_task
        from jev_libero.world import World

        world = World(seed=seed, render=render, task_config=load_task(task),
                      libero_root=libero_root, config_dir=config_dir)
        return cls(world)

    def tcp_pos(self) -> np.ndarray:
        return np.asarray(self.world.obs["robot0_eef_pos"], dtype=float).copy()

    def gripper_width(self) -> float:
        return float(self.world.features().get("finger_gap_mm", 0.0)) / 1000.0

    def success(self) -> bool:
        return bool(self.world.features().get("success", False))

    def _move_name(self, delta: np.ndarray) -> str:
        delta = np.asarray(delta, dtype=float)
        if delta.shape != (3,) or not np.isfinite(delta).all() or np.count_nonzero(delta) != 1:
            raise ValueError("translation must have exactly one finite nonzero world axis")
        axis = int(np.argmax(np.abs(delta)))
        if not np.isclose(abs(delta[axis]), self.step_m, rtol=0, atol=1e-12):
            raise ValueError("translation must match the calibrated primitive step size")
        sign = 1 if delta[axis] >= 0 else -1
        names = ("x", "y", "z")
        return f"{names[axis]}{sign * self.step_mm:+d}mm"

    def _execute(self, name):
        self.last_execution = self.world.execute(name, grip=self._grip_cmd, record=False)

    def apply_delta(self, delta_m: np.ndarray, grip_cmd: float | None = None) -> None:
        # World.execute owns the actual 7-D robosuite action and controller stepping.
        name = self._move_name(delta_m)
        if grip_cmd is not None:
            raise ValueError("translation cannot change gripper command; use GRASP/RELEASE")
        self._execute(name)

    def close_gripper(self) -> None:
        self._grip_cmd = 1.0
        self._execute("close")

    def open_gripper(self) -> None:
        self._grip_cmd = -1.0
        self._execute("open")

    def hold(self) -> None:
        self._execute("hold")

    def rotate(self, token: str) -> None:
        # Rotation mapping is explicit and stays at the execution boundary.
        axis = "z"
        sign = -1 if token == "ROTATE_CW" else 1
        self._execute(f"rotate_{axis}{sign * 10:+d}deg")

    def execution_state(self):
        features = self.world.features()
        return {
            "sim_time": float(self.world.data.time),
            "tcp_xyz": self.tcp_pos().tolist(),
            "orientation": features["eef_rotation_matrix"],
            "finger_gap_m": features["finger_gap_mm"] / 1000.0,
            "gripper_command": self._grip_cmd,
            "contacts": features["contacts"], "success": features["success"],
        }

    def execution_evidence(self, token, before):
        after = self.execution_state()
        delta = np.asarray(after["tcp_xyz"]) - before["tcp_xyz"]
        rotation = np.asarray(after["orientation"]) @ np.asarray(before["orientation"]).T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1, 1))))
        reasons = []
        expected_grip = {"GRASP": 1.0, "RELEASE": -1.0}.get(token, before["gripper_command"])
        commands = [] if token == "DONE" else self.last_execution["commands"]
        if after["gripper_command"] != expected_grip or any(a[-1] != expected_grip for a in commands):
            reasons.append("gripper_command_changed_unexpectedly")
        tolerance = CONTRACT_TOLERANCES
        if token in MOVE:
            if np.linalg.norm(delta - np.asarray(MOVE[token]) * self.step_m) > tolerance["translation_error_m"]:
                reasons.append("translation_error")
        elif np.linalg.norm(delta) > tolerance["hold_translation_m"]:
            reasons.append("unintended_translation")
        if token.startswith("ROTATE_"):
            theta = np.radians(-10 if token == "ROTATE_CW" else 10)
            expected = np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])
            error = float(np.degrees(np.arccos(np.clip((np.trace(rotation @ expected.T) - 1) / 2, -1, 1))))
            if error > tolerance["rotation_error_deg"]:
                reasons.append("rotation_error")
        elif angle > tolerance["hold_rotation_deg"]:
            reasons.append("unintended_rotation")
        return {
            "execution_contract_version": CONTRACT_VERSION,
            "execution_contract_tolerances": dict(tolerance),
            "execution_contract_violation": bool(reasons),
            "execution_contract_reason": reasons,
            "execution_before": before, "execution_after": after,
            "rotation_delta": rotation.tolist(), "rotation_angle_deg": angle,
            "finger_gap_delta": after["finger_gap_m"] - before["finger_gap_m"],
            "environment_step_count": len(commands),
            "low_level_step_count": int(round((after["sim_time"] - before["sim_time"]) / self.world.model.opt.timestep)),
            "low_level_commands": [np.asarray(a).tolist() for a in commands],
        }

    def close(self) -> None:
        self.world.close()
