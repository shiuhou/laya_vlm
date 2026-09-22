"""Run a small, auditable LIBERO/Jev episode."""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from ..adapters.libero import LiberoWorldBackend
from ..adapters.libero_rgbd import LiberoRgbdSource
from ..adapters.locateanything import LocateAnythingWorker
from ..adapters.physics_preview import (
    PhysicsPreviewCandidateBuilder,
    VisionCandidateBuilder,
)
from ..runtime import Runtime
from ..runtime_core import RuleProvider, load_laya_provider
from ..vision import LocateAnythingProvider


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
    visual = args.experiment.startswith("vision")
    if args.provider == "laya":
        provider = load_laya_provider(args.laya_path, subfolder=None, device=args.device)
    candidate_builder = VisionCandidateBuilder() if visual else PhysicsPreviewCandidateBuilder(world)
    runtime = Runtime(f"{args.task}-seed{args.seed}", provider, backend, candidate_builder)
    rgbd = LocateAnythingWorker(args.locateanything_path, device=args.device or "cuda") if visual else None
    vision_source = LiberoRgbdSource(world) if visual else None
    rows = []
    try:
        for step in range(args.steps):
            before = world.features()
            vision_event = None
            vision_result = None
            if visual:
                frame = vision_source.capture()
                infer_started = time.perf_counter()
                vision_result = rgbd.infer(frame["rgb"], args.query)
                vision_provider = LocateAnythingProvider(lambda _rgb, _query, result=vision_result: result, frame["intrinsics"])
                vision_event = vision_provider.observe(
                    frame["rgb"], frame["depth_m"], args.query,
                    episode_id=f"{args.task}-seed{args.seed}", source_seq=frame["capture_seq"],
                    capture_sim_time=frame["capture_sim_time"], camera_to_world_matrix=frame["camera_to_world"],
                )
                if vision_event is not None:
                    runtime.ingest(vision_event, now_sim=float(world.data.time))
                vision_latency_ms = (time.perf_counter() - infer_started) * 1000.0
            else:
                vision_latency_ms = None
                runtime.observe("oracle", float(world.data.time), before, quality=1.0, valid_until_sim=float(world.data.time) + 0.5)
            started = time.perf_counter()
            result = runtime.step(float(world.data.time), goal={"task": args.task, "satisfied": False if visual else bool(before.get("success"))})
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            snap, decision, execution = result["snapshot"], result["decision"], result["result"]
            preview = runtime.candidate_builder.last_preview or {}
            rows.append({
                "task": args.task, "seed": args.seed, "step": step, "method": f"{args.experiment}_{args.provider}",
                "oracle": not visual, "belief_revision": snap.revision,
                "candidates": [_jsonable(c.__dict__) for c in snap.candidates],
                "decision": _jsonable(decision.__dict__), "decision_latency_ms": elapsed_ms,
                "before_features": _jsonable(before), "after_features": _jsonable(world.features()),
                "success": bool(backend.success()), "vision_capture_seq": vision_event.source_seq if vision_event else None,
                "vision_age_s": (float(world.data.time) - vision_event.capture_sim_time) if vision_event else None,
                "model_latency_ms": vision_result.get("model_latency_ms") if vision_result else vision_latency_ms,
                "physics_preview": None if visual else {"rejected": _jsonable(preview.get("rejected", {})),
                                    "pool_names": {k: list(v) for k, v in preview.get("pools", {}).items()}},
                "vision_result": _jsonable(vision_result),
                "execution": _jsonable(execution),
            })
            if backend.success():
                break
    finally:
        if rgbd is not None:
            del rgbd
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
        f"# LIBERO smoke run\n\n- task: `{args.task}`\n- seed: `{args.seed}`\n- method: `{args.provider}`\n- steps: `{len(rows)}`\n- success_at_step_end: `{successes > 0}`\n- oracle_state_used: `{not visual}` (only execution/success checks may read simulator state)\n- vision_semantic_used: `{visual}`\n\nEach action and preview contract is recorded in `episodes.jsonl`.\n",
        encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"run_id": run_id, "task": args.task, "seed": args.seed, "provider": args.provider, "oracle": not args.experiment.startswith("vision"), "vision": args.experiment.startswith("vision")}, indent=2), encoding="utf-8")
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="top_drawer")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--provider", choices=("rule", "laya"), default="rule")
    ap.add_argument("--experiment", choices=("oracle", "vision"), default="oracle")
    ap.add_argument("--query", default="the top drawer of the cabinet")
    ap.add_argument("--locateanything-path", default="/home/junhongli/models/huggingface/LocateAnything-3B")
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

