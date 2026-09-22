"""Independent, short-horizon evaluator; NEVER part of a provider input.

This is a set-valued local utility diagnostic, not an expert policy or a safety
certificate. In particular an unhelpful one-step result does not disprove a
multi-step preparatory action. All offered probes, including STOP, are simulated
from the same complete controller snapshot before any model outputs are read.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from ..runtime_core import AtomicExecutor
from .equivalence import distribution, paired_inputs
from .records import file_hash, load_records

RUBRIC = {
    "version": "reference-local-utility-v0.1",
    "progress_tolerance_mm": .25,
    "approach_threshold_mm": 2.,
    "threshold_source": "existing top_drawer ordinary task thresholds, not calibrated safety limits",
    "scope": "one actual atomic primitive, up to 8 control steps; STOP-adjusted dynamics",
    "obstacle_rule": "no new sampled obstacle pairs and no endpoint obstacle contact; NOT a safety certificate",
    "unresolved": "no local utility demonstrated is not proof of long-horizon incorrectness",
}

# Selected from existing collector evidence, before new reference choices.
PILOT_STEPS = (0, 20, 24, 29, 33, 48, 80, 120, 140, 144, 152, 155)


def local_reference(before, previews):
    """Compute observable utility and a set-valued near-best local reference."""
    stop = previews["STOP"]["after"]
    eps = RUBRIC["progress_tolerance_mm"]
    approach = RUBRIC["approach_threshold_mm"]
    existing = {(c["hand"], c["other"]) for c in before["contacts"] if c["obstacle"]}
    values = {}
    for token, p in previews.items():
        after = p["after"]
        new_obstacles = set(map(tuple, p["obstacle_pairs_seen"])) - existing
        admitted = not new_obstacles and not after["obstacle_contact"]
        closure = before["remaining_open_mm"] - after["remaining_open_mm"]
        incremental = stop["remaining_open_mm"] - after["remaining_open_mm"]
        gap = stop["distance_to_moving_geometry_mm"] - after["distance_to_moving_geometry_mm"]
        nonregressing = closure >= -eps and incremental >= -eps
        support = []
        if admitted:
            if after["success"]:
                support.append("terminal_preservation" if before["success"] else "task_completion")
            if not before["success"] and incremental >= eps and closure >= eps:
                support.append("incremental_closure")
            if not before["moving_contact"] and not stop["moving_contact"] and after["moving_contact"] and nonregressing:
                support.append("incremental_contact")
            if not before["moving_contact"] and gap >= approach and nonregressing:
                support.append("incremental_approach")
        values[token] = {
            "sampled_obstacle_admissible": admitted,
            "new_obstacle_pairs": [list(pair) for pair in sorted(new_obstacles)],
            "closing_mm": closure, "closing_vs_stop_mm": incremental,
            "surface_approach_vs_stop_mm": gap,
            "local_support": support,
            "useful_local_reference": bool(support),
            "interpretation": "local_support" if support else "no_local_utility_demonstrated",
            "equal_horizon_to_stop": None if any(x.get("execution", {}).get("environment_step_count") is None
                                                  for x in (p, previews["STOP"])) else (
                p["execution"]["environment_step_count"] == previews["STOP"]["execution"]["environment_step_count"]),
        }
    terminal = [t for t, v in values.items() if any(s in v["local_support"] for s in ("task_completion", "terminal_preservation"))]
    closing = [t for t, v in values.items() if "incremental_closure" in v["local_support"]]
    contact = [t for t, v in values.items() if "incremental_contact" in v["local_support"]]
    approaching = [t for t, v in values.items() if "incremental_approach" in v["local_support"]]
    if terminal:
        reference, tier = terminal, "terminal"
    elif closing:
        best = max(values[t]["closing_vs_stop_mm"] for t in closing)
        reference = [t for t in closing if values[t]["closing_vs_stop_mm"] >= best - eps]
        tier = "incremental_closure"
    elif contact:
        reference, tier = contact, "incremental_contact"
    elif approaching:
        best = max(values[t]["surface_approach_vs_stop_mm"] for t in approaching)
        reference = [t for t in approaching if values[t]["surface_approach_vs_stop_mm"] >= best - approach]
        tier = "incremental_approach"
    else:
        reference, tier = [], "no_resolved_one_step_reference"
    return {"rubric": RUBRIC, "tier": tier, "reference_tokens": reference, "candidates": values}


def preview_probes(backend, candidates, recorder, physical_id):
    """Branch through the real atomic executor, then restore all mutable state."""
    from jev_libero.world import Snapshot

    world = backend.world
    snapshot = Snapshot(world)
    grip, last = backend._grip_cmd, deepcopy(backend.last_execution)
    before = world.features()
    physical_before = world.env.sim.get_state().flatten().copy()
    predictions = {}

    def restore():
        snapshot.restore()
        backend._grip_cmd, backend.last_execution = grip, deepcopy(last)

    def execute(token):
        restore()
        result = AtomicExecutor(backend).execute(token)
        return {"execution": result, "after": world.features(),
                "sim_state_after": world.env.sim.get_state().flatten().tolist(),
                "peak_obstacle_force_N": backend.last_execution["peak_obstacle_force_N"],
                "obstacle_pairs_seen": backend.last_execution["obstacle_pairs_seen"]}

    try:
        for candidate in candidates:
            recorder.record("evaluator_probe_started", {"physical_state_id": physical_id, "token": candidate.token,
                                                        "not_supplied_to_model": True})
            prediction = execute(candidate.token)
            predictions[candidate.token] = prediction
            recorder.record("evaluator_probe", {"physical_state_id": physical_id, "token": candidate.token,
                                                "not_supplied_to_model": True, **prediction})
        # A repeated STOP checks controller restoration, not only qpos/qvel.
        repeated_stop = execute("STOP")
        error = float(np.max(np.abs(np.asarray(repeated_stop["sim_state_after"]) - predictions["STOP"]["sim_state_after"])))
        if error > 1e-8:
            raise RuntimeError(f"evaluator controller replay mismatch: {error}")
    finally:
        restore()
    restore_error = float(np.max(np.abs(world.env.sim.get_state().flatten() - physical_before)))
    if restore_error != 0.:
        raise RuntimeError(f"evaluator changed source physical state: {restore_error}")
    diagnostic = {"physical_state_id": physical_id, "not_supplied_to_model": True, "before": before,
                  "stop_replay_max_error": error, "source_restore_max_error": restore_error,
                  **local_reference(before, predictions)}
    recorder.record("reference_evaluator", diagnostic)
    return diagnostic


def summarize(collection, replay):
    """Recompute evaluator labels and join raw, identity-checked model outputs."""
    from .summarize_equivalence import _effective_input_id, _truncation_status, _validate_decision

    raw, incomplete = load_records(collection)
    decisions, partial = load_records(replay)
    if incomplete or partial:
        raise ValueError("incomplete evidence; retain failure and inspect before analysis")
    def unique(rows, kind, key):
        out = {}
        for row in rows:
            if row["kind"] == kind:
                data = row["data"]
                if data[key] in out:
                    raise ValueError(f"duplicate {kind}")
                out[data[key]] = data
        return out
    pairs = unique(raw, "paired_state", "pair_id")
    evaluators = unique(raw, "reference_evaluator", "physical_state_id")
    probes = {}
    for row in raw:
        if row["kind"] == "evaluator_probe":
            d = row["data"]
            local = probes.setdefault(d["physical_state_id"], {})
            if d["token"] in local:
                raise ValueError("duplicate evaluator probe")
            local[d["token"]] = d
    result = []
    seen = set()
    for row in decisions:
        if row["kind"] != "equivalence_decision" or row["data"]["branch"] != "oracle":
            continue
        d = row["data"]
        key = (d["pair_id"], d["provider"], d["repeat"])
        if key in seen:
            raise ValueError("duplicate reference decision")
        seen.add(key)
        pair = pairs[d["pair_id"]]
        inputs = paired_inputs(pair)
        oracle = inputs[0]
        decision = _validate_decision(d, inputs)
        if d["provider"] == "LayaProvider" and (_truncation_status(d) != "not_truncated" or _effective_input_id(d) is None):
            raise ValueError("reference decision lacks complete token audit")
        pid = pair["physical"]["physical_state_id"]
        evaluator = evaluators[pid]
        if set(probes[pid]) != oracle.allowed():
            raise ValueError("incomplete or mismatched evaluator probes")
        recomputed = local_reference(evaluator["before"], probes[pid])
        if recomputed != {k: evaluator[k] for k in recomputed}:
            raise ValueError("cached evaluator result disagrees with raw preview")
        tokens = sorted(oracle.allowed())
        p = distribution(decision, tokens)
        ordered = sorted(zip(tokens, p), key=lambda item: -item[1]) if p is not None else []
        result.append({"pair_id": pair["pair_id"], "init_state_id": pair["physical"]["init_state_id"],
                       "step": pair["physical"]["environment_step"], "provider": d["provider"], "repeat": d["repeat"],
                       "oracle_position": oracle.state.fields["target.position_m"].value,
                       "before": evaluator["before"], "choice": decision.token,
                       "raw_probabilities": decision.probabilities,
                       "top2": ordered[:2], "margin": float(ordered[0][1] - ordered[1][1]) if len(ordered) > 1 else None,
                       "chosen_evidence": {**recomputed["candidates"][decision.token], **probes[pid][decision.token]},
                       "reference_tier": recomputed["tier"], "reference_tokens": recomputed["reference_tokens"],
                       "stop_evidence": probes[pid]["STOP"],
                       "all_local_utilities": recomputed["candidates"]})
    return {"collection_sha256": file_hash(collection), "replay_sha256": file_hash(replay), "rubric": RUBRIC,
            "scope": "reference-quality pilot, not policy accuracy or formal E0", "rows": result}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("collection")
    ap.add_argument("replay")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    data = summarize(args.collection, args.replay)
    with Path(args.output).open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"oracle_decisions": len(data["rows"]), "output": args.output}))


if __name__ == "__main__":
    main()
