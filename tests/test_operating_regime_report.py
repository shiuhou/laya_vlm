from copy import deepcopy
import json

import numpy as np
import pytest

from embodied_runtime.experiments.operating_regime_report import compare_probes, probe_metrics, summarize
from embodied_runtime.experiments.records import RunRecorder


def probe(token="STOP", *, x=0., observed=None, duration=.4, variant="native", repeat=0):
    telemetry = {"sim_time": 0., "tcp_fk_m": [0., 0., 0.], "tcp_observed_m": [0., 0., 0.],
                 "orientation_fk": np.eye(3).tolist(), "gripper_width_joint_m": .08, "gripper_command": -1.}
    after = {**telemetry, "sim_time": duration, "tcp_fk_m": [x, 0., 0.],
             "tcp_observed_m": [x if observed is None else observed, 0., 0.]}
    features = {"remaining_open_mm": 100., "moving_contact": False, "obstacle_contact": False, "success": False}
    return {"context_id": "ctx", "token": token, "variant": variant, "repeat": repeat, "before": telemetry,
            "after": after, "features_before": features, "features_after": {**features, "remaining_open_mm": 95.},
            "execution": {"delta_m": [x, 0., 0.], "environment_step_count": 8, "low_level_step_count": 200,
                          "execution_contract_violation": False, "execution_contract_reason": [],
                          "low_level_commands": [[0., 0., 0., 0., 0., 0., -1.]]},
            "sim_state_after": [duration, x], "endpoint_context_id": str(x), "traced": True,
            "control_trace": [{"inner": {"physics_steps": 25, "clipped_steps_by_joint": [0, 1, 2]}}],
            "restore": {"context_matches": True, "sim_max_error": 0.}, "not_supplied_to_model": True}


def fixture(path, probes, *, terminate=True, starts=(), failure=None):
    rec = RunRecorder(path, {}, {"run_id": path.name})
    rec.record("regime_boundary", {"context_id": "ctx", "physical": {"task": "top_drawer", "init_state_id": 0,
               "environment_step": 144}, "phases": ["contact"], "telemetry": {}})
    for item in starts:
        rec.record("regime_probe_started", item)
    begun = {(p["token"], p["variant"], p["repeat"]) for p in starts}
    for item in probes:
        key = item["token"], item["variant"], item["repeat"]
        if key not in begun:
            rec.record("regime_probe_started", {k: item[k] for k in ("context_id", "token", "variant", "repeat")})
            begun.add(key)
        rec.record("regime_probe", item)
    if failure:
        rec.record("failure", failure)
    if terminate:
        rec.record("termination", {"reason": "operating_regime_complete"})
    rec.close()
    return path


