from copy import deepcopy

import pytest

from embodied_runtime.experiments import selective_grip as selective
from embodied_runtime.experiments.effect_binding import binding_fixture
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
    return move_fixture(binding_fixture(base, **{"descriptions": "native", "detail": "relative",
                        "assignment": "true", "goal": "closed", "reverse": False, **kwargs}))


@pytest.mark.parametrize("goal", ["closed", "open"])
@pytest.mark.parametrize("assignment", ["true", "shift4"])
@pytest.mark.parametrize("reverse", [False, True])
def test_only_two_nominal_prefixes_change(goal, assignment, reverse):
    parent = fixture(goal=goal, assignment=assignment, reverse=reverse)
    old = deepcopy(parent)
    f = selective.neutralize_fixture(parent)
    assert parent == old
    for key in parent.keys() - {"questions", "fixture_id", "payload_id", "intervention"}:
        assert f[key] == parent[key]
    assert f["questions"]["action"]["instructions"] == parent["questions"]["action"]["instructions"]
    before, after = [x["questions"]["action"]["criteria"] for x in (parent, f)]
    changed = []
    for option in parent["option_order"]:
        token = parent["option_to_canonical"][option]
        assert before[option].split("; opening ", 1)[1] == after[option].split("; opening ", 1)[1]
        if token in {"GRASP", "RELEASE"}:
            assert after[option].startswith("intervention; opening ")
            changed.append(token)
        else:
            assert after[option] == before[option]
    assert set(changed) == {"GRASP", "RELEASE"}
    assert list(after) == parent["option_order"]
    assert f["payload_id"] == payload_id(f["state"], f["questions"]) != parent["payload_id"]
    assert f["intervention"]["parent_intervention"] == parent["intervention"]


@pytest.mark.parametrize("mutation", [
    lambda f: f["source"].update(descriptions="anonymous"),
    lambda f: f["source"].update(effect_detail="absolute"),
    lambda f: f.update(state=f["state"] + " Additional rule."),
    lambda f: f["intervention"].update(version="other"),
    lambda f: f["questions"]["action"]["criteria"].update(A00="intervention; opening decreases; vs STOP lower; obstacle no"),
    lambda f: f["questions"]["action"]["criteria"].update(A09="grasp; opening decreases; vs STOP lower; obstacle no"),
])
def test_wrong_parent_or_description_is_rejected(mutation):
    f = fixture()
    mutation(f)
    with pytest.raises(ValueError):
        selective.neutralize_fixture(f)


def call(f, choice, **kwargs):
    return {"fixture_id": f["fixture_id"], "repeat": 0, "choice": choice,
            "probabilities": {choice: 1.}, "raw_logits": [[1., 2.]], **kwargs}


def test_matches_immediate_parent_even_when_parent_is_a_previous_intervention():
    original = fixture()
    new = selective.neutralize_fixture(original)
    before, after = call(original, "MV_LEFT"), call(new, "MV_FWD")
    pairs, controls = selective.matched_calls([original], [original, new], [before], [before, after])
    assert len(controls) == len(pairs) == 1
    assert controls[0]["raw_equal"]
    assert pairs[0]["parent_fixture_id"] == original["fixture_id"]
    assert pairs[0]["direction_transition"] == "open->closed"
    assert pairs[0]["after"]["presented_fact_consistent"]


def test_control_checks_logits_and_invalid_output_remains_in_pairs():
    original = fixture()
    new = selective.neutralize_fixture(original)
    archive = call(original, "MV_LEFT")
    now = call(original, "MV_LEFT", raw_logits=[[1.1, 2.]])
    pairs, controls = selective.matched_calls([original], [original, new], [archive], [now, call(new, None)])
    assert controls[0]["choice_equal"] and not controls[0]["raw_equal"]
    assert pairs[0]["after"]["direction"] == "unknown"
    assert not pairs[0]["after"]["presented_fact_consistent"]


def test_grip_candidate_can_be_fact_correct_without_being_physically_useful():
    f = selective.neutralize_fixture(fixture(assignment="shift4"))
    r = binding_metrics([f], [call(f, "RELEASE")])
    c = r["calls"][0]
    assert c["presented_fact_consistent"] and c["direction"] == "closed"
    assert not c["local_support"] and c["contract_flag"]


def test_moving_away_from_grip_is_not_automatically_goal_binding():
    closed = selective.neutralize_fixture(fixture())
    opened = selective.neutralize_fixture(fixture(goal="open"))
    r = binding_metrics([closed, opened], [call(closed, "MV_FWD"), call(opened, "MV_RIGHT")])
    pair = r["contrasts"]["goal"][0]
    assert pair["choice_changed"] and not pair["appropriate_goal_reversal"]
    assert not pair["both_fact_consistent"]


def test_pair_schedule_preserves_all_originals_and_alternates_first_position():
    originals = [fixture(goal=g, reverse=reverse) for g in ("closed", "open") for reverse in (False, True)]
    design = selective.design(originals)
    for i, original in enumerate(originals):
        assert design[2*i+i % 2] is original
        assert design[2*i+1-i % 2]["intervention"]["parent_fixture_id"] == original["fixture_id"]


def test_unaccepted_source_rejected_before_loading_a_model(tmp_path):
    (tmp_path / "episodes.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="frozen"):
        selective.frozen_source(tmp_path)
