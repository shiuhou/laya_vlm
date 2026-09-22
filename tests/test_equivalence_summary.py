from copy import deepcopy
from dataclasses import asdict, replace
import json

import numpy as np
import pytest

from embodied_runtime.decision_interface import project_belief, project_oracle, shared_atomic_candidates
from embodied_runtime.experiments.equivalence import make_pair, paired_inputs
from embodied_runtime.experiments.records import RunRecorder
from embodied_runtime.experiments.summarize_equivalence import summarize_equivalence
from embodied_runtime.runtime_core import BeliefSnapshot, RuleProvider, _sha256_json


def paired_state():
    belief = BeliefSnapshot("episode", 2, .5, {"tcp_pos_world_m": [0., 0., 1.],
        "vision:drawer:position_world_m": [.2, 0., 1.]}, {}, {"instruction": "close the drawer"},
        validity={"drawer": {"geometry_age_s": .1, "geometry_valid": True}})
    perceptual = project_belief(belief, "drawer")
    oracle = project_oracle(perceptual, {"source_id": "physical", "target_position_m": [-.2, 0., 1.],
        "position_definition": "moving_collision_geometry_world_aabb_center", "remaining_open_mm": 120.})
    candidates = shared_atomic_candidates()
    natural = tuple(replace(c, feasible=c.token == "STOP") for c in candidates)
    return make_pair(oracle, perceptual, candidates, natural_perceptual=natural,
        physical={"sim_time": .5, "physical_state_id": "physical", "task": "top_drawer", "init_state_id": 3, "seed": 1})


def decision_record(pair, branch, repeat):
    inp = paired_inputs(pair)[0 if branch == "oracle" else 1]
    return {"pair_id": pair["pair_id"], "branch": branch, "repeat": repeat, "provider": "RuleProvider",
            "decision": asdict(RuleProvider().decide(inp)),
            "presentation_version": "compact-v0.1",
            "model_input_id": _sha256_json({"state": inp.provider_input(), "question": inp.model_questions()}),
            "latency_ms": 1.5, "choice_allowed": True}


def write_run(path, pair, decisions, *, terminate=True, derived=None):
    recorder = RunRecorder(path, {"provider": "rule", "repeats": 2}, {"run_id": "summary-test"})
    recorder.record("paired_state", pair)
    for data in decisions:
        recorder.record("equivalence_decision", data)
    if derived is not None:
        recorder.record("equivalence_diagnostic", derived)
    if terminate:
        recorder.record("termination", {"reason": "smoke_complete"})
    recorder.close()


def test_summary_reproduces_raw_decisions_not_saved_diagnostics(tmp_path):
    pair = paired_state()
    records = [decision_record(pair, branch, repeat) for repeat in range(2) for branch in ("oracle", "perceptual")]
    path = tmp_path / "run"
    write_run(path, pair, records, derived={"paired_comparisons": [{"top1_agreement": True, "js_divergence_nats": 0}]})
    summary = summarize_equivalence(path)
    assert summary["complete_comparisons"] == 2
    assert summary["incomplete_comparisons"] == 0
    assert summary["decision_count"] == 4
    row = summary["comparisons"][0]
    assert row["top1_agreement"] is False
    assert row["js_divergence_nats"] == pytest.approx(np.log(2))
    assert row["oracle_margin"] == 1
    assert row["oracle_latency_ms"] == row["perceptual_latency_ms"] == 1.5
    assert row["natural_perceptual_feasible_count"] == 1
    assert row["natural_oracle_candidate_count"] is None
    assert row["natural_candidate_set_agreement"] is None
    assert row["perceptual_geometry_age_s"] == .1
    assert row["init_state_id"] == 3
    assert row["position_error_m"] is None  # incomparable target definitions, not measured error
    assert all(s["max_probability_difference"] == 0 for s in summary["stability"])
    before = [(path / name).read_bytes() for name in ("equivalence_summary.json", "equivalence_summary.csv")]
    assert summarize_equivalence(path) == summary
    assert before == [(path / name).read_bytes() for name in ("equivalence_summary.json", "equivalence_summary.csv")]
    assert json.loads(before[0])["purpose"] == "descriptive_smoke_diagnostics_not_statistical_evidence"


