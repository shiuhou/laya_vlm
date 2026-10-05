from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments.p1_annotation_packet import build_packet
from embodied_runtime.perception.evaluation_annotations import (
    ANNOTATION_SCHEMA, ENTITIES, PACKET_SCHEMA, PREDICTION_SCHEMA, RULES_VERSION,
    evaluate_grounding, image_binding, load_packet, packet_identity,
    validate_annotations, validate_packet_manifest, validate_polygons,
)
from embodied_runtime.perception.recording import FrameRecorder
from embodied_runtime.sensor_api import Proprioception


def manifest(count=50):
    result = {"schema": PACKET_SCHEMA, "dataset_id": None, "source_run_manifest_sha256": "a"*64,
              "selection_rule": "first_bundle_each_camera_per_init_raw_rgb_only", "expected_image_count": count,
              "rules_version": RULES_VERSION, "rules_sha256": "b"*64, "rules_path": "annotation_rules.md",
              "images": []}
    for n in range(count):
        init = n//2
        camera = ("agentview", "robot0_eye_in_hand")[n % 2]
        identity = f"p1/init{init}/{camera}/1"
        result["images"].append(dict(image_id=identity, frame_id=identity, source_frame_id=f"{camera}:1",
            episode_id=f"p1/init{init}", init_index=init, camera_id=camera, width=16, height=12,
            rgb_blob_sha256=f"{n+1:064x}", rgb_pixel_sha256=f"{n+101:064x}", png_sha256=f"{n+201:064x}",
            image_path=f"images/{n:03d}.png"))
    result["dataset_id"] = packet_identity(result)
    return result


def annotations(packet):
    region = {"status": "VISIBLE", "reason": "Synthetic schema test fixture only",
              "polygons": [[[2, 2], [10, 2], [10, 9], [2, 9]]]}
    return {"schema": ANNOTATION_SCHEMA, "dataset_id": packet["dataset_id"], "annotator_id": "test-reviewer-01",
            "annotator_role": "project_primary_human", "rules_version": packet["rules_version"], "rules_sha256": packet["rules_sha256"],
            "attestations": {"is_human": True, "independent_of_model_outputs": True, "raw_rgb_only": True},
            "exported_at_utc": "2026-10-05T00:00:00Z",
            "annotations": [{**image_binding(image), "entities": {name: {**deepcopy(region), **({"reference_types": ["FRONT_FRAME"]} if name == "fixed_cabinet_reference" else {})} for name in ENTITIES}}
                            for image in packet["images"]]}


def predictions(packet, labels):
    result = {"schema": PREDICTION_SCHEMA, "dataset_id": packet["dataset_id"], "producer_id": "synthetic-predictor",
              "revision": "test-v1", "records": deepcopy(labels["annotations"])}
    for row in result["records"]:
        for entity in row["entities"].values():
            entity["points"] = [[5, 5], [15, 5]]
    return result


def test_complete_50_image_coverage_is_required_and_no_verified_human_claim():
    packet = manifest()
    labels = annotations(packet)
    result = validate_annotations(labels, packet)
    assert result["complete"] and result["annotated_images"] == 50
    assert result["human_identity_claim"] == "self_attested_not_independently_verified"
    assert result["annotator_role"] == "project_primary_human"
    assert result["third_party_review_claimed"] is False
    labels["annotations"].pop()
    with pytest.raises(ProtocolError, match="ANNOTATION_COVERAGE"):
        validate_annotations(labels, packet)
    assert len(validate_annotations(labels, packet, require_complete=False)["missing_image_ids"]) == 1


@pytest.mark.parametrize("disclosure", [
    {"prior_ai_exposure": True},
    {"eligible_for_human_blind_evaluation": False},
    {"prior_ai_exposure": True, "eligible_for_human_blind_evaluation": False},
])
def test_blind_self_attestation_cannot_override_negative_provenance(disclosure):
    packet = manifest()
    labels = annotations(packet)
    labels["provenance"] = disclosure
    original = deepcopy(labels)
    with pytest.raises(ProtocolError, match="ANNOTATION_BLINDNESS_CONFLICT"):
        validate_annotations(labels, packet)
    assert labels == original


@pytest.mark.parametrize("change", ["binding", "dimension", "duplicate", "extra_field", "missing_reason", "blank_identity", "agent_identity", "unattested"])
def test_incomplete_or_untrusted_labels_fail_closed(change):
    packet = manifest()
    labels = annotations(packet)
    if change == "binding":
        labels["annotations"][0]["rgb_blob_sha256"] = "f"*64
    elif change == "dimension":
        labels["annotations"][0]["width"] += 1
    elif change == "duplicate":
        labels["annotations"][-1] = deepcopy(labels["annotations"][0])
    elif change == "extra_field":
        labels["oracle_success"] = True
    elif change == "missing_reason":
        labels["annotations"][0]["entities"][ENTITIES[0]]["reason"] = ""
    elif change == "blank_identity":
        labels["annotator_id"] = " "
    elif change == "agent_identity":
        labels["annotator_id"] = "codex"
    elif change == "unattested":
        labels["attestations"]["independent_of_model_outputs"] = False
    with pytest.raises(ProtocolError):
        validate_annotations(labels, packet)


