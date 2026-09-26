from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime.experiments import current_motor_replication as replication
from embodied_runtime.experiments.reference_model_diagnostic import payload_id


def source_fixture(count=3, objective="advance_target"):
    order = [f"primitive-{i}" for i in range(count)]
    criteria = dict.fromkeys(reversed(order), "saved description")
    saved = {"state": "original saved model input", "questions": {"action": {
        "type": "choice", "instructions": "original instructions", "criteria": criteria}},
        "option_order": order, "candidate_count": count, "forced_singleton": False,
        "model_called": True, "effect_source": "oracle_sim", "privileged": True,
        "objective_routing": {"motor_pool": order}, "local_objective": objective,
        "pool_source": "one_step", "snapshot_id": "snapshot",
        "audit": {"available": True, "truncated": False, "questions": {"action": {
            "effective_input_ids": [1, 2, 3], "option_markers": list(range(count))}}}}
    response = {"raw_response": {"answers": {"action": {"choice": order[0],
                                                        "probabilities": dict.fromkeys(order, 1/count)}}},
                "forward_traces": [{"input_ids": [[1, 2, 3]], "option_markers": [list(range(count))],
                                    "raw_option_logits": [[0.]*count]}]}
    outcome = {"step": 9, "action": order[0], "comparison": {"passed": True}}
    preview = {"objective_routing": saved["objective_routing"], "predictions": {
        token: {"closing_mm": float(i), "geometry_approach_mm": 1., "peak_obstacle_force_N": 0.,
                "steps": 8, "after": {"moving_contact": True, "success": False}}
        for i, token in enumerate(order)}}
    return saved, response, outcome, preview


def test_native_fixture_restores_exact_order_without_new_wording():
    source = source_fixture(25)
    before = deepcopy(source)
    fixture = replication.make_fixture(*source, {"reference_model_input": "id"})
    assert source == before
    assert fixture["state"] == source[0]["state"]
    assert fixture["questions"] == source[0]["questions"]
    assert list(fixture["questions"]["action"]["criteria"]) == source[0]["option_order"]
    assert len(fixture["option_order"]) == 25
    assert fixture["payload_id"] == payload_id(fixture["state"], fixture["questions"])
    assert fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] is None


@pytest.mark.parametrize("mutation", [
    lambda s: s[0].update(candidate_count=2),
    lambda s: s[0].update(forced_singleton=True),
    lambda s: s[0].update(privileged=False),
    lambda s: s[0]["audit"].update(truncated=True),
    lambda s: s[1]["forward_traces"][0].update(input_ids=[[99]]),
    lambda s: s[1]["forward_traces"][0].update(option_markers=[[99]]),
    lambda s: s[2].update(action="not the selected action"),
])
def test_source_provenance_and_token_inconsistencies_rejected(mutation):
    source = source_fixture()
    mutation(source)
    with pytest.raises(ValueError):
        replication.make_fixture(*source, {})


def test_selection_is_chronological_and_independent_of_model_choices():
    objectives = ["approach_target"]*3 + ["advance_target"]*3 + ["reposition"]
    inputs = [{"snapshot_id": str(i), "local_objective": objective, "candidate_count": 3,
               "pool_source": "lookahead" if i == 6 else "one_step"} for i, objective in enumerate(objectives)]
    outcomes = [{"snapshot_id": str(i), "genuine_laya_decision": True, "step": i,
                 "action": "arbitrary"} for i in range(7)]
    assert replication.select_boundaries(inputs, outcomes) == [0, 1, 3, 4, 6]


def test_immediate_comparison_keeps_controls_force_contact_and_success():
    source = source_fixture(5)
    predictions = source[3]["predictions"]
    predictions["primitive-2"]["peak_obstacle_force_N"] = 1.
    predictions["primitive-3"]["steps"] = 7
    predictions["primitive-4"]["after"]["moving_contact"] = False
    fixture = replication.make_fixture(*source, {})
    result = replication.immediate_comparison(fixture, "primitive-0")
    assert result["greater_closure_with_no_worse_reported_fields"] == ["primitive-1"]
    assert result["strict_argmax_is_not_a_correctness_label"]
    assert len(result["effects"]) == 5
    assert not result["new_execution"]


def test_witness_remains_hypothetical_not_a_new_executed_sequence():
    source = source_fixture(objective="reposition")
    source[0]["pool_source"] = "lookahead"
    witness = {"second_input": "z-10mm", "net_progress": 3.}
    source[3]["predictions"]["primitive-0"]["reposition_witness"] = witness
    fixture = replication.make_fixture(*source, {})
    result = replication.immediate_comparison(fixture, "primitive-0")
    assert result["witness_is_not_executed_sequence"]
    assert result["chosen_effect"]["hypothetical_witness_not_executed"] == witness


@pytest.mark.parametrize("count", [7, 16, 25])
def test_raw_validator_supports_native_cardinalities(count):
    fixture = replication.make_fixture(*source_fixture(count), {})
    logits = np.arange(count, dtype=float)/count
    probabilities = np.exp(logits-logits.max())
    probabilities /= probabilities.sum()
    intent = {"repeat": 0, "call_id": "call", "input_encoding": fixture["source"]["archived_audit"],
              "temperature": {"configured": 1., "effective": 1.}, "device_before": "cpu", "dtype_before": "float32"}
    response = deepcopy(fixture["source"]["archived_response"])
    response.update(actual_device="cpu", actual_dtype="float32")
    response["raw_response"]["answers"]["action"] = {
        "choice": fixture["option_order"][-1], "probabilities": dict(zip(fixture["option_order"], probabilities))}
    response["forward_traces"][0]["raw_option_logits"] = [logits.tolist()]
    result = replication.validate_response(fixture, intent, response)
    assert result["choice"] == fixture["option_order"][-1]
    response["raw_response"]["answers"]["action"]["choice"] = fixture["option_order"][0]
    with pytest.raises(ValueError, match="scorer"):
        replication.validate_response(fixture, intent, response)


def test_checkpoint_source_rejected_before_model_load(tmp_path):
    (tmp_path / "episodes.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="frozen"):
        replication.frozen_source(tmp_path)


def test_real_source_design_and_registered_comparison_when_available():
    source = Path("runs/privileged-reference/local-objective-task-adapter-episode-01")
    if not source.exists():
        pytest.skip("local archived evidence unavailable")
    fixtures, _, _ = replication.frozen_source(source)
    assert [f["source"]["step"] for f in fixtures] == [0, 1, 9, 10, 87]
    assert [len(f["option_order"]) for f in fixtures] == [7, 7, 25, 16, 25]
    for fixture in fixtures[2:4]:
        result = replication.immediate_comparison(fixture, "open")
        assert "y-40mm" in result["greater_closure_with_no_worse_reported_fields"]
        assert result["effects"]["y-40mm"]["closure_mm"] > result["chosen_effect"]["closure_mm"]
