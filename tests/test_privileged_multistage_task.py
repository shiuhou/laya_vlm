from types import SimpleNamespace

import pytest

from embodied_runtime.experiments.privileged_multistage_task import (
    BDDL_PATH,
    WINE_BOTTLE_DRAWER_ADAPTER,
    WINE_BOTTLE_DRAWER_SPEC,
)


def test_task_declares_native_conjunctive_success_and_existing_27_actions():
    adapter = WINE_BOTTLE_DRAWER_ADAPTER
    config = adapter.task_config()
    assert config["binding"]["task"] == (
        "KITCHEN_SCENE4_put_the_wine_bottle_in_the_bottom_drawer_of_the_cabinet"
    )
    assert config["binding"]["bddl_file"] == str(BDDL_PATH.resolve())
    bddl = BDDL_PATH.read_text()
    assert "(In wine_bottle_1 white_cabinet_1_bottom_region)" in bddl
    assert "(Close white_cabinet_1_bottom_region)" in bddl
    assert len(adapter.actions()) == 27
    assert not WINE_BOTTLE_DRAWER_SPEC.requires_flat_baseline


def test_phase_router_switches_measurement_target_without_selecting_a_primitive():
    adapter = WINE_BOTTLE_DRAWER_ADAPTER
    adapter.reset_episode()
    state = {
        "bilateral_target_contact": False,
        "valid_grasp_relation": False,
        "object_inside_drawer": False,
        "placement_fit": False,
        "placement_violation_mm": 100.0,
        "object_released": False,
        "remaining_open_mm": 160.0,
    }
    bindings = []
    world = SimpleNamespace(
        features=lambda: dict(state),
        set_active_target=lambda obj, joint: bindings.append((obj, joint)),
    )
    assert adapter.prepare_world(world)["phase"] == "approach_and_grasp"
    state.update(bilateral_target_contact=True, valid_grasp_relation=True)
    assert adapter.prepare_world(world)["phase"] == "transport_place_release"
    state.update(bilateral_target_contact=False, valid_grasp_relation=False,
                 object_inside_drawer=True, placement_fit=True,
                 placement_violation_mm=0.0)
    assert adapter.prepare_world(world)["phase"] == "transport_place_release"
    state.update(object_released=True)
    assert adapter.prepare_world(world)["phase"] == "close_drawer"
    assert bindings[-1] == ("white_cabinet_1", "bottom_level")
    state.update(object_inside_drawer=False, object_released=False)
    with pytest.raises(RuntimeError, match="object_loss"):
        adapter.prepare_world(world)


def test_release_and_placement_contracts_encode_observed_physical_transitions():
    from jev_libero.config import expression

    config = WINE_BOTTLE_DRAWER_ADAPTER.task_config()
    thresholds = config["thresholds"]["collision_aware"]
    base = {
        "bilateral_target_contact": True,
        "valid_grasp_relation": True,
        "object_inside_drawer": False,
        "placement_fit": False,
        "placement_violation_mm": 3.0,
        "placement_axis_violation_mm": [3.0, 0.0, 0.0],
        "object_released": False,
        "clearance_mm": 12.0,
        "target_destination_contact": True,
    }
    context = {
        "before": base,
        "after": {**base, "object_inside_drawer": True, "placement_fit": True,
                  "placement_violation_mm": 0.0},
        "p": {"delivery_progress_mm": 3.0, "gap_change_mm": 0.0,
              "placement_fit_progress_mm": 3.0, "valid_grasp_maintained": True},
        "thresholds": thresholds,
    }
    assert expression(config["contracts"]["place_object"], context)
    release_context = {
        "before": {**context["after"], "object_released": False},
        "after": {**context["after"], "object_released": True},
        "p": {"gap_change_mm": 3.0},
        "thresholds": thresholds,
    }
    assert expression(config["contracts"]["release_object"], release_context)
    release_context["p"]["gap_change_mm"] = 0.0
    assert not expression(config["contracts"]["release_object"], release_context)
    release_context["p"]["gap_change_mm"] = 3.0
    release_context["before"]["placement_fit"] = False
    assert not expression(config["contracts"]["release_object"], release_context)


def test_drawer_contract_requires_placement_fit_throughout_execution():
    from jev_libero.config import expression

    config = WINE_BOTTLE_DRAWER_ADAPTER.task_config()
    context = {
        "before": {
            "placement_fit": True,
            "object_inside_drawer": True,
            "object_released": True,
        },
        "after": {
            "placement_fit": True,
            "object_inside_drawer": True,
            "object_released": True,
            "success": False,
        },
        "p": {"placement_fit_maintained": True, "closing_mm": 1.0},
        "thresholds": config["thresholds"]["collision_aware"],
    }
    contract = config["contracts"]["advance_drawer"]
    assert expression(contract, context)
    context["p"]["placement_fit_maintained"] = False
    assert not expression(contract, context)


def test_multistage_presentation_preserves_candidate_order_and_release_effect():
    adapter = WINE_BOTTLE_DRAWER_ADAPTER
    adapter.reset_episode()
    before = {
        "bilateral_target_contact": True, "valid_grasp_relation": True,
        "object_inside_drawer": False, "placement_fit": False,
        "placement_violation_mm": 5.0,
        "object_released": False, "drawer_closed": False, "remaining_open_mm": 150.0,
        "grasp_alignment_mm": 4.0, "goal_xy_error_mm": 20.0,
        "goal_distance_mm": 30.0, "distance_to_moving_geometry_mm": 5.0,
        "moving_contact": True, "obstacle_contact": False, "success": False,
    }
    after = {**before, "object_inside_drawer": True, "object_released": True,
             "bilateral_target_contact": False, "valid_grasp_relation": False,
             "placement_fit": True, "placement_violation_mm": 0.0}
    effect = {
        "after": after, "alignment_gain_mm": 1.0, "height_gain_mm": -2.0,
        "xy_gain_mm": 3.0, "delivery_progress_mm": 4.0, "closing_mm": 0.0,
        "placement_fit_progress_mm": 5.0,
        "geometry_approach_mm": 2.0, "peak_obstacle_force_N": 0.0, "steps": 8,
    }
    names = ["open", "x+3mm"]
    state, questions = adapter.presentation(
        before, {name: effect for name in names}, names, 1.0, None,
        "release_object", "unused",
    )
    assert state.index("open|") < state.index("x+3mm|")
    assert "inside|held|fit|fit_progress_mm|released" in state
    assert list(questions["action"]["criteria"]) == names
