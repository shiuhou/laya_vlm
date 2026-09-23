"""Evaluate original Jev two-step witnesses at the frozen reference dead end."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .dead_end_boundary_audit import load_episode, replay_dead_state
from .operating_regime_probe import context_id
from .records import RunRecorder, code_identity, file_hash, versions

VERSION = "two-step-lookahead-audit-v1"


def physical_first_actions(names, grip):
    """Collapse the native hold/open or hold/close command alias."""
    return {"hold" if name == ("open" if grip < 0 else "close") else name for name in names}


def classification(witnesses, grip):
    count = len(physical_first_actions(witnesses, grip))
    if count >= 2:
        return "MULTIPLE VALID FIRST-STEP WITNESSES"
    if count == 1:
        return "SINGLE VALID FIRST-STEP WITNESS"
    return "NO VALID WITNESS"


def enumerate_valid_pairs(world, grip, original_witnesses):
    """Mirror Jev's branch test while retaining every qualifying second action."""
    from jev_libero.actions import ACTIONS
    from jev_libero.config import expression, project
    from jev_libero.policy import blocked_pairs, contracts
    from jev_libero.world import Snapshot

    root = Snapshot(world)
    before = world.features()
    root_state = world.env.sim.get_state().flatten().copy()
    initial_obstacles = blocked_pairs(before)
    rules = world.config["contact"]
    pairs = []
    first_rows = []
    evaluations = 0
    try:
        for first in ACTIONS:
            root.restore()
            one = world.execute(first, grip)
            first_prediction = {
                "closure_mm": project(world.config["predictions"], {
                    "before": before, "after": one["features"],
                })[world.config["search"]["progress_field"]],
                "surface_gap_change_mm": (
                    before["distance_to_moving_geometry_mm"]
                    - one["features"]["distance_to_moving_geometry_mm"]
                ),
                "target_contact": bool(one["features"]["moving_contact"]),
                "obstacle_contact": bool(one["features"]["obstacle_contact"]),
                "obstacle_peak_force_N": one["peak_obstacle_force_N"],
                "success": bool(one["features"]["success"]),
                "controls": one["steps"],
            }
            introduced = set(one["obstacle_pairs_seen"]) - initial_obstacles
            safe = not (
                (rules["reject_new_obstacles"] and introduced)
                or (rules["require_obstacle_free_endpoint"]
                    and one["features"]["obstacle_contact"])
            )
            valid_seconds = []
            if safe:
                second_before, seconds = world.predict_all(one["grip"])
                if second_before != one["features"]:
                    raise RuntimeError(f"second-step source mismatch after {first}")
                for second, prediction in seconds.items():
                    evaluations += 1
                    end = prediction["after"]
                    combined = {
                        **prediction,
                        **project(world.config["predictions"], {
                            "before": before, "after": end,
                        }),
                        "geometry_approach_mm": (
                            before["distance_to_moving_geometry_mm"]
                            - end["distance_to_moving_geometry_mm"]
                        ),
                        "obstacle_pairs_seen": sorted(
                            set(one["obstacle_pairs_seen"])
                            | set(map(tuple, prediction["obstacle_pairs_seen"]))
                        ),
                        "peak_obstacle_force_N": max(
                            one["peak_obstacle_force_N"],
                            prediction["peak_obstacle_force_N"],
                        ),
                    }
                    goals, rejection = contracts(
                        before, {first: combined}, collision_aware=True,
                        task_config=world.config,
                    )
                    if not goals:
                        continue
                    effects = list(goals)
                    context = {
                        "after": end,
                        "before": before,
                        "p": combined,
                        "effects": {key: key in goals for key in world.config["contracts"]},
                    }
                    score = tuple(
                        expression(rule, context) for rule in world.config["search"]["score"]
                    )
                    row = {
                        "first_action": first,
                        "second_action": second,
                        "selected_by_original": False,
                        "first": first_prediction,
                        "second": {
                            "closure_mm": prediction["closing_mm"],
                            "surface_gap_change_mm": prediction["geometry_approach_mm"],
                            "target_contact": bool(end["moving_contact"]),
                            "obstacle_contact": bool(end["obstacle_contact"]),
                            "obstacle_peak_force_N": prediction["peak_obstacle_force_N"],
                            "success": bool(end["success"]),
                            "controls": prediction["steps"],
                        },
                        "combined": {
                            "net_closure_mm": combined[world.config["search"]["progress_field"]],
                            "net_surface_gap_change_mm": combined["geometry_approach_mm"],
                            "final_surface_gap_mm": end["distance_to_moving_geometry_mm"],
                            "final_target_contact": bool(end["moving_contact"]),
                            "final_obstacle_contact": bool(end["obstacle_contact"]),
                            "peak_obstacle_force_N": combined["peak_obstacle_force_N"],
                            "predicted_success": bool(end["success"]),
                            "passed_contracts": effects,
                            "rejection": rejection,
                        },
                        "search_score": list(score),
                    }
                    pairs.append(row)
                    valid_seconds.append(second)
            witness = original_witnesses.get(first)
            selected = None if witness is None else witness["second_input"]
            if bool(valid_seconds) != bool(witness):
                raise RuntimeError(f"enumeration/original witness disagreement: {first}")
            if selected is not None:
                match = next((row for row in pairs
                              if row["first_action"] == first
                              and row["second_action"] == selected), None)
                if match is None:
                    raise RuntimeError(f"original selected invalid pair: {first}/{selected}")
                match["selected_by_original"] = True
                expected = {
                    "second_input": selected,
                    "net_progress": match["combined"]["net_closure_mm"],
                    "net_gap_reduction_mm": match["combined"]["net_surface_gap_change_mm"],
                    "terminal_contact": match["combined"]["final_target_contact"],
                    "terminal_success": match["combined"]["predicted_success"],
                    "peak_obstacle_force_N": match["combined"]["peak_obstacle_force_N"],
                    "witnessed_effects": match["combined"]["passed_contracts"],
                }
                if expected != witness:
                    raise RuntimeError(f"original witness payload disagreement: {first}")
            first_rows.append({
                "first_action": first,
                "first": first_prediction,
                "first_step_safe": safe,
                "valid_second_actions": valid_seconds,
                "original_selected_witness": witness,
                "no_witness_reason": None if witness else (
                    "first_step_collision_gate" if not safe
                    else "no_second_branch_passed_combined_contracts"
                ),
            })
    finally:
        root.restore()
    if not np.array_equal(world.env.sim.get_state().flatten(), root_state):
        raise RuntimeError("pair enumeration did not restore the root simulator state")
    return first_rows, pairs, evaluations


