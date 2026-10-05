"""Same-exposure RGB-D with explicit robot-base camera calibration.

Simulator camera calibration and a known fixed robot base are allowed sensing
configuration. No target pose, object identity, contact or success is read here.
Legacy world-coordinate aliases are preserved for old recording tools; new
perception consumes only ``intrinsics_K`` and ``T_base_camera``.
"""
from __future__ import annotations

from contextlib import nullcontext
import time

import numpy as np

from ..contracts import ProtocolError, content_hash


def _readonly(value, *, dtype=float):
    result = np.array(value, dtype=dtype, copy=True)
    result.setflags(write=False)
    return result


def rigid_transform(value, name="transform"):
    result = np.array(value, dtype=float, copy=True)
    if result.shape != (4, 4) or not np.isfinite(result).all():
        raise ProtocolError("INVALID_CALIBRATION", f"{name} must be finite 4x4")
    if not np.allclose(result[3], [0, 0, 0, 1], atol=1e-9, rtol=0):
        raise ProtocolError("INVALID_CALIBRATION", f"{name} homogeneous row")
    rotation = result[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6, rtol=0) \
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-6, rtol=0):
        raise ProtocolError("INVALID_CALIBRATION", f"{name} rotation")
    return _readonly(result)


def rotation_from_xyzw(value):
    q = np.asarray(value, dtype=float)
    if q.shape != (4,) or not np.isfinite(q).all() or not np.isclose(np.linalg.norm(q), 1, atol=1e-6, rtol=0):
        raise ProtocolError("INVALID_CALIBRATION", "normalized xyzw quaternion required")
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def fixed_robot_base(world):
    """Use known robot setup metadata, never an arbitrary scene body lookup."""
    robot = world.env.env.robots[0]
    position = np.asarray(robot.base_pos, dtype=float)
    orientation = np.asarray(robot.base_ori, dtype=float)
    if position.shape != (3,) or not np.isfinite(position).all():
        raise ProtocolError("INVALID_CALIBRATION", "robot base position unavailable")
    # robosuite 1.4.1 stores xyzw; accept an explicitly supplied rotation matrix
    # from other backend versions, but never substitute identity on mismatch.
    rotation = rotation_from_xyzw(orientation) if orientation.shape == (4,) else orientation
    if rotation.shape != (3, 3):
        raise ProtocolError("INVALID_CALIBRATION", "robot base orientation shape")
    result = np.eye(4)
    result[:3, :3], result[:3, 3] = rotation, position
    return rigid_transform(result, "T_world_base")


