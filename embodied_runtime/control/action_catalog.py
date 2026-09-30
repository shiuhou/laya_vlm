"""Stable robot-base action semantics; independent of task or utility."""

from dataclasses import dataclass
from math import pi

CATALOG_REVISION = "base27-v1"
REFERENCE_FRAME = "robot_base"
MAX_SEGMENT_DURATION_S = 0.100
MAX_SEGMENT_TRANSLATION_M = 0.005
MAX_CONTACT_TRANSLATION_M = 0.002
MAX_SEGMENT_ROTATION_RAD = pi / 90


@dataclass(frozen=True)
class ActionSpec:
    id: str
    primitive: str
    nominal_delta: tuple[float, float, float]
    gripper_command: str = "KEEP"
    reference_frame: str = REFERENCE_FRAME


def _catalog() -> tuple[ActionSpec, ...]:
    specs = []
    for axis, label in enumerate("XYZ"):
        for suffix, distance in (
            ("-40", -0.040), ("-10", -0.010), ("-03", -0.003),
            ("+03", 0.003), ("+10", 0.010), ("+40", 0.040),
        ):
            delta = [0.0, 0.0, 0.0]
            delta[axis] = distance
            specs.append(ActionSpec(label + suffix, "TRANSLATE", tuple(delta)))
    for axis, label in enumerate("XYZ"):
        for sign, direction in (("-", -1), ("+", 1)):
            delta = [0.0, 0.0, 0.0]
            delta[axis] = direction * pi / 18
            specs.append(ActionSpec("R" + label + sign + "10", "ROTATE", tuple(delta)))
    specs.extend((
        ActionSpec("OPEN", "GRIPPER", (0.0, 0.0, 0.0), "OPEN"),
        ActionSpec("CLOSE", "GRIPPER", (0.0, 0.0, 0.0), "CLOSE"),
        ActionSpec("HOLD", "HOLD", (0.0, 0.0, 0.0)),
    ))
    return tuple(specs)


CATALOG = _catalog()
ACTION_IDS = tuple(spec.id for spec in CATALOG)


def action_spec(action_id: str) -> ActionSpec:
    """No implicit aliases or legacy GRASP/RELEASE interpretation."""
    for spec in CATALOG:
        if spec.id == action_id:
            return spec
    raise ValueError(f"Unknown {CATALOG_REVISION} action: {action_id!r}")
