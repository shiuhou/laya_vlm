import json
import os
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.adapters.libero import LiberoWorldBackend
from embodied_runtime.adapters.physics_preview import PhysicsPreviewCandidateBuilder, VisionCandidateBuilder
from embodied_runtime.experiments.records import RunRecorder, load_records, package_directory, summarize
from embodied_runtime.runtime import Runtime
from embodied_runtime.runtime_core import FakeBackend, RuleProvider
from embodied_runtime.vision import LocateAnythingProvider, position_covariance_from_depth


def recorder(path):
    return RunRecorder(path, {"task": "fixture", "seed": 1, "method": "fixture", "oracle": False}, {"run_id": "fixture"})


def test_namespace_package_provenance_path(tmp_path):
    assert package_directory(SimpleNamespace(__file__=None, __path__=[str(tmp_path)])) == tmp_path
    assert package_directory(SimpleNamespace(__file__=str(tmp_path / "__init__.py"))) == tmp_path


def test_durable_chain_regenerates_tables_and_rejects_corruption(tmp_path):
    out = tmp_path / "run"
    rec = recorder(out)
    runtime = Runtime("ep", RuleProvider(), FakeBackend(), event_sink=rec.record)
    runtime.step(0)
    rec.record("termination", {"reason": "action_budget"})
    rec.close()
    assert summarize(out) == {"completed_actions": 1, "failure_events": 0, "terminated": True}
    before = (out / "summary.csv").read_bytes()
    summarize(out)
    assert (out / "summary.csv").read_bytes() == before
    rows, _ = load_records(out / "episodes.jsonl")
    assert [r["kind"] for r in rows] == ["run_start", "snapshot", "decision", "execution_started", "action", "termination"]
    raw = (out / "episodes.jsonl").read_text().replace('"task": "fixture"', '"task": "corrupted"', 1)
    (out / "episodes.jsonl").write_text(raw)
    with pytest.raises(ValueError, match="integrity"):
        summarize(out)


@pytest.mark.parametrize("case,reason", [("expired", "decision_expired"), ("wrong_id", "decision_invalid"),
                                        ("invalid", "decision_not_allowed")])
def test_original_invalid_decision_preserved_and_stop_is_explicit(tmp_path, case, reason):
    class Provider(RuleProvider):
        def decide(self, snapshot):
            d = super().decide(snapshot)
            return replace(d, **({"token": "NOT_A_TOKEN"} if case == "invalid" else
                                 {"input_snapshot_id": "wrong"} if case == "wrong_id" else {}))
    rec = recorder(tmp_path / "run")
    runtime = Runtime("ep", Provider(), FakeBackend(), event_sink=rec.record,
                      sim_clock=lambda: 1 if case == "expired" else 0)
    result = runtime.step(0)
    rec.close()
    assert result["decision_invalid_reason"] == reason
    assert result["result"]["token"] == "STOP"
    assert result["raw_decision"].source == "rule"
    rows, _ = load_records(rec.output / "episodes.jsonl")
    raw = next(r["data"]["decision"] for r in rows if r["kind"] == "decision")
    assert raw["source"] == "rule"
    intent = next(r["data"] for r in rows if r["kind"] == "execution_started")
    assert intent["fallback_reason"] == reason
    assert intent["decision"]["source"] == "fallback"


def test_model_and_environment_exceptions_leave_completed_actions(tmp_path):
    class Provider(RuleProvider):
        calls = 0
        def decide(self, snapshot):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("injected model exception")
            return super().decide(snapshot)
    rec = recorder(tmp_path / "run")
    rt = Runtime("ep", Provider(), FakeBackend(), event_sink=rec.record)
    rt.step(0)
    with pytest.raises(RuntimeError, match="injected"):
        rt.step(.1)
    rec.close()
    assert summarize(rec.output)["completed_actions"] == 1
    assert "model_error" in (rec.output / "failures.csv").read_text()
    assert "run_incomplete" in (rec.output / "failures.csv").read_text()


def test_hard_exit_and_truncated_tail_recovery(tmp_path):
    out = tmp_path / "killed"
    code = '''
import os, sys
from embodied_runtime.experiments.records import RunRecorder
from embodied_runtime.runtime import Runtime
from embodied_runtime.runtime_core import FakeBackend, RuleProvider
r = RunRecorder(sys.argv[1], {}, {"run_id": "hard-exit"})
t = Runtime("ep", RuleProvider(), FakeBackend(), event_sink=r.record)
t.step(0)
r.record("execution_started", {"step": 1})
os._exit(9)
'''
    result = subprocess.run([sys.executable, "-c", code, str(out)], env=os.environ.copy())
    assert result.returncode == 9
    assert summarize(out)["completed_actions"] == 1
    with (out / "episodes.jsonl").open("ab") as stream:
        stream.write(b'{"partial":')
    summary = summarize(out)
    assert summary["failure_events"] == 3
    failures = (out / "failures.csv").read_text()
    assert "execution_outcome_unknown" in failures
    assert "incomplete_record" in failures


