"""Small LIBERO smoke runner. Raw durable records are the source of truth."""
from __future__ import annotations

import argparse
import json
import random
import signal
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ..adapters.libero import CONTRACT_TOLERANCES, CONTRACT_VERSION, LiberoWorldBackend
from ..adapters.libero_rgbd import LiberoRgbdSource
from ..adapters.locateanything import LatestFrameWorker, LocateAnythingWorker
from ..adapters.physics_preview import PhysicsPreviewCandidateBuilder, VisionCandidateBuilder
from ..fusion import MultiRateFusion, TemporalConfig
from ..runtime import Runtime
from ..runtime_core import RuleProvider, load_laya_provider
from ..vision import LocateAnythingProvider
from .records import RunRecorder, code_identity, model_identity, package_directory, repository_identity, summarize, versions


def run_episode(args):
    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    out = Path(args.output) / run_id
    visual = args.experiment == "vision"
    temporal = TemporalConfig(**json.loads(Path(args.temporal_config).read_text())) if args.temporal_config else TemporalConfig()
    builder = VisionCandidateBuilder(target_track=args.query)
    config = {**vars(args), "run_id": run_id, "oracle": not visual,
              "method": f"{args.experiment}_{args.provider}", "experiment_version": "stage2-smoke-v1",
              "temporal": asdict(temporal) if visual else None,
              "candidate_builder": builder.resolved_config() if visual else {"version": "physics-preview-candidates-v1", "collision_aware": True},
              "tracking_active": False, "init_index": 0, "success_predicate": "official_LIBERO",
              "atomic": {"step_m": .01, "rotation_world_z_deg": 10, "control_steps": 8,
                         "contract_version": CONTRACT_VERSION, "tolerances": CONTRACT_TOLERANCES},
              "vision": {"camera": "agentview", "size": [384, 384], "event_ttl_s": .75,
                         "covariance_source": "heuristic_depth_projection_v1", "covariance_calibrated": False,
                         "depth_sigma_floor_m": .002, "pixel_sigma_floor": 1, "box_sigma_fraction": .05,
                         "score_source": "box_present_indicator_not_calibrated_probability"},
              "scheduling": "one capture per action boundary; simulation paused during decision",
              "timeout_scope": "whole run wall clock, interrupt via SIGALRM"}
    recorder = RunRecorder(out, config, {"run_id": run_id, "code": code_identity(),
                                       "versions": versions(), "oracle": not visual,
                                       "tracking_active": False, "experiment_version": "stage2-smoke-v1"})
    backend = worker = None
    phase, step, success = "startup", None, False
    old_handlers = {}

    def interrupted(signum, _frame):
        if signum == signal.SIGALRM:
            raise TimeoutError("run wall-time budget exceeded")
        raise KeyboardInterrupt(f"signal {signum}")

    try:
        for sig in (signal.SIGTERM, signal.SIGALRM):
            old_handlers[sig] = signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, args.timeout_s)
        random.seed(args.seed)
        np.random.seed(args.seed)
        model_ids = {}
        if visual:
            model_ids["vision"] = model_identity(args.locateanything_path)
        if args.provider == "laya":
            model_ids["decision"] = model_identity(args.laya_path)
        recorder.manifest_update({"models": model_ids})
        phase = "environment_startup"
        backend = LiberoWorldBackend.from_task(args.task, seed=args.seed, render=args.render or visual,
                                               libero_root=args.libero_root, config_dir=args.config_dir)
        world = backend.world
        import jev_libero.world
        import libero
        recorder.manifest_update({"environment_repositories": {
            "jev": repository_identity(package_directory(jev_libero.world)),
            "libero": repository_identity(package_directory(libero))}})
        recorder.record("environment", {"purpose": "execution_and_offline_evaluation_only",
                                        "task_config": world.config, "instruction": world.task,
                                        "initial_state": backend.execution_state(),
                                        "initial_qpos": world.data.qpos.copy(), "initial_qvel": world.data.qvel.copy(),
                                        "sim_timestep": float(world.model.opt.timestep)})
        phase = "model_startup"
        if visual or args.provider == "laya":
            import torch
            torch.manual_seed(args.seed)
            recorder.manifest_update({"torch_execution": {"cuda_version": torch.version.cuda,
                "device": args.device or "cuda", "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                "cudnn_benchmark": torch.backends.cudnn.benchmark,
                "gpu": torch.cuda.get_device_name(args.device or "cuda") if torch.cuda.is_available() else None}})
        provider = RuleProvider() if args.provider == "rule" else load_laya_provider(args.laya_path, subfolder=None, device=args.device)
        if not visual:
            builder = PhysicsPreviewCandidateBuilder(world, grip_command=backend.gripper_command)
        runtime = Runtime(f"{args.task}-seed{args.seed}", provider, backend, builder,
                          fusion=MultiRateFusion(config=temporal) if visual else None,
                          event_sink=recorder.record, sim_clock=lambda: world.data.time, oracle=not visual)
        recorder.record("provider", {"name": type(provider).__name__, "version": provider.version})
        if visual:
            model = LocateAnythingWorker(args.locateanything_path, device=args.device or "cuda")
            source = LiberoRgbdSource(world)
            first_frame = source.capture()
            vision = LocateAnythingProvider(lambda _rgb, _query: {}, first_frame["intrinsics"])
            worker = LatestFrameWorker(vision, model.infer, query=args.query,
                                       episode_id=runtime.store.episode_id, event_sink=recorder.record)
        termination = "action_budget"
        for step in range(args.steps):
            phase = "observation"
            # Privileged telemetry never enters a visual snapshot.
            recorder.record("evaluation", {"step": step, "phase": "before", "oracle_evaluator": True,
                                           "sim_time": float(world.data.time), "features": world.features()})
            if visual:
                frame = first_frame if step == 0 else source.capture()
                recorder.capture(frame)
                worker.submit(frame)
                deadline = time.perf_counter() + (args.vision_warmup_s if step == 0 else 0)
                events = []
                while True:
                    event = worker.poll()
                    if event is not None:
                        events.append(event)
                        continue
                    if events or time.perf_counter() >= deadline:
                        break
                    time.sleep(.01)
                for event in events:
                    runtime.ingest(event, now_sim=float(world.data.time))
                runtime.observe("proprio", float(world.data.time), backend.proprioception())
            else:
                runtime.observe("oracle", float(world.data.time), world.features())
            phase = "decision_execution"
            result = runtime.step(float(world.data.time), goal={"task": args.task, "instruction": world.task,
                                                               "target_query": args.query, "satisfied": False})
            success = result["result"]["success"]
            phase = "evaluation"
            recorder.record("evaluation", {"step": step, "phase": "after", "oracle_evaluator": True,
                                           "snapshot_id": result["snapshot_id"], "sim_time": float(world.data.time),
                                           "features": world.features()})
            if success:
                termination = "success"
                break
        recorder.record("termination", {"reason": termination, "success": success, "step": step})
    except BaseException as exc:
        category = ("timeout" if isinstance(exc, TimeoutError) else "interrupted" if isinstance(exc, KeyboardInterrupt)
                    else "model_error" if phase == "model_startup" else "run_error")
        recorder.record("failure", {"category": category, "phase": phase, "step": step, "exception": repr(exc)})
        recorder.record("termination", {"reason": category, "success": success, "step": step})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        try:
            if worker is not None:
                worker.close()
            if backend is not None:
                backend.close()
        except Exception as exc:
            recorder.record("failure", {"category": "environment_error", "phase": "cleanup", "exception": repr(exc)})
        finally:
            recorder.close()
            summarize(out)
            print(out)
    return out


def parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="top_drawer")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--provider", choices=("rule", "laya"), default="rule")
    ap.add_argument("--experiment", choices=("oracle", "vision"), default="oracle")
    ap.add_argument("--query", default="the top drawer of the cabinet")
    ap.add_argument("--locateanything-path", default="/home/junhongli/models/huggingface/LocateAnything-3B")
    ap.add_argument("--vision-warmup-s", type=float, default=3.0)
    ap.add_argument("--timeout-s", type=float, default=180)
    ap.add_argument("--temporal-config", help="JSON TemporalConfig overrides")
    ap.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    ap.add_argument("--device", default=None)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--libero-root", default=None)
    ap.add_argument("--config-dir", default=None)
    ap.add_argument("--run-id")
    ap.add_argument("--output", default="runs")
    return ap


def main():
    args = parser().parse_args()
    if args.steps < 1 or args.timeout_s <= 0 or args.vision_warmup_s < 0:
        raise ValueError("positive action/time budgets required")
    run_episode(args)


if __name__ == "__main__":
    main()
