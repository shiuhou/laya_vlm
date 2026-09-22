"""Compare provider interfaces on one recorded snapshot, with no environment."""
import argparse
import time
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from ..runtime_core import RuleProvider, load_laya_provider
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, restore_snapshot, summarize, versions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_jsonl")
    ap.add_argument("--step", type=int, default=0)
    ap.add_argument("--output", required=True)
    ap.add_argument("--laya-path", required=True)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()
    rows, diagnostics = load_records(args.episode_jsonl)
    if diagnostics:
        raise ValueError("use a complete fixture log")
    source = next(r["data"] for r in rows if r["kind"] == "snapshot" and r["data"]["step"] == args.step)
    snapshot = restore_snapshot(source["snapshot"])
    if snapshot.snapshot_id() != source["snapshot_id"]:
        raise ValueError("fixture identity mismatch")
    config = {**vars(args), "source_sha256": file_hash(args.episode_jsonl), "oracle": False,
              "purpose": "matched_interface_smoke_not_accuracy_evaluation"}
    if next(r for r in rows if r["kind"] == "run_start")["data"]["resolved_config"]["oracle"]:
        raise ValueError("fixture must be from a non-oracle run")
    recorder = RunRecorder(args.output, config, {"run_id": Path(args.output).name, "code": code_identity(),
                                               "versions": versions(), "oracle": False, "tracking_active": False})
    try:
        recorder.record("snapshot", source)
        recorder.manifest_update({"models": {"decision": model_identity(args.laya_path)}})
        providers = [RuleProvider(), load_laya_provider(args.laya_path, subfolder=None, device=args.device)]
        for provider in providers:
            started = time.perf_counter()
            decision = provider.decide(deepcopy(snapshot))
            recorder.record("matched_decision", {"provider": type(provider).__name__, "decision": asdict(decision),
                                                 "snapshot_id": snapshot.snapshot_id(),
                                                 "latency_ms": (time.perf_counter() - started) * 1000})
            assert decision.input_snapshot_id == snapshot.snapshot_id()
            assert decision.input_belief_id == snapshot.belief_id()
            assert decision.candidate_set_id == snapshot.candidate_set_id()
            assert decision.token in snapshot.allowed()
        recorder.record("termination", {"reason": "matched_interface_verified", "executed_actions": 0})
    except BaseException as exc:
        recorder.record("failure", {"category": "fixture_error", "exception": repr(exc)})
        raise
    finally:
        recorder.close()
        summarize(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
