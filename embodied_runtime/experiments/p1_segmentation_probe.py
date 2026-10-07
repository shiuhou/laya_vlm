"""Two recorded development images: frozen BOX versus all native SAM2 masks.

prepare precedes model calls. BOX and SAM stages seal native evidence before
geometry. No labels, simulator, POINT, mask ranking, tracker or control paths.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.recording import replay_frames
from ..perception.rgbd_geometry import estimate_visible_patch
from ..perception.segmented_patch import estimate_segmented_patch
from ..perception.semantic_output import parse_semantic_reply
from ..perception.surface_association import sensor_view_identity
from .p1_semantic_grounding import (
    QUERIES, _cuda_allocation, _explicit_gpu_mask, _load_worker,
    frozen_geometry, infer_audited,
)
from .point_grounding_probe import SETTINGS
from .records import code_identity, file_hash


SOURCE = Path("runs/p1/surface-dev-20261006-capture02")
BOX25 = Path("runs/p1/drawer-pair-gpu-20261007/init-025-drawer_front_pushable-box-response.json")
BOX25_REQUEST = BOX25.with_name("init-025-drawer_front_pushable-box-request.json")
SAM_REVISION = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
CHECKPOINT_SHA = "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69"
CONFIG_SHA = "f932eac1c6241e910031b2f000a81cd9f8a8d4896e2277ab5ffb721f378b188d"
SAM_SETTINGS = dict(apply_postprocessing=False, mask_threshold=0.0,
                    max_hole_area=0.0, max_sprinkle_area=0.0,
                    multimask_output=True, return_logits=True, dtype="float32",
                    autocast=False, matmul_tf32=False, cudnn_tf32=False,
                    deterministic_algorithms=True, cublas_workspace_config=":4096:8",
                    seed=1, mask_order="native_decoder_tokens_1_2_3")


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open("x") as stream:
        stream.write(canonical_json(value)+"\n")


def view_for(source, init):
    bundles = list(replay_frames(Path(source)/f"init-{init:03d}"))
    require(len(bundles) == 1, "one sealed development exposure required")
    env, views = bundles[0]
    view = next(v for v in views if v["camera_id"] == "robot0_eye_in_hand")
    require(view["rgb"].shape == (256, 384, 3), "frozen development dimensions")
    return view, env.payload["proprio"]


def seal(directory):
    directory = Path(directory)
    hashes = {str(p.relative_to(directory)): file_hash(p) for p in sorted(directory.rglob("*")) if p.is_file()}
    write(directory/"sealed.json", dict(files=hashes, content_sha256=content_hash(hashes)))


def verify_seal(directory):
    directory = Path(directory)
    record = read(directory/"sealed.json")
    require(content_hash(record["files"]) == record["content_sha256"], "stage seal changed")
    for name, digest in record["files"].items():
        path = (directory/name).resolve()
        require(path.is_relative_to(directory.resolve()) and file_hash(path) == digest,
                "stage artifact changed", "SOURCE_MISMATCH")


def registration(root):
    root = Path(root)
    r = read(root/"registration.json")
    require(r["registration_content_sha256"] == content_hash({k: v for k, v in r.items()
            if k != "registration_content_sha256"}), "registration changed", "CONDITION_CHANGED")
    require(r["condition"] == "p1-box-sam2-development/1" and r["query"] == QUERIES["drawer_front_pushable"]
            and r["generation_settings"] == SETTINGS and r["sam_settings"] == SAM_SETTINGS
            and r["init_indices"] == [25, 26], "registered condition differs", "CONDITION_CHANGED")
    for path, digest in r["source_files_sha256"].items():
        require(file_hash(path) == digest, "development source changed", "SOURCE_MISMATCH")
    require(file_hash(r["checkpoint_path"]) == CHECKPOINT_SHA, "SAM checkpoint changed")
    require(file_hash(Path(r["sam_source"])/"sam2/configs/sam2.1/sam2.1_hiera_t.yaml") == CONFIG_SHA,
            "SAM config changed")
    for name, digest in r["sam_source_files_sha256"].items():
        require(file_hash(Path(r["sam_source"])/name) == digest, "SAM source changed", "CONDITION_CHANGED")
    frozen_geometry("configs/p1_geometry.json")
    if "sam_compatibility" in r:
        overlay = r["sam_compatibility"]
        require(overlay["condition"] == "sam2-dense-grid-arange/1"
                and file_hash(Path(__file__).with_name("sam2_deterministic_grid.py")) == overlay["source_sha256"],
                "registered compatibility overlay differs", "CONDITION_CHANGED")
    return r


def prepare(output, assets, inherited_boxes=None, deterministic_grid=False):
    assets = read(assets)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    inputs, source_files = [], {}
    for init in (25, 26):
        for path in sorted((SOURCE/f"init-{init:03d}").rglob("*")):
            if path.is_file():
                source_files[str(path.resolve())] = file_hash(path)
        view, _ = view_for(SOURCE, init)
        identity = sensor_view_identity(view)
        inputs.append(dict(init_index=init, source_identity=identity,
                           sensor_view_sha256=content_hash(identity)))
    for path in (SOURCE/"registration.json", SOURCE/"inputs.json", BOX25, BOX25_REQUEST):
        source_files[str(path.resolve())] = file_hash(path)
    require(assets["checkpoint_sha256"] == CHECKPOINT_SHA and assets["sam_revision"] == SAM_REVISION,
            "fixed tiny assets required")
    r = dict(condition="p1-box-sam2-development/1", registered_at_utc=datetime.now(timezone.utc).isoformat(),
             code=code_identity(), baseline="1fedb9ce00d749e327a26e0f69a4c1d05499318f",
             source=str(SOURCE.resolve()), source_files_sha256=source_files,
             init_indices=[25, 26], inputs=inputs, query=QUERIES["drawer_front_pushable"],
             generation_settings=SETTINGS, new_BOX_calls=1, new_POINT_calls=0,
             box25=str(BOX25.resolve()), box25_request=str(BOX25_REQUEST.resolve()), sam_source=assets["sam_source"],
             sam_revision=SAM_REVISION, checkpoint_path=assets["checkpoint_path"],
             checkpoint_sha256=CHECKPOINT_SHA, sam_config_sha256=CONFIG_SHA,
             sam_settings=SAM_SETTINGS, environment_receipt=assets,
             sam_source_files_sha256={str(p.relative_to(assets["sam_source"])): file_hash(p)
                 for p in sorted((Path(assets["sam_source"])/"sam2").rglob("*"))
                 if p.is_file() and p.suffix in {".py", ".yaml"}},
             mask_geometry_condition="outside native mask depth NaN; unchanged original BOX and denominator",
             native_masks_per_box=3, selected_mask=None, calibrated_confidence=None,
             evaluation_labels_used=False, sealed50_evaluation_read=False,
             independent_evaluation=False, for_execution=False, tracker_calls=0,
             qwen_calls=0, laya_calls=0, controls=0,
             failure_rule="stop runtime/invalid output/incomplete generation; retain every ordinary geometry rejection")
    if inherited_boxes is not None:
        prior_root = Path(inherited_boxes).absolute()
        prior = registration(prior_root)
        verify_seal(prior_root/"boxes")
        for key in ("inputs", "query", "generation_settings", "sam_settings", "checkpoint_sha256",
                    "sam_config_sha256", "sam_source_files_sha256", "source_files_sha256"):
            require(prior[key] == r[key], "inherited condition differs", "CONDITION_CHANGED")
        r["new_BOX_calls"] = 0
        r["inherited_boxes"] = dict(root=str(prior_root),
            registration_sha256=file_hash(prior_root/"registration.json"),
            boxes_seal_sha256=file_hash(prior_root/"boxes/sealed.json"),
            correction="invoke absolute venv executable without symlink resolution",
            independent_replication=False)
    if deterministic_grid:
        require(inherited_boxes is not None, "compatibility continuation requires sealed BOX inheritance")
        r["sam_compatibility"] = dict(condition="sam2-dense-grid-arange/1",
            source_sha256=file_hash(Path(__file__).with_name("sam2_deterministic_grid.py")),
            change="dense grid ones/cumsum replaced by exact float32 arange; no learned buffer change",
            strict_determinism=True, numerical_gate="bitwise native-size coordinate/PE checks before images")
    r["registration_content_sha256"] = content_hash(r)
    write(root/"registration.json", r)
    registration(root)


def reuse_boxes(root):
    root = Path(root)
    r = registration(root)
    inherited = r["inherited_boxes"]
    prior_root = Path(inherited["root"])
    require(file_hash(prior_root/"registration.json") == inherited["registration_sha256"]
            and file_hash(prior_root/"boxes/sealed.json") == inherited["boxes_seal_sha256"],
            "inherited registration/seal changed", "SOURCE_MISMATCH")
    prior = registration(prior_root)
    verify_seal(prior_root/"boxes")
    require(r["new_BOX_calls"] == 0 and r["inputs"] == prior["inputs"]
            and r["query"] == prior["query"] and r["generation_settings"] == prior["generation_settings"],
            "inherited BOX condition differs", "CONDITION_CHANGED")
    rows = read(prior_root/"boxes/inputs.json")
    require([row["init_index"] for row in rows] == r["init_indices"], "inherited sample order differs")
    for row in rows:
        init = row["init_index"]
        view, _ = view_for(r["source"], init)
        require(row["source_identity"] == sensor_view_identity(view) and row["query"] == r["query"],
                "inherited BOX sensor source differs", "SOURCE_MISMATCH")
        if init == 25:
            response = read(prior_root/"boxes/init-025-original-response.json")
            raw, audit = response["raw_output"], response["audit"]
        else:
            raw = read(prior_root/"boxes/init-026-raw-output.json")["raw_response"]
            audit = read(prior_root/"boxes/init-026-audit.json")
        parsed = parse_semantic_reply(raw, 384, 256, mode="box", audit=audit)
        require(parsed.admitted and canonical_json(parsed.evidence())
                == canonical_json(read(prior_root/f"boxes/init-{init:03d}-typed.json"))
                and [list(a.pixels) for a in parsed.selected] == row["ordered_boxes"],
                "inherited whole-output BOX parse differs", "SOURCE_MISMATCH")
    shutil.copytree(prior_root/"boxes", root/"boxes")
    # A byte-identical inherited seal is preserved; continuation lineage is separate.
    write(root/"boxes-inheritance.json", dict(**inherited, code=code_identity(), new_model_calls=0))
    verify_seal(root/"boxes")


def boxes(root):
    root = Path(root)
    r = registration(root)
    require(r["new_BOX_calls"] == 1 and "inherited_boxes" not in r,
            "continuation forbids new semantic calls; use reuse-boxes", "CONDITION_CHANGED")
    out = root/"boxes"
    out.mkdir(exist_ok=False)
    write(out/"condition.json", dict(code=code_identity(), registration_sha256=file_hash(root/"registration.json")))
    try:
        rows = []
        for init in (25, 26):
            view, _ = view_for(r["source"], init)
            if init == 25:
                response = read(r["box25"])
                source = sensor_view_identity(view)
                request = read(r["box25_request"])
                require(response["frame"]["rgb_sha256"] == source["rgb_sha256"]
                        and response["frame"]["frame_id"] == source["frame_id"]
                        and response["frame"]["camera_id"] == source["camera_id"]
                        and response["frame"]["calibration_version"] == source["calibration_version"]
                        and response["frame"]["sensor_view_sha256"] == content_hash(source)
                        and response["entity"] == "drawer_front_pushable" and response["mode"] == "box"
                        and request["frame"] == response["frame"]
                        and request["question"] == f"Locate a single instance that matches the following description: {r['query']}.",
                        "BOX25 source/query mismatch", "SOURCE_MISMATCH")
                raw, audit = response["raw_output"], response["audit"]
                write(out/"init-025-original-response.json", response)
                response_hash = file_hash(r["box25"])
            else:
                worker, identity = _load_worker()
                require(_explicit_gpu_mask().startswith("GPU-"), "identifiable GPU UUID required")
                worker.torch.set_num_threads(8)
                worker.torch.manual_seed(1)
                write(out/"LocateAnything-identity.json", identity)
                raw, audit = infer_audited(worker, view["rgb"], r["query"],
                    lambda kind, value: write(out/f"init-026-{kind}.json", value))
                write(out/"init-026-audit.json", audit)
                response_hash = file_hash(out/"init-026-raw-output.json")
            reply = parse_semantic_reply(raw, 384, 256, mode="box", audit=audit)
            write(out/f"init-{init:03d}-typed.json", reply.evidence())
            require(reply.admitted, "complete typed BOX required; no retry", "SEMANTIC_OUTPUT_NOT_ADMITTED")
            rows.append(dict(init_index=init, source_identity=sensor_view_identity(view),
                             response_sha256=response_hash, ordered_boxes=[list(a.pixels) for a in reply.selected],
                             query=r["query"], calibrated_confidence=None))
        write(out/"inputs.json", rows)
        seal(out)
    except Exception as exc:
        write(out/"failure.json", dict(error=repr(exc), hidden_retry=False))
        raise


def _masks_native(root):
    root = Path(root)
    r = registration(root)
    verify_seal(root/"boxes")
    out = root/"masks"
    out.mkdir(exist_ok=False)
    import torch
    expected_executable = r["environment_receipt"]["python_executable"]
    environment = dict(executable=sys.executable, prefix=sys.prefix, base_prefix=sys.base_prefix,
                       torch=torch.__version__, expected_executable=expected_executable)
    write(out/"process-environment.json", environment)
    require(os.path.abspath(sys.executable) == os.path.abspath(expected_executable)
            and Path(sys.prefix).absolute() == Path(expected_executable).absolute().parent.parent,
            "prepared venv invocation required; do not resolve executable symlink", "ENVIRONMENT_MISMATCH")
    require(torch.__version__ == "2.5.1+cu121", "isolated locked Torch condition required")
    require(os.environ.get("CUBLAS_WORKSPACE_CONFIG") == SAM_SETTINGS["cublas_workspace_config"],
            "explicit deterministic CuBLAS workspace required before CUDA initialization")
    mask = _explicit_gpu_mask()
    require(mask.startswith("GPU-"), "GPU UUID allocation required")
    allocation = _cuda_allocation(torch, mask)
    import sam2
    require(Path(sam2.__file__).resolve().is_relative_to(Path(r["sam_source"]).resolve()),
            "SAM import differs from pinned source checkout", "CONDITION_CHANGED")
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    torch.manual_seed(1)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    write(out/"condition.json", dict(code=code_identity(), registration_sha256=file_hash(root/"registration.json"),
                                     allocation=allocation, sam_settings=SAM_SETTINGS,
                                     sam_compatibility=r.get("sam_compatibility"),
                                     model_inputs=["original_full_RGB", "sealed_BOX_xyxy"],
                                     evaluation_labels_used=False, depth_to_SAM=False))
    try:
        model = build_sam2("configs/sam2.1/sam2.1_hiera_t.yaml", r["checkpoint_path"],
                           device="cuda:0", apply_postprocessing=False)
        if "sam_compatibility" in r:
            from .sam2_deterministic_grid import install_and_verify
            write(out/"dense-grid-equivalence.json", install_and_verify(model))
        predictor = SAM2ImagePredictor(model, mask_threshold=0.0, max_hole_area=0.0, max_sprinkle_area=0.0)
        records = []
        with torch.inference_mode():
            for row in read(root/"boxes/inputs.json"):
                view, _ = view_for(r["source"], row["init_index"])
                require(sensor_view_identity(view) == row["source_identity"], "BOX/SAM source mismatch")
                torch.cuda.synchronize()
                start = time.perf_counter()
                # Same RGB bytes; writable copy avoids torchvision's readonly-array warning.
                predictor.set_image(view["rgb"].copy())
                torch.cuda.synchronize()
                encode_s = time.perf_counter()-start
                for index, box in enumerate(row["ordered_boxes"]):
                    torch.cuda.synchronize()
                    start = time.perf_counter()
                    logits, scores, lowres = predictor.predict(box=np.asarray(box, dtype=np.float32),
                        multimask_output=True, return_logits=True)
                    torch.cuda.synchronize()
                    predict_s = time.perf_counter()-start
                    require(logits.shape == (3, 256, 384) and scores.shape == (3,)
                            and np.isfinite(logits).all() and np.isfinite(scores).all()
                            and np.isfinite(lowres).all(), "invalid native masks; no repair", "INVALID_OUTPUT")
                    native = logits > 0.0
                    path = out/f"init-{row['init_index']:03d}-box-{index:03d}.npz"
                    np.savez_compressed(path, logits=logits, predicted_ious=scores, lowres_logits=lowres, masks=native)
                    record = dict(**row, box_index=index, box_xyxy=box, artifact_uri=str(path.resolve()),
                                  artifact_sha256=file_hash(path), encode_s=encode_s, predict_s=predict_s,
                                  sam_input_box_float32=np.asarray(box, dtype=np.float32).tolist(),
                                  native_mask_sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in native],
                                  predicted_ious=scores.tolist(), mask_count=3, selected_mask=None,
                                  source_boundary="RGB-only learned mask; query is BOX provenance, not a SAM text input")
                    write(out/f"init-{row['init_index']:03d}-box-{index:03d}.json", record)
                    records.append(record)
        write(out/"outputs.json", records)
        seal(out)
    except Exception as exc:
        write(out/"failure.json", dict(error=repr(exc), hidden_retry=False))
        raise


def masks(root):
    # Device/version/import failures precede model loading but remain evidence.
    try:
        _masks_native(root)
    except Exception as exc:
        failure = Path(root)/"masks/failure.json"
        if failure.parent.is_dir() and not failure.exists():
            write(failure, dict(error=repr(exc), hidden_retry=False, stage="before_native_model_call"))
        raise


def geometry(root):
    root = Path(root)
    r = registration(root)
    verify_seal(root/"boxes")
    verify_seal(root/"masks")
    out = root/"geometry"
    out.mkdir(exist_ok=False)
    config = frozen_geometry("configs/p1_geometry.json")
    results = []
    for record in read(root/"masks/outputs.json"):
        view, proprio = view_for(r["source"], record["init_index"])
        source = sensor_view_identity(view)
        require(source == record["source_identity"] and file_hash(record["artifact_uri"]) == record["artifact_sha256"],
                "mask artifact/source changed", "SOURCE_MISMATCH")
        start = time.perf_counter()
        baseline = estimate_visible_patch(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
            roi_xyxy=record["box_xyxy"], source_frame_id=source["frame_id"],
            calibration_version=source["calibration_version"], track_id="drawer_front_pushable",
            feature_id=f"box-{record['box_index']}", capture_sim_time_s=view["capture_sim_time_s"],
            capture_monotonic_ns=view["capture_monotonic_ns"], config=config, seed=0,
            eef_position_base_m=proprio["eef_position_base_m"]).to_dict()
        baseline_geometry_s = time.perf_counter()-start
        estimates = []
        mask_geometry_s = []
        with np.load(record["artifact_uri"], allow_pickle=False) as data:
            require(data["masks"].dtype == bool and data["masks"].shape == (3, 256, 384), "mask shape changed")
            require(np.array_equal(data["masks"], data["logits"] > 0.0), "mask/logit relation changed")
            for index, native in enumerate(data["masks"]):
                binding = dict(source_identity=source, sensor_view_sha256=content_hash(source),
                    query=r["query"], box_index=record["box_index"], box_xyxy=record["box_xyxy"],
                    box_response_sha256=record["response_sha256"], mask_index=index,
                    raw_mask_sha256=record["native_mask_sha256"][index],
                    mask_artifact_uri=record["artifact_uri"], mask_artifact_sha256=record["artifact_sha256"],
                    coordinate_convention="top-left-origin-pixel-xyxy", mask_input_channels=["rgb"],
                    evaluation_labels_used=False, provenance="learned estimate")
                start = time.perf_counter()
                estimates.append(estimate_segmented_patch(view, record["box_xyxy"], native,
                    mask_binding=binding, config=config, track_id="drawer_front_pushable",
                    feature_id=f"box-{record['box_index']}/mask-{index}", seed=0,
                    eef_position_base_m=proprio["eef_position_base_m"]))
                mask_geometry_s.append(time.perf_counter()-start)
        results.append(dict(init_index=record["init_index"], box_index=record["box_index"],
                            baseline=baseline, native_mask_estimates=estimates,
                            baseline_geometry_s=baseline_geometry_s, mask_geometry_s=mask_geometry_s,
                            semantic_association="UNKNOWN_UNREVIEWED_MULTIMASK_HYPOTHESES",
                            calibrated_confidence=None, for_execution=False))
    write(out/"results.json", results)
    write(out/"condition.json", dict(code=code_identity(), registration_sha256=file_hash(root/"registration.json"),
                                     geometry_config=config.to_dict(), selected_mask=None,
                                     geometry_gates_changed=False, tracker_started=False, for_execution=False))
    seal(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "boxes", "reuse-boxes", "masks", "geometry"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--assets", help="pinned model/environment receipt, prepare only")
    parser.add_argument("--reuse-boxes-from", help="sealed predecessor root, prepare only")
    parser.add_argument("--deterministic-grid", action="store_true", help="preregister dense-grid compatibility overlay")
    args = parser.parse_args()
    if args.stage == "prepare":
        require(args.assets is not None, "assets receipt required")
        prepare(args.output, args.assets, args.reuse_boxes_from, args.deterministic_grid)
    else:
        {"boxes": boxes, "reuse-boxes": reuse_boxes, "masks": masks, "geometry": geometry}[args.stage](args.output)


if __name__ == "__main__":
    main()
