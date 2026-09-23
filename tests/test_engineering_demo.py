from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.adapters.physics_preview import VisionCandidateBuilder
from embodied_runtime.experiments import engineering_demo as demo
from embodied_runtime.experiments import demo_report
from embodied_runtime.runtime_core import BeliefSnapshot, Candidate


def snapshot(valid=True):
    s = BeliefSnapshot("demo", 1, .5, {"tcp_pos_world_m": [0., 0., 1.],
        "gripper_width_m": .08, "gripper_command": "OPEN", "holding": None,
        "vision:drawer:position_world_m": [.2, 0., 1.]}, {}, {"instruction": "close drawer"},
        validity={"drawer": {"geometry_valid": valid, "geometry_age_s": 0.,
            "position_covariance": (np.eye(3)*.00001).tolist(), "semantic_valid": True,
            "temporal_consistency_ok": True, "provenance": []}})
    return replace(s, candidates=VisionCandidateBuilder(target_track="drawer").build(s))


def test_demo_view_preserves_natural_authorization_and_unknowns():
    s = snapshot()
    v = demo.DemoView(s, "drawer")
    assert set(v.model_questions()["action"]["criteria"]) == s.allowed()
    assert v.belief_id() == s.belief_id()
    assert v.snapshot_id() == s.snapshot_id()
    assert v.candidate_set_id() == s.candidate_set_id()
    assert v.canonical.allowed() == s.allowed()
    assert v.provider_input()["state"]["progress.remaining_open_mm"] is None
    assert v.provider_input()["state"]["interaction.target_contact"] is None
    assert v.provider_input()["effects"] == {}
    assert not v.canonical.state.privileged
    assert all(not c.metadata for c in v.canonical.candidates)
    assert any(c.metadata for c in s.candidates)


def test_demo_does_not_silently_bypass_stale_gate():
    s = snapshot(False)
    v = demo.DemoView(s, "drawer")
    assert s.allowed() == v.canonical.allowed() == {"STOP"}


def test_demo_rejects_privilege_and_unsupported_actions():
    s = snapshot()
    with pytest.raises(ValueError, match="privileged"):
        demo.DemoView(replace(s, continuous={**s.continuous, "remaining_open_mm": 10.}), "drawer")
    with pytest.raises(ValueError, match="supported"):
        demo.DemoView(replace(s, candidates=(Candidate("PUSH", "push drawer"),)), "drawer")


def test_recording_backend_only_changes_record_flag():
    calls = []
    world = SimpleNamespace(execute=lambda *a, **kw: calls.append((a, kw)))
    b = demo.RecordingBackend(world)
    b.apply_delta(np.array([.01, 0., 0.]))
    b.close_gripper()
    b.hold()
    assert calls == [(("x+10mm",), {"grip": -1., "record": True}),
                     (("close",), {"grip": 1., "record": True}),
                     (("hold",), {"grip": 1., "record": True})]


def test_demo_clipping_is_logged_and_rejected_before_model(monkeypatch):
    rows = []
    monkeypatch.setattr(demo, "encoding_audit", lambda *a: {"available": True, "truncated": True})
    provider = demo.DemoProvider(object(), "drawer", lambda k, d: rows.append((k, d)))
    with pytest.raises(ValueError, match="clipped"):
        provider.decide(snapshot())
    assert rows[0][0] == "demo_model_input"
    assert rows[0][1]["audit"]["truncated"]


def test_raw_response_preserved_before_token_mismatch_rejection(monkeypatch):
    rows = []
    agent = SimpleNamespace(device="cpu", dtype="float32", system_one=lambda *a: {"answers": {}})
    wrapper = demo.RecordingAgent(agent, lambda k, d: rows.append((k, d)))
    monkeypatch.setattr(demo, "encoding_audit", lambda *a: {"available": True, "truncated": False,
        "questions": {"action": {"effective_input_ids": [1], "option_markers": [0]}}})
    monkeypatch.setattr(demo, "observe_forward", lambda *a: None)
    with pytest.raises(ValueError, match="consumed tokens"):
        wrapper.system_one({}, {})
    assert rows[0][0] == "demo_model_response"
    assert rows[0][1]["raw_response"] == {"answers": {}}


def test_report_refuses_incomplete_chain(monkeypatch, tmp_path):
    monkeypatch.setattr(demo_report, "load_records", lambda p: ([], ["incomplete_tail"]))
    with pytest.raises(ValueError, match="incomplete raw"):
        demo_report.evidence(tmp_path)


def test_report_does_not_upgrade_failed_empty_run_to_success(monkeypatch, tmp_path):
    rows = [{"kind": "run_start", "data": {"resolved_config": {"oracle": False}}},
            {"kind": "failure", "data": {"category": "demo_error"}},
            {"kind": "termination", "data": {"reason": "demo_error", "success": False}}]
    monkeypatch.setattr(demo_report, "load_records", lambda p: (rows, []))
    monkeypatch.setattr(demo_report, "summarize", lambda p: None)
    monkeypatch.setattr(demo_report, "file_hash", lambda p: "raw")
    result = demo_report.evidence(tmp_path)
    assert result["steps"] == []
    assert result["failures"] == [{"category": "demo_error"}]
    assert result["termination"][0]["success"] is False
