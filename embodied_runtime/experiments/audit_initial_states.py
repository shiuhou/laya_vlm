"""Small recorded-control transfer audit, independent of decision models.

Controls are replayed open-loop on explicitly identified benchmark initial states.
Only the source init/seed is expected to reproduce the archived trajectory. This
is a collection-coverage diagnostic, not autonomous-policy performance or E0.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from ..runtime_core import _sha256_json
from .collect_pairs import initial_state_inventory, physical_evidence
from .records import RunRecorder, code_identity, file_hash, load_records, versions

PHASE_RULES = {
    "far": "surface gap >= 20 mm",
    "approach": "5 mm <= surface gap < 20 mm",
    "near_contact": "surface gap < 5 mm and no instantaneous target contact",
    "contact": "instantaneous simulator target contact",
    "progressing": "remaining opening decreased > 0.1 mm since previous 50 ms boundary",
    "near_completion": "0 < remaining opening <= 10 mm",
    "success": "official LIBERO success predicate",
}


def phases(features, previous=None):
    """Overlapping evaluator strata, never inputs to compared decisions."""
    gap, remaining = features["distance_to_moving_geometry_mm"], features["remaining_open_mm"]
    labels = []
    if gap >= 20:
        labels.append("far")
    elif gap >= 5:
        labels.append("approach")
    elif not features["moving_contact"]:
        labels.append("near_contact")
    if features["moving_contact"]:
        labels.append("contact")
    if previous is not None and previous["remaining_open_mm"] - remaining > .1:
        labels.append("progressing")
    if 0 < remaining <= 10:
        labels.append("near_completion")
    if features["success"]:
        labels.append("success")
    return labels


def audit_unit(backend, recorder, unit, trajectory, *, check_archive):
    """Record intent before each control and complete physical state afterward."""
    previous, maximum_error = None, 0. if check_archive else None
    coverage = Counter()
    first_state = None
    for step in range(len(trajectory["actions"]) + 1):
        physical = physical_evidence(backend, unit, step)
        error = None
        if check_archive:
            expected = (trajectory["states_before"][step] if step < len(trajectory["actions"])
                        else trajectory["final_state"])
            error = float(np.max(np.abs(np.asarray(physical["sim_state"]) - expected)))
            maximum_error = max(maximum_error, error)
        labels = phases(physical["features"], previous)
        coverage.update(labels)
        recorder.record("collection_state", {**physical, "phases": labels,
                         "archive_comparison_applicable": check_archive,
                         "replay_state_max_error": error})
        first_state = first_state or physical["physical_state_id"]
        if error is not None and error > 1e-8:
            raise RuntimeError(f"source trajectory state mismatch at step {step}: {error}")
        previous = physical["features"]
        if step == len(trajectory["actions"]):
            break
        action = trajectory["actions"][step]
        recorder.record("collection_control_started", {**unit, "environment_step": step,
                         "physical_state_id": physical["physical_state_id"], "control": action,
                         "source": "fixed_recorded_controls_not_model_decision"})
        backend.world.obs, _, _, _ = backend.world.env.step(action)
        backend._grip_cmd = float(action[-1])
    result = {**unit, "reason": "all_recorded_controls_completed", "controls": len(trajectory["actions"]),
              "physical_states": len(trajectory["actions"]) + 1, "phase_coverage": dict(coverage),
              "initial_physical_state_id": first_state, "final_physical_state_id": physical["physical_state_id"],
              "max_archive_state_error": maximum_error,
              "final_remaining_open_mm": previous["remaining_open_mm"], "final_success": previous["success"],
              "model_decisions_executed": 0}
    recorder.record("initial_state_termination", result)
    return result


def summarize(path):
    """Recompute from ordered physical states; cached labels/totals are checks.

