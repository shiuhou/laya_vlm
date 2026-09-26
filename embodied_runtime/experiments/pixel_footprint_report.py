"""Read-only stored-array checks and a fixed-witness footprint panel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .pixel_footprint_comparison import SAMPLES, exact, load_arrays, read, statistics, write
from .records import file_hash


def report(source, output):
    source, output = Path(source), Path(output)
    checks = []

    def check(name, condition):
        if not condition:
            raise ValueError("Stored footprint audit failed: " + name)
        checks.append(name)

    artifacts = read(source / "artifacts.json")
    for name, expected in artifacts.items():
        check("artifact " + name, file_hash(source / name) == expected)
    seal = read(source / "sensor-output-seal.json")
    for name, expected in seal["sha256"].items():
        check("sensor seal " + name, file_hash(source / "sensor-output" / name) == expected)
    check("sealed before evaluator", seal["evaluator_started"] is False)
    check("cached data not admitted", seal["cached_poses_admitted_to_sensor_worker"] is False)
    manifest = read(source / "manifest.json")
    check("real calibration schema preflight", manifest["real_calibration_topology_preflight"] == "passed")
    check("worker exit 0", read(source / "process.json")["exit_code"] == 0)
    measurements = read(source / "sensor-output/measurements.json")
    comparison = read(source / "evaluator/comparison.json")
    render = Path(manifest["sources"]) / "render-measurement-diagnosis-01"
    panels = []
    for index, boundary in enumerate((24, 25)):
        label = f"sample{index}"
        frame = load_arrays(render / f"native-before-{boundary}.npz")
        zero = load_arrays(render / f"zero-msaa-before-{boundary}.npz")
        own, cached = {}, {}
        for name, samples in (("native", 4), ("center", 1)):
            own[name] = load_arrays(source / "sensor-output" / f"{label}-{name}.npz")
            cached[name] = load_arrays(source / "evaluator" / f"{label}-cached-{name}.npz")
            for family, arrays in (("own", own[name]), ("cached", cached[name])):
                prefix = f"{boundary}/{name}/{family}"
                check(prefix + " scalar exact", exact(arrays["resolved_depth_m"], frame["depth_m"]))
                coverage, depth = arrays["potential_own_coverage"], arrays["potential_own_depth_m"]
                check(prefix + " shape", coverage.shape == (*frame["depth_m"].shape, samples))
                check(prefix + " depth coverage", np.array_equal(coverage, np.isfinite(depth)) and (depth[coverage] > 0).all())
                check(prefix + " count", np.array_equal(arrays["covered_sample_count"], coverage.sum(axis=-1)))
                check(prefix + " optical ray", (arrays["sample_rays_camera"][..., 2] == 1).all())
                check(prefix + " own index", (arrays["nearest_own_geometry_index"][~coverage] == -1).all()
                      and ((arrays["nearest_own_geometry_index"][coverage] >= 0)
                           & (arrays["nearest_own_geometry_index"][coverage] < 3)).all())
            both = own[name]["potential_own_coverage"] & cached[name]["potential_own_coverage"]
            different = own[name]["potential_own_coverage"] != cached[name]["potential_own_coverage"]
            recorded = comparison["states"][str(boundary)]["cached_vs_own_qpos"][name]
            check(f"{boundary}/{name} cache count", int(different.sum()) == recorded["coverage_disagreement_samples"]
                  and int(different.any(axis=-1).sum()) == recorded["coverage_disagreement_pixels"])
            check(f"{boundary}/{name} cache depth", statistics(cached[name]["potential_own_depth_m"][both]
                  - own[name]["potential_own_depth_m"][both]) == recorded["cached_minus_own_depth_on_common_hits_m"])
        count, center = own["native"]["covered_sample_count"], own["center"]["potential_own_coverage"][..., 0]
        delta = zero["depth_m"].astype(float) - frame["depth_m"].astype(float)
        for n in range(5):
            for hit in (False, True):
                selected = (count == n) & (center == hit)
                key = str(hit).lower()
                check(f"{boundary}/{n}/{key} count", int(selected.sum()) == measurements[label]["coverage_by_native_count_and_center"][str(n)][key])
                check(f"{boundary}/{n}/{key} depth", statistics(delta[selected]) == comparison["states"][str(boundary)]["zero_minus_native_depth_by_own_coverage_m"][str(n)][key])
        for witness in comparison["states"][str(boundary)]["fixed_witnesses"]:
            x, y = witness["registered_center_xy"]
            check(f"{boundary}/{x}/{y} all neighbors", [p["pixel_xy"] for p in witness["all_3x3_pixels"]]
                  == [[xx, yy] for yy in range(y - 1, y + 2) for xx in range(x - 1, x + 2)])
            for p in witness["all_3x3_pixels"]:
                xx, yy = p["pixel_xy"]
                check(f"{boundary}/{xx}/{yy} stored witness", p["own_native_sample_coverage"] == own["native"]["potential_own_coverage"][yy, xx].tolist()
                      and p["own_center_coverage"] == bool(center[yy, xx])
                      and p["cached_native_sample_coverage"] == cached["native"]["potential_own_coverage"][yy, xx].tolist()
                      and p["cached_center_coverage"] == bool(cached["center"]["potential_own_coverage"][yy, xx, 0])
                      and p["native_resolved_depth_m"] == float(frame["depth_m"][yy, xx])
                      and p["zero_minus_native_resolved_depth_m"] == float(delta[yy, xx]))
        panels.append((boundary, frame, comparison["states"][str(boundary)]["fixed_witnesses"]))
    output.mkdir(parents=True, exist_ok=True)
    write(output / "pixel_sample_footprint_summary.json", {
        "raw_directory": str(source), "producer_commit": manifest["code"]["commit"],
        "protocol_sha256": manifest["protocol_sha256"], "triangle_topology_sha256": manifest["triangle_topology_sha256"],
        "raw_artifact_hashes": artifacts, "post_seal_checks_passed": len(checks),
        "own_coverage_summary": measurements, "separate_evaluator_comparison": comparison,
        "limits": ["development frames", "potential own contribution only; ownership unknown",
                   "native scalar unchanged; no depth-resolve rule", "no clearance, contact or candidate gate"],
    })
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 6, figsize=(15, 7.6))
    fig.subplots_adjust(left=.025, right=.99, bottom=.025, top=.86, hspace=.45, wspace=.12)
    for row, (boundary, frame, witnesses) in enumerate(panels):
        for col in range(6):
            ax = axes[row, col]
            if col >= len(witnesses):
                ax.axis("off")
                continue
            p = witnesses[col]["all_3x3_pixels"][4]
            x, y = p["pixel_xy"]
            ax.imshow(frame["rgb"][y-1:y+2, x-1:x+2], extent=(x-1, x+2, y+2, y-1), interpolation="nearest")
            for (sx, sy), hit in zip(SAMPLES, p["own_native_sample_coverage"]):
                ax.plot(x+sx, y+1-sy, "o", ms=9, mfc="#00bfff" if hit else "#ffa600", mec="black", mew=.7)
            ax.plot(x+.5, y+.5, "x", color="white", ms=8, mew=1.7)
            ax.set_title(f'{boundary}: ({x},{y})  {sum(p["own_native_sample_coverage"])}/4 samples\nCenter {"hit" if p["own_center_coverage"] else "miss"}; Δz {1000*p["zero_minus_native_resolved_depth_m"]:+.1f} mm', fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
    fig.suptitle("Fixed witnesses: potential own-gripper sample contribution; observed ownership unknown\nBlue: modeled triangle hit · Orange: no modeled triangle hit · White ×: center ray", fontsize=12)
    fig.savefig(output / "pixel_sample_footprint_witnesses.png", dpi=170)
    plt.close(fig)
    print(json.dumps({"checks_passed": len(checks), "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report(args.source, args.output)
