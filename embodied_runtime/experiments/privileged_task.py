"""Task boundary for privileged references; policy mechanics stay in the runner."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from .collect_pairs import initial_state_inventory


@dataclass(frozen=True)
class TaskSpec:
    """Declarative task identity and model-facing objective vocabulary."""

    task_id: str
    model_task: str
    flat_instruction: str
    objective_priority: tuple[str, ...]
    objective_criteria: Mapping[str, str]
    objective_effect_codes: Mapping[str, str]
    routing_version: str
    default_trajectory: str
    comparison_tolerance: float = 1e-8
    requires_flat_baseline: bool = True


class TaskAdapter(ABC):
    """Own task/simulator semantics without choosing a winning primitive."""

    spec: TaskSpec

    @abstractmethod
    def actions(self) -> Mapping[str, Mapping[str, Any]]: ...

    @abstractmethod
    def contracts(self, before, predictions, *, collision_aware, task_config): ...

    @abstractmethod
    def make_backend(self, args, *, render: bool): ...

    @abstractmethod
    def measured_outcome(self, world, before, token, execution): ...

    def inventory(self, args):
        return initial_state_inventory(self.spec.task_id, args.libero_root, args.config_dir)

    def goal(self, world):
        return {"task": self.spec.task_id, "instruction": world.task, "satisfied": False}

    def reset_episode(self):
        """Reset adapter-only phase evidence before constructing a fresh world."""

    def prepare_world(self, world):
        """Bind task-selected measurement target without choosing an action."""
        return {"phase": self.spec.task_id, "active_target": world.active_target_object,
                "transition_reason": "single_target_task"}

    def console_outcome(self, outcome):
        return {
            "closure_mm": outcome["closure_mm"],
            "gap_mm": outcome["after"]["distance_to_moving_geometry_mm"],
            "contact": outcome["after"]["moving_contact"],
            "remaining_mm": outcome["after"]["remaining_open_mm"],
        }

    def preflight_fixtures(self):
        return ("reset", "closed_gripper", "loaded_step48")

    def objective_routing(self, pools, order: Sequence[str]):
        """Select the first nonempty task objective without ranking primitives."""
        priority = self.spec.objective_priority
        if set(pools) - set(priority):
            raise ValueError("unknown objective contract")
        objective = next((name for name in priority if pools.get(name)), None)
        union = {name for pool in pools.values() for name in pool}
        if not union.issubset(order) or len(order) != len(set(order)):
            raise ValueError("invalid primitive order or contract membership")
        members = set(pools[objective]) if objective else set()
        return {"version": self.spec.routing_version,
                "source": "deterministic_task_policy",
                "priority": list(priority), "objective": objective,
                "reason": "first_nonempty_contract" if objective else "all_contract_pools_empty",
                "primitive_order": list(order),
                "contract_union": [name for name in order if name in union],
                "motor_pool": [name for name in order if name in members],
                "objective_excluded": {
                    name: "outside_selected_objective" for name in order
                    if name in union and name not in members}}

    def routing_context(self):
        return {}

    def presentation_format(self, predictions, names, objective, compact_version):
        has_witnesses = any(predictions[name].get("reposition_witness") for name in names)
        return compact_version if objective is not None and has_witnesses else "verbose-v1"

    def compact_witness_state(self, before, predictions, names, grip, last, objective):
        """Lossless model view of witness fields with shared invariants factored once."""
        if not names or any(not predictions[name].get("reposition_witness") for name in names):
            raise ValueError("compact witness serialization requires a witness for every candidate")
        common_values = {
            "fp": {f"{predictions[name]['peak_obstacle_force_N']:.1f}" for name in names},
            "fs": {str(int(predictions[name]["after"]["success"])) for name in names},
            "n": {str(predictions[name]["steps"]) for name in names},
            "wp": {f"{predictions[name]['reposition_witness']['peak_obstacle_force_N']:.1f}"
                   for name in names},
            "ws": {str(int(predictions[name]["reposition_witness"]["terminal_success"]))
                   for name in names},
        }
        field_labels = {"fp": "first_force", "fs": "first_success", "n": "controls",
                        "wp": "witness_force", "ws": "witness_success"}
        varying = [key for key, values in common_values.items() if len(values) != 1]
        common = " ".join(f"{field_labels[key]} {next(iter(values))}"
                          for key, values in common_values.items() if len(values) == 1)
        lines = [
            f"{self.spec.model_task.capitalize()}. effect_source oracle_sim; privileged true. "
            "Preview 8 controls/0.4 s; world mm/degrees; nominal motion; retained grip except "
            "open/close. Execute first action only; replan.",
            f"Objective {objective}.",
            (f"State opening {before['remaining_open_mm']:.3f} gap "
             f"{before['distance_to_moving_geometry_mm']:.2f} target "
             f"{int(before['moving_contact'])} obstacle {int(before['obstacle_contact'])} "
             f"grip {'open' if grip < 0 else 'closed'} finger {before['finger_gap_mm']:.2f}."),
        ]
        if last is None:
            lines.append("Last none.")
        else:
            after = last["after"]
            lines.append(
                f"Last {last['action']} closure {last['closure_mm']:.3f} gap "
                f"{last['gap_reduction_mm']:.2f} target {int(after['moving_contact'])} "
                f"obstacle {int(after['obstacle_contact'])} success "
                f"{int(last['official_success'])} controls {last['controls']}."
            )
        schema = ("Rows follow numbered option order: closure gap target > witness "
                  "net_closure net_gap final_target effects")
        if varying:
            schema += " " + " ".join(field_labels[key] for key in varying)
        lines.extend([
            schema + ".",
            "Effects A advance E establish P approach R release W reposition. "
            f"Common {common}.",
        ])
        for index, name in enumerate(names, 1):
            prediction = predictions[name]
            witness = prediction["reposition_witness"]
            codes = "".join(self.spec.objective_effect_codes[value]
                            for value in witness["witnessed_effects"])
            values = {"fp": f"{prediction['peak_obstacle_force_N']:.1f}",
                      "fs": str(int(prediction["after"]["success"])),
                      "n": str(prediction["steps"]),
                      "wp": f"{witness['peak_obstacle_force_N']:.1f}",
                      "ws": str(int(witness["terminal_success"]))}
            suffix = "".join(f" {values[key]}" for key in varying)
            lines.append(
                f"{index} {prediction['closing_mm']:.3f} "
                f"{prediction['geometry_approach_mm']:.2f} "
                f"{int(prediction['after']['moving_contact'])} > {witness['second_input']} "
                f"{witness['net_progress']:.3f} {witness['net_gap_reduction_mm']:.2f} "
                f"{int(witness['terminal_contact'])} {codes}{suffix}"
            )
        return "\n".join(lines) + "\n"

    def presentation(self, before, predictions, names, grip, last, objective, compact_version):
        format_version = self.presentation_format(predictions, names, objective, compact_version)
        if format_version == compact_version:
            state = self.compact_witness_state(before, predictions, names, grip, last, objective)
            instruction = ("Choose one atomic action that best advances the stated local objective. "
                           + self.spec.objective_criteria[objective])
            return state, {"action": {"type": "choice", "instructions": instruction,
                                       "criteria": {name: "" for name in names}}}
        state = (
            f"Task: {self.spec.model_task}. effect_source=oracle_sim; privileged=true. "
            "Preview up to 8 controls/0.4s. XYZ world mm; rotations world degrees; "
            "nominal commands, predicted dynamics; grip retained except open/close.\n"
            f"Current opening={before['remaining_open_mm']:.3f}mm "
            f"gap={before['distance_to_moving_geometry_mm']:.2f}mm "
            f"target_contact={int(before['moving_contact'])} "
            f"obstacle_contact={int(before['obstacle_contact'])} "
            f"grip={'open' if grip < 0 else 'closed'} "
            f"finger_gap={before['finger_gap_mm']:.2f}mm.\n"
        )
        if last is None:
            state += "Last actual: none.\n"
        else:
            after = last["after"]
            state += (f"Last actual: {last['action']}; closure={last['closure_mm']:.3f}mm "
                      f"gap_reduction={last['gap_reduction_mm']:.2f}mm "
                      f"target_contact={int(after['moving_contact'])} "
                      f"obstacle_contact={int(after['obstacle_contact'])} "
                      f"success={int(last['official_success'])} controls={last['controls']}.\n")
        has_witnesses = any(predictions[name].get("reposition_witness") for name in names)
        if has_witnesses:
            common_values = {
                "fp": {f"{predictions[name]['peak_obstacle_force_N']:.1f}" for name in names},
                "fs": {str(int(predictions[name]["after"]["success"])) for name in names},
                "n": {str(predictions[name]["steps"]) for name in names},
                "wp": {f"{predictions[name]['reposition_witness']['peak_obstacle_force_N']:.1f}"
                       for name in names},
                "ws": {str(int(predictions[name]["reposition_witness"]["terminal_success"]))
                       for name in names},
            }
            varying = [key for key, values in common_values.items() if len(values) != 1]
            common = ",".join(f"{key}={next(iter(values))}"
                              for key, values in common_values.items() if len(values) == 1)
            state += (
                "W rows: a c g t > w C G T e"
                f"{' ' + ' '.join(varying) if varying else ''}. "
                "c/g/t=first closure/gap/contact; w=verified second; "
                "C/G/T=two-step net closure/gap/final contact; "
                "e=A advance,E establish,P approach,R release. "
                "Execute a only; replan. "
                "fp/fs/n=first obstacleN/success/controls; "
                "wp/ws=witness obstacleN/success. "
                f"Common: {common}.\n"
            )
        else:
            state += ("Effects: action|closure_mm (positive closes)|gap_reduction_mm "
                      "(positive approaches)|target_contact|obstacle_peak_N|success|controls\n")
        for name in names:
            prediction = predictions[name]
            witness = prediction.get("reposition_witness")
            if witness is None:
                state += (f"{name}|{prediction['closing_mm']:.3f}|"
                          f"{prediction['geometry_approach_mm']:.2f}|"
                          f"{int(prediction['after']['moving_contact'])}|"
                          f"{prediction['peak_obstacle_force_N']:.1f}|"
                          f"{int(prediction['after']['success'])}|{prediction['steps']}\n")
                continue
            codes = "".join(self.spec.objective_effect_codes[value]
                            for value in witness["witnessed_effects"])
            values = {"fp": f"{prediction['peak_obstacle_force_N']:.1f}",
                      "fs": str(int(prediction["after"]["success"])),
                      "n": str(prediction["steps"]),
                      "wp": f"{witness['peak_obstacle_force_N']:.1f}",
                      "ws": str(int(witness["terminal_success"]))}
            suffix = "".join(f" {values[key]}" for key in varying)
            state += (
                f"{name} {prediction['closing_mm']:.3f} "
                f"{prediction['geometry_approach_mm']:.2f} "
                f"{int(prediction['after']['moving_contact'])} > {witness['second_input']} "
                f"{witness['net_progress']:.3f} {witness['net_gap_reduction_mm']:.2f} "
                f"{int(witness['terminal_contact'])} {codes}{suffix}\n"
            )
        instruction = self.spec.flat_instruction
        if objective is not None:
            state = f"Current local objective: {objective}.\n" + state
            instruction = ("Choose one atomic action that best advances the stated local objective. "
                           + self.spec.objective_criteria[objective])
        return state, {"action": {"type": "choice", "instructions": instruction,
                                   "criteria": {name: "" for name in names}}}

    def compare_prediction(self, world, prediction, outcome, execution):
        error = float(np.max(np.abs(world.env.sim.get_state().flatten()
                                    - np.asarray(prediction["sim_state_after"]))))
        comparisons = {
            "state_max_error": error,
            "closure_error_mm": abs(outcome["closure_mm"] - prediction["closing_mm"]),
            "gap_reduction_error_mm": abs(outcome["gap_reduction_mm"]
                                          - prediction["geometry_approach_mm"]),
            "obstacle_force_error_N": abs(execution["peak_obstacle_force_N"]
                                          - prediction["peak_obstacle_force_N"]),
            "controls_match": outcome["controls"] == prediction["steps"],
            "success_match": outcome["official_success"] == prediction["after"]["success"],
            "target_contact_match": (outcome["after"]["moving_contact"]
                                     == prediction["after"]["moving_contact"]),
            "obstacle_contact_match": (outcome["after"]["obstacle_contact"]
                                       == prediction["after"]["obstacle_contact"]),
            "obstacle_pairs_match": (sorted(execution["obstacle_pairs_seen"])
                                     == sorted(prediction["obstacle_pairs_seen"])),
        }
        comparisons["passed"] = (
            all(comparisons[key] <= self.spec.comparison_tolerance for key in
                ("state_max_error", "closure_error_mm", "gap_reduction_error_mm",
                 "obstacle_force_error_N"))
            and all(comparisons[key] for key in
                    ("controls_match", "success_match", "target_contact_match",
                     "obstacle_contact_match", "obstacle_pairs_match"))
            and not execution["execution_contract_violation"]
        )
        return comparisons


TOP_DRAWER_SPEC = TaskSpec(
    task_id="top_drawer",
    model_task="close top drawer",
    flat_instruction=(
        "Choose one action to close the drawer using its predicted effects. "
        "Prefer completion, closure, then contact or approach; avoid obstacle force."
    ),
    objective_priority=("advance_target", "establish_contact", "approach_target",
                        "release_contact", "reposition"),
    objective_criteria={
        "advance_target": "Prefer actual task completion, otherwise greater predicted closure without unnecessary obstacle force.",
        "establish_contact": "Prefer useful contact with closure.",
        "approach_target": "Prefer substantial predicted surface-gap reduction.",
        "release_contact": "Release the obstruction with less loss of task progress.",
        "reposition": "Compare the verified two-step net effects rather than demanding immediate progress from the first input. Execute only the first input; replan.",
    },
    objective_effect_codes={"advance_target": "A", "establish_contact": "E",
                            "approach_target": "P", "release_contact": "R",
                            "reposition": "W"},
    routing_version="fixed-contract-objective-v1",
    default_trajectory="/home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1",
)


class TopDrawerTaskAdapter(TaskAdapter):
    spec = TOP_DRAWER_SPEC

    def actions(self):
        from jev_libero.actions import ACTIONS
        return ACTIONS

    def contracts(self, before, predictions, *, collision_aware, task_config):
        from jev_libero.policy import contracts
        return contracts(before, predictions, collision_aware=collision_aware,
                         task_config=task_config)

    def make_backend(self, args, *, render):
        return LiberoWorldBackend.from_task(
            self.spec.task_id, seed=args.seed, init_state_id=args.init_state_id,
            render=render, libero_root=args.libero_root, config_dir=args.config_dir
        )

    def measured_outcome(self, world, before, token, execution):
        """Fresh drawer measurements, never candidate predictions."""
        after = world.features()
        joint = float(world.data.qpos[world.qindex])
        success = bool(world.env.check_success())
        if joint != after["qpos_m"] or success != after["success"]:
            raise RuntimeError("independent live evaluator disagrees with feature reading")
        return {"action": token, "before": before, "after": after,
                "actual_joint_qpos_m": joint, "official_success": success,
                "closure_mm": 1000. * (joint - before["qpos_m"]),
                "gap_reduction_mm": (before["distance_to_moving_geometry_mm"]
                                     - after["distance_to_moving_geometry_mm"]),
                "controls": execution["environment_step_count"],
                "obstacle_peak_N": execution["peak_obstacle_force_N"]}


TOP_DRAWER_ADAPTER = TopDrawerTaskAdapter()
