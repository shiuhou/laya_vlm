from copy import deepcopy

import numpy as np
import pytest

from embodied_runtime.experiments import explicit_consequence as explicit
from embodied_runtime.experiments import predicate_verification as verification
from embodied_runtime.experiments import selective_grip as selective
from embodied_runtime.experiments.effect_binding import binding_fixture, presented_support
from embodied_runtime.experiments.goal_placement import move_fixture
from embodied_runtime.experiments.interface_search import TOKENS
from embodied_runtime.experiments.reference_model_diagnostic import payload_id
from embodied_runtime.runtime_core import _sha256_json


def parent(goal="closed", assignment="true", reverse=False, boundary=0):
    deltas = [-3., -1., 4., -4., 1., -2., 0., -2.25, -2., 3., -2.]
    base = {"state": "The drawer is currently partly open. The requested state is closed.",
            "source": {"physical": {"init_state_id": boundary, "environment_step": 48},
                       "oracle_effects_not_model_input_as_numeric_table": {
                           t: {"opening_change_mm": d, "obstacle": False,
                               "opening_change": "decreases" if d < -.25 else "increases" if d > .25 else "unchanged"}
                           for t, d in zip(TOKENS, deltas)},
                       "contract_flags_not_model_input": {t: True for t in TOKENS}}}
    return explicit.explicit_fixture(selective.neutralize_fixture(move_fixture(binding_fixture(
        base, descriptions="native", detail="relative", assignment=assignment,
        goal=goal, reverse=reverse))))


@pytest.mark.parametrize("goal", ["closed", "open"])
@pytest.mark.parametrize("assignment", ["true", "shift4"])
@pytest.mark.parametrize("token", TOKENS)
def test_exact_bundle_and_state_preserved_without_evaluator_truth(goal, assignment, token):
    source = parent(goal, assignment)
    before = deepcopy(source)
    fixture = verification.verification_fixture(source, token)
    option = fixture["verification"]["tested_option"]
    assert source == before
    assert fixture["state"] == source["state"]
    assert fixture["source"] == source["source"]
    assert fixture["questions"]["action"]["instructions"] == (
        "Determine whether this candidate satisfies the stated criterion. Criterion: "
        + source["questions"]["action"]["instructions"] + "\nCandidate: "
        + source["questions"]["action"]["criteria"][option])
    assert fixture["option_to_canonical"] == verification.ANSWER_LABELS
    assert fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == [
        "satisfies" if presented_support(source["source"], token) else "does_not_satisfy"]
    assert fixture["payload_id"] == payload_id(fixture["state"], fixture["questions"])
    hashable = deepcopy(fixture)
    assert hashable.pop("fixture_id") == _sha256_json(hashable)


def test_answer_order_only_changes_criteria_order_not_label_mapping():
    source = parent()
    a, b = [verification.verification_fixture(source, "MV_FWD", reverse) for reverse in (False, True)]
    assert a["state"] == b["state"]
    assert a["questions"] == b["questions"]  # dict content equal, insertion differs
    assert a["option_order"] == list(reversed(b["option_order"]))
    assert a["option_to_canonical"] == b["option_to_canonical"]
    assert a["payload_id"] != b["payload_id"]
    a["diagnostic_reference_not_model_input"] = {"scored_expected_tokens": ["opposite_fake_label"]}
    assert a["payload_id"] == payload_id(a["state"], a["questions"])


@pytest.mark.parametrize("mutate", [
    lambda p: p["source"].update(reverse=True),
    lambda p: p["intervention"].update(version="unknown"),
    lambda p: p["questions"]["action"].update(instructions="Choose a winner"),
    lambda p: p["option_to_canonical"].pop(next(iter(p["option_to_canonical"]))),
])
def test_nonfrozen_parent_shape_rejected(mutate):
    fixture = parent()
    mutate(fixture)
    with pytest.raises(ValueError):
        verification.verification_fixture(fixture, "MV_FWD")


def test_exact_design_coverage_and_unchanged_controls():
    parents = [parent(g, a, r, i) for i in range(4) for g in ("closed", "open")
               for a in ("true", "shift4") for r in (False, True)]
    fixtures = verification.design(parents)
    controls = [f for f in fixtures if "verification" not in f]
    binaries = [f for f in fixtures if "verification" in f]
    assert controls == parents
    assert len(fixtures) == len({f["fixture_id"] for f in fixtures}) == 384
    assert len(binaries) == 352
    assert len(fixtures)*2 == 768
    for source in parents:
        associated = [f for f in binaries if f["verification"]["parent_fixture_id"] == source["fixture_id"]]
        assert len(associated) == (0 if source["source"]["reverse"] else 22)
        if associated:
            assert {f["verification"]["tested_token"] for f in associated} == set(TOKENS)
            assert sum(f["verification"]["answer_order_reversed"] for f in associated) == 11


