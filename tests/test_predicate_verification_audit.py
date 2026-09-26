"""Corruption and leakage checks independent of the experiment builder."""
from copy import deepcopy

import pytest

from embodied_runtime.experiments import predicate_verification_audit as audit
from embodied_runtime.runtime_core import _sha256_json


def parent():
    effects = {t: {"opening_change_mm": 0., "obstacle": False} for t in audit.TOKENS}
    effects["MV_FWD"]["opening_change_mm"] = -1.
    effects["MV_BACK"]["opening_change_mm"] = -.25
    effects["MV_LEFT"]["opening_change_mm"] = .251
    effects["MV_RIGHT"]["opening_change_mm"] = -.251
    effects["MV_RIGHT"]["obstacle"] = True
    texts = ["decreases; vs STOP lower; obstacle no", "unchanged; vs STOP same; obstacle no",
             "increases; vs STOP higher; obstacle no", "decreases; vs STOP lower; obstacle yes"]
    texts += ["unchanged; vs STOP same; obstacle no"] * 7
    return {"fixture_id": "parent", "payload_id": "payload", "state": "The drawer is partly open.",
            "questions": {"action": {"type": "choice", "instructions":
                "Choose an intervention with opening decreases, vs STOP lower, and obstacle no.",
                "criteria": {f"A{i:02d}": "intervention; opening " + text for i, text in enumerate(texts)}}},
            "option_to_canonical": dict(zip((f"A{i:02d}" for i in range(11)), audit.TOKENS)),
            "diagnostic_reference_not_model_input": {"scored_expected_tokens": ["MV_FWD"]},
            "source": {"goal": "closed", "reverse": False, "effect_detail": "relative", "assignment": "true",
                       "oracle_effects_not_model_input_as_numeric_table": effects,
                       "effect_assignment": {t: t for t in audit.TOKENS}}}


def binary(p):
    return {"fixture_id": "binary", "payload_id": "binary_payload", "source": deepcopy(p["source"]),
            "state": p["state"], "verification": {"version": audit.VERSION, "parent_fixture_id": "parent",
                "parent_payload_id": "payload", "tested_token": "MV_FWD", "tested_option": "A00",
                "answer_order_reversed": False}, "option_order": ["V0", "V1"],
            "option_to_canonical": dict(audit.ANSWERS),
            "questions": {"action": {"type": "choice", "instructions":
                "Determine whether this candidate satisfies the stated criterion. Criterion: "
                + p["questions"]["action"]["instructions"] + "\nCandidate: "
                + p["questions"]["action"]["criteria"]["A00"], "criteria": dict(audit.ANSWERS)}},
            "diagnostic_reference_not_model_input": {"scored_expected_tokens": ["satisfies"]}}


def response_fixture():
    f = binary(parent())
    encoding = {"available": True, "truncated": False, "questions": {"action": {
        "state_truncated": False, "heading_truncated": False, "options_truncated": False,
        "effective_input_ids": [10, 20, 30], "effective_input_id": _sha256_json([10, 20, 30]),
        "effective_token_count": 3, "option_markers": [1, 2]}}}
    intent = {"fixture_id": f["fixture_id"], "payload_id": f["payload_id"], "input_encoding": encoding,
              "device_before": "cpu", "dtype_before": "float32", "repeat": 0,
              "temperature": {"bucket": "choice:2", "configured": 1., "effective": 1.}}
    raw = {"forward_hook_active": True, "forward_traces": [{"input_ids": [[10, 20, 30]],
            "option_markers": [[1, 2]], "raw_option_logits": [[1., 0.]]}],
           "actual_device": "cpu", "actual_dtype": "float32", "raw_response": {
               "usage": {"input_tokens": 3}, "answers": {"action": {
                   "choice": "V0", "probabilities": {"V0": .7311, "V1": .2689}}}}}
    return f, intent, raw, deepcopy(encoding)


