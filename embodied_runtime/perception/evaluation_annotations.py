"""Offline-only human annotation contracts. Never a policy observation source.

Identity and independence are explicit self-attestations, not verified human
identity. Incomplete, uncertain, or missing labels never become positive labels.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath

import numpy as np

from ..contracts import ProtocolError, content_hash, require


PACKET_SCHEMA = "p1-human-annotation-packet/2"
ANNOTATION_SCHEMA = "p1-human-annotations/2"
PREDICTION_SCHEMA = "p1-grounding-predictions/2"
RULES_VERSION = "p1-rgb-annotation-rules/2"
ENTITIES = ("drawer_front_pushable", "fixed_cabinet_reference")
STATUSES = ("VISIBLE", "UNKNOWN", "NOT_VISIBLE")
REFERENCE_TYPES = ("FRONT_FRAME", "FIXED_EDGE", "ADJACENT_FIXED_BODY")
BINDING_KEYS = ("image_id", "frame_id", "rgb_blob_sha256", "rgb_pixel_sha256", "png_sha256", "width", "height")
IMAGE_KEYS = {*BINDING_KEYS, "source_frame_id", "episode_id", "init_index", "camera_id", "image_path"}


def _keys(value, keys, name):
    require(isinstance(value, Mapping) and set(value) == set(keys), f"invalid {name} fields", "ANNOTATION_SCHEMA")


def _text(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"{name} is required", "ANNOTATION_SCHEMA")


def _hash(value, name):
    require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value), f"invalid {name}", "ANNOTATION_SCHEMA")


def packet_identity(manifest):
    return content_hash({key: value for key, value in manifest.items() if key != "dataset_id"})


def validate_packet_manifest(manifest, *, expected_count=50):
    _keys(manifest, {"schema", "dataset_id", "source_run_manifest_sha256", "selection_rule",
                     "expected_image_count", "images", "rules_version", "rules_sha256", "rules_path"}, "packet")
    require(manifest["schema"] == PACKET_SCHEMA, "packet version mismatch", "ANNOTATION_SCHEMA")
    require(manifest["rules_version"] == RULES_VERSION and manifest["rules_path"] == "annotation_rules.md",
            "frozen annotation rules version/path mismatch", "ANNOTATION_RULES")
    _hash(manifest["rules_sha256"], "rules hash")
    _hash(manifest["source_run_manifest_sha256"], "source manifest hash")
    require(manifest["dataset_id"] == packet_identity(manifest), "packet content hash mismatch", "ANNOTATION_BINDING")
    require(manifest["selection_rule"] == "first_bundle_each_camera_per_init_raw_rgb_only", "selection rule mismatch")
    require(type(manifest["expected_image_count"]) is int and manifest["expected_image_count"] == expected_count,
            "unexpected dataset size", "ANNOTATION_COVERAGE")
    require(isinstance(manifest["images"], list) and len(manifest["images"]) == expected_count,
            "incomplete packet", "ANNOTATION_COVERAGE")
    images, frames, content, selection = {}, set(), set(), set()
    for image in manifest["images"]:
        _keys(image, IMAGE_KEYS, "image")
        for key in ("image_id", "frame_id", "source_frame_id", "episode_id", "camera_id"):
            _text(image[key], key)
        for key in ("rgb_blob_sha256", "rgb_pixel_sha256", "png_sha256"):
            _hash(image[key], key)
        require(type(image["width"]) is int and type(image["height"]) is int and min(image["width"], image["height"]) > 0,
                "invalid image dimensions")
        require(type(image["init_index"]) is int and image["init_index"] >= 0, "invalid init index")
        path = PurePosixPath(image["image_path"])
        require(not path.is_absolute() and path.parts[:1] == ("images",) and len(path.parts) == 2 and path.suffix == ".png",
                "image must be a local raw PNG", "ANNOTATION_BINDING")
        require(image["image_id"] not in images and image["frame_id"] not in frames,
                "duplicate image/frame identity", "ANNOTATION_COVERAGE")
        require(image["rgb_pixel_sha256"] not in content, "duplicate RGB image in independent packet", "ANNOTATION_COVERAGE")
        pair = (image["init_index"], image["camera_id"])
        require(pair not in selection, "more than one frame selected per init/camera", "ANNOTATION_COVERAGE")
        images[image["image_id"]] = image
        frames.add(image["frame_id"])
        content.add(image["rgb_pixel_sha256"])
        selection.add(pair)
    if expected_count == 50:
        require(selection == {(init, camera) for init in range(25) for camera in ("agentview", "robot0_eye_in_hand")},
                "canonical packet requires init0..24 and both declared cameras", "ANNOTATION_COVERAGE")
    return images


def load_packet(directory, *, expected_count=50, verify_images=True):
    root = Path(directory).resolve()
    manifest = json.loads((root/"manifest.json").read_text())
    images = validate_packet_manifest(manifest, expected_count=expected_count)
    require(hashlib.sha256((root/manifest["rules_path"]).read_bytes()).hexdigest() == manifest["rules_sha256"],
            "frozen annotation rules changed", "ANNOTATION_RULES")
    if verify_images:
        from PIL import Image
        for entry in images.values():
            path = (root/entry["image_path"]).resolve()
            require(path.is_relative_to(root), "image path escapes packet", "ANNOTATION_BINDING")
            require(hashlib.sha256(path.read_bytes()).hexdigest() == entry["png_sha256"], "PNG hash mismatch", "ANNOTATION_BINDING")
            with Image.open(path) as image:
                require(image.mode == "RGB" and image.size == (entry["width"], entry["height"]), "PNG dimensions/mode mismatch")
                pixels = np.asarray(image)
                require(hashlib.sha256(pixels.tobytes()).hexdigest() == entry["rgb_pixel_sha256"], "decoded pixel hash mismatch", "ANNOTATION_BINDING")
    return manifest


def image_binding(image):
    return {key: image[key] for key in BINDING_KEYS}


def _point(point, width, height):
    require(isinstance(point, (tuple, list)) and len(point) == 2
            and all(type(v) in (int, float) and np.isfinite(v) for v in point), "point must be finite pixel XY", "ANNOTATION_POLYGON")
    require(0 <= point[0] <= width and 0 <= point[1] <= height, "point outside image", "ANNOTATION_POLYGON")
    return np.asarray(point, dtype=float)


def _cross(a, b, c):
    return float((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))


def _segments_intersect(a, b, c, d):
    if max(min(a[0], b[0]), min(c[0], d[0])) > min(max(a[0], b[0]), max(c[0], d[0])) + 1e-9:
        return False
    if max(min(a[1], b[1]), min(c[1], d[1])) > min(max(a[1], b[1]), max(c[1], d[1])) + 1e-9:
        return False
    values = (_cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b))
    return values[0]*values[1] <= 1e-12 and values[2]*values[3] <= 1e-12


def validate_polygons(polygons, width, height):
    require(isinstance(polygons, list), "polygons must be a list", "ANNOTATION_POLYGON")
    for polygon in polygons:
        require(isinstance(polygon, list) and 3 <= len(polygon) <= 4096, "polygon needs 3..4096 unclosed vertices", "ANNOTATION_POLYGON")
        vertices = np.array([_point(point, width, height) for point in polygon])
        next_vertices = np.roll(vertices, -1, axis=0)
        require(np.all(np.linalg.norm(next_vertices-vertices, axis=1) > 1e-9), "repeated polygon vertex", "ANNOTATION_POLYGON")
        area = abs(float(np.sum(vertices[:, 0]*next_vertices[:, 1]-next_vertices[:, 0]*vertices[:, 1])))/2
        require(area > 1e-9, "degenerate polygon", "ANNOTATION_POLYGON")
        n = len(vertices)
        for i in range(n):
            for j in range(i+1, n):
                if j == i+1 or (i == 0 and j == n-1):
                    continue
                require(not _segments_intersect(vertices[i], vertices[(i+1) % n], vertices[j], vertices[(j+1) % n]),
                        "self-intersecting polygon", "ANNOTATION_POLYGON")


def _validate_record(record, images, *, prediction=False):
    _keys(record, {*BINDING_KEYS, "entities"}, "image annotation")
    require(record["image_id"] in images, "unknown annotated image", "ANNOTATION_BINDING")
    image = images[record["image_id"]]
    require(image_binding(record) == image_binding(image), "image/frame/hash/dimensions differ from packet", "ANNOTATION_BINDING")
    _keys(record["entities"], ENTITIES, "entities")
    for name, entity in record["entities"].items():
        _keys(entity, {"status", "reason", "polygons", *( ("points",) if prediction else ()),
                      *(("reference_types",) if name == "fixed_cabinet_reference" else ())}, "entity")
        require(entity["status"] in STATUSES, "entity visibility must be explicit", "ANNOTATION_SCHEMA")
        _text(entity["reason"], "reason")
        validate_polygons(entity["polygons"], image["width"], image["height"])
        require(entity["status"] != "VISIBLE" or bool(entity["polygons"]), "visible region requires polygons", "ANNOTATION_POLYGON")
        require(entity["status"] != "NOT_VISIBLE" or not entity["polygons"], "NOT_VISIBLE cannot contain visible polygons", "ANNOTATION_POLYGON")
        if name == "fixed_cabinet_reference":
            kinds = entity["reference_types"]
            require(isinstance(kinds, list) and len(kinds) == len(entity["polygons"]),
                    "each fixed reference polygon needs an explicit type", "ANNOTATION_REFERENCE")
            allowed = (*REFERENCE_TYPES, "UNKNOWN") if prediction else (("UNKNOWN",) if entity["status"] == "UNKNOWN" else REFERENCE_TYPES)
            require(all(kind in allowed for kind in kinds), "fixed reference type conflicts with visibility/identity", "ANNOTATION_REFERENCE")
        if prediction:
            require(isinstance(entity["points"], list), "predicted points must be a list")
            for point in entity["points"]:
                _point(point, image["width"], image["height"])
    return image


def validate_annotations(annotations, manifest, *, require_complete=True, expected_count=50):
    images = validate_packet_manifest(manifest, expected_count=expected_count)
    # An affirmative checkbox cannot override a contradictory provenance
    # disclosure. Never normalize away AI exposure to admit a blind condition.
    if isinstance(annotations, Mapping) and isinstance(annotations.get("provenance"), Mapping):
        provenance = annotations["provenance"]
        require(provenance.get("prior_ai_exposure") is not True
                and provenance.get("eligible_for_human_blind_evaluation") is not False,
                "declared AI exposure or blind-evaluation ineligibility; preserve disclosure",
                "ANNOTATION_BLINDNESS_CONFLICT")
    _keys(annotations, {"schema", "dataset_id", "annotator_id", "annotator_role", "rules_version", "rules_sha256",
                       "attestations", "exported_at_utc", "annotations"}, "annotation export")
    require(annotations["schema"] == ANNOTATION_SCHEMA and annotations["dataset_id"] == manifest["dataset_id"],
            "annotation schema/dataset mismatch", "ANNOTATION_BINDING")
    require(annotations["rules_version"] == manifest["rules_version"] and annotations["rules_sha256"] == manifest["rules_sha256"],
            "annotations do not bind the frozen rules", "ANNOTATION_RULES")
    require(annotations["annotator_role"] == "project_primary_human", "this packet is for the primary human annotator", "ANNOTATOR_ATTESTATION")
    _text(annotations["annotator_id"], "human annotator identity")
    require(annotations["annotator_id"].strip().lower() not in {"agent", "assistant", "codex", "astra", "chatgpt", "qwen", "laya", "anonymous"},
            "distinct human annotator identity required", "ANNOTATOR_ATTESTATION")
    _keys(annotations["attestations"], {"is_human", "independent_of_model_outputs", "raw_rgb_only"}, "attestations")
    require(all(value is True for value in annotations["attestations"].values()), "explicit human/independence/RGB-only self-attestation required", "ANNOTATOR_ATTESTATION")
    try:
        timestamp = datetime.fromisoformat(annotations["exported_at_utc"].replace("Z", "+00:00"))
        require(timestamp.tzinfo is not None and timestamp.utcoffset().total_seconds() == 0, "export timestamp must be UTC")
    except (ValueError, AttributeError, TypeError) as exc:
        raise ProtocolError("ANNOTATION_SCHEMA", "invalid export timestamp") from exc
    require(isinstance(annotations["annotations"], list), "annotations must be a list")
    seen = set()
    counts = {entity: Counter() for entity in ENTITIES}
    for record in annotations["annotations"]:
        _validate_record(record, images)
        require(record["image_id"] not in seen, "duplicate annotation image", "ANNOTATION_COVERAGE")
        seen.add(record["image_id"])
        for name, entity in record["entities"].items():
            counts[name][entity["status"]] += 1
    missing = sorted(set(images)-seen)
    require(not require_complete or not missing, f"missing {len(missing)} image annotations", "ANNOTATION_COVERAGE")
    return {"dataset_id": manifest["dataset_id"], "annotator_id": annotations["annotator_id"],
            "annotator_role": annotations["annotator_role"], "third_party_review_claimed": False,
            "rules_version": annotations["rules_version"], "rules_sha256": annotations["rules_sha256"],
            "complete": not missing, "annotated_images": len(seen), "expected_images": len(images),
            "missing_image_ids": missing, "visibility_counts": {k: dict(v) for k, v in counts.items()},
            "human_identity_claim": "self_attested_not_independently_verified",
            "independence_claim": "self_attested_not_independently_verified", "evaluation_only": True}


def _inside(points, polygons):
    result = np.zeros(len(points), dtype=bool)
    x, y = points[:, 0], points[:, 1]
    for polygon in polygons:
        hit = np.zeros(len(points), dtype=bool)
        for a, b in zip(polygon, polygon[1:]+polygon[:1]):
            if a[1] == b[1]:
                continue
            crosses = (a[1] > y) != (b[1] > y)
            x_cross = (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]
            hit ^= crosses & (x < x_cross)
        result |= hit
    return result


def _boundary_distance(point, polygons):
    distance = float("inf")
    p = np.asarray(point, dtype=float)
    for polygon in polygons:
        for start, finish in zip(polygon, polygon[1:]+polygon[:1]):
            a, b = np.asarray(start), np.asarray(finish)
            delta = b-a
            fraction = np.clip((p-a) @ delta / (delta @ delta), 0, 1)
            distance = min(distance, float(np.linalg.norm(p-(a+fraction*delta))))
    return distance


def evaluate_grounding(predictions, annotations, manifest, *, expected_count=50):
    """Full-coverage offline IoU/point metrics; no labels enter runtime state."""
    annotation_summary = validate_annotations(annotations, manifest, expected_count=expected_count)
    images = validate_packet_manifest(manifest, expected_count=expected_count)
    _keys(predictions, {"schema", "dataset_id", "producer_id", "revision", "records"}, "prediction export")
    require(predictions["schema"] == PREDICTION_SCHEMA and predictions["dataset_id"] == manifest["dataset_id"], "prediction dataset mismatch")
    _text(predictions["producer_id"], "prediction producer")
    _text(predictions["revision"], "prediction revision")
    require(predictions["producer_id"].strip().casefold() != annotations["annotator_id"].strip().casefold(), "prediction and annotator identities must differ", "ANNOTATOR_ATTESTATION")
    require(isinstance(predictions["records"], list), "prediction records must be a list")
    by_image = {}
    for record in predictions["records"]:
        _validate_record(record, images, prediction=True)
        require(record["image_id"] not in by_image, "duplicate prediction", "ANNOTATION_COVERAGE")
        by_image[record["image_id"]] = record
    require(set(by_image) == set(images), "predictions must cover the complete packet", "ANNOTATION_COVERAGE")
    results = []
    for label in annotations["annotations"]:
        image = images[label["image_id"]]
        yy, xx = np.indices((image["height"], image["width"]))
        pixels = np.column_stack((xx.ravel()+.5, yy.ravel()+.5))
        for name in ENTITIES:
            truth = label["entities"][name]
            predicted = by_image[label["image_id"]]["entities"][name]
            iou = None
            point_metrics = []
            if truth["status"] == "VISIBLE":
                truth_mask = _inside(pixels, truth["polygons"])
                pred_mask = _inside(pixels, predicted["polygons"])
                union = np.count_nonzero(truth_mask | pred_mask)
                iou = float(np.count_nonzero(truth_mask & pred_mask)/union) if union else None
                for point in predicted["points"]:
                    distance = _boundary_distance(point, truth["polygons"])
                    inside = bool(_inside(np.asarray([point]), truth["polygons"])[0]) or distance <= 1e-9
                    point_metrics.append({"point_px": point, "inside_annotated_region": inside,
                                          "boundary_distance_px": distance, "signed_interior_margin_px": distance if inside else -distance})
            results.append({"image_id": label["image_id"], "entity": name,
                            "annotated_status": truth["status"], "predicted_status": predicted["status"],
                            "status_match": None if truth["status"] == "UNKNOWN" else truth["status"] == predicted["status"],
                            "annotated_reference_types": truth.get("reference_types"),
                            "predicted_reference_types": predicted.get("reference_types"),
                            "polygon_iou_on_visible_label": iou,
                            "predicted_point_count": len(predicted["points"]), "point_metrics": point_metrics})
    summary = {}
    for name in ENTITIES:
        rows = [r for r in results if r["entity"] == name]
        defined = [r for r in rows if r["status_match"] is not None]
        ious = [r["polygon_iou_on_visible_label"] for r in rows if r["polygon_iou_on_visible_label"] is not None]
        summary[name] = {
            "known_label_count": len(defined),
            "status_accuracy_on_known_labels": sum(r["status_match"] for r in defined)/len(defined) if defined else None,
            "visible_iou_count": len(ious), "mean_visible_polygon_iou": float(np.mean(ious)) if ious else None,
            "unknown_labels_excluded": sum(r["annotated_status"] == "UNKNOWN" for r in rows),
        }
    return {"schema": "p1-human-grounding-evaluation/2", "dataset_id": manifest["dataset_id"],
            "annotation_export_sha256": content_hash(annotations), "prediction_export_sha256": content_hash(predictions),
            "annotation_summary": annotation_summary, "prediction_producer": predictions["producer_id"],
            "prediction_revision": predictions["revision"], "evaluation_only": True,
            "labels_prove_contact_safety": False, "labels_prove_static_reference": False,
            "summary": summary, "records": results}
