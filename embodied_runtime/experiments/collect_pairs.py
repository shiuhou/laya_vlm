"""Bounded paired-state smoke from recorded controls; not a formal E0 collector.

Model decisions are offline probes and NEVER control the replayed environment.
Collection pauses simulation for RGB-D inference, keeping state alignment exact.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from ..adapters.libero_rgbd import LiberoRgbdSource
from ..adapters.locateanything import LocateAnythingWorker
from ..adapters.physics_preview import VisionCandidateBuilder
from ..decision_interface import geometric_effects, project_belief, project_oracle, shared_atomic_candidates
from ..fusion import MultiRateFusion
from ..runtime import Runtime
from ..runtime_core import RuleProvider, _sha256_json
from ..vision import LocateAnythingProvider
from .equivalence import make_pair
from .records import RunRecorder, code_identity, file_hash, model_identity, package_directory, repository_identity, versions


def initial_state_inventory(task, libero_root, config_dir):
    from jev_libero.config import load_task
    from jev_libero.environment import load_libero
    benchmark, _, _, _ = load_libero(libero_root, config_dir)
    binding = load_task(task)["binding"]
    suite = benchmark.get_benchmark_dict()[binding["suite"]]()
    index = next(i for i in range(suite.n_tasks) if suite.get_task(i).name == binding["task"])
    states = np.asarray(suite.get_task_init_states(index))
    ids = [_sha256_json(s.tolist()) for s in states]
    return {"binding": binding, "count": len(states), "shape": list(states.shape),
            "state_ids": ids, "unique_states": len(set(ids)),
            "max_abs_difference_from_init0": np.max(np.abs(states - states[0]), axis=1).tolist(),
            "note": "distinct vectors are not proof of independent task regimes"}


def physical_evidence(backend, unit, step):
    world = backend.world
    state = world.env.sim.get_state().flatten().tolist()
    data = {**unit, "environment_step": step, "sim_time": float(world.data.time), "sim_state": state,
            "robot_proprioception": backend.proprioception(), "features": world.features()}
    data["physical_state_id"] = _sha256_json(data)
    return data


def oracle_target(backend, physical):
    world = backend.world
    points = np.concatenate([world.scene.local_vertices(g) @ world.data.geom_xmat[g].reshape(3, 3).T + world.data.geom_xpos[g]
                             for g in world.scene.moving])
    return {"source_id": physical["physical_state_id"],
            "target_position_m": ((points.min(axis=0) + points.max(axis=0)) / 2).tolist(),
            "position_definition": "moving_collision_geometry_world_aabb_center",
            "moving_contact": physical["features"]["moving_contact"],
            "remaining_open_mm": physical["features"]["remaining_open_mm"]}


def collect(args):
    directory = Path(args.trajectory)
    config = json.loads((directory / "config.json").read_text())
    task_config = json.loads((directory / "task_config.json").read_text())
    trajectory = np.load(directory / "sim_trajectory.npz")
    from jev_libero.config import load_task
    installed = load_task(args.task)
    # Historical drawer records predate declarative measurements. The only
    # allowed migration is the equivalent legacy raw.joint_position accessor.
    resolved_recorded = dict(task_config)
    if "measurements" not in resolved_recorded and args.task == "top_drawer":
        resolved_recorded["measurements"] = {"joint_position": {"kind": "joint_position"}}
    if resolved_recorded != installed:
        raise ValueError("recorded trajectory does not match requested task configuration")
    samples = sorted(set(args.sample_steps))
    if not samples or len(samples) > 8 or min(samples) < 0 or max(samples) > len(trajectory["actions"]):
        raise ValueError("smoke requires 1..8 valid sample steps, not a formal grid")
    unit = {"task": args.task, "init_state_id": config["initial_state"], "seed": config["seed"]}
    resolved = {**vars(args), **unit, "experiment_version": "decision-interface-smoke-v0.1",
                "oracle": True, "purpose": "paired_diagnostic_not_deployable_policy",
                "candidate_mode": "shared_atomic_offline_probes", "effect_mode": "none",
                "history": "previous recorded low-level control + robot displacement only",
                "replay_state_error_tolerance": 1e-8, "sampling": "paused_at_selected_control_boundaries",
                "trajectory_sha256": file_hash(directory / "sim_trajectory.npz"),
                "trajectory_config": config, "trajectory_task_config": task_config,
                "resolved_task_config": installed,
                "legacy_measurement_migration": task_config != resolved_recorded,
                "tracking_active": False, "covariance_calibrated": False}
    recorder = RunRecorder(args.output, resolved, {"run_id": Path(args.output).name, "code": code_identity(),
                                                  "versions": versions(), "oracle": True})
    backend = None
    try:
        inventory = initial_state_inventory(args.task, args.libero_root, args.config_dir)
        recorder.record("initial_state_inventory", inventory)
        unit["benchmark_state_id"] = inventory["state_ids"][unit["init_state_id"]]
        backend = LiberoWorldBackend.from_task(args.task, seed=unit["seed"], init_state_id=unit["init_state_id"],
                                               render=not args.audit_only, libero_root=args.libero_root, config_dir=args.config_dir)
        world = backend.world
        import jev_libero.world
        import libero
        recorder.manifest_update({"repositories": {"jev": repository_identity(package_directory(jev_libero.world)),
                                                   "libero": repository_identity(package_directory(libero))}})
        if not args.audit_only:
            recorder.manifest_update({"models": {"vision": model_identity(args.locateanything_path)}})
            model = LocateAnythingWorker(args.locateanything_path, device=args.device)
            source = LiberoRgbdSource(world)
        builder = VisionCandidateBuilder(target_track=args.query)
        runtime = Runtime("paired-smoke", RuleProvider(), backend, builder, MultiRateFusion(), oracle=False,
                          event_sink=recorder.record)
        recorder.record("projection_config", {"temporal": asdict(runtime.fusion.config),
                                             "natural_candidates": builder.resolved_config(),
                                             "target_query": args.query})
        candidates = shared_atomic_candidates()
        history = ()
        max_error, pairs = 0., 0
        def export(physical, variant):
            nonlocal pairs
            now = float(world.data.time)
            runtime.observe("proprio", now, backend.proprioception())
            snap = runtime.store.snapshot(now, goal={"task": args.task, "instruction": world.task, "target_query": args.query})
            # observe() republishes the current-time fusion including age/covariance.
            natural = builder.build(snap)
            perceptual = project_belief(snap, args.query)
            oracle = project_oracle(perceptual, oracle_target(backend, physical))
            pair = make_pair(oracle, perceptual, candidates, physical={**physical, "variant": variant},
                             history=history, natural_perceptual=natural)
            recorder.record("belief_fixture", {"belief_id": snap.belief_id(), "snapshot": json.loads(snap.canonical_json())})
            recorder.record("paired_state", pair)
            recorder.record("tier0_effect_diagnostic", {"pair_id": pair["pair_id"],
                             "not_supplied_to_primary_replay": True, "effects": asdict(geometric_effects(perceptual, candidates))})
            pairs += 1

        for step in range(len(trajectory["actions"]) + 1):
            expected = trajectory["states_before"][step] if step < len(trajectory["actions"]) else trajectory["final_state"]
            error = float(np.max(np.abs(world.env.sim.get_state().flatten() - expected)))
            max_error = max(error, max_error)
            if error > 1e-8:
                raise RuntimeError(f"trajectory state mismatch at {step}: {error}")
            physical = physical_evidence(backend, unit, step)
            recorder.record("collection_state", {**physical, "replay_state_max_error": error})
            if step in samples and not args.audit_only:
                if step == args.stale_step and runtime.fusion.geometry:
                    export(physical, "previous_observation_only")
                frame = source.capture()
                recorder.capture(frame)
                started = time.perf_counter()
                result = model.infer(frame["rgb"], args.query)
                vision = LocateAnythingProvider(lambda *_: result, frame["intrinsics"])
                event = vision.observe(frame["rgb"], frame["depth_m"], args.query, episode_id="paired-smoke",
                                       source_seq=frame["capture_seq"], capture_sim_time=frame["capture_sim_time"],
                                       camera_to_world_matrix=frame["camera_to_world"], inference_result=result)
                recorder.record("vision_completed", {"capture_seq": frame["capture_seq"], "result": result,
                                                     "event": event, "latency_ms": (time.perf_counter() - started) * 1000})
                if event is not None:
                    runtime.ingest(event, now_sim=float(world.data.time))
                else:
                    recorder.record("failure", {"category": "vision_missing", "environment_step": step})
                if physical_evidence(backend, unit, step)["physical_state_id"] != physical["physical_state_id"]:
                    raise RuntimeError("simulator changed while producing paired perception")
                export(physical, "fresh_capture")
            if step == len(trajectory["actions"]):
                break
            before_tcp = backend.tcp_pos()
            before_time = float(world.data.time)
            action = trajectory["actions"][step]
            # This is an external recorded collector control, not a new atomic
            # vocabulary or a DecisionProvider output. Keep it outside Runtime.step.
            recorder.record("collection_control_started", {"step": step, "control": action,
                                                            "source": "recorded_trajectory_not_model_decision"})
            world.obs, _, _, _ = world.env.step(action)
            backend._grip_cmd = float(action[-1])  # retained actuator command during recorded replay
            history = ({"action": {"recorded_robosuite_control": action.tolist()},
                        "tcp_delta_m": (backend.tcp_pos() - before_tcp).tolist(),
                        "elapsed_sim_s": float(world.data.time) - before_time,
                        "gripper_command": backend.proprioception()["gripper_command"], "source": "proprioception"},)
        recorder.record("termination", {"reason": "collection_smoke_complete", "pairs": pairs,
                                         "controls": len(trajectory["actions"]), "max_replay_state_error": max_error,
                                         "collector_success": backend.success(), "model_decisions_executed": 0})
    except BaseException as exc:
        recorder.record("failure", {"category": "collection_error", "exception": repr(exc)})
        raise
    finally:
        if backend:
            backend.close()
        recorder.close()
    print(args.output)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectory", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--task", default="top_drawer")
    ap.add_argument("--sample-steps", type=int, nargs="+", default=[0, 80, 144, 152])
    ap.add_argument("--stale-step", type=int, default=152)
    ap.add_argument("--audit-only", action="store_true")
    ap.add_argument("--query", default="the top drawer of the cabinet")
    ap.add_argument("--locateanything-path", default="/home/junhongli/models/huggingface/LocateAnything-3B")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--libero-root")
    ap.add_argument("--config-dir")
    collect(ap.parse_args())


if __name__ == "__main__":
    main()