The JSONL hash chain protects serialization, while these checks also reject
internally inconsistent, correctly rehashed records. No terminal cache supplies
phase coverage, physical-state counts, motion outcomes, or control counts.
"""
    rows, diagnostics = load_records(Path(path) / "episodes.jsonl")
    units, previous, identities, terminated = {}, {}, {}, False
    config, benchmark_ids = {}, None
    identity_keys = ("task", "init_state_id", "seed", "benchmark_state_id", "trajectory_sha256")
    for row in rows:
        kind, data = row["kind"], row["data"]
        if kind == "run_start":
            config = data["resolved_config"]
            if "phase_rules" in config and config["phase_rules"] != PHASE_RULES:
                raise ValueError("unsupported phase rules for raw regeneration")
        if kind == "initial_state_inventory":
            benchmark_ids = data["state_ids"]
        if kind == "termination":
            terminated = True
        if "init_state_id" not in data:
            continue
        init = data["init_state_id"]
        identity = {key: data[key] for key in identity_keys if key in data}
        if identities.setdefault(init, identity) != identity:
            raise ValueError("initial-state source identity changed within audit")
        for key in ("task", "seed", "trajectory_sha256"):
            if key in config and identity.get(key) != config[key]:
                raise ValueError(f"initial-state {key} differs from run config")
        if benchmark_ids is not None and (not 0 <= init < len(benchmark_ids)
                                         or identity.get("benchmark_state_id") != benchmark_ids[init]):
            raise ValueError("benchmark initial-state hash mismatch")
        result = units.setdefault(init, {**identity, "physical_states": 0, "controls": 0,
                                         "phase_coverage": Counter(), "completed": False,
                                         "max_archive_state_error": None, "model_decisions_executed": 0})
        if kind == "collection_state":
            if result["completed"] or data["environment_step"] != result["physical_states"]:
                raise ValueError("collection state step is duplicate or out of order")
            if data["environment_step"] != result["controls"]:
                raise ValueError("collection state lacks preceding control intent")
            content = {k: v for k, v in data.items() if k not in {
                "physical_state_id", "phases", "archive_comparison_applicable", "replay_state_max_error"}}
            if _sha256_json(content) != data["physical_state_id"]:
                raise ValueError("physical state content hash mismatch")
            labels = phases(data["features"], previous.get(init))
            if "phases" in data and data["phases"] != labels:
                raise ValueError("cached phases differ from physical features")
            previous[init] = data["features"]
            result["physical_states"] += 1
            result["phase_coverage"].update(labels)
            result.setdefault("initial_physical_state_id", data["physical_state_id"])
            result["final_physical_state_id"] = data["physical_state_id"]
            result["final_remaining_open_mm"] = data["features"]["remaining_open_mm"]
            result["final_success"] = data["features"]["success"]
            error = data.get("replay_state_max_error")
            if error is not None:
                result["max_archive_state_error"] = max(result["max_archive_state_error"] or 0., error)
        elif kind == "collection_control_started":
            if (result["completed"] or data["environment_step"] != result["controls"]
                    or result["physical_states"] != result["controls"] + 1
                    or data["physical_state_id"] != result["final_physical_state_id"]):
                raise ValueError("control intent does not match preceding physical state")
            result["controls"] += 1
        elif kind == "initial_state_termination":
            if result["completed"] or result["physical_states"] != result["controls"] + 1:
                raise ValueError("termination without completed control outcomes")
            for key, measured in result.items():
                if key in data and key != "completed" and data[key] != measured:
                    raise ValueError(f"cached termination {key} differs from raw evidence")
            # The termination reason is a declared event, not a measured outcome.
            if "reason" in data:
                result["reason"] = data["reason"]
            result["completed"] = True
        elif kind == "failure":
            result["failure"] = data
    return {"initial_states": list(units.values()), "terminated": terminated, "recovery_diagnostics": diagnostics}


def audit(args):
    if len(set(args.init_state_ids)) != len(args.init_state_ids) or not 1 <= len(args.init_state_ids) <= 3:
        raise ValueError("pilot requires one to three distinct benchmark initial-state IDs")
    directory = Path(args.trajectory)
    source = json.loads((directory / "config.json").read_text())
    recorded_task = json.loads((directory / "task_config.json").read_text())
    from jev_libero.config import load_task
    installed_task = load_task(args.task)
    migrated = dict(recorded_task)
    if "measurements" not in migrated and args.task == "top_drawer":
        migrated["measurements"] = {"joint_position": {"kind": "joint_position"}}
    if migrated != installed_task:
        raise ValueError("recorded controls do not match requested task configuration")
    resolved = {**vars(args), "experiment_version": "initial-state-transfer-pilot-v0.1", "oracle": True,
                "trajectory_sha256": file_hash(directory / "sim_trajectory.npz"), "source_config": source,
                "recorded_task_config": recorded_task, "resolved_task_config": installed_task,
                "legacy_measurement_migration": migrated != recorded_task, "phase_rules": PHASE_RULES,
                "phase_rules_role": "overlapping descriptive evaluator strata, not safety or policy rules",
                "archive_state_error_tolerance": 1e-8, "render": False,
                "note": "fixed controls, not current atomic executor or decision provider; no statistical claim"}
    recorder = RunRecorder(args.output, resolved, {"run_id": Path(args.output).name, "code": code_identity(),
                                                 "versions": versions(), "oracle": True})
    failures = 0
    try:
        inventory = initial_state_inventory(args.task, args.libero_root, args.config_dir)
        recorder.record("initial_state_inventory", inventory)
        if any(index < 0 or index >= inventory["count"] for index in args.init_state_ids):
            raise ValueError("benchmark initial-state ID out of range")
        with np.load(directory / "sim_trajectory.npz") as trajectory:
            for init in args.init_state_ids:
                unit = {"task": args.task, "init_state_id": init, "seed": args.seed,
                        "benchmark_state_id": inventory["state_ids"][init],
                        "trajectory_sha256": resolved["trajectory_sha256"]}
                recorder.record("initial_state_started", unit)
                backend = None
                try:
                    backend = LiberoWorldBackend.from_task(args.task, seed=args.seed, init_state_id=init,
                              render=False, libero_root=args.libero_root, config_dir=args.config_dir)
                    audit_unit(backend, recorder, unit, trajectory,
                               check_archive=init == source["initial_state"] and args.seed == source["seed"])
                except Exception as exc:
                    failures += 1
                    recorder.record("failure", {**unit, "category": "initial_state_audit_error", "exception": repr(exc)})
                finally:
                    if backend is not None:
                        backend.close()
        recorder.record("termination", {"reason": "audit_complete", "failed_initial_states": failures,
                                         "initial_state_ids": args.init_state_ids, "model_decisions_executed": 0})
    except BaseException as exc:
        recorder.record("failure", {"category": "audit_error", "exception": repr(exc)})
        raise
    finally:
        recorder.close()
    print(json.dumps(summarize(args.output), sort_keys=True))
    if failures:
        raise RuntimeError(f"{failures} initial-state audit(s) failed; records preserved")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--task", default="top_drawer")
    parser.add_argument("--init-state-ids", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--libero-root")
    parser.add_argument("--config-dir")
    audit(parser.parse_args())


if __name__ == "__main__":
    main()
