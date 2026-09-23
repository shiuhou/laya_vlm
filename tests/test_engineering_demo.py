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
    assert demo_report.render_report(tmp_path).endswith("demo.html")
    assert "demo_error" in (tmp_path / "demo.html").read_text()


def recorded_demo(tmp_path, monkeypatch, *, singleton=False, choice="GRASP", interrupt=False,
                  mismatch=None):
    """A real DemoProvider/Runtime path over an instrumented fake backend."""
    from embodied_runtime.adapters import laya_input
    from embodied_runtime.experiments.records import RunRecorder, file_hash
    from embodied_runtime.runtime import Runtime
    from embodied_runtime.runtime_core import FakeBackend

    s = snapshot(not singleton)
    audit = {"available": True, "truncated": False, "questions": {"action": {
        "effective_input_ids": [1, 2], "option_markers": [1], "effective_token_count": 2}}}
    monkeypatch.setattr(demo, "encoding_audit", lambda *a: audit)
    monkeypatch.setattr(laya_input, "encoding_audit", lambda *a: audit)
    monkeypatch.setattr(demo, "observe_forward", lambda agent, traces: traces.append(
        {"input_ids": [[1, 2]], "option_markers": [[1]]}))
    agent = SimpleNamespace(device="cpu", dtype="float32", system_one=lambda *a:
        {"answers": {"action": {"choice": choice, "probabilities": {choice: .7}, "confidence": .2}}})
    out = tmp_path / "run"
    rec = RunRecorder(out, {"query": "drawer", "oracle": False}, {"run_id": "fixture"})
    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    rec.capture({"capture_seq": 7, "capture_sim_time": .5, "camera_name": "fake",
                 "rgb": rgb, "depth_m": np.ones((8, 8)), "intrinsics": np.eye(3), "camera_to_world": np.eye(4)})
    rec.record("demo_boundary", {"step": 0, "capture_seq": 7})
    rec.record("vision_completed", {"capture_seq": 7, "event": None})

    def sink(kind, data):
        from copy import deepcopy
        if kind == "demo_model_response" and mismatch == "response":
            data = deepcopy(data)
            data["raw_response"]["answers"]["action"]["choice"] = "RELEASE"
        if kind == "demo_model_input" and mismatch == "privilege":
            data = deepcopy(data)
            data["state"]["state"]["progress.remaining_open_mm"] = 100.
        return rec.record(kind, data)

    class Backend(FakeBackend):
        def execution_state(self):
            return {"finger_gap_m": self.width, "sim_time": .5}

        def execution_evidence(self, token, before):
            return {"execution_before": before, "execution_after": {"finger_gap_m": self.width, "sim_time": .55},
                    "environment_step_count": 1, "low_level_commands": [[0, 0, 0, 0, 0, 0, 1]],
                    "rotation_angle_deg": 0., "execution_contract_violation": False, "execution_contract_reason": []}

        def close_gripper(self):
            if interrupt:
                raise RuntimeError("injected execution interruption")
            super().close_gripper()

    rt = Runtime("demo", demo.DemoProvider(agent, "drawer", sink), Backend(), event_sink=sink)
    # Fixed sensor belief for this fixture, while using real validation/execution.
    monkeypatch.setattr(rt.store, "snapshot", lambda *a, **kw: s)
    rec.record("evaluation", {"step": 0, "phase": "before", "oracle_evaluator": True,
                               "features": {"remaining_open_mm": 100., "success": False}})
    try:
        rt.step(.5)
    except RuntimeError:
        assert interrupt
    if not interrupt:
        path = out / "trajectory.npz"
        np.savez_compressed(path, commands=[[0, 0, 0, 0, 0, 0, 0 if mismatch == "controls" else 1]],
                            states_before=[[0]], frames=[rgb], state_after=[0])
        rec.record("demo_trajectory", {"step": 0, "artifact": path.name, "sha256": file_hash(path), "frames": 1})
        rec.record("evaluation", {"step": 0, "phase": "after", "oracle_evaluator": True,
                                   "features": {"remaining_open_mm": 100., "success": False}})
        rec.record("termination", {"reason": "action_budget", "success": False})
    rec.close()
    return out


