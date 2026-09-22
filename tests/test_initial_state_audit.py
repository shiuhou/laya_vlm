from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import audit_initial_states as audit
from embodied_runtime.experiments.records import RunRecorder, load_records
from embodied_runtime.runtime_core import _sha256_json


def features(gap=30., remaining=150., contact=False, success=False):
    return {"distance_to_moving_geometry_mm": gap, "remaining_open_mm": remaining,
            "moving_contact": contact, "success": success}


def test_phase_rules_are_explicit_overlapping_evaluator_strata():
    assert audit.phases(features(gap=20.)) == ["far"]
    assert audit.phases(features(gap=5.)) == ["approach"]
    assert audit.phases(features(gap=4.99)) == ["near_contact"]
    assert audit.phases(features(gap=0., remaining=5., contact=True), features(remaining=6.)) == [
        "contact", "progressing", "near_completion"]
    assert audit.phases(features(gap=0., remaining=-1., success=True)) == ["near_contact", "success"]


def fake_backend(monkeypatch, *, offset=0., fail_at=None):
    backend = SimpleNamespace(index=0, _grip_cmd=-1., world=SimpleNamespace())
    def evidence(backend, unit, step):
        result = {**unit, "environment_step": step, "sim_state": [backend.index + offset],
                  "sim_time": step * .05, "features": features(gap=30. - step * 10., remaining=150. - step)}
        return {**result, "physical_state_id": _sha256_json(result)}
    def step(action):
        if fail_at == backend.index:
            raise RuntimeError("injected environment error")
        backend.index += 1
        return {}, 0., False, {}
    monkeypatch.setattr(audit, "physical_evidence", evidence)
    backend.world.env = SimpleNamespace(step=step)
    return backend


def trajectory():
    return {"actions": np.array([[0, 0, 0, 0, 0, 0, -1], [0, 0, 0, 0, 0, 0, 1]]),
            "states_before": np.array([[0.], [1.]]), "final_state": np.array([2.])}


def test_source_identity_archive_agreement_and_all_controls(monkeypatch, tmp_path):
    backend = fake_backend(monkeypatch)
    root = tmp_path / "run"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    result = audit.audit_unit(backend, recorder, {"init_state_id": 0, "seed": 1}, trajectory(), check_archive=True)
    recorder.record("termination", {"reason": "test_complete"})
    recorder.close()
    assert result["physical_states"] == 3
    assert result["controls"] == 2
    assert result["max_archive_state_error"] == 0
    assert backend._grip_cmd == 1
    rows, diagnostics = load_records(root / "episodes.jsonl")
    assert not diagnostics
    assert [r["kind"] for r in rows][1:6] == ["collection_state", "collection_control_started",
                                                         "collection_state", "collection_control_started", "collection_state"]
    recovered = audit.summarize(root)
    assert recovered["terminated"]
    assert recovered["initial_states"][0]["completed"]
    assert recovered["initial_states"][0]["phase_coverage"] == {"far": 2, "approach": 1, "progressing": 2}


def test_other_initial_states_do_not_assert_archived_identity(monkeypatch, tmp_path):
    backend = fake_backend(monkeypatch, offset=100.)
    recorder = RunRecorder(tmp_path / "run", {}, {"run_id": "test"})
    result = audit.audit_unit(backend, recorder, {"init_state_id": 1, "seed": 1}, trajectory(), check_archive=False)
    recorder.close()
    assert result["max_archive_state_error"] is None
    assert result["controls"] == 2


def test_source_mismatch_preserves_observed_state_before_rejection(monkeypatch, tmp_path):
    backend = fake_backend(monkeypatch, offset=.1)
    root = tmp_path / "run"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    with pytest.raises(RuntimeError, match="source trajectory state mismatch"):
        audit.audit_unit(backend, recorder, {"init_state_id": 0}, trajectory(), check_archive=True)
    recorder.close()
    rows, _ = load_records(root / "episodes.jsonl")
    assert rows[-1]["kind"] == "collection_state"
    assert rows[-1]["data"]["replay_state_max_error"] == .1
    assert backend.index == 0


def test_environment_exception_retains_completed_states_and_last_intent(monkeypatch, tmp_path):
    backend = fake_backend(monkeypatch, fail_at=1)
    root = tmp_path / "run"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    with pytest.raises(RuntimeError, match="injected environment error"):
        audit.audit_unit(backend, recorder, {"init_state_id": 0}, trajectory(), check_archive=True)
    recorder.close()
    rows, _ = load_records(root / "episodes.jsonl")
    assert rows[-1]["kind"] == "collection_control_started"
    recovered = audit.summarize(root)
    assert not recovered["terminated"]
    assert not recovered["initial_states"][0]["completed"]
    assert recovered["initial_states"][0]["physical_states"] == 2


def recorded_fixture(monkeypatch, root):
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    audit.audit_unit(fake_backend(monkeypatch), recorder, {"init_state_id": 0, "seed": 1},
                     trajectory(), check_archive=True)
    recorder.record("termination", {"reason": "test_complete"})
    recorder.close()
    return load_records(root / "episodes.jsonl")[0]


def rerecord(root, rows):
    """Build a valid outer hash chain around deliberately inconsistent data."""
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    for row in rows[1:]:
        recorder.record(row["kind"], row["data"])
    recorder.close()


@pytest.mark.parametrize("field,value", [
    ("phase_coverage", {"far": 999}), ("physical_states", 999), ("controls", 999),
    ("final_remaining_open_mm", 999.), ("final_success", True),
    ("initial_physical_state_id", "bad"), ("final_physical_state_id", "bad"),
    ("max_archive_state_error", 999.),
])
def test_rehashed_termination_cache_corruption_is_rejected(monkeypatch, tmp_path, field, value):
    rows = recorded_fixture(monkeypatch, tmp_path / "source")
    next(r["data"] for r in rows if r["kind"] == "initial_state_termination")[field] = value
    rerecord(tmp_path / "changed", rows)
    with pytest.raises(ValueError, match="cached termination"):
        audit.summarize(tmp_path / "changed")


def test_phase_and_terminal_caches_can_be_absent(monkeypatch, tmp_path):
    rows = recorded_fixture(monkeypatch, tmp_path / "source")
    expected = audit.summarize(tmp_path / "source")
    for row in rows:
        if row["kind"] == "collection_state":
            row["data"].pop("phases")
        if row["kind"] == "initial_state_termination":
            row["data"] = {key: row["data"][key] for key in ("init_state_id", "seed", "reason")}
    rerecord(tmp_path / "changed", rows)
    assert audit.summarize(tmp_path / "changed") == expected


@pytest.mark.parametrize("kind,field,value,match", [
    ("collection_state", "phases", ["success"], "cached phases"),
    ("collection_state", "physical_state_id", "bad", "content hash"),
    ("collection_state", "environment_step", 2, "out of order"),
    ("collection_control_started", "physical_state_id", "bad", "control intent"),
    ("collection_control_started", "seed", 99, "source identity"),
])
def test_rehashed_state_and_source_inconsistencies_are_rejected(monkeypatch, tmp_path, kind, field, value, match):
    rows = recorded_fixture(monkeypatch, tmp_path / "source")
    next(r["data"] for r in rows if r["kind"] == kind)[field] = value
    rerecord(tmp_path / "changed", rows)
    with pytest.raises(ValueError, match=match):
        audit.summarize(tmp_path / "changed")