def test_observed_vs_fk_nominal_rotation_and_clipping():
    p = probe("MV_FWD", x=.01, observed=.012)
    result = probe_metrics(p)
    assert result["fk_nominal_translation_error_m"] == 0.
    assert result["fk_vs_observed_delta_error_m"] == pytest.approx(.002)
    assert result["torque_clipped_steps_by_joint"] == [0, 1, 2]
    assert result["torque_clipped_joint_steps_total"] == 3
    assert result["closure_mm"] == 5.
    p["token"] = "ROTATE_CCW"
    a = np.radians(10)
    p["after"]["orientation_fk"] = [[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]
    result = probe_metrics(p)
    assert result["fk_rotation_deg"] == pytest.approx(10.)
    assert result["fk_nominal_rotation_error_deg"] == pytest.approx(0., abs=1e-5)


def test_stop_relative_only_equal_duration_and_step_count(tmp_path):
    stop, shorter, same = probe(), probe("MV_FWD", x=.01, duration=.05), probe("RELEASE")
    same["features_after"]["remaining_open_mm"] = 93.
    out = summarize(fixture(tmp_path / "raw", [stop, shorter, same]))
    rows = {p["token"]: p for p in out["boundaries"][0]["probes"]}
    assert rows["MV_FWD"]["equal_horizon_to_native_stop"] is False
    assert rows["MV_FWD"]["closure_vs_native_stop_mm"] is None
    assert rows["RELEASE"]["closure_vs_native_stop_mm"] == 2.
    assert not out["evidence_complete"]
    assert out["boundaries"][0]["missing_expected_probes"]


def test_exact_command_and_sim_alias_both_required():
    a, b = probe(), probe("RELEASE")
    out = compare_probes(a, b, probe_metrics(a), probe_metrics(b))
    assert out["exact_command_and_sim_alias"] is True
    b["execution"]["low_level_commands"][0][-1] = 1.
    out = compare_probes(a, b, probe_metrics(a), probe_metrics(b))
    assert out["exact_sim_endpoint_equal"] is True
    assert out["exact_command_and_sim_alias"] is False


def test_near_aliases_are_pairwise_not_transitive(tmp_path):
    values = [probe("STOP", x=0.), probe("RELEASE", x=.000075), probe("GRASP", x=.000150)]
    out = summarize(fixture(tmp_path / "raw", values))
    pairs = out["boundaries"][0]["native_pairwise_comparisons"]
    near = {(p["a"][0], p["b"][0]): p["near_endpoint_telemetry_only"] for p in pairs}
    assert near[("STOP", "RELEASE")] and near[("RELEASE", "GRASP")]
    assert not near[("STOP", "GRASP")]
    assert "not transitive" in out["near_alias_scope"]


def test_missing_telemetry_and_untraced_repetition_are_unknown_not_zero():
    p = probe(repeat=1)
    p["control_trace"] = []
    p["traced"] = False
    p["before"].pop("tcp_fk_m")
    p["after"].pop("sim_time")
    p["execution"].pop("low_level_commands")
    result = probe_metrics(p)
    for field in ("fk_delta_m", "fk_displacement_m", "duration_s", "torque_clipped_steps_by_joint", "command_id"):
        assert result[field] is None
    assert compare_probes(p, p, result, result)["near_endpoint_telemetry_only"] is None


def test_diagnostics_separate_native_and_missing_outcomes_preserved(tmp_path):
    native, diagnostic = probe(), probe(variant="reanchor_orientation", x=.003)
    diagnostic["restore"]["context_matches"] = False
    missing = {"context_id": "ctx", "token": "MV_UP", "variant": "native", "repeat": 0}
    directory = fixture(tmp_path / "raw", [native, diagnostic], terminate=False, starts=[missing],
                        failure={"category": "regime_probe_error", "detail": "injected"})
    with (directory / "episodes.jsonl").open("ab") as stream:
        stream.write(b'{"unfinished":')
    out = summarize(directory)
    assert out["native_probe_count"] == 1
    assert len(out["boundaries"][0]["stop_diagnostic_comparisons"]) == 1
    categories = {f["category"] for f in out["failures"]}
    assert {"incomplete_record", "run_incomplete", "probe_outcome_unknown", "restore_not_verified", "regime_probe_error"} <= categories


def test_hash_corruption_and_duplicate_probe_are_rejected(tmp_path):
    directory = fixture(tmp_path / "corrupt", [probe()])
    path = directory / "episodes.jsonl"
    lines = path.read_text().splitlines()
    row = json.loads(lines[-1])
    row["data"]["reason"] = "fabricated"
    lines[-1] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="integrity"):
        summarize(directory)
    with pytest.raises(ValueError, match="duplicate completed"):
        summarize(fixture(tmp_path / "duplicate", [probe(), deepcopy(probe())]))


def test_empty_terminal_log_and_failed_restore_cannot_be_complete(tmp_path):
    rec = RunRecorder(tmp_path / "empty", {}, {"run_id": "empty"})
    rec.record("termination", {"reason": "operating_regime_complete"})
    rec.close()
    assert not summarize(rec.output)["evidence_complete"]
    from embodied_runtime.experiments.operating_regime_report import TOKENS
    probes = [probe(token) for token in TOKENS] + [probe(repeat=1)]
    probes += [probe(variant=v) for v in ("reanchor_orientation", "fk_feedback", "both")]
    assert summarize(fixture(tmp_path / "complete", probes))["evidence_complete"]
    probes[0]["restore"]["context_matches"] = False
    assert not summarize(fixture(tmp_path / "unrestored", probes))["evidence_complete"]


@pytest.mark.parametrize("error", ["intent", "boundary", "duplicate_intent"])
def test_completed_probes_require_unique_prior_intent_and_boundary(tmp_path, error):
    rec = RunRecorder(tmp_path / error, {}, {"run_id": error})
    p = probe()
    if error != "boundary":
        rec.record("regime_boundary", {"context_id": "ctx", "physical": {}, "phases": [], "telemetry": {}})
    if error != "intent":
        rec.record("regime_probe_started", p)
    if error == "duplicate_intent":
        rec.record("regime_probe_started", p)
    rec.record("regime_probe", p)
    rec.close()
    with pytest.raises(ValueError, match="duplicate regime probe intent|preceding"):
        summarize(rec.output)
