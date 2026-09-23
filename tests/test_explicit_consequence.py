from copy import deepcopy

import pytest

from embodied_runtime.experiments import explicit_consequence as explicit
from embodied_runtime.experiments import selective_grip as selective
from embodied_runtime.experiments.effect_binding import binding_fixture, presented_support
from embodied_runtime.experiments.goal_placement import binding_metrics, move_fixture
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
    return selective.neutralize_fixture(move_fixture(binding_fixture(base, **{
        "descriptions": "native", "detail": "relative", "assignment": "true",
        "goal": "closed", "reverse": False, **kwargs})))


@pytest.mark.parametrize("goal", ["closed", "open"])
@pytest.mark.parametrize("assignment", ["true", "shift4"])
@pytest.mark.parametrize("reverse", [False, True])
def test_exactly_one_model_input_field_changes(goal, assignment, reverse):
    parent = fixture(goal=goal, assignment=assignment, reverse=reverse)
    before = deepcopy(parent)
    f = explicit.explicit_fixture(parent)
    assert parent == before
    for key in parent.keys() - {"questions", "fixture_id", "payload_id", "intervention"}:
        assert f[key] == parent[key]
    q = deepcopy(f["questions"])
    q["action"]["instructions"] = parent["questions"]["action"]["instructions"]
    assert q == parent["questions"]
    assert list(q["action"]["criteria"]) == parent["option_order"]
    assert f["questions"]["action"]["instructions"] == explicit.QUESTIONS[goal]
    assert f["payload_id"] == payload_id(f["state"], f["questions"]) != parent["payload_id"]
    assert f["intervention"]["parent_intervention"] == parent["intervention"]
    assert f["intervention"]["parent_fixture_id"] == parent["fixture_id"]
    assert not any(t in explicit.QUESTIONS[goal] for t in TOKENS if t != "STOP")


@pytest.mark.parametrize("mutation", [
    lambda f: f["source"].update(goal="unknown"),
    lambda f: f["source"].update(effect_detail="absolute"),
    lambda f: f.update(state=f["state"] + " Extra rule."),
    lambda f: f["intervention"].update(version="other"),
    lambda f: f["questions"]["action"].update(instructions="Choose A00."),
    lambda f: f["questions"]["action"]["criteria"].update(A00="intervention; opening decreases; vs STOP lower; obstacle no"),
    lambda f: f["questions"]["action"]["criteria"].update(A09="close grip; hold pose; opening increases; vs STOP higher; obstacle no"),
    lambda f: f.update(option_order=list(reversed(f["option_order"]))),
    lambda f: f["source"]["oracle_effects_not_model_input_as_numeric_table"]["STOP"].update(opening_change_mm=None),
])
def test_invalid_or_changed_parent_rejected(mutation):
    f = fixture()
    mutation(f)
    with pytest.raises(ValueError):
        explicit.explicit_fixture(f)


@pytest.mark.parametrize("goal", ["closed", "open"])
def test_conjunction_requires_absolute_relative_and_safety(goal):
    f = fixture(goal=goal)
    s = f["source"]
    sign = -1 if goal == "closed" else 1
    effects = s["oracle_effects_not_model_input_as_numeric_table"]
    for stop, candidate, obstacle, expected in [
        (0., .25, False, False),  # absolute threshold is strict
        (1., 1.25, False, False),  # relative threshold is strict
        (2., 1., False, False),  # desired absolute direction but worse than STOP
        (-2., -1., False, False),  # better than STOP but wrong absolute direction
        (0., 1., True, False),
        (0., 1., False, True),
    ]:
        effects["STOP"]["opening_change_mm"] = sign * stop
        effects["MV_FWD"].update(opening_change_mm=sign*candidate, obstacle=obstacle)
        assert presented_support(s, "MV_FWD") == expected


def call(f, choice, **kwargs):
    return {"fixture_id": f["fixture_id"], "repeat": 0, "choice": choice,
            "probabilities": {choice: 1.}, "raw_logits": [[1., 2.]], **kwargs}


def test_immediate_selective_control_and_invalid_choice_remain_visible():
    parent = fixture()
    f = explicit.explicit_fixture(parent)
    old = call(parent, "MV_LEFT")
    now = call(parent, "MV_LEFT", raw_logits=[[1.1, 2.]])
    pairs, controls = selective.matched_calls([parent], [parent, f], [old], [now, call(f, None)])
    assert len(controls) == len(pairs) == 1
    assert controls[0]["choice_equal"] and not controls[0]["raw_equal"]
    assert pairs[0]["parent_fixture_id"] == parent["fixture_id"]
    assert pairs[0]["after"]["direction"] == "unknown"
    assert not pairs[0]["after"]["presented_fact_consistent"]


def test_correct_shifted_predicate_does_not_imply_physical_utility():
    f = explicit.explicit_fixture(fixture(assignment="shift4"))
    c = binding_metrics([f], [call(f, "RELEASE")])["calls"][0]
    assert c["presented_fact_consistent"] and c["direction"] == "closed"
    assert not c["local_support"] and c["contract_flag"]


def test_question_identifies_same_effect_even_when_identity_or_order_changes():
    fs = [explicit.explicit_fixture(fixture(assignment=a, reverse=r))
          for a in ("true", "shift4") for r in (False, True)]
    assert len({f["questions"]["action"]["instructions"] for f in fs}) == 1
    assert fs[0]["diagnostic_reference_not_model_input"] != fs[2]["diagnostic_reference_not_model_input"]
    originals = [fixture(goal=g, reverse=r) for g in ("closed", "open") for r in (False, True)]
    design = explicit.design(originals)
    for i, parent in enumerate(originals):
        assert design[2*i+i % 2] is parent
        assert design[2*i+1-i % 2]["intervention"]["parent_fixture_id"] == parent["fixture_id"]


def test_unaccepted_source_rejected_before_model_load(tmp_path):
    (tmp_path / "episodes.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="frozen"):
        explicit.frozen_source(tmp_path)