def synthetic_call(fixture, ordinal=0, repeat=0):
    ids, markers = [1, 2, 3], [1, 2]
    audit = {"available": True, "truncated": False, "questions": {
        "action": {"effective_input_ids": ids, "option_markers": markers}}}
    intent = {"fixture_id": fixture["fixture_id"], "ordinal": ordinal, "repeat": repeat,
              "payload_id": fixture["payload_id"], "input_encoding": audit,
              "temperature": {"configured": 1., "effective": 1.},
              "device_before": "cuda", "dtype_before": "torch.bfloat16"}
    intent["call_id"] = _sha256_json({k: intent[k] for k in ("fixture_id", "repeat", "ordinal")})
    probs = np.exp([0., 1.]) / np.exp([0., 1.]).sum()
    response = {"call_id": intent["call_id"], "actual_device": "cuda", "actual_dtype": "torch.bfloat16",
                "raw_response": {"answers": {"action": {"choice": fixture["option_order"][1],
                    "probabilities": dict(zip(fixture["option_order"], probs.tolist()))}}},
                "forward_traces": [{"input_ids": [ids], "option_markers": [markers],
                                    "raw_option_logits": [[0., 1.]], "raw_act_logits": [[0., 0.]]}]}
    return intent, response


def test_two_option_raw_logits_and_tokens_are_verified():
    fixture = verification.verification_fixture(parent(), "MV_FWD")
    intent, response = synthetic_call(fixture)
    recovered = verification.validate_response(fixture, intent, response)
    assert recovered["choice"] == "does_not_satisfy"
    assert recovered["raw_logits"] == [[0., 1.]]


@pytest.mark.parametrize("mutate", [
    lambda r: r["raw_response"]["answers"]["action"].update(choice="V0"),
    lambda r: r["raw_response"]["answers"]["action"].update(choice="unrecognized"),
    lambda r: r["raw_response"]["answers"]["action"].update(probabilities={"V0": 1.}),
    lambda r: r["raw_response"]["answers"]["action"].update(probabilities={"V0": float("nan"), "V1": 0.}),
    lambda r: r["raw_response"]["answers"]["action"].update(probabilities={"V0": .5, "V1": .5}),
    lambda r: r["forward_traces"][0].update(input_ids=[[9]]),
    lambda r: r["forward_traces"][0].update(option_markers=[[0, 1]]),
    lambda r: r["forward_traces"][0].update(raw_option_logits=[[0., 1., 2.]]),
    lambda r: r.update(forward_traces=[]),
    lambda r: r.update(actual_device="cpu"),
])
def test_malformed_output_or_evidence_is_missing_not_success(mutate):
    fixture = verification.verification_fixture(parent(), "MV_FWD")
    intent, response = synthetic_call(fixture)
    mutate(response)
    rows = [{"kind": "model_call_intent", "data": intent},
            {"kind": "model_raw_response", "data": response},
            {"kind": "model_call_analysis", "data": {"matches_diagnostic_reference": True}}]
    calls, invalid, unmatched = verification.recover_calls(rows, [fixture], {fixture["fixture_id"]: intent["input_encoding"]})
    assert not calls and len(invalid) == 1 and not unmatched
    metrics = verification.confusion([fixture], calls)
    assert metrics["tp"] == metrics["tn"] == 0
    assert metrics["missing_positive"] + metrics["missing_negative"] == 1


def test_missing_intent_response_and_traversal_mismatch():
    fixture = verification.verification_fixture(parent(), "MV_FWD")
    intent, _ = synthetic_call(fixture)
    rows = [{"kind": "model_call_intent", "data": intent}]
    calls, invalid, unmatched = verification.recover_calls(rows, [fixture], {fixture["fixture_id"]: intent["input_encoding"]})
    assert calls == invalid == [] and unmatched == [intent["call_id"]]
    intent["ordinal"] = 2
    intent["call_id"] = _sha256_json({k: intent[k] for k in ("fixture_id", "repeat", "ordinal")})
    with pytest.raises(ValueError, match="traversal"):
        verification.recover_calls(rows, [fixture], {fixture["fixture_id"]: intent["input_encoding"]})


def test_balanced_accuracy_keeps_missing_denominators_and_does_not_trust_cached_labels():
    fixtures = [verification.verification_fixture(parent(), t) for t in TOKENS]
    calls = [{"fixture_id": f["fixture_id"], "repeat": 0, "choice": "satisfies"}
             for f in fixtures if presented_support(f["source"], f["verification"]["tested_token"])]
    for f in fixtures:
        f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] = ["incorrect_cached_label"]
    counts = verification.confusion(fixtures, calls)
    assert counts["sensitivity"] == 1.
    assert counts["specificity"] == 0.
    assert counts["balanced_accuracy"] == .5
    assert counts["missing_negative"] > 0


def test_shifted_effect_truth_is_supplied_predicate_not_real_action_effect():
    source = parent(assignment="shift4")
    fixture = verification.verification_fixture(source, "RELEASE")
    assert fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["satisfies"]
    assert source["source"]["effect_assignment"]["RELEASE"] != "RELEASE"


def test_gpu_environment_difference_is_a_report_not_a_constraint():
    assert verification.environment_difference({"cuda_visible_devices": "1"}, {"cuda_visible_devices": "0"}) == {
        "cuda_visible_devices": {"archived": "1", "current": "0"}}


def test_invalid_source_rejected_before_model_load(tmp_path):
    (tmp_path / "episodes.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="frozen"):
        verification.frozen_source(tmp_path)
