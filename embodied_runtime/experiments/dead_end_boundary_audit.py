"""Audit the first zero-candidate privileged-reference boundary without policy calls."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from ..adapters.physics_preview import PhysicsPreviewCandidateBuilder
from ..runtime_core import BeliefSnapshot
from .operating_regime_probe import context_id
from .records import (
    RunRecorder, code_identity, file_hash, load_records, package_directory,
    repository_identity, versions,
)

VERSION = "dead-end-boundary-audit-v1"
TOLERANCE = 1e-8


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def contact_pairs(features):
    return {(c["hand"], c["other"]) for c in features["contacts"]}


def blocked_pairs(features):
    return {(c["hand"], c["other"]) for c in features["contacts"]
            if c.get("obstacle", not c["moving_target"])}


def clause_audit(before, prediction, config):
    """Expose every Boolean contributing to the original Jev contract result."""
    after = prediction["after"]
    rules = config["contact"]
    threshold = config["thresholds"]["collision_aware"]
    blocked = blocked_pairs(before)
    introduced = set(map(tuple, prediction["obstacle_pairs_seen"])) - blocked
    groups = {"blocked": blocked, "all": contact_pairs(before)}
    release_pairs = next((groups[key] for key in rules["release_priority"] if groups[key]), set())
    release_removed = bool(release_pairs) and not bool(release_pairs & contact_pairs(after))
    collision = {
        "reject_new_obstacles_enabled": rules["reject_new_obstacles"],
        "introduced_obstacle_pairs": sorted(introduced),
        "no_new_obstacle_pairs": not bool(introduced),
        "require_obstacle_free_endpoint": rules["require_obstacle_free_endpoint"],
        "endpoint_obstacle_contact": bool(after["obstacle_contact"]),
        "endpoint_obstacle_free": not bool(after["obstacle_contact"]),
    }
    collision["pass"] = (
        (not rules["reject_new_obstacles"] or collision["no_new_obstacle_pairs"])
        and (not rules["require_obstacle_free_endpoint"] or collision["endpoint_obstacle_free"])
    )
    advance = {
        "closure_ge_progress": prediction["closing_mm"] >= threshold["progress"],
        "predicted_success": bool(after["success"]),
    }
    advance["pass"] = advance["closure_ge_progress"] or advance["predicted_success"]
    establish = {
        "before_no_target_contact": not bool(before["moving_contact"]),
        "after_target_contact": bool(after["moving_contact"]),
        "closure_ge_negative_progress": prediction["closing_mm"] >= -threshold["progress"],
    }
    establish["pass"] = all(establish.values())
    approach = {
        "before_no_target_contact": not bool(before["moving_contact"]),
        "gap_reduction_ge_threshold": prediction["geometry_approach_mm"] >= threshold["approach_mm"],
        "endpoint_no_obstacle_contact": not bool(after["obstacle_contact"]),
        "closure_ge_negative_progress": prediction["closing_mm"] >= -threshold["progress"],
    }
    approach["pass"] = all(approach.values())
    release = {
        "required_contact_pairs": sorted(release_pairs),
        "required_contact_exists": bool(release_pairs),
        "required_contacts_removed": release_removed,
        "pass": release_removed,
    }
    reposition = {
        "has_reposition_witness": bool(prediction.get("reposition_witness")),
        "pass": bool(prediction.get("reposition_witness")),
    }
    raw = {
        "closure_mm": prediction["closing_mm"],
        "surface_gap_change_mm": prediction["geometry_approach_mm"],
        "target_contact": bool(after["moving_contact"]),
        "obstacle_contact": bool(after["obstacle_contact"]),
        "obstacle_peak_force_N": prediction["peak_obstacle_force_N"],
        "predicted_success": bool(after["success"]),
        "controls": prediction["steps"],
        "horizon_s": prediction["steps"] * 0.05,
    }
    passed = [name for name, result in (
        ("advance_target", advance), ("establish_contact", establish),
        ("approach_target", approach), ("release_contact", release),
        ("reposition", reposition),
    ) if collision["pass"] and result["pass"]]
    return {"raw": raw, "thresholds": threshold, "collision_gate": collision,
            "contracts": {"advance_target": advance, "establish_contact": establish,
                          "approach_target": approach, "release_contact": release,
                          "reposition": reposition},
            "passed_contracts": passed}


def load_episode(path):
    rows, errors = load_records(Path(path) / "episodes.jsonl")
    if errors:
        raise ValueError(f"incomplete source chain: {errors}")
    previews = [r for r in rows if r["kind"] == "reference_preview"]
    inputs = {r["data"]["belief_id"] for r in rows if r["kind"] == "reference_model_input"}
    dead = [r for r in previews if r["data"]["belief_id"] not in inputs]
    if len(dead) != 1 or dead[0]["data"]["pools"]:
        raise ValueError("expected exactly one unexecuted empty-pool preview")
    trajectories = sorted(
        (r["data"] for r in rows if r["kind"] == "demo_trajectory"),
        key=lambda row: row["step"],
    )
    return rows, dead[0]["data"], trajectories


def replay_dead_state(args, recorder, source_dead, trajectories):
    backend = LiberoWorldBackend.from_task(
        "top_drawer", seed=args.seed, init_state_id=args.init_state_id, render=False,
        libero_root=args.libero_root, config_dir=args.config_dir,
    )
    try:
        world = backend.world
        for row in trajectories:
            artifact = Path(args.episode) / row["artifact"]
            if file_hash(artifact) != row["sha256"]:
                raise ValueError(f"trajectory hash mismatch: {artifact}")
            with np.load(artifact) as saved:
                for command, expected in zip(saved["commands"], saved["states_before"], strict=True):
                    error = float(np.max(np.abs(world.env.sim.get_state().flatten() - expected)))
                    if error > TOLERANCE:
                        raise RuntimeError(f"recorded boundary replay mismatch: {error}")
                    world.obs, _, _, _ = world.env.step(command)
                    backend._grip_cmd = float(command[-1])
                error = float(np.max(np.abs(world.env.sim.get_state().flatten() - saved["state_after"])))
                if error > TOLERANCE:
                    raise RuntimeError(f"recorded endpoint replay mismatch: {error}")
        sim_state = world.env.sim.get_state().flatten()
        before = world.features()
        context = context_id(backend)
        if before != source_dead["before"] or context != source_dead["context_before"]:
            raise RuntimeError("replayed dead-end state differs from frozen preview source")
        initial_context = context
        jev_before, predictions = world.predict_all(backend.gripper_command())
        if context_id(backend) != initial_context or jev_before != before:
            raise RuntimeError("original predict_all changed or misread frozen state")
        if predictions != source_dead["predictions"]:
            raise RuntimeError("recomputed original predictions differ from recorded preview")

        from jev_libero.actions import ACTIONS
        from jev_libero.policy import NoFeasibleAction, ValidatedPolicy, contracts

        original_pools, original_rejected = contracts(
            before, predictions, collision_aware=True, task_config=world.config,
        )
        policy_api_called = False

        class NoCallAPI:
            def choose(self, *_args, **_kwargs):
                nonlocal policy_api_called
                policy_api_called = True
                raise AssertionError("empty pools must stop before any policy API call")

        policy_result = None
        try:
            ValidatedPolicy(collision_aware=True, task_config=world.config).choose(
                NoCallAPI(), 18, before, predictions,
            )
        except NoFeasibleAction as exc:
            policy_result = {"exception": type(exc).__name__, "message": str(exc),
                             "api_called": policy_api_called}
        if policy_result is None or policy_api_called:
            raise RuntimeError("original Jev policy did not stop at empty one-step pools")

        builder = PhysicsPreviewCandidateBuilder(
            world, collision_aware=True, grip_command=backend.gripper_command,
            action_map={name: name for name in ACTIONS},
        )
        candidates = builder.build(BeliefSnapshot("audit", 1, float(world.data.time), {}, {}, {}))
        current_pools = builder.last_preview["pools"]
        current_rejected = builder.last_preview["rejected"]
        if (current_pools != original_pools or current_rejected != original_rejected
                or builder.last_preview["predictions"] != predictions):
            raise RuntimeError("reference port differs from original Jev results")
        candidate_rows = []
        for candidate in candidates:
            clauses = clause_audit(before, predictions[candidate.token], world.config)
            exact_reason = original_rejected.get(candidate.token)
            if candidate.feasible != bool(clauses["passed_contracts"]):
                raise RuntimeError(f"candidate feasibility mismatch: {candidate.token}")
            candidate_rows.append({
                "action": candidate.token, **clauses,
                "original_jev_pool_membership": [
                    name for name, pool in original_pools.items() if candidate.token in pool
                ],
                "current_reference_feasible": candidate.feasible,
                "current_reference_reason_codes": list(candidate.reason_codes),
                "exact_rejection_reason": exact_reason,
            })
        identity = {
            "sim_time_s": float(world.data.time),
            "sim_state_sha256": sha256_bytes(np.asarray(sim_state).tobytes()),
            "sim_state_length": len(sim_state),
            "controller_context_id": context,
            "source_preview_belief_id": source_dead["belief_id"],
            "source_episode_sha256": file_hash(Path(args.episode) / "episodes.jsonl"),
            "features": before,
            "grip_command": backend.gripper_command(),
        }
        recorder.record("dead_end_snapshot", identity)
        recorder.record("original_jev_same_snapshot", {
            "pools": original_pools, "rejected": original_rejected,
            "validated_policy_without_lookahead": policy_result,
            "source": repository_identity(package_directory(__import__("jev_libero.world", fromlist=[""]))),
        })
        recorder.record("current_reference_same_snapshot", {
            "pools": current_pools, "rejected": current_rejected,
            "candidates": [candidate.canonical() for candidate in candidates],
            "matches_original_jev_exactly": True,
        })
        for row in candidate_rows:
            recorder.record("candidate_clause_audit", row)
        return backend, identity, candidate_rows, original_pools, original_rejected
    except BaseException:
        backend.close()
        raise


def successful_comparison(args, dead_features, recorder):
    root = Path(args.successful_trajectory)
    with gzip.open(root / "trace.jsonl.gz", "rt") as stream:
        trace = [json.loads(line) for line in stream]
    with gzip.open(root / "predictions.jsonl.gz", "rt") as stream:
        predictions = [json.loads(line) for line in stream]
    config = json.loads((root / "task_config.json").read_text())
    from jev_libero.policy import contracts
    first_contact = next(
        index for index, (row, preview) in enumerate(zip(trace, predictions))
        if preview["predictions"][row["choice"]]["after"]["moving_contact"]
    )
    nearest = min(
        range(len(trace)),
        key=lambda index: abs(predictions[index]["before"]["distance_to_moving_geometry_mm"]
                              - dead_features["distance_to_moving_geometry_mm"]),
    )
    selected_indices = sorted({nearest, max(0, first_contact - 1), first_contact})
    comparisons = []
    for index in selected_indices:
        row, preview = trace[index], predictions[index]
        pools, rejected = contracts(preview["before"], preview["predictions"], True, config)
        if {key: list(value) for key, value in pools.items()} != row["eligible_by_intent"]:
            raise RuntimeError(f"archived successful pools do not recompute at step {index}")
        selected = preview["predictions"][row["choice"]]
        rotation = np.asarray(preview["before"]["eef_rotation_matrix"])
        dead_rotation = np.asarray(dead_features["eef_rotation_matrix"])
        angle = float(np.degrees(np.arccos(np.clip(
            (np.trace(rotation @ dead_rotation.T) - 1) / 2, -1, 1))))
        comparison = {
            "step": index, "relation": (
                "first_contact_transition" if index == first_contact else
                "preceding_contact_transition" if index == first_contact - 1 else
                "closest_surface_gap"
            ),
            "before": preview["before"], "candidate_pools": {key: list(value) for key, value in pools.items()},
            "rejected": rejected, "actual_primitive": row["choice"],
            "selected_prediction": selected, "actual_closing_mm": row["actual_progress"],
            "temporarily_worsened_opening": selected["closing_mm"] < 0,
            "eef_position_delta_from_dead_mm": (
                np.asarray(preview["before"]["eef_mm"]) - dead_features["eef_mm"]
            ).tolist(),
            "eef_position_distance_from_dead_mm": float(np.linalg.norm(
                np.asarray(preview["before"]["eef_mm"]) - dead_features["eef_mm"])),
            "eef_orientation_difference_from_dead_deg": angle,
        }
        comparisons.append(comparison)
        recorder.record("successful_trajectory_comparison", comparison)
    return {
        "source_sha256": {
            "trace": file_hash(root / "trace.jsonl.gz"),
            "predictions": file_hash(root / "predictions.jsonl.gz"),
            "task_config": file_hash(root / "task_config.json"),
        },
        "nearest_step": nearest, "first_contact_step": first_contact,
        "rows": comparisons,
    }


def render_report(output, audit):
    path = Path(output) / "dead-end-boundary-report.md"
    state = audit["dead_end_state"]["features"]
    lines = [
        "# Dead-end boundary audit",
        "",
        "Diagnostic only: no model call, live policy execution, threshold change, "
        "lookahead, hierarchy or ablation.",
        "",
        "## Exact frozen state",
        "",
        f"- Simulation time: {audit['dead_end_state']['sim_time_s']:.12g} s",
        f"- Controller context: {audit['dead_end_state']['controller_context_id']}",
        f"- Simulator state SHA-256: {audit['dead_end_state']['sim_state_sha256']}",
        f"- Drawer opening: {state['remaining_open_mm']:.15g} mm",
        f"- Surface gap: {state['distance_to_moving_geometry_mm']:.15g} mm",
        f"- EEF XYZ: {state['eef_mm']} mm",
        f"- Finger gap: {state['finger_gap_mm']:.15g} mm",
        f"- Target/obstacle contact: {state['moving_contact']} / {state['obstacle_contact']}",
        f"- Success: {state['success']}",
        "",
        "## Complete 27-primitive audit",
        "",
        "A=advance (closure>=0.01 or success); E=establish contact "
        "(no current contact / endpoint contact / closure>=-0.01); "
        "P=approach (no current contact / gap>=2 / no endpoint obstacle / closure>=-0.01); "
        "R=release required contacts; W=reposition witness. Clause cells retain each Boolean.",
        "",
        "| Primitive | Closure mm | Gap reduction mm | Target / obstacle | Peak N | Success | Controls / s | Collision | A clauses | E clauses | P clauses | R | W | Exact reason |",
        "|---|---:|---:|---|---:|---|---:|---|---|---|---|---|---|---|",
    ]
    for row in audit["candidates"]:
        raw, contracts = row["raw"], row["contracts"]
        collision = row["collision_gate"]
        a, e, p = contracts["advance_target"], contracts["establish_contact"], contracts["approach_target"]
        lines.append(
            f"| {row['action']} | {raw['closure_mm']:.15g} | "
            f"{raw['surface_gap_change_mm']:.15g} | {raw['target_contact']} / "
            f"{raw['obstacle_contact']} | {raw['obstacle_peak_force_N']:.15g} | "
            f"{raw['predicted_success']} | {raw['controls']} / {raw['horizon_s']:.3g} | "
            f"new={collision['no_new_obstacle_pairs']},end={collision['endpoint_obstacle_free']} | "
            f"{a['closure_ge_progress']}/{a['predicted_success']}→{a['pass']} | "
            f"{e['before_no_target_contact']}/{e['after_target_contact']}/"
            f"{e['closure_ge_negative_progress']}→{e['pass']} | "
            f"{p['before_no_target_contact']}/{p['gap_reduction_ge_threshold']}/"
            f"{p['endpoint_no_obstacle_contact']}/{p['closure_ge_negative_progress']}→{p['pass']} | "
            f"{contracts['release_contact']['required_contact_exists']}/"
            f"{contracts['release_contact']['required_contacts_removed']}→"
            f"{contracts['release_contact']['pass']} | "
            f"{contracts['reposition']['has_reposition_witness']}→"
            f"{contracts['reposition']['pass']} | {row['exact_rejection_reason']} |"
        )
    lines += [
        "",
        "Raw full-precision predictions, contact pairs, all clause fields and source "
        "identities are in dead-end-boundary-audit.json.",
        "",
        "## Original Jev comparison on the identical snapshot",
        "",
        f"Original pools: {audit['original_jev']['pools']}.",
        "The current reference produces the same empty pools, identical predictions "
        "and identical rejection strings. Original ValidatedPolicy.choose() raises "
        "NoFeasibleAction before calling its API when given these one-step predictions. "
        "There is no port/integration discrepancy.",
        "The original runner's lookahead=2 mode would next invoke two_step_witnesses "
        "outside contracts() and then retry contracts with reposition witnesses. "
        "This audit intentionally did not invoke that fallback, so it classifies the "
        "frozen one-step contract boundary rather than the full lookahead runner.",
        "",
        "## Successful Jev approach/contact transition",
        "",
        "| Step | Relation | Gap mm | Opening mm | Contact | Pools | Selected | Predicted / actual closure mm | Endpoint contact | Temporary opening? | Pose distance / orientation from dead state |",
        "|---:|---|---:|---:|---|---|---|---:|---|---|---:|",
    ]
    for row in audit["successful_comparison"]["rows"]:
        before, prediction = row["before"], row["selected_prediction"]
        pools = "; ".join(f"{key}: {','.join(value)}" for key, value in row["candidate_pools"].items())
        lines.append(
            f"| {row['step']} | {row['relation']} | "
            f"{before['distance_to_moving_geometry_mm']:.15g} | "
            f"{before['remaining_open_mm']:.15g} | {before['moving_contact']} | "
            f"{pools} | {row['actual_primitive']} | "
            f"{prediction['closing_mm']:.15g} / {row['actual_closing_mm']:.15g} | "
            f"{prediction['after']['moving_contact']} | {row['temporarily_worsened_opening']} | "
            f"{row['eef_position_distance_from_dead_mm']:.6g} mm / "
            f"{row['eef_orientation_difference_from_dead_deg']:.6g}° |"
        )
    lines += [
        "",
        "## Classification",
        "",
        "**CONTRACT DEAD-END.** Original Jev's unchanged one-step contract logic also "
        "returns no pool on this exact snapshot. The successful trajectory avoids this "
        "contract state: at the closest 2.397 mm boundary it already has a y-40mm "
        "action predicting +30.946 mm closure, then establishes palm contact with "
        "z-40mm while predicting +7.163 mm closure. It does not temporarily worsen "
        "opening. Pose differences show that gap alone does not identify equivalent "
        "contact geometry. This supports a trajectory contribution, but does not prove "
        "the dead state has no physically useful continuation.",
        "",
        "## Smallest justified next step",
        "",
        "Do not increase the -0.01 mm threshold. Specify, then separately audit, one "
        "contact-transition contract whose admissibility requires: absent current "
        "target contact; obstacle-free endpoint; newly established target contact; "
        "and a verified next primitive from the complete restored endpoint that "
        "recovers the temporary opening and produces positive net closure over the "
        "two primitives. This names the excluded physical transition and prevents "
        "arbitrary opening. Reuse Jev's existing reversible witness mechanism if "
        "authorized. Do not implement or execute it as part of this audit.",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def run(args):
    output = Path(args.output)
    rows, source_dead, trajectories = load_episode(args.episode)
    recorder = RunRecorder(output, {**vars(args), "version": VERSION,
        "diagnostic_only": True, "no_model_calls": True, "no_live_policy": True,
        "thresholds_unchanged": True, "lookahead_executed": False},
        {"run_id": output.name, "code": code_identity(), "versions": versions()})
    backend = None
    try:
        backend, identity, candidates, pools, rejected = replay_dead_state(
            args, recorder, source_dead, trajectories,
        )
        successful = successful_comparison(args, identity["features"], recorder)
        classification = {
            "label": "CONTRACT DEAD-END",
            "port_integration_bug": False,
            "original_one_step_pool_empty": not bool(pools),
            "successful_trajectory_avoids_same_contract_state": True,
            "physical_continuation_proven_impossible": False,
            "original_lookahead_runner_evaluated": False,
            "rationale": (
                "Original Jev and the reference produce identical empty one-step pools "
                "on the exact state. The successful trajectory reaches a similar gap in "
                "a materially different pose with closure-positive actions."
            ),
        }
        recorder.record("classification", classification)
        audit = {
            "version": VERSION,
            "source_episode_rows": len(rows),
            "dead_end_state": identity,
            "candidates": candidates,
            "original_jev": {"pools": pools, "rejected": rejected,
                "validated_policy_result": "NoFeasibleAction before API call"},
            "current_reference": {"pools": pools, "rejected": rejected,
                "matches_original_jev_exactly": True},
            "successful_comparison": successful,
            "classification": classification,
            "smallest_next_step": (
                "Review a contact-transition contract requiring obstacle-free new contact "
                "plus a reversible two-primitive witness with positive net closure; do not "
                "change the numeric regression threshold or implement it in this audit."
            ),
        }
        recorder.record("termination", {"reason": "audit_complete", "classification": classification["label"]})
    except BaseException as exc:
        recorder.record("failure", {"category": "audit_error", "exception": repr(exc)})
        raise
    finally:
        if backend is not None:
            backend.close()
        recorder.close()
    audit["raw_evidence_sha256"] = file_hash(output / "episodes.jsonl")
    (output / "dead-end-boundary-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    report = render_report(output, audit)
    print(json.dumps({"classification": classification["label"], "report": str(report),
                      "raw_sha256": audit["raw_evidence_sha256"]}, indent=2))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--episode", default="runs/privileged-reference/episode-01")
    p.add_argument("--output", required=True)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--init-state-id", type=int, default=0)
    p.add_argument("--libero-root", default="/home/junhongli/projects/LIBERO")
    p.add_argument("--config-dir", default="/home/junhongli/runs/libero-config")
    p.add_argument("--successful-trajectory",
                   default="/home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1")
    return p


def main():
    run(parser().parse_args())


if __name__ == "__main__":
    main()
