"""Offline interaction attribution and frozen Task-2 boundary audit; never calls Laya."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .privileged_multistage_task import WINE_BOTTLE_DRAWER_ADAPTER
from .privileged_task import TOP_DRAWER_ADAPTER


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), indent=2) + "\n")


def _arguments(args):
    return SimpleNamespace(
        seed=1,
        init_state_id=0,
        libero_root=args.libero_root,
        config_dir=args.config_dir,
    )


def audit_task1(args):
    from jev_libero.interaction import classify_interaction
    from jev_libero.world import relation_summary

    sources = [Path(value) for value in args.task1_runs]
    results = []
    for source in sources:
        backend = TOP_DRAWER_ADAPTER.make_backend(_arguments(args), render=False)
        world = backend.world
        try:
            evidence = json.loads((source / "reference-evidence.json").read_text())
            actions = [row["outcome"]["action"] for row in evidence["trace"]]
            artifacts = sorted((source / "trajectory").glob("action-*.npz"))
            if len(actions) != len(artifacts):
                raise ValueError("Task-1 action/evidence length mismatch")
            initial = world.features()
            rows, maximum_error = [], 0.0
            for step, (action, artifact) in enumerate(zip(actions, artifacts)):
                before = world.features()
                relation_trace = {name: [] for name in world.config["interaction_relations"]}
                controls = []
                with np.load(artifact) as saved:
                    commands = np.asarray(saved["commands"])
                    states_before = np.asarray(saved["states_before"])
                    expected_after = np.asarray(saved["state_after"])
                for index, command in enumerate(commands):
                    state_error = float(
                        np.max(np.abs(world.env.sim.get_state().flatten() - states_before[index]))
                    )
                    maximum_error = max(maximum_error, state_error)
                    control_before = world.features()
                    world.obs, _, _, _ = world.env.step(command)
                    control_after = world.features()
                    for name in relation_trace:
                        relation_trace[name].append(bool(control_after[name]))
                    controls.append(
                        {
                            "index": index,
                            "closure_mm": control_before["remaining_open_mm"]
                            - control_after["remaining_open_mm"],
                            "valid_handle_contact": control_after["valid_handle_contact"],
                            "non_designated_robot_contact": control_after[
                                "non_designated_robot_contact"
                            ],
                            "contacts": control_after["contacting_robot_links"],
                            "effector_center_mm": control_after[
                                "designated_effector_center_mm"
                            ],
                            "handle_center_mm": control_after["handle_center_mm"],
                            "joint_axis_world": control_after["drawer_joint_axis"],
                        }
                    )
                maximum_error = max(
                    maximum_error,
                    float(np.max(np.abs(world.env.sim.get_state().flatten() - expected_after))),
                )
                after = world.features()
                closing = before["remaining_open_mm"] - after["remaining_open_mm"]
                relations = relation_summary(relation_trace)
                context = {
                    "before": before,
                    "after": after,
                    "relations": relations,
                    "p": {"closing_mm": closing},
                    "thresholds": world.config["thresholds"]["collision_aware"],
                }
                evaluation = classify_interaction(
                    world.config["interaction_evaluation"]["drawer_progress"], context
                )
                rows.append(
                    {
                        "step": step,
                        "action": action,
                        "controls": len(commands),
                        "opening_before_mm": before["remaining_open_mm"],
                        "opening_after_mm": after["remaining_open_mm"],
                        "closure_mm": closing,
                        "relations": relations,
                        "evaluation": evaluation,
                        "control_evidence": controls,
                    }
                )
            final = world.features()
            totals = {}
            for label in (
                "interaction_valid",
                "interaction_invalid",
                "interaction_ambiguous",
                "no_goal_progress",
            ):
                selected = [row for row in rows if row["evaluation"]["classification"] == label]
                totals[label] = {
                    "actions": len(selected),
                    "net_closure_mm": sum(row["closure_mm"] for row in selected),
                    "positive_closure_mm": sum(max(0.0, row["closure_mm"]) for row in selected),
                    "negative_closure_mm": sum(min(0.0, row["closure_mm"]) for row in selected),
                }
            results.append(
                {
                    "run_id": source.name,
                    "source": {
                        "episodes_sha256": _hash(source / "episodes.jsonl"),
                        "manifest_sha256": _hash(source / "manifest.json"),
                    },
                    "controls": sum(row["controls"] for row in rows),
                    "opening_start_mm": initial["remaining_open_mm"],
                    "opening_final_mm": final["remaining_open_mm"],
                    "official_success": bool(world.env.check_success()),
                    "maximum_replay_state_error": maximum_error,
                    "totals": totals,
                    "actions": rows,
                }
            )
        finally:
            backend.close()
    output = {
        "schema_version": "interaction-attribution-v2",
        "purpose": "observational_replay_not_policy_execution",
        "classification": {
            "valid": "required relation maintained, no forbidden relation, axis motion supported",
            "invalid": "forbidden without required relation, or opposed axis motion",
            "ambiguous": "mixed, intermittent, inertial, or otherwise incomplete causal evidence",
        },
        "runs": results,
    }
    _write(args.task1_output, output)
    return output


def _expression_tree(node, context, path="root"):
    from jev_libero.config import expression

    value = expression(node, context)
    result = {"path": path, "expression": node, "value": _jsonable(value)}
    if isinstance(node, dict):
        op, arguments = next(iter(node.items()))
        result["operator"] = op
        if op not in ("ref", "not", "norm", "count"):
            children = arguments if isinstance(arguments, list) else [arguments]
            result["children"] = [
                _expression_tree(child, context, f"{path}.{op}[{index}]")
                for index, child in enumerate(children)
                if isinstance(child, (dict, list))
            ]
        elif isinstance(arguments, dict):
            result["children"] = [_expression_tree(arguments, context, f"{path}.{op}")]
    return result


def _first_false(tree):
    if bool(tree["value"]):
        return None
    operator = tree.get("operator")
    children = tree.get("children", [])
    if operator == "all":
        return next((_first_false(child) for child in children if not bool(child["value"])), tree["path"])
    if operator == "any":
        return tree["path"] + ":all_alternatives_false"
    return tree["path"]


def _contract_audit(world, before, predictions, collision_aware=True):
    from jev_libero.policy import blocked_pairs, contact_pairs

    cfg = world.config
    rules = cfg["contact"]
    blocked = blocked_pairs(before)
    pair_groups = {"blocked": blocked, "all": contact_pairs(before)}
    release_pairs = next(
        (pair_groups[key] for key in rules["release_priority"] if pair_groups[key]), set()
    )
    thresholds = cfg["thresholds"]["collision_aware" if collision_aware else "ordinary"]
    output = {}
    for name, prediction in predictions.items():
        after = prediction["after"]
        new_obstacles = sorted(
            set(map(tuple, prediction["obstacle_pairs_seen"])) - blocked
        )
        endpoint_obstacle = bool(after["obstacle_contact"])
        collision_pass = not (
            collision_aware
            and (
                (rules["reject_new_obstacles"] and new_obstacles)
                or (rules["require_obstacle_free_endpoint"] and endpoint_obstacle)
            )
        )
        context = {
            "before": before,
            "after": after,
            "p": prediction,
            "thresholds": thresholds,
            "released_required_contacts": bool(release_pairs)
            and not bool(release_pairs & contact_pairs(after)),
            "has_reposition_witness": bool(prediction.get("reposition_witness")),
        }
        contracts = {}
        for objective, clause in cfg["contracts"].items():
            tree = _expression_tree(clause, context)
            contracts[objective] = {
                "passed": bool(tree["value"]),
                "first_failure": _first_false(tree),
                "tree": tree,
            }
        eligible = [key for key, value in contracts.items() if value["passed"]] if collision_pass else []
        output[name] = {
            "collision_gate": {
                "passed": collision_pass,
                "new_obstacle_pairs": new_obstacles,
                "endpoint_obstacle": endpoint_obstacle,
            },
            "eligible_contracts": eligible,
            "contracts": contracts,
            "effect": prediction,
        }
    return output


def _combine_two_step(world, before, first_result, second_prediction):
    from jev_libero.config import project
    from jev_libero.world import relation_summary

    end = second_prediction["after"]
    combined_trace = {
        name: [
            *first_result["relation_trace"].get(name, []),
            *second_prediction["relation_trace"].get(name, []),
        ]
        for name in set(first_result["relation_trace"]) | set(second_prediction["relation_trace"])
    }
    summary = relation_summary(combined_trace)
    return {
        **second_prediction,
        **project(
            world.config["predictions"],
            {"before": before, "after": end, "relations": summary},
        ),
        "relation_trace": combined_trace,
        "relation_summary": summary,
        "geometry_approach_mm": before["distance_to_moving_geometry_mm"]
        - end["distance_to_moving_geometry_mm"],
        "obstacle_pairs_seen": sorted(
            set(first_result["obstacle_pairs_seen"])
            | set(map(tuple, second_prediction["obstacle_pairs_seen"]))
        ),
        "peak_obstacle_force_N": max(
            first_result["peak_obstacle_force_N"], second_prediction["peak_obstacle_force_N"]
        ),
    }


def _snapshot_hashes(world, directory):
    from jev_libero.world import Snapshot

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = Snapshot(world)
    state_path = directory / "task2-boundary-sim-state.npy"
    np.save(state_path, world.env.sim.get_state().flatten())
    controller_path = directory / "task2-boundary-controller.pkl"
    controller_path.write_bytes(
        pickle.dumps(
            {
                "controller": snapshot.controller,
                "robot": snapshot.robot,
                "gripper": snapshot.gripper,
                "clock": snapshot.clock,
                "rng": snapshot.rng,
                "py_rng": snapshot.py_rng,
            },
            protocol=5,
        )
    )
    return {
        "sim_state_path": str(state_path),
        "sim_state_sha256": _hash(state_path),
        "controller_path": str(controller_path),
        "controller_sha256": _hash(controller_path),
    }


def _geometry_validation(world, features):
    measurement = world.config["measurements"]["drawer_frame_geometry"]
    site = world.env.sim.model.site_name2id(measurement["frame_site"])
    site_body = int(world.model.site_bodyid[site])
    joint = world.named_joint_id("white_cabinet_1", "bottom_level")
    joint_body = int(world.model.jnt_bodyid[joint])
    body = site_body
    ancestry = []
    while body:
        ancestry.append(world.env.sim.model.body_id2name(body))
        if body == joint_body:
            break
        body = int(world.model.body_parentid[body])
    frame_position = np.asarray(world.data.site_xpos[site])
    frame_rotation = np.asarray(world.data.site_xmat[site]).reshape(3, 3)
    points = world.measurements.points(measurement["entity"])
    local = (points - frame_position) @ frame_rotation * 1000
    recomputed = np.array([local.min(axis=0), local.max(axis=0)])
    recorded = np.asarray(features["object_drawer_frame_bounds_mm"])
    return {
        "frame_site": measurement["frame_site"],
        "site_body": world.env.sim.model.body_id2name(site_body),
        "drawer_joint_body": world.env.sim.model.body_id2name(joint_body),
        "site_descends_from_joint_body": joint_body in [
            world.env.sim.model.body_name2id(name) for name in ancestry
        ],
        "body_ancestry": ancestry,
        "site_half_extent_mm": (np.asarray(world.model.site_size[site]) * 1000).tolist(),
        "bounds_recompute_max_error_mm": float(np.max(np.abs(recomputed - recorded))),
        "limitation": (
            "The LIBERO region site is an articulated containment box. Its frame and bounds are "
            "verified here; equivalence to the complete collision-swept closing volume remains unproven."
        ),
    }


def _replay_comparison_with_current_contracts(args, rows):
    """Replay archived diagnostic choices and audit them under the current contracts."""
    from jev_libero.actions import ACTIONS

    backend = WINE_BOTTLE_DRAWER_ADAPTER.make_backend(_arguments(args), render=False)
    world = backend.world
    grip = -1.0
    replay = []
    try:
        for archived in rows:
            preparation = WINE_BOTTLE_DRAWER_ADAPTER.prepare_world(world)
            before, predictions = world.predict_all(grip)
            pools, _ = WINE_BOTTLE_DRAWER_ADAPTER.contracts(
                before,
                predictions,
                collision_aware=True,
                task_config=world.config,
            )
            eligible = [
                action
                for action in ACTIONS
                if any(action in candidates for candidates in pools.values())
            ]
            objectives = [
                objective
                for objective, candidates in pools.items()
                if archived["choice"] in candidates
            ]
            row = {
                "step": archived["step"],
                "archived_action": archived["choice"],
                "preparation": preparation,
                "current_contract_eligible": bool(objectives),
                "current_objectives": objectives,
                "current_one_step_pool": eligible,
                "before": {
                    "valid_grasp": before["valid_grasp_relation"],
                    "inside": before["object_inside_drawer"],
                    "placement_fit": before["placement_fit"],
                    "placement_violation_mm": before["placement_violation_mm"],
                    "goal_xy_error_mm": before["goal_xy_error_mm"],
                    "clearance_mm": before["clearance_mm"],
                },
            }
            replay.append(row)
            if not objectives:
                break
            execution = world.execute(archived["choice"], grip)
            grip = execution["grip"]
            actual = execution["features"]
            comparisons = {
                "opening_mm": abs(actual["remaining_open_mm"] - archived["opening_mm"]),
                "goal_xy_mm": abs(actual["goal_xy_error_mm"] - archived["goal_xy_mm"]),
                "clearance_mm": abs(actual["clearance_mm"] - archived["clearance_mm"]),
            }
            row["recorded_feature_errors"] = comparisons
            row["maximum_recorded_feature_error"] = max(comparisons.values())
        return {
            "steps": replay,
            "maximum_recorded_feature_error": max(
                (
                    row.get("maximum_recorded_feature_error", 0.0)
                    for row in replay
                ),
                default=0.0,
            ),
            "first_current_contract_incompatibility": next(
                (row for row in replay if not row["current_contract_eligible"]),
                None,
            ),
        }
    finally:
        backend.close()


def audit_task2(args):
    from jev_libero.actions import ACTIONS
    from jev_libero.world import Snapshot

    trace_path = Path(args.task2_trace)
    trace = [json.loads(line) for line in trace_path.read_text().splitlines()]
    steps = [row for row in trace if row.get("kind") == "step"]
    failure = next(row for row in trace if row.get("kind") == "failure")
    backend = WINE_BOTTLE_DRAWER_ADAPTER.make_backend(_arguments(args), render=False)
    world = backend.world
    grip = -1.0
    replay = []
    try:
        for expected in steps:
            preparation = WINE_BOTTLE_DRAWER_ADAPTER.prepare_world(world)
            result = world.execute(expected["choice"], grip=grip, record=False)
            grip = result["grip"]
            actual = result["features"]
            comparisons = {
                "opening_mm": abs(actual["remaining_open_mm"] - expected["opening_mm"]),
                "goal_xy_mm": abs(actual["goal_xy_error_mm"] - expected["goal_xy_mm"]),
                "clearance_mm": abs(actual["clearance_mm"] - expected["clearance_mm"]),
                "fit_violation_mm": abs(
                    actual["placement_violation_mm"] - expected["fit_violation_mm"]
                ),
            }
            replay.append(
                {
                    "step": expected["step"],
                    "action": expected["choice"],
                    "preparation": preparation,
                    "max_recorded_feature_error": max(comparisons.values()),
                    "comparisons": comparisons,
                }
            )
        preparation = WINE_BOTTLE_DRAWER_ADAPTER.prepare_world(world)
        before = world.features()
        if preparation != failure["preparation"]:
            raise ValueError("reconstructed Task-2 preparation differs from frozen failure")
        snapshot = _snapshot_hashes(world, args.snapshot_directory)
        geometry = _geometry_validation(world, before)
        predicted_before, predictions = world.predict_all(grip)
        if predicted_before != before:
            raise ValueError("preview before-state mismatch")
        one_step = _contract_audit(world, before, predictions)
        if any(value["eligible_contracts"] for value in one_step.values()):
            raise ValueError("frozen boundary unexpectedly has a one-step contract")

        root = Snapshot(world)
        pairs = []
        try:
            for first in ACTIONS:
                root.restore()
                first_result = world.execute(first, grip)
                _, seconds = world.predict_all(first_result["grip"])
                for second, prediction in seconds.items():
                    combined = _combine_two_step(world, before, first_result, prediction)
                    audited = _contract_audit(world, before, {first: combined})[first]
                    pairs.append(
                        {
                            "first": first,
                            "second": second,
                            "eligible_contracts": audited["eligible_contracts"],
                            "collision_gate": audited["collision_gate"],
                            "contract_failures": {
                                name: value["first_failure"]
                                for name, value in audited["contracts"].items()
                                if not value["passed"]
                            },
                            "terminal": {
                                "valid_grasp": combined["after"]["valid_grasp_relation"],
                                "inside": combined["after"]["object_inside_drawer"],
                                "placement_fit": combined["after"]["placement_fit"],
                                "placement_violation_mm": combined["after"][
                                    "placement_violation_mm"
                                ],
                                "goal_xy_error_mm": combined["after"]["goal_xy_error_mm"],
                                "clearance_mm": combined["after"]["clearance_mm"],
                                "fit_progress_mm": combined["placement_fit_progress_mm"],
                                "xy_gain_mm": combined["xy_gain_mm"],
                                "height_gain_mm": combined["height_gain_mm"],
                            },
                        }
                    )
        finally:
            root.restore()
        if len(pairs) != 729 or any(row["eligible_contracts"] for row in pairs):
            raise ValueError("Task-2 two-step evidence no longer matches the empty 729-pair boundary")

        old_path = Path(args.task2_comparison_trace)
        old_rows = [json.loads(line) for line in old_path.read_text().splitlines()]
        current_contract_replay = _replay_comparison_with_current_contracts(args, old_rows)
        strict_choices = [row["choice"] for row in steps]
        old_choices = [row["choice"] for row in old_rows]
        divergence = next(
            index
            for index, (strict, old) in enumerate(zip(strict_choices, old_choices))
            if strict != old
        )
        comparison = {
            "trace": str(old_path),
            "trace_sha256": _hash(old_path),
            "earliest_action_divergence": divergence,
            "strict_action": strict_choices[divergence],
            "older_diagnostic_action": old_choices[divergence],
            "shared_prefix_actions": strict_choices[:divergence],
            "strict_after_divergence": steps[divergence],
            "older_after_divergence": old_rows[divergence],
            "current_contract_replay": current_contract_replay,
        }
        output = {
            "schema_version": "task2-interaction-boundary-audit-v1",
            "purpose": "frozen mechanical reconstruction; no policy or model execution",
            "source_trace": str(trace_path),
            "source_trace_sha256": _hash(trace_path),
            "replay": {
                "steps": replay,
                "maximum_recorded_feature_error": max(
                    row["max_recorded_feature_error"] for row in replay
                ),
            },
            "boundary": {
                "preparation": preparation,
                "features": before,
                "grip": grip,
                "snapshot": snapshot,
                "geometry_validation": geometry,
            },
            "one_step": one_step,
            "two_step": {"evaluations": len(pairs), "pairs": pairs},
            "trajectory_comparison": comparison,
        }
        _write(args.task2_output, output)
        return output
    finally:
        backend.close()


def parser():
    root = Path("runs/privileged-reference")
    evidence = Path("docs/evidence/privileged_reference")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("task1", "task2", "all"), default="all")
    ap.add_argument("--libero-root", default="/home/junhongli/projects/LIBERO")
    ap.add_argument("--config-dir", default="/home/junhongli/runs/libero-config")
    ap.add_argument(
        "--task1-runs",
        nargs=3,
        default=[root / f"local-objective-task-adapter-episode-{index:02d}" for index in (1, 2, 3)],
    )
    ap.add_argument("--task1-output", default=evidence / "task1_interaction_classification.json")
    ap.add_argument(
        "--task2-trace", default=evidence / "task2_valid_interaction_gate_failure.jsonl"
    )
    ap.add_argument(
        "--task2-comparison-trace",
        default=root / "task2-oracle-feasibility-dev-03" / "trace.jsonl",
    )
    ap.add_argument("--task2-output", default=evidence / "task2_boundary_audit.json")
    ap.add_argument(
        "--snapshot-directory", default=root / "interaction-boundary-audit"
    )
    return ap


def main():
    args = parser().parse_args()
    if args.mode in ("task1", "all"):
        task1 = audit_task1(args)
        print(json.dumps({"task1": [run["totals"] for run in task1["runs"]]}, indent=2))
    if args.mode in ("task2", "all"):
        task2 = audit_task2(args)
        print(
            json.dumps(
                {
                    "task2_replay_max_error": task2["replay"]["maximum_recorded_feature_error"],
                    "one_step": len(task2["one_step"]),
                    "two_step": task2["two_step"]["evaluations"],
                    "divergence": task2["trajectory_comparison"]["earliest_action_divergence"],
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
