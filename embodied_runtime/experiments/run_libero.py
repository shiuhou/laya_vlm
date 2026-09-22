"""Run a small, auditable LIBERO/Jev episode."""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from ..adapters.libero import LiberoWorldBackend
from ..adapters.physics_preview import PhysicsPreviewCandidateBuilder
from ..runtime import Runtime
from ..runtime_core import RuleProvider, load_laya_provider


def _jsonable(value):
    if hasattr(value, "__dict__") and not isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.__dict__.items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return value


def run_episode(args):
    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    out = Path(args.output) / run_id
    out.mkdir(parents=True, exist_ok=True)
    backend = LiberoWorldBackend.from_task(args.task, seed=args.seed, render=args.render, libero_root=args.libero_root, config_dir=args.config_dir)
    world = backend.world
    provider = RuleProvider()
    if args.provider == "laya":
        provider = load_laya_provider(args.laya_path, subfolder=None, device=args.device)
    runtime = Runtime(f"{args.task}-seed{args.seed}", provider, backend, PhysicsPreviewCandidateBuilder(world))
    rows = []
    try:
        for step in range(args.steps):
            before = world.features()
            runtime.observe("oracle", float(world.data.time), before, quality=1.0, valid_until_sim=float(world.data.time) + 0.5)
            started = time.perf_counter()
            result = runtime.step(float(world.data.time), goal={"satisfied": bool(before.get("success"))})
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            snap, decision, execution = result["snapshot"], result["decision"], result["result"]
            preview = runtime.candidate_builder.last_preview or {}
            rows.append({
                "task": args.task, "seed": args.seed, "step": step, "method": args.provider,
                "oracle": True, "belief_revision": snap.revision,
                "candidates": [_jsonable(c.__dict__) for c in snap.candidates],
                "decision": _jsonable(decision.__dict__), "decision_latency_ms": elapsed_ms,
                "before_features": _jsonable(before), "after_features": _jsonable(world.features()),
                "success": bool(world.success()), "vision_capture_seq": None,
                "vision_age_s": None, "model_latency_ms": None,
                "physics_preview": {"rejected": _jsonable(preview.get("rejected", {})),
                                    "pool_names": {k: list(v) for k, v in preview.get("pools", {}).items()}},
                "execution": _jsonable(execution),
            })
            if world.success():
                break
    finally:
        world.close()
    jsonl = out / "episodes.jsonl"
    with jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    fields = ["task", "seed", "step", "method", "decision", "success", "decision_latency_ms"]
    with (out / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] if k != "decision" else row[k]["token"] for k in fields})
    successes = sum(bool(r["success"]) for r in rows)
    (out / "summary.md").write_text(
        f"# LIBERO smoke run\n\n- task: `{args.task}`\n- seed: `{args.seed}`\n- method: `{args.provider}`\n- steps: `{len(rows)}`\n- success_at_step_end: `{successes > 0}`\n- oracle_state_used: `true` (execution/success upper-bound line)\n- vision_semantic_used: `false`\n\nEach action and preview contract is recorded in `episodes.jsonl`.\n",
        encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"run_id": run_id, "task": args.task, "seed": args.seed, "provider": args.provider, "oracle": True, "vision": False}, indent=2), encoding="utf-8")
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="top_drawer")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--provider", choices=("rule", "laya"), default="rule")
    ap.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    ap.add_argument("--device", default=None)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--libero-root", default=None)
    ap.add_argument("--config-dir", default=None)
    ap.add_argument("--run-id")
    ap.add_argument("--output", default="runs")
    args = ap.parse_args()
    run_episode(args)


if __name__ == "__main__":
    main()
