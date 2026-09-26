"""Fixed offline admission, sealed sensor worker, then separate evaluator.

Reads existing artifacts only. There is no simulator or rendering import.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from ..pixel_footprint import own_gripper_footprint
from .pixel_footprint_measurement import FRAME_KEYS, validate_topology
from .records import code_identity, file_hash

SOURCE_MANIFESTS = {
    "gripper-visual-mask-control-01": "4e0109bdf477cb579086b2a0fbe0f1cfea69fa7ccca89f1bfa47b93c478bdff5",
    "render-measurement-diagnosis-01": "e8852ee0a9162cd46acc3ea78ecfff6d7b6eccc10d3510ca62447cfaf570050c",
}
VISUAL_SHA256 = "c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98"
SAMPLES = [[.375, .125], [.875, .375], [.125, .625], [.625, .875]]
TOPOLOGY_SHA256 = None  # Must be frozen after the separately reviewed static export.


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def load_arrays(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def exact(a, b):
    return a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()


def hashes(directory):
    return {str(path.relative_to(directory)): file_hash(path)
            for path in sorted(directory.rglob("*")) if path.is_file()}


def statistics(values):
    values = np.asarray(values)
    if not len(values):
        return {"count": 0}
    return {"count": int(len(values)), "minimum": float(values.min()),
            "median": float(np.median(values)), "maximum": float(values.max()),
            "mean_absolute": float(np.abs(values).mean()),
            "maximum_absolute": float(np.abs(values).max())}


def evaluator(render, sensor_output, output, calibration, topology, source_measurements):
    """Called only after sensor-output-seal exists; cached poses stay here."""
    output.mkdir(exist_ok=False)
    results = {}
    for index, boundary in enumerate((24, 25)):
        label = f"sample{index}"
        native = load_arrays(render / f"native-before-{boundary}.npz")
        zero = load_arrays(render / f"zero-msaa-before-{boundary}.npz")
        own = {name: load_arrays(sensor_output / f"{label}-{name}.npz") for name in ("native", "center")}
        cached_poses = {row["geometry"]: row for row in source_measurements["states"][str(boundary)]["cache_vs_own_qpos"]
                        if row["family"] == "visual"}
        meshes = []
        for geom in calibration["geometries"]:
            pose = cached_poses[geom["name"]]
            vertices = np.asarray(geom["vertices_local_m"]) @ np.asarray(pose["cached_rotation_world"]).T + pose["cached_position_world_m"]
            meshes.append((vertices, topology["triangle_faces"][geom["name"]]))
        cached = {}
        cache_comparison = {}
        for condition, samples in (("native", SAMPLES), ("center", [[.5, .5]])):
            cached[condition] = own_gripper_footprint(native["depth_m"], native["intrinsics"],
                                                     native["camera_to_world"], meshes, samples)
            arrays = {key: value for key, value in cached[condition].items() if isinstance(value, np.ndarray)}
            np.savez_compressed(output / f"{label}-cached-{condition}.npz", **arrays)
            a, b = own[condition], cached[condition]
            both = a["potential_own_coverage"] & b["potential_own_coverage"]
            different = a["potential_own_coverage"] != b["potential_own_coverage"]
            cache_comparison[condition] = {
                "coverage_disagreement_samples": int(different.sum()),
                "coverage_disagreement_pixels": int(different.any(axis=-1).sum()),
                "cached_minus_own_depth_on_common_hits_m": statistics(b["potential_own_depth_m"][both] - a["potential_own_depth_m"][both]),
            }
        delta = zero["depth_m"].astype(float) - native["depth_m"].astype(float)
        count = own["native"]["covered_sample_count"]
        center = own["center"]["potential_own_coverage"][..., 0]
        by_coverage = {str(n): {str(bool(hit)).lower(): statistics(delta[(count == n) & (center == hit)])
                               for hit in (False, True)} for n in range(5)}
        witnesses = []
        for registered in source_measurements["states"][str(boundary)]["witnesses"]:
            entries = []
            for registered_pixel in registered["all_3x3_pixels"]:
                x, y = registered_pixel["pixel_xy"]
                entries.append({"pixel_xy": [x, y], "native_resolved_depth_m": float(native["depth_m"][y, x]),
                    "zero_minus_native_resolved_depth_m": float(delta[y, x]),
                    "own_native_sample_coverage": own["native"]["potential_own_coverage"][y, x].tolist(),
                    "own_center_coverage": bool(center[y, x]),
                    "cached_native_sample_coverage": cached["native"]["potential_own_coverage"][y, x].tolist(),
                    "cached_center_coverage": bool(cached["center"]["potential_own_coverage"][y, x, 0])})
            witnesses.append({"registered_center_xy": registered["center_pixel_xy"], "all_3x3_pixels": entries})
        results[str(boundary)] = {"zero_minus_native_depth_by_own_coverage_m": by_coverage,
                                  "cached_vs_own_qpos": cache_comparison, "fixed_witnesses": witnesses}
    write(output / "comparison.json", {"states": results, "ownership": "unknown",
          "interpretation": "potential own-triangle sample support; no GPU ownership/resolve or clearance claim"})


def run(sources, output):
    sources, output = Path(sources), Path(output)
    identity = code_identity()
    if identity["dirty_status"]:
        raise RuntimeError("Commit code and protocol before the fixed comparison")
    for directory, expected in SOURCE_MANIFESTS.items():
        path = sources / directory
        if file_hash(path / "artifacts.json") != expected:
            raise RuntimeError("Frozen source manifest mismatch: " + directory)
        for name, digest in read(path / "artifacts.json").items():
            if file_hash(path / name) != digest:
                raise RuntimeError("Source artifact mismatch: " + directory + "/" + name)
    visual_path = sources / "gripper-visual-calibration-01/gripper-visual-calibration.json"
    if file_hash(visual_path) != VISUAL_SHA256:
        raise RuntimeError("Frozen visual calibration mismatch")
    calibration = read(visual_path)
    topology_path = sources / "gripper-visual-triangle-topology-01/triangle-topology.json"
    if TOPOLOGY_SHA256 is None or file_hash(topology_path) != TOPOLOGY_SHA256:
        raise RuntimeError("Freeze and verify exact-gated own triangle topology before comparison")
    topology = read(topology_path)
    validate_topology(calibration, topology)
    prior = sources / "gripper-visual-mask-control-01/estimator-input"
    request = read(prior / "request.json")
    if request["visual_calibration"] != calibration:
        raise RuntimeError("Previously admitted calibration differs")
    render = sources / "render-measurement-diagnosis-01"
    recorded = read(render / "measurements.json")
    for name, digest in read(render / "output-seal.json")["sha256"].items():
        if file_hash(render / name) != digest:
            raise RuntimeError("Render output seal mismatch")
    for boundary in (24, 25):
        context = recorded["baseline"][str(boundary)]["context"]
        if context["gl"]["sample_positions_bottom_left_pixel_coordinates"] != SAMPLES or context["context_actual_offSamples"] != 4:
            raise RuntimeError("Native sample calibration mismatch")
    output.mkdir(parents=True, exist_ok=False)
    protocol = Path(__file__).resolve().parents[2] / "docs/research/pixel_sample_footprint_protocol.md"
    shutil.copyfile(protocol, output / "protocol.md")
    sensor_input, sensor_output = output / "sensor-input", output / "sensor-output"
    sensor_input.mkdir()
    write(sensor_input / "request.json", {"visual_calibration": calibration, "triangle_topology": topology,
        "own_joint_packets": request["own_joint_packets"], "samples_bottom_left": SAMPLES})
    for index, boundary in enumerate((24, 25)):
        frame = load_arrays(prior / f"sample{index}.npz")
        native = load_arrays(render / f"native-before-{boundary}.npz")
        if set(frame) != FRAME_KEYS or not all(exact(frame[key], native[key]) for key in FRAME_KEYS):
            raise RuntimeError("Sanitized native frame mismatch")
        np.savez_compressed(sensor_input / f"sample{index}.npz", **frame)
    write(output / "manifest.json", {"code": identity, "sources": str(sources),
        "source_manifest_hashes": SOURCE_MANIFESTS, "visual_calibration_sha256": VISUAL_SHA256,
        "triangle_topology_sha256": TOPOLOGY_SHA256, "real_calibration_topology_preflight": "passed",
        "protocol_sha256": file_hash(protocol), "sensor_input_sha256": hashes(sensor_input)})
    command = [sys.executable, "-m", "embodied_runtime.experiments.pixel_footprint_measurement",
               "--input", str(sensor_input), "--output", str(sensor_output)]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    write(output / "process.json", {"argv": command, "exit_code": process.returncode,
                                   "stdout": process.stdout, "stderr": process.stderr})
    if process.returncode:
        raise RuntimeError("Sensor worker failed; retained incomplete output")
    write(output / "sensor-output-seal.json", {"sha256": hashes(sensor_output),
          "evaluator_started": False, "cached_poses_admitted_to_sensor_worker": False})
    evaluator(render, sensor_output, output / "evaluator", calibration, topology, recorded)
    for name, digest in read(output / "sensor-output-seal.json")["sha256"].items():
        if file_hash(sensor_output / name) != digest:
            raise RuntimeError("Sensor output changed during evaluator")
    write(output / "artifacts.json", hashes(output))
    print(json.dumps({"status": "sealed", "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default="/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.sources, args.output)
