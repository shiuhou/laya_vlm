from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.experiments import p1_semantic_roi_timing as timing
from embodied_runtime.perception.recording import FrameRecorder
from embodied_runtime.perception.rgbd_geometry import GeometryConfig
from embodied_runtime.sensor_api import Proprioception


def view():
    return dict(camera_id="agentview", frame_id="agentview:1", canonical_frame_id="ep/agentview/1", frame_seq=1,
        rgb=np.zeros((8, 12, 3), dtype=np.uint8), depth_m=np.ones((8, 12), dtype=np.float32),
        intrinsics_K=np.array([[20., 0, 6], [0, 20., 4], [0, 0, 1]]), T_base_camera=np.eye(4),
        calibration_version="cal1", capture_sim_time_s=1., capture_monotonic_ns=1000, frame="robot_base")


def prediction(boxes, *, admitted=True):
    return dict(entity="drawer_front_pushable", frame_id="ep/agentview/1", ordered_boxes=boxes,
                structurally_admitted=admitted, query="frozen query", geometry=[])


def test_every_ordered_box_and_abstention_retained_with_identical_geometry(monkeypatch):
    source = view()
    bundle = dict(views=(source,), proprio={"eef_position_base_m": (0., 0., 0.)})
    calls = []

    def estimate(*args, **kwargs):
        calls.append(kwargs["roi_xyxy"])
        class Patch:
            def to_dict(self):
                return {"geometry_status": "UNKNOWN", "reason": "synthetic_test"}
        return Patch()

    monkeypatch.setattr(timing, "estimate_visible_patch", estimate)
    first = prediction([[0., 0., 4., 4.], [5., 1., 10., 6.], [.1, .1, .2, .2]])
    first["geometry"] = [dict(box_index=i, roi_xyxy=box, patch={"geometry_status": "UNKNOWN", "reason": "synthetic_test"},
                              for_execution=False, structural_reason=None) for i, box in enumerate(first["ordered_boxes"])]
    first["geometry"][-1].update(patch=None, structural_reason="NO_INTEGER_PIXEL_ROI_SUPPORT")
    abstain = prediction([], admitted=False)
    rows = timing.process_workload(bundle, [first, abstain], GeometryConfig(),
                                   source_frames={source["canonical_frame_id"]: source}, mode="offline")
    assert calls == first["ordered_boxes"][:2]
    assert len(rows[0]["geometry"]) == 3 and rows[1]["abstained"]
    assert not any(row["for_execution"] for row in rows)
    assert all(row["semantic_cache_reused"] is False for row in rows)
    first["geometry"][0]["patch"]["reason"] = "different"
    with pytest.raises(ProtocolError, match="GEOMETRY_REPLAY_MISMATCH"):
        timing.process_workload(bundle, [first], GeometryConfig(), source_frames={source["canonical_frame_id"]: source}, mode="offline")


def test_live_cache_requires_identical_sensors_but_preserves_new_capture_times():
    source = view()
    live = {**source, "frame_id": "live:50", "capture_monotonic_ns": 5000}
    bundle = dict(views=(live,), proprio={"eef_position_base_m": (0., 0., 0.)})
    rows = timing.process_workload(bundle, [prediction([], admitted=False)], GeometryConfig(),
                                   source_frames={source["canonical_frame_id"]: source}, mode="live-static")
    assert rows[0]["source_capture_monotonic_ns"] == 5000
    assert rows[0]["semantic_cache_reused"] is True
    live["depth_m"] = live["depth_m"].copy()
    live["depth_m"][0, 0] += .001
    with pytest.raises(ProtocolError, match="FROZEN_WORKLOAD_MISMATCH"):
        timing.process_workload(bundle, [prediction([])], GeometryConfig(), source_frames={source["canonical_frame_id"]: source}, mode="live-static")


def test_timing_payload_and_sidecar_persistence_not_hidden_and_offline_never_fresh():
    now = [0]
    payloads, receipts = [], []

    def acquire(cycle):
        now[0] += 50_000_000
        return dict(bundle_id=str(cycle), capture_sim_time_s=1.)

    def process(bundle, cycle):
        now[0] += 200_000_000
        return [dict(source_capture_monotonic_ns=99_000_000_000, source_capture_sim_time_s=1.,
                     geometry=[], abstained=True, ordered_box_count=0)]

    def persist(bundle, record):
        now[0] += 50_000_000
        payloads.append(deepcopy(record))

    def receipt(record):
        now[0] += 10_000_000
        receipts.append(deepcopy(record))

    records, completions, summary = timing.run_timing_cycles(acquire, process, persist, receipt,
        count=3, mode="offline", clock_ns=lambda: now[0])
    assert summary["complete_persisted_workload_cycles_hz"] == pytest.approx(1/.31)
    assert summary["capture_to_publication_ms"] is None and summary["requested_hz"] is None
    assert summary["payload_persistence_ms"]["p95"] == 50
    assert summary["completion_sidecar_persistence_ms"]["p95"] == 10
    assert records[0]["result"][0]["freshness"] == {"evaluated": False, "reason": "OFFLINE_HISTORICAL_CAPTURE_CLOCK"}
    assert receipts[0]["payload_persistence_finished_monotonic_ns"] == 300_000_000
    assert receipts[0]["record_sha256"] == content_hash(payloads[0])
    assert completions[0]["completion_sidecar_persistence_ms"] == 10
    assert summary["source_timestamps_rewritten"] is False


