from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.experiments import interface_search as search
from embodied_runtime.experiments.reference_model_diagnostic import payload_id
from embodied_runtime.experiments.records import RunRecorder
from embodied_runtime.runtime_core import _sha256_json


def test_discovery_balances_directions_without_pruning_or_effects():
    fixtures = search.discovery()
    assert len(fixtures) == 41
    assert len({f["fixture_id"] for f in fixtures}) == 41
    for f in fixtures:
        assert len(f["option_order"]) == 11
        assert set(f["option_to_canonical"].values()) == set(search.TOKENS)
        assert f["effects_supplied"] is False
        assert f["payload_id"] == payload_id(f["state"], f["questions"])
        assert "scored_expected_tokens" not in str(f["state"])
    for c in search.CONDITIONS:
        assert {f["diagnostic_reference_not_model_input"]["scored_expected_tokens"][0]
                for f in fixtures if f["condition"] == c} == set(search.MOVE) | {"STOP"}


def test_geometry_reference_handles_stop_ties_and_invalids():
    assert search.expected([.03, 0, 0]) == ["MV_FWD"]
    assert search.expected([-.03, 0, 0]) == ["MV_BACK"]
    assert search.expected([.001, .001, .001]) == ["STOP"]
    assert set(search.expected([.03, .03, 0])) == {"MV_FWD", "MV_LEFT"}
    for bad in ([0, 0], [np.nan, 0, 0]):
        with pytest.raises(ValueError):
            search.expected(bad)


def test_presentations_and_reordering_change_no_physical_facts():
    d = [.02, -.01, .04]
    original = deepcopy(d)
    a = search.geometry_fixture(d, "spatial_english", "a")
    b = search.geometry_fixture(d, "spatial_english", "a", reverse=True)
    c = search.geometry_fixture(d, "spatial_neutral", "a")
    assert d == original
    assert a["state"] == b["state"] == c["state"]
    assert a["option_order"] == list(reversed(b["option_order"]))
    assert a["payload_id"] != b["payload_id"]
    assert a["diagnostic_reference_not_model_input"] == c["diagnostic_reference_not_model_input"]
    assert list(a["questions"]["action"]["criteria"].values()) == list(c["questions"]["action"]["criteria"].values())


def test_alias_shift_remaps_by_semantics_not_option_index():
    a = search.geometry_fixture([.02, 0, 0], "spatial_neutral", "a")
    b = search.transform(a, "shifted", shift=4, reverse=True)
    for key, desc in a["questions"]["action"]["criteria"].items():
        new = next(k for k, value in b["questions"]["action"]["criteria"].items() if value == desc)
        assert a["option_to_canonical"][key] == b["option_to_canonical"][new]
    assert a["state"] == b["state"]


def test_task_completion_uses_strict_installed_predicates_and_goal_contrasts():
    for qpos, close, opened in [(-.15, False, True), (-.14, False, False),
                               (0., False, False), (.002, True, False)]:
        for goal, done in [("close", close), ("open", opened)]:
            for presentation in ("numeric", "categorical"):
                f = search.completion_fixture(qpos, goal, presentation, "test")
                assert f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["DONE" if done else "CONTINUE"]
                assert len(f["option_order"]) == 2
                assert not f["effects_supplied"]
    a = search.completion_fixture(-.15, "open", "categorical", "test")
    b = search.completion_fixture(-.15, "close", "categorical", "test")
    assert a["state"] == b["state"]
    assert a["diagnostic_reference_not_model_input"] != b["diagnostic_reference_not_model_input"]


def test_policy_upper_bound_is_explicitly_identified():
    raw, ranked = search.rubric_fixtures([.012, .065, -.021], "test")
    assert raw["source"]["handwritten_policy_in_criteria"]
    assert not raw["source"]["answer_equivalent_projection"]
    assert ranked["source"]["answer_equivalent_projection"]
    assert "12 mm" in raw["state"]
    assert "12 mm" not in ranked["state"]
    assert raw["diagnostic_reference_not_model_input"] == ranked["diagnostic_reference_not_model_input"]