def test_privilege_boundary_and_robot_only_proprioception():
    def forbidden(*args):
        raise AssertionError("privileged access")
    world = SimpleNamespace(features=forbidden, predict_all=forbidden,
                            obs={"robot0_eef_pos": [0, 0, 1], "robot0_gripper_qpos": [.04, -.04]})
    backend = LiberoWorldBackend(world)
    proprio = backend.proprioception()
    assert proprio["gripper_width_m"] == pytest.approx(.08)
    rt = Runtime("ep", RuleProvider(), FakeBackend(), VisionCandidateBuilder(), oracle=False)
    rt.observe("proprio", 0, proprio)
    assert rt.store.snapshot(0).continuous["tcp_pos_world_m"] == [0, 0, 1]
    with pytest.raises(ValueError, match="forbidden"):
        rt.observe("oracle", 0, {"object_pose": [1, 2, 3]})
    with pytest.raises(ValueError, match="unknown proprioception"):
        rt.observe("proprio", 0, {"object_pose": [1, 2, 3]})
    with pytest.raises(ValueError, match="requires a visual"):
        Runtime("ep", RuleProvider(), backend, PhysicsPreviewCandidateBuilder(world), oracle=False)


def test_covariance_is_uncalibrated_rotated_and_positive():
    k = {"fx": 100, "fy": 200, "cx": 5, "cy": 5}
    c = position_covariance_from_depth(5, 5, 1, (0, 0, 10, 10), {"std_m": 0, "mad_m": 0}, k)
    assert np.allclose(c, np.diag([1e-4, 2.5e-5, 4e-6]))
    transform = np.eye(4)
    transform[:3, :3] = [[0, -1, 0], [1, 0, 0], [0, 0, 1]]
    provider = LocateAnythingProvider(lambda *_: {"boxes": [[0, 0, 10, 10]], "score": 1}, k)
    event = provider.observe(np.zeros((10, 10, 3)), np.ones((10, 10)), "drawer",
                             episode_id="ep", source_seq=1, capture_sim_time=0,
                             camera_to_world_matrix=transform)
    expected = transform[:3, :3] @ c @ transform[:3, :3].T
    assert np.allclose(event.value["position_covariance_m2"], expected)
    assert np.linalg.eigvalsh(expected).min() > 0
    assert event.value["position_covariance_calibrated"] is False


def test_runner_startup_failure_preserved(tmp_path, monkeypatch):
    from embodied_runtime.experiments import run_libero
    args = run_libero.parser().parse_args(["--output", str(tmp_path), "--run-id", "broken"])
    def broken(*args, **kwargs):
        raise RuntimeError("injected environment error")
    monkeypatch.setattr(run_libero.LiberoWorldBackend, "from_task", broken)
    with pytest.raises(RuntimeError, match="injected"):
        run_libero.run_episode(args)
    rows, _ = load_records(tmp_path / "broken" / "episodes.jsonl")
    assert any(r["kind"] == "termination" for r in rows)
    assert "environment_startup" in (tmp_path / "broken" / "failures.csv").read_text()
    json.loads((tmp_path / "broken" / "manifest.json").read_text())


def test_oracle_preview_explicitly_privileged_and_uses_retained_command(monkeypatch):
    policy = SimpleNamespace(contracts=lambda *a, **kw: ({"valid": {"x+10mm": {}}}, {}))
    monkeypatch.setitem(sys.modules, "jev_libero.policy", policy)
    calls = []
    world = SimpleNamespace(config={}, predict_all=lambda grip: (calls.append(grip) or {}, {}))
    builder = PhysicsPreviewCandidateBuilder(world, grip_command=lambda: 1.)
    builder.build(None)
    assert calls == [1.]
    assert builder.last_diagnostics["oracle"] is True
    assert builder.last_diagnostics["privileged_state_used"] is True


def test_execution_exception_preserves_unknown_physical_outcome(tmp_path):
    class BrokenBackend(FakeBackend):
        def apply_delta(self, *args, **kwargs):
            raise RuntimeError("partial actuation")
    rec = recorder(tmp_path / "run")
    rt = Runtime("ep", RuleProvider(), BrokenBackend(), event_sink=rec.record)
    with pytest.raises(RuntimeError, match="partial"):
        rt.step(0)
    rec.close()
    assert summarize(rec.output)["completed_actions"] == 0
    failures = (rec.output / "failures.csv").read_text()
    assert "execution_outcome_unknown" in failures
    assert "environment_error" in failures
