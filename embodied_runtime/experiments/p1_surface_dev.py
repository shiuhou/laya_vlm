"""Bounded fresh-development BOX/POINT association; never a control policy.

No labels, target simulator state, prompt tuning, retries or execution. Source
RGB goes to the model; metric depth/calibration goes only to surface geometry.
CPU timing is not a live/GPU claim. Track initialization is offline diagnostic.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np

from ..contracts import content_hash, require, thaw
from ..perception.recording import FrameRecorder, replay_frames
from ..perception.surface_association import (
    associate_point, inventory_surfaces, sensor_view_identity, tracker_seed_rectangle,
)
from ..perception.visual_tracker import TrackerConfig, VisualTracker
from .p1_semantic_grounding import (
    MODEL_CONTENT_ID, QUERIES, _cuda_allocation, _explicit_gpu_mask, frozen_geometry,
)
from .point_grounding_probe import SETTINGS, generation_audit, parse_grounding, serialize_model_config
from .records import code_identity, file_hash, jsonable, model_identity, versions


def write(path, payload):
    Path(path).write_text(json.dumps(jsonable(payload), indent=2, allow_nan=False)+"\n")


def capture(output):
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_sensor_env import LiberoSensorEnv
    from PIL import Image

    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    config = json.loads(Path("configs/p1_surface_dev.json").read_text())
    geometry = frozen_geometry(config["geometry_config"])
    registration = dict(config=config, queries=QUERIES, generation_settings=SETTINGS,
                        model_content_id=MODEL_CONTENT_ID, code=code_identity(), versions=versions(),
                        created_at_utc=datetime.now(timezone.utc).isoformat(),
                        geometry_sha256=content_hash(geometry.to_dict()), tracker_config=asdict(TrackerConfig()),
                        model_calls=8, independent_blind_evaluation=False,
                        robot_controls="World constructor settling only; no post-reset commands",
                        condition_note="Software EGL acquisition; separate from frozen GPU 50-view evaluation",
                        environment={k: os.environ.get(k) for k in (
                            "MUJOCO_GL", "EGL_PLATFORM", "LIBGL_ALWAYS_SOFTWARE", "PYOPENGL_PLATFORM",
                            "MESA_SHADER_CACHE_DIR", "NUMBA_CACHE_DIR")},
                        failure_rule="no retries, incomplete token audit stops inference; association uncertainty retained",
                        verify_status="UNKNOWN: no fixedness/closed-state relation established")
    write(root/"registration.json", registration)
    frames = []
    for init in config["init_indices"]:
        backend = LiberoWorldBackend.from_task(config["task"], seed=config["seed"], init_state_id=init,
            libero_root="/home/junhongli/projects/LIBERO", config_dir="/tmp/laya-surface-dev-libero", render=True)
        sensor = None
        try:
            sensor = LiberoSensorEnv(backend.world, camera_names=config["camera_names"],
                width=config["width"], height=config["height"],
                retained_gripper_command=lambda: "OPEN" if backend.gripper_command() < 0 else "CLOSE")
            directory = root/f"init-{init:03d}"
            with FrameRecorder(directory, episode_id=f"p1-surface-dev/init{init}",
                clock_domain="surface-dev/local-process", condition=config["acquisition_condition"]) as recorder:
                bundle = sensor.sensor_port().capture()
                recorder.append(bundle["views"], bundle["proprio"], emitted_monotonic_ns=time.monotonic_ns())
        finally:
            if sensor is not None:
                sensor.close()
            backend.world.close()
        for _, views in replay_frames(directory):
            for view in views:
                name = f"init-{init:03d}-{view['camera_id']}"
                Image.fromarray(view["rgb"]).save(root/f"{name}.png")
                frames.append(dict(init_index=init, recording=f"init-{init:03d}", camera_id=view["camera_id"],
                    frame_id=view["canonical_frame_id"], calibration_version=view["calibration_version"],
                    sensor_view_sha256=content_hash(sensor_view_identity(view)),
                    rgb_sha256=hashlib.sha256(view["rgb"].tobytes()).hexdigest(),
                    image=f"{name}.png", image_file_sha256=file_hash(root/f"{name}.png")))
    write(root/"inputs.json", dict(frames=frames, registration_sha256=file_hash(root/"registration.json")))
    print(json.dumps(dict(capture_complete=True, views=len(frames))), flush=True)


def load_inputs(root):
    registration = json.loads((root/"registration.json").read_text())
    inputs = json.loads((root/"inputs.json").read_text())
    require(inputs["registration_sha256"] == file_hash(root/"registration.json"), "registration changed")
    require(registration["config"] == json.loads(Path("configs/p1_surface_dev.json").read_text())
            and registration["queries"] == QUERIES and registration["generation_settings"] == SETTINGS,
            "condition changed")
    frozen_geometry(registration["config"]["geometry_config"])
    return registration, inputs


def registered_pairs(registration, inputs):
    return [f"init-{frame['init_index']:03d}-{entity}"
            for frame in inputs["frames"]
            for entity, camera in registration["config"]["entity_cameras"].items()
            if frame["camera_id"] == camera]


def infer(output, *, device="cpu", inference_dir=None, selected_pair=None):
    import torch
    from PIL import Image
    from ..adapters.locateanything import LocateAnythingWorker

    root = Path(output)
    registration, inputs = load_inputs(root)
    config = registration["config"]
    require(selected_pair is None or selected_pair in registered_pairs(registration, inputs),
            "pair must already exist in frozen registration")
    expected_calls = 2 if selected_pair else registration["model_calls"]
    require(device in {"cpu", "cuda:0"}, "explicit CPU or allocated logical cuda:0 required")
    allocation = None
    if device == "cuda:0":
        mask = _explicit_gpu_mask()
        require(mask.startswith("GPU-"), "use a GPU UUID mask for identifiable allocation", "GPU_ALLOCATION_REQUIRED")
        allocation = _cuda_allocation(torch, mask)
    # Execution device/output override never rewrites source registration or
    # resumes/splices the interrupted CPU predictions into a matched GPU run.
    folder = Path(inference_dir) if inference_dir else root/"inference"
    require(not folder.exists(), "fresh inference directory required; no overwrite/resume")
    identity = model_identity(config["model_path"])
    require(identity["content_id"] == registration["model_content_id"], "checkpoint bytes changed")
    folder.mkdir(parents=True, exist_ok=False)
    write(folder/"loading.json", dict(model=identity, versions=versions(), code=code_identity(), device=device,
        execution_allocation=allocation, source_root=str(root.resolve()),
        device_override_only=device != config["device"],
        selected_pair=selected_pair, expected_scope_calls=expected_calls,
        registered_total_calls=registration["model_calls"],
        dtype=config["dtype"], threads=config["torch_threads"],
        inputs_sha256=file_hash(root/"inputs.json"), registration_sha256=file_hash(root/"registration.json")))
    torch.set_num_threads(config["torch_threads"])
    worker = LocateAnythingWorker(config["model_path"], device=device, dtype=config["dtype"],
                                  model_revision=identity["content_id"])
    torch = worker.torch
    torch.set_num_threads(config["torch_threads"])
    write(folder/"model_config.json", serialize_model_config(worker.model.config.to_dict()))
    original_decode, observed = worker.tokenizer.batch_decode, []

    def decode_audit(sequences, *args, **kwargs):
        observed.append(sequences.detach().cpu().tolist())
        return original_decode(sequences, *args, **kwargs)

    worker.tokenizer.batch_decode = decode_audit
    started_all = time.perf_counter()
    try:
        for frame in inputs["frames"]:
            for entity, camera in config["entity_cameras"].items():
                if frame["camera_id"] != camera:
                    continue
                if selected_pair and f"init-{frame['init_index']:03d}-{entity}" != selected_pair:
                    continue
                image_path = root/frame["image"]
                require(file_hash(image_path) == frame["image_file_sha256"], "RGB artifact changed")
                image = Image.open(image_path).convert("RGB")
                require(hashlib.sha256(np.asarray(image).tobytes()).hexdigest() == frame["rgb_sha256"], "RGB bytes changed")
                for mode in config["mode_order"]:
                    call = f"init-{frame['init_index']:03d}-{entity}-{mode}"
                    question = (f"Point to: {QUERIES[entity]}." if mode == "point" else
                                f"Locate a single instance that matches the following description: {QUERIES[entity]}.")
                    messages = [{"role": "user", "content": [{"type": "image", "image": image},
                                                             {"type": "text", "text": question}]}]
                    template = worker.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    images, videos = worker.processor.process_vision_info(messages)
                    tensors = worker.processor(text=[template], images=images, videos=videos, return_tensors="pt").to(device)
                    input_ids = tensors["input_ids"].detach().cpu().tolist()[0]
                    request = dict(frame=frame, entity=entity, mode=mode,
                        question=question, prompt=template, input_token_ids=input_ids,
                        pixel_values_sha256=hashlib.sha256(tensors["pixel_values"].float().cpu().numpy().tobytes()).hexdigest(),
                        pixel_values_hash_encoding="processor float32 contiguous bytes",
                        image_grid_hws=jsonable(tensors["image_grid_hws"].detach().cpu().numpy()
                            if hasattr(tensors["image_grid_hws"], "detach") else tensors["image_grid_hws"]))
                    old_request = root/"inference"/f"{call}-request.json"
                    if inference_dir is not None and old_request.exists():
                        require(request == json.loads(old_request.read_text()), "recorded model-facing input changed",
                                "CONDITION_CHANGED")
                    write(folder/f"{call}-request.json", request)
                    require(len(input_ids)+SETTINGS["max_new_tokens"] <= worker.tokenizer.model_max_length,
                            "input exceeds model budget")
                    observed.clear()
                    if allocation is not None:
                        torch.cuda.synchronize(0)
                    started = time.perf_counter()
                    print(f"Starting {call}", flush=True)
                    with torch.no_grad():
                        raw = worker.model.generate(pixel_values=tensors["pixel_values"].to(worker.dtype),
                            input_ids=tensors["input_ids"], attention_mask=tensors["attention_mask"],
                            image_grid_hws=tensors.get("image_grid_hws"), tokenizer=worker.tokenizer, **SETTINGS)
                    if allocation is not None:
                        torch.cuda.synchronize(0)
                    require(len(observed) == 1 and len(observed[0]) == 1, "actual output tokens unavailable")
                    raw = raw[0] if isinstance(raw, tuple) else raw
                    require(isinstance(raw, str), "raw output must be text")
                    audit = generation_audit(observed[0][0], len(input_ids), worker.tokenizer.model_max_length,
                                              worker.tokenizer.convert_tokens_to_ids("<|im_end|>"))
                    payload = dict(frame=frame, entity=entity, mode=mode, raw_output=raw, audit=audit,
                        parsed=parse_grounding(raw, image.width, image.height), latency_s=time.perf_counter()-started)
                    write(folder/f"{call}-response.json", payload)
                    print(json.dumps(dict(call=call, raw=raw, complete=audit["complete_generation"],
                                          latency_s=payload["latency_s"])), flush=True)
                    require(audit["complete_generation"] and len(observed[0][0]) <= audit["effective_limit"],
                            "incomplete generation; stop without retry")
        responses = sorted(folder.glob("*-response.json"))
        require(len(responses) == expected_calls, "incomplete declared scope coverage")
        write(folder/"complete.json", dict(calls=len(responses), elapsed_s=time.perf_counter()-started_all,
            selected_pair=selected_pair, registered_total_calls=registration["model_calls"],
            artifacts_sha256={p.name: file_hash(p) for p in sorted(folder.glob("*.json"))}))
    except Exception as exc:
        write(folder/"failure.json", dict(error=repr(exc), elapsed_s=time.perf_counter()-started_all))
        raise
    finally:
        worker.tokenizer.batch_decode = original_decode


def analyze(output, *, inference_dir=None, analysis_dir=None, test_tracker=False):
    from PIL import Image, ImageDraw

    root = Path(output)
    registration, inputs = load_inputs(root)
    inference = Path(inference_dir) if inference_dir else root/"inference"
    require((inference/"complete.json").exists(), "seal inference before inspecting predictions")
    loading = json.loads((inference/"loading.json").read_text())
    require(loading["inputs_sha256"] == file_hash(root/"inputs.json")
            and loading["registration_sha256"] == file_hash(root/"registration.json"), "inference source changed")
    seal = json.loads((inference/"complete.json").read_text())
    selected_pair = loading.get("selected_pair")
    require(selected_pair is None or selected_pair in registered_pairs(registration, inputs), "unregistered analysis scope")
    require(seal["calls"] == (2 if selected_pair else registration["model_calls"]), "incomplete declared scope coverage")
    require(seal.get("selected_pair") == selected_pair, "inference scope mismatch")
    for name, digest in seal["artifacts_sha256"].items():
        require(file_hash(inference/name) == digest, "sealed inference artifact changed")
    geometry = frozen_geometry(registration["config"]["geometry_config"])
    folder = Path(analysis_dir) if analysis_dir else root/"association"
    folder.mkdir(parents=True, exist_ok=False)
    summaries = []
    for frame in inputs["frames"]:
        view = next(v for _, views in replay_frames(root/frame["recording"]) for v in views
                    if v["camera_id"] == frame["camera_id"])
        require(hashlib.sha256(view["rgb"].tobytes()).hexdigest() == frame["rgb_sha256"], "source changed")
        require(content_hash(sensor_view_identity(view)) == frame["sensor_view_sha256"], "sensor view changed")
        for entity, camera in registration["config"]["entity_cameras"].items():
            if camera != frame["camera_id"]:
                continue
            stem = f"init-{frame['init_index']:03d}-{entity}"
            if selected_pair and stem != selected_pair:
                continue
            box = json.loads((inference/f"{stem}-box-response.json").read_text())
            point_path = inference/f"{stem}-point-response.json"
            point = json.loads(point_path.read_text())
            boxes = box["parsed"]["boxes"] if box["parsed"]["status"] in {"single_box", "multiple_boxes"} else []
            xy = [p["continuous_xy"] for p in point["parsed"]["points"]] if point["parsed"]["status"] == "single_point" else []
            inventories, bindings, matches, surfaces = [], [], [], []
            overlay = view["rgb"].copy()
            for index, region in enumerate(boxes):
                inventory = inventory_surfaces(view, region["continuous_xyxy"], config=geometry, seed=0)
                write(folder/f"{stem}-roi{index}-inventory.json", inventory.evidence())
                binding = associate_point(inventory, dict(frame_id=frame["frame_id"], camera_id=camera,
                    rgb_sha256=frame["rgb_sha256"], calibration_version=frame["calibration_version"],
                    sensor_view_sha256=frame["sensor_view_sha256"], parsed_status=point["parsed"]["status"],
                    query=QUERIES[entity], response_sha256=file_hash(point_path), evaluation_labels_used=False,
                    generation_complete=point["audit"]["complete_generation"], points_xy=xy))
                inventories.append(dict(roi_index=index, surfaces=len(inventory.surfaces),
                    residual_pixels=int(inventory.residual_mask.sum())))
                bindings.append(binding)
                for surface in inventory.surfaces:
                    color = np.array([(53+index*71+len(surfaces)*37)%256,
                                      (151+len(surfaces)*61)%256, (227+len(surfaces)*83)%256])
                    overlay[surface.support_mask] = (.6*overlay[surface.support_mask]+.4*color).astype(np.uint8)
                    surfaces.append(surface)
                    if surface.surface_id in binding["matching_surface_ids"]:
                        matches.append(surface)
            result = dict(entity=entity, frame=frame, inventories=inventories, bindings=bindings,
                          point_xy=xy, association_status="UNKNOWN", tracker_status="NOT_INITIALIZED",
                          semantic_identity_verified=False, verify_status="UNKNOWN", for_execution=False,
                          reason="NO_SINGLE_SUPPORTED_POINT")
            # Cross-ROI ambiguity remains ambiguity, even for overlapping boxes.
            if len(matches) > 1:
                result.update(association_status="AMBIGUOUS", reason="MULTIPLE_ROI_SURFACE_SUPPORTS")
            elif len(matches) == 1 and any(b["status"] == "BOUND_HYPOTHESIS" for b in bindings):
                result.update(association_status="BOUND_HYPOTHESIS", reason=None)
                if not test_tracker:
                    result["tracker_status"] = "NOT_TESTED_ASSOCIATION_REVIEW_FIRST"
                else:
                    rectangle = tracker_seed_rectangle(matches[0], xy[0], tracker_config=TrackerConfig())
                    result["seed_rectangle_xyxy"] = rectangle
                    if rectangle is not None:
                        tracker = VisualTracker(f"surface-dev/{stem}")
                        tracked = tracker.initialize(view, rectangle, query=QUERIES[entity], seed_source="semantic_query",
                            now_sim_time_s=view["capture_sim_time_s"], now_monotonic_ns=view["capture_monotonic_ns"])
                        result.update(tracker_status=tracked.status, tracker_evidence=thaw(tracked),
                                      clock_condition="offline capture clock; not a live freshness claim")
                    else:
                        result["reason"] = "NO_SUPPORT_CONTAINED_TRACKER_RECTANGLE"
            image = Image.fromarray(overlay)
            draw = ImageDraw.Draw(image)
            for b in boxes:
                draw.rectangle(b["continuous_xyxy"], outline="yellow", width=2)
            for p in xy:
                x, y = p
                draw.ellipse((x-3, y-3, x+3, y+3), fill="red")
            image.save(folder/f"{stem}-overlay.png")
            write(folder/f"{stem}-result.json", result)
            summaries.append(result)
            print(json.dumps(dict(case=stem, association=result["association_status"],
                                  tracker=result["tracker_status"], inventories=inventories)), flush=True)
    write(folder/"summary.json", dict(cases=summaries, development_only=True, verify_status="UNKNOWN", code=code_identity(),
                                      no_policy_or_control=True, tracker_test_explicitly_requested=test_tracker,
                                      selected_pair=selected_pair, registered_total_calls=registration["model_calls"],
                                      inference_seal_sha256=file_hash(inference/"complete.json")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("capture", "infer", "analyze"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda:0"), default="cpu")
    parser.add_argument("--inference-dir", help="fresh GPU inference outputs, separate from frozen input evidence")
    parser.add_argument("--analysis-dir", help="fresh association/track outputs; never overwrite a prior stage")
    parser.add_argument("--test-tracker", action="store_true", help="only after surface-association review succeeds")
    parser.add_argument("--pair", help="newly preregistered single-pair scope; original frozen inputs/settings unchanged")
    args = parser.parse_args()
    if args.phase == "capture":
        require(args.device == "cpu" and args.inference_dir is None and args.analysis_dir is None
                and not args.test_tracker and args.pair is None, "capture has no execution overrides")
        capture(args.output)
    elif args.phase == "infer":
        require(args.analysis_dir is None and not args.test_tracker, "inference cannot run tracking")
        infer(args.output, device=args.device, inference_dir=args.inference_dir, selected_pair=args.pair)
    else:
        require(args.device == "cpu" and args.pair is None, "analysis uses sealed inference scope; no manual rescope")
        analyze(args.output, inference_dir=args.inference_dir, analysis_dir=args.analysis_dir,
                test_tracker=args.test_tracker)


if __name__ == "__main__":
    main()