def test_observed_category_is_goal_independent_and_unknown_is_not_fabricated():
    a = search.goal_state_fixture("open", "open", "sentence")
    b = search.goal_state_fixture("open", "closed", "sentence")
    assert a["state"].split(".")[0] == b["state"].split(".")[0]
    assert a["diagnostic_reference_not_model_input"] != b["diagnostic_reference_not_model_input"]
    assert len(search.goal_placement()) == 48
    with pytest.raises(ValueError, match="known"):
        search.goal_state_fixture("unknown", "open", "sentence")


def raw_run(tmp_path, *, corrupt=None, omit=False, failure=False):
    f = search.goal_state_fixture("open", "closed", "sentence")
    recorder = RunRecorder(tmp_path / "run", {"fixture_ids": [f["fixture_id"]], "repeats": 1}, {"run_id": "run"})
    recorder.record("search_fixture", f)
    identity = {"fixture_id": f["fixture_id"], "repeat": 0, "ordinal": 0}
    intent = {**identity, "call_id": _sha256_json(identity), "payload_id": f["payload_id"],
              "input_encoding": {"available": True, "truncated": False, "questions": {"action": {
                  "effective_input_ids": [10, 11], "option_markers": [0, 1],
                  "state_tokens": 1, "effective_token_count": 2}}},
              "device_before": "cpu", "dtype_before": "float32", "temperature": {"effective": 1.}}
    response = {"call_id": intent["call_id"], "actual_device": "cpu", "actual_dtype": "float32",
                "latency_ms": 1., "raw_response": {"answers": {"action": {
                    "choice": "B", "probabilities": {"A": 0., "B": 1.}}}},
                "forward_traces": [{"input_ids": [[10, 11]], "option_markers": [[0, 1]],
                                    "raw_option_logits": [[0., 10.]]}]}
    if corrupt:
        corrupt(response)
    if not omit:
        recorder.record("model_call_intent", intent)
        recorder.record("model_raw_response", response)
        recorder.record("model_call_analysis", {"canonical_choice": "WRONG", "matches_diagnostic_reference": False})
    if failure:
        recorder.record("failure", {"exception": "preserved"})
    recorder.record("termination", {"reason": "interface_search_complete", "calls": 1})
    recorder.close()
    return tmp_path / "run"


def test_summary_recomputes_raw_response_ignores_analysis_and_recovers_key_order(tmp_path):
    r = search.summarize(raw_run(tmp_path))
    assert r["complete"]
    assert r["calls"][0]["choice"] == "CONTINUE"
    assert r["calls"][0]["correct"]


@pytest.mark.parametrize("mutation,match", [
    (lambda r: r.update(actual_device="cuda"), "device"),
    (lambda r: r["raw_response"]["answers"]["action"]["probabilities"].update(A=-.1), "distribution"),
    (lambda r: r["raw_response"]["answers"]["action"]["probabilities"].update(A=.2, B=.8), "calibrated"),
    (lambda r: r["raw_response"]["answers"]["action"].update(choice="A"), "scorer"),
    (lambda r: r["forward_traces"][0].update(input_ids=[[12, 13]]), "tokens"),
])
def test_summary_rejects_corrupt_inference_evidence(tmp_path, mutation, match):
    with pytest.raises(ValueError, match=match):
        search.summarize(raw_run(tmp_path, corrupt=mutation))


def test_termination_cannot_hide_missing_planned_calls(tmp_path):
    r = search.summarize(raw_run(tmp_path, omit=True))
    assert not r["complete"]
    assert not r["planned_coverage_complete"]


def test_recorded_failure_prevents_complete_status(tmp_path):
    assert not search.summarize(raw_run(tmp_path, failure=True))["complete"]
