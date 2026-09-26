from copy import deepcopy
from pathlib import Path

import pytest

from embodied_runtime.adapters.laya_input import encoding_audit
from embodied_runtime.experiments import action_semantics_binding as probe
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


def test_binding_preserves_every_original_model_byte_and_candidate():
    original = fixture()
    before = deepcopy(original)
    result = probe.binding_fixture(original)
    assert original == before
    assert result["state"] == probe.ACTION_DEFINITIONS + original["state"]
    for key in ("questions", "option_order", "option_to_canonical", "source"):
        assert result[key] == original[key]
    assert result["payload_id"] != original["payload_id"]


def test_hidden_predictions_and_objective_metadata_cannot_change_model_payload():
    original = fixture()
    poisoned = deepcopy(original)
    poisoned["source"] = {"objective": "approach_target", "predictions": {"winner": "y-40mm"}, "oracle": "poison"}
    poisoned["diagnostic_reference_not_model_input"] = {"scored_expected_tokens": ["open"]}
    poisoned["fixture_id"] = _sha256_json({k: v for k, v in poisoned.items() if k != "fixture_id"})
    assert probe.binding_fixture(original)["payload_id"] == probe.binding_fixture(poisoned)["payload_id"]


@pytest.mark.parametrize("key", ["state", "option_order", "questions"])
def test_changed_source_fixture_is_rejected(key):
    changed = fixture()
    changed[key] = "tampered"
    with pytest.raises(ValueError):
        probe.binding_fixture(changed)


@pytest.mark.parametrize("options", [["close_drawer"], ["open", "open"], ["rotate_z+90deg"], []])
def test_undefined_or_noncanonical_primitive_is_rejected(options):
    with pytest.raises(ValueError):
        probe.action_prefix(fixture()["state"], options)


def test_actual_token_components_match_and_truncation_is_rejected():
    pytest.importorskip("laya.common")
    if not Path(probe.MODEL_PATH).exists():
        pytest.skip("frozen local tokenizer unavailable")
    agent = probe.tokenizer_agent()
    f = probe.binding_fixture(fixture())
    audit = encoding_audit(agent, f["state"], f["questions"])
    parts = probe.component_audit(agent, f, audit)
    for part in ("heading", "option", "state"):
        assert parts[f"raw_{part}_ids"] == parts[f"consumed_{part}_ids"]
    f["state"] += " excess" * 1500
    audit = encoding_audit(agent, f["state"], f["questions"])
    with pytest.raises(ValueError):
        probe.component_audit(agent, f, audit)
