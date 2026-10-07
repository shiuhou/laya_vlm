"""Offline Formal-50 scoring. Human labels are opened only after stage seals.

This evaluator never selects a mask, component, candidate, or runtime target.
Continuous polygon overlap is a diagnostic, not a new acceptance threshold.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path

import numpy as np

from ..contracts import content_hash, require
from ..perception.evaluation_annotations import _inside, image_binding
from ..perception.recording import project_base_points
from .p1_segmentation_probe import read, write, seal, verify_seal

TAXONOMY = ("UNKNOWN", "NOT_VISIBLE", "SEMANTIC_BOX_FAILURE", "SEGMENTATION_IDENTITY_FAILURE",
            "INSUFFICIENT_DEPTH", "AMBIGUOUS_DEPTH_COMPONENTS", "GEOMETRY_REJECTED",
            "EDGE_UNCERTAINTY_TOOL_REJECTED", "VALID_DRAWER_FRONT_CANDIDATE",
            "GEOMETRIC_CANDIDATE", "INFERENCE_FAILURE", "GEOMETRY_FAILURE")


def taxonomy_counts(values):
    counts = Counter(values)
    return {key: counts[key] for key in (*TAXONOMY, *sorted(set(counts)-set(TAXONOMY)))}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geometry_category(patch):
    """First reached failure boundary, independent of evaluator identity."""
    reasons = patch["reason_codes"]
    if any(r in {"INSUFFICIENT_VALID_DEPTH", "EMPTY_DEPTH_AVAILABILITY_MASK",
                 "INSUFFICIENT_CONNECTED_SUPPORT"} for r in reasons):
        return "INSUFFICIENT_DEPTH"
    if "AMBIGUOUS_DEPTH_COMPONENTS" in reasons:
        return "AMBIGUOUS_DEPTH_COMPONENTS"
    if patch["geometry_status"] == "VALID":
        return "GEOMETRIC_CANDIDATE" if patch["candidates"] else "EDGE_UNCERTAINTY_TOOL_REJECTED"
    if any("UNCERTAINTY" in r or r.startswith("ERODED_") or "TOOL" in r or "EDGE" in r
           for r in reasons):
        return "EDGE_UNCERTAINTY_TOOL_REJECTED"
    return "GEOMETRY_REJECTED"


def polygon_mask(image, truth):
    if truth["status"] != "VISIBLE":
        return None
    yy, xx = np.indices((image["height"], image["width"]))
    return _inside(np.column_stack((xx.ravel()+.5, yy.ravel()+.5)),
                   truth["polygons"]).reshape(xx.shape)


def overlap_metrics(mask, label):
    count = int(mask.sum())
    overlap = int((mask & label).sum()) if label is not None else None
    return dict(pixel_count=count, annotated_overlap_pixels=overlap,
                annotated_coverage=overlap/int(label.sum()) if label is not None and label.any() else None,
                annotated_purity=overlap/count if label is not None and count else None,
                contamination=1-overlap/count if label is not None and count else None,
                evaluation_only=True)


def box_metrics(box, image, label):
    yy, xx = np.indices((image["height"], image["width"]))
    mask = ((xx+.5 >= box[0]) & (xx+.5 < box[2]) &
            (yy+.5 >= box[1]) & (yy+.5 < box[3]))
    metrics = overlap_metrics(mask, label)
    metrics.update(intersects_annotated_region=metrics["annotated_overlap_pixels"] > 0 if label is not None else None,
                   fully_covers_annotated_region=bool(np.all(mask[label])) if label is not None and label.any() else None)
    return metrics


def score_mask(image, truth, mask, estimate, *, ordinal, box, stage_ledger=None):
    """Evaluate a native mask without changing its frozen geometry outcome."""
    label = polygon_mask(image, truth)
    metrics = overlap_metrics(mask, label)
    bm = box_metrics(box, image, label)
    patch = estimate["patch"]
    source = estimate["source_identity"]
    candidates = []
    for candidate in patch["candidates"]:
        uv = project_base_points([candidate["position_base_m"]], source["intrinsics_K"],
                                 source["T_base_camera"])[0]
        finite = bool(np.isfinite(uv).all())
        inside = bool(_inside(np.asarray([uv]), truth["polygons"])[0]) if label is not None and finite else None
        candidates.append(dict(point_id=candidate["point_id"], image_xy=uv.tolist() if finite else None,
            inside_annotated_region=inside, evaluation_category=("VALID_DRAWER_FRONT_CANDIDATE" if inside is True
                and patch["geometry_status"] == "VALID" else "SEGMENTATION_IDENTITY_FAILURE" if inside is False
                else truth["status"] if label is None else "GEOMETRY_REJECTED"),
            usable_status=candidate["usable_status"], reason_codes=candidate["reason_codes"],
            executable_acceptance=False, evaluation_only=True))
    geometry = geometry_category(patch)
    if label is None:
        category = truth["status"]
    elif bm["annotated_overlap_pixels"] == 0:
        category = "SEMANTIC_BOX_FAILURE"
    elif metrics["annotated_overlap_pixels"] == 0:
        category = "SEGMENTATION_IDENTITY_FAILURE"
    elif any(c["evaluation_category"] == "SEGMENTATION_IDENTITY_FAILURE" for c in candidates):
        # Do not hide wrong-target candidates behind another successful point.
        category = "SEGMENTATION_IDENTITY_FAILURE"
    elif any(c["evaluation_category"] == "VALID_DRAWER_FRONT_CANDIDATE" for c in candidates):
        category = "VALID_DRAWER_FRONT_CANDIDATE"
    else:
        category = geometry
    return dict(native_mask_ordinal=ordinal, human_status=truth["status"],
        geometry_category=geometry, evaluation_category=category, mask_overlap=metrics,
        box_overlap=bm, geometry_status=patch["geometry_status"],
        reason_codes=patch["reason_codes"], geometry_metrics=patch["metrics"],
        stage_ledger=stage_ledger, candidates=candidates,
        task_valid_candidate_count=sum(c["evaluation_category"] == "VALID_DRAWER_FRONT_CANDIDATE" for c in candidates),
        outside_region_candidate_count=sum(c["inside_annotated_region"] is False for c in candidates),
        downstream_rejected_stages_not_evaluated=True, evaluation_only=True)


def _percentiles(values):
    values = [float(v) for v in values if v is not None and np.isfinite(v)]
    return dict(n=len(values), p50_s=float(np.percentile(values, 50)) if values else None,
                p95_s=float(np.percentile(values, 95)) if values else None)


def _distribution(values):
    result = _percentiles(values)
    return dict(n=result["n"], p50=result["p50_s"], p95=result["p95_s"])


def summarize(rows):
    result = {}
    for camera in ("agentview", "robot0_eye_in_hand", "total"):
        selected = [r for r in rows if camera == "total" or r["camera_id"] == camera]
        native = [m for r in selected for b in r["boxes"] for m in b["masks"]]
        boxes = [b for r in selected for b in r["boxes"]]
        visible = [r for r in selected if r["human_status"] == "VISIBLE"]
        visible_boxes = [b for r in visible for b in r["boxes"]]
        bm = [b["box_overlap"] for b in visible_boxes]
        count = len(visible)
        full_frames = sum(any(b["box_overlap"]["fully_covers_annotated_region"] is True for b in r["boxes"]) for r in visible)
        task_frames = sum(r["task_valid_candidate_count"] > 0 for r in selected)
        visibility = Counter(r["human_status"] for r in selected)
        result[camera] = dict(frame_count=len(selected), human_visibility={s:visibility[s] for s in ("VISIBLE","UNKNOWN","NOT_VISIBLE")},
            semantic_response_failures=sum(r["semantic_failure"] for r in selected), box_count=len(boxes),
            box_grounding=dict(visible_frame_denominator=count, fully_covered_visible_frames=full_frames,
                fully_covered_visible_frame_rate=full_frames/count if count else None,
                visible_box_denominator=len(bm), intersecting_visible_boxes=sum(b["intersects_annotated_region"] is True for b in bm),
                fully_covering_visible_boxes=sum(b["fully_covers_annotated_region"] is True for b in bm),
                partially_covering_visible_boxes=sum(b["intersects_annotated_region"] is True and b["fully_covers_annotated_region"] is False for b in bm)),
            native_mask_count=len(native), geometry_taxonomy=taxonomy_counts(m["geometry_category"] for m in native),
            evaluation_taxonomy=taxonomy_counts(m["evaluation_category"] for m in native),
            frame_failure_taxonomy_nonexclusive=taxonomy_counts(category for r in selected for category in r["frame_categories"]),
            frame_failure_taxonomy_note="Each category counted once per frame; categories can coexist. No mask is selected.",
            native_ordinal_taxonomy={str(i): taxonomy_counts(m["geometry_category"] for m in native if m["native_mask_ordinal"] == i) for i in range(3)},
            visible_native_mask_overlap=dict(
                denominator=sum(m["human_status"] == "VISIBLE" for m in native),
                disjoint=sum(m["human_status"] == "VISIBLE" and m["mask_overlap"]["annotated_overlap_pixels"] == 0 for m in native),
                partial=sum(m["human_status"] == "VISIBLE" and 0 < (m["mask_overlap"]["annotated_coverage"] or 0) < 1 for m in native),
                full=sum(m["human_status"] == "VISIBLE" and m["mask_overlap"]["annotated_coverage"] == 1 for m in native),
                annotated_coverage=_distribution([m["mask_overlap"]["annotated_coverage"] for m in native]),
                annotated_purity=_distribution([m["mask_overlap"]["annotated_purity"] for m in native])),
            ambiguous_component_count=sum(m["geometry_category"] == "AMBIGUOUS_DEPTH_COMPONENTS" for m in native),
            ambiguous_component_fraction=sum(m["geometry_category"] == "AMBIGUOUS_DEPTH_COMPONENTS" for m in native)/len(native) if native else None,
            geometric_candidate_count=sum(len(m["candidates"]) for m in native),
            geometric_candidate_masks=sum(bool(m["candidates"]) for m in native),
            task_valid_candidate_count=sum(m["task_valid_candidate_count"] for m in native),
            outside_region_candidate_count=sum(m["outside_region_candidate_count"] for m in native),
            task_valid_candidate_frames=task_frames,
            task_valid_visible_frame_rate=task_frames/count if count else None,
            task_valid_all_frame_rate=task_frames/len(selected) if selected else None,
            timing=dict(encode=_percentiles([r.get("encode_s") for r in selected]),
                predict=_percentiles([b.get("predict_s") for b in boxes]),
                native_inference_total=_percentiles([b.get("native_total_s") for b in boxes]),
                mask_geometry=_percentiles([m.get("geometry_s") for m in native])),
            inference_failures=sum(b["inference_status"] != "COMPLETE" for b in boxes),
            geometry_failures=sum(b["geometry_status"] != "COMPLETE" for b in boxes))
    return result


def _verified_generation(root):
    """Authenticate and check complete coverage before any annotation read."""
    root = Path(root)
    for stage, required in (("masks", "outputs.json"), ("geometry", "results.json")):
        verify_seal(root/stage)
        require(required in read(root/stage/"sealed.json")["files"], "stage output not sealed", "SOURCE_MISMATCH")
    registration = read(root/"registration.json")
    require(registration["registration_content_sha256"] == content_hash({k: v for k, v in registration.items()
            if k != "registration_content_sha256"}), "registration changed", "SOURCE_MISMATCH")
    from .p1_formal50 import registration as verified_registration
    require(verified_registration(root) == registration, "registration changed while scoring")
    for stage in ("masks", "geometry"):
        condition = read(root/stage/"condition.json")
        require(condition["registration_sha256"] == sha(root/"registration.json"),
                "generation registration binding differs", "SOURCE_MISMATCH")
    inputs = registration["inputs"]
    entry = registration["entry"]
    require(len(inputs) == 50 and [r["image"] for r in inputs] == entry["ordered50_images"],
            "Formal-50 identity/order differs", "SOURCE_MISMATCH")
    masks, geometry = read(root/"masks/outputs.json"), read(root/"geometry/results.json")
    expected = [(i, b) for i, row in enumerate(inputs)
                for b in (range(len(row["ordered_boxes"])) if row["ordered_boxes"] else [None])]
    require([(r["input_index"], r["box_index"]) for r in masks] == expected
            and [(r["input_index"], r["box_index"]) for r in geometry] == expected,
            "complete canonical BOX outputs required", "SOURCE_MISMATCH")
    for record, geo in zip(masks, geometry):
        row = inputs[record["input_index"]]
        require(record["image"] == geo["image"] == row["image"]
            and record["source_identity"] == row["source_identity"]
            and record["sensor_view_sha256"] == content_hash(row["source_identity"])
            and record["response_sha256"] == row["response_sha256"]
            and record["query"] == row["query"]
            and (record["box_index"] is None or record["box_xyxy"] == row["ordered_boxes"][record["box_index"]]),
            "BOX/source binding differs", "SOURCE_MISMATCH")
        if record["status"] == "COMPLETE":
            path = Path(record["artifact_uri"])
            require(path.resolve().is_relative_to((root/"masks").resolve())
                and sha(path) == record["artifact_sha256"], "native artifact differs", "SOURCE_MISMATCH")
            relative = str(path.resolve().relative_to((root/"masks").resolve()))
            require(relative in read(root/"masks/sealed.json")["files"], "native artifact not sealed")
            with np.load(path, allow_pickle=False) as data:
                native = data["masks"]
                require(native.dtype == bool and native.shape == (3,row["image"]["height"],row["image"]["width"])
                    and np.array_equal(native, data["logits"] > 0), "native output shape/threshold differs")
                require([hashlib.sha256(m.tobytes()).hexdigest() for m in native] == record["native_mask_sha256"],
                    "native mask ordinal/raw bytes differ")
                require(data["predicted_ious"].tolist() == record["predicted_ious"], "native score receipt differs")
            if geo["status"] == "COMPLETE":
                require(len(geo["native_mask_estimates"]) == 3 and len(geo["mask_geometry_s"]) == 3,
                        "all three native masks required")
                for ordinal, estimate in enumerate(geo["native_mask_estimates"]):
                    binding = estimate["mask_binding"]
                    require(binding["mask_index"] == ordinal and binding["box_index"] == record["box_index"]
                        and binding["raw_mask_sha256"] == record["native_mask_sha256"][ordinal]
                        and binding["source_identity"] == estimate["source_identity"] == record["source_identity"]
                        and binding["sensor_view_sha256"] == estimate["sensor_view_sha256"] == record["sensor_view_sha256"]
                        and binding["mask_artifact_uri"] == record["artifact_uri"]
                        and binding["mask_artifact_sha256"] == record["artifact_sha256"]
                        and binding["box_xyxy"] == estimate["original_box_xyxy"] == record["box_xyxy"]
                        and binding["query"] == record["query"]
                        and binding["box_response_sha256"] == record["response_sha256"]
                        and binding["evaluation_labels_used"] is False
                        and estimate["measurement_contract"] == entry["measurement_contract"],
                        "geometry native binding differs", "SOURCE_MISMATCH")
                    metrics = estimate["patch"]["metrics"]
                    require(metrics["depth_availability_domain"] == "full_native_mask"
                        and metrics["mask_pixel_count"] == int(native[ordinal].sum())
                        and (metrics["depth_availability"] is None if metrics["mask_pixel_count"] == 0
                             else metrics["depth_availability"] == metrics["valid_depth_inside_mask"]/metrics["mask_pixel_count"]),
                        "repaired native-mask availability contract differs")
    return registration, masks, geometry


def score(root):
    root = Path(root)
    registration, masks, geometry = _verified_generation(root)
    entry = registration["entry"]
    # Hash bytes without deserializing labels; the seals above precede this.
    for path, digest in ((entry["annotation_path"], entry["annotation_sha256"]),
                         (entry["annotation_seal_path"], entry["annotation_seal_sha256"]),
                         (entry["rules_path"], entry["rules_sha256"]),
                         (entry["annotation_packet_manifest_path"], entry["annotation_packet_manifest_sha256"])):
        require(sha(path) == digest, "frozen annotation packet changed", "ANNOTATION_BINDING")
    labels = read(entry["annotation_path"])
    manifest = read(entry["annotation_packet_manifest_path"])
    require(labels["rules_version"] == manifest["rules_version"] == "p1-rgb-annotation-rules/2"
        and labels["rules_sha256"] == entry["rules_sha256"]
        and labels["dataset_id"] == manifest["dataset_id"], "legacy annotation identity differs", "ANNOTATION_BINDING")
    by_label = {label["image_id"]: label for label in labels["annotations"]}
    require(len(by_label) == 50 and set(by_label) == {im["image_id"] for im in entry["ordered50_images"]},
            "label coverage differs", "ANNOTATION_BINDING")
    grouped = {(r["input_index"],r["box_index"]): (r,g) for r,g in zip(masks,geometry)}
    rows = []
    for index, row in enumerate(registration["inputs"]):
        image = row["image"]
        annotation = by_label[image["image_id"]]
        require(image_binding(annotation) == image_binding(image), "annotation source differs", "ANNOTATION_BINDING")
        truth = annotation["entities"]["drawer_front_pushable"]
        label = polygon_mask(image,truth)
        boxes = []
        for box_index, box in enumerate(row["ordered_boxes"]):
            native, geo = grouped[index,box_index]
            scored_masks = []
            if native["status"] == "COMPLETE" and geo["status"] == "COMPLETE":
                with np.load(native["artifact_uri"],allow_pickle=False) as data:
                    for ordinal, mask in enumerate(data["masks"]):
                        ledgers = geo.get("stage_ledger")
                        scored = score_mask(image,truth,mask,geo["native_mask_estimates"][ordinal],
                            ordinal=ordinal,box=box,stage_ledger=ledgers[ordinal] if ledgers else None)
                        scored["geometry_s"] = geo["mask_geometry_s"][ordinal]
                        scored_masks.append(scored)
            boxes.append(dict(box_index=box_index, box_xyxy=box,box_overlap=box_metrics(box,image,label),
                inference_status=native["status"],geometry_status=geo["status"],
                failure=native.get("error",geo.get("error")), failure_stage=native.get("failure_stage",geo.get("failure_stage")),
                failure_category="INFERENCE_FAILURE" if native["status"] != "COMPLETE" else "GEOMETRY_FAILURE" if geo["status"] != "COMPLETE" else None,
                predict_s=native.get("predict_s"),
                native_total_s=(native["encode_s"]+native["predict_s"]) if native["status"] == "COMPLETE" else None,
                masks=scored_masks))
        categories = ({truth["status"]} if label is None else {"SEMANTIC_BOX_FAILURE"} if not boxes else
                      {m["evaluation_category"] for b in boxes for m in b["masks"]})
        categories.update(b["failure_category"] for b in boxes if b["failure_category"] is not None)
        rows.append(dict(image_id=image["image_id"],camera_id=image["camera_id"],init_index=image["init_index"],
            human_status=truth["status"],human_reason=truth["reason"],boxes=boxes,
            semantic_failure=not bool(row["ordered_boxes"]),
            frame_categories=sorted(categories),
            encode_s=grouped[index,0][0].get("encode_s") if boxes else None,
            task_valid_candidate_count=sum(m["task_valid_candidate_count"] for b in boxes for m in b["masks"]),
            selected_mask=None,selected_candidate=None,evaluation_only=True))
    out = root/"scoring"
    out.mkdir(exist_ok=False)
    write(out/"rows.json",rows)
    summary = dict(schema="p1-formal50-blind-scoring/1",by_camera=summarize(rows),
        generation_seal_sha256={s:sha(root/s/"sealed.json") for s in ("masks","geometry")},
        annotation_sha256=entry["annotation_sha256"],annotation_independence=entry["annotation_independence"],
        annotation_rules_version=labels["rules_version"],evaluation_only=True,
        runtime_identity_admitted=False,executable_candidate_acceptance=False,
        continuous_end_to_end_hz_measured=False,temporal_tracking_tested=False,
        status="P2 remains blocked pending Formal-50 / temporal P1 gate")
    write(out/"summary.json",summary)
    seal(out)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    args = parser.parse_args()
    score(args.root)


if __name__ == "__main__":
    main()
