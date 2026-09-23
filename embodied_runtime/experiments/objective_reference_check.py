"""Bounded checks for the local-objective reference; no live policy or warm start."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random

import numpy as np

from . import privileged_reference as ref
from .engineering_demo import RecordingAgent
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from ..runtime_core import BeliefSnapshot


def run(args):
    baseline = Path(args.baseline)
    config = json.loads((baseline / "resolved_config.yaml").read_text())
    manifest = json.loads((baseline / "manifest.json").read_text())
    rows, errors = load_records(baseline / "episodes.jsonl")
    if errors:
        raise ValueError(errors)
    evidence = json.loads((baseline / "reference-evidence.json").read_text())
    if evidence["raw_sha256"] != file_hash(baseline / "episodes.jsonl"):
        raise ValueError("stale baseline evidence")
    identity = {"baseline_commit": "cae7437fd5564fa9cc7a292aab397fe66cb3d4e7",
        "baseline_run_commit": manifest["code"]["commit"],
        "baseline_path": str(baseline.resolve()),
        "baseline_artifacts": {name: file_hash(baseline / name) for name in
            ("episodes.jsonl", "reference-evidence.json", "manifest.json", "resolved_config.yaml")},
        "model": manifest["models"]["decision"], "model_execution": manifest["model_execution"]}
    rec = RunRecorder(args.output, {"mode": args.mode, **ref.PRIVILEGE,
        "routing_version": ref.ROUTING_VERSION, "no_live_policy": True},
        {"run_id": Path(args.output).name, "code": code_identity(), "versions": versions(), "baseline": identity})
    backend = None
    try:
        if args.mode == "mechanical":
            backend = ref.make_backend(argparse.Namespace(**config), render=False)
            world = backend.world
            environment = next(r["data"] for r in rows if r["kind"] == "environment")
            if world.features() != environment["features"] or world.config != environment["task_config"]:
                raise RuntimeError("fresh baseline state/config mismatch")
            from jev_libero.world import Snapshot
            snap = Snapshot(world)
            context = ref.context_id(backend)
            builder = ref.ReferenceBuilder(backend, rec.record, "local_objective")
            candidates = builder.build(BeliefSnapshot("mechanical", 0, float(world.data.time), {}, {}, {}, ()))
            routing = builder.last_preview["objective_routing"]
            if routing["objective"] != "approach_target" or len(routing["motor_pool"]) != 7:
                raise RuntimeError("unexpected initial objective pool")
            if [c.token for c in candidates if c.feasible] != routing["motor_pool"]:
                raise RuntimeError("builder/routing mismatch")
            executor = ref.JevAtomicExecutor(backend)
            # Independent branches from reset, never a policy trajectory.
            for token in ref.actions():
                snap.restore()
                backend._grip_cmd, backend.last_execution = -1., None
                execution = executor.execute(token)
                outcome = ref.measured_outcome(world, builder.last_preview["before"], token, execution)
                comparison = ref.compare_prediction(world, builder.last_preview["predictions"][token], outcome, execution)
                rec.record("mechanical_branch", {"token": token, "comparison": comparison})
                if not comparison["passed"]:
                    raise RuntimeError(f"preview/execution mismatch: {token}")
            snap.restore()
            backend._grip_cmd, backend.last_execution = -1., None
            if ref.context_id(backend) != context:
                raise RuntimeError("source snapshot not restored")
            rec.record("mechanical_passed", {"actions": 27, "restored": True, "routing": routing})
        else:
            import torch
            if model_identity(config["laya_path"]) != manifest["models"]["decision"]:
                raise RuntimeError("model bytes changed")
            random.seed(config["seed"])
            np.random.seed(config["seed"])
            torch.manual_seed(config["seed"])
            agent = ref.load_laya_provider(config["laya_path"], subfolder=None, device=config["device"]).agent
            expected_model = manifest["model_execution"]
            if (agent.cfg != expected_model["config"] or str(agent.dtype) != expected_model["dtype"]
                    or str(agent.device) != expected_model["device"]):
                raise RuntimeError("model execution configuration changed")
            wrapped = RecordingAgent(agent, rec.record)
            results = []
            for step in (0, 1):
                saved = evidence["trace"][step]
                before, predictions = saved["outcome"]["before"], saved["all_predictions"]
                last = None if step == 0 else evidence["trace"][step-1]["outcome"]
                routing = ref.objective_routing(saved["effect_contract_pools"], config["primitive_order"])
                rec.record("frozen_fixture", {"step": step, "before": before,
                    "predictions": predictions, "last_actual": last, "routing": routing,
                    "source_snapshot_id": saved["selection"]["snapshot_id"]})
                for condition in ("flat", "local_objective"):
                    objective = routing["objective"] if condition == "local_objective" else None
                    names = routing["motor_pool"] if objective else saved["candidates"]
                    state, questions = ref.presentation(before, predictions, names, -1., last, objective)
                    if not objective and (state != saved["selection"]["state"]
                                          or questions != saved["selection"]["questions"]):
                        raise RuntimeError("flat baseline presentation changed")
                    audit = ref.encoding_audit(wrapped, state, questions)
                    wrapped.snapshot_id = f"frozen-flat-boundary-{step}:{condition}"
                    rec.record("paired_input", {"step": step, "condition": condition,
                        "snapshot_id": wrapped.snapshot_id, "objective": objective,
                        "option_order": names, "state": state, "questions": questions, "audit": audit})
                    response = wrapped.system_one(state, questions)
                    choice = response["answers"]["action"]["choice"]
                    if choice not in names:
                        raise RuntimeError("invalid model choice")
                    result = {"step": step, "condition": condition, "objective": objective,
                        "candidates": names, "choice": choice,
                        "archived_flat_choice": saved["outcome"]["action"],
                        "answer": response["answers"]["action"]}
                    rec.record("paired_result", result)
                    results.append(result)
                    print(json.dumps(result), flush=True)
            (Path(args.output) / "paired-results.json").write_text(json.dumps(results, indent=2)+"\n")
        rec.record("termination", {"reason": "checks_passed"})
    except BaseException as exc:
        rec.record("failure", {"exception": repr(exc)})
        raise
    finally:
        if backend is not None:
            backend.close()
        rec.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("mechanical", "paired"), required=True)
    parser.add_argument("--baseline", default="runs/privileged-reference/forced-singleton-episode-01")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
