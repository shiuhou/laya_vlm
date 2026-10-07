"""Prospective measurement repair on sealed masks; no inference or label input."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import time

import numpy as np

from ..contracts import canonical_json, content_hash, require
from ..perception.rgbd_geometry import GeometryConfig, estimate_visible_patch
from ..perception.segmented_patch import estimate_segmented_patch
from ..perception.surface_association import sensor_view_identity
from .p1_segmentation_probe import SAM_SETTINGS, read, seal, verify_seal, view_for, write
from .p1_semantic_grounding import GEOMETRY_CODE_SHA256, GEOMETRY_FILE_SHA256, GEOMETRY_RESOLVED_SHA256, QUERIES
from .records import code_identity, file_hash


BASELINE = "b5ada28becf7b84c57d4ea5c5dc41e78a1f42182"
CONTRACT = "native-mask-depth/2"
GEOMETRY = Path("embodied_runtime/perception/rgbd_geometry.py")
WRAPPER = Path("embodied_runtime/perception/segmented_patch.py")


def config():
    require(file_hash("configs/p1_geometry.json") == GEOMETRY_FILE_SHA256,
            "geometry thresholds changed", "CONDITION_CHANGED")
    result = GeometryConfig.load("configs/p1_geometry.json")
    require(content_hash(result.to_dict()) == GEOMETRY_RESOLVED_SHA256, "resolved geometry differs")
    return result


def downstream_ast(text):
    fn = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "estimate_visible_patch")
    index = next(i for i, n in enumerate(fn.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "components" for t in n.targets))
    return [ast.dump(n, include_attributes=False) for n in fn.body[index:]]


def source_receipt(source):
    root = Path(source)
    r = read(root/"registration.json")
    require(r["registration_content_sha256"] == content_hash({k: v for k, v in r.items()
            if k != "registration_content_sha256"}), "historical registration changed")
    require(r["code"]["commit"] == BASELINE and r["code"]["dirty_status"] == ""
            and r["sam_settings"] == SAM_SETTINGS and r["query"] == QUERIES["drawer_front_pushable"]
            and r["init_indices"] == [25, 26], "sealed condition differs", "SOURCE_MISMATCH")
    require(r["code"]["source_sha256"][str(GEOMETRY)] == GEOMETRY_CODE_SHA256,
            "wrong historical geometry source")
    for path, digest in r["source_files_sha256"].items():
        require(file_hash(path) == digest, "recorded evidence changed", "SOURCE_MISMATCH")
    for stage in ("boxes", "masks", "geometry"):
        verify_seal(root/stage)
    return r


def prepare(source, output):
    config()
    original = source_receipt(source)
    legacy = subprocess.check_output(["git", "show", f"{BASELINE}:{GEOMETRY}"], text=True)
    require(downstream_ast(legacy) == downstream_ast(GEOMETRY.read_text()),
            "component/plane/edge/uncertainty/tool/candidate-order code changed", "CONDITION_CHANGED")
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    masks = read(Path(source)/"masks/outputs.json")
    require([m["init_index"] for m in masks] == [25, 26] and all(m["mask_count"] == 3 for m in masks),
            "retain all six native masks")
    r = dict(condition="p1-mask-support-reanalysis/1", registered_at_utc=datetime.now(timezone.utc).isoformat(),
        code=code_identity(), frozen_inference_code=BASELINE, source_root=str(Path(source).absolute()),
        source_registration_sha256=file_hash(Path(source)/"registration.json"),
        source_seals={stage: file_hash(Path(source)/stage/"sealed.json") for stage in ("boxes", "masks", "geometry")},
        original_condition=original["condition"], measurement_contract=CONTRACT,
        availability="valid depth inside complete native mask / complete native mask pixels",
        coverage="native mask inside original BOX / original BOX pixels; diagnostic only",
        fitting_domain="unchanged original BOX with outside-mask depth UNKNOWN",
        new_source_sha256={str(p): file_hash(p) for p in (GEOMETRY, WRAPPER, Path(__file__))},
        geometry_config_sha256=GEOMETRY_FILE_SHA256, downstream_ast_unchanged=True,
        ordered_samples=[25, 26], ordered_native_masks=[0, 1, 2], selected_mask=None,
        LocateAnything_calls=0, SAM_calls=0, model_inputs_changed=False, masks_changed=False,
        thresholds_changed=False, candidate_order_changed=False, evaluation_labels_consumed=False,
        controls=0, tracker_calls=0, Qwen_calls=0, Laya_calls=0, for_execution=False,
        stop_development_tuning_after_reanalysis=True,
        next_milestone="frozen pipeline to50frame evaluation, then10temporal sequences and GateA/B/C")
    r["registration_content_sha256"] = content_hash(r)
    write(root/"registration.json", r)


def reanalyze(output):
    root = Path(output)
    r = read(root/"registration.json")
    require(r["registration_content_sha256"] == content_hash({k: v for k, v in r.items()
            if k != "registration_content_sha256"}), "new registration changed")
    require(r["measurement_contract"] == CONTRACT, "measurement condition changed")
    for path, digest in r["new_source_sha256"].items():
        require(file_hash(path) == digest, "reanalysis source changed", "CONDITION_CHANGED")
    source = Path(r["source_root"])
    original = source_receipt(source)
    require(file_hash(source/"registration.json") == r["source_registration_sha256"]
            and all(file_hash(source/s/"sealed.json") == digest for s, digest in r["source_seals"].items()),
            "sealed input lineage changed")
    out = root/"geometry"
    out.mkdir(exist_ok=False)
    results = []
    old_rows = read(source/"geometry/results.json")
    records = read(source/"masks/outputs.json")
    require(len(records) == len(old_rows) == 2
            and [row["init_index"] for row in records] == [25, 26]
            and [row["init_index"] for row in old_rows] == [25, 26]
            and all(len(row["native_mask_estimates"]) == 3 for row in old_rows),
            "complete ordered two-frame/six-mask input required")
    for record, old_row in zip(records, old_rows):
        view, proprio = view_for(original["source"], record["init_index"])
        identity = sensor_view_identity(view)
        require(identity == record["source_identity"] and file_hash(record["artifact_uri"]) == record["artifact_sha256"],
                "native mask artifact/sensor mismatch", "SOURCE_MISMATCH")
        baseline = estimate_visible_patch(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
            roi_xyxy=record["box_xyxy"], source_frame_id=identity["frame_id"],
            calibration_version=identity["calibration_version"], track_id="drawer_front_pushable",
            feature_id=f"box-{record['box_index']}", capture_sim_time_s=view["capture_sim_time_s"],
            capture_monotonic_ns=view["capture_monotonic_ns"], config=config(), seed=0,
            eef_position_base_m=proprio["eef_position_base_m"]).to_dict()
        require(canonical_json(baseline) == canonical_json(old_row["baseline"]),
                "defaultBOX regression mismatch", "NUMERICAL_MISMATCH")
        estimates, seconds = [], []
        with np.load(record["artifact_uri"], allow_pickle=False) as data:
            require(data["masks"].dtype == bool and data["masks"].shape == (3, 256, 384)
                    and np.array_equal(data["masks"], data["logits"] > 0.0), "native masks changed")
            for index, native in enumerate(data["masks"]):
                binding = old_row["native_mask_estimates"][index]["mask_binding"]
                require(binding["mask_index"] == index and binding["box_index"] == record["box_index"],
                        "native mask/BOX order differs")
                args = dict(mask_binding=binding, config=config(), track_id="drawer_front_pushable",
                    feature_id=f"box-{record['box_index']}/mask-{index}", seed=0,
                    eef_position_base_m=proprio["eef_position_base_m"])
                legacy = estimate_segmented_patch(view, record["box_xyxy"], native,
                    measurement_contract="original-box-depth/1", **args)
                require(canonical_json(legacy) == canonical_json(old_row["native_mask_estimates"][index]),
                        "legacy-mask regression mismatch", "NUMERICAL_MISMATCH")
                start = time.perf_counter()
                estimates.append(estimate_segmented_patch(view, record["box_xyxy"], native,
                    measurement_contract=CONTRACT, **args))
                seconds.append(time.perf_counter()-start)
        results.append(dict(init_index=record["init_index"], box_index=record["box_index"],
            baseline=baseline, native_mask_estimates=estimates, geometry_s=seconds,
            defaultBOX_unchanged=True, legacy_mask_results_unchanged=True,
            semantic_association="UNKNOWN_NO_DEV_HUMAN_LABELS", calibrated_confidence=None,
            selected_mask=None, for_execution=False))
    write(out/"results.json", results)
    write(out/"condition.json", r)
    seal(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "reanalyze"])
    parser.add_argument("--source", default="runs/p1/box-sam2-grid-complete-20261007")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare(args.source, args.output)
    else:
        reanalyze(args.output)


if __name__ == "__main__":
    main()
