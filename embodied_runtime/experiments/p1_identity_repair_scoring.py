"""Development-only paired POINT+BOX evaluation after all generation seals.

Raw prompt intervention and deterministic POINT admission are reported separately.
The exposed Formal-50 set is development evidence, never independent acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from pathlib import Path

import numpy as np

from ..contracts import content_hash, require
from ..perception.evaluation_annotations import _inside, image_binding
from ..perception.semantic_output import parse_semantic_reply
from .p1_segmentation_probe import read, write, seal, verify_seal
from .p1_formal50_scoring import (sha, polygon_mask, box_metrics, score_mask,
                                summarize, taxonomy_counts, _distribution, _percentiles)


def slot_taxonomy(values):
    counts = taxonomy_counts(values)
    for category in ("POINT_NOT_ADMITTED", "POINT_INFERENCE_FAILURE", "POINT_BOX_CONTRADICTION",
                     "INVALID_POINT_DEPTH", "POINT_MASK_CONTRADICTION"):
        counts.setdefault(category,0)
    return counts


def point_label_relation(point, truth):
    """Evaluator-only relation; UNKNOWN stays UNKNOWN even for a finite point."""
    if point is None:
        return None
    if truth["status"] != "VISIBLE":
        return None
    return bool(_inside(np.asarray([point], dtype=float), truth["polygons"])[0])


def verify_complete_point(point,image):
    """Raw-call completion does not grant admission to an unterminated prefix."""
    require(hashlib.sha256(point["raw_output"].encode()).hexdigest() == point["response_sha256"],
            "POINT response bytes differ")
    audit = point["audit"]
    if not (audit["complete_generation"] and audit["terminal_eos_observed"]):
        require(point["typed"] is None and point["source_admitted"] is False
            and point["point_xy"] is None and point["sample_pixel_xy"] is None
            and point["reason"] == "INCOMPLETE_GENERATION",
            "incomplete output must stay unparsed and nonadmitted")
        return
    parsed = parse_semantic_reply(point["raw_output"],image["width"],image["height"],
                                  mode="point",audit=audit)
    require(content_hash(parsed.evidence()) == content_hash(point["typed"])
            and parsed.admitted == point["source_admitted"], "typed POINT output differs")
    if parsed.admitted:
        require(len(parsed.selected) == 1 and list(parsed.selected[0].pixels) == point["point_xy"],
                "one native semantic POINT required")
        require(list(parsed.selected[0].sample_pixel_xy) == point["sample_pixel_xy"],
                "POINT sample differs from typed atom")
    else:
        require(point["point_xy"] is None and point["sample_pixel_xy"] is None,
                "nonadmitted POINT must not supply coordinates")


def _registration(root):
    registration = read(root/"registration.json")
    require(registration["registration_content_sha256"] == content_hash({k:v for k,v in registration.items()
            if k != "registration_content_sha256"}), "repair registration differs", "SOURCE_MISMATCH")
    for path, digest in registration["source_files_sha256"].items():
        require(sha(path) == digest, "repair registered source differs", "SOURCE_MISMATCH")
    entry = registration["entry"]
    require(entry["measurement_contract"] == "native-mask-depth/2"
        and len(registration["inputs"]) == 50
        and [r["image"] for r in registration["inputs"]] == entry["ordered50_images"],
        "repair Formal-50 source set differs", "SOURCE_MISMATCH")
    require(registration["evaluation_labels_used"] is False, "label-free generation required", "INFORMATION_BOUNDARY")
    return registration


def verified_generation(root):
    """Check every stage, native artifact and binding before opening labels."""
    root = Path(root)
    for stage, output in (("points", "outputs.json"), ("masks", "outputs.json"), ("geometry", "results.json")):
        verify_seal(root/stage)
        manifest = read(root/stage/"sealed.json")["files"]
        require(output in manifest and "condition.json" in manifest, "required stage output not sealed")
        condition = read(root/stage/"condition.json")
        require(condition["registration_sha256"] == sha(root/"registration.json")
                and condition["evaluation_labels_used"] is False, "generation binding/boundary differs")
    r = _registration(root)
    require(r["condition"] == "p1-point-positive-sam-repair/1", "repair condition differs")
    from .p1_identity_prompt import registration as validate_registration
    require(validate_registration(root) == r, "registered model/source pins differ")
    baseline = Path(r["baseline_root"])
    for stage in ("masks", "geometry", "scoring"):
        verify_seal(baseline/stage)
    baseline_registration = read(baseline/"registration.json")
    require(r["entry"] == baseline_registration["entry"]
        and r["inputs"] == baseline_registration["inputs"], "paired baseline inputs differ")
    require(all(len(row["ordered_boxes"]) == 1 for row in r["inputs"]),
            "frozen paired condition requires one registered BOX per frame")
    points, masks, geometry = (read(root/"points/outputs.json"), read(root/"masks/outputs.json"),
                              read(root/"geometry/results.json"))
    require([p["input_index"] for p in points] == list(range(50)), "complete ordered POINT corpus required")
    expected = [(i,b) for i,row in enumerate(r["inputs"])
                for b in (range(len(row["ordered_boxes"])) if row["ordered_boxes"] else [None])]
    require([(x["input_index"],x["box_index"]) for x in masks] == expected
        and [(x["input_index"],x["box_index"]) for x in geometry] == expected,
        "complete canonical BOX outputs required")
    for point, row in zip(points,r["inputs"]):
        require(point["image"] == row["image"] and point["source_identity"] == row["source_identity"]
            and point["query"] == row["query"], "POINT sensor/query binding differs")
        if point["status"] == "COMPLETE":
            verify_complete_point(point,row["image"])
    mask_seal = read(root/"masks/sealed.json")["files"]
    for mask, geo in zip(masks,geometry):
        row, point = r["inputs"][mask["input_index"]], points[mask["input_index"]]
        require(mask["image"] == geo["image"] == row["image"]
            and mask["source_identity"] == row["source_identity"]
            and mask["sensor_view_sha256"] == content_hash(row["source_identity"])
            and mask["response_sha256"] == row["response_sha256"]
            and mask["query"] == row["query"], "paired BOX source differs")
        if mask["status"] != "COMPLETE":
            require(geo["status"] != "COMPLETE" and not geo["native_mask_estimates"],
                    "failed SAM cannot have fabricated geometry")
            continue
        require(point["source_admitted"] is True and mask["point_xy"] == point["point_xy"]
            and mask["point_response_sha256"] == point["response_sha256"], "SAM positive POINT source differs")
        box_index = mask["box_index"]
        require(box_index is not None and mask["box_xyxy"] == row["ordered_boxes"][box_index],
                "SAM original BOX differs")
        path = Path(mask["artifact_uri"])
        require(path.resolve().is_relative_to((root/"masks").resolve())
            and str(path.resolve().relative_to((root/"masks").resolve())) in mask_seal
            and sha(path) == mask["artifact_sha256"], "native mask artifact differs")
        with np.load(path,allow_pickle=False) as data:
            native = data["masks"]
            image = row["image"]
            require(native.dtype == bool and native.shape == (3,image["height"],image["width"])
                and np.array_equal(native,data["logits"] > 0)
                and data["predicted_ious"].tolist() == mask["predicted_ious"], "native decoder output differs")
            require([hashlib.sha256(m.tobytes()).hexdigest() for m in native] == mask["native_mask_sha256"],
                    "native masks/ordinals differ")
        require(geo["status"] == "COMPLETE" and len(geo["native_mask_estimates"]) == 3
            and len(geo["mask_geometry_s"]) == 3 and len(geo["mask_point_admission"]) == 3,
            "all native raw geometries and admissions required")
        for ordinal, (estimate,admission) in enumerate(zip(geo["native_mask_estimates"],geo["mask_point_admission"])):
            binding = estimate["mask_binding"]
            require(binding["mask_index"] == admission["native_mask_ordinal"] == ordinal
                and binding["box_index"] == box_index
                and binding["source_identity"] == estimate["source_identity"] == row["source_identity"]
                and binding["raw_mask_sha256"] == mask["native_mask_sha256"][ordinal]
                and binding["mask_artifact_uri"] == mask["artifact_uri"]
                and binding["mask_artifact_sha256"] == mask["artifact_sha256"]
                and binding["box_xyxy"] == estimate["original_box_xyxy"] == mask["box_xyxy"]
                and binding["box_response_sha256"] == row["response_sha256"]
                and binding["evaluation_labels_used"] is False
                and estimate["measurement_contract"] == r["entry"]["measurement_contract"],
                "raw geometry binding differs")
            x,y = admission["sample_pixel_xy"]
            require(admission["sample_pixel_xy"] == point["sample_pixel_xy"]
                and 0 <= x < image["width"] and 0 <= y < image["height"],
                "POINT admission sample binding differs")
            contains = bool(native[ordinal,y,x])
            require(admission["mask_contains_sample"] == admission["admitted"] == contains
                and admission["reason"] == (None if contains else "POINT_MASK_CONTRADICTION"),
                "POINT-mask admission does not match raw native pixels")
    return r, points, masks, geometry


def paired_metrics(rows, baseline_rows):
    require([r["image_id"] for r in rows] == [r["image_id"] for r in baseline_rows], "paired scoring order differs")
    paired = []
    for row, base in zip(rows,baseline_rows):
        old = [m for b in base["boxes"] for m in b["masks"]]
        new = [m for b in row["boxes"] for m in b["masks"]]
        admitted = [m for m in new if m["point_admission"]["admitted"]]
        values = dict(image_id=row["image_id"],camera_id=row["camera_id"],human_status=row["human_status"],
            source_point_inside_annotated_region=row["point_inside_annotated_region"],
            native_mask_denominator={"BOX_only":len(old),"POINT_BOX_raw":len(new),"POINT_admitted":len(admitted)},
            planned_native_slots=3,raw_mask_generation_completed=bool(new),
            baseline_candidate_count=sum(len(m["candidates"]) for m in old),
            raw_candidate_count=sum(len(m["candidates"]) for m in new),
            admitted_candidate_count=sum(len(m["candidates"]) for m in admitted),
            baseline_task_valid_count=sum(m["task_valid_candidate_count"] for m in old),
            raw_task_valid_count=sum(m["task_valid_candidate_count"] for m in new),
            admitted_task_valid_count=sum(m["task_valid_candidate_count"] for m in admitted),
            baseline_outside_count=sum(m["outside_region_candidate_count"] for m in old),
            raw_outside_count=sum(m["outside_region_candidate_count"] for m in new),
            admitted_outside_count=sum(m["outside_region_candidate_count"] for m in admitted),
            native_mask_contamination={"BOX_only":[m["mask_overlap"]["contamination"] for m in old],
                "POINT_BOX_raw":[m["mask_overlap"]["contamination"] for m in new],
                "POINT_admitted":[m["mask_overlap"]["contamination"] for m in admitted]},
            failure_categories=row["frame_categories"],evaluation_only=True,selected_mask=None)
        paired.append(values)
    summaries = {}
    for camera in ("agentview","robot0_eye_in_hand","total"):
        selected = [p for p in paired if camera == "total" or p["camera_id"] == camera]
        visible = [p for p in selected if p["human_status"] == "VISIBLE"]
        generated = [p for p in selected if p["raw_mask_generation_completed"]]
        summaries[camera] = dict(frame_denominator=len(selected),visible_frame_denominator=len(visible),
            point_inside_visible_region=sum(p["source_point_inside_annotated_region"] is True for p in visible),
            point_outside_visible_region=sum(p["source_point_inside_annotated_region"] is False for p in visible),
            point_unavailable_visible_region=sum(p["source_point_inside_annotated_region"] is None for p in visible),
            generated_frame_count=sum(p["raw_mask_generation_completed"] for p in selected),
            planned_mask_slots=3*len(selected),
            candidate_counts={key:sum(p[key] for p in selected) for key in
                ("baseline_candidate_count","raw_candidate_count","admitted_candidate_count",
                 "baseline_task_valid_count","raw_task_valid_count","admitted_task_valid_count",
                 "baseline_outside_count","raw_outside_count","admitted_outside_count")},
            task_valid_frames={condition:sum(p[key] > 0 for p in selected) for condition,key in
                (("BOX_only","baseline_task_valid_count"),("POINT_BOX_raw","raw_task_valid_count"),
                 ("POINT_admitted","admitted_task_valid_count"))},
            contamination={condition:_distribution([value for p in selected for value in p["native_mask_contamination"][condition]])
                for condition in ("BOX_only","POINT_BOX_raw","POINT_admitted")},
            matched_generated_subgroup=dict(frame_denominator=len(generated),
                candidate_counts={key:sum(p[key] for p in generated) for key in
                    ("baseline_candidate_count","raw_candidate_count","admitted_candidate_count",
                     "baseline_task_valid_count","raw_task_valid_count","admitted_task_valid_count",
                     "baseline_outside_count","raw_outside_count","admitted_outside_count")},
                contamination={condition:_distribution([value for p in generated for value in p["native_mask_contamination"][condition]])
                    for condition in ("BOX_only","POINT_BOX_raw","POINT_admitted")}),
            conditional_generation_note="Raw prompting contrast conditions on passed POINT preconditions; full-frame/slot failures retained separately. Admission filtering is not a model effect.")
    return paired,summaries


def score(root):
    root = Path(root)
    registration,points,masks,geometry = verified_generation(root)
    entry = registration["entry"]
    for path,digest in ((entry["annotation_path"],entry["annotation_sha256"]),
        (entry["annotation_seal_path"],entry["annotation_seal_sha256"]),
        (entry["rules_path"],entry["rules_sha256"]),
        (entry["annotation_packet_manifest_path"],entry["annotation_packet_manifest_sha256"])):
        require(sha(path) == digest,"frozen evaluator annotations/rules differ")
    # All POINT/SAM/geometry outputs authenticated before this label read.
    labels = read(entry["annotation_path"])
    manifest = read(entry["annotation_packet_manifest_path"])
    require(labels["rules_version"] == manifest["rules_version"] == "p1-rgb-annotation-rules/2"
        and labels["rules_sha256"] == entry["rules_sha256"] and labels["dataset_id"] == manifest["dataset_id"],
        "frozen annotation identity differs")
    by_label = {label["image_id"]:label for label in labels["annotations"]}
    require(len(by_label) == 50 and set(by_label) == {im["image_id"] for im in entry["ordered50_images"]},
            "annotation coverage differs")
    outputs = {(r["input_index"],r["box_index"]):(r,g) for r,g in zip(masks,geometry)}
    rows,slots = [],[]
    for i,input_row in enumerate(registration["inputs"]):
        image,point = input_row["image"],points[i]
        annotation = by_label[image["image_id"]]
        require(image_binding(annotation) == image_binding(image),"annotation image binding differs")
        truth = annotation["entities"]["drawer_front_pushable"]
        label,boxes,categories = polygon_mask(image,truth),[],set()
        for box_index,box in enumerate(input_row["ordered_boxes"]):
            native,geo = outputs[i,box_index]
            scored_masks = []
            if native["status"] == geo["status"] == "COMPLETE":
                with np.load(native["artifact_uri"],allow_pickle=False) as data:
                    for ordinal,mask in enumerate(data["masks"]):
                        scored = score_mask(image,truth,mask,geo["native_mask_estimates"][ordinal],
                            ordinal=ordinal,box=box,stage_ledger=geo["stage_ledger"][ordinal])
                        scored.update(geometry_s=geo["mask_geometry_s"][ordinal],
                                      point_admission=geo["mask_point_admission"][ordinal])
                        scored_masks.append(scored)
                        category = scored["evaluation_category"] if scored["point_admission"]["admitted"] else "POINT_MASK_CONTRADICTION"
                        slots.append(dict(image_id=image["image_id"],camera_id=image["camera_id"],
                            box_index=box_index,native_mask_ordinal=ordinal,generated=True,
                            geometry_evaluation="EVALUATED",raw_category=scored["evaluation_category"],
                            admitted_category=category,evaluation_only=True))
            else:
                reason = native.get("failure_stage",geo.get("failure_stage","INFERENCE_FAILURE"))
                categories.add(reason)
                for ordinal in range(3):
                    slots.append(dict(image_id=image["image_id"],camera_id=image["camera_id"],
                        box_index=box_index,native_mask_ordinal=ordinal,generated=False,
                        geometry_evaluation="NOT_EVALUATED",raw_category=reason,
                        admitted_category=reason,evaluation_only=True))
            boxes.append(dict(box_index=box_index,box_xyxy=box,box_overlap=box_metrics(box,image,label),
                inference_status=native["status"],geometry_status=geo["status"],
                predict_s=native.get("predict_s"),native_total_s=native["encode_s"]+native["predict_s"]
                if native["status"] == "COMPLETE" else None,masks=scored_masks))
        categories.update(m["evaluation_category"] for b in boxes for m in b["masks"])
        if truth["status"] != "VISIBLE":
            categories.add(truth["status"])
        point_failure = None
        if point["status"] != "COMPLETE":
            point_failure = "POINT_INFERENCE_FAILURE"
        elif not point["source_admitted"]:
            point_failure = point.get("reason") or "POINT_NOT_ADMITTED"
        if point_failure:
            categories.add(point_failure)
        rows.append(dict(image_id=image["image_id"],camera_id=image["camera_id"],init_index=image["init_index"],
            human_status=truth["status"],human_reason=truth["reason"],boxes=boxes,
            semantic_failure=not input_row["ordered_boxes"],frame_categories=sorted(categories),
            encode_s=outputs[i,0][0].get("encode_s") if boxes else None,
            task_valid_candidate_count=sum(m["task_valid_candidate_count"] for b in boxes for m in b["masks"]),
            point_status=point["status"],point_admitted=point["source_admitted"],point_failure=point_failure,
            point_inside_annotated_region=point_label_relation(point["point_xy"],truth),
            selected_mask=None,selected_candidate=None,evaluation_only=True))
    baseline_rows = read(Path(registration["baseline_root"])/"scoring/rows.json")
    paired,paired_summary = paired_metrics(rows,baseline_rows)
    slot_summary = {}
    for camera in ("agentview","robot0_eye_in_hand","total"):
        selected = [s for s in slots if camera == "total" or s["camera_id"] == camera]
        frames = [r for r in rows if camera == "total" or r["camera_id"] == camera]
        slot_summary[camera] = dict(frame_denominator=len(frames),planned_mask_slot_denominator=len(selected),
            generated_native_masks=sum(s["generated"] for s in selected),
            downstream_not_evaluated_slots=sum(s["geometry_evaluation"] == "NOT_EVALUATED" for s in selected),
            raw_slot_taxonomy=slot_taxonomy(s["raw_category"] for s in selected),
            admission_slot_taxonomy=slot_taxonomy(s["admitted_category"] for s in selected),
            point_status=dict(Counter(r["point_status"] for r in frames)),
            point_admission_failures=dict(Counter(r["point_failure"] for r in frames if r["point_failure"])),
            point_call_timing=_percentiles([p.get("inference_s") for p in points
                if camera == "total" or p["image"]["camera_id"] == camera]))
    out = root/"scoring"
    out.mkdir(exist_ok=False)
    write(out/"rows.json",rows)
    write(out/"potential-mask-slots.json",slots)
    write(out/"paired-rows.json",paired)
    summary = dict(schema="p1-identity-repair-scoring/1",by_camera=summarize(rows),
        planned_slot_summary=slot_summary,paired_by_camera=paired_summary,
        annotation_sha256=entry["annotation_sha256"],
        generation_seal_sha256={stage:sha(root/stage/"sealed.json") for stage in ("points","masks","geometry")},
        baseline_scoring_seal_sha256=sha(Path(registration["baseline_root"])/"scoring/sealed.json"),
        evaluation_only=True,development_only=True,independent_heldout=False,P1_acceptance=False,
        selected_mask=None,selected_candidate=None,continuous_end_to_end_hz_measured=False,
        admission_filter_is_model_gain=False,status="P2 remains blocked pending Formal-50 / temporal P1 gate")
    write(out/"summary.json",summary)
    seal(out)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    score(parser.parse_args().root)


if __name__ == "__main__":
    main()
