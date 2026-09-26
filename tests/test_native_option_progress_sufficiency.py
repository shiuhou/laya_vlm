from copy import deepcopy

import pytest

from embodied_runtime.experiments import native_option_progress_sufficiency as probe
from embodied_runtime.experiments.reference_model_diagnostic import payload_id
from embodied_runtime.runtime_core import _sha256_json


def fixture(phase="advance_target"):
    state = (f"Current local objective: {phase}.\n"
             "Task: close top drawer. effect_source=oracle_sim; privileged=true.\n"
             "Effects: action|closure_mm (positive closes)|gap_reduction_mm (positive approaches)|"
             "target_contact|obstacle_peak_N|success|controls\n"
             "y-3mm|2.371|-0.00|0|0.0|0|8\nopen|0.056|-0.06|0|0.0|0|8\n")
    questions = {"action": {"type": "choice", "instructions": "unchanged objective",
                            "criteria": {"y-3mm": "", "open": ""}}}
    value = {"condition": "unchanged_current_motor", "state": state, "questions": questions,
             "option_order": ["y-3mm", "open"], "option_to_canonical": {"y-3mm": "y-3mm", "open": "open"},
             "source": {"objective": phase, "predictions": {"winner": "open"}},
             "diagnostic_reference_not_model_input": {"scored_expected_tokens": None},
             "payload_id": payload_id(state, questions)}
    value["fixture_id"] = _sha256_json(value)
    return value


def test_only_empty_criteria_change_with_every_state_byte_and_option_preserved():
    original = fixture()
    saved = deepcopy(original)
    treatment = probe.progress_fixture(original)
    assert original == saved
    for key in ("state", "option_order", "option_to_canonical", "source"):
        assert treatment[key] == original[key]
    assert treatment["questions"]["action"] == {
        **original["questions"]["action"],
        "criteria": {"y-3mm": "closure_mm=2.371", "open": "closure_mm=0.056"}}


def test_visible_objective_routes_field_and_signed_printed_strings_are_not_normalized():
    original = fixture("approach_target")
    assert probe.progress_fixture(original)["questions"]["action"]["criteria"] == {
        "y-3mm": "gap_reduction_mm=-0.00", "open": "gap_reduction_mm=-0.06"}


def test_hidden_predictions_and_objective_metadata_cannot_change_payload():
    original = fixture()
    poisoned = deepcopy(original)
    poisoned["source"] = {"objective": "approach_target", "predictions": {"winner": "y-3mm"}}
    poisoned["diagnostic_reference_not_model_input"] = {"scored_expected_tokens": ["open"]}
    poisoned["fixture_id"] = _sha256_json({k: v for k, v in poisoned.items() if k != "fixture_id"})
    assert probe.progress_fixture(original)["payload_id"] == probe.progress_fixture(poisoned)["payload_id"]


@pytest.mark.parametrize("key", ["state", "option_order", "questions"])
def test_modified_baseline_identity_is_rejected(key):
    original = fixture()
    original[key] = "modified"
    with pytest.raises(ValueError):
        probe.progress_fixture(original)


def test_wrong_effect_order_and_missing_field_are_rejected():
    original = fixture()
    with pytest.raises(ValueError):
        probe.criterion_values(original["state"], list(reversed(original["option_order"])))
    with pytest.raises(ValueError):
        probe.criterion_values(original["state"].replace("closure_mm", "gain_mm"), original["option_order"])
