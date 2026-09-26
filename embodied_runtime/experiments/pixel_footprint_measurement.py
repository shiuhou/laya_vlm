"""Sensor-only worker: own joints/triangles and native depth/camera calibration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..pixel_footprint import own_gripper_footprint
from .robot_only_geometry import forward

FRAME_KEYS = {"depth_m", "intrinsics", "camera_to_world"}


def measure(calibration, own_joints, frame, samples):
    if set(frame) != FRAME_KEYS:
        raise ValueError("Only resolved depth and optical camera calibration admitted")
    poses = forward(calibration, own_joints)["geometries"]
    meshes = [(poses[geom["name"]]["vertices_world_m"], geom["faces"])
              for geom in calibration["geometries"]]
    return own_gripper_footprint(frame["depth_m"], frame["intrinsics"],
                                 frame["camera_to_world"], meshes, samples)


def worker(source, output):
    source, output = Path(source), Path(output)
    request = json.loads((source / "request.json").read_text())
    if set(request) != {"visual_calibration", "own_joint_packets", "samples_bottom_left"}:
        raise ValueError("Strict own-joint/triangle/sample metadata boundary required")
    calibration = request["visual_calibration"]
    if len(calibration["geometries"]) != 3 or set(request["own_joint_packets"]) != {"sample0", "sample1"}:
        raise ValueError("Fixed three-gripper-mesh, two-frame comparison required")
    if np.asarray(request["samples_bottom_left"]).shape != (4, 2):
        raise ValueError("Calibrated four-sample positions required")
    output.mkdir(exist_ok=False)
    summaries = {}
    for label, joints in request["own_joint_packets"].items():
        with np.load(source / f"{label}.npz", allow_pickle=False) as archive:
            frame = {key: archive[key] for key in archive.files}
        results = {}
        for condition, samples in (("native", request["samples_bottom_left"]), ("center", [[.5, .5]])):
            result = measure(calibration, joints, frame, samples)
            if result["resolved_depth_m"].dtype != frame["depth_m"].dtype or result["resolved_depth_m"].tobytes() != frame["depth_m"].tobytes():
                raise RuntimeError("Native scalar representation changed")
            arrays = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
            np.savez_compressed(output / f"{label}-{condition}.npz", **arrays)
            results[condition] = result
        counts = results["native"]["covered_sample_count"]
        center = results["center"]["potential_own_coverage"][..., 0]
        summaries[label] = {
            "coverage_by_native_count_and_center": {
                str(count): {str(bool(hit)).lower(): int(((counts == count) & (center == hit)).sum())
                             for hit in (False, True)} for count in range(5)},
            "conditions": {name: {key: value for key, value in result.items() if not isinstance(value, np.ndarray)}
                           for name, result in results.items()},
            "own_geometry_names": [geom["name"] for geom in calibration["geometries"]],
        }
    with (output / "measurements.json").open("x") as stream:
        json.dump(summaries, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    worker(args.input, args.output)
