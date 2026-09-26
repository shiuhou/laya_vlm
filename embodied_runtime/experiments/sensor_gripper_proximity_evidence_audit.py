"""Check sealed proximity files and summary arithmetic; never recompute FK/hulls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import digest, near, read_json, records, require


def audit(raw):
    manifest = read_json(raw / "manifest.json")
    require(not manifest["code"]["dirty_status"], "clean freeze")
    artifacts = read_json(raw / "artifacts.json")
    for name, expected in artifacts.items():
        require(digest(raw / name) == expected, "sealed artifact")
    seal = read_json(raw / "estimator-output-seal.json")
    for folder, key in (("estimator-input", "input_sha256"), ("estimator-output", "output_sha256")):
        require({p.name for p in (raw / folder).iterdir()} == set(seal[key]), "directory membership")
        for name, expected in seal[key].items():
            require(digest(raw / folder / name) == expected, "input/output seal")
    source, robot_source = Path(manifest["archive_source"]), Path(manifest["robot_calibration_source"])
    require(digest(source / "episodes.jsonl") == manifest["archive_sha256"], "source identity")
    require(digest(robot_source / "robot-calibration.json") == manifest["robot_calibration_sha256"], "robot identity")
    require(digest(robot_source / "archive-admission-map.json") == manifest["own_joint_admission_map_sha256"], "extraction map")
    source_rows = records(source)
    request = read_json(raw / "estimator-input/request.json")
    require(set(request) == {"calibration", "own_joint_packets"}, "request schema")
    require(set(request["own_joint_packets"]) == {"sample0", "sample1"}, "sample names")
    require(request["calibration"] == read_json(robot_source / "robot-calibration.json"), "calibration bytes")
    extraction = read_json(robot_source / "archive-admission-map.json")["own_qpos_flat_indices"]
    measured = read_json(raw / "estimator-output/measurements.json")
    results, witness_count = [], 0
    for metadata in read_json(raw / "preparation.json")["samples"]:
        label = metadata["sample"]
        capture, control = (source_rows[metadata[k]] for k in ("capture_seq", "own_joint_source_seq"))
        require(capture["record_id"] == metadata["capture_record_id"]
                and control["record_id"] == metadata["own_joint_source_record_id"], "source records")
        require(control["data"]["state_before"][0] == capture["data"]["capture_sim_time"], "archive time")
        require(request["own_joint_packets"][label] ==
                {name: control["data"]["state_before"][index] for name, index in extraction.items()}, "own packet")
        require(digest(source / metadata["artifact"]) == metadata["artifact_sha256"], "original frame")
        with np.load(source / metadata["artifact"], allow_pickle=False) as original, \
                np.load(raw / "estimator-input" / f"{label}.npz", allow_pickle=False) as frame, \
                np.load(raw / "estimator-output" / f"{label}-arrays.npz", allow_pickle=False) as arrays:
            require(set(frame.files) == {"depth_m", "intrinsics", "camera_to_world"}, "sensor-only NPZ")
            for field in frame.files:
                require(np.array_equal(frame[field], original[field]), "unchanged sensor arrays")
            depth, k, transform = frame["depth_m"], frame["intrinsics"], frame["camera_to_world"]
            valid = np.isfinite(depth) & (depth > 0)
            distance, mask = arrays["distance_to_proxy_m"], arrays["partial_gripper_mask"]
            names = measured[label]["geometry_names"]
            require(distance.shape == (*depth.shape, len(names)), "distance map shape")
            require(np.array_equal(valid, arrays["valid_depth_mask"]), "validity map")
            require(np.array_equal(mask, arrays["per_proxy_projected_masks"].any(axis=-1)), "mask union")
            require(np.isfinite(distance[valid]).all() and (distance[valid] >= 0).all()
                    and np.isnan(distance[~valid]).all(), "distance validity")
            require(measured[label]["valid_depth_pixels"] == int(valid.sum())
                    and measured[label]["partial_mask_pixels"] == int(mask.sum()), "pixel counts")
            for group_name, selected in (("all_valid_depth", valid), ("outside_partial_gripper_silhouette", valid & ~mask)):
                group = measured[label]["groups"][group_name]
                for name, result in [("union", group["union"]), *group["per_proxy"].items()]:
                    values = np.min(distance, axis=-1) if name == "union" else distance[..., names.index(name)]
                    require(result["point_count"] == int(selected.sum()), "group count")
                    near(list(result["quantiles_m"].values()), np.quantile(values[selected], [0, .01, .1, .5]), "quantiles")
                    for threshold, count in result["counts_at_or_below_m"].items():
                        require(count == int(np.count_nonzero(values[selected] <= float(threshold))), "threshold counts")
                    y, x = np.unravel_index(np.argmin(np.where(selected, values, np.inf)), depth.shape)
                    witness = result["nearest"]
                    require(witness["pixel_xy"] == [int(x), int(y)] and witness["distance_m"] == values[y, x], "nearest pixel")
                    require(witness["pixel_center_xy"] == [x+.5, y+.5] and witness["depth_m"] == depth[y, x], "pixel/depth convention")
                    point = transform[:3, :3] @ (np.linalg.solve(k, [x+.5, y+.5, 1.]) * depth[y, x]) + transform[:3, 3]
                    near(point, witness["point_world_m"], "witness backprojection")
                    near(np.linalg.norm(point-witness["closest_solid_proxy_point_world_m"]), witness["distance_m"], "point-pair distance")
                    proxy = names[int(np.argmin(distance[y, x]))] if name == "union" else name
                    require(witness["proxy"] == proxy, "proxy identity")
                    witness_count += 1
                best = np.argmin(distance[selected], axis=-1)
                minimum = np.min(distance[selected], axis=-1)
                for threshold, contributions in group["union"]["nearest_proxy_contributions_at_or_below_m"].items():
                    require(contributions == {name: int(np.count_nonzero((minimum <= float(threshold)) & (best == i)))
                                              for i, name in enumerate(names)}, "proxy contributions")
            residual = measured[label]["groups"]["outside_partial_gripper_silhouette"]
            results.append({"sample": label, "boundary": metadata["development_boundary"],
                "valid_pixels": int(valid.sum()), "partial_mask_pixels": int(mask.sum()),
                "residual_points": int((valid & ~mask).sum()),
                "residual_union_minimum_mm": residual["union"]["nearest"]["distance_m"]*1000,
                "residual_per_proxy_minimum_mm": {name: value["nearest"]["distance_m"]*1000
                                                  for name, value in residual["per_proxy"].items()}})
    return {"passed": True, "scope": "file/input identity, stored-map arithmetic, witness backprojection and point-pair distance only",
        "excluded": "no FK, hull-distance or silhouette rerun; no semantic labels or scene-clearance validation",
        "producer_commit": manifest["code"]["commit"], "artifacts_manifest_sha256": digest(raw / "artifacts.json"),
        "output_seal_sha256": digest(raw / "estimator-output-seal.json"), "artifact_count": len(artifacts),
        "witness_checks": witness_count, "samples": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.raw)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result))
