"""Offline independent review; no model, simulator, or runtime execution.

Run from repository root with .venv-p1/bin/python and this file's path.
Outputs are exclusive-create. Original sealed experiment files are read only.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from embodied_runtime.contracts import content_hash  # noqa: E402
from embodied_runtime.experiments.p1_semantic_grounding import (  # noqa: E402
    _sensor_frames, annotation_upper_bound, frozen_geometry,
)
from embodied_runtime.perception.evaluation_annotations import _inside  # noqa: E402
from embodied_runtime.perception.recording import project_base_points  # noqa: E402

RUN = ROOT/"runs/p1/corrected-v2-fixed-query-evaluation-20261005"
PACKET = ROOT/"runs/p1/human-annotation-packet-v2-20261005"
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def project(patch, view):
    candidates = patch["candidates"] if patch is not None else []
    return project_base_points([p["position_base_m"] for p in candidates], view["intrinsics_K"],
                               view["T_base_camera"]) if candidates else np.empty((0, 2))


def point_metrics(points, truth):
    if truth["status"] != "VISIBLE":
        return dict(count=len(points), inside=None, outside=None, boundary_min_px=None)
    inside = _inside(points, truth["polygons"])
    distances = np.full(len(points), np.inf)
    for polygon in truth["polygons"]:
        for a, b in zip(polygon, polygon[1:]+polygon[:1]):
            a, b = np.asarray(a), np.asarray(b)
            delta = b-a
            fraction = np.clip((points-a) @ delta / (delta @ delta), 0, 1)
            distances = np.minimum(distances, np.linalg.norm(points-(a+fraction[:, None]*delta), axis=1))
    inside |= distances <= 1e-9
    return dict(count=len(points), inside=int(inside.sum()), outside=int((~inside).sum()),
                boundary_min_px=float(distances.min()) if len(points) else None)


def polygons(draw, truth):
    for polygon in truth["polygons"]:
        points = [tuple(p) for p in polygon]
        draw.line(points+[points[0]], fill="orange", width=2)


def main():
    manifest = read(PACKET/"manifest.json")
    registration = read(RUN/"preregistration.json")
    frames = _sensor_frames(registration, manifest)
    annotations = read(RUN/"annotations-evaluation-input.json")
    labels = {r["image_id"]: r["entities"] for r in annotations["annotations"]}
    calls = [read(p) for p in sorted(RUN.glob("call-*/prediction.json"))]
    seal = read(RUN/"predictions-sealed.json")
    assert content_hash(calls) == seal["predictions_sha256"] and len(calls) == 100
    assert all(p["generation_audit"]["terminal_eos_observed"] and
               not p["generation_audit"]["length_limit_reached"] for p in calls)
    upper = {(r["image_id"], r["entity"]): r["evidence"] for r in read(RUN/"annotation-conditioned-upper-bound.json")}
    existing = {(r["image_id"], r["entity"]): r for r in read(RUN/"human-evaluation.json")["records"]}
    stats, rows = defaultdict(Counter), []
    pixels_by_call, upper_pixels_by_call = {}, {}
    for number, prediction in enumerate(calls):
        key = prediction["image_id"], prediction["entity"]
        view, _ = frames[key[0]]
        truth = labels[key[0]][key[1]]
        points = np.concatenate([project(box["patch"], view) for box in prediction["geometry"]])
        upper_points = project(upper[key].get("patch"), view)
        metrics, upper_metrics = point_metrics(points, truth), point_metrics(upper_points, truth)
        if truth["status"] == "VISIBLE":
            assert metrics["inside"] == sum(p["inside_annotated_region"] for p in existing[key]["point_metrics"])
        pixels_by_call[number], upper_pixels_by_call[number] = points, upper_points
        camera = manifest["images"][number//2]["camera_id"]
        group = f"{key[1]}:{camera}"
        stats[group]["views"] += 1
        stats[group]["model_candidates"] += len(points)
        stats[group]["mask_candidates"] += len(upper_points)
        for status in [b["patch"]["geometry_status"] for b in prediction["geometry"] if b["patch"]]:
            stats[group]["model_geometry_"+status] += 1
        stats[group]["mask_geometry_"+upper[key]["status"]] += 1
        if truth["status"] == "VISIBLE":
            stats[group]["model_points_inside_labels"] += metrics["inside"]
            stats[group]["model_points_outside_labels"] += metrics["outside"]
            stats[group]["mask_points_inside_labels"] += upper_metrics["inside"]
            stats[group]["mask_points_outside_labels"] += upper_metrics["outside"]
        rows.append(dict(call=f"call-{number:03d}", image_id=key[0], entity=key[1], camera=camera,
                         label_status=truth["status"], boxes=prediction["ordered_boxes"],
                         geometry_statuses=[b["patch"]["geometry_status"] for b in prediction["geometry"]],
                         semantic_candidate_projection=metrics, mask_geometry_status=upper[key]["status"],
                         mask_candidate_projection=upper_metrics))

    # Preregistered model condition is unchanged. This additional experiment is
    # post-registration, evaluator-only, and explicitly uses human polygons.
    config = frozen_geometry(ROOT/"configs/p1_geometry.json")
    split_records = []
    for image in manifest["images"]:
        truth = labels[image["image_id"]]["fixed_cabinet_reference"]
        if truth["status"] != "VISIBLE":
            continue
        view, proprio = frames[image["frame_id"]]
        for index, polygon in enumerate(truth["polygons"]):
            single = {**truth, "polygons": [polygon], "reference_types": [truth["reference_types"][index]]}
            result = annotation_upper_bound(view, proprio, f"fixed_cabinet_reference/polygon-{index}", single, config)
            points = project(result.get("patch"), view)
            split_records.append(dict(image_id=image["image_id"], polygon_index=index,
                                      reference_type=single["reference_types"][0], evidence=result,
                                      projection=point_metrics(points, single)))
    split_summary = dict(Counter(row["evidence"]["status"] for row in split_records))
    write(OUT/"independent-reference-polygon-diagnostic.json", {
        "condition": "post_registration_evaluator_only_human_reference_polygons_separately",
        "purpose": "Distinguish union-of-two-surfaces ambiguity from lack of usable local surface geometry.",
        "changes_original_condition": False, "for_execution": False,
        "source_upper_bound_sha256": sha(RUN/"annotation-conditioned-upper-bound.json"),
        "geometry_code_sha256": sha(ROOT/"embodied_runtime/perception/rgbd_geometry.py"),
        "geometry_config_sha256": sha(ROOT/"configs/p1_geometry.json"),
        "summary": split_summary, "records": split_records})

    selected = [0, 1, 2, 6, 10, 14, 98]
    sheet = Image.new("RGB", (384*4, 294*len(selected)), "white")
    sheet_draw = ImageDraw.Draw(sheet)
    for row_index, number in enumerate(selected):
        p = calls[number]
        view, _ = frames[p["image_id"]]
        truth = labels[p["image_id"]][p["entity"]]
        y = row_index*294
        for column in range(4):
            im = Image.fromarray(view["rgb"]).convert("RGB")
            draw = ImageDraw.Draw(im)
            if column:
                polygons(draw, truth)
            if column == 1:
                for box in p["ordered_boxes"]:
                    draw.rectangle(box, outline="magenta", width=2)
            if column in (2, 3):
                points = pixels_by_call[number] if column == 2 else upper_pixels_by_call[number]
                for x, v in points:
                    draw.ellipse((x-1, v-1, x+1, v+1), fill="cyan")
                polygons(draw, truth)
            sheet.paste(im, (column*384, y))
            title = ("Raw RGB", "Orange: label; magenta: model bbox", "All model geometry points (cyan)", "Human-mask geometry points (cyan)")[column]
            sheet_draw.text((column*384+4, y+258), title, fill="black")
        sheet_draw.text((4, y+277), f"call-{number:03d} {p['image_id']} {p['entity']} label={truth['status']} geometry={rows[number]['geometry_statuses']}", fill="black")
    with (OUT/"independent-contact-sheet.jpg").open("xb") as stream:
        sheet.save(stream, format="JPEG", quality=94)
    write(OUT/"independent-review.json", {
        "schema": "p1-independent-offline-review/1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": "Codex p0_boundary independent artifact audit; not a human annotator",
        "run": str(RUN.relative_to(ROOT)), "runtime_actions": 0, "new_model_calls": 0,
        "predictions_seal_matches": True, "point_metric_recomputation_matches": True,
        "all_100_single_box": all(p["parsed"]["status"] == "single_box" for p in calls),
        "all_100_eos_without_length_limit": True,
        "source_sha256": {name: sha(RUN/name) for name in ["predictions-sealed.json", "human-evaluation.json", "annotation-conditioned-upper-bound.json", "annotations-evaluation-input.json", "preregistration.json"]},
        "script_sha256": sha(Path(__file__)), "summary": dict(stats), "records": rows,
        "contact_sheet_calls": selected, "contact_sheet_sha256": sha(OUT/"independent-contact-sheet.jpg"),
        "postregistration_reference_split_summary": split_summary,
        "limitations": ["Labels are conservative visible subsets; outside polygon is not proof of semantic invalidity.",
                        "Fixed query asks for front frame; visible labels are ADJACENT_FIXED_BODY top/side surfaces.",
                        "Zero images have both entities marked visible; views do not establish temporal fixedness.",
                        "All 25 agentview reference polygon sets are identical; limited cabinet/view diversity.",
                        "Annotation independence is project-user-reported with a preserved metadata correction, not independently verified.",
                        "No candidate is certified reachable, collision-safe, interaction-valid, or executable by this review."]})
    print(json.dumps({"summary": dict(stats), "reference_split": split_summary}, indent=2))


if __name__ == "__main__":
    main()