def render_report(output, result):
    path = Path(output) / "two-step-lookahead-report.md"
    lines = [
        "# Original Jev two-step lookahead audit",
        "",
        "Offline frozen-snapshot diagnostic. No model call or live policy episode.",
        "",
        f"Classification: **{result['classification']}**.",
        f"Original branch evaluations: {result['original_two_step_evaluations']}.",
        f"Witnessed first actions: {result['witnessed_first_action_count']} "
        f"({result['physically_distinct_first_action_count']} physically distinct).",
        f"All qualifying first/second pairs: {len(result['all_valid_pairs'])}.",
        "",
        "## Original selected witness for each first action",
        "",
        "| First | First closure | First gap change | First contact | Best second | Second closure | Second contact | Net closure | Final gap | Final contact | Peak N | Success | Passed combined contracts |",
        "|---|---:|---:|---|---|---:|---|---:|---:|---|---:|---|---|",
    ]
    selected = {(row["first_action"], row["second_action"]): row
                for row in result["all_valid_pairs"] if row["selected_by_original"]}
    for first in result["first_actions"]:
        witness = first["original_selected_witness"]
        if witness is None:
            continue
        row = selected[(first["first_action"], witness["second_input"])]
        one, two, combined = row["first"], row["second"], row["combined"]
        lines.append(
            f"| {row['first_action']} | {one['closure_mm']:.15g} | "
            f"{one['surface_gap_change_mm']:.15g} | {one['target_contact']} | "
            f"{row['second_action']} | {two['closure_mm']:.15g} | "
            f"{two['target_contact']} | {combined['net_closure_mm']:.15g} | "
            f"{combined['final_surface_gap_mm']:.15g} | "
            f"{combined['final_target_contact']} | {combined['peak_obstacle_force_N']:.15g} | "
            f"{combined['predicted_success']} | {','.join(combined['passed_contracts'])} |"
        )
    lines += [
        "",
        "## First actions without a witness",
        "",
        "| First | Closure | Gap change | Contact | Safe | Reason |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in result["first_actions"]:
        if row["original_selected_witness"] is not None:
            continue
        one = row["first"]
        lines.append(
            f"| {row['first_action']} | {one['closure_mm']:.15g} | "
            f"{one['surface_gap_change_mm']:.15g} | {one['target_contact']} | "
            f"{row['first_step_safe']} | {row['no_witness_reason']} |"
        )
    lines += [
        "",
        "## Every qualifying pair",
        "",
        "The full pair list, including non-selected valid second actions, immediate "
        "and net effects, contract membership and search scores, is retained in "
        "two-step-lookahead-audit.json.",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def run(args):
    output = Path(args.output)
    rows, source_dead, trajectories = load_episode(args.episode)
    recorder = RunRecorder(output, {**vars(args), "version": VERSION,
        "diagnostic_only": True, "no_model_calls": True, "no_live_policy": True,
        "original_jev_implementation_unmodified": True},
        {"run_id": output.name, "code": code_identity(), "versions": versions()})
    backend = None
    try:
        backend, identity, _, one_step_pools, _ = replay_dead_state(
            args, recorder, source_dead, trajectories,
        )
        world = backend.world
        root_context = context_id(backend)
        root_state = world.env.sim.get_state().flatten().copy()
        witnesses, original_evaluations = world.two_step_witnesses(
            backend.gripper_command()
        )
        if context_id(backend) != root_context or not np.array_equal(
                world.env.sim.get_state().flatten(), root_state):
            raise RuntimeError("original two_step_witnesses did not restore root context")
        first_rows, pairs, audit_evaluations = enumerate_valid_pairs(
            world, backend.gripper_command(), witnesses,
        )
        if original_evaluations != audit_evaluations:
            raise RuntimeError("branch enumeration count differs from original")
        from jev_libero.policy import contracts
        _, predictions = world.predict_all(backend.gripper_command())
        for name, witness in witnesses.items():
            predictions[name]["reposition_witness"] = witness
        witness_pools, witness_rejected = contracts(
            identity["features"], predictions, collision_aware=True,
            task_config=world.config,
        )
        from ..runtime_core import BeliefSnapshot
        from .privileged_reference import ReferenceBuilder, presentation
        reference_events = []
        reference_builder = ReferenceBuilder(
            backend, lambda kind, data: reference_events.append((kind, data)),
        )
        reference_candidates = reference_builder.build(BeliefSnapshot(
            "lookahead-audit", 1, float(world.data.time), {}, {}, {},
        ))
        reference_names = [candidate.token for candidate in reference_candidates
                           if candidate.feasible]
        if (reference_builder.last_preview["reposition_witnesses"] != witnesses
                or reference_builder.last_preview["pools"] != witness_pools
                or reference_names != list(witnesses)
                or context_id(backend) != root_context):
            raise RuntimeError("reference integration differs from original lookahead")
        model_state, model_questions = presentation(
            reference_builder.last_preview["before"],
            reference_builder.last_preview["predictions"], reference_names,
            backend.gripper_command(), None,
        )
        complete_witness_rows = all(
            f"\n{name} " in model_state
            and f" > {witnesses[name]['second_input']} " in model_state
            for name in reference_names
        )
        if (set(model_questions["action"]["criteria"]) != set(reference_names)
                or not complete_witness_rows):
            raise RuntimeError("reference presentation omits witness-backed candidates")
        physical = physical_first_actions(witnesses, backend.gripper_command())
        label = classification(witnesses, backend.gripper_command())
        result = {
            "version": VERSION,
            "dead_end_state": identity,
            "source_episode_rows": len(rows),
            "one_step_pools": one_step_pools,
            "original_two_step_evaluations": original_evaluations,
            "root_context_restored": True,
            "witnessed_first_action_count": len(witnesses),
            "physically_distinct_first_action_count": len(physical),
            "first_actions": first_rows,
            "all_valid_pairs": pairs,
            "witness_pools": {key: list(pool) for key, pool in witness_pools.items()},
            "witness_rejected": witness_rejected,
            "reference_integration": {
                "matches_original_witnesses": True,
                "offered_first_actions": reference_names,
                "physically_distinct_first_actions": len(physical),
                "context_restored": True,
                "model_state": model_state,
                "questions": model_questions,
            },
            "classification": label,
        }
        recorder.record("original_two_step_result", {
            "evaluations": original_evaluations,
            "witnesses": witnesses,
            "root_context_restored": True,
        })
        for row in first_rows:
            recorder.record("two_step_first_action", row)
        for row in pairs:
            recorder.record("two_step_valid_pair", row)
        recorder.record("reference_integration_same_snapshot", {
            "matches_original_witnesses": True,
            "offered_first_actions": reference_names,
            "physically_distinct_first_actions": len(physical),
            "context_restored": True,
            "reference_preview_recorded": len(reference_events) == 1,
            "model_state": model_state,
            "questions": model_questions,
        })
        recorder.record("classification", {"label": label,
            "witnessed_first_actions": len(witnesses),
            "physically_distinct_first_actions": len(physical)})
        recorder.record("termination", {"reason": "audit_complete", "classification": label})
    except BaseException as exc:
        recorder.record("failure", {"category": "lookahead_audit_error", "exception": repr(exc)})
        raise
    finally:
        if backend is not None:
            backend.close()
        recorder.close()
    result["raw_evidence_sha256"] = file_hash(output / "episodes.jsonl")
    audit_path = output / "two-step-lookahead-audit.json"
    audit_path.write_text(json.dumps(result, indent=2) + "\n")
    report = render_report(output, result)
    print(json.dumps({"classification": label,
        "witnessed_first_actions": len(witnesses),
        "physically_distinct_first_actions": len(physical),
        "valid_pairs": len(pairs), "report": str(report),
        "raw_sha256": result["raw_evidence_sha256"]}, indent=2))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--episode", default="runs/privileged-reference/episode-01")
    value.add_argument("--output", required=True)
    value.add_argument("--seed", type=int, default=1)
    value.add_argument("--init-state-id", type=int, default=0)
    value.add_argument("--libero-root", default="/home/junhongli/projects/LIBERO")
    value.add_argument("--config-dir", default="/home/junhongli/runs/libero-config")
    return value


def main():
    run(parser().parse_args())


if __name__ == "__main__":
    main()
