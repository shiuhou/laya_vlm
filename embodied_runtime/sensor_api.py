"""Robot-only capabilities for the sensor path; no simulator truth interface.

This module does not adapt LIBERO. Real sensor calibration and control remain a
P1/P2 integration gate. A held relation is never inferred from jaw width or a
retained command.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from math import isfinite, sqrt
from typing import Any, Protocol, runtime_checkable

from .contracts import ProtocolError


GRIPPER_COMMANDS = frozenset({"KEEP", "OPEN", "CLOSE"})


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value):
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be finite")
    if nonnegative and value < 0:
        raise ProtocolError("INVALID_SCHEMA", f"{name} must be nonnegative")
    return float(value)


def _vector(value: Any, name: str, size: int | None = None) -> tuple[float, ...]:
    if not isinstance(value, (tuple, list)) or (size is not None and len(value) != size):
        raise ProtocolError("INVALID_SCHEMA", f"invalid {name} shape")
    return tuple(_finite(x, name) for x in value)


@dataclass(frozen=True)
class Proprioception:
    capture_sim_time_s: float
    capture_monotonic_ns: int
    eef_position_base_m: tuple[float, float, float] | None
    eef_quaternion_xyzw: tuple[float, float, float, float] | None
    joint_position_rad: tuple[float, ...] | None
    gripper_width_m: float | None
    valid: bool
    source_ids: tuple[str, ...]
    gripper_width_calibration_id: str | None = None
    gripper_command: str = "KEEP"
    joint_velocity_rad_s: tuple[float, ...] | None = None
    gripper_joint_position_rad: tuple[float, ...] | None = None
    eef_pose_source: str = "robot_sensor"
    robot_model_id: str | None = None
    provenance: str = "proprioceptive"
    frame: str = "robot_base"
    reason_codes: tuple[str, ...] = ()
    holding: None = None

    def __post_init__(self):
        _finite(self.capture_sim_time_s, "capture_sim_time_s", nonnegative=True)
        if type(self.capture_monotonic_ns) is not int or self.capture_monotonic_ns < 0:
            raise ProtocolError("INVALID_SCHEMA", "invalid capture_monotonic_ns")
        if type(self.valid) is not bool:
            raise ProtocolError("INVALID_SCHEMA", "valid must be boolean")
        if self.frame != "robot_base" or self.provenance != "proprioceptive":
            raise ProtocolError("INFORMATION_BOUNDARY", "robot_base proprioception required")
        if self.eef_pose_source not in {"robot_sensor", "robot_fk"}:
            raise ProtocolError("INFORMATION_BOUNDARY", "unknown EEF sensor source")
        for name in ("robot_model_id", "gripper_width_calibration_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise ProtocolError("INVALID_SCHEMA", f"invalid {name}")
        if self.eef_pose_source == "robot_fk" and not self.robot_model_id:
            raise ProtocolError("INVALID_SCHEMA", "FK requires robot_model_id")
        if self.holding is not None:
            raise ProtocolError("INFORMATION_BOUNDARY", "holding is not a proprioceptive measurement")
        for name in ("source_ids", "reason_codes"):
            value = getattr(self, name)
            if not isinstance(value, (tuple, list)) or any(not isinstance(x, str) or not x for x in value):
                raise ProtocolError("INVALID_SCHEMA", f"invalid {name}")
            object.__setattr__(self, name, tuple(value))
        if not self.source_ids:
            raise ProtocolError("INVALID_SCHEMA", "proprioception needs sensor source IDs")
        for name, size in (("eef_position_base_m", 3), ("eef_quaternion_xyzw", 4),
                           ("joint_position_rad", None), ("joint_velocity_rad_s", None),
                           ("gripper_joint_position_rad", None)):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _vector(value, name, size))
        if self.eef_quaternion_xyzw is not None:
            norm = sqrt(sum(x * x for x in self.eef_quaternion_xyzw))
            if abs(norm - 1.0) > 1e-6:
                raise ProtocolError("INVALID_SCHEMA", "quaternion must be normalized xyzw")
        if self.valid and (self.eef_position_base_m is None or self.eef_quaternion_xyzw is None
                           or not self.joint_position_rad):
            raise ProtocolError("INVALID_SCHEMA", "valid proprioception needs EEF pose and joints")
        if not self.valid and not self.reason_codes:
            raise ProtocolError("INVALID_SCHEMA", "invalid proprioception requires reasons")
        if self.joint_velocity_rad_s is not None and (self.joint_position_rad is None
                or len(self.joint_velocity_rad_s) != len(self.joint_position_rad)):
            raise ProtocolError("INVALID_SCHEMA", "joint velocity shape differs from position")
        if self.gripper_width_m is not None:
            _finite(self.gripper_width_m, "gripper_width_m", nonnegative=True)
            if not self.gripper_width_calibration_id:
                raise ProtocolError("INVALID_SCHEMA", "jaw width requires explicit calibration")
        elif not self.reason_codes:
            raise ProtocolError("INVALID_SCHEMA", "unknown jaw width requires a reason")
        if self.gripper_command not in GRIPPER_COMMANDS:
            raise ProtocolError("INVALID_SCHEMA", "gripper command must be KEEP, OPEN or CLOSE")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Proprioception:
        if not isinstance(value, Mapping):
            raise ProtocolError("INVALID_SCHEMA", "proprioception must be a mapping")
        unknown = set(value) - {field.name for field in fields(cls)}
        if unknown:
            raise ProtocolError("INFORMATION_BOUNDARY", f"unlisted proprioception fields: {sorted(unknown)}")
        try:
            return cls(**value)
        except TypeError as exc:
            raise ProtocolError("INVALID_SCHEMA", "missing or invalid proprioception fields") from exc

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class SensorBackend(Protocol):
    """Capabilities given to servo: robot observation and single control ticks.

    KEEP and hold() preserve the backend-owned gripper command/polarity. Delta
    arguments are one tick in robot_base, not the entire primitive intention.
    Implementations must not expose success or target-state methods here.
    """

    def read_proprioception(self) -> Proprioception: ...

    def command_tick(self, delta_position_m: tuple[float, float, float],
                     delta_rotation_rad: tuple[float, float, float],
                     gripper_command: str, duration_s: float) -> None: ...

    def hold(self) -> None: ...

    def close(self) -> None: ...


class SensorPort:
    """Inject narrow callables rather than giving a policy the simulator object."""

    __slots__ = ("_read", "_command", "_hold", "_close")

    def __init__(self, *, read: Callable[[], Proprioception | Mapping[str, Any]],
                 command: Callable[..., None], hold: Callable[[], None],
                 close: Callable[[], None]):
        self._read, self._command, self._hold, self._close = read, command, hold, close

    def read_proprioception(self) -> Proprioception:
        value = self._read()
        return value if isinstance(value, Proprioception) else Proprioception.from_mapping(value)

    def command_tick(self, delta_position_m, delta_rotation_rad,
                     gripper_command, duration_s):
        delta_position_m = _vector(delta_position_m, "delta_position_m", 3)
        delta_rotation_rad = _vector(delta_rotation_rad, "delta_rotation_rad", 3)
        if gripper_command not in GRIPPER_COMMANDS:
            raise ProtocolError("INVALID_SCHEMA", "invalid gripper command")
        if not 0 < _finite(duration_s, "duration_s") <= .1:
            raise ProtocolError("INVALID_SCHEMA", "control tick must be <=100ms")
        self._command(delta_position_m, delta_rotation_rad, gripper_command, duration_s)

    def hold(self):
        self._hold()

    def close(self):
        self._close()