@pytest.mark.parametrize("polygon", [
    [[1, 1], [9, 9], [1, 9], [9, 1]],
    [[1, 1], [2, 2], [3, 3]],
    [[-1, 1], [5, 1], [5, 5]],
    [[1, 1], [5, 1], [5, 5], [1, 1]],
    [[1, 1], [float("nan"), 1], [5, 5]],
])
def test_degenerate_crossed_outside_or_nonfinite_polygons_rejected(polygon):
    with pytest.raises(ProtocolError, match="ANNOTATION_POLYGON"):
        validate_polygons([polygon], 16, 12)


def test_visible_unknown_not_visible_and_multiple_typed_fixed_reference_regions():
    packet = manifest()
    labels = annotations(packet)
    for n, status in enumerate(("NOT_VISIBLE", "UNKNOWN", "UNKNOWN")):
        labels["annotations"][n]["entities"][ENTITIES[0]] = {"status": status, "reason": "Explicit fixture uncertainty", "polygons": []}
    labels["annotations"][3]["entities"][ENTITIES[1]]["polygons"].append([[11, 1], [15, 1], [15, 5]])
    labels["annotations"][3]["entities"][ENTITIES[1]]["reference_types"].append("FIXED_EDGE")
    summary = validate_annotations(labels, packet)
    assert summary["visibility_counts"][ENTITIES[0]] == {"VISIBLE": 47, "NOT_VISIBLE": 1, "UNKNOWN": 2}
    labels["annotations"][0]["entities"][ENTITIES[0]]["polygons"] = [[[1, 1], [3, 1], [3, 3]]]
    with pytest.raises(ProtocolError):
        validate_annotations(labels, packet)


@pytest.mark.parametrize("change", ["legacy_status", "rule_hash", "rule_version", "third_party", "untyped_reference", "unknown_reference_visible"])
def test_frozen_v2_rules_and_typed_human_reference_required(change):
    packet = manifest()
    labels = annotations(packet)
    reference = labels["annotations"][0]["entities"][ENTITIES[1]]
    if change == "legacy_status":
        reference["status"] = "occluded"
    elif change == "rule_hash":
        labels["rules_sha256"] = "c"*64
    elif change == "rule_version":
        labels["rules_version"] = "p1-rgb-annotation-rules/1"
    elif change == "third_party":
        labels["annotator_role"] = "independent_reviewer"
    elif change == "untyped_reference":
        reference["reference_types"] = []
    elif change == "unknown_reference_visible":
        reference["reference_types"] = ["UNKNOWN"]
    with pytest.raises(ProtocolError):
        validate_annotations(labels, packet)


def test_unknown_fixed_identity_preserved_and_model_type_not_invented():
    packet = manifest()
    labels = annotations(packet)
    ref = labels["annotations"][0]["entities"][ENTITIES[1]]
    ref.update(status="UNKNOWN", reference_types=["UNKNOWN"], reason="Cannot distinguish moving drawer from fixed body")
    validate_annotations(labels, packet)
    guesses = predictions(packet, labels)
    guesses["records"][1]["entities"][ENTITIES[1]]["reference_types"] = ["UNKNOWN"]
    report = evaluate_grounding(guesses, labels, packet)
    assert report["summary"][ENTITIES[1]]["unknown_labels_excluded"] == 1
    assert any(row["predicted_reference_types"] == ["UNKNOWN"] and row["annotated_status"] == "VISIBLE" for row in report["records"])


def test_partial_annotation_export_cannot_enter_evaluation():
    packet = manifest()
    labels = annotations(packet)
    guesses = predictions(packet, labels)
    labels["annotations"].pop()
    assert not validate_annotations(labels, packet, require_complete=False)["complete"]
    with pytest.raises(ProtocolError, match="ANNOTATION_COVERAGE"):
        evaluate_grounding(guesses, labels, packet)


def test_offline_iou_and_inside_boundary_metrics_preserve_uncertain_exclusion():
    packet = manifest()
    labels = annotations(packet)
    labels["annotations"][0]["entities"][ENTITIES[0]] = {"status": "UNKNOWN", "reason": "Insufficient view", "polygons": []}
    guesses = predictions(packet, labels)
    report = evaluate_grounding(guesses, labels, packet)
    result = report["summary"][ENTITIES[0]]
    assert result["visible_iou_count"] == 49 and result["mean_visible_polygon_iou"] == 1
    assert result["unknown_labels_excluded"] == 1
    row = next(r for r in report["records"] if r["point_metrics"])
    assert row["point_metrics"][0]["inside_annotated_region"]
    assert row["point_metrics"][0]["signed_interior_margin_px"] == 3
    assert not row["point_metrics"][1]["inside_annotated_region"]
    assert row["point_metrics"][1]["signed_interior_margin_px"] == -5
    assert report["evaluation_only"] and not report["labels_prove_contact_safety"]
    assert not report["labels_prove_static_reference"]


