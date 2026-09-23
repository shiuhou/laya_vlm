from copy import deepcopy

import pytest

from embodied_runtime.experiments import effect_binding as binding
from embodied_runtime.experiments.interface_search import TOKENS
from embodied_runtime.experiments.reference_gate import physical_assessment


def base():
    # STOP closes by 2 mm. Merely decreasing opening does not beat that drift.
    deltas = [-3., -1., 4., -4., 1., -2., 0., -2.25, -2., 3., -2.]
    return {"state": "The drawer is currently partly open. The requested state is closed.",
            "source": {"physical": {"init_state_id": 0, "environment_step": 48},
                       "oracle_effects_not_model_input_as_numeric_table": {
                           t: {"opening_change_mm": d, "obstacle": False,
                               "opening_change": "decreases" if d < -.25 else "increases" if d > .25 else "unchanged"}
                           for t, d in zip(TOKENS, deltas)},
                       "contract_flags_not_model_input": {t: True for t in TOKENS}}}


def make(b=None, **kwargs):
    return binding.binding_fixture(b or base(), **{
        "descriptions": "native", "detail": "relative", "assignment": "true",
        "goal": "closed", "reverse": False, **kwargs})


def test_full_facts_match_independent_numeric_utility_and_keep_stop_aliases():
    for goal in ("closed", "open"):
        f = make(goal=goal)
        s = f["source"]
        expected = [t for t in TOKENS if physical_assessment(s, t)["local_support"]]
        assert f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == expected
        assert all(binding.presented_support(s, t) == physical_assessment(s, t)["local_support"] for t in TOKENS)
        assert not binding.presented_support(s, "STOP")
        assert not binding.presented_support(s, "RELEASE")
        assert all(s["contract_flags_not_model_input"].values())
    assert binding.effect_facts(make()["source"])["STOP"] == {
        "opening": "decreases", "vs_stop": "same", "obstacle": False}


def test_absolute_consistency_does_not_invent_missing_relative_information():
    absolute, full = make(detail="absolute"), make()
    assert absolute["state"] == full["state"]
    assert binding.presented_support(absolute["source"], "MV_BACK")
    assert not binding.presented_support(full["source"], "MV_BACK")
    assert not physical_assessment(absolute["source"], "MV_BACK")["local_support"]
    assert absolute["questions"]["action"]["instructions"] == full["questions"]["action"]["instructions"]


def test_factors_preserve_actual_set_goal_independent_facts_and_source():
    b = base()
    original = deepcopy(b)
    native, anonymous, reversed_order, opened = make(b), make(b, descriptions="anonymous"), make(b, reverse=True), make(b, goal="open")
    assert b == original
    assert native["state"] == anonymous["state"] == reversed_order["state"]
    assert native["questions"]["action"]["criteria"] == opened["questions"]["action"]["criteria"]
    assert native["option_order"] == list(reversed(reversed_order["option_order"]))
    assert native["payload_id"] != reversed_order["payload_id"]
    for f in (native, anonymous, reversed_order, opened):
        assert set(f["option_to_canonical"].values()) == set(TOKENS)
        assert len(f["option_order"]) == 11 and f["effects_supplied"]
        assert "scored_expected_tokens" not in str((f["state"], f["questions"]))
        assert "oracle_effects_not_model_input_as_numeric_table" not in str((f["state"], f["questions"]))
    for key, value in anonymous["questions"]["action"]["criteria"].items():
        assert value.startswith("intervention;")
        assert value.split("; opening ", 1)[1] == native["questions"]["action"]["criteria"][key].split("; opening ", 1)[1]


def test_shifted_presented_facts_are_not_actual_action_utility():
    true, shifted = make(), make(assignment="shift4")
    assert true["state"] == shifted["state"]
    assert true["option_to_canonical"] == shifted["option_to_canonical"]
    assert true["source"]["oracle_effects_not_model_input_as_numeric_table"] == shifted["source"]["oracle_effects_not_model_input_as_numeric_table"]
    assert binding.presented_support(shifted["source"], "ROTATE_CCW")  # assigned MV_FWD facts
    assert not physical_assessment(shifted["source"], "ROTATE_CCW")["local_support"]
    assert binding.presented_support(true["source"], "MV_FWD")
    assert not binding.presented_support(shifted["source"], "MV_FWD")


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_unknown_or_nonfinite_effects_cannot_be_converted_to_unchanged(value):
    b = base()
    b["source"]["oracle_effects_not_model_input_as_numeric_table"]["STOP"]["opening_change_mm"] = value
    with pytest.raises(ValueError, match="finite"):
        make(b)


def test_threshold_and_obstacle_checks_are_independent_of_nominal_semantics():
    for d in (-.25, 0., .25):
        assert binding.category(d, "lower", "higher", "same") == "same"
    b = base()
    b["source"]["oracle_effects_not_model_input_as_numeric_table"]["MV_FWD"]["obstacle"] = True
    f = make(b)
    assert not binding.presented_support(f["source"], "MV_FWD")
    assert not physical_assessment(f["source"], "MV_FWD")["local_support"]
    b["source"]["oracle_effects_not_model_input_as_numeric_table"]["MV_FWD"]["obstacle"] = None
    with pytest.raises(ValueError, match="known measured"):
        make(b)


def test_missing_candidate_effect_is_rejected():
    b = base()
    del b["source"]["oracle_effects_not_model_input_as_numeric_table"]["RELEASE"]
    with pytest.raises(ValueError, match="eleven"):
        make(b)
