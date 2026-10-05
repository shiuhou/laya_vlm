"""Measure a continuous, read-only diagnostic RGB-D→geometry stream.

No physics steps after reset, semantic models, target truth or task verification.
This serial baseline reports missed timing/freshness honestly; it does not alter
runtime scheduling or pretend the frozen diagnostic ROIs are semantic targets.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from ..contracts import canonical_json, require
from ..perception.recording import FrameRecorder
from ..perception.rgbd_geometry import GeometryConfig, estimate_visible_patch
from .p1_rgbd_probe import identity


def age_metrics(
    view, *, publish_sim_time_s, publish_monotonic_ns, free_age_s, contact_age_s
):
    wall_age = (publish_monotonic_ns - view["capture_monotonic_ns"]) / 1e9
    sim_age = publish_sim_time_s - view["capture_sim_time_s"]
    require(wall_age >= 0 and sim_age >= 0, "publication precedes capture")
    age = max(wall_age, sim_age)
    return dict(
        wall_age_s=wall_age,
        sim_age_s=sim_age,
        conservative_age_s=age,
        free_geometry_fresh=age <= free_age_s,
        contact_geometry_fresh=age <= contact_age_s,
        freshness_does_not_certify_geometry=True,
    )


def run_stream(
    capture,
    process,
    persist,
    *,
    duration_s,
    requested_hz,
    clock_ns=time.monotonic_ns,
    sleep=time.sleep,
):
    """Injectable serial workload; source timestamps are never rewritten."""
    require(duration_s > 0 and requested_hz > 0, "positive stream duration/rate")
    start = clock_ns()
    period_ns = round(1e9 / requested_hz)
    deadline = start + round(duration_s * 1e9)
    records = []
    while clock_ns() < deadline:
        scheduled = start + len(records) * period_ns
        current = clock_ns()
        if current < scheduled:
            sleep((scheduled - current) / 1e9)
        if clock_ns() >= deadline:
            break
        began = clock_ns()
        bundle = capture()
        capture_finished = clock_ns()
        result = process(bundle)
        finished = clock_ns()
        record = dict(
            cycle=len(records) + 1,
            scheduled_monotonic_ns=scheduled,
            started_monotonic_ns=began,
            capture_finished_monotonic_ns=capture_finished,
            published_monotonic_ns=finished,
            source_bundle_id=bundle["bundle_id"],
            capture_ms=(capture_finished - began) / 1e6,
            geometry_pipeline_ms=(finished - capture_finished) / 1e6,
            end_to_end_ms=(finished - began) / 1e6,
            schedule_lag_ms=max(0, (began - scheduled) / 1e6),
            missed_cycle_deadline=finished > scheduled + period_ns,
            result=result,
        )
        persist(bundle, record)
        record["persistence_finished_monotonic_ns"] = clock_ns()
        records.append(record)
    end = clock_ns()
    elapsed = (end - start) / 1e9
    summary = dict(
        cycles=len(records),
        measurement_elapsed_s=elapsed,
        complete_persisted_cycles_hz=len(records) / elapsed if elapsed else 0,
        requested_hz=requested_hz,
        missed_cycle_deadlines=sum(r["missed_cycle_deadline"] for r in records),
        source_timestamps_rewritten=False,
        end_to_end_definition="capture_begin_to_geometry_publication; achieved rate includes persistence",
        warmup_cycles=0,
        includes_live_wall_freshness=True,
        robot_motion_evaluated=False,
        semantic_ROIs_evaluated=False,
    )
    for key in (
        "capture_ms",
        "geometry_pipeline_ms",
        "end_to_end_ms",
        "schedule_lag_ms",
    ):
        summary[key] = (
            {
                "p50": float(np.percentile([r[key] for r in records], 50)),
                "p95": float(np.percentile([r[key] for r in records], 95)),
            }
            if records
            else None
        )
    return records, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/p1_throughput.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    source = json.loads(Path(config["capture_config"]).read_text())
    runtime = json.loads(Path(config["runtime_config"]).read_text())
    geometry = GeometryConfig.load(source["geometry_config"])
    raw_geometry = Path(source["geometry_config"]).read_bytes()
    require(
        hashlib.sha256(raw_geometry).hexdigest()
        == "7f9795086d0406287aa60492a22dfd9f338c58c5cf5f25b0cab6316df1d57d85",
        "frozen geometry config changed",
    )
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    (out / "manifest.json").write_text(
        canonical_json(
            dict(
                code=identity(),
                config=config,
                capture_config=source,
                runtime_config=runtime,
                geometry_config=geometry.to_dict(),
                target_oracle_inputs=False,
                sensor_calibration_source="simulator_camera_setup_and_robot_owned_FK",
                reset_controls={"count": 10, "action": [0, 0, 0, 0, 0, 0, -1]},
                runtime_controls=0,
            )
        )
        + "\n"
    )
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_sensor_env import LiberoSensorEnv

    backend = LiberoWorldBackend.from_task(
        source["task"],
        seed=source["seed"],
        init_state_id=config["init_index"],
        render=True,
    )
    sensor = LiberoSensorEnv(
        backend.world,
        camera_names=source["camera_names"],
        width=source["width"],
        height=source["height"],
        retained_gripper_command=lambda: (
            "OPEN" if backend.gripper_command() < 0 else "CLOSE"
        ),
    )
    port = sensor.sensor_port()

    def process(bundle):
        patches = []
        for view in bundle["views"]:
            for name, roi in source["rois"][view["camera_id"]].items():
                start = time.monotonic_ns()
                patch = estimate_visible_patch(
                    view["depth_m"],
                    view["intrinsics_K"],
                    view["T_base_camera"],
                    roi_xyxy=roi,
                    source_frame_id=view["frame_id"],
                    calibration_version=view["calibration_version"],
                    track_id=f"{view['camera_id']}/{name}",
                    feature_id="diagnostic-visible-patch",
                    capture_sim_time_s=view["capture_sim_time_s"],
                    capture_monotonic_ns=view["capture_monotonic_ns"],
                    config=geometry,
                    seed=0,
                    eef_position_base_m=bundle["proprio"]["eef_position_base_m"],
                )
                patches.append(
                    dict(
                        camera_id=view["camera_id"],
                        roi_name=name,
                        patch=patch.to_dict(),
                        single_roi_ms=(time.monotonic_ns() - start) / 1e6,
                        source=view,
                    )
                )
        publication = time.monotonic_ns()
        for row in patches:
            view = row.pop("source")
            row["freshness"] = age_metrics(
                view,
                publish_sim_time_s=bundle["capture_sim_time_s"],
                publish_monotonic_ns=publication,
                free_age_s=runtime["free_geometry_age_s"],
                contact_age_s=runtime["contact_geometry_age_s"],
            )
        return patches

    try:
        with (
            FrameRecorder(
                out / "frames",
                episode_id="p1-continuous/init0",
                clock_domain="live-local-process",
                condition=config["condition"],
            ) as recorder,
            (out / "cycles.jsonl").open("x") as log,
        ):

            def persist(bundle, record):
                recorder.append(
                    bundle["views"],
                    bundle["proprio"],
                    emitted_monotonic_ns=time.monotonic_ns(),
                )
                log.write(canonical_json(record) + "\n")
                log.flush()

            records, summary = run_stream(
                port.capture,
                process,
                persist,
                duration_s=config["duration_s"],
                requested_hz=config["requested_hz"],
            )
        rows = [row for r in records for row in r["result"]]
        summary["roi_geometry_counts"] = dict(
            Counter(row["patch"]["geometry_status"] for row in rows)
        )
        summary["free_fresh_ROIs"] = sum(
            row["freshness"]["free_geometry_fresh"] for row in rows
        )
        summary["contact_fresh_ROIs"] = sum(
            row["freshness"]["contact_geometry_fresh"] for row in rows
        )
        summary["roi_count"] = len(rows)
        summary["single_roi_ms"] = (
            {
                "p50": float(np.percentile([r["single_roi_ms"] for r in rows], 50)),
                "p95": float(np.percentile([r["single_roi_ms"] for r in rows], 95)),
            }
            if rows
            else None
        )
        (out / "summary.json").write_text(canonical_json(summary) + "\n")
        print(json.dumps(summary, indent=2))
    except Exception as exc:
        (out / "failure.json").write_text(canonical_json({"error": repr(exc)}) + "\n")
        raise
    finally:
        sensor.close()
        backend.world.close()


if __name__ == "__main__":
    main()