def test_missing_outputs_and_interruption_are_not_decisions(tmp_path):
    pair = paired_state()
    path = tmp_path / "run"
    write_run(path, pair, [decision_record(pair, "oracle", 0)], terminate=False)
    summary = summarize_equivalence(path)
    assert not summary["terminated"]
    assert summary["complete_comparisons"] == 0 and summary["incomplete_comparisons"] == 2
    assert summary["comparisons"][0]["missing_branches"] == "perceptual"
    assert summary["comparisons"][1]["missing_branches"] == "oracle,perceptual"
    assert all(row["top1_agreement"] is None for row in summary["comparisons"])
    assert all(not row["repeatability_measured"] for row in summary["stability"])
    assert all(row["max_probability_difference"] is None for row in summary["stability"])
    assert any(d["category"] == "run_incomplete" for d in summary["diagnostics"])


def test_missing_distributions_do_not_become_zero_probabilities(tmp_path):
    pair = paired_state()
    records = [decision_record(pair, branch, repeat) for repeat in range(2) for branch in ("oracle", "perceptual")]
    records[1]["decision"]["probabilities"] = {}
    path = tmp_path / "run"
    write_run(path, pair, records)
    summary = summarize_equivalence(path)
    assert summary["comparisons"][0]["top1_agreement"] is False
    assert summary["comparisons"][0]["js_divergence_nats"] is None
    assert summary["stability"][1]["max_probability_difference"] is None


@pytest.mark.parametrize("change, message", [
    ({"model_input_id": "wrong"}, "model input identity"),
    ({"branch": "other"}, "unknown decision branch"),
    ({"branch": "perceptual"}, "decision input identity"),
    ({"choice_allowed": False}, "choice allowance"),
    ({"repeat": 2}, "exceeds resolved configuration"),
])
def test_malformed_decision_identity_rejected(tmp_path, change, message):
    pair = paired_state()
    data = {**decision_record(pair, "oracle", 0), **change}
    path = tmp_path / "run"
    write_run(path, pair, [data])
    with pytest.raises(ValueError, match=message):
        summarize_equivalence(path)


def test_duplicate_decision_observation_rejected(tmp_path):
    pair = paired_state()
    data = decision_record(pair, "oracle", 0)
    path = tmp_path / "run"
    write_run(path, pair, [data, deepcopy(data)])
    with pytest.raises(ValueError, match="duplicate decision observation"):
        summarize_equivalence(path)


def test_duplicate_pair_observation_rejected(tmp_path):
    pair = paired_state()
    path = tmp_path / "run"
    recorder = RunRecorder(path, {"provider": "rule", "repeats": 2}, {"run_id": "duplicate"})
    recorder.record("paired_state", pair)
    recorder.record("paired_state", pair)
    recorder.close()
    with pytest.raises(ValueError, match="duplicate paired-state observation"):
        summarize_equivalence(path)


def test_same_input_probability_variability_is_exposed(tmp_path):
    pair = paired_state()
    records = [decision_record(pair, branch, repeat) for repeat in range(2) for branch in ("oracle", "perceptual")]
    records[2]["decision"]["probabilities"]["MV_BACK"] = .75
    records[2]["decision"]["probabilities"]["STOP"] = .25
    path = tmp_path / "run"
    write_run(path, pair, records)
    summary = summarize_equivalence(path)
    assert summary["stability"][0]["unique_choices"] == ["MV_BACK"]
    assert summary["stability"][0]["max_probability_difference"] == .25
    assert summary["stability"][1]["max_probability_difference"] == 0


