"""Normalize serialization only, retaining the original v2 annotation chronology.

Run from the main repository using Python; validate/run subsequently in the
unmodified ea4dd51494d19d351def97488d01e1e194d045a9 evaluator worktree.
This is an evidence-specific transformation, not an annotation validator bypass.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    evidence = Path("docs/evidence/p1_grounding")
    correction = evidence / "annotation_metadata_correction_20261005"
    original_path = evidence / "annotation_receipt_20261005/annotations.received.json"
    corrected_path = correction / "annotations.metadata-corrected.json"
    receipt = json.loads((correction / "correction-receipt.json").read_text())
    original = json.loads(original_path.read_bytes())
    corrected = json.loads(corrected_path.read_bytes())
    assert sha(original_path) == receipt["original_sha256"]
    assert sha(corrected_path) == receipt["corrected_sha256"]
    assert receipt["new_annotation_required"] is False
    assert corrected["annotations"] == original["annotations"]
    assert corrected["provenance"]["prior_ai_exposure"] is False
    assert corrected["provenance"]["eligible_for_human_blind_evaluation"] is True
    assert {k: v for k, v in original.items() if k != "provenance"} == {
        k: v for k, v in corrected.items() if k != "provenance"
    }
    packet = Path("runs/p1/human-annotation-packet-v2-20261005")
    manifest = json.loads((packet / "manifest.json").read_text())
    images = {r["image_id"]: r for r in manifest["images"]}
    bindings = ("image_id", "frame_id", "rgb_blob_sha256", "rgb_pixel_sha256", "png_sha256", "width", "height")
    normalized = {k: v for k, v in corrected.items() if k != "provenance"}
    normalized["annotations"] = []
    for record in corrected["annotations"]:
        source = images[record["image_id"]]
        assert {k: v for k, v in record.items() if k != "entities"} == source
        normalized["annotations"].append({k: record[k] for k in (*bindings, "entities")})
    assert normalized["schema"] == "p1-human-annotations/2"
    assert normalized["dataset_id"] == manifest["dataset_id"]
    assert normalized["rules_sha256"] == manifest["rules_sha256"]
    assert normalized["exported_at_utc"] == original["exported_at_utc"]
    registration_path = Path("runs/p1/grounding-preregistration-20261005.json")
    registration = json.loads(registration_path.read_text())
    assert datetime.fromisoformat(registration["created_at_utc"]) < datetime.fromisoformat(normalized["exported_at_utc"])
    out = evidence / "corrected_v2_seal_20261005"
    annotation_path = out / "annotations.corrected-v2.complete.json"
    write_new(annotation_path, normalized)
    write_new(out / "seal.json", {
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "original_sha256": sha(original_path), "corrected_receipt_sha256": sha(correction / "correction-receipt.json"),
        "normalized_sha256": sha(annotation_path),
        "original_exported_at_utc": original["exported_at_utc"],
        "original_registration_created_at_utc": registration["created_at_utc"],
        "registration_sha256": registration["registration_sha256"],
        "annotator_source": "independent human never exposed to AI draft, as reported by project user",
        "identity_independently_verified": False,
        "legacy_identity_fields": "project-user/project_primary_human retained as original serialized aliases; not evidence of actual annotator identity",
        "normalization": "provenance retained in separate correction receipt; extra image metadata removed after exact manifest equality check",
        "regions_statuses_reasons_types_changed": False, "original_export_timestamp_changed": False,
        "new_v3_annotation_claimed": False, "model_calls": 0,
        "frozen_evaluator_commit": "ea4dd51494d19d351def97488d01e1e194d045a9",
        "blindness_basis": "user correction plus existing RGB-only/independence attestations, not independently authenticated",
    })
    print(annotation_path)


if __name__ == "__main__":
    main()
