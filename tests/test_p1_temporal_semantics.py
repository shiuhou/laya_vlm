import json

import numpy as np
import pytest

from embodied_runtime.experiments import p1_temporal_semantics as probe
from embodied_runtime.contracts import ProtocolError


def view():
    return dict(camera_id="agentview", frame_id="agentview:1", canonical_frame_id="test/agentview/1",
                frame_seq=1, calibration_version="test-calibration", capture_monotonic_ns=0,
                capture_sim_time_s=0., rgb=np.zeros((8, 8, 3), np.uint8),
                private_evaluator_truth="must not enter inference")


@pytest.mark.parametrize("boxes", [[], [[1., 1., 5., 5.]], [[1., 1., 3., 3.], [4., 4., 7., 7.]]])
def test_all_responses_preserved_but_only_unambiguous_seed_exported(tmp_path, monkeypatch, boxes):
    calls = []
    frame = view()

    def infer(worker, rgb, query, emit):
        assert rgb is frame["rgb"]
        calls.append(query)
        emit("model-input", {"rgb_only": True, "query": query})
        return "synthetic response", {"fixture": True}

    monkeypatch.setattr(probe, "infer_audited", infer)
    monkeypatch.setattr(probe, "classify_response", lambda *a: {"structurally_admitted": bool(boxes), "ordered_boxes": boxes})
    seeds, receipts = probe.infer_views(object(), [frame], tmp_path / "results", request_time_ns=0, deadline_ns=1)
    assert len(calls) == len(receipts) == 2
    assert len(seeds) == (2 if len(boxes) == 1 else 0)
    assert all(r["deadline_expired"] is True for r in receipts)
    for r in receipts:
        assert "private_evaluator_truth" not in r
        assert r["source_frame_id"] == "test/agentview/1"
        assert r["raw_source_frame_id"] == "agentview:1"
        assert r["classification"]["ordered_boxes"] == boxes
    for seed in seeds:
        artifact = json.loads(__import__("pathlib").Path(seed["artifact_uri"]).read_text())
        assert artifact["seed_source"] == "real_model"
        assert artifact["evaluation_labels_used"] is False
        assert seed["artifact_sha256"] == probe.sha(seed["artifact_uri"])


def test_existing_evidence_is_never_overwritten(tmp_path):
    output = tmp_path / "already.json"
    output.write_text("original")
    with pytest.raises(FileExistsError):
        probe.write(output, {"replacement": True})
    assert output.read_text() == "original"


def test_invalid_mode_rejects_before_model_load(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["probe", "--output", str(tmp_path)])
    monkeypatch.setattr(probe, "_load_worker", lambda: pytest.fail("model must not load"))
    with pytest.raises(ProtocolError):
        probe.main()
