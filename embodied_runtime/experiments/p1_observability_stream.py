"""Experiment-local latest-frame RGB-D throughput, with honest unknown identity.

Capture runs independently of one geometry/persistence worker. Both views are
replaced atomically in a capacity-one pending slot. No simulator steps, semantic
models, annotation, task truth, or generic-runtime scheduling changes occur.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import threading
import time

import numpy as np

from ..contracts import canonical_json, require
from ..perception.recording import FrameRecorder
from ..perception.rgbd_geometry import GeometryConfig
from ..perception.surface_association import inventory_surfaces
from .p1_geometry_stream_probe import age_metrics
from .p1_rgbd_probe import identity


class LatestBundleSlot:
    """One pending synchronized bundle, in addition to the worker's active one."""

    def __init__(self):
        self._condition = threading.Condition()
        self._pending = None
        self._closed = False

    def put(self, item):
        with self._condition:
            require(not self._closed, "put into closed stream")
            replaced, self._pending = self._pending, item
            self._condition.notify()
            return replaced

    def take(self):
        with self._condition:
            self._condition.wait_for(lambda: self._pending is not None or self._closed)
            item, self._pending = self._pending, None
            return item

    def close(self):
        with self._condition:
            self._closed = True
            self._condition.notify_all()


def percentiles(values):
    return {"p50": float(np.percentile(values, 50)), "p95": float(np.percentile(values, 95))} if values else None


