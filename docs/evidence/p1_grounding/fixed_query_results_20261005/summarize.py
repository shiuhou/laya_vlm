"""Summarize sealed evaluation without modifying its records or thresholds."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    root = Path("runs/p1/corrected-v2-fixed-query-evaluation-20261005")
    assert (root / "completed.json").exists() and not (root / "failure.json").exists()
    evaluation = json.loads((root / "human-evaluation.json").read_text())
    predictions = [json.loads(p.read_text()) for p in sorted(root.glob("call-*/prediction.json"))]
    upper = json.loads((root / "annotation-conditioned-upper-bound.json").read_text())
    coverage = json.loads((root / "coverage-contamination.json").read_text())
    latencies = [json.loads(p.read_text())["inference_s"] for p in root.glob("call-*/raw-output.json")]
    audits = [p["generation_audit"] for p in predictions]
    result = {
        "source_run": str(root), "evaluation_only": True, "model_calls": len(predictions),
        "all_generation_eos_complete": all(a["complete_generation"] and a["terminal_eos_observed"] for a in audits),
        "truncated_calls": sum(a["length_limit_reached"] for a in audits),
        "input_tokens_range": [min(a["input_token_count"] for a in audits), max(a["input_token_count"] for a in audits)],
        "output_tokens_range": [min(a["actual_generated_token_count"] for a in audits), max(a["actual_generated_token_count"] for a in audits)],
        "inference_seconds": {"p50": float(np.percentile(latencies, 50)), "p95": float(np.percentile(latencies, 95)), "total": sum(latencies)},
        "runtime_actions": 0, "annotator_independence_source": "project-user correction, not independently authenticated",
        "frozen_evaluator_commit": "ea4dd51494d19d351def97488d01e1e194d045a9",
        "human_evaluation_summary": evaluation["summary"], "by_entity_camera": {},
        "interpretation_limits": [
            "UNKNOWN annotations are excluded, never negative labels",
            "candidate outside conservative annotation is unsupported, not proof every outside pixel is wrong",
            "fixed query asks FRONT_FRAME; visible reference labels are ADJACENT_FIXED_BODY",
            "all reference polygon sets identical; 25 inits do not imply 25 cabinet configurations",
            "geometry VALID is not semantic identity, safety, calibrated uncertainty or fixedness",
            "human-mask intervention is evaluator-only, not an executable ROI or tracker seed",
        ],
    }
    for entity in evaluation["summary"]:
        for camera in ("agentview", "robot0_eye_in_hand"):
            rows = [p for p in predictions if p["entity"] == entity and camera in p["image_id"]]
            labels = [r for r in evaluation["records"] if r["entity"] == entity and camera in r["image_id"]]
            patches = [g["patch"] for r in rows for g in r["geometry"] if g["patch"] is not None]
            points = [m for r in labels for m in r["point_metrics"]]
            masks = [r["evidence"] for r in upper if r["entity"] == entity and camera in r["image_id"]]
            overlaps = [b for r in coverage if r["entity"] == entity and camera in r["image_id"] for b in r["boxes"] if b["label_status"] == "VISIBLE"]
            result["by_entity_camera"][f"{entity}/{camera}"] = {
                "annotation_statuses": dict(Counter(r["annotated_status"] for r in labels)),
                "parsed_responses": dict(Counter(r["parsed"]["status"] for r in rows)),
                "geometry_statuses": dict(Counter(p["geometry_status"] for p in patches)),
                "geometry_reasons": dict(Counter(reason for p in patches for reason in p["reason_codes"])),
                "raw_candidate_count": sum(len(p["candidates"]) for p in patches),
                "candidate_points_evaluable": len(points),
                "candidate_points_inside_annotation": sum(p["inside_annotated_region"] for p in points),
                "median_bbox_contamination": float(np.median([b["bbox_contamination"] for b in overlaps])) if overlaps else None,
                "median_annotation_coverage": float(np.median([b["annotated_pixel_coverage"] for b in overlaps])) if overlaps else None,
                "human_mask_geometry_statuses": dict(Counter(m["status"] for m in masks)),
                "human_mask_reasons": dict(Counter(reason for m in masks for reason in (m.get("patch") or {}).get("reason_codes", []))),
                "human_mask_candidate_count": sum(len((m.get("patch") or {}).get("candidates", [])) for m in masks),
            }
    files = [p for p in root.rglob("*.json") if p.is_file()]
    result["source_file_sha256"] = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    output = Path("docs/evidence/p1_grounding/fixed_query_results_20261005/summary.json")
    with output.open("x") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
