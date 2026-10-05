"""Observational timing of complete sealed semantic-box geometry workloads.

No model is imported or called. Offline mode processes historical sensor frames;
live-static mode explicitly reuses frozen boxes as a workload cache, requires
identical observed RGB/depth/calibration, and never calls this fresh grounding.
All boxes and abstentions survive; no policy eligibility is inferred from age.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import os
from pathlib import Path
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.recording import FrameRecorder, replay_frames
from ..perception.rgbd_geometry import GeometryConfig, estimate_visible_patch

GEOMETRY_FILE_SHA256 = "7f9795086d0406287aa60492a22dfd9f338c58c5cf5f25b0cab6316df1d57d85"
GEOMETRY_CODE_SHA256 = "9050bbe7985a9f1e0de5017e04234993fb0a59c0ab75e7f5b1c49d739cd3df01"
ENTITIES = ("drawer_front_pushable", "fixed_cabinet_reference")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    return json.loads(Path(path).read_text())


def load_sealed_workload(directory, *, geometry_path="configs/p1_geometry.json"):
    """Validate completed raw prediction seal and source images, never read labels."""
    root = Path(directory)
    registration = _json(root/"preregistration.json")
    require(registration["registration_sha256"] == content_hash({k: v for k, v in registration.items() if k != "registration_sha256"}),
            "semantic registration hash differs", "CONDITION_CHANGED")
    require(registration["entity_order"] == list(ENTITIES) and registration["generator_inputs"] == ["RGB", "fixed_query"]
            and registration["for_execution"] is False, "not the fixed RGB-only condition", "CONDITION_CHANGED")
    seal, completed = _json(root/"predictions-sealed.json"), _json(root/"completed.json")
    require(seal["annotation_geometry_consumed"] is False and seal["runtime_actions"] == 0
            and completed["model_calls"] == seal["model_calls"] == registration["model_calls"],
            "incomplete or contaminated static source", "CONDITION_CHANGED")
    require(_sha(geometry_path) == GEOMETRY_FILE_SHA256 == registration["geometry_file_sha256"], "geometry configuration changed", "CONDITION_CHANGED")
    geometry_file = Path(__file__).parents[1]/"perception/rgbd_geometry.py"
    require(_sha(geometry_file) == GEOMETRY_CODE_SHA256 == registration["geometry_code_sha256"], "geometry implementation changed", "CONDITION_CHANGED")
    geometry = GeometryConfig.load(geometry_path)
    require(content_hash(geometry.to_dict()) == registration["geometry_resolved_sha256"], "resolved geometry changed")
    folders = sorted(root.glob("call-[0-9][0-9][0-9]"))
    require([p.name for p in folders] == [f"call-{i:03d}" for i in range(registration["model_calls"])], "semantic call coverage differs")
    predictions, requests = [], []
    for n, folder in enumerate(folders):
        request, prediction = _json(folder/"request.json"), _json(folder/"prediction.json")
        entity = ENTITIES[n % len(ENTITIES)]
        image_id = registration["image_order"][n//len(ENTITIES)]
        require(request["entity"] == prediction["entity"] == entity
                and request["image_id"] == prediction["image_id"] == image_id
                and request["frame_id"] == prediction["frame_id"]
                and request["query"] == prediction["query"] == registration["queries"][entity]
                and request["rgb_pixel_sha256"] == prediction["rgb_pixel_sha256"], "semantic request/response identity mismatch")
        require(type(prediction["structurally_admitted"]) is bool and isinstance(prediction["ordered_boxes"], list), "invalid sealed response schema")
        predictions.append(prediction)
        requests.append(request)
    require(content_hash(predictions) == seal["predictions_sha256"], "sealed predictions changed", "CONDITION_CHANGED")
    source = Path(registration["source"]["path"])
    require(_sha(source/"manifest.json") == registration["source"]["manifest_sha256"], "source manifest changed")
    for relative, digest in registration["source"]["recording_metadata_sha256"].items():
        path = (source/relative).resolve()
        require(path.is_relative_to(source.resolve()) and _sha(path) == digest, "source recording metadata changed")
    expected = {request["frame_id"]: request for request in requests}
    bundles, frames = {}, {}
    for folder in sorted(source.glob("init-*")):
        for envelope, views in replay_frames(folder):
            selected = [v for v in views if v["canonical_frame_id"] in expected]
            if not selected:
                continue
            require(len(selected) == len(views), "partial source bundle selection is not declared")
            refs = {r["camera_id"]: r for r in envelope.payload["views"]}
            for view in selected:
                key = view["canonical_frame_id"]
                request = expected[key]
                require(key not in frames and view["rgb"].shape[:2] == (request["height"], request["width"])
                        and hashlib.sha256(view["rgb"].tobytes()).hexdigest() == request["rgb_pixel_sha256"]
                        and refs[view["camera_id"]]["rgb_blob"]["sha256"] == request["rgb_blob_sha256"], "source image binding mismatch")
                frames[key] = view
            bundles[envelope.episode_id] = dict(bundle_id=envelope.message_id, capture_sim_time_s=envelope.payload["capture_sim_time_s"],
                                               views=tuple(selected), proprio=dict(envelope.payload["proprio"]))
    require(set(frames) == set(expected), "missing or duplicate sealed source frames")
    return dict(registration=registration, geometry=geometry, predictions=predictions,
                bundles=tuple(bundles.values()), frames=frames,
                seal_sha256=_sha(root/"predictions-sealed.json"), completed_sha256=_sha(root/"completed.json"),
                source_directory=str(source.resolve()), sealed_directory=str(root.resolve()))


def sensor_fingerprint(view):
    return content_hash(dict(camera_id=view["camera_id"], calibration_version=view["calibration_version"],
        rgb_shape=list(view["rgb"].shape), depth_shape=list(view["depth_m"].shape),
        rgb_sha256=hashlib.sha256(view["rgb"].tobytes()).hexdigest(),
        depth_sha256=hashlib.sha256(view["depth_m"].tobytes()).hexdigest(),
        K=np.asarray(view["intrinsics_K"]).tolist(), T=np.asarray(view["T_base_camera"]).tolist()))


def process_workload(bundle, predictions, geometry, *, source_frames, mode, clock_ns=time.monotonic_ns):
    """Timing wrapper only; identical geometry algorithm/thresholds/box order."""
    require(mode in {"offline", "live-static"}, "unknown timing mode")
    by_camera = {view["camera_id"]: view for view in bundle["views"]}
    rows = []
    for prediction in predictions:
        source = source_frames[prediction["frame_id"]]
        require(source["camera_id"] in by_camera, "semantic workload camera missing")
        view = by_camera[source["camera_id"]]
        if mode == "offline":
            require(view["canonical_frame_id"] == prediction["frame_id"], "offline source frame identity mismatch")
        else:
            require(sensor_fingerprint(view) == sensor_fingerprint(source),
                    "frozen ROI cache no longer bound to identical observed RGB-D/calibration", "FROZEN_WORKLOAD_MISMATCH")
        call_rows = []
        for index, roi in enumerate(prediction["ordered_boxes"]):
            started = clock_ns()
            patch, reason = None, None
            if not prediction["structurally_admitted"]:
                reason = "RESPONSE_NOT_ADMITTED"
            elif int(roi[2]) <= int(roi[0]) or int(roi[3]) <= int(roi[1]):
                reason = "NO_INTEGER_PIXEL_ROI_SUPPORT"
            else:
                patch = estimate_visible_patch(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
                    roi_xyxy=roi, source_frame_id=view["canonical_frame_id"] if mode == "offline" else view["frame_id"],
                    calibration_version=view["calibration_version"], track_id=prediction["entity"], feature_id=f"box-{index}",
                    capture_sim_time_s=view["capture_sim_time_s"], capture_monotonic_ns=view["capture_monotonic_ns"],
                    config=geometry, seed=0, eef_position_base_m=bundle["proprio"]["eef_position_base_m"]).to_dict()
            finished = clock_ns()
            value = dict(box_index=index, roi_xyxy=roi, patch=patch, for_execution=False, structural_reason=reason)
            if mode == "offline":
                require(value == prediction["geometry"][index], "frozen geometry replay differed", "GEOMETRY_REPLAY_MISMATCH")
            call_rows.append({**value, "single_roi_ms": (finished-started)/1e6,
                              "started_monotonic_ns": started, "finished_monotonic_ns": finished})
        rows.append(dict(entity=prediction["entity"], semantic_source_frame_id=prediction["frame_id"],
                         geometry_source_frame_id=view.get("canonical_frame_id", view["frame_id"]), camera_id=view["camera_id"],
                         query=prediction["query"], structurally_admitted=prediction["structurally_admitted"],
                         source_capture_sim_time_s=view["capture_sim_time_s"], source_capture_monotonic_ns=view["capture_monotonic_ns"],
                         ordered_box_count=len(prediction["ordered_boxes"]), abstained=not bool(prediction["ordered_boxes"]),
                         geometry=call_rows, semantic_cache_reused=mode == "live-static", for_execution=False))
    return rows


def _percentiles(values):
    return {"p50": float(np.percentile(values, 50)), "p95": float(np.percentile(values, 95)), "max": float(max(values))} if values else None


def run_timing_cycles(acquire, process, persist_payload, persist_completion, *, count, mode, duration_s=None,
                      requested_hz=10., free_age_s=.3, contact_age_s=.2,
                      clock_ns=time.monotonic_ns, sleep=time.sleep):
    """Serial diagnostic; completion sidecar records prior payload persistence.

    Published means an immutable serial-complete result is available here, not
    state-store/servo delivery. Receipt-fsync overhead is separate and included
    in achieved rate. Offline reads never become fresh acquisitions.
    """
    require((count is None or type(count) is int and count > 0) and requested_hz > 0, "invalid timing count/rate")
    require(duration_s is None or np.isfinite(duration_s) and duration_s > 0, "invalid duration")
    require(count is not None or duration_s is not None, "timing requires a count or duration bound")
    require(mode in {"offline", "live-static"}, "invalid timing condition")
    beginning = clock_ns()
    period = round(1e9/requested_hz)
    records, completions = [], []
    deadline = None if duration_s is None else beginning+round(duration_s*1e9)
    for cycle in range(count) if count is not None else itertools.count():
        if deadline is not None and clock_ns() >= deadline:
            break
        scheduled = beginning + cycle*period
        if mode == "live-static" and clock_ns() < scheduled:
            sleep((scheduled-clock_ns())/1e9)
        if deadline is not None and clock_ns() >= deadline:
            break
        began = clock_ns()
        bundle = acquire(cycle)
        acquired = clock_ns()
        rows = process(bundle, cycle)
        finished_geometry = clock_ns()
        for row in rows:
            if mode == "offline":
                row["freshness"] = {"evaluated": False, "reason": "OFFLINE_HISTORICAL_CAPTURE_CLOCK"}
            else:
                wall_age = (finished_geometry-row["source_capture_monotonic_ns"])/1e9
                sim_age = bundle["capture_sim_time_s"]-row["source_capture_sim_time_s"]
                require(wall_age >= 0 and sim_age >= 0, "negative source age")
                row["freshness"] = dict(evaluated=True, wall_age_s=wall_age, sim_age_s=sim_age,
                    free_geometry_fresh=max(wall_age,sim_age) <= free_age_s,
                    contact_geometry_fresh=max(wall_age,sim_age) <= contact_age_s,
                    does_not_certify_semantic_freshness_or_action_eligibility=True)
        record = dict(cycle=cycle+1, mode=mode, source_bundle_id=bundle["bundle_id"], scheduled_monotonic_ns=scheduled,
            started_monotonic_ns=began, input_ready_monotonic_ns=acquired, published_monotonic_ns=finished_geometry,
            acquisition_ms=(acquired-began)/1e6 if mode == "live-static" else None,
            historical_input_lookup_ms=(acquired-began)/1e6 if mode == "offline" else None,
            geometry_pipeline_ms=(finished_geometry-acquired)/1e6,
            capture_to_publication_ms=(finished_geometry-began)/1e6 if mode == "live-static" else None,
            input_ready_to_publication_ms=(finished_geometry-acquired)/1e6,
            scheduled_lag_ms=max(0,(began-scheduled)/1e6) if mode == "live-static" else None,
            missed_scheduled_deadline=finished_geometry > scheduled+period if mode == "live-static" else None,
            exceeds_100ms_processing_budget=(finished_geometry-acquired) > 100_000_000,
            result=rows, publication_scope="diagnostic_serial_result_available_no_runtime_install")
        persist_began = clock_ns()
        persist_payload(bundle, record)
        payload_finished = clock_ns()
        completion = dict(cycle=cycle+1, record_sha256=content_hash(record),
                          payload_persistence_started_monotonic_ns=persist_began,
                          payload_persistence_finished_monotonic_ns=payload_finished,
                          payload_persistence_ms=(payload_finished-persist_began)/1e6,
                          cycle_through_payload_persistence_ms=(payload_finished-began)/1e6)
        persist_completion(completion)
        receipt_finished = clock_ns()
        completions.append(completion)
        records.append(record)
        completion["completion_sidecar_persistence_ms"] = (receipt_finished-payload_finished)/1e6
    ended = clock_ns()
    elapsed = (ended-beginning)/1e9
    all_boxes = [box for record in records for row in record["result"] for box in row["geometry"]]
    publication_times = [r["published_monotonic_ns"] for r in records]
    summary = dict(mode=mode, cycles=len(records), measurement_elapsed_s=elapsed,
        complete_persisted_workload_cycles_hz=len(records)/elapsed if elapsed else None,
        requested_duration_s=duration_s, warmup_cycles=0,
        requested_hz=requested_hz if mode == "live-static" else None,
        hypothetical_processing_budget_hz=10., geometry_budget_misses=sum(r["exceeds_100ms_processing_budget"] for r in records),
        live_scheduled_deadline_misses=sum(r["missed_scheduled_deadline"] for r in records) if mode == "live-static" else None,
        box_count=len(all_boxes), abstained_calls=sum(row["abstained"] for r in records for row in r["result"]),
        single_roi_ms=_percentiles([row["single_roi_ms"] for row in all_boxes]),
        capture_to_publication_ms=_percentiles([r["capture_to_publication_ms"] for r in records]) if mode == "live-static" else None,
        geometry_pipeline_ms=_percentiles([r["geometry_pipeline_ms"] for r in records]),
        payload_persistence_ms=_percentiles([r["payload_persistence_ms"] for r in completions]),
        completion_sidecar_persistence_ms=_percentiles([r["completion_sidecar_persistence_ms"] for r in completions]),
        publication_gaps_ms=_percentiles([(b-a)/1e6 for a,b in zip(publication_times,publication_times[1:])]),
        geometry_status_counts=dict(Counter(box["patch"]["geometry_status"] if box["patch"] else "NOT_COMPUTED" for box in all_boxes)),
        free_fresh_ROIs=sum(row["ordered_box_count"] for r in records for row in r["result"] if row["freshness"].get("free_geometry_fresh")) if mode == "live-static" else None,
        contact_fresh_ROIs=sum(row["ordered_box_count"] for r in records for row in r["result"] if row["freshness"].get("contact_geometry_fresh")) if mode == "live-static" else None,
        model_calls=0, runtime_controls=0, source_timestamps_rewritten=False,
        fresh_semantic_grounding=False, live_wall_freshness_measured=mode == "live-static",
        semantic_boxes_condition="frozen_sealed_workload_cache" if mode == "live-static" else "same_historical_frame_sealed_outputs",
        temporal_sequence_acceptance=False, scheduling_changed=False)
    return records, completions, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sealed-run", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("offline", "live-static"), default="offline")
    parser.add_argument("--init-index", type=int, default=0)
    parser.add_argument("--live-duration-s", type=float, default=10.)
    args = parser.parse_args()
    loaded_at = time.monotonic_ns()
    workload = load_sealed_workload(args.sealed_run)
    loading_ms = (time.monotonic_ns()-loaded_at)/1e6
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    from .records import code_identity, versions
    manifest = dict(schema="p1-sealed-semantic-roi-timing/1", code=code_identity(), versions=versions(), mode=args.mode,
        sealed_run=workload["sealed_directory"], predictions_seal_sha256=workload["seal_sha256"],
        source_run=workload["source_directory"], registration_sha256=workload["registration"]["registration_sha256"],
        geometry_file_sha256=GEOMETRY_FILE_SHA256, geometry_code_sha256=GEOMETRY_CODE_SHA256,
        source_validation_and_loading_ms=loading_ms, geometry_config=workload["geometry"].to_dict(),
        requested_live_hz=10 if args.mode == "live-static" else None, live_duration_s=args.live_duration_s if args.mode == "live-static" else None,
        live_init_index=args.init_index if args.mode == "live-static" else None,
        model_calls=0, controls_after_standard_reset=0, roi_selection="all_ordered_sealed_model_boxes",
        publication_scope="diagnostic_serial_result_available_no_runtime_install", fsync_payloads=True,
        persistence_semantics="closed_frame_blob_files_and_flushed_frame_metadata_plus_fsynced_geometry_and_completion_logs")
    (output/"manifest.json").write_text(canonical_json(manifest)+"\n")
    sensor = backend = recorder = None
    try:
        bundles = workload["bundles"]
        if args.mode == "live-static":
            chosen = [b for b in bundles if b["bundle_id"].startswith(f"p1/init{args.init_index}/")]
            require(len(chosen) == 1, "requested static init absent")
            bundles = tuple(chosen)
            from ..adapters.libero import LiberoWorldBackend
            from ..adapters.libero_sensor_env import LiberoSensorEnv
            source_config = _json(Path(workload["source_directory"])/"manifest.json")["config"]
            backend = LiberoWorldBackend.from_task(source_config["task"], seed=source_config["seed"], init_state_id=args.init_index, render=True)
            sensor = LiberoSensorEnv(backend.world, camera_names=source_config["camera_names"], width=source_config["width"], height=source_config["height"],
                                    retained_gripper_command=lambda: "OPEN" if backend.gripper_command() < 0 else "CLOSE")
            recorder = FrameRecorder(output/"frames", episode_id=f"p1-frozen-roi-live/init{args.init_index}", clock_domain="local-process",
                                     condition="live_static_frozen_semantic_workload_cache_no_models_no_actions")
        workloads = []
        for bundle in bundles:
            keys = {v["canonical_frame_id"] for v in bundle["views"]}
            workloads.append([p for p in workload["predictions"] if p["frame_id"] in keys])
        with (output/"cycles.jsonl").open("x") as payload, (output/"persistence-completions.jsonl").open("x") as completions:
            def persist(bundle, record):
                if recorder is not None:
                    recorder.append(bundle["views"], bundle["proprio"], emitted_monotonic_ns=time.monotonic_ns())
                payload.write(canonical_json(record)+"\n")
                payload.flush()
                os.fsync(payload.fileno())

            def complete(record):
                completions.write(canonical_json(record)+"\n")
                completions.flush()
                os.fsync(completions.fileno())

            records, receipts, summary = run_timing_cycles(
                lambda cycle: sensor.capture() if sensor is not None else bundles[cycle],
                lambda bundle, cycle: process_workload(bundle, workloads[0 if sensor else cycle], workload["geometry"],
                                                       source_frames=workload["frames"], mode=args.mode),
                persist, complete, count=None if sensor else len(bundles), mode=args.mode,
                duration_s=args.live_duration_s if sensor else None)
        (output/"persistence-intervals.json").write_text(canonical_json(receipts)+"\n")
        (output/"summary.json").write_text(canonical_json(summary)+"\n")
        print(json.dumps(summary, indent=2))
    except Exception as exc:
        (output/"failure.json").write_text(canonical_json({"error": repr(exc), "partial": True})+"\n")
        raise
    finally:
        if recorder is not None:
            recorder.close()
        if sensor is not None:
            sensor.close()
        if backend is not None:
            backend.world.close()


if __name__ == "__main__":
    main()
