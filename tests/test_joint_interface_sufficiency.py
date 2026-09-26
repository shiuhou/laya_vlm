from copy import deepcopy

import pytest

from embodied_runtime.experiments import joint_interface_sufficiency as probe
from embodied_runtime.experiments.reference_model_diagnostic import payload_id
from embodied_runtime.runtime_core import _sha256_json


def fixture():
    state = ("Current local objective: advance_target.\n"
             "Task: close top drawer. effect_source=oracle_sim; privileged=true.\n"
             "Current opening=149.564mm gap=0.01mm target_contact=0 grip=open.\n"
             "Effects: action|closure_mm|gap_reduction_mm\nopen|1.756|0.01\ny-40mm|34.177|0.01\n")
    questions = {"action": {"type": "choice", "instructions": "unchanged objective",
                            "criteria": {"open": "", "y-40mm": ""}}}
    value = {"condition": "unchanged_current_motor", "state": state, "questions": questions,
             "option_order": ["open", "y-40mm"], "option_to_canonical": {"open": "open", "y-40mm": "y-40mm"},
             "source": {"objective": "advance_target", "predictions": {"winner": "open"}},
             "diagnostic_reference_not_model_input": {"scored_expected_tokens": None},
             "payload_id": payload_id(state, questions)}
    value["fixture_id"] = _sha256_json(value)
    return value


def test_exact_existing_prefixes_and_all_original_model_bytes():
    original = fixture()
    saved = deepcopy(original)
    combined = probe.joint_fixture(original)
    w = probe.worldview.worldview_fixture(original)
    a = probe.binding.binding_fixture(original)
    assert original == saved
    assert combined["state"] == w["intervention"]["prefix"] + a["state"]
    assert combined["state"].endswith(original["state"])
    for key in ("questions", "option_order", "option_to_canonical", "source"):
        assert combined[key] == original[key]
    assert combined["intervention"]["worldview_fixture_id"] == w["fixture_id"]
    assert combined["intervention"]["action_fixture_id"] == a["fixture_id"]


def test_hidden_labels_cannot_change_joint_payload():
    original = fixture()
    poisoned = deepcopy(original)
    poisoned["source"] = {"objective": "approach_target", "predictions": {"winner": "y-40mm"}}
    poisoned["diagnostic_reference_not_model_input"] = {"scored_expected_tokens": ["open"]}
    poisoned["fixture_id"] = _sha256_json({k: v for k, v in poisoned.items() if k != "fixture_id"})
    assert probe.joint_fixture(original)["payload_id"] == probe.joint_fixture(poisoned)["payload_id"]


@pytest.mark.parametrize("key", ["state", "option_order", "questions"])
def test_changed_original_is_rejected(key):
    original = fixture()
    original[key] = "modified"
    with pytest.raises(ValueError):
        probe.joint_fixture(original)
