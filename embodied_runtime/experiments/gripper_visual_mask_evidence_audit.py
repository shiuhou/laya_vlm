"""Read-only visual-mask control audit; no FK, projection or distance rerun."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .information_boundary_audit import digest, near, read_json, require


def audit(raw):
    manifest = read_json(raw / "manifest.json")
    reference, visual_source = Path(manifest["reference_source"]), Path(manifest["visual_export_source"])
    require(not manifest["code"]["dirty_status"], "clean freeze")
    for directory in (raw, visual_source):
        for name, expected in read_json(directory / "artifacts.json").items():
            require(digest(directory / name) == expected, "artifact identity")
    seal = read_json(raw / "estimator-output-seal.json")
    for folder, key in (("estimator-input", "input_sha256"), ("estimator-output", "output_sha256")):
        require({p.name for p in (raw/folder).iterdir()} == set(seal[key]), "directory contents")
        for name, expected in seal[key].items():
            require(digest(raw/folder/name) == expected, "sealed bytes")
    for name, expected in manifest["reference_files_sha256"].items():
        require(digest(reference/name) == expected, "prior input/map identity")
        if not name.endswith("request.json"):
            require(digest(raw/"estimator-input"/Path(name).name) == expected, "exact byte copy")
    request = read_json(raw / "estimator-input/request.json")
    original = read_json(reference / "estimator-input/request.json")
    visual = read_json(visual_source / "gripper-visual-calibration.json")
    require(set(request) == {"visual_calibration", "own_joint_packets", "distance_proxy_names"}, "input schema")
    require(digest(visual_source / "gripper-visual-calibration.json") == manifest["visual_calibration_sha256"]
            and request["visual_calibration"] == visual, "static visual input")
    require(all(visual[k] == original["calibration"][k] for k in ("version", "bodies", "sites")), "shared own calibration")
    require(request["own_joint_packets"] == original["own_joint_packets"], "same own packets")
    names = request["distance_proxy_names"]
    require(names == [g["name"] for g in original["calibration"]["geometries"]], "distance column order")
    for step in read_json(visual_source/"constructor-audit-evaluator-only.json")["half_steps"]:
        require(step["before"] == step["after"] and step["unchanged"], "static constructor state")
    measured, results, witness_checks = read_json(raw/"estimator-output/measurements.json"), [], 0
    for label, result in measured.items():
        with np.load(raw/"estimator-input"/f"{label}.npz", allow_pickle=False) as frame, \
                np.load(raw/"estimator-input"/f"{label}-arrays.npz", allow_pickle=False) as prior, \
                np.load(raw/"estimator-output"/f"{label}-visual-mask.npz", allow_pickle=False) as output:
            require(set(frame.files) == {"depth_m", "intrinsics", "camera_to_world"}, "sensor schema")
            visual_mask, old, distance = output["visual_mask"], prior["partial_gripper_mask"], prior["distance_to_proxy_m"]
            require(np.array_equal(visual_mask, output["individual_visual_masks"].any(axis=-1)), "visual mask union")
            counts = {"old_collision": int(old.sum()), "new_visual": int(visual_mask.sum()),
                "newly_excluded": int((visual_mask & ~old).sum()), "newly_admitted": int((old & ~visual_mask).sum()),
                "intersection": int((old & visual_mask).sum())}
            require(counts == result["mask_counts"], "replacement counts")
            for group_name, mask in (("collision_mask_residual", old), ("visual_mask_residual", visual_mask)):
                eligible = prior["valid_depth_mask"] & ~mask
                group = result["groups"][group_name]
                for name, stats in [("union", group["union"]), *group["per_proxy"].items()]:
                    values = distance.min(axis=-1) if name == "union" else distance[..., names.index(name)]
                    require(stats["point_count"] == int(eligible.sum()), "residual count")
                    near(list(stats["quantiles_m"].values()), np.quantile(values[eligible], [0, .01, .1, .5]), "quantiles")
                    for threshold, count in stats["counts_at_or_below_m"].items():
                        require(count == int(np.count_nonzero(values[eligible] <= float(threshold))), "fixed counts")
                    y, x = np.unravel_index(np.argmin(np.where(eligible, values, np.inf)), mask.shape)
                    witness = stats["nearest"]
                    require(witness["pixel_xy"] == [int(x), int(y)] and witness["distance_m"] == values[y, x], "unchanged-map witness")
                    point = frame["camera_to_world"][:3, :3] @ (np.linalg.solve(frame["intrinsics"], [x+.5, y+.5, 1.]) * frame["depth_m"][y, x]) + frame["camera_to_world"][:3, 3]
                    near(point, witness["point_world_m"], "recorded point")
                    witness_checks += 1
                best, minimum = distance[eligible].argmin(axis=-1), distance[eligible].min(axis=-1)
                for threshold, counts in group["union"]["nearest_proxy_contributions_at_or_below_m"].items():
                    require(counts == {name: int(np.count_nonzero((minimum <= float(threshold)) & (best == i)))
                                      for i, name in enumerate(names)}, "union contributions")
            for name, value in result["old_nearest_witness_exclusion"].items():
                group = result["groups"]["collision_mask_residual"]
                stats = group["union"] if name == "union" else group["per_proxy"][name]
                require(value["old_nearest_pixel_xy"] == stats["nearest"]["pixel_xy"]
                        and value["old_distance_m"] == stats["nearest"]["distance_m"], "old witness identity")
                x, y = value["old_nearest_pixel_xy"]
                require(value["excluded_by_visual_mask"] == bool(visual_mask[y, x]), "old witness exclusion")
            new = result["groups"]["visual_mask_residual"]
            results.append({"sample": label, "mask_counts": result["mask_counts"],
                "new_union_minimum_mm": new["union"]["nearest"]["distance_m"]*1000,
                "new_union_witness": new["union"]["nearest"],
                "new_per_proxy_minimum_mm": {name: stats["nearest"]["distance_m"]*1000 for name, stats in new["per_proxy"].items()},
                "old_nearest_witness_exclusion": result["old_nearest_witness_exclusion"]})
    return {"passed": True, "producer_commit": manifest["code"]["commit"],
        "scope": "stored-map/mask arithmetic and input ownership; no FK, projection, distance or simulator rerun",
        "artifacts_manifest_sha256": digest(raw/"artifacts.json"), "output_seal_sha256": digest(raw/"estimator-output-seal.json"),
        "visual_calibration_sha256": manifest["visual_calibration_sha256"], "witness_checks": witness_checks, "samples": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); result = audit(args.raw)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": True, "witness_checks": result["witness_checks"], "samples": result["samples"]}))