def test_legacy_audit_json_model_input_hashes_still_regenerate(tmp_path):
    pair = paired_state()
    records = [decision_record(pair, branch, repeat) for repeat in range(2) for branch in ("oracle", "perceptual")]
    for record in records:
        inp = paired_inputs(pair)[0 if record["branch"] == "oracle" else 1]
        record.pop("presentation_version")
        record["model_input_id"] = _sha256_json({
            "state": inp.provider_input(presentation_version="audit-json-v0"),
            "question": inp.model_questions(presentation_version="audit-json-v0")})
    path = tmp_path / "legacy"
    write_run(path, pair, records)
    summary = summarize_equivalence(path)
    assert summary["complete_comparisons"] == 2
    assert summary["comparisons"][0]["js_divergence_nats"] == pytest.approx(np.log(2))
    assert summary["comparisons"][0]["oracle_presentation_version"] == "audit-json-v0"
    assert summary["comparisons"][0]["oracle_input_truncation_status"] == "unknown"
    assert summary["input_encoding_decision_counts"] == {"unknown": 4, "truncated": 0, "not_truncated": 0}


def test_encoding_audit_exposes_truncation_without_inventing_old_audit(tmp_path):
    pair = paired_state()
    records = [decision_record(pair, branch, repeat) for repeat in range(2) for branch in ("oracle", "perceptual")]
    records[0]["input_encoding"] = {"available": True, "truncated": False}
    records[1]["input_encoding"] = {"available": True, "truncated": True}
    records[2]["input_encoding"] = {"available": False, "reason": "agent_has_no_tokenizer_config"}
    path = tmp_path / "run"
    write_run(path, pair, records)
    summary = summarize_equivalence(path)
    assert summary["comparisons"][0]["oracle_presentation_version"] == "compact-v0.1"
    assert summary["comparisons"][0]["oracle_input_truncation_status"] == "not_truncated"
    assert summary["comparisons"][0]["perceptual_input_truncation_status"] == "truncated"
    assert summary["comparisons"][1]["oracle_input_truncation_status"] == "unknown"
    assert summary["comparisons"][1]["perceptual_input_truncation_status"] == "unknown"
    assert summary["input_encoding_decision_counts"] == {"unknown": 2, "truncated": 1, "not_truncated": 1}


def test_consumed_token_stability_is_separate_from_model_payload_stability(tmp_path):
    pair = paired_state()
    records = [decision_record(pair, branch, repeat) for repeat in range(2) for branch in ("oracle", "perceptual")]
    for record, tokens in zip(records, ([1, 2], [3, 4], [1, 2], [3, 5])):
        record["input_encoding"] = {"available": True, "truncated": False, "questions": {
            "action": {"effective_input_id": _sha256_json(tokens), "effective_input_ids": tokens}}}
    path = tmp_path / "run"
    write_run(path, pair, records)
    summary = summarize_equivalence(path)
    assert summary["stability"][0]["effective_input_stable"] is True
    assert summary["stability"][1]["effective_input_stable"] is False
    assert all(row["effective_input_agreement"] is False for row in summary["comparisons"])
    records[0]["input_encoding"]["questions"]["action"]["effective_input_id"] = "corrupt"
    corrupt = tmp_path / "corrupt"
    write_run(corrupt, pair, records)
    with pytest.raises(ValueError, match="effective token identity mismatch"):
        summarize_equivalence(corrupt)


@pytest.mark.parametrize("corruption, message", [("hash", "pair content identity"), ("question", "question mismatch")])
def test_pair_identity_revalidated(tmp_path, corruption, message):
    pair = paired_state()
    if corruption == "hash":
        pair["shared_candidates"][0]["description"] = "corrupt"
    else:
        pair["question_id"] = "different-question"
        pair["pair_id"] = _sha256_json({k: v for k, v in pair.items() if k != "pair_id"})
    path = tmp_path / "run"
    write_run(path, pair, [])
    with pytest.raises(ValueError, match=message):
        summarize_equivalence(path)
