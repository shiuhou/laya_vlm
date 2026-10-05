"""Fresh-reset RGB-D recording, offline geometry and explicit seed diagnostics.

No policy, model calls, action choice or simulator target lookup. The existing
World constructor performs its standard ten reset-settling controls; after that
this probe never steps simulation. Evaluation labels are not model-facing input.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require, thaw
from ..perception.recording import FrameRecorder, replay_frames, project_base_points
from ..perception.rgbd_geometry import (
    GeometryConfig,
    estimate_visible_patch,
    project_depth,
)
from ..perception.visual_tracker import VisualTracker


def identity():
    from .records import code_identity

    result = code_identity()
    packages = {}
    for name in (
        "numpy",
        "mujoco",
        "robosuite",
        "Pillow",
        "opencv-python",
        "jev-libero",
        "libero",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    from .records import repository_identity

    external = {}
    for name, path in (
        ("jev-libero", "/home/junhongli/projects/jev-libero"),
        ("LIBERO", os.environ.get("LIBERO_ROOT", "/home/junhongli/projects/LIBERO")),
    ):
        external[name] = repository_identity(path) if Path(path).is_dir() else None
    result.update(
        python=sys.version,
        packages=packages,
        source_hashes={
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in Path("embodied_runtime").rglob("*.py")
        },
        external_repositories=external,
    )
    return result


def verify_reprojection(view, config):
    cloud = project_depth(
        view["depth_m"],
        view["intrinsics_K"],
        view["T_base_camera"],
        source_frame_id=view["frame_id"],
        calibration_version=view["calibration_version"],
        config=config,
    )
    points = cloud.points_base_m
    if not len(points):
        return {
            "status": "UNKNOWN",
            "reason": "NO_VALID_DEPTH",
            "check": "numeric_inverse_consistency_only",
        }
    index = np.arange(0, len(points), max(1, len(points) // 500))
    pixels = project_base_points(
        points[index], view["intrinsics_K"], view["T_base_camera"]
    )
    error = np.linalg.norm(pixels - cloud.pixels_uv[index], axis=1)
    require(float(error.max()) < 1e-6, "numeric reprojection error")
    return {
        "status": "PASS",
        "max_error_px": float(error.max()),
        "tested_points": len(index),
        "check": "numeric_inverse_consistency_only",
    }


def json_patch(patch):
    # Preserve every candidate and thaw immutable raw metrics without deepcopy.
    return patch.to_dict()


def process_recording(recording, config, geometry_config, *, init_index):
    records = []
    trackers = {}
    for env, views in replay_frames(recording):
        for view in views:
            # R4 frame identity is episode-scoped; the recorder retains the raw
            # capture identity separately. Never infer this alias implicitly.
            view = dict(
                view,
                source_capture_frame_id=view["frame_id"],
                frame_id=view["canonical_frame_id"],
            )
            camera = view["camera_id"]
            projection = verify_reprojection(view, geometry_config)
            for roi_name, roi in config["rois"][camera].items():
                started = time.perf_counter()
                diagnostic_patch = estimate_visible_patch(
                    view["depth_m"],
                    view["intrinsics_K"],
                    view["T_base_camera"],
                    roi_xyxy=roi,
                    source_frame_id=view["frame_id"],
                    calibration_version=view["calibration_version"],
                    track_id=f"{camera}/{roi_name}",
                    feature_id="visible-patch",
                    capture_sim_time_s=view["capture_sim_time_s"],
                    capture_monotonic_ns=view["capture_monotonic_ns"],
                    config=geometry_config,
                    seed=0,
                    eef_position_base_m=env.payload["proprio"]["eef_position_base_m"],
                )
                elapsed = (time.perf_counter() - started) * 1000
                record = dict(
                    init_index=init_index,
                    bundle_id=env.message_id,
                    camera_id=camera,
                    frame_id=view["frame_id"],
                    roi_name=roi_name,
                    roi_xyxy=roi,
                    roi_source=config["roi_source"],
                    projection=projection,
                    geometry_ms=elapsed,
                    diagnostic_patch=json_patch(diagnostic_patch),
                    source_capture_frame_id=view["source_capture_frame_id"],
                    rgb_sha256=hashlib.sha256(view["rgb"].tobytes()).hexdigest(),
                    depth_sha256=hashlib.sha256(view["depth_m"].tobytes()).hexdigest(),
                    processing_clock="offline_capture_time_no_latency_gate",
                )
                tracker = trackers.get((camera, roi_name))
                started = time.perf_counter()
                if tracker is None:
                    tracker = VisualTracker(
                        env.episode_id,
                        track_id=f"{camera}/{roi_name}",
                        feature_id="visible-patch",
                    )
                    trackers[(camera, roi_name)] = tracker
                    track = tracker.initialize(
                        view,
                        roi,
                        query=roi_name,
                        seed_source="manual_seed",
                        now_sim_time_s=view["capture_sim_time_s"],
                        now_monotonic_ns=view["capture_monotonic_ns"],
                    )
                else:
                    track = tracker.update(
                        view,
                        now_sim_time_s=view["capture_sim_time_s"],
                        now_monotonic_ns=view["capture_monotonic_ns"],
                    )
                record["tracker"] = thaw(track)
                record["tracker_ms"] = (time.perf_counter() - started) * 1000
                if track.status == "TRACKED":
                    if tuple(track.roi_xyxy_px) == tuple(roi):
                        record["patch"] = json_patch(diagnostic_patch)
                    else:
                        record["patch"] = json_patch(
                            estimate_visible_patch(
                                view["depth_m"],
                                view["intrinsics_K"],
                                view["T_base_camera"],
                                roi_xyxy=track.roi_xyxy_px,
                                source_frame_id=view["frame_id"],
                                calibration_version=view["calibration_version"],
                                track_id=track.track_id,
                                feature_id=track.feature_id,
                                capture_sim_time_s=view["capture_sim_time_s"],
                                capture_monotonic_ns=view["capture_monotonic_ns"],
                                config=geometry_config,
                                seed=0,
                                eef_position_base_m=env.payload["proprio"][
                                    "eef_position_base_m"
                                ],
                            )
                        )
                else:
                    record["patch"] = dict(
                        geometry_status="UNKNOWN",
                        candidates=[],
                        reason_codes=["TRACK_NOT_ACCEPTED", *track.reason_codes],
                        source_frame_id=view["frame_id"],
                        track_id=track.track_id,
                        feature_id=track.feature_id,
                    )
                records.append(record)
    return records


def contact_sheet(recordings, config, output, results, geometry_config):
    from PIL import Image, ImageDraw
    from ..perception.visualization import write_patch_diagnostics

    indexed = {
        (r["init_index"], r["camera_id"], r["frame_id"], r["roi_name"]): r
        for r in results
    }

    w, h = config["width"], config["height"]
    for camera in config["camera_names"]:
        cols = 5
        sheet = Image.new(
            "RGB",
            (cols * w, ((len(recordings) + cols - 1) // cols) * (h + 28)),
            "white",
        )
        draw = ImageDraw.Draw(sheet)
        for n, (idx, path) in enumerate(recordings):
            _, views = next(replay_frames(path))
            view = next(v for v in views if v["camera_id"] == camera)
            tile = Image.fromarray(view["rgb"])
            td = ImageDraw.Draw(tile)
            for label, roi in config["rois"][camera].items():
                td.rectangle(
                    roi, outline="red" if "drawer" in label else "cyan", width=2
                )
                record = indexed[(idx, camera, view["canonical_frame_id"], label)]
                write_patch_diagnostics(
                    output / "diagnostics" / f"init-{idx:03d}" / camera / label,
                    rgb=view["rgb"],
                    depth_m=view["depth_m"],
                    K=view["intrinsics_K"],
                    T_base_camera=view["T_base_camera"],
                    roi_xyxy=roi,
                    patch=record["diagnostic_patch"],
                    geometry_config=geometry_config,
                    source_frame_id=view["canonical_frame_id"],
                )
            x, y = (n % cols) * w, (n // cols) * (h + 28)
            sheet.paste(tile, (x, y))
            draw.text((x + 4, y + h + 4), f"init {idx} | {camera}", fill="black")
        sheet.save(output / f"{camera}-contact-sheet.png")


def stable_records(records):
    """Runtime is measured anew; all sensor-derived decisions must match exactly."""
    return [
        {k: v for k, v in r.items() if k not in {"geometry_ms", "tracker_ms"}}
        for r in records
    ]


def verify_replay(source, results):
    expected = [
        json.loads(line)
        for line in (source / "geometry.jsonl").read_text().splitlines()
    ]
    require(
        canonical_json(stable_records(expected))
        == canonical_json(stable_records(results)),
        "replayed geometry/tracking diverged",
        "REPLAY_DIVERGENCE",
    )
    return dict(
        status="PASS",
        records_compared=len(results),
        stable_results_sha256=content_hash(stable_records(results)),
        excluded_fields=["geometry_ms", "tracker_ms"],
    )


def table_plane_checks(results):
    from ..perception.plane_consistency import compare_planes

    groups = {}
    for r in results:
        if r["roi_name"] == "table_positive_control":
            groups.setdefault(r["bundle_id"], []).append(r)
    checks = []
    for bundle, rows in groups.items():
        require(len(rows) == 2, "two table views required for this diagnostic")
        result = compare_planes(
            rows[0]["diagnostic_patch"],
            rows[1]["diagnostic_patch"],
            first_camera_id=rows[0]["camera_id"],
            second_camera_id=rows[1]["camera_id"],
            same_plane_assumption="analyst_tabletop_ROIs_not_independently_validated",
        )
        checks.append(dict(bundle_id=bundle, comparison=thaw(result)))
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/p1_capture.json")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--init-indices",
        type=int,
        nargs="+",
        help="explicit development subset; recorded",
    )
    parser.add_argument(
        "--replay-only", help="existing recording probe root; no simulator loaded"
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="numeric replay without optional Pillow",
    )
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    if args.init_indices is not None:
        config["init_indices"] = args.init_indices
    geometry_config = GeometryConfig.load(config["geometry_config"])
    parent = None
    if args.replay_only:
        source = Path(args.replay_only)
        raw = (source / "manifest.json").read_bytes()
        parent = json.loads(raw)
        require(parent["config"] == config, "replay configuration differs from capture")
        require(
            content_hash(parent["geometry_config"])
            == content_hash(geometry_config.to_dict()),
            "replay geometry configuration differs",
        )
        parent = {
            "path": str(source.resolve()),
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "capture_code": parent["code"],
            "recording_metadata_hashes": {
                str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(source.glob("init-*/*.json*"))
            },
        }
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "code": identity(),
                "config": config,
                "config_hash": content_hash(config),
                "geometry_config": geometry_config.to_dict(),
                "condition": config["condition"],
                "parent_capture": parent,
                "processing_clock": "offline_capture_time_no_latency_gate",
                "reset_controls": {
                    "count": 10,
                    "action": [0, 0, 0, 0, 0, 0, -1],
                    "owner": "Jev World constructor; no policy controls after reset",
                },
                "oracle_inputs_to_perception": False,
                "runtime_actions_after_reset": 0,
                "roi_labels_independently_validated": False,
                "manual_seed_is_diagnostic": True,
            },
            indent=2,
        )
        + "\n"
    )
    recordings = []
    results = []
    try:
        for idx in config["init_indices"]:
            record_dir = out / f"init-{idx:03d}"
            if args.replay_only:
                record_dir = Path(args.replay_only) / f"init-{idx:03d}"
            else:
                from ..adapters.libero import LiberoWorldBackend
                from ..adapters.libero_sensor_env import LiberoSensorEnv

                backend = LiberoWorldBackend.from_task(
                    config["task"], seed=config["seed"], init_state_id=idx, render=True
                )
                sensor = None
                try:
                    sensor = LiberoSensorEnv(
                        backend.world,
                        camera_names=config["camera_names"],
                        width=config["width"],
                        height=config["height"],
                        retained_gripper_command=lambda: (
                            "OPEN" if backend.gripper_command() < 0 else "CLOSE"
                        ),
                    )
                    port = sensor.sensor_port()
                    with FrameRecorder(
                        record_dir,
                        episode_id=f"p1/init{idx}",
                        clock_domain="p1/local-process",
                        condition=config["condition"],
                    ) as rec:
                        for _ in range(config["frames_per_reset"]):
                            bundle = port.capture()
                            rec.append(
                                bundle["views"],
                                bundle["proprio"],
                                emitted_monotonic_ns=time.monotonic_ns(),
                            )
                finally:
                    if sensor:
                        sensor.close()
                    backend.world.close()
            recordings.append((idx, record_dir))
            records = process_recording(
                record_dir, config, geometry_config, init_index=idx
            )
            results.extend(records)
            with (out / "geometry.jsonl").open("a") as f:
                for record in records:
                    f.write(canonical_json(record) + "\n")
        if not args.no_images:
            contact_sheet(recordings, config, out, results, geometry_config)
        plane_checks = table_plane_checks(results)
        (out / "plane-consistency.json").write_text(canonical_json(plane_checks) + "\n")
        counts = Counter(
            (r["roi_name"], r["diagnostic_patch"]["geometry_status"]) for r in results
        )
        durations = [r["geometry_ms"] for r in results]
        summary = dict(
            init_indices=config["init_indices"],
            reset_camera_views=len(recordings) * len(config["camera_names"]),
            recorded_bundles=len({r["bundle_id"] for r in results}),
            recorded_camera_views=len({r["frame_id"] for r in results}),
            distinct_camera_rgb_depth_hashes=len(
                {(r["camera_id"], r["rgb_sha256"], r["depth_sha256"]) for r in results}
            ),
            fixed_roi_diagnostic_counts={
                f"{k[0]}/{k[1]}": v for k, v in counts.items()
            },
            tracked_patch_counts=dict(
                Counter(r["patch"]["geometry_status"] for r in results)
            ),
            tracker_counts=dict(Counter(r["tracker"]["status"] for r in results)),
            geometry_p50_ms=float(np.percentile(durations, 50)),
            geometry_p95_ms=float(np.percentile(durations, 95)),
            tracker_p95_ms=float(np.percentile([r["tracker_ms"] for r in results], 95)),
            reprojection_status_counts=dict(
                Counter(r["projection"]["status"] for r in results)
            ),
            numeric_inverse_consistency_max_error_px=max(
                (
                    r["projection"]["max_error_px"]
                    for r in results
                    if r["projection"]["status"] == "PASS"
                ),
                default=None,
            ),
            execution_usable_candidates=sum(
                c["usable_status"] == "USABLE"
                for r in results
                for c in r["patch"]["candidates"]
            ),
            real_temporal_sequences=False,
            independent_human_labels=False,
            official_success_evaluated=False,
            online_freshness_evaluated=False,
            positive_control_plane_counts=dict(
                Counter(p["comparison"]["status"] for p in plane_checks)
            ),
        )
        if args.replay_only:
            summary["replay_verification"] = verify_replay(
                Path(args.replay_only), results
            )
            require(
                canonical_json(plane_checks)
                == canonical_json(
                    json.loads(
                        (Path(args.replay_only) / "plane-consistency.json").read_text()
                    )
                ),
                "plane replay diverged",
                "REPLAY_DIVERGENCE",
            )
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
    except Exception as exc:
        (out / "failure.json").write_text(
            json.dumps({"error": repr(exc), "partial": True}, indent=2) + "\n"
        )
        raise


if __name__ == "__main__":
    main()
