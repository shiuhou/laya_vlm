"""Task-specific semantics for the privileged wine-bottle / bottom-drawer reference."""
from __future__ import annotations

from pathlib import Path

from ..adapters.libero import LiberoWorldBackend
from .collect_pairs import initial_state_inventory
from .privileged_task import TaskAdapter, TaskSpec


TASK_DIR = Path(__file__).with_name("tasks")
CONFIG_PATH = TASK_DIR / "wine_bottle_bottom_drawer.json"
BDDL_PATH = TASK_DIR / "KITCHEN_SCENE4_put_the_wine_bottle_in_the_bottom_drawer_and_close_it.bddl"


WINE_BOTTLE_DRAWER_SPEC = TaskSpec(
    task_id="wine_bottle_bottom_drawer",
    model_task="pick up the wine bottle, place and release it inside the bottom drawer, then close the drawer",
    flat_instruction="Choose one predicted atomic action that advances the current manipulation task.",
    objective_priority=(
        "release_object", "advance_drawer", "establish_drawer_contact", "approach_drawer",
        "place_object", "transport_object", "establish_grasp", "approach_object",
        "release_contact", "release_obstruction", "reposition",
    ),
    objective_criteria={
        "approach_object": "Prefer greater bottle/gripper alignment gain and a graspable aperture without pushing the bottle.",
        "establish_grasp": "Prefer predicted bilateral fingerpad contact while limiting bottle displacement.",
        "transport_object": "Preserve bilateral contact while lifting for clearance or reducing horizontal drawer-goal error.",
        "place_object": "Reduce full-object violation of the drawer close envelope while preserving the bilateral grasp.",
        "release_object": "Release only when the bottle is inside and its full extent and orientation fit the drawer close envelope.",
        "approach_drawer": "Prefer substantial gripper-to-drawer surface-gap reduction while preserving released placement_fit.",
        "establish_drawer_contact": "Prefer useful bottom-drawer contact while preserving released placement_fit.",
        "advance_drawer": "Prefer official task completion, otherwise greater closure while placement_fit remains valid.",
        "release_contact": "Remove obstructing drawer contact with the least loss of closure.",
        "release_obstruction": "Remove obstructing contact while preserving an existing bottle grasp.",
        "reposition": "Compare verified two-step effects; execute only the first primitive and reobserve.",
    },
    objective_effect_codes={
        "release_object": "R", "advance_drawer": "D", "establish_drawer_contact": "C",
        "approach_drawer": "A", "place_object": "P", "transport_object": "T",
        "establish_grasp": "G", "approach_object": "O", "release_contact": "X",
        "release_obstruction": "B", "reposition": "W",
    },
    routing_version="wine-bottle-bottom-drawer-objective-v1",
    default_trajectory="",
    requires_flat_baseline=False,
)


