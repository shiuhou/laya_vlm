"""Sensor-only generation, sealed BEFORE separate immutable-label evaluation.

No model inference or simulator execution. Legacy corrected-v2 annotation is
validated against its historical seals, never upgraded to today's v3 contract.
Polygon overlap is evaluator-only and never assigns a target/reference identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from ..contracts import content_hash, require
from ..perception.evaluation_annotations import ENTITIES, _inside, image_binding
from ..perception.recording import project_base_points
from ..perception.reference_candidates import enumerate_reference_candidates
from .p1_semantic_grounding import QUERIES, _sensor_frames, _write, frozen_geometry
from .records import code_identity


def _read(path):
    return json.loads(Path(path).read_text())


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate(source, predictions, packet, output, *, geometry_path="configs/p1_geometry.json"):
    """This API has no annotation input; persist every hypothesis before scoring."""
    prediction_root, packet_root, source_root = map(Path, (predictions, packet, source))
    registration = _read(prediction_root / "preregistration.json")
    manifest = _read(packet_root / "manifest.json")
    config = frozen_geometry(geometry_path)
    require(_sha(packet_root / "manifest.json") == registration["packet_manifest_sha256"],
            "frozen packet changed", "CONDITION_CHANGED")
    require(manifest["rules_version"] == "p1-rgb-annotation-rules/2"
            and manifest["rules_sha256"] == registration["annotation_rules_sha256"]
            and _sha(packet_root / manifest["rules_path"]) == manifest["rules_sha256"],
            "retain frozen v2 rules", "CONDITION_CHANGED")
    require(_sha(source_root / "manifest.json") == registration["source"]["manifest_sha256"],
            "recorded source manifest changed", "CONDITION_CHANGED")
    for name, digest in registration["source"]["recording_metadata_sha256"].items():
        require(_sha(source_root / name) == digest, "recording metadata changed", "CONDITION_CHANGED")
    require(registration["queries"] == QUERIES and len(manifest["images"]) == 50,
            "frozen query/image condition changed", "CONDITION_CHANGED")
    calls = [_read(prediction_root / f"call-{i:03d}" / "prediction.json") for i in range(100)]
    prediction_seal = _read(prediction_root / "predictions-sealed.json")
    require(prediction_seal["model_calls"] == 100
            and content_hash(calls) == prediction_seal["predictions_sha256"],
            "ordered100 predictions differ from seal", "CONDITION_CHANGED")
    expected = [(image["image_id"], entity) for image in manifest["images"] for entity in ENTITIES]
    require([(call["image_id"], call["entity"]) for call in calls] == expected,
            "prediction canonical order differs", "CONDITION_CHANGED")
    require(all(call["query"] == QUERIES[call["entity"]] for call in calls), "prediction query changed")
    relocated = {**registration, "source": {**registration["source"], "path": str(source_root.resolve())}}
    frames = _sensor_frames(relocated, manifest)
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    _write(root / "packet-manifest.json", manifest)
    # Historical hashes bind later scorer input, without exposing polygon values.
    _write(root / "annotation-expected-seal.json", _read(prediction_root / "gate.json"))
    inputs = dict(code=code_identity(), source_path=str(source_root.resolve()),
                  source_manifest_sha256=_sha(source_root / "manifest.json"),
                  packet_manifest_sha256=_sha(packet_root / "manifest.json"),
                  predictions_sha256=prediction_seal["predictions_sha256"],
                  geometry_sha256=content_hash(config.to_dict()), query=QUERIES,
                  evaluation_labels_consumed=False, model_calls=0, runtime_actions=0)
    _write(root / "condition.json", inputs)
    for index, image in enumerate(manifest["images"]):
        view, _ = frames[image["frame_id"]]
        rows = []
        for entity in ENTITIES:
            call = calls[index * 2 + ENTITIES.index(entity)]
            require(call["frame_id"] == image["frame_id"]
                    and call["rgb_pixel_sha256"] == image["rgb_pixel_sha256"], "prediction RGB binding changed")
            inventories = []
            if call["structurally_admitted"]:
                for box_index, roi in enumerate(call["ordered_boxes"]):
                    inventories.append(dict(box_index=box_index, roi_xyxy=roi,
                        evidence=enumerate_reference_candidates(view, roi, config=config, seed=0)))
            rows.append(dict(entity=entity, structurally_admitted=call["structurally_admitted"],
                             parsed_status=call["parsed"]["status"], ordered_boxes=call["ordered_boxes"],
                             original_geometry=call["geometry"], roi_inventories=inventories,
                             selected_surface_id=None, semantic_identity="UNKNOWN"))
        scene = enumerate_reference_candidates(view, [0, 0, image["width"], image["height"]],
                                               config=config, seed=0)
        _write(root / f"frame-{index:03d}.json", dict(image=image, entities=rows, scene_context=scene,
                                                     evaluation_labels_consumed=False, for_execution=False))
    files = {str(path.relative_to(root)): _sha(path) for path in sorted(root.glob("*.json"))}
    _write(root / "generation-sealed.json", dict(schema="p1-observability-generation/1", files=files,
                seal_sha256=content_hash(files), evaluation_labels_consumed=False,
                frame_count=50, model_calls=0, runtime_actions=0))
    return root


def _support_metrics(geometry, label, shape):
    mask = np.zeros(shape, dtype=bool)
    for row, left, right in geometry["support_row_spans"]:
        require(0 <= row < shape[0] and 0 <= left < right <= shape[1], "support outside image")
        mask[row, left:right] = True
    overlap = int((mask & label).sum()) if label is not None else None
    return dict(support_pixel_count=int(mask.sum()), annotated_overlap_pixels=overlap,
                support_purity=overlap / int(mask.sum()) if label is not None and mask.any() else None,
                support_contamination=1 - overlap / int(mask.sum()) if label is not None and mask.any() else None,
                annotated_coverage=overlap / int(label.sum()) if label is not None and label.any() else None,
                evaluation_only=True)


def _score_image(record, annotation):
    image = record["image"]
    shape = image["height"], image["width"]
    require(image_binding(annotation) == image_binding(image), "label source changed", "ANNOTATION_BINDING")
    yy, xx = np.indices(shape)
    pixels = np.column_stack((xx.ravel() + .5, yy.ravel() + .5))
    result = []
    for entity in record["entities"]:
        truth = annotation["entities"][entity["entity"]]
        visible = truth["status"] == "VISIBLE"
        label = _inside(pixels, truth["polygons"]).reshape(shape) if visible else None
        box_rows, support_rows, points, patch_diagnostics, reasons = [], [], [], [], Counter()
        if not entity["structurally_admitted"]:
            reasons["SEMANTIC_RESPONSE_NOT_ADMITTED"] += 1
        for inventory in entity["roi_inventories"]:
            roi = inventory["roi_xyxy"]
            box_mask = ((xx + .5 >= roi[0]) & (xx + .5 < roi[2])
                        & (yy + .5 >= roi[1]) & (yy + .5 < roi[3]))
            overlap = int((box_mask & label).sum()) if visible else None
            box_rows.append(dict(box_index=inventory["box_index"],
                annotated_coverage=overlap / int(label.sum()) if visible and label.any() else None,
                roi_contamination=1 - overlap / int(box_mask.sum()) if visible and box_mask.any() else None))
            for surface in inventory["evidence"]["inventory"]["surfaces"]:
                support_rows.append(dict(box_index=inventory["box_index"], surface_id=surface["surface_id"],
                    plane_valid=surface["plane_valid"], **_support_metrics(surface, label, shape)))
        for box in entity["original_geometry"]:
            patch = box["patch"]
            if patch is None:
                reasons[box["structural_reason"] or "NO_ORIGINAL_PATCH"] += 1
                continue
            reasons.update(patch["reason_codes"])
            patch_diagnostics.append(dict(box_index=box["box_index"], geometry_status=patch["geometry_status"],
                                          reason_codes=patch["reason_codes"], metrics=patch["metrics"]))
            source = record["scene_context"]["source"]
            for candidate in patch["candidates"]:
                uv = project_base_points([candidate["position_base_m"]], source["intrinsics_K"],
                                         source["T_base_camera"])[0]
                finite = bool(np.isfinite(uv).all())
                inside = bool(_inside(np.asarray([uv]), truth["polygons"])[0]) if visible and finite else None
                points.append(dict(point_id=candidate["point_id"], image_xy=uv.tolist() if finite else None,
                    inside_annotated_region=inside, original_geometry_status=patch["geometry_status"],
                    polygon_evaluation=("ANNOTATED_REGION_SUPPORT" if inside is True else
                        "OUTSIDE_ANNOTATED_REGION_IDENTITY_UNCONFIRMED" if inside is False else "UNKNOWN"),
                    usable_status=candidate["usable_status"],
                    reason_codes=candidate["reason_codes"], evaluation_only=True))
        scene_supports = [dict(surface_id=s["surface_id"], plane_valid=s["plane_valid"],
                               **_support_metrics(s, label, shape))
                          for s in record["scene_context"]["inventory"]["surfaces"]]
        result.append(dict(entity=entity["entity"], label_status=truth["status"], parsed_status=entity["parsed_status"],
            label_reason=truth["reason"], box_metrics=box_rows, support_metrics=support_rows,
            scene_context_support_metrics=scene_supports, original_candidate_metrics=points,
            original_patch_diagnostics=patch_diagnostics, geometry_rejections=dict(sorted(reasons.items())),
            evaluator_only_support_exists=(any(s["plane_valid"] and s["annotated_overlap_pixels"] > 0
                                               for s in support_rows) if visible else None),
            semantic_identity="UNKNOWN", fixedness="UNKNOWN", reference_status="REFERENCE_UNKNOWN",
            evaluation_only=True))
    return dict(image_id=image["image_id"], init_index=image["init_index"], camera_id=image["camera_id"], entities=result)


def score(generated, annotations, output):
    """Verify complete sensor-only seals BEFORE loading immutable human labels."""
    root = Path(generated)
    seal = _read(root / "generation-sealed.json")
    require(seal["frame_count"] == 50 and seal["evaluation_labels_consumed"] is False
            and content_hash(seal["files"]) == seal["seal_sha256"], "invalid generation seal", "CONDITION_CHANGED")
    require({f"frame-{i:03d}.json" for i in range(50)} <= set(seal["files"]),
            "frame set not sealed", "CONDITION_CHANGED")
    for name, digest in seal["files"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root.resolve()) and _sha(path) == digest,
                "generation file changed", "CONDITION_CHANGED")
    expected = _read(root / "annotation-expected-seal.json")
    require(_sha(annotations) == expected["annotation_sha256"], "immutable corrected-v2 annotation changed",
            "ANNOTATION_BINDING")
    labels = _read(annotations)
    manifest = _read(root / "packet-manifest.json")
    require(content_hash(labels) == expected["annotation_content_sha256"]
            and labels["rules_version"] == manifest["rules_version"] == "p1-rgb-annotation-rules/2"
            and labels["rules_sha256"] == manifest["rules_sha256"]
            and labels["dataset_id"] == manifest["dataset_id"], "v2 label identity differs", "ANNOTATION_BINDING")
    by_label = {label["image_id"]: label for label in labels["annotations"]}
    require(len(by_label) == 50 and set(by_label) == {im["image_id"] for im in manifest["images"]}, "label coverage differs")
    rows = [_score_image(_read(root / f"frame-{i:03d}.json"), by_label[image["image_id"]])
            for i, image in enumerate(manifest["images"])]
    counts, rejections = Counter(), Counter()
    drawer_original_gate_supported_inits = set()
    for row in rows:
        for entity in row["entities"]:
            prefix = entity["entity"] + "/" + row["camera_id"]
            counts[prefix + "/label_" + entity["label_status"]] += 1
            if entity["label_status"] == "VISIBLE":
                counts[prefix + "/evaluator_support_exists"] += int(entity["evaluator_only_support_exists"])
                counts[prefix + "/original_candidate_inside"] += int(any(
                    p["inside_annotated_region"] is True for p in entity["original_candidate_metrics"]))
                if entity["entity"] == "drawer_front_pushable" and any(
                        p["inside_annotated_region"] is True and p["original_geometry_status"] == "VALID"
                        for p in entity["original_candidate_metrics"]):
                    drawer_original_gate_supported_inits.add(row["init_index"])
            rejections.update({prefix + "/" + k: v for k, v in entity["geometry_rejections"].items()})
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    _write(out / "per-frame-evaluation.json", rows)
    summary = dict(schema="p1-observability-offline-evaluation/1", counts=dict(sorted(counts.items())),
                   geometry_rejections=dict(sorted(rejections.items())), frame_count=50,
                   annotation_rules_version=labels["rules_version"], generation_seal_sha256=_sha(root / "generation-sealed.json"),
                   annotation_sha256=_sha(annotations), evaluation_only=True, semantic_identity_admitted=False,
                   drawer_original_gate_annotated_tool_interior_inits=sorted(drawer_original_gate_supported_inits),
                   drawer_original_gate_annotated_tool_interior_init_count=len(drawer_original_gate_supported_inits),
                   engineering_static_target_20_of_25_met=len(drawer_original_gate_supported_inits) >= 20,
                   reference_status="REFERENCE_UNKNOWN", temporal_tracking_tested=False,
                   warning="Polygon overlap measures support existence, never policy identity or fixedness; outside is unconfirmed, not proven wrong identity.")
    _write(out / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("generate")
    for name in ("source", "predictions", "packet", "output"):
        create.add_argument("--" + name, required=True)
    evaluate = commands.add_parser("score")
    for name in ("generated", "annotations", "output"):
        evaluate.add_argument("--" + name, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    generate(**args) if command == "generate" else score(**args)


if __name__ == "__main__":
    main()