def test_threshold_obstacle_and_shifted_assignment_are_independent():
    p = parent()
    labels = audit.independent_labels(p)
    assert labels["MV_FWD"]["presented_truth"]
    assert not labels["MV_BACK"]["presented_truth"]  # exactly .25 is unchanged
    assert not labels["MV_RIGHT"]["presented_truth"]  # obstacle veto
    p["source"]["effect_assignment"].update(MV_FWD="MV_LEFT", MV_LEFT="MV_FWD")
    criteria = p["questions"]["action"]["criteria"]
    criteria["A00"], criteria["A02"] = criteria["A02"], criteria["A00"]
    p["diagnostic_reference_not_model_input"]["scored_expected_tokens"] = ["MV_LEFT"]
    shifted = audit.independent_labels(p)
    assert shifted["MV_LEFT"]["presented_truth"] and not shifted["MV_LEFT"]["physical_support"]
    assert not shifted["MV_FWD"]["presented_truth"] and shifted["MV_FWD"]["physical_support"]


def test_stop_effect_comparison_is_required():
    p = parent()
    p["source"]["oracle_effects_not_model_input_as_numeric_table"]["STOP"]["opening_change_mm"] = -.9
    with pytest.raises(ValueError, match="numeric effects"):
        audit.independent_labels(p)


@pytest.mark.parametrize("corruption", ["label", "text", "nan"])
def test_bad_numeric_text_or_cached_truth_is_rejected(corruption):
    p = parent()
    if corruption == "label":
        p["diagnostic_reference_not_model_input"]["scored_expected_tokens"] = ["STOP"]
    elif corruption == "text":
        p["questions"]["action"]["criteria"]["A00"] = "intervention; opening increases; vs STOP higher; obstacle no"
    else:
        p["source"]["oracle_effects_not_model_input_as_numeric_table"]["MV_FWD"]["opening_change_mm"] = float("nan")
    with pytest.raises(ValueError):
        audit.independent_labels(p)


@pytest.mark.parametrize("where", ["state", "instructions", "criteria"])
def test_truth_leakage_into_model_payload_is_rejected(where):
    p = parent()
    f = binary(p)
    assert audit.audit_binary(f, p)["presented_truth"]
    if where == "state":
        f["state"] += " Correct answer: satisfies."
    elif where == "instructions":
        f["questions"]["action"]["instructions"] += " Ground truth: satisfies."
    else:
        f["questions"]["action"]["criteria"]["V0"] = "satisfies (correct)"
    with pytest.raises(ValueError, match="truth leaked"):
        audit.audit_binary(f, p)


def test_answer_order_changes_without_changing_meaning():
    p = parent()
    f = binary(p)
    f["verification"]["answer_order_reversed"] = True
    f["option_order"] = ["V1", "V0"]
    assert audit.audit_binary(f, p)["presented_truth"]
    f["option_to_canonical"] = {"V0": "does_not_satisfy", "V1": "satisfies"}
    with pytest.raises(ValueError, match="order mismatch"):
        audit.audit_binary(f, p)


@pytest.mark.parametrize("corruption", [None, "tokens", "argmax", "cardinality", "temperature", "truncation"])
def test_actual_forward_and_probabilities_are_checked(corruption):
    f, intent, raw, presentation = response_fixture()
    if corruption is None:
        assert audit.audit_response(f, intent, raw, presentation)["choice"] == "satisfies"
        return
    if corruption == "tokens":
        raw["forward_traces"][0]["input_ids"][0][0] = 999
    elif corruption == "argmax":
        raw["raw_response"]["answers"]["action"]["choice"] = "V1"
    elif corruption == "cardinality":
        del raw["raw_response"]["answers"]["action"]["probabilities"]["V1"]
    elif corruption == "temperature":
        intent["temperature"]["bucket"] = "choice:11+"
    else:
        presentation["truncated"] = intent["input_encoding"]["truncated"] = True
    with pytest.raises(ValueError):
        audit.audit_response(f, intent, raw, presentation)
