"""Preregistered RGB-only grounding with a prior independent annotation gate.

prepare writes the exact condition before labels or model calls. run requires
complete, source-bound human self-attestations before even importing the model
loader. Human polygons are used only after every prediction has been sealed.
No control, simulator, Qwen, Laya, retry, query tuning or candidate selection.

After the annotation gate passes and GPU availability has been rechecked, use
an explicitly allocated GPU in the dedicated environment, for example:
CUDA_VISIBLE_DEVICES=2 /home/junhongli/miniforge3/envs/locateanything/bin/python
    -m embodied_runtime.experiments.p1_semantic_grounding run ...
The selected physical GPU is logical cuda:0 inside that fresh process. No GPU
is selected automatically. Allocation is run metadata, not an experimental
query, model, annotation, or geometry condition.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.evaluation_annotations import (
    ENTITIES, PREDICTION_SCHEMA, _inside, evaluate_grounding, image_binding,
    load_packet, validate_annotations,
)
from ..perception.recording import project_base_points, replay_frames
from ..perception.rgbd_geometry import GeometryConfig, estimate_visible_patch
from .point_grounding_probe import SETTINGS, generation_audit, parse_grounding

VERSION = "p1-fixed-query-grounding/2"
CLASSIFICATION = "ordered-complete-boxes-or-explicit-abstention/1"
MODEL_PATH = "/home/junhongli/models/huggingface/LocateAnything-3B"
MODEL_CONTENT_ID = "4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f"
GEOMETRY_REVISION = "92865a89fd5905cc7345fbc4966d5edc5f44eb08"
GEOMETRY_FILE_SHA256 = "7f9795086d0406287aa60492a22dfd9f338c58c5cf5f25b0cab6316df1d57d85"
GEOMETRY_RESOLVED_SHA256 = "f3abcfd935087aa5992df6419bac6068b49fadc782e51b841ffc557808ef5da8"
GEOMETRY_CODE_SHA256 = "9050bbe7985a9f1e0de5017e04234993fb0a59c0ab75e7f5b1c49d739cd3df01"
QUERIES = {
    "drawer_front_pushable": "the flat outward-facing front panel of the open top drawer of the small cabinet on the tabletop, excluding its handle, inner cavity, rim, and tabletop",
    "fixed_cabinet_reference": "the fixed front-facing frame of the small tabletop cabinet immediately surrounding the open top drawer, excluding the moving drawer, its handle, the drawer interior, the tabletop, and the kitchen cabinets in the background",
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(value)+"\n")


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, "UTC timestamp required")
    return parsed


def frozen_geometry(path):
    require(_sha(path) == GEOMETRY_FILE_SHA256, "geometry differs from frozen 92865a8", "CONDITION_CHANGED")
    require(_sha(Path(__file__).parents[1]/"perception"/"rgbd_geometry.py") == GEOMETRY_CODE_SHA256,
            "geometry implementation differs from frozen 92865a8", "CONDITION_CHANGED")
    config = GeometryConfig.load(path)
    require(content_hash(config.to_dict()) == GEOMETRY_RESOLVED_SHA256, "resolved geometry changed", "CONDITION_CHANGED")
    return config


def source_binding(directory):
    root = Path(directory).resolve()
    return {"path": str(root), "manifest_sha256": _sha(root/"manifest.json"),
            "recording_metadata_sha256": {str(p.relative_to(root)): _sha(p)
                                          for p in sorted(root.glob("init-*/*.json*"))}}


def preregister(packet_dir, source_run, output, *, geometry_path="configs/p1_geometry.json",
                annotation_upper_bound=False):
    """No annotation input exists here. Existing registrations are never overwritten."""
    manifest = load_packet(packet_dir)
    config = frozen_geometry(geometry_path)
    source = source_binding(source_run)
    require(source["manifest_sha256"] == manifest["source_run_manifest_sha256"], "packet source differs")
    registration = dict(schema=VERSION, created_at_utc=_utc(), dataset_id=manifest["dataset_id"],
                        packet_manifest_sha256=_sha(Path(packet_dir)/"manifest.json"), source=source,
                        annotation_rules_version=manifest["rules_version"], annotation_rules_sha256=manifest["rules_sha256"],
                        queries=QUERIES, entity_order=list(ENTITIES), generation_settings=SETTINGS,
                        classification_version=CLASSIFICATION, model_path=MODEL_PATH,
                        model_content_id=MODEL_CONTENT_ID, geometry_commit=GEOMETRY_REVISION,
                        geometry_file_sha256=GEOMETRY_FILE_SHA256,
                        geometry_code_sha256=GEOMETRY_CODE_SHA256,
                        geometry_resolved_sha256=content_hash(config.to_dict()),
                        model_calls=2*len(manifest["images"]), image_order=[r["image_id"] for r in manifest["images"]],
                        annotation_conditioned_upper_bound=bool(annotation_upper_bound),
                        generator_inputs=["RGB", "fixed_query"], for_execution=False)
    registration["registration_sha256"] = content_hash(registration)
    _write(output, registration)
    return registration


def validate_gate(packet_dir, annotation_path, registration_path, *, geometry_path="configs/p1_geometry.json"):
    """Complete all source/label/chronology checks before model import or load."""
    registration = json.loads(Path(registration_path).read_text())
    require(registration.get("registration_sha256") == content_hash({k: v for k, v in registration.items() if k != "registration_sha256"}),
            "registration changed", "CONDITION_CHANGED")
    require(registration["schema"] == VERSION and registration["queries"] == QUERIES
            and registration["generation_settings"] == SETTINGS and registration["entity_order"] == list(ENTITIES)
            and registration["classification_version"] == CLASSIFICATION
            and registration["model_path"] == MODEL_PATH and registration["model_content_id"] == MODEL_CONTENT_ID
            and registration["generator_inputs"] == ["RGB", "fixed_query"] and registration["for_execution"] is False,
            "registered condition differs", "CONDITION_CHANGED")
    manifest = load_packet(packet_dir)
    require(registration["dataset_id"] == manifest["dataset_id"]
            and registration["packet_manifest_sha256"] == _sha(Path(packet_dir)/"manifest.json")
            and registration["annotation_rules_version"] == manifest["rules_version"]
            and registration["annotation_rules_sha256"] == manifest["rules_sha256"], "packet changed", "CONDITION_CHANGED")
    require(registration["source"] == source_binding(registration["source"]["path"])
            and registration["source"]["manifest_sha256"] == manifest["source_run_manifest_sha256"], "capture source changed")
    config = frozen_geometry(geometry_path)
    require(registration["geometry_file_sha256"] == GEOMETRY_FILE_SHA256
            and registration["geometry_code_sha256"] == GEOMETRY_CODE_SHA256
            and registration["geometry_resolved_sha256"] == GEOMETRY_RESOLVED_SHA256
            and registration["geometry_commit"] == GEOMETRY_REVISION, "geometry registration changed")
    require(registration["image_order"] == [r["image_id"] for r in manifest["images"]]
            and registration["model_calls"] == 2*len(manifest["images"]), "call coverage differs")
    annotations = json.loads(Path(annotation_path).read_text())
    summary = validate_annotations(annotations, manifest, require_complete=True)
    require(_timestamp(registration["created_at_utc"]) <= _timestamp(annotations["exported_at_utc"]) <= _timestamp(_utc()),
            "registration must precede completed annotations and model calls", "ANNOTATION_CHRONOLOGY")
    return registration, manifest, annotations, summary, config


def classify_response(raw, audit, width, height):
    require(isinstance(raw, str), "model raw response must be a string", "INVALID_OUTPUT")
    expected = generation_audit(audit["actual_generated_token_ids"], audit["input_token_count"],
                                audit["model_max_length"], audit["eos_token_id"])
    require(audit == expected, "token audit inconsistent", "INVALID_OUTPUT")
    require(audit["complete_generation"] and audit["terminal_eos_observed"]
            and 0 < audit["actual_generated_token_count"] <= audit["effective_limit"],
            "incomplete or over-budget generation; no retry", "INPUT_OR_OUTPUT_TRUNCATED")
    parsed = parse_grounding(raw, width, height)
    admitted = parsed["status"] in {"single_box", "multiple_boxes"}
    return dict(parsed=parsed, structurally_admitted=admitted,
                ordered_boxes=[b["continuous_xyxy"] for b in parsed["boxes"]],
                detection_present=bool(parsed["boxes"]), calibrated_confidence=None,
                semantic_identity_verified=False, classification_version=CLASSIFICATION)


def _explicit_gpu_mask():
    mask = os.environ.get("CUDA_VISIBLE_DEVICES")
    require(isinstance(mask, str) and re.fullmatch(r"(?:0|[1-9]\d*|GPU-[0-9a-fA-F-]+)", mask) is not None,
            "set CUDA_VISIBLE_DEVICES to exactly one GPU index or UUID before starting this process",
            "GPU_ALLOCATION_REQUIRED")
    return mask


def _cuda_allocation(torch, mask):
    require(_explicit_gpu_mask() == mask, "GPU mask changed during loading", "GPU_ALLOCATION_CHANGED")
    require(not torch.cuda.is_initialized(), "use a fresh process with allocation set before CUDA initialization",
            "GPU_ALLOCATION_CHANGED")
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1,
            "explicit allocation must expose exactly one CUDA GPU", "GPU_ALLOCATION_REQUIRED")
    properties = torch.cuda.get_device_properties(0)
    require(torch.cuda.current_device() == 0, "allocated device must be logical cuda:0", "GPU_ALLOCATION_CHANGED")
    return dict(cuda_visible_devices=mask, cuda_device_order=os.environ.get("CUDA_DEVICE_ORDER"),
                logical_device="cuda:0", visible_device_count=1, name=properties.name,
                total_memory_bytes=int(properties.total_memory), compute_capability=[properties.major, properties.minor],
                uuid=str(properties.uuid) if getattr(properties, "uuid", None) is not None else None,
                pci_bus_id=str(properties.pci_bus_id) if getattr(properties, "pci_bus_id", None) is not None else None,
                identity_source="explicit_cuda_mask_and_torch_device_properties")


def _load_worker():
    # Deliberately below validate_gate in run(). Hash local bytes before loading.
    mask = _explicit_gpu_mask()
    from .records import model_identity
    identity = model_identity(MODEL_PATH)
    require(identity["content_id"] == MODEL_CONTENT_ID, "frozen LocateAnything checkpoint changed", "CONDITION_CHANGED")
    import torch
    allocation = _cuda_allocation(torch, mask)
    from ..adapters.locateanything import LocateAnythingWorker
    return LocateAnythingWorker(MODEL_PATH, device="cuda", model_revision=MODEL_CONTENT_ID), {**identity, "execution_allocation": allocation}


def infer_audited(worker, rgb, query, emit):
    """Only RGB and the fixed query enter model preprocessing/generation."""
    from PIL import Image
    image = Image.fromarray(rgb).convert("RGB")
    question = f"Locate a single instance that matches the following description: {query}."
    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": question}]}]
    text = worker.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos = worker.processor.process_vision_info(messages)
    inputs = worker.processor(text=[text], images=images, videos=videos, return_tensors="pt", truncation=False).to(worker.device)
    ids = inputs["input_ids"].detach().cpu().tolist()[0]
    pixels = inputs["pixel_values"].to(worker.dtype)
    grid = inputs.get("image_grid_hws")
    grid = grid.detach().cpu().tolist() if hasattr(grid, "detach") else np.asarray(grid).tolist()
    emit("model-input", dict(query=query, question=question, formatted_text=text, input_token_ids=ids,
                             attention_mask=inputs["attention_mask"].detach().cpu().tolist(), image_grid_hws=grid,
                             pixel_shape=list(pixels.shape), pixel_dtype=str(pixels.dtype),
                             pixel_sha256=hashlib.sha256(pixels.contiguous().view(worker.torch.uint8).cpu().numpy().tobytes()).hexdigest(),
                             rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(), generator_inputs=["RGB", "fixed_query"],
                             input_token_count=len(ids), model_max_length=worker.tokenizer.model_max_length,
                             reserved_generation_tokens=SETTINGS["max_new_tokens"], processor_truncation=False))
    require(0 < len(ids) and len(ids) + SETTINGS["max_new_tokens"] <= worker.tokenizer.model_max_length,
            "input leaves insufficient full generation budget", "INPUT_OR_OUTPUT_TRUNCATED")
    observed = []
    original_decode = worker.tokenizer.batch_decode
    def audit_decode(sequences, *args, **kwargs):
        observed.append(sequences.detach().cpu().tolist())
        return original_decode(sequences, *args, **kwargs)
    worker.tokenizer.batch_decode = audit_decode
    worker.torch.cuda.synchronize()
    started = time.perf_counter()
    try:
        with worker.torch.no_grad():
            raw = worker.model.generate(pixel_values=pixels, input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"], image_grid_hws=inputs.get("image_grid_hws"),
                tokenizer=worker.tokenizer, **SETTINGS)
        worker.torch.cuda.synchronize()
    finally:
        worker.tokenizer.batch_decode = original_decode
    normalized = raw[0] if isinstance(raw, tuple) else raw
    emit("raw-output", dict(raw_response=normalized if isinstance(normalized, str) else repr(normalized),
                            raw_return_repr=repr(raw), observed_decoded_sequences=observed,
                            inference_s=time.perf_counter()-started))
    require(len(observed) == 1 and len(observed[0]) == 1, "generated token evidence missing", "INVALID_OUTPUT")
    audit = generation_audit(observed[0][0], len(ids), worker.tokenizer.model_max_length,
                             worker.tokenizer.convert_tokens_to_ids("<|im_end|>"))
    return normalized, audit


def _sensor_frames(registration, manifest):
    wanted = {image["frame_id"]: image for image in manifest["images"]}
    frames = {}
    for directory in sorted(Path(registration["source"]["path"]).glob("init-*")):
        for envelope, views in replay_frames(directory):
            rgb_refs = {entry["camera_id"]: entry["rgb_blob"]["sha256"] for entry in envelope.payload["views"]}
            for view in views:
                key = view["canonical_frame_id"]
                if key not in wanted:
                    continue
                image = wanted[key]
                require(hashlib.sha256(view["rgb"].tobytes()).hexdigest() == image["rgb_pixel_sha256"], "RGB source changed")
                require(rgb_refs[view["camera_id"]] == image["rgb_blob_sha256"]
                        and view["frame_id"] == image["source_frame_id"]
                        and view["episode_id"] == image["episode_id"]
                        and view["camera_id"] == image["camera_id"]
                        and view["rgb"].shape[:2] == (image["height"], image["width"]), "RGB source binding differs")
                require(key not in frames, "duplicate sensor frame")
                frames[key] = (view, envelope.payload["proprio"])
    require(set(frames) == set(wanted), "source50 frames missing")
    return frames


def box_geometry(view, proprio, entity, result, config):
    records = []
    for index, roi in enumerate(result["ordered_boxes"]):
        patch = None
        if result["structurally_admitted"]:
            # Preserve a valid continuous box that projects to zero integer ROI
            # support as UNKNOWN; do not expand its physical evidence silently.
            integer_roi = [int(value) for value in roi]
            if integer_roi[2] <= integer_roi[0] or integer_roi[3] <= integer_roi[1]:
                records.append(dict(box_index=index, roi_xyxy=roi, patch=None, for_execution=False,
                                    structural_reason="NO_INTEGER_PIXEL_ROI_SUPPORT"))
                continue
            patch = estimate_visible_patch(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
                roi_xyxy=roi, source_frame_id=view["canonical_frame_id"], calibration_version=view["calibration_version"],
                track_id=entity, feature_id=f"box-{index}", capture_sim_time_s=view["capture_sim_time_s"],
                capture_monotonic_ns=view["capture_monotonic_ns"], config=config, seed=0,
                eef_position_base_m=proprio["eef_position_base_m"]).to_dict()
        records.append(dict(box_index=index, roi_xyxy=roi, patch=patch, for_execution=False,
                            structural_reason=None if patch is not None else "RESPONSE_NOT_ADMITTED"))
    return records


def _rectangle(box):
    x0, y0, x1, y1 = box
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def coverage_metrics(boxes, truth, width, height):
    yy, xx = np.indices((height, width))
    pixels = np.column_stack((xx.ravel()+.5, yy.ravel()+.5))
    rows = []
    label = _inside(pixels, truth["polygons"]) if truth["status"] == "VISIBLE" else None
    for index, box in enumerate(boxes):
        predicted = _inside(pixels, [_rectangle(box)])
        intersection = int(np.count_nonzero(predicted & label)) if label is not None else None
        rows.append(dict(box_index=index, label_status=truth["status"], predicted_pixel_count=int(predicted.sum()),
                         annotated_pixel_coverage=(intersection/int(label.sum())) if label is not None and label.sum() else None,
                         bbox_contamination=(1-intersection/int(predicted.sum())) if label is not None and predicted.sum() else None,
                         evaluation_only=True))
    return rows


def annotation_upper_bound(view, proprio, entity, truth, config):
    """Explicit evaluator-only oracle-mask intervention; not a self-robot mask."""
    if truth["status"] != "VISIBLE":
        return dict(status="UNKNOWN", reason="LABEL_NOT_VISIBLE", label_status=truth["status"], for_execution=False)
    height, width = view["depth_m"].shape
    yy, xx = np.indices((height, width))
    mask = _inside(np.column_stack((xx.ravel()+.5, yy.ravel()+.5)), truth["polygons"]).reshape(height, width)
    if not mask.any():
        return dict(status="UNKNOWN", reason="NO_LABEL_PIXEL_SUPPORT", for_execution=False)
    depth = view["depth_m"].copy()
    depth[~mask] = np.nan
    y, x = np.nonzero(mask)
    suffix = f"{view['canonical_frame_id']}/evaluation-human-mask/{entity}"
    patch = estimate_visible_patch(depth, view["intrinsics_K"], view["T_base_camera"],
        roi_xyxy=[int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)], source_frame_id=suffix,
        calibration_version=view["calibration_version"], track_id=entity, feature_id="human-mask-upper-bound",
        capture_sim_time_s=view["capture_sim_time_s"], capture_monotonic_ns=view["capture_monotonic_ns"],
        config=config, seed=0, eef_position_base_m=proprio["eef_position_base_m"]).to_dict()
    patch["provenance"] = "evaluation_human_mask_and_sensor_depth"
    for candidate in patch["candidates"]:
        candidate["provenance"] = "evaluation_human_mask_and_sensor_depth"
    return dict(status=patch["geometry_status"], patch=patch, for_execution=False, intervention="human_polygon_nan_mask",
                original_depth_sha256=hashlib.sha256(view["depth_m"].tobytes()).hexdigest(),
                mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest(),
                retained_depth_unchanged=bool(np.array_equal(depth[mask], view["depth_m"][mask], equal_nan=True)))


def run(packet_dir, annotation_path, registration_path, output, *, geometry_path="configs/p1_geometry.json"):
    registration, manifest, annotations, gate, config = validate_gate(packet_dir, annotation_path, registration_path, geometry_path=geometry_path)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    _write(out/"gate.json", dict(registration_sha256=registration["registration_sha256"], gate=gate,
                                annotation_sha256=_sha(annotation_path), annotation_content_sha256=content_hash(annotations),
                                validated_at_utc=_utc(), model_imported=False))
    _write(out/"preregistration.json", registration)
    from .records import code_identity, versions
    run_manifest = dict(code=code_identity(), versions=versions(),
             condition="fixed_query_rgb_only_offline_no_runtime", registration_sha256=registration["registration_sha256"],
             annotation_sha256=_sha(annotation_path), annotation_identity="human_self_attestation_not_authenticated",
             simulator_calibration="source_camera_configuration_and_robot_owned_fk", oracle_target_inputs=False,
             requested_cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"))
    _write(out/"run-preflight-manifest.json", run_manifest)
    all_calls = []
    started_calls = 0
    try:
        # Inputs are verified before model load, without consulting polygon values.
        frames = _sensor_frames(registration, manifest)
        worker, model = _load_worker()
        _write(out/"model.json", model)
        _write(out/"run-manifest.json", {**run_manifest, "execution_allocation": model.get("execution_allocation")})
        for image in manifest["images"]:
            view, proprio = frames[image["frame_id"]]
            for entity in ENTITIES:
                number = len(all_calls)
                folder = out/f"call-{number:03d}"
                folder.mkdir()
                _write(folder/"request.json", dict(**image_binding(image), entity=entity, query=QUERIES[entity]))
                def emit(kind, payload):
                    _write(folder/(kind+".json"), payload)
                started_calls += 1
                raw, audit = infer_audited(worker, view["rgb"], QUERIES[entity], emit)
                _write(folder/"generation-audit.json", audit)
                result = classify_response(raw, audit, image["width"], image["height"])
                result.update(image_id=image["image_id"], entity=entity, query=QUERIES[entity],
                              frame_id=image["frame_id"], rgb_pixel_sha256=image["rgb_pixel_sha256"],
                              raw_response=raw, generation_audit=audit,
                              geometry=box_geometry(view, proprio, entity, result, config))
                _write(folder/"prediction.json", result)
                all_calls.append(result)
        require(len(all_calls) == registration["model_calls"], "incomplete fixed call set")
        _write(out/"predictions-sealed.json", dict(model_calls=len(all_calls), predictions_sha256=content_hash(all_calls),
                   completed_at_utc=_utc(), annotation_geometry_consumed=False, runtime_actions=0))
        # Only now read polygon contents for comparisons and optional upper bound.
        _write(out/"annotations-evaluation-input.json", annotations)
        by_label = {r["image_id"]: r for r in annotations["annotations"]}
        prediction_records, coverage, upper = [], [], []
        for image in manifest["images"]:
            view, proprio = frames[image["frame_id"]]
            entities = {}
            for entity in ENTITIES:
                prediction = next(p for p in all_calls if p["image_id"] == image["image_id"] and p["entity"] == entity)
                boxes = prediction["ordered_boxes"] if prediction["structurally_admitted"] else []
                points = []
                for box in prediction["geometry"]:
                    if box["patch"] is not None:
                        for candidate in box["patch"]["candidates"]:
                            points.extend(project_base_points([candidate["position_base_m"]], view["intrinsics_K"], view["T_base_camera"]).tolist())
                entities[entity] = dict(status="VISIBLE" if boxes else "UNKNOWN", reason=prediction["parsed"]["status"],
                                        polygons=[_rectangle(box) for box in boxes], points=points)
                if entity == "fixed_cabinet_reference":
                    # LocateAnything emits no subtype; do not infer one from the
                    # query or from human labels. Structural boxes are claims.
                    entities[entity]["reference_types"] = ["UNKNOWN"]*len(boxes)
                truth = by_label[image["image_id"]]["entities"][entity]
                coverage.append(dict(image_id=image["image_id"], entity=entity,
                                     boxes=coverage_metrics(boxes, truth, image["width"], image["height"])))
                if registration["annotation_conditioned_upper_bound"]:
                    upper.append(dict(image_id=image["image_id"], entity=entity,
                                      evidence=annotation_upper_bound(view, proprio, entity, truth, config)))
            prediction_records.append(dict(**image_binding(image), entities=entities))
        predictions = dict(schema=PREDICTION_SCHEMA, dataset_id=manifest["dataset_id"], producer_id="LocateAnything-frozen",
                           revision=CLASSIFICATION, records=prediction_records)
        _write(out/"predictions-evaluation-format.json", predictions)
        _write(out/"human-evaluation.json", evaluate_grounding(predictions, annotations, manifest))
        _write(out/"coverage-contamination.json", coverage)
        if upper:
            _write(out/"annotation-conditioned-upper-bound.json", upper)
        _write(out/"completed.json", dict(model_calls=len(all_calls), runtime_actions=0, policy_execution=False,
                                          semantic_identity_source="independent_human_self_attested_evaluation_only"))
    except Exception as exc:
        _write(out/"failure.json", dict(error=repr(exc), started_inference_calls=started_calls,
                                        completed_model_calls=len(all_calls), retries=0))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--packet", required=True)
    prepare.add_argument("--source-run", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--annotation-upper-bound", action="store_true")
    execute = commands.add_parser("run")
    execute.add_argument("--packet", required=True)
    execute.add_argument("--annotations", required=True)
    execute.add_argument("--preregistration", required=True)
    execute.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        preregister(args.packet, args.source_run, args.output, annotation_upper_bound=args.annotation_upper_bound)
    else:
        run(args.packet, args.annotations, args.preregistration, args.output)


if __name__ == "__main__":
    main()