def test_live_timing_clock_deadlines_and_geometry_freshness_do_not_certify_semantics():
    now = [0]

    def acquire(cycle):
        now[0] += 10_000_000
        return dict(bundle_id=str(cycle), capture_sim_time_s=1., captured_ns=now[0])

    def process(bundle, cycle):
        now[0] += 400_000_000
        return [dict(source_capture_monotonic_ns=bundle["captured_ns"], source_capture_sim_time_s=1., geometry=[], abstained=True, ordered_box_count=0)]

    records, _, summary = timing.run_timing_cycles(acquire, process, lambda *_: None, lambda *_: None,
        count=2, mode="live-static", clock_ns=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0]+round(s*1e9)))
    freshness = records[0]["result"][0]["freshness"]
    assert freshness["wall_age_s"] == .4 and freshness["sim_age_s"] == 0
    assert not freshness["free_geometry_fresh"] and not freshness["contact_geometry_fresh"]
    assert freshness["does_not_certify_semantic_freshness_or_action_eligibility"]
    assert summary["live_scheduled_deadline_misses"] == 2
    assert summary["capture_to_publication_ms"]["p95"] == 410
    assert summary["fresh_semantic_grounding"] is False


def test_duration_bound_finishes_active_cycle_but_starts_no_cycle_after_deadline():
    now = [0]
    def acquire(cycle):
        return dict(bundle_id=str(cycle), capture_sim_time_s=1.)
    def process(*args):
        now[0] += 400_000_000
        return []
    records, _, summary = timing.run_timing_cycles(acquire, process, lambda *_: None, lambda *_: None,
        count=None, mode="live-static", duration_s=1., clock_ns=lambda: now[0])
    assert len(records) == 3 and summary["measurement_elapsed_s"] == 1.2
    assert all(record["started_monotonic_ns"] < 1_000_000_000 for record in records)


def sealed_fixture(tmp_path):
    source = tmp_path/"source"
    source.mkdir()
    (source/"manifest.json").write_text("{}")
    sensor = view()
    robot = Proprioception(1., 1000, (0., 0., 0.), (0., 0., 0., 1.), (0.,), None, True, ("r",), reason_codes=("WIDTH_UNCALIBRATED",))
    with FrameRecorder(source/"init-000", episode_id="ep", clock_domain="test", condition="synthetic") as recorder:
        recorder.append((sensor,), robot, emitted_monotonic_ns=2000)
    envelope = json.loads((source/"init-000/frames.jsonl").read_text())
    rgb_hash = envelope["payload"]["views"][0]["rgb_blob"]["sha256"]
    registration = dict(entity_order=list(timing.ENTITIES), generator_inputs=["RGB", "fixed_query"], for_execution=False,
        geometry_file_sha256=timing.GEOMETRY_FILE_SHA256, geometry_code_sha256=timing.GEOMETRY_CODE_SHA256,
        geometry_resolved_sha256=content_hash(GeometryConfig().to_dict()), model_calls=2,
        image_order=["ep/agentview/1"], queries={entity: entity for entity in timing.ENTITIES},
        source=dict(path=str(source), manifest_sha256=hashlib.sha256((source/"manifest.json").read_bytes()).hexdigest(),
                    recording_metadata_sha256={str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("init-*/*.json*")}))
    registration["registration_sha256"] = content_hash(registration)
    out = tmp_path/"sealed"
    out.mkdir()
    (out/"preregistration.json").write_text(json.dumps(registration))
    predictions = []
    for n, entity in enumerate(timing.ENTITIES):
        call = out/f"call-{n:03d}"
        call.mkdir()
        request = dict(entity=entity, image_id="ep/agentview/1", frame_id="ep/agentview/1", query=entity,
                       rgb_pixel_sha256=hashlib.sha256(sensor["rgb"].tobytes()).hexdigest(), rgb_blob_sha256=rgb_hash, width=12, height=8)
        pred = {**request, "structurally_admitted": False, "ordered_boxes": [], "geometry": []}
        predictions.append(pred)
        (call/"request.json").write_text(json.dumps(request))
        (call/"prediction.json").write_text(json.dumps(pred))
    (out/"predictions-sealed.json").write_text(json.dumps(dict(model_calls=2, predictions_sha256=content_hash(predictions), annotation_geometry_consumed=False, runtime_actions=0)))
    (out/"completed.json").write_text(json.dumps(dict(model_calls=2)))
    return out


def test_unsealed_or_tampered_predictions_cannot_supply_timing_workload(tmp_path):
    out = sealed_fixture(tmp_path)
    loaded = timing.load_sealed_workload(out)
    assert len(loaded["predictions"]) == 2 and len(loaded["bundles"]) == 1
    path = out/"call-000/prediction.json"
    value = json.loads(path.read_text())
    value["ordered_boxes"] = [[0, 0, 1, 1]]
    path.write_text(json.dumps(value))
    with pytest.raises(ProtocolError, match="CONDITION_CHANGED"):
        timing.load_sealed_workload(out)
    (out/"predictions-sealed.json").unlink()
    with pytest.raises(FileNotFoundError):
        timing.load_sealed_workload(out)


def test_timing_module_does_not_import_semantic_model_or_annotation_contents():
    source = Path(timing.__file__).read_text()
    assert "annotations-evaluation-input.json" not in source
    assert "_load_worker" not in source and "import torch" not in source