def test_inspector_traces_actual_provider_to_controls(tmp_path, monkeypatch):
    from embodied_runtime.experiments.demo_inspector import write_inspector
    out = recorded_demo(tmp_path, monkeypatch)
    data = demo_report.evidence(out)
    assert data["verified_laya_executions"] == 1
    assert data["attempts"][0]["issues"] == []
    assert data["steps"][0]["capture"]["capture_seq"] == 7
    assert data["steps"][0]["evaluation"]["after"]["features"]["success"] is False
    html = open(write_inspector(out, data)).read()
    assert "remaining_open_mm" in html
    assert "Model state argument" in html
    assert "data:image/png;base64," in html
    assert "GRASP" in html and "STOP" in html
    assert "Record" in html


@pytest.mark.parametrize("mismatch,issue", [("response", "raw Laya response"), ("controls", "trajectory controls"),
                                         ("privilege", "visual demo projection")])
def test_inspector_does_not_certify_unconnected_evidence(tmp_path, monkeypatch, mismatch, issue):
    data = demo_report.evidence(recorded_demo(tmp_path, monkeypatch, mismatch=mismatch))
    assert data["verified_laya_executions"] == 0
    assert any(issue in i for i in data["attempts"][0]["issues"])


@pytest.mark.parametrize("singleton,choice,label", [(True, "GRASP", "forced singleton"),
                                                     (False, "NOT_AN_ACTION", "validation fallback")])
def test_forced_and_fallback_actions_never_count_as_laya_execution(tmp_path, monkeypatch, singleton, choice, label):
    data = demo_report.evidence(recorded_demo(tmp_path, monkeypatch, singleton=singleton, choice=choice))
    row = data["attempts"][0]
    assert row["issues"] == []
    assert label in row["classification"]
    assert row["execution"]["token"] == "STOP"
    assert data["verified_laya_executions"] == 0
    if not singleton:
        assert row["decision"]["token"] == "NOT_AN_ACTION"
        assert row["intent"]["fallback_reason"] == "decision_not_allowed"


def test_interrupted_execution_keeps_input_and_unknown_outcome(tmp_path, monkeypatch):
    out = recorded_demo(tmp_path, monkeypatch, interrupt=True)
    data = demo_report.evidence(out)
    assert data["run_incomplete"]
    assert data["steps"] == []
    assert data["attempts"][0]["model_input"]
    assert "execution outcome unknown" in data["attempts"][0]["issues"]
    assert data["failures"][0]["category"] == "environment_error"
    assert demo_report.render_report(out).endswith("demo.html")


def test_corrupt_trajectory_refused(tmp_path, monkeypatch):
    out = recorded_demo(tmp_path, monkeypatch)
    (out / "trajectory.npz").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="trajectory artifact mismatch"):
        demo_report.evidence(out)


def test_stale_replay_is_labeled_and_html_escapes_failure(tmp_path, monkeypatch):
    import json
    from embodied_runtime.experiments.demo_inspector import write_inspector
    out = recorded_demo(tmp_path, monkeypatch)
    (out / "replay-check.json").write_text(json.dumps({"passed": True, "raw_source_sha256": "another-run"}))
    data = demo_report.evidence(out)
    assert data["replay"]["matches_raw_source"] is False
    data["failures"].append({"exception": "<script>alert('failure')</script>"})
    html = open(write_inspector(out, data)).read()
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_telemetry_records_before_console_and_exposes_fallback(capsys):
    rows = []
    emit = demo.DemoTelemetry(SimpleNamespace(record=lambda k, d: rows.append((k, d))))
    emit("execution_started", {"step": 0, "decision": {"token": "STOP", "source": "fallback"},
                                "fallback_reason": "decision_expired"})
    assert rows[0][0] == "execution_started"
    assert "decision_expired" in capsys.readouterr().out