class LiberoRgbdSource:
    def __init__(self, world, *, camera_name: str = "agentview", width: int = 384, height: int = 384,
                 T_world_base=None, calibration_version: str | None = None,
                 monotonic_ns=time.monotonic_ns, capture_lock=None, camera_utils=None):
        if not isinstance(camera_name, str) or not camera_name:
            raise ProtocolError("INVALID_SCHEMA", "camera name required")
        if type(width) is not int or type(height) is not int or min(width, height) <= 0:
            raise ProtocolError("INVALID_SCHEMA", "positive integer image dimensions required")
        self.world = world  # trusted capture adapter only; never passed to policy
        self.camera_name, self.width, self.height = camera_name, width, height
        self.capture_seq = 0
        self.T_world_base = fixed_robot_base(world) if T_world_base is None else rigid_transform(T_world_base, "T_world_base")
        self.T_base_world = rigid_transform(np.linalg.inv(self.T_world_base), "T_base_world")
        if calibration_version is not None and (not isinstance(calibration_version, str) or not calibration_version):
            raise ProtocolError("INVALID_SCHEMA", "calibration version must be nonempty")
        self._calibration_version = calibration_version
        self._clock, self._lock, self._utils = monotonic_ns, capture_lock, camera_utils
        self._last_capture_sim_s = self._last_capture_ns = None

    def _calibration(self, sim, intrinsics):
        if self._calibration_version is not None:
            return self._calibration_version
        # Static camera attachment/intrinsics, not the changing wrist world pose.
        model = sim.model
        camera_id = model.camera_name2id(self.camera_name)
        descriptor = {"camera_id": self.camera_name, "width_px": self.width, "height_px": self.height,
                      "intrinsics_K": intrinsics.tolist(), "T_world_base": self.T_world_base.tolist(),
                      "camera_position_parent_m": np.asarray(model.cam_pos[camera_id]).tolist(),
                      "camera_quaternion_parent_wxyz": np.asarray(model.cam_quat[camera_id]).tolist(),
                      "camera_parent": model.body_id2name(int(model.cam_bodyid[camera_id])),
                      "camera_calibration_source": "configured_simulator_camera_attachment_and_intrinsics"}
        return "camera-calibration:" + content_hash(descriptor)

    def capture(self) -> dict:
        with self._lock if self._lock is not None else nullcontext():
            if not getattr(self.world, "render_enabled", False):
                raise RuntimeError("LIBERO World must be created with render=True for RGB-D capture")
            sim = self.world.env.sim
            capture_sim_s = float(self.world.data.time)
            capture_ns = self._clock()
            if not np.isfinite(capture_sim_s) or capture_sim_s < 0 or type(capture_ns) is not int or capture_ns < 0:
                raise ProtocolError("INVALID_CLOCK", "invalid capture clock")
            if self._last_capture_sim_s is not None and (capture_sim_s < self._last_capture_sim_s
                    or capture_ns < self._last_capture_ns):
                raise ProtocolError("INVALID_CLOCK", "capture clock regressed; recreate source after reset")
            rendered = sim.render(width=self.width, height=self.height, camera_name=self.camera_name, depth=True)
            if not isinstance(rendered, tuple) or len(rendered) != 2:
                raise ProtocolError("UNSYNCHRONIZED_RGBD", "depth render must return (rgb, depth) from one exposure")
            raw_rgb, raw_depth = map(np.asarray, rendered)
            if raw_rgb.shape != (self.height, self.width, 3) or raw_rgb.dtype != np.uint8:
                raise ProtocolError("INVALID_SENSOR", "RGB must be HWC uint8 at requested size")
            if raw_depth.shape != (self.height, self.width) or not np.issubdtype(raw_depth.dtype, np.floating):
                raise ProtocolError("INVALID_SENSOR", "depth must be floating HW at requested size")
            if self._utils is None:
                from robosuite.utils import camera_utils
                self._utils = camera_utils
            # API order is height,width (essential for non-square captures).
            K = np.asarray(self._utils.get_camera_intrinsic_matrix(sim, self.camera_name, self.height, self.width), dtype=float)
            if K.shape != (3, 3) or not np.isfinite(K).all() or min(K[0, 0], K[1, 1]) <= 0 \
                    or not np.allclose(K[2], [0, 0, 1], atol=1e-9, rtol=0):
                raise ProtocolError("INVALID_CALIBRATION", "invalid camera intrinsics")
            T_world_camera = rigid_transform(self._utils.get_camera_extrinsic_matrix(sim, self.camera_name), "T_world_camera")
            rgb = _readonly(raw_rgb[::-1], dtype=np.uint8)
            depth = np.array(self._utils.get_real_depth_map(sim, np.array(raw_depth[::-1], copy=True)), dtype=np.float32, copy=True)
            if depth.shape != (self.height, self.width):
                raise ProtocolError("INVALID_SENSOR", "metric depth shape changed")
            # Missing/invalid depth remains unknown. Never substitute a target point.
            depth[~np.isfinite(depth) | (depth <= 0)] = np.nan
            depth.setflags(write=False)
            calibration = self._calibration(sim, K)
            if float(self.world.data.time) != capture_sim_s:
                raise ProtocolError("UNSYNCHRONIZED_RGBD", "simulation advanced during capture/calibration")
            self.capture_seq += 1
            self._last_capture_sim_s, self._last_capture_ns = capture_sim_s, capture_ns
            frame_id = f"{self.camera_name}:{self.capture_seq}"
            K = _readonly(K)
            T_base_camera = rigid_transform(self.T_base_world @ T_world_camera, "T_base_camera")
            return {
                "rgb": rgb, "depth_m": depth, "intrinsics_K": K, "T_base_camera": T_base_camera,
                "camera_id": self.camera_name, "frame_seq": self.capture_seq, "frame_id": frame_id,
                "calibration_version": calibration, "capture_sim_time_s": capture_sim_s,
                "capture_monotonic_ns": capture_ns, "width_px": self.width, "height_px": self.height,
                "depth_units": "m", "pixel_origin": "top_left", "frame": "robot_base",
                "provenance": "sensor-derived", "calibration_provenance": "known_camera_and_fixed_robot_base",
                "synchronization": "single_depth_render_tuple",
                # Explicit legacy aliases, not the base-frame perception contract.
                "intrinsics": K, "camera_to_world": T_world_camera, "camera_name": self.camera_name,
                "capture_seq": self.capture_seq, "capture_sim_time": capture_sim_s,
            }
