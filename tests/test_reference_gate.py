from copy import deepcopy

import pytest

from embodied_runtime.decision_interface import project_belief, project_oracle, shared_atomic_candidates
from embodied_runtime.experiments.equivalence import make_pair
from embodied_runtime.experiments.interface_search import transform
from embodied_runtime.experiments import reference_gate as gate
from embodied_runtime.runtime_core import BeliefSnapshot, _sha256_json


def pair(qpos=-.15):
    belief = BeliefSnapshot("ep", 1, .5, {"tcp_pos_world_m": [0., 0., 1.],
        "gripper_width_m": .08, "gripper_command": "OPEN", "holding": None,
        "vision:drawer:position_world_m": [.18, .02, 1.03]}, {}, {"instruction": "close top drawer"})
    perceptual = project_belief(belief, "drawer")
    oracle = project_oracle(perceptual, {"source_id": "physical", "target_position_m": [.2, .03, 1.02],
                           "position_definition": "test-point", "moving_contact": False, "remaining_open_mm": -qpos*1000})
    return make_pair(oracle, perceptual, shared_atomic_candidates(),
                     physical={"task": "top_drawer", "init_state_id": 0, "seed": 1,
                               "environment_step": 0, "sim_time": .5, "physical_state_id": "physical"})


@pytest.mark.parametrize("qpos,word,label", [(-.15, "open", "CONTINUE"),(-.08,"partly open","CONTINUE"),(.002,"closed","DONE")])
def test_progress_projection_keeps_unknown_and_matches_context(qpos, word, label):
    source = pair(qpos)
    old = deepcopy(source)
    before = {"qpos_m": qpos, "success": qpos > 0}
    fixtures = gate.progress_projection(source, before, "sourcehash")
    assert source == old
    assert len(fixtures) == 6
    oracle, perceptual, masked = fixtures[:3]
    assert f"currently {word}." in oracle["state"]
    assert "currently unknown." in perceptual["state"]
    assert oracle["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == [label]
    assert perceptual["diagnostic_reference_not_model_input"]["scored_expected_tokens"] is None
    assert masked["payload_id"] == perceptual["payload_id"]
    assert oracle["questions"] == perceptual["questions"] == masked["questions"]
    assert all(not f["effects_supplied"] for f in fixtures)
    before["future_outcomes"] = {"GRASP": "task success"}
    assert gate.progress_projection(source, before, "sourcehash") == fixtures


def test_progress_rejects_invented_perceptual_progress_and_inconsistent_oracle():
    p = pair()
    p["perceptual_state"]["fields"]["progress.remaining_open_mm"].update(value=5., source="sensor")
    p["pair_id"] = _sha256_json({k:v for k,v in p.items() if k != "pair_id"})
    with pytest.raises(ValueError, match="explicitly unknown"):
        gate.progress_projection(p, {"qpos_m": -.15, "success": False}, "hash")
    with pytest.raises(ValueError, match="success predicate"):
        gate.progress_projection(pair(), {"qpos_m": -.15, "success": True}, "hash")
    with pytest.raises(ValueError, match="disagree"):
        gate.progress_projection(pair(), {"qpos_m": -.10, "success": False}, "hash")


def test_articulation_uses_strict_predicates():
    assert gate.articulation(-.14) == gate.articulation(0.) == "partly open"
    with pytest.raises(ValueError, match="finite"):
        gate.articulation(float("nan"))


def test_consequence_controls_balance_goals_assignments_orders_without_recommendations():
    fixtures = gate.consequence_fixtures()
    assert len(fixtures) == len({f["fixture_id"] for f in fixtures}) == 32
    for fmt in gate.FORMATS:
        cases = [f for f in fixtures if f["condition"] == fmt]
        assert len(cases) == 8
        assert sum(f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["A"] for f in cases) == 4
        for f in cases:
            assert f["effects_supplied"]
            assert f["source"]["effect_source"] == "synthetic_control"
            assert len(f["option_order"]) == 2
            assert "scored_expected_tokens" not in str(f["state"])
    for fmt in gate.FORMATS:
        a = gate.consequence_fixture(fmt, "closed", False, False)
        reverse = gate.consequence_fixture(fmt, "closed", False, True)
        swapped = gate.consequence_fixture(fmt, "closed", True, False)
        assert a["state"] == reverse["state"]
        assert a["diagnostic_reference_not_model_input"] == reverse["diagnostic_reference_not_model_input"]
        assert a["diagnostic_reference_not_model_input"] != swapped["diagnostic_reference_not_model_input"]
        assert transform(a, "alias", shift=1)["effects_supplied"]


def test_js_symmetry_and_identical_distributions():
    assert gate.js([.6,.4], [.6,.4]) == 0
    assert gate.js([.8,.2], [.2,.8]) == pytest.approx(gate.js([.2,.8],[.8,.2]))


def test_abstention_adds_output_without_changing_state_or_question(monkeypatch):
    fixtures = gate.progress_projection(pair(), {"qpos_m": -.15, "success": False}, "hash")
    monkeypatch.setattr(gate, "status_fixtures", lambda path: fixtures)
    result = gate.abstention_fixtures("unused")
    assert len(result) == 4
    for f in result:
        assert set(f["option_to_canonical"].values()) == {"DONE", "CONTINUE", "UNKNOWN"}
        assert f["questions"]["action"]["instructions"] == gate.QUESTION
        if "unknown" in f["state"]:
            assert f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["UNKNOWN"]
        else:
            assert f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["CONTINUE"]
        assert not f["effects_supplied"]


def test_directional_closure_does_not_imply_incremental_utility_or_safety():
    s = {"goal": "closed", "effect_mode": "true", "effect_assignment": {"A":"A","STOP":"STOP"},
         "oracle_effects_not_model_input_as_numeric_table": {
             "A": {"opening_change_mm": -2., "opening_change":"decreases", "obstacle":False},
             "STOP": {"opening_change_mm": -2., "opening_change":"decreases", "obstacle":False}},
         "contract_flags_not_model_input": {"A":True,"STOP":True}}
    a = gate.physical_assessment(s,"A")
    assert a["absolute_goal_progress"] and a["presented_direction_matches_goal"]
    assert not a["local_support"] and a["closure_vs_stop_mm"] == 0
    s["oracle_effects_not_model_input_as_numeric_table"]["A"]["opening_change_mm"] = -3.
    assert gate.physical_assessment(s,"A")["local_support"]
    assert gate.physical_assessment(s,"A")["contract_flag"]  # never erase reset-envelope anomaly
    s["oracle_effects_not_model_input_as_numeric_table"]["A"]["obstacle"] = True
    assert not gate.physical_assessment(s,"A")["local_support"]


def test_misassigned_consequences_cannot_replace_physical_outcome_evaluation():
    s = {"goal":"closed", "effect_mode":"misassigned", "effect_assignment":{"A":"B"},
         "oracle_effects_not_model_input_as_numeric_table": {
             "A":{"opening_change_mm":4.,"opening_change":"increases","obstacle":False},
             "B":{"opening_change_mm":-4.,"opening_change":"decreases","obstacle":False},
             "STOP":{"opening_change_mm":0.,"opening_change":"unchanged","obstacle":False}},
         "contract_flags_not_model_input":{"A":False}}
    a = gate.physical_assessment(s,"A")
    assert a["presented_direction_matches_goal"]
    assert not a["absolute_goal_progress"] and not a["local_support"]
    s["goal"] = "open"
    assert gate.physical_assessment(s,"A")["local_support"]
    assert not gate.physical_assessment(s,"A")["presented_direction_matches_goal"]
