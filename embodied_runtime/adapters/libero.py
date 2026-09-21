"""Adapter for the public jev-libero World implementation.

This is an oracle/state-based adapter: it deliberately reads simulator state for the
first executor and physics-preview validation. It must not be reported as visual
performance. A future RGB-D adapter can feed the same BeliefStore without changing this
execution boundary.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ..runtime_core import AtomicBackend


class LiberoWorldBackend(AtomicBackend):
    """Map Show-Harness-like atomic tokens onto jev-libero World actions."""

    def __init__(self, world: Any, step_mm: int = 10):
        self.world = world
        self.step_mm = int(step_mm)
        self._grip_cmd = -1.0  # robosuite convention: open/close is backend-owned

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
        axis = int(np.argmax(np.abs(delta)))
        sign = 1 if delta[axis] >= 0 else -1
        names = ("x", "y", "z")
        return f"{names[axis]}{sign * self.step_mm:+d}mm"

    def apply_delta(self, delta_m: np.ndarray, grip_cmd: float) -> None:
        # World.execute owns the actual 7-D robosuite action and controller stepping.
        self._grip_cmd = float(grip_cmd)
        self.world.execute(self._move_name(delta_m), grip=self._grip_cmd, record=False)

    def close_gripper(self) -> None:
        self._grip_cmd = 1.0
        self.world.execute("close", grip=self._grip_cmd, record=False)

    def open_gripper(self) -> None:
        self._grip_cmd = -1.0
        self.world.execute("open", grip=self._grip_cmd, record=False)

    def hold(self) -> None:
        self.world.execute("hold", grip=self._grip_cmd, record=False)

    def rotate(self, token: str) -> None:
        # Rotation mapping is explicit and stays at the execution boundary.
        axis = "z" if token == "ROTATE_CW" else "x"
        sign = -1 if token == "ROTATE_CW" else 1
        self.world.execute(f"rotate_{axis}{sign * 10:+d}deg", grip=self._grip_cmd, record=False)

    def close(self) -> None:
        self.world.close()
