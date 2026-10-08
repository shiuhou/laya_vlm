"""Synthetic packet boundaries only; no real heldout labels or images are read."""
from copy import deepcopy
import json

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_heldout_annotation_packet as packet
from embodied_runtime.perception.evaluation_annotations import image_binding
from embodied_runtime.perception.recording import FrameRecorder
from embodied_runtime.sensor_api import Proprioception


@pytest.fixture
def raw_packet(tmp_path):
    source, output = tmp_path / "source", tmp_path / "packet"
    (source / "capture").mkdir(parents=True)
    (source / "capture/manifest.json").write_text(json.dumps({"config": {"init_indices": list(range(27, 50))}}))
    proprio = Proprioception(1., 10, (0., 0., 0.), (0., 0., 0., 1.), (0.,), None, True,
                            ("robot/1",), reason_codes=("WIDTH_UNCALIBRATED",))
    for init in range(27, 50):
        views = [dict(rgb=np.full((12, 16, 3), init + n * 100, dtype=np.uint8),
            depth_m=np.ones((12, 16), dtype=np.float32),
            intrinsics_K=np.array([[20., 0, 8], [0, 20., 6], [0, 0, 1]]), T_base_camera=np.eye(4),
            camera_id=camera, frame_seq=1, frame_id=f"{camera}:1", calibration_version="synthetic-cal1",
            capture_sim_time_s=1., capture_monotonic_ns=10, frame="robot_base")
            for n, camera in enumerate(("agentview", packet.CAMERA))]
        with FrameRecorder(source / f"init-{init:03d}", episode_id=f"synthetic/init{init}",
                           clock_domain="host", condition="synthetic_test") as recorder:
            recorder.append(views, proprio, emitted_monotonic_ns=20)
    packet.build_packet(source, output)
    return source, output


def labels(manifest):
    value = dict(schema=packet.ANNOTATION_SCHEMA, dataset_id=manifest["dataset_id"],
        annotator_id="synthetic-test-fixture-not-research-evidence", annotator_role="independent_human_annotator",
        rules_version=packet.RULES_VERSION, rules_sha256=packet.RULES_SHA256,
        attestations={key: True for key in packet.ATTESTATIONS}, exported_at_utc="2026-10-08T00:00:00Z",
        annotations=[])
    for n, image in enumerate(manifest["images"]):
        status = ("VISIBLE", "UNKNOWN", "NOT_VISIBLE")[n % 3]
        region = dict(status=status, reason="Synthetic fixture only",
                      polygons=[[[2, 2], [10, 2], [10, 9], [2, 9]]] if status == "VISIBLE" else [])
        value["annotations"].append({**image_binding(image), "entities": {
            "drawer_front_pushable": region,
            "fixed_cabinet_reference": dict(status="UNKNOWN", reason="Synthetic uncertainty", polygons=[], reference_types=[]),
        }})
    return value


def test_packet_roundtrip_raw_wrist_only_frozen_rules_and_no_prefill(raw_packet):
    source, out = raw_packet
    manifest = packet.load_packet(out)
    assert [x["init_index"] for x in manifest["images"]] == list(range(27, 50))
    assert all(x["camera_id"] == packet.CAMERA for x in manifest["images"])
    assert manifest["rules_version"] == "p1-rgb-annotation-rules/2"
    assert (out / "annotation_rules.md").read_bytes() == packet.RULES_SOURCE.read_bytes()
    page = (out / "index.html").read_text()
    assert packet.ANNOTATION_SCHEMA in page and packet.SCOPE_NOTICE in page
    assert "p1-human-annotations/3" not in page and "fetch(" not in page
    assert "depth_blob" not in page and "candidate_projections" not in page
    assert "independent_of_ai_drafts:true" in page
    empty = out / "annotations.empty.json"
    assert json.loads(empty.read_text())["annotations"] == []
    with pytest.raises(ProtocolError):
        packet.validate_complete(empty, out)
    with pytest.raises(FileExistsError):
        packet.build_packet(source, out)
    export = out / "synthetic-only.json"
    export.write_text(json.dumps(labels(manifest)))
    summary = packet.validate_complete(export, out)
    assert summary["complete"] and summary["annotated_images"] == 23
    assert summary["visibility_counts"]["drawer_front_pushable"] == {"VISIBLE": 8, "UNKNOWN": 8, "NOT_VISIBLE": 7}


def test_complete_validator_rejects_binding_partial_draft_version_and_unattested(raw_packet):
    _, out = raw_packet
    pristine = labels(packet.load_packet(out))
    changes = [
        lambda x: x["annotations"].pop(),
        lambda x: x["annotations"].__setitem__(-1, deepcopy(x["annotations"][0])),
        lambda x: x["annotations"][0].__setitem__("rgb_pixel_sha256", "f" * 64),
        lambda x: x.__setitem__("rules_version", "p1-rgb-annotation-rules/3"),
        lambda x: x.__setitem__("rules_sha256", "f" * 64),
        lambda x: x.__setitem__("schema", "p1-human-annotations/2"),
        lambda x: x["attestations"].__setitem__("independent_of_ai_drafts", False),
        lambda x: x["attestations"].__setitem__("is_human", "true"),
        lambda x: x.__setitem__("provenance", {"prior_ai_exposure": True}),
        lambda x: x.__setitem__("annotator_id", "codex"),
        lambda x: x["annotations"][0]["entities"]["drawer_front_pushable"].__setitem__("polygons", []),
    ]
    for mutate in changes:
        value = deepcopy(pristine)
        mutate(value)
        path = out / "invalid-synthetic.json"
        path.write_text(json.dumps(value))
        with pytest.raises(ProtocolError):
            packet.validate_complete(path, out)


def test_packet_checks_population_duplicate_pixels_and_raw_png_integrity(raw_packet):
    _, out = raw_packet
    pristine = packet.load_packet(out)
    for key, replacement in (("init_index", 0), ("camera_id", "agentview"),
                             ("rgb_pixel_sha256", pristine["images"][1]["rgb_pixel_sha256"])):
        value = deepcopy(pristine)
        value["images"][0][key] = replacement
        value["dataset_id"] = packet.packet_identity(value)
        with pytest.raises(ProtocolError):
            packet.validate_manifest(value)
    image = out / pristine["images"][0]["image_path"]
    image.write_bytes(b"corrupt")
    with pytest.raises(ProtocolError, match="PNG hash mismatch"):
        packet.load_packet(out)
