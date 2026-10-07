"""Frozen Formal-50 corpus generation; no annotation or control input.

Separate exclusive prepare/masks/geometry/score stages. Every BOX retains native
decoder order. Failed first attempts remain records, never retried or replaced.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

from ..contracts import content_hash, require
from ..perception.segmented_patch import estimate_segmented_patch
from ..perception.semantic_output import parse_semantic_reply
from ..perception.surface_association import sensor_view_identity
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import (
    SAM_SETTINGS, SAM_REVISION, CHECKPOINT_SHA, CONFIG_SHA, read, write, seal, verify_seal,
)
from .p1_semantic_grounding import QUERIES, _sensor_frames, _explicit_gpu_mask, _cuda_allocation
from .records import code_identity, file_hash

ENTRY = Path("docs/evidence/p1_grounding/mask_support_reanalysis_20261007/formal50-evaluation-entry.json")
ASSETS = Path("runs/p1/sam2-preparation-pip25-20261007/assets.json")


def frames(entry):
    return _sensor_frames({"source": {"path": str(Path(entry["source_manifest_path"]).parent)}},
                          {"images": entry["ordered50_images"]})


def check_entry(entry):
    require(content_hash({k: v for k, v in entry.items() if k != "content_sha256"}) == entry["content_sha256"],
            "frozen entry changed")
    require(entry["measurement_contract"] == "native-mask-depth/2"
            and entry["SAM_settings"] == SAM_SETTINGS and entry["queries"] == QUERIES,
            "frozen condition differs")
    for path, digest in entry["pipeline_source_sha256"].items():
        require(file_hash(path) == digest, "pipeline implementation changed")
    for stem in ("source_manifest", "annotation_packet_manifest", "rules"):
        require(file_hash(entry[f"{stem}_path"]) == entry[f"{stem}_sha256"], "frozen input changed")
    config()


def registration(root):
    r = read(Path(root)/"registration.json")
    require(content_hash({k: v for k, v in r.items() if k != "registration_content_sha256"})
            == r["registration_content_sha256"], "registration changed")
    check_entry(r["entry"])
    for path, digest in r["source_files_sha256"].items():
        require(file_hash(path) == digest, "registered source changed", "SOURCE_MISMATCH")
    for name, digest in r["sam_source_files_sha256"].items():
        require(file_hash(Path(r["environment_receipt"]["sam_source"])/name) == digest,
                "SAM source changed")
    assets = r["environment_receipt"]
    require(file_hash(assets["checkpoint_path"]) == CHECKPOINT_SHA
            and file_hash(Path(assets["sam_source"])/"sam2/configs/sam2.1/sam2.1_hiera_t.yaml") == CONFIG_SHA,
            "SAM weights/config changed")
    return r


def prepare(output):
    entry, assets = read(ENTRY), read(ASSETS)
    check_entry(entry)
    require(assets["sam_revision"] == SAM_REVISION and assets["checkpoint_sha256"] == CHECKPOINT_SHA,
            "SAM assets differ")
    code = code_identity()
    require(code["dirty_status"] == "", "freeze runner before generation")
    source = Path(entry["source_manifest_path"]).parent
    packet = Path(entry["annotation_packet_manifest_path"]).parent
    prediction_root = Path(entry["sealed100_BOX_path"])
    calls = [read(prediction_root/f"call-{i:03d}/prediction.json") for i in range(100)]
    require(content_hash(calls) == entry["sealed100_BOX_sha256"], "ordered BOX100 differs")
    require(file_hash(prediction_root/"preregistration.json") == entry["BOX_preregistration_sha256"],
            "BOX preregistration changed")
    original = read(prediction_root/"preregistration.json")
    for name, digest in original["source"]["recording_metadata_sha256"].items():
        require(file_hash(source/name) == digest, "historical recording metadata changed")
    frozen_sam_path = Path("runs/p1/box-sam2-grid-complete-20261007/registration.json")
    frozen_sam = read(frozen_sam_path)
    require(frozen_sam["registration_content_sha256"] == content_hash({k: v for k, v in frozen_sam.items()
            if k != "registration_content_sha256"}) and frozen_sam["sam_settings"] == SAM_SETTINGS,
            "frozen SAM registration changed")
    for name, digest in frozen_sam["sam_source_files_sha256"].items():
        require(file_hash(Path(assets["sam_source"])/name) == digest, "frozen SAM source changed")
    expected = [(image["image_id"], entity) for image in entry["ordered50_images"] for entity in QUERIES]
    require([(c["image_id"], c["entity"]) for c in calls] == expected, "BOX canonical order differs")
    sensor_frames = frames(entry)
    rows = []
    for i, image in enumerate(entry["ordered50_images"]):
        view, _ = sensor_frames[image["frame_id"]]
        call = calls[i*2]
        require(call["entity"] == "drawer_front_pushable" and call["frame_id"] == image["frame_id"]
                and call["rgb_pixel_sha256"] == image["rgb_pixel_sha256"]
                and call["query"] == QUERIES["drawer_front_pushable"], "BOX/frame/query differs")
        require(file_hash(packet/image["image_path"]) == image["png_sha256"], "RGB packet changed")
        reply = parse_semantic_reply(call["raw_response"], image["width"], image["height"],
                                    mode="box", audit=call["generation_audit"])
        if reply.admitted:
            require([list(a.pixels) for a in reply.selected] == call["ordered_boxes"]
                    and call["structurally_admitted"], "frozen typed BOX ordering differs")
        rows.append(dict(input_index=i, image=image, source_identity=sensor_view_identity(view),
            sensor_view_sha256=content_hash(sensor_view_identity(view)), query=call["query"],
            response_sha256=file_hash(prediction_root/f"call-{i*2:03d}/prediction.json"),
            source_call_uri=str((prediction_root/f"call-{i*2:03d}/prediction.json").absolute()),
            typed=reply.evidence(), ordered_boxes=call["ordered_boxes"] if reply.admitted else [],
            source_admitted=reply.admitted, source_reason=reply.reason))
    paths = [p for p in source.rglob("*") if p.is_file()]
    # Pin BOX response/condition records only, never historical scored labels.
    paths += [prediction_root/f"call-{i:03d}/prediction.json" for i in range(100)]
    paths += [prediction_root/"preregistration.json", prediction_root/"predictions-sealed.json"]
    paths += [ENTRY, ASSETS, frozen_sam_path, Path(entry["annotation_packet_manifest_path"]), Path(entry["rules_path"]),
              Path(assets["dependency_lock_path"]), Path("requirements/p1-sam2-py310-linux.lock")]
    paths += [Path(p) for p in code["source_sha256"]]
    paths += [packet/image["image_path"] for image in entry["ordered50_images"]]
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    r = dict(condition="p1-formal50-native-masks/1", registered_at_utc=datetime.now(timezone.utc).isoformat(),
        code=code, baseline="25f1e4a", entry=entry, inputs=rows, environment_receipt=assets,
        source_files_sha256={str(p.absolute()): file_hash(p) for p in paths},
        sam_source_files_sha256=frozen_sam["sam_source_files_sha256"],
        input_camera_counts={"agentview": 25, "robot0_eye_in_hand": 25},
        mask_order=[0, 1, 2], selected_mask=None, selected_candidate=None,
        candidate_order="unchanged lexicographic plane grid", calibrated_confidence=None,
        annotation_read_stage="score only after masks+geometry seals", evaluation_labels_used=False,
        LocateAnything_calls=0, tracker_calls=0, controls=0, Qwen_calls=0, Laya_calls=0,
        failure_rule="retain first attempt; no retries; continue independent samples after ordinary sample failures",
        scoring_contract="p1-formal50-blind-scoring/1", for_execution=False)
    r["registration_content_sha256"] = content_hash(r)
    write(root/"registration.json", r)
    registration(root)


def _masks(root, r, out):
    import torch
    assets = r["environment_receipt"]
    write(out/"process-environment.json", dict(executable=sys.executable, prefix=sys.prefix,
        base_prefix=sys.base_prefix, torch=torch.__version__, pid=os.getpid()))
    require(os.path.abspath(sys.executable) == os.path.abspath(assets["python_executable"])
            and Path(sys.prefix).absolute() == Path(assets["python_executable"]).absolute().parent.parent,
            "invoke prepared venv without resolving symlink")
    require(torch.__version__ == "2.5.1+cu121" and os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8",
            "locked torch/workspace required")
    gpu = _explicit_gpu_mask()
    require(gpu.startswith("GPU-"), "GPU UUID required")
    allocation = _cuda_allocation(torch, gpu)
    import sam2
    require(Path(sam2.__file__).resolve().is_relative_to(Path(assets["sam_source"]).resolve()),
            "SAM import differs")
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    from .sam2_deterministic_grid import install_and_verify
    torch.manual_seed(1)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    write(out/"condition.json", dict(code=code_identity(), allocation=allocation, sam_settings=SAM_SETTINGS,
        compatibility=r["entry"]["SAM_compatibility"], model_inputs=["original_full_RGB", "sealed_BOX_xyxy"],
        evaluation_labels_used=False, depth_to_SAM=False, registration_sha256=file_hash(root/"registration.json")))
    start = time.perf_counter()
    model = build_sam2(assets["sam_config"], assets["checkpoint_path"], device="cuda:0", apply_postprocessing=False)
    write(out/"dense-grid-equivalence.json", install_and_verify(model))
    predictor = SAM2ImagePredictor(model, mask_threshold=0.0, max_hole_area=0.0, max_sprinkle_area=0.0)
    torch.cuda.synchronize()
    write(out/"startup.json", dict(model_load_and_overlay_s=time.perf_counter()-start))
    sensor_frames = frames(r["entry"])
    records = []
    with torch.inference_mode():
        for row in r["inputs"]:
            i, image = row["input_index"], row["image"]
            view, _ = sensor_frames[image["frame_id"]]
            require(sensor_view_identity(view) == row["source_identity"], "sensor binding changed")
            if not row["source_admitted"] or not row["ordered_boxes"]:
                record = dict(**row, status="FAILURE", failure_stage="semantic_source_admission",
                              error=row["source_reason"], box_index=None, mask_count=0, hidden_retry=False)
                write(out/f"frame-{i:03d}-failure.json", record)
                records.append(record)
                continue
            encode_error, encode_s = None, None
            try:
                torch.cuda.synchronize()
                start = time.perf_counter()
                predictor.set_image(view["rgb"].copy())
                torch.cuda.synchronize()
                encode_s = time.perf_counter()-start
            except Exception as exc:
                encode_error = repr(exc)
            for index, box in enumerate(row["ordered_boxes"]):
                record = dict(**row, box_index=index, box_xyxy=box, encode_s=encode_s,
                              mask_count=0, selected_mask=None, hidden_retry=False)
                phase = "image_encoding"
                try:
                    require(encode_error is None, encode_error or "encoding failed")
                    phase = "mask_prediction"
                    torch.cuda.synchronize()
                    start = time.perf_counter()
                    logits, scores, lowres = predictor.predict(box=np.asarray(box, dtype=np.float32),
                        multimask_output=True, return_logits=True)
                    torch.cuda.synchronize()
                    record["predict_s"] = time.perf_counter()-start
                    # Retain raw returned arrays even if validation rejects them.
                    native = logits > 0.0
                    path = out/f"frame-{i:03d}-box-{index:03d}.npz"
                    np.savez_compressed(path, logits=logits, predicted_ious=scores, lowres_logits=lowres, masks=native)
                    record.update(artifact_uri=str(path.absolute()), artifact_sha256=file_hash(path))
                    phase = "native_output_validation"
                    require(logits.shape == (3, image["height"], image["width"]) and scores.shape == (3,)
                            and np.isfinite(logits).all() and np.isfinite(scores).all()
                            and np.isfinite(lowres).all(), "invalid native output; no repair")
                    record.update(status="COMPLETE", mask_count=3, predicted_ious=scores.tolist(),
                        native_mask_sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in native],
                        sam_input_box_float32=np.asarray(box, dtype=np.float32).tolist(),
                        native_mask_pixel_counts=[int(m.sum()) for m in native], calibrated_confidence=None)
                except Exception as exc:
                    record.update(status="FAILURE", failure_stage=phase, error=repr(exc))
                write(out/f"frame-{i:03d}-box-{index:03d}.json", record)
                records.append(record)
            print(f"SAM frame {i+1}/50 {image['camera_id']} preserved", flush=True)
    write(out/"outputs.json", records)


def masks(root):
    root = Path(root)
    r = registration(root)
    out = root/"masks"
    out.mkdir(exist_ok=False)
    try:
        _masks(root, r, out)
    except Exception as exc:
        write(out/"runtime-failure.json", dict(error=repr(exc), hidden_retry=False))
        seal(out)
        raise
    seal(out)


def ledger(patch):
    """Record reached stages, without changing or rerunning any geometry gate."""
    m, reasons = patch["metrics"], patch["reason_codes"]
    availability_reject = any(r in reasons for r in ("EMPTY_DEPTH_AVAILABILITY_MASK", "INSUFFICIENT_VALID_DEPTH"))
    component_reject = any(r in reasons for r in ("INSUFFICIENT_CONNECTED_SUPPORT", "AMBIGUOUS_DEPTH_COMPONENTS"))
    plane_reject = any(r in reasons for r in ("INSUFFICIENT_VOXEL_SUPPORT", "PLANE_DEGENERATE",
        "INSUFFICIENT_PLANE_SUPPORT", "PLANE_RESIDUAL_TOO_LARGE"))
    eroded_reject = any(r.startswith("ERODED_PLANE_") for r in reasons)
    reached = dict(semantic_source_admission=True, mask_depth_availability=True,
        depth_components="component_sizes" in m, plane_local_geometry="fitted_point_count" in m,
        visible_boundary="boundary_point_count" in m,
        uncertainty="position_sigma_m" in m and not eroded_reject,
        grid_generation="grid_cell_count" in m,
        tool_candidate_gates="candidate_rejection_counts" in m)
    rejecting = ("mask_depth_availability" if availability_reject else "depth_components" if component_reject
                 else "plane_local_geometry" if plane_reject
                 else "uncertainty" if "POSITION_UNCERTAINTY_TOO_LARGE" in reasons
                 else "visible_boundary" if eroded_reject
                 else "grid_generation" if "GEOMETRY_GRID_BUDGET_EXCEEDED" in reasons
                 else "tool_candidate_gates")
    return {stage: ("NOT_EVALUATED" if not yes else "REJECTED" if stage == rejecting and reasons
                    else "EVALUATED") for stage, yes in reached.items()}


def geometry(root):
    root = Path(root)
    r = registration(root)
    verify_seal(root/"masks")
    require((root/"masks/outputs.json").exists(), "corpus incomplete after runtime failure; no hidden retry")
    out = root/"geometry"
    out.mkdir(exist_ok=False)
    sensor_frames, cfg, rows = frames(r["entry"]), config(), []
    for record in read(root/"masks/outputs.json"):
        row = dict(input_index=record["input_index"], image=record["image"], box_index=record["box_index"],
                   status=record["status"], native_mask_estimates=[], mask_geometry_s=[], stage_ledger=[])
        if record["status"] != "COMPLETE":
            row.update(failure_stage=record["failure_stage"], error=record["error"],
                       geometry_evaluation="NOT_EVALUATED")
        else:
            view, proprio = sensor_frames[record["image"]["frame_id"]]
            require(sensor_view_identity(view) == record["source_identity"]
                    and file_hash(record["artifact_uri"]) == record["artifact_sha256"], "mask source changed")
            with np.load(record["artifact_uri"], allow_pickle=False) as data:
                require(data["masks"].dtype == bool and data["masks"].shape == (3, *view["depth_m"].shape)
                        and np.array_equal(data["masks"], data["logits"] > 0.0), "native masks changed")
                for index, native in enumerate(data["masks"]):
                    binding = dict(source_identity=record["source_identity"], sensor_view_sha256=record["sensor_view_sha256"],
                        query=record["query"], box_index=record["box_index"], box_xyxy=record["box_xyxy"],
                        box_response_sha256=record["response_sha256"], mask_index=index,
                        raw_mask_sha256=record["native_mask_sha256"][index], mask_artifact_uri=record["artifact_uri"],
                        mask_artifact_sha256=record["artifact_sha256"], coordinate_convention="top-left-origin-pixel-xyxy",
                        mask_input_channels=["rgb"], evaluation_labels_used=False, provenance="learned estimate")
                    start = time.perf_counter()
                    estimate = estimate_segmented_patch(view, record["box_xyxy"], native, mask_binding=binding,
                        config=cfg, track_id="drawer_front_pushable", feature_id=f"box-{record['box_index']}/mask-{index}",
                        seed=0, eef_position_base_m=proprio["eef_position_base_m"],
                        measurement_contract="native-mask-depth/2")
                    row["mask_geometry_s"].append(time.perf_counter()-start)
                    row["native_mask_estimates"].append(estimate)
                    row["stage_ledger"].append(ledger(estimate["patch"]))
        write(out/f"frame-{record['input_index']:03d}-box-{record['box_index']}.json", row)
        rows.append(row)
        print(f"geometry frame {record['input_index']+1}/50 preserved", flush=True)
    write(out/"results.json", rows)
    write(out/"condition.json", dict(code=code_identity(), config=cfg.to_dict(),
        measurement_contract="native-mask-depth/2", masks_seal_sha256=file_hash(root/"masks/sealed.json"),
        registration_sha256=file_hash(root/"registration.json"),
        all_native_masks_evaluated=True, selected_mask=None, evaluation_labels_used=False, for_execution=False))
    seal(out)


def launch(root, gpu):
    root = Path(root)
    r = registration(root)
    require(gpu.startswith("GPU-"), "GPU UUID required")
    cmd = [str(Path(r["environment_receipt"]["python_executable"]).absolute()), "-m",
           "embodied_runtime.experiments.p1_formal50", "masks", "--output", str(root)]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=gpu, CUBLAS_WORKSPACE_CONFIG=":4096:8")
    start = datetime.now(timezone.utc).isoformat()
    with (root/"masks-process.log").open("x") as log:
        result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    write(root/"masks-process.json", dict(command=cmd, started_at_utc=start,
        ended_at_utc=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode, gpu_uuid=gpu, hidden_retry=False))
    require(result.returncode == 0, "SAM process failed; no hidden retry")


def review(root):
    """All-frame evaluator contact sheets, only after completed blind scoring."""
    from PIL import Image, ImageDraw
    root = Path(root)
    r = registration(root)
    for stage in ("masks", "geometry", "scoring"):
        verify_seal(root/stage)
    require(file_hash(r["entry"]["annotation_path"]) == r["entry"]["annotation_sha256"], "labels changed")
    labels = {row["image_id"]: row for row in read(r["entry"]["annotation_path"])["annotations"]}
    scored = read(root/"scoring/rows.json")
    masks = read(root/"masks/outputs.json")
    out = root/"review"
    out.mkdir(exist_ok=False)
    page_rows, inventory = [], []
    for record in masks:
        image = record["image"]
        rgb = np.asarray(Image.open(Path(r["entry"]["annotation_packet_manifest_path"]).parent/image["image_path"]).convert("RGB"))
        w, h = image["width"], image["height"]
        sheet = Image.new("RGB", (w*4, h+72), "white")
        sheet.paste(Image.fromarray(rgb), (0, 0))
        draw = ImageDraw.Draw(sheet)
        draw.text((2, h+2), f"{record['input_index']:02d} init{image['init_index']} {image['camera_id']}", fill="black")
        draw.text((2, h+20), "original RGB; no model overlay", fill="black")
        draw.text((2, h+38), f"human: {scored[record['input_index']]['human_status']}", fill="black")
        if record["status"] == "COMPLETE":
            with np.load(record["artifact_uri"], allow_pickle=False) as data:
                for ordinal, mask in enumerate(data["masks"]):
                    overlay = rgb.copy()
                    overlay[mask] = (.55*rgb[mask]+.45*np.array([255, 0, 100])).astype(np.uint8)
                    sheet.paste(Image.fromarray(overlay), ((ordinal+1)*w, 0))
                    x = (ordinal+1)*w
                    truth = labels[image["image_id"]]["entities"]["drawer_front_pushable"]
                    if truth["status"] == "VISIBLE":
                        for polygon in truth["polygons"]:
                            vertices = [(x+float(p[0]), float(p[1])) for p in polygon]
                            draw.line(vertices+[vertices[0]], fill="yellow", width=2)
                    sm = scored[record["input_index"]]["boxes"][record["box_index"]]["masks"][ordinal]
                    for candidate in sm["candidates"]:
                        if candidate["image_xy"] is not None:
                            u, v = candidate["image_xy"]
                            draw.ellipse((x+u-2, v-2, x+u+2, v+2), fill="cyan")
                    draw.text((x+2, h+2), f"BOX{record['box_index']} native{ordinal}; IoU uncalibrated", fill="black")
                    draw.text((x+2, h+20), ",".join(sm["reason_codes"]) or "geometry passed", fill="black")
                    sizes = sm["geometry_metrics"].get("component_sizes", [])
                    draw.text((x+2, h+38), f"components {sizes[:5]}; candidates {len(sm['candidates'])}", fill="black")
                    draw.text((x+2, h+54), f"label overlap {sm['mask_overlap']['annotated_purity']}", fill="black")
        else:
            draw.text((w+2, 10), f"INFERENCE FAILURE: {record.get('error')}", fill="red")
        page_rows.append(sheet)
        inventory.append(dict(input_index=record["input_index"], image_id=image["image_id"],
                              box_index=record["box_index"], page_index=(len(inventory)//5)))
        if len(page_rows) == 5 or record is masks[-1]:
            page = Image.new("RGB", (w*4, (h+72)*len(page_rows)), "white")
            for row_index, row_image in enumerate(page_rows):
                page.paste(row_image, (0, row_index*(h+72)))
            page.save(out/f"page-{(len(inventory)-1)//5:02d}.png")
            page_rows = []
    write(out/"inventory.json", dict(rows=inventory, colors={"native_mask": "pink", "human_eval_only": "yellow",
        "geometric_candidate": "cyan"}, original_rgb_column=0, all_failures_preserved=True, evaluation_only=True))
    seal(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "launch", "masks", "geometry", "score", "review"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--gpu-uuid")
    args = parser.parse_args()
    if args.stage == "launch":
        launch(args.output, args.gpu_uuid or "")
    elif args.stage == "score":
        from .p1_formal50_scoring import score
        score(args.output)
    else:
        {"prepare": prepare, "masks": masks, "geometry": geometry, "review": review}[args.stage](args.output)


if __name__ == "__main__":
    main()