def test_evaluation_cannot_skip_difficult_images_or_use_same_annotator_as_model():
    packet = manifest()
    labels = annotations(packet)
    guesses = predictions(packet, labels)
    guesses["records"].pop()
    with pytest.raises(ProtocolError, match="ANNOTATION_COVERAGE"):
        evaluate_grounding(guesses, labels, packet)
    guesses = predictions(packet, labels)
    guesses["producer_id"] = labels["annotator_id"].upper()
    with pytest.raises(ProtocolError, match="ANNOTATOR_ATTESTATION"):
        evaluate_grounding(guesses, labels, packet)


def test_packet_detects_hash_tampering_duplicate_content_and_wrong_init_coverage():
    for mutation in ("hash", "duplicate_content", "coverage"):
        packet = manifest()
        if mutation == "hash":
            packet["images"][0]["width"] += 1
        elif mutation == "duplicate_content":
            packet["images"][1]["rgb_pixel_sha256"] = packet["images"][0]["rgb_pixel_sha256"]
            packet["dataset_id"] = packet_identity(packet)
        else:
            packet["images"][0]["init_index"] = 100
            packet["dataset_id"] = packet_identity(packet)
        with pytest.raises(ProtocolError):
            validate_packet_manifest(packet)


def source_fixture(tmp_path):
    source = tmp_path/"source"
    source.mkdir()
    (source/"manifest.json").write_text(json.dumps({"config": {"init_indices": [0]}}))
    proprio = Proprioception(1., 10, (0., 0., 0.), (0., 0., 0., 1.), (0.,), None, True, ("robot/1",), reason_codes=("WIDTH_UNCALIBRATED",))
    views = []
    for n, camera in enumerate(("agentview", "robot0_eye_in_hand")):
        views.append(dict(rgb=np.full((12, 16, 3), 40+n*80, dtype=np.uint8), depth_m=np.ones((12, 16), dtype=np.float32),
            intrinsics_K=np.array([[20., 0, 8], [0, 20., 6], [0, 0, 1]]), T_base_camera=np.eye(4),
            camera_id=camera, frame_seq=1, frame_id=f"{camera}:1", calibration_version="cal1",
            capture_sim_time_s=1., capture_monotonic_ns=10, frame="robot_base"))
    with FrameRecorder(source/"init-000", episode_id="p1/init0", clock_domain="host", condition="synthetic_test") as recorder:
        recorder.append(views, proprio, emitted_monotonic_ns=20)
    return source


def test_generated_packet_has_only_raw_rgb_no_labels_and_roundtrip_hashes(tmp_path):
    pytest.importorskip("PIL")
    source = source_fixture(tmp_path)
    output = tmp_path/"packet"
    result = build_packet(source, output, expected_count=2)
    assert result["image_count"] == 2 and result["completed_annotations"] == 0
    packet = load_packet(output, expected_count=2)
    assert len(packet["images"]) == 2
    source_rules = (Path(__file__).parents[1]/"docs/p1-annotation-rules.md").read_bytes()
    assert (output/"annotation_rules.md").read_bytes() == source_rules
    assert packet["rules_sha256"] == hashlib.sha256(source_rules).hexdigest()
    empty = json.loads((output/"annotations.empty.json").read_text())
    assert empty["annotations"] == [] and empty["annotator_id"] is None
    assert not any(empty["attestations"].values())
    with pytest.raises(ProtocolError):
        validate_annotations(empty, packet, expected_count=2)
    html = (output/"index.html").read_text()
    assert "fetch(" not in html and "https://" not in html
    assert "type=\"application/json\"" in html
    assert "depth_blob" not in html and "candidate_projections" not in html
    assert "p1-rgb-annotation-rules/2" in html and packet["rules_sha256"] in html
    assert "<option>VISIBLE</option><option>UNKNOWN</option><option>NOT_VISIBLE</option>" in html
    assert "Partial exports cannot enter evaluation" in html
    assert set(p.suffix for p in (output/"images").iterdir()) == {".png"}
    image = output/packet["images"][0]["image_path"]
    image.write_bytes(b"tampered")
    with pytest.raises(ProtocolError, match="PNG hash mismatch"):
        load_packet(output, expected_count=2)


def test_packet_frozen_rules_cannot_change_after_distribution(tmp_path):
    pytest.importorskip("PIL")
    source = source_fixture(tmp_path)
    output = tmp_path/"packet"
    build_packet(source, output, expected_count=2)
    (output/"annotation_rules.md").write_text("different instructions")
    with pytest.raises(ProtocolError, match="ANNOTATION_RULES"):
        load_packet(output, expected_count=2)


def test_packet_generation_never_overwrites_human_work(tmp_path):
    pytest.importorskip("PIL")
    source = source_fixture(tmp_path)
    output = tmp_path/"packet"
    build_packet(source, output, expected_count=2)
    original = hashlib.sha256((output/"index.html").read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        build_packet(source, output, expected_count=2)
    assert hashlib.sha256((output/"index.html").read_bytes()).hexdigest() == original
