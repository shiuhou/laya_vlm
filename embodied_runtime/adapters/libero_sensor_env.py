"""Read-only P1 LIBERO sensing, isolated from task truth and execution.

Only registered robot arm encoders and its EEF site FK are sampled. RGB-D uses
known camera calibration and a fixed robot base. This does not install a servo,
step the simulator or claim independent real-world sensor calibration.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from ..contracts import ProtocolError
from ..sensor_api import Proprioception
from .libero_rgbd import LiberoRgbdSource, fixed_robot_base, rigid_transform


def quaternion_xyzw(rotation):
    """Convert a validated rotation matrix without importing simulator utilities."""
    R = np.asarray(rotation, dtype=float)
    transform = np.eye(4)
    transform[:3, :3] = R
    rigid_transform(transform, "EEF rotation")
    trace = np.trace(R)
    if trace > 0:
        s = np.sqrt(trace + 1) * 2
        q = np.array([(R[2, 1]-R[1, 2])/s, (R[0, 2]-R[2, 0])/s,
                      (R[1, 0]-R[0, 1])/s, s/4])
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i+1) % 3, (i+2) % 3
        s = np.sqrt(1 + R[i, i]-R[j, j]-R[k, k]) * 2
        q = np.empty(4)
        q[i], q[j], q[k], q[3] = s/4, (R[j, i]+R[i, j])/s, (R[k, i]+R[i, k])/s, (R[k, j]-R[j, k])/s
    q /= np.linalg.norm(q)
    return q if q[3] >= 0 else -q


class LiberoSensingPort:
    """Consumer-facing sensing capabilities; has no world or motion methods."""
    __slots__ = ("_capture", "_read")

    def __init__(self, capture, read):
        self._capture, self._read = capture, read

    def capture(self):
        return self._capture()

    def read_proprioception(self):
        return self._read()


class LiberoSensorEnv:
    """Trusted boundary owns simulator references; consumers receive sensor_port.

    The robot-site read is explicitly simulated robot FK, not target truth or a
    claim that an independent hardware sensor measured Cartesian pose. Panda
    finger joints are prismatic; they are not mislabeled radians or a calibrated
    fingerpad gap. Jaw width therefore remains null in this P1 adapter.
    """
    __slots__ = ("_world", "_robot", "_sources", "_lock", "_clock", "_base", "_base_inverse",
                 "_robot_model_id", "_qpos_indices", "_qvel_indices", "_eef_site_id",
                 "_retained_command", "_bundle_seq", "_proprio_seq", "_closed", "_owns_world")

    def __init__(self, world, *, camera_names=("agentview", "robot0_eye_in_hand"), width=384, height=384,
                 calibration_versions=None, T_world_base=None, robot_model_id=None,
                 monotonic_ns=time.monotonic_ns, capture_lock=None, camera_utils=None,
                 retained_gripper_command=None, owns_world=False):
        cameras = tuple(camera_names)
        if not cameras or len(cameras) != len(set(cameras)):
            raise ProtocolError("INVALID_SCHEMA", "nonempty unique cameras required")
        self._world, self._robot = world, world.env.env.robots[0]
        self._lock = capture_lock if capture_lock is not None else threading.RLock()
        self._clock = monotonic_ns
        self._base = fixed_robot_base(world) if T_world_base is None else rigid_transform(T_world_base, "T_world_base")
        self._base_inverse = rigid_transform(np.linalg.inv(self._base))
        self._robot_model_id = robot_model_id or f"{type(self._robot.robot_model).__name__}:{self._robot.robot_model.root_body}"
        self._qpos_indices = tuple(int(index) for index in self._robot._ref_joint_pos_indexes)
        self._qvel_indices = tuple(int(index) for index in self._robot._ref_joint_vel_indexes)
        if not self._qpos_indices or len(self._qpos_indices) != len(self._qvel_indices) \
                or len(set(self._qpos_indices)) != len(self._qpos_indices) \
                or min(self._qpos_indices + self._qvel_indices) < 0:
            raise ProtocolError("INVALID_CALIBRATION", "robot encoder index mapping required")
        self._eef_site_id = int(self._robot.eef_site_id)
        if self._eef_site_id < 0:
            raise ProtocolError("INVALID_CALIBRATION", "registered robot EEF site required")
        calibrations = calibration_versions or {}
        if set(calibrations) - set(cameras):
            raise ProtocolError("INVALID_CALIBRATION", "calibration for undeclared camera")
        self._sources = tuple(LiberoRgbdSource(world, camera_name=camera, width=width, height=height,
                              T_world_base=self._base, calibration_version=calibrations.get(camera),
                              monotonic_ns=monotonic_ns, camera_utils=camera_utils)
                              for camera in cameras)
        self._retained_command = retained_gripper_command
        self._bundle_seq = self._proprio_seq = 0
        self._closed, self._owns_world = False, owns_world

    def _ensure_open(self):
        if self._closed:
            raise ProtocolError("SENSOR_CLOSED")

    def _read_proprioception(self):
        self._ensure_open()
        captured = float(self._world.data.time)
        monotonic = self._clock()
        data = self._world.env.sim.data
        # Indexing only the declared robot-owned registers avoids copying the
        # full scene qpos/qvel or querying scene body/site identifiers.
        joints = tuple(float(data.qpos[index]) for index in self._qpos_indices)
        velocity = tuple(float(data.qvel[index]) for index in self._qvel_indices)
        position_world = np.array(data.site_xpos[self._eef_site_id], dtype=float, copy=True)
        rotation_world = np.array(data.site_xmat[self._eef_site_id], dtype=float, copy=True).reshape(3, 3)
        if position_world.shape != (3,):
            raise ProtocolError("INVALID_SENSOR", "EEF position shape")
        position = self._base_inverse[:3, :3] @ position_world + self._base_inverse[:3, 3]
        orientation = quaternion_xyzw(self._base_inverse[:3, :3] @ rotation_world)
        if float(self._world.data.time) != captured:
            raise ProtocolError("UNSYNCHRONIZED_PROPRIO", "simulation advanced during robot measurement")
        command = "KEEP" if self._retained_command is None else self._retained_command()
        if command not in {"KEEP", "OPEN", "CLOSE"}:
            raise ProtocolError("INVALID_SENSOR", "retained command must use semantic polarity")
        self._proprio_seq += 1
        return Proprioception(capture_sim_time_s=captured, capture_monotonic_ns=monotonic,
                             eef_position_base_m=tuple(position), eef_quaternion_xyzw=tuple(orientation),
                             joint_position_rad=joints, joint_velocity_rad_s=velocity,
                             gripper_width_m=None, valid=True,
                             source_ids=(f"robot-encoders-fk:{self._proprio_seq}",),
                             eef_pose_source="robot_fk", robot_model_id=self._robot_model_id,
                             gripper_command=command, reason_codes=("WIDTH_UNCALIBRATED",) +
                             (("GRIPPER_COMMAND_NOT_OBSERVED",) if self._retained_command is None else ()))

    def read_proprioception(self):
        with self._lock:
            return self._read_proprioception()

    def capture(self):
        with self._lock:
            self._ensure_open()
            initial_time = float(self._world.data.time)
            views = [source.capture() for source in self._sources]
            proprio = self._read_proprioception()
            finished_time, finished_ns = float(self._world.data.time), self._clock()
            if finished_time != initial_time or any(view["capture_sim_time_s"] != initial_time for view in views):
                raise ProtocolError("UNSYNCHRONIZED_RGBD", "simulation advanced across bundle views/proprio")
            if finished_ns < max(proprio.capture_monotonic_ns, *(view["capture_monotonic_ns"] for view in views)):
                raise ProtocolError("INVALID_CLOCK", "bundle wall clock regressed")
            self._bundle_seq += 1
            return {"bundle_id": f"sensor-bundle:{self._bundle_seq}", "capture_sim_time_s": finished_time,
                    "capture_monotonic_ns": finished_ns, "views": views, "proprio": proprio.to_dict()}

    def sensor_port(self):
        return LiberoSensingPort(self.capture, self.read_proprioception)

    def close(self):
        with self._lock:
            if not self._closed:
                self._closed = True
                if self._owns_world:
                    self._world.close()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
