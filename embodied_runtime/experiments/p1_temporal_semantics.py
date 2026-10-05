"""Source-bound fixed-query semantic hypotheses for observation-only sequences.

Offline seeds are capture-time diagnostics, never fresh online observations.
T10 optionally records real asynchronous inference during original free-space
controls. No annotation input, query tuning, oracle state or runtime installation.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time

from ..contracts import canonical_json, require
from ..perception.recording import replay_frames
from .p1_semantic_grounding import QUERIES, _load_worker, classify_response, infer_audited


ROLES = {"drawer_front_pushable": "face", "fixed_cabinet_reference": "reference"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x") as stream:
        stream.write(canonical_json(value) + "\n")


def infer_views(worker, views, output, *, request_time_ns=None, deadline_ns=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    seeds, receipts = [], []
    for view in views:
        for entity, role in ROLES.items():
            folder = output / f"{view['camera_id']}-{role}"
            folder.mkdir()
            request_ns = time.monotonic_ns() if request_time_ns is None else request_time_ns
            request = dict(camera_id=view["camera_id"], source_frame_id=view.get("canonical_frame_id", view["frame_id"]),
                           raw_source_frame_id=view["frame_id"],
                           canonical_frame_id=view.get("canonical_frame_id"),
                           frame_seq=view["frame_seq"], calibration_version=view["calibration_version"],
                           capture_monotonic_ns=view["capture_monotonic_ns"], capture_sim_time_s=view["capture_sim_time_s"],
                           request_monotonic_ns=request_ns, deadline_monotonic_ns=deadline_ns,
                           query=QUERIES[entity], role=role, evaluation_labels_used=False,
                           rgb_sha256=hashlib.sha256(view["rgb"].tobytes()).hexdigest())
            write(folder / "request.json", request)
            raw, audit = infer_audited(worker, view["rgb"], QUERIES[entity],
                                       lambda kind, payload: write(folder / f"{kind}.json", payload))
            received_ns = time.monotonic_ns()
            height, width = view["rgb"].shape[:2]
            result = classify_response(raw, audit, width, height)
            record = {**request, "received_monotonic_ns": received_ns,
                      "deadline_expired": received_ns >= deadline_ns if deadline_ns is not None else None,
                      "source_wall_age_s": (received_ns-view["capture_monotonic_ns"])/1e9,
                      "raw_response": raw, "classification": result, "generation_audit": audit,
                      "seed_source": "real_model", "semantic_identity_verified": False}
            write(folder / "response.json", record)
            receipts.append(record)
            # A sequence diagnostic cannot silently select one of many boxes.
            if result["structurally_admitted"] and len(result["ordered_boxes"]) == 1:
                bound = {**record, "roi_xyxy_px": result["ordered_boxes"][0]}
                artifact = folder / "seed-artifact.json"
                write(artifact, bound)
                seeds.append({k: bound[k] for k in ("camera_id", "role", "source_frame_id", "roi_xyxy_px", "query")}
                             | {"artifact_uri": str(artifact.resolve()), "artifact_sha256": sha(artifact)})
    write(output / "responses-sealed.json", {"receipts": receipts, "model_calls": len(receipts),
                                             "evaluation_labels_used": False, "for_execution": False})
    return seeds, receipts


def seed_file(recording, seeds, output):
    write(output, {"condition": "real_model_seed", "recording_frames_sha256": sha(Path(recording)/"frames.jsonl"),
                   "seeds": seeds})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recordings-root")
    parser.add_argument("--case-ids", nargs="+", help="explicit offline subset; recorded in manifest")
    parser.add_argument("--output", required=True)
    parser.add_argument("--async-config")
    parser.add_argument("--static-evidence")
    parser.add_argument("--acquisition-output")
    args = parser.parse_args()
    require(bool(args.recordings_root) != bool(args.async_config), "choose offline recordings or actual async acquisition")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    from .records import code_identity, versions
    write(output / "manifest.json", {"code": code_identity(), "versions": versions(), "queries": QUERIES,
                                      "condition": "actual_async_T10" if args.async_config else "offline_initial_frame_diagnostic",
                                      "case_ids": args.case_ids,
                                      "evaluation_labels_used": False, "oracle_inputs": False, "for_execution": False})
    worker, model = _load_worker()
    write(output / "model.json", model)
    if not args.async_config:
        for case in sorted(Path(args.recordings_root).glob("T[0-9][0-9]")):
            if args.case_ids is not None and case.name not in args.case_ids:
                continue
            recording = case / "frames"
            require(recording.exists(), "case recording missing")
            _, views = next(replay_frames(recording))
            seeds, _ = infer_views(worker, views, output / case.name)
            seed_file(recording, seeds, output / case.name / "seeds.json")
    else:
        from .p1_temporal_probe import acquire
        require(args.static_evidence and args.acquisition_output, "async acquisition needs explicit config/evidence/output")
        config = json.loads(Path(args.async_config).read_text())
        require(config["case_id"] == "T10", "asynchronous case must be T10")
        future = None
        with ThreadPoolExecutor(max_workers=1) as executor:
            def observe(receipt, bundle):
                nonlocal future
                if future is None:
                    request_ns = time.monotonic_ns()
                    ttl_s = json.loads(Path("configs/p0_runtime.json").read_text())["proposal_ttl_s"]
                    views = [dict(view, canonical_frame_id=f"{receipt.episode_id}/{view['camera_id']}/{view['frame_seq']}")
                             for view in bundle["views"]]
                    future = executor.submit(infer_views, worker, views, output / "T10",
                                             request_time_ns=request_ns, deadline_ns=request_ns+round(ttl_s*1e9))
            summary = acquire(config, args.acquisition_output, static_evidence=args.static_evidence,
                              capture_observer=observe, observer_identity="p1_temporal_semantics_first_bundle_async_fixed_queries")
            require(future is not None, "no first capture request")
            seeds, receipts = future.result()
        seed_file(Path(args.acquisition_output)/"frames", seeds, output / "T10/seeds.json")
        write(output / "T10/async-completed.json", {"acquisition": summary, "responses": receipts,
              "actual_async_inference": True, "injected_delay": False, "online_tracker_installed": False,
              "deadline_source": "configs/p0_runtime.json proposal_ttl_s, recorded at request time"})


if __name__ == "__main__":
    main()
