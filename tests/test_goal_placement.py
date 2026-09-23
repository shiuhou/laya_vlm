from copy import deepcopy

import pytest

from embodied_runtime.experiments import goal_placement as placement
from embodied_runtime.experiments.effect_binding import binding_fixture
from embodied_runtime.experiments.interface_search import TOKENS
from embodied_runtime.experiments.reference_model_diagnostic import payload_id


def fixture(**kwargs):
    deltas = [-3., -1., 4., -4., 1., -2., 0., -2.25, -2., 3., -2.]
    base = {"state": "The drawer is currently partly open. The requested state is closed.",
            "source": {"physical": {"init_state_id": 0, "environment_step": 48},
                       "oracle_effects_not_model_input_as_numeric_table": {
                           t: {"opening_change_mm": d, "obstacle": False,
                               "opening_change": "decreases" if d < -.25 else "increases" if d > .25 else "unchanged"}
                           for t, d in zip(TOKENS, deltas)},
                       "contract_flags_not_model_input": {t: True for t in TOKENS}}}
    return binding_fixture(base, **{"descriptions": "native", "detail": "relative",
                                   "assignment": "true", "goal": "closed", "reverse": False, **kwargs})


@pytest.mark.parametrize("goal", ["closed", "open"])
@pytest.mark.parametrize("assignment", ["true", "shift4"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("descriptions", ["native", "anonymous"])
def test_only_unchanged_goal_sentence_moves(goal, assignment, reverse, descriptions):
    parent = fixture(goal=goal, assignment=assignment, reverse=reverse, descriptions=descriptions)
    original = deepcopy(parent)
    moved = placement.move_fixture(parent)
    sentence = f"The requested state is {goal}."
    assert parent == original
    assert moved["state"].endswith(placement.clause.ORIGINAL + " " + sentence)
    assert moved["state"].count(sentence) == 1
    observed = "The drawer is currently partly open. "
    reconstructed = observed + sentence + " " + moved["state"][len(observed):-(len(sentence)+1)]
    assert reconstructed == parent["state"]
    assert len(moved["state"]) == len(parent["state"])
    for key in parent.keys() - {"fixture_id", "payload_id", "state"}:
        assert moved[key] == parent[key]
    assert moved["payload_id"] == payload_id(moved["state"], moved["questions"])
    assert moved["payload_id"] != parent["payload_id"]
    assert moved["intervention"]["parent_fixture_id"] == parent["fixture_id"]
    assert list(moved["questions"]["action"]["criteria"]) == parent["option_order"]


@pytest.mark.parametrize("mutation", [
    lambda f: f.update(state=f["state"].replace(placement.clause.ORIGINAL, placement.clause.SWAPPED)),
    lambda f: f.update(state=f["state"] + " The requested state is closed."),
    lambda f: f.update(state=f["state"].replace("The requested state is closed.", "Please close it.")),
    lambda f: f["source"].update(effect_detail="absolute"),
    lambda f: f["source"].update(goal="open"),
])
def test_additional_changes_or_wrong_sources_rejected(mutation):
    f = fixture()
    mutation(f)
    with pytest.raises(ValueError, match="exact original"):
        placement.move_fixture(f)


def test_every_original_is_preserved_and_pair_order_counterbalanced():
    originals = [fixture(goal=g, descriptions=d) for g in ("closed", "open") for d in ("native", "anonymous")]
    design = placement.design(originals)
    assert len(design) == 2*len(originals)
    for i, original in enumerate(originals):
        pair = design[2*i:2*i+2]
        assert pair[i % 2] is original
        assert pair[1-i % 2]["intervention"]["parent_fixture_id"] == original["fixture_id"]
    assert list(reversed(design))[0] == design[-1]


def call(f, choice, probabilities=None):
    return {"fixture_id": f["fixture_id"], "repeat": 0, "choice": choice,
            "probabilities": probabilities or {choice: 1.}}


def test_action_change_requires_appropriate_consequence_reversal():
    closed, opened = fixture(), fixture(goal="open")
    wrong = placement.binding_metrics([closed, opened], [call(closed, "MV_FWD"), call(opened, "MV_RIGHT")])
    pair = wrong["contrasts"]["goal"][0]
    assert pair["choice_changed"] and not pair["appropriate_goal_reversal"]
    right = placement.binding_metrics([closed, opened], [call(closed, "MV_FWD"), call(opened, "MV_LEFT")])
    assert right["contrasts"]["goal"][0]["appropriate_goal_reversal"]


def test_shifted_direction_mass_uses_supplied_facts_and_keeps_physical_flags():
    f = fixture(assignment="shift4")
    result = placement.binding_metrics([f], [call(f, "ROTATE_CCW")])
    c = result["calls"][0]
    assert c["direction"] == "closed" and c["direction_probability_mass"]["closed"] == 1.
    assert c["presented_fact_consistent"] and not c["local_support"] and c["contract_flag"]


def test_invalid_choice_does_not_disappear_or_become_supported():
    f = fixture()
    result = placement.binding_metrics([f], [call(f, None, {"MV_FWD": .5, "MV_LEFT": .5})])
    g = result["groups"]["native/true/closed"]
    assert g["n"] == 1 and g["facts_correct"] == g["actual_useful"] == 0
    assert g["directions"] == {"unknown": 1}