class WineBottleBottomDrawerAdapter(TaskAdapter):
    spec = WINE_BOTTLE_DRAWER_SPEC

    def __init__(self):
        self.reset_episode()

    def reset_episode(self):
        self.phase = "approach_object"
        self.active_target = "wine_bottle_1"
        self.transition_reason = "episode_reset_object_not_contained"
        self.released_inside_seen = False

    def task_config(self):
        from jev_libero.config import load_task

        config = load_task(CONFIG_PATH)
        config["binding"]["bddl_file"] = str(BDDL_PATH.resolve())
        return config

    def actions(self):
        from jev_libero.actions import ACTIONS
        return ACTIONS

    def contracts(self, before, predictions, *, collision_aware, task_config):
        from jev_libero.policy import contracts
        return contracts(before, predictions, collision_aware=collision_aware,
                         task_config=task_config)

    def inventory(self, args):
        return initial_state_inventory(self.task_config(), args.libero_root, args.config_dir)

    def make_backend(self, args, *, render):
        from jev_libero.world import World

        self.reset_episode()
        world = World(
            seed=args.seed, init_index=args.init_state_id, render=render,
            task_config=self.task_config(), libero_root=args.libero_root,
            config_dir=args.config_dir,
        )
        return LiberoWorldBackend(world)

    def prepare_world(self, world):
        state = world.features()
        held = bool(state["valid_grasp_relation"])
        inside = bool(state["object_inside_drawer"])
        placement_fit = bool(state["placement_fit"])
        released = bool(state["object_released"])
        previous = self.phase
        if self.released_inside_seen and not inside:
            raise RuntimeError("unrecoverable_object_loss_after_verified_release")
        if released:
            self.released_inside_seen = True
            phase = "close_drawer"
            target, joint = "white_cabinet_1", "bottom_level"
            reason = "bottle_inside_and_released"
        elif held or inside:
            phase = "transport_place_release"
            target, joint = "wine_bottle_1", None
            reason = ("bilateral_bottle_contact" if held
                      else "contained_bottle_still_in_gripper_contact")
        else:
            phase = "approach_and_grasp"
            target, joint = "wine_bottle_1", None
            reason = "bottle_not_held_or_released_inside"
        world.set_active_target(target, joint)
        self.phase, self.active_target = phase, target
        self.transition_reason = reason if phase != previous else f"phase_retained:{reason}"
        return {"phase": phase, "previous_phase": previous, "active_target": target,
                "active_joint_suffix": joint, "transition_reason": self.transition_reason,
                "held": held, "object_inside_drawer": inside,
                "object_released": released,
                "placement_fit": placement_fit,
                "placement_violation_mm": state["placement_violation_mm"],
                "drawer_opening_mm": state["remaining_open_mm"]}

    def routing_context(self):
        return {"phase": self.phase, "active_target": self.active_target,
                "transition_reason": self.transition_reason}

    def goal(self, world):
        state = world.features()
        return {"task": self.spec.task_id, "instruction": world.task,
                "satisfied": bool(state["success"]), "phase": self.phase,
                "held": bool(state["valid_grasp_relation"]),
                "object_inside_drawer": bool(state["object_inside_drawer"]),
                "placement_fit": bool(state["placement_fit"]),
                "object_released": bool(state["object_released"]),
                "drawer_closed": bool(state["drawer_closed"])}

    def presentation_format(self, predictions, names, objective, compact_version):
        return "multistage-effects-v1"

    def presentation(self, before, predictions, names, grip, last, objective, compact_version):
        rows = [
            f"Task: {self.spec.model_task}. effect_source=oracle_sim; privileged=true.",
            f"Current local objective: {objective}. Phase: {self.phase}. Active contact target: {self.active_target}.",
            (f"State held={int(before['valid_grasp_relation'])} inside={int(before['object_inside_drawer'])} "
             f"placement_fit={int(before['placement_fit'])} fit_violation="
             f"{before['placement_violation_mm']:.2f}mm "
             f"released={int(before['object_released'])} "
             f"drawer_closed={int(before['drawer_closed'])} opening={before['remaining_open_mm']:.3f}mm "
             f"alignment={before['grasp_alignment_mm']:.2f}mm goal_xy={before['goal_xy_error_mm']:.2f}mm "
             f"goal_distance={before['goal_distance_mm']:.2f}mm surface_gap="
             f"{before['distance_to_moving_geometry_mm']:.2f}mm target_contact={int(before['moving_contact'])} "
             f"obstacle_contact={int(before['obstacle_contact'])} grip={'open' if grip < 0 else 'closed'}."),
        ]
        if last is None:
            rows.append("Last actual: none.")
        else:
            after = last["after"]
            rows.append(
                f"Last actual: {last['action']} held={int(after['valid_grasp_relation'])} "
                f"inside={int(after['object_inside_drawer'])} released={int(after['object_released'])} "
                f"placement_fit={int(after['placement_fit'])} "
                f"closure={last['closure_mm']:.3f}mm "
                f"success={int(last['official_success'])} controls={last['controls']}."
            )
        rows.append(
            "Effects: action|alignment_gain_mm|height_gain_mm|xy_gain_mm|delivery_progress_mm|"
            "inside|held|fit|fit_progress_mm|released|closure_mm|gap_reduction_mm|"
            "target_contact|obstacle_peak_N|success|controls"
        )
        for name in names:
            p = predictions[name]
            after = p["after"]
            line = (
                f"{name}|{p['alignment_gain_mm']:.2f}|{p['height_gain_mm']:.2f}|{p['xy_gain_mm']:.2f}|"
                f"{p['delivery_progress_mm']:.2f}|{int(after['object_inside_drawer'])}|"
                f"{int(after['valid_grasp_relation'])}|{int(after['placement_fit'])}|"
                f"{p['placement_fit_progress_mm']:.2f}|{int(after['object_released'])}|"
                f"{p['closing_mm']:.3f}|"
                f"{p['geometry_approach_mm']:.2f}|{int(after['moving_contact'])}|"
                f"{p['peak_obstacle_force_N']:.1f}|{int(after['success'])}|{p['steps']}"
            )
            witness = p.get("reposition_witness")
            if witness:
                effects = ",".join(witness["witnessed_effects"])
                line += (f" > {witness['second_input']} net_progress={witness['net_progress']:.3f} "
                         f"net_gap={witness['net_gap_reduction_mm']:.2f} "
                         f"final_contact={int(witness['terminal_contact'])} "
                         f"success={int(witness['terminal_success'])} effects={effects}")
            rows.append(line)
        instruction = ("Choose one atomic action that best advances the stated local objective. "
                       + self.spec.objective_criteria[objective])
        return "\n".join(rows) + "\n", {
            "action": {"type": "choice", "instructions": instruction,
                       "criteria": {name: "" for name in names}}
        }

    def measured_outcome(self, world, before, token, execution):
        after = world.features()
        joint = float(after["drawer_qpos_m"])
        success = bool(world.env.check_success())
        if success != after["success"]:
            raise RuntimeError("independent LIBERO evaluator disagrees with feature reading")
        result = {
            "action": token, "before": before, "after": after,
            "actual_joint_qpos_m": joint, "official_success": success,
            "closure_mm": 1000.0 * (joint - before["drawer_qpos_m"]),
            "gap_reduction_mm": (before["distance_to_moving_geometry_mm"]
                                 - after["distance_to_moving_geometry_mm"]),
            "controls": execution["environment_step_count"],
            "obstacle_peak_N": execution["peak_obstacle_force_N"],
            "phase": self.phase, "objective_transition_reason": self.transition_reason,
            "held": bool(after["valid_grasp_relation"]),
            "object_inside_drawer": bool(after["object_inside_drawer"]),
            "placement_fit": bool(after["placement_fit"]),
            "placement_violation_mm": after["placement_violation_mm"],
            "object_released": bool(after["object_released"]),
            "drawer_opening_mm": after["remaining_open_mm"],
            "drawer_closed": bool(after["drawer_closed"]),
        }
        if result["object_released"]:
            self.released_inside_seen = True
        return result

    def console_outcome(self, outcome):
        after = outcome["after"]
        return {
            "phase": outcome["phase"], "held": outcome["held"],
            "inside": outcome["object_inside_drawer"],
            "placement_fit": outcome["placement_fit"],
            "released": outcome["object_released"],
            "closure_mm": outcome["closure_mm"],
            "opening_mm": outcome["drawer_opening_mm"],
            "gap_mm": after["distance_to_moving_geometry_mm"],
            "contact": after["moving_contact"],
        }

    def preflight_fixtures(self):
        return ("reset", "closed_gripper")


WINE_BOTTLE_DRAWER_ADAPTER = WineBottleBottomDrawerAdapter()
