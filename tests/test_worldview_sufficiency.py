from copy import deepcopy

import pytest

from embodied_runtime.experiments import worldview_sufficiency as probe
from embodied_runtime.experiments.reference_model_diagnostic import payload_id
from embodied_runtime.runtime_core import _sha256_json


def fixture(phase="advance_target", gap="0.01"):
    state = (f"Current local objective: {phase}.\n"
             "Task: close top drawer. effect_source=oracle_sim; privileged=true.\n"
             f"Current opening=149.564mm gap={gap}mm target_contact=0 grip=open.\n"
             "Effects: action|closure_mm|gap_reduction_mm\nopen|1.756|0.01\ny-40mm|34.177|0.01\n")
    questions = {"action": {"type": "choice", "instructions": "unchanged objective", "criteria": {"open": "", "y-40mm": ""}}}
    value = {"condition": "unchanged_current_motor", "state": state, "questions": questions,
             "option_order": ["open", "y-40mm"], "option_to_canonical": {"open": "open", "y-40mm": "y-40mm"},
             "source": {"objective": phase, "predictions": {"winner": "open"}},
             "diagnostic_reference_not_model_input": {"scored_expected_tokens": None},
             "payload_id": payload_id(state, questions)}
    value["fixture_id"] = _sha256_json(value)
    return value


def reidentify(value):
    value["fixture_id"] = _sha256_json({k: v for k, v in value.items() if k != "fixture_id"})


def test_intervention_preserves_every_original_model_byte_and_candidate():
    original = fixture()
    before = deepcopy(original)
    result = probe.worldview_fixture(original)
    assert original == before
    assert result["state"] == probe.WORLDVIEWS["advance_target"] + original["state"]
    for key in ("questions", "option_order", "option_to_canonical", "source"):
        assert result[key] == original[key]
    assert result["payload_id"] != original["payload_id"]


def test_hidden_predictions_and_objective_metadata_cannot_change_model_payload():
    original = fixture()
    poisoned = deepcopy(original)
    poisoned["source"] = {"objective": "approach_target", "predictions": {"winner": "y-40mm"}, "oracle": "poison"}
    poisoned["diagnostic_reference_not_model_input"] = {"scored_expected_tokens": ["open"]}
    reidentify(poisoned)
    assert probe.worldview_fixture(original)["payload_id"] == probe.worldview_fixture(poisoned)["payload_id"]


@pytest.mark.parametrize("phase,gap", [("reposition", "0.01"), ("advance_target", "10.0")])
def test_unsupported_situation_is_rejected(phase, gap):
    with pytest.raises(ValueError):
        probe.worldview_fixture(fixture(phase, gap))


def test_changed_payload_is_rejected():
    changed = fixture()
    changed["state"] += "winner y-40mm"
    with pytest.raises(ValueError):
        probe.worldview_fixture(changed)


def test_worldview_contains_no_numeric_action_or_direction():
    for prefix in probe.WORLDVIEWS.values():
        assert not any(c.isdigit() for c in prefix)
        assert not any(word in prefix for word in ("y-", "x+", "rotate", "left", "right", "forward", "backward"))
