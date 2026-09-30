"""Single-owner, tick-interruptible execution; never calls a model/evaluator."""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, sqrt

from ..contracts import ProtocolError, canonical_json, freeze, require
from .action_catalog import MAX_SEGMENT_ROTATION_RAD, MAX_SEGMENT_TRANSLATION_M
from .action_contracts import ActionContract, validate_latest


@dataclass(frozen=True)
class ExecutionFeedback:
    contract_id: str
    decision_id: str
    status: str
    started_sim_time_s: float
    finished_sim_time_s: float
    started_monotonic_ns: int
    finished_monotonic_ns: int
    measured_eef_delta_m: tuple
    measured_gripper_state: object
    remaining_requested_magnitude: float
    reason_codes: tuple


class Servo:
    def __init__(self, backend, *, latest_context, sink=None):
        self.backend, self.latest_context, self.sink = backend, latest_context, sink
        self.active = None
        self.seen = {}
        self.decisions = {}
        self.feedback = []
        self._before = None
        self._elapsed = 0.

    def install(self, contract: ActionContract, *, sim_time_s, monotonic_ns):
        content = canonical_json(contract)
        if contract.contract_id in self.seen:
            require(self.seen[contract.contract_id] == content, "contract content changed", "CONTRACT_ID_CONFLICT")
            return False
        require(contract.decision_id not in self.decisions, "decision already authorized a segment", "DECISION_REUSED")
        require(self.active is None, "one active contract", "CONTRACT_BUSY")
        require(not contract.expired(sim_time_s=sim_time_s, monotonic_ns=monotonic_ns), "expired contract", "CONTRACT_EXPIRED")
        require(sim_time_s >= contract.issued_sim_time_s and monotonic_ns >= contract.issued_monotonic_ns,
                "contract from future", "INVALID_CLOCK")
        require(contract.reference_frame == "robot_base", "contract frame")
        require(0 < contract.valid_until_sim_s-contract.issued_sim_time_s <= .100000001,
                "contract duration")
        require(0 < contract.expires_monotonic_ns-contract.issued_monotonic_ns <= 100_000_000,
                "contract wall duration")
        require(sqrt(sum(x*x for x in contract.delta_position_m)) <= MAX_SEGMENT_TRANSLATION_M+1e-12,
                "translation cap")
        require(sqrt(sum(x*x for x in contract.delta_rotation_rad)) <= MAX_SEGMENT_ROTATION_RAD+1e-12,
                "rotation cap")
        require(contract.gripper_command in {"KEEP", "OPEN", "CLOSE"}, "gripper contract")
        validate_latest(contract.identity, contract.source_snapshot_id, contract.action_id,
                        self.latest_context(sim_time_s, monotonic_ns))
        before = self.backend.read_proprioception()
        require(before.valid and before.eef_position_base_m is not None, "invalid measured EEF", "SENSOR_INVALID")
        self.active, self._before, self._elapsed = contract, before, 0.
        self.seen[contract.contract_id] = content
        self.decisions[contract.decision_id] = contract.contract_id
        if self.sink:
            self.sink("contract_installed", contract)
        return True

    def _finish(self, status, reasons, sim_time_s, monotonic_ns):
        c = self.active
        if c is None:
            return None
        self.active = None  # Revoke before interacting with a backend or log sink.
        self.backend.hold()
        after = self.backend.read_proprioception()
        before = self._before
        delta = None
        progress = 0.
        if after.valid and after.eef_position_base_m is not None:
            delta = tuple(a-b for a,b in zip(after.eef_position_base_m, before.eef_position_base_m))
            if c.magnitude_unit == "m" and c.segment_magnitude:
                progress = max(0., sum(d*x for d,x in zip(delta, c.delta_position_m))/c.segment_magnitude)
            elif c.magnitude_unit == "rad" and after.eef_quaternion_xyzw is not None:
                # Measured base-frame relative rotation, projected on the chosen
                # signed axis; opposite/orthogonal rotation is not progress.
                ax,ay,az,aw = after.eef_quaternion_xyzw
                bx,by,bz,bw = before.eef_quaternion_xyzw
                relative = (ax*bw-aw*bx-ay*bz+az*by,
                            ay*bw-aw*by-az*bx+ax*bz,
                            az*bw-aw*bz-ax*by+ay*bx,
                            aw*bw+ax*bx+ay*by+az*bz)
                if relative[3] < 0:
                    relative = tuple(-x for x in relative)
                norm = sqrt(sum(x*x for x in relative[:3]))
                if norm > 1e-12:
                    angle = 2*acos(max(-1., min(1., relative[3])))
                    vector = tuple(x*angle/norm for x in relative[:3])
                    progress = max(0., sum(x*d for x,d in zip(vector,c.delta_rotation_rad))/c.segment_magnitude)
        else:
            status, reasons = "ABORTED", (*reasons, "SENSOR_INVALID")
        remaining = max(0., c.requested_magnitude - min(c.segment_magnitude, progress))
        if status != "ABORTED":
            status = "PARTIAL" if remaining > 1e-9 else "COMPLETED"
            if c.action_id in {"OPEN", "CLOSE"}:
                # A measured width is not a calibrated open/closed predicate.
                # P0 deliberately has no such physical completion evaluator.
                status, reasons = "PARTIAL", (*reasons, "GRIPPER_COMPLETION_UNKNOWN")
        grip = freeze({key: value for key, value in after.to_dict().items() if key in {
            "gripper_width_m", "gripper_width_calibration_id", "gripper_joint_position_rad",
            "gripper_command", "valid", "reason_codes", "source_ids", "holding"}})
        result = ExecutionFeedback(c.contract_id, c.decision_id, status,
                                   before.capture_sim_time_s, after.capture_sim_time_s,
                                   before.capture_monotonic_ns, after.capture_monotonic_ns,
                                   delta, grip, remaining, tuple(reasons))
        self.feedback.append(result)
        if self.sink:
            self.sink("execution_feedback", result)
        return result

    def cancel(self, reason, *, sim_time_s=0., monotonic_ns=0):
        if self.active is not None:
            return self._finish("ABORTED", (reason,), sim_time_s, monotonic_ns)
        self.backend.hold()
        return None

    def tick(self, *, sim_time_s, monotonic_ns, duration_s=.05):
        require(0 < duration_s <= .1, "servo tick duration")
        c = self.active
        if c is None:
            self.backend.hold()
            if self.sink:
                self.sink("proprioception", self.backend.read_proprioception())
            return None
        try:
            require(not c.expired(sim_time_s=sim_time_s, monotonic_ns=monotonic_ns),
                    "servo deadline", "CONTRACT_EXPIRED")
            validate_latest(c.identity, c.source_snapshot_id, c.action_id,
                            self.latest_context(sim_time_s, monotonic_ns))
            total = c.valid_until_sim_s-c.issued_sim_time_s
            dt = min(duration_s, total-self._elapsed, c.valid_until_sim_s-sim_time_s,
                     (c.expires_monotonic_ns-monotonic_ns)/1e9)
            require(dt > 1e-12, "no executable duration", "CONTRACT_EXPIRED")
            fraction = dt/total
            self.backend.command_tick(tuple(d*fraction for d in c.delta_position_m),
                                      tuple(d*fraction for d in c.delta_rotation_rad),
                                      c.gripper_command, dt)
            self._elapsed += dt
            if self.sink:
                self.sink("servo_tick", dict(contract_id=c.contract_id, sim_time_s=sim_time_s,
                                            monotonic_ns=monotonic_ns, duration_s=dt))
                self.sink("proprioception", self.backend.read_proprioception())
            if self._elapsed >= total-1e-12:
                return self._finish("COMPLETED", (), sim_time_s, monotonic_ns)
        except ProtocolError as exc:
            return self._finish("ABORTED", (exc.code,), sim_time_s, monotonic_ns)
        except Exception:
            self.active = None
            self.backend.hold()
            raise
        return None
