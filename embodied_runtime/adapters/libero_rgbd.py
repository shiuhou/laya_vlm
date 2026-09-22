"""Real MuJoCo/LIBERO RGB-D capture with simulator calibration."""
from __future__ import annotations

import numpy as np


class LiberoRgbdSource:
    def __init__(self, world, *, camera_name: str = "agentview", width: int = 384, height: int = 384):
        self.world = world
        self.camera_name = camera_name
        self.width = int(width)
        self.height = int(height)
        self.capture_seq = 0

    def capture(self) -> dict:
        if not getattr(self.world, "render_enabled", False):
            raise RuntimeError("LIBERO World must be created with render=True for RGB-D capture")
        sim = self.world.env.sim
        rgb = np.asarray(sim.render(width=self.width, height=self.height, camera_name=self.camera_name), dtype=np.uint8)[::-1].copy()
        rendered_depth = sim.render(width=self.width, height=self.height, camera_name=self.camera_name, depth=True)
        if isinstance(rendered_depth, tuple):
            rendered_depth = rendered_depth[-1]
        raw_depth = np.asarray(rendered_depth, dtype=np.float32)[::-1].copy()
        from robosuite.utils.camera_utils import (
            get_camera_extrinsic_matrix,
            get_camera_intrinsic_matrix,
            get_real_depth_map,
        )
        K = np.asarray(get_camera_intrinsic_matrix(sim, self.camera_name, self.width, self.height), dtype=float)
        T = np.asarray(get_camera_extrinsic_matrix(sim, self.camera_name), dtype=float)
        depth_m = np.asarray(get_real_depth_map(sim, raw_depth), dtype=np.float32)
        self.capture_seq += 1
        return {
            "rgb": rgb, "depth_m": depth_m, "intrinsics": K, "camera_to_world": T,
            "camera_name": self.camera_name, "capture_seq": self.capture_seq,
            "capture_sim_time": float(self.world.data.time),
        }
