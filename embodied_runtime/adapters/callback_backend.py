"""Callback-based AtomicBackend for MuJoCo, LIBERO and test environments.

The backend owns action dimensionality, frame conventions and gripper polarity. The
runtime never assumes ManiSkill or LIBERO action scales.
"""
from __future__ import annotations
from typing import Any, Callable
import numpy as np
from ..runtime_core import AtomicBackend


class CallbackBackend(AtomicBackend):
    def __init__(self, *, tcp_pos: Callable[[], Any], apply_delta: Callable[[np.ndarray, float], None],
                 gripper_width: Callable[[], float], success: Callable[[], bool],
                 close_gripper: Callable[[], None] | None = None,
                 open_gripper: Callable[[], None] | None = None,
                 rotate: Callable[[str], None] | None = None,
                 hold: Callable[[], None] | None = None):
        self._tcp_pos, self._apply_delta = tcp_pos, apply_delta
        self._width, self._success = gripper_width, success
        self._close, self._open = close_gripper, open_gripper
        self._rotate, self._hold = rotate, hold

    def tcp_pos(self) -> np.ndarray:
        return np.asarray(self._tcp_pos(), dtype=float).reshape(3)
    def apply_delta(self, delta_m: np.ndarray, grip_cmd: float) -> None:
        self._apply_delta(np.asarray(delta_m, dtype=float), float(grip_cmd))
    def gripper_width(self) -> float:
        return float(self._width())
    def success(self) -> bool:
        return bool(self._success())
    def close_gripper(self) -> None:
        if self._close: self._close()
    def open_gripper(self) -> None:
        if self._open: self._open()
    def rotate(self, token: str) -> None:
        if self._rotate: self._rotate(token)
    def hold(self) -> None:
        if self._hold: self._hold()
