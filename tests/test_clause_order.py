from copy import deepcopy

import pytest

from embodied_runtime.experiments import clause_order as clause
from embodied_runtime.experiments.effect_binding import binding_fixture
from embodied_runtime.experiments.interface_search import TOKENS
from embodied_runtime.experiments.reference_model_diagnostic import payload_id


def fixture(**kwargs):
    base = {"state": "The drawer is currently partly open. The requested state is closed.",
            "source": {"physical": {"init_state_id": 0, "environment_step": 48},
                       "oracle_effects_not_model_input_as_numeric_table": {
                           t: {"opening_change_mm": d, "obstacle": False,
                               "opening_change": "decreases" if d < -.25 else "increases" if d > .25 else "unchanged"}
                           for t, d in zip(TOKENS, [-3., -1., 4., -4., 1., -2., 0., -2.25, -2., 3., -2.])},
                       "contract_flags_not_model_input": {t: True for t in TOKENS}}}
    return binding_fixture(base, **{"descriptions": "native", "detail": "relative",
                                   "assignment": "true", "goal": "closed", "reverse": False, **kwargs})


@pytest.mark.parametrize("goal", ["closed", "open"])
@pytest.mark.parametrize("assignment", ["true", "shift4"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("descriptions", ["native", "anonymous"])
def test_only_final_clause_order_changes(goal, assignment, reverse, descriptions):
    parent = fixture(goal=goal, assignment=assignment, reverse=reverse, descriptions=descriptions)
    original = deepcopy(parent)
    changed = clause.swap_fixture(parent)
    assert parent == original
    assert changed["fixture_id"] != parent["fixture_id"]
    assert changed["payload_id"] != parent["payload_id"]
    assert changed["payload_id"] == payload_id(changed["state"], changed["questions"])
    assert changed["state"][:-len(clause.SWAPPED)] == parent["state"][:-len(clause.ORIGINAL)]
    assert changed["state"].replace(clause.SWAPPED, clause.ORIGINAL) == parent["state"]
    for key in parent.keys() - {"state", "payload_id", "fixture_id"}:
        assert changed[key] == parent[key]
    assert list(changed["questions"]["action"]["criteria"]) == parent["option_order"]
    assert changed["intervention"]["parent_fixture_id"] == parent["fixture_id"]


@pytest.mark.parametrize("mutate", [lambda f: f.update(state=f["state"] + " Extra instruction."),
    lambda f: f.update(state=clause.ORIGINAL + f["state"]),
    lambda f: f["source"].update(effect_detail="absolute")])
def test_unplanned_inputs_rejected(mutate):
    f = fixture()
    mutate(f)
    with pytest.raises(ValueError, match="exact frozen"):
        clause.swap_fixture(f)


def test_direction_uses_presented_assignment_preserves_mixed_and_unknown():
    true, shifted = fixture(), fixture(assignment="shift4")
    assert clause.direction(true, "MV_FWD")["direction"] == "closed"
    assert clause.direction(shifted, "MV_FWD")["direction"] == "open"
    assert clause.direction(true, "STOP")["direction"] == "other"
    assert clause.direction(true, "STOP")["facts"]["vs_stop"] == "same"
    assert clause.direction(true, None) == {"direction": "unknown", "facts": None}


def test_reversal_can_follow_final_clause_while_losing_goal_correctness():
    original = fixture(goal="open")
    changed = clause.swap_fixture(original)
    before = [{"fixture_id": original["fixture_id"], "repeat": 0, "choice": "MV_LEFT"}]
    after = [{"fixture_id": changed["fixture_id"], "repeat": 0, "choice": "MV_FWD"}]
    pairs, controls = clause.compare_calls([original], [changed], before, after)
    pair, = pairs
    assert not controls
    assert pair["follows_both_final_clauses"] and pair["choice_changed"]
    assert pair["before"]["presented_fact_consistent"] and pair["before"]["local_support"]
    assert not pair["after"]["presented_fact_consistent"] and not pair["after"]["local_support"]


def test_invalid_choice_stays_in_matched_pairs_and_denominator():
    original = fixture()
    changed = clause.swap_fixture(original)
    pairs, _ = clause.compare_calls([original], [changed],
        [{"fixture_id": original["fixture_id"], "repeat": 0, "choice": "MV_LEFT"}],
        [{"fixture_id": changed["fixture_id"], "repeat": 0, "choice": None}])
    assert pairs[0]["after"]["direction"] == "unknown"
    assert not pairs[0]["after"]["valid"]
    assert not pairs[0]["after"]["presented_fact_consistent"]
    assert not pairs[0]["follows_both_final_clauses"]


def test_control_checks_raw_values_even_when_choice_repeats():
    a = {"choice": "MV_FWD", "raw_logits": [[1., 2.]], "probabilities": {"A": .2, "B": .8}}
    b = {**a, "raw_logits": [[1.01, 2.]]}
    assert clause.raw_equal(a, b) == {"choice_equal": True, "raw_equal": False}
    a = {"choice": "MV_FWD", "generated_ids": [1, 2], "logits_values_sha256": "aaa"}
    assert not clause.raw_equal(a, {**a, "logits_values_sha256": "bbb"})["raw_equal"]


def test_control_selection_is_predeclared_and_does_not_use_choices():
    originals = [fixture(descriptions=d, goal=g, reverse=r, assignment=a)
                 for d in ("native", "anonymous") for g in ("closed", "open")
                 for r in (False, True) for a in ("true", "shift4")]
    fs = clause.design(originals)
    assert len(fs) == len(originals) + 2
    assert all("intervention" not in f for f in fs[:2])
    assert {f["source"]["descriptions"] for f in fs[:2]} == {"native", "anonymous"}
    assert all(f["source"]["goal"] == "closed" and f["source"]["assignment"] == "true"
               and not f["source"]["reverse"] for f in fs[:2])
