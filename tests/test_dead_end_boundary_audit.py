from copy import deepcopy

from embodied_runtime.experiments.dead_end_boundary_audit import clause_audit


def config():
    return {
        "contact": {
            "reject_new_obstacles": True,
            "require_obstacle_free_endpoint": True,
            "release_priority": ["blocked", "all"],
        },
        "thresholds": {"collision_aware": {"progress": .01, "approach_mm": 2.}},
    }


def features(**updates):
    value = {"moving_contact": False, "obstacle_contact": False, "success": False,
             "contacts": []}
    value.update(updates)
    return value


def prediction(**updates):
    value = {"after": features(), "closing_mm": 0., "geometry_approach_mm": 0.,
             "peak_obstacle_force_N": 0., "obstacle_pairs_seen": [], "steps": 8}
    value.update(updates)
    return value


def test_approach_requires_distance_effect_and_nonregression():
    row = clause_audit(features(), prediction(geometry_approach_mm=2.), config())
    assert row["contracts"]["approach_target"]["pass"]
    assert row["passed_contracts"] == ["approach_target"]
    row = clause_audit(features(), prediction(geometry_approach_mm=2., closing_mm=-.0100001), config())
    assert not row["contracts"]["approach_target"]["pass"]
    assert not row["passed_contracts"]


def test_contact_transition_fails_only_closure_guard_at_dead_boundary():
    row = clause_audit(features(), prediction(
        after=features(moving_contact=True),
        geometry_approach_mm=2.732324299728142,
        closing_mm=-.108773173028126,
    ), config())
    establish = row["contracts"]["establish_contact"]
    assert establish["before_no_target_contact"]
    assert establish["after_target_contact"]
    assert not establish["closure_ge_negative_progress"]
    assert not establish["pass"]
    approach = row["contracts"]["approach_target"]
    assert [approach[key] for key in ("before_no_target_contact", "gap_reduction_ge_threshold",
                                      "endpoint_no_obstacle_contact")] == [True, True, True]
    assert not approach["closure_ge_negative_progress"]


def test_positive_closure_passes_advance_contract():
    row = clause_audit(features(), prediction(closing_mm=.01), config())
    assert row["contracts"]["advance_target"]["pass"]
    assert row["passed_contracts"] == ["advance_target"]


def test_predicted_success_can_pass_advance_without_closure():
    row = clause_audit(features(), prediction(after=features(success=True), closing_mm=-1.), config())
    assert row["contracts"]["advance_target"]["pass"]


def test_new_obstacle_contact_vetoes_otherwise_valid_effect():
    after = features(obstacle_contact=True)
    row = clause_audit(features(), prediction(
        after=after, closing_mm=1., obstacle_pairs_seen=[["hand", "obstacle"]],
    ), config())
    assert row["contracts"]["advance_target"]["pass"]
    assert not row["collision_gate"]["pass"]
    assert not row["passed_contracts"]


def test_release_requires_existing_pair_and_removal():
    before = features(contacts=[{"hand": "h", "other": "o", "obstacle": True,
                                 "moving_target": False}])
    row = clause_audit(before, prediction(after=features()), config())
    assert row["contracts"]["release_contact"]["pass"]
    kept = deepcopy(before)
    row = clause_audit(before, prediction(after=kept), config())
    assert not row["contracts"]["release_contact"]["pass"]


def test_reposition_is_false_without_explicit_witness():
    row = clause_audit(features(), prediction(), config())
    assert not row["contracts"]["reposition"]["pass"]
    row = clause_audit(features(), prediction(reposition_witness={"second_input": "x+3mm"}), config())
    assert row["contracts"]["reposition"]["pass"]
    assert "reposition" in row["passed_contracts"]