def run_latest_stream(capture, process, persist, *, duration_s, requested_hz,
                      free_age_s=0.3, contact_age_s=0.2,
                      log_capture=None, log_completed=None):
    """Return publication/persistence and drop evidence; never retime inputs.

    ``process`` returns a JSON-safe diagnostic result. Publication is an
    experiment-local completed snapshot, before durable persistence. Source
    frames replaced while queued are logged, not silently called processed.
    """
    require(duration_s > 0 and requested_hz > 0, "positive stream duration/rate")
    slot = LatestBundleSlot()
    records, captures, failures = [], [], []
    period_ns = round(1e9 / requested_hz)
    start = time.monotonic_ns()
    deadline = start + round(duration_s * 1e9)

    def worker():
        try:
            while (item := slot.take()) is not None:
                bundle = item["bundle"]
                began = time.monotonic_ns()
                result = process(bundle)
                publication = time.monotonic_ns()
                record = {k: v for k, v in item.items() if k != "bundle"}
                record.update(
                    geometry_started_monotonic_ns=began,
                    published_monotonic_ns=publication,
                    source_bundle_id=bundle["bundle_id"],
                    queue_wait_ms=(began-item["capture_finished_monotonic_ns"])/1e6,
                    geometry_pipeline_ms=(publication-began)/1e6,
                    end_to_end_ms=(publication-item["capture_started_monotonic_ns"])/1e6,
                    missed_cycle_deadline=publication > item["scheduled_monotonic_ns"]+period_ns,
                    result=result,
                    freshness=[dict(camera_id=v["camera_id"], frame_id=v["frame_id"],
                                    capture_monotonic_ns=v["capture_monotonic_ns"],
                                    capture_sim_time_s=v["capture_sim_time_s"],
                                    **age_metrics(v, publish_sim_time_s=bundle["capture_sim_time_s"],
                                                  publish_monotonic_ns=publication,
                                                  free_age_s=free_age_s, contact_age_s=contact_age_s))
                               for v in bundle["views"]],
                    valid_target_publication=False,
                )
                # Completed snapshot exists at publication; I/O is downstream.
                records.append(record)
                persist(bundle, record)
                record["persistence_finished_monotonic_ns"] = time.monotonic_ns()
                record["persistence_ms"] = (record["persistence_finished_monotonic_ns"]-publication)/1e6
                if log_completed is not None:
                    log_completed(record)
                record["journal_finished_monotonic_ns"] = time.monotonic_ns()
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=worker, name="p1-geometry-worker")
    thread.start()
    cycle = 0
    try:
        while time.monotonic_ns() < deadline and not failures:
            scheduled = start + cycle*period_ns
            wait_ns = scheduled-time.monotonic_ns()
            if wait_ns > 0:
                time.sleep(wait_ns/1e9)
            if time.monotonic_ns() >= deadline:
                break
            began = time.monotonic_ns()
            bundle = capture()
            finished = time.monotonic_ns()
            item = dict(bundle=bundle, capture_cycle=cycle+1,
                        scheduled_monotonic_ns=scheduled,
                        capture_started_monotonic_ns=began,
                        capture_finished_monotonic_ns=finished,
                        capture_ms=(finished-began)/1e6,
                        schedule_lag_ms=max(0, (began-scheduled)/1e6))
            replaced = slot.put(item)
            captures.append(dict(capture_cycle=cycle+1, source_bundle_id=bundle["bundle_id"],
                                 capture_started_monotonic_ns=began,
                                 capture_finished_monotonic_ns=finished,
                                 source_frame_ids=[v["frame_id"] for v in bundle["views"]],
                                 replaced_bundle_id=replaced["bundle"]["bundle_id"] if replaced else None,
                                 replaced_view_count=len(replaced["bundle"]["views"]) if replaced else 0))
            if log_capture is not None:
                log_capture(captures[-1])
            # Missed capture ticks are skipped, never burst-replayed.
            cycle = max(cycle+1, (finished-start)//period_ns+1)
    finally:
        capture_end = time.monotonic_ns()
        slot.close()
        thread.join()
    if failures:
        raise failures[0]
    end = time.monotonic_ns()
    publication_in_window = sum(r["published_monotonic_ns"] <= deadline for r in records)
    persisted_in_window = sum(r["persistence_finished_monotonic_ns"] <= deadline for r in records)
    journaled_in_window = sum(r["journal_finished_monotonic_ns"] <= deadline for r in records)
    fresh = [f for r in records for f in r["freshness"]]
    summary = dict(requested_hz=requested_hz, requested_duration_s=duration_s,
                   capture_elapsed_s=(capture_end-start)/1e9, drain_finished_elapsed_s=(end-start)/1e9,
                   captured_bundles=len(captures), published_snapshots=len(records),
                   captured_bundles_hz=len(captures)/((capture_end-start)/1e9),
                   publication_hz_in_measurement_window=publication_in_window/duration_s,
                   frames_persisted_hz_in_measurement_window=persisted_in_window/duration_s,
                   complete_persisted_hz_in_measurement_window=journaled_in_window/duration_s,
                   complete_persisted_hz_including_drain=len(records)/((end-start)/1e9),
                   queue_replacements=sum(c["replaced_bundle_id"] is not None for c in captures),
                   dropped_views=sum(c["replaced_view_count"] for c in captures),
                   missed_capture_ticks=max(0, cycle-len(captures)),
                   missed_cycle_deadlines=sum(r["missed_cycle_deadline"] for r in records),
                   pending_capacity_bundles=1, synchronized_views_replaced_atomically=True,
                   journal_io_included_in_drain_rate=True,
                   valid_target_hz=0.0, tracking_initialized=False,
                   semantic_identity="UNKNOWN", target_geometry_freshness_acceptance="NOT_EVALUATED_NO_SEED",
                   source_timestamps_rewritten=False, robot_motion_evaluated=False,
                   geometry_wall_age_s=percentiles([f["wall_age_s"] for f in fresh]),
                   geometry_sim_age_s=percentiles([f["sim_age_s"] for f in fresh]),
                   free_fresh_diagnostic_views=sum(f["free_geometry_fresh"] for f in fresh),
                   contact_fresh_diagnostic_views=sum(f["contact_geometry_fresh"] for f in fresh),
                   diagnostic_view_count=len(fresh),
                   publication_gap_ms=percentiles([(b["published_monotonic_ns"]-a["published_monotonic_ns"])/1e6
                                                   for a, b in zip(records, records[1:])]))
    for key in ("capture_ms", "queue_wait_ms", "geometry_pipeline_ms", "end_to_end_ms",
                "persistence_ms", "schedule_lag_ms"):
        summary[key] = percentiles([r[key] for r in records])
    return records, captures, summary


@dataclass(frozen=True)
class GeometryWorkload:
    geometry: GeometryConfig
    # Optional archived ROI windows are search diagnostics, never semantic seeds.
    search_rois: dict

    def __call__(self, bundle):
        from ..perception.reference_candidates import enumerate_reference_candidates

        rows = []
        for view in bundle["views"]:
            h, w = view["depth_m"].shape
            rois = dict(self.search_rois.get(view["camera_id"], {}))
            rois["scene_context"] = [0, 0, w, h]
            for name, roi in rois.items():
                began = time.monotonic_ns()
                if "reference" in name or name == "scene_context":
                    reference = enumerate_reference_candidates(view, roi, config=self.geometry, seed=0)
                    evidence = reference["inventory"]
                else:
                    reference = None
                    evidence = inventory_surfaces(view, roi, config=self.geometry, seed=0).evidence()
                rows.append(dict(camera_id=view["camera_id"], search_name=name,
                                 inventory=evidence, reference_candidates=reference,
                                 search_workload_ms=(time.monotonic_ns()-began)/1e6,
                                 semantic_identity="UNKNOWN", valid_target=False))
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--init-index", required=True, type=int, choices=[0, 12, 24])
    parser.add_argument("--search-rois", help="JSON camera→named ROI windows; diagnostic only")
    args = parser.parse_args()
    capture_config = json.loads(Path("configs/p1_capture.json").read_text())
    runtime = json.loads(Path("configs/p0_runtime.json").read_text())
    geometry_path = Path(capture_config["geometry_config"])
    require(hashlib.sha256(geometry_path.read_bytes()).hexdigest() ==
            "7f9795086d0406287aa60492a22dfd9f338c58c5cf5f25b0cab6316df1d57d85",
            "frozen geometry config changed")
    geometry = GeometryConfig.load(geometry_path)
    rois = json.loads(Path(args.search_rois).read_text()) if args.search_rois else {}
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(code=identity(), init_index=args.init_index, task="top_drawer", seed=1,
                    duration_s=30.0, requested_hz=10.0, pending_capacity_bundles=1,
                    camera_names=capture_config["camera_names"], width=384, height=256,
                    geometry_config=geometry.to_dict(), search_rois=rois,
                    search_rois_are_semantic_seeds=False, source_timestamps_rewritten=False,
                    annotation_inputs=False, target_oracle_inputs=False, semantic_models=False,
                    environment={name: os.environ.get(name) for name in
                                 ("MUJOCO_GL", "PYOPENGL_PLATFORM", "LIBGL_ALWAYS_SOFTWARE",
                                  "EGL_PLATFORM", "__EGL_VENDOR_LIBRARY_FILENAMES",
                                  "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")},
                    runtime_controls=0, reset_controls={"count": 10, "action": [0,0,0,0,0,0,-1]},
                    condition="live_static_latest_bundle_geometry_inventory_unknown_identity")
    (out/"manifest.json").write_text(canonical_json(manifest)+"\n")
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_sensor_env import LiberoSensorEnv
    backend = LiberoWorldBackend.from_task("top_drawer", seed=1, init_state_id=args.init_index, render=True)
    sensor = LiberoSensorEnv(backend.world, camera_names=capture_config["camera_names"], width=384, height=256,
                            retained_gripper_command=lambda: "OPEN" if backend.gripper_command() < 0 else "CLOSE")
    try:
        with (FrameRecorder(out/"frames", episode_id=f"p1-observability-stream/init{args.init_index}",
                            clock_domain="live-local-process", condition=manifest["condition"]) as recorder,
              (out/"cycles.jsonl").open("x") as cycle_log,
              (out/"captures.jsonl").open("x") as capture_log):
            def persist(bundle, record):
                recorder.append(bundle["views"], bundle["proprio"], emitted_monotonic_ns=time.monotonic_ns())

            def log_completed(record):
                cycle_log.write(canonical_json(record)+"\n")
                cycle_log.flush()

            def log_capture(record):
                capture_log.write(canonical_json(record)+"\n")
                capture_log.flush()

            records, captures, summary = run_latest_stream(
                sensor.sensor_port().capture, GeometryWorkload(geometry, rois), persist,
                duration_s=30.0, requested_hz=10.0, free_age_s=runtime["free_geometry_age_s"],
                contact_age_s=runtime["contact_geometry_age_s"],
                log_capture=log_capture, log_completed=log_completed)
        inventory_rows = [row for r in records for row in r["result"]]
        summary["single_search_workload_ms"] = percentiles([r["search_workload_ms"] for r in inventory_rows])
        summary["surface_plane_valid_counts"] = dict(Counter(s["plane_valid"] for row in inventory_rows
                                                           for s in row["inventory"]["surfaces"]))
        (out/"summary.json").write_text(canonical_json(summary)+"\n")
        print(json.dumps(summary, indent=2))
    except Exception as exc:
        (out/"failure.json").write_text(canonical_json({"error": repr(exc)})+"\n")
        raise
    finally:
        sensor.close()
        backend.world.close()


if __name__ == "__main__":
    main()
