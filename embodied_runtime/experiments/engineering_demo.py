"""Auditable visual embodied demo, not an E0 experiment or a success policy.

Reuses CDS v0.1, natural visual gates, LayaProvider, Runtime validation and the
native executor. Simulation waits for perception. No oracle previews or effects.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import random
import signal
import sys
import time

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..adapters.libero import LiberoWorldBackend
from ..adapters.libero_rgbd import LiberoRgbdSource
from ..adapters.locateanything import LocateAnythingWorker
from ..adapters.physics_preview import VisionCandidateBuilder
from ..decision_interface import (
    CandidateEffectBundle, CanonicalDecisionInput, candidate_id, project_belief,
    shared_atomic_candidates,
)
from ..fusion import MultiRateFusion, TemporalConfig
from ..runtime import Runtime
from ..runtime_core import LayaProvider, load_laya_provider
from ..vision import LocateAnythingProvider
from .collect_pairs import initial_state_inventory
from .records import (
    RunRecorder, code_identity, file_hash, load_records, model_identity,
    package_directory, repository_identity, summarize, versions,
)
from .reference_model_diagnostic import observe_forward

VERSION = "visual-connectivity-demo-v1"
QUERY = "the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground"
INSTRUCTION = ("Choose one allowed atomic action for the task. Null means unknown. "
               "Moves retain orientation/grip; rotations retain position/grip. "
               "Collision freedom is not established.")


class DemoTelemetry:
    """Persist first, then show selected stages without affecting decisions."""
    def __init__(self, recorder):
        self.recorder = recorder

    def __call__(self, kind, data):
        record_id = self.recorder.record(kind, data)
        display = None
        if kind in {"demo_boundary", "demo_sensing_complete", "failure", "termination"}:
            display = data
        elif kind == "demo_model_input":
            display = {"allowed": list(data["questions"]["action"]["criteria"]),
                       "singleton_forced_not_model": data["singleton_forced_not_model"]}
        elif kind == "decision":
            display = {"step": data["step"], "source": data["decision"]["source"],
                       "proposed": data["decision"]["token"], "latency_ms": data["decision_latency_ms"]}
        elif kind == "execution_started":
            display = {"step": data["step"], "executed_intent": data["decision"]["token"],
                       "source": data["decision"]["source"], "fallback_reason": data["fallback_reason"]}
        elif kind == "evaluation" and data["phase"] == "after":
            display = {"step": data["step"], "evaluator_only": True,
                       **{k: data["features"][k] for k in
                          ("remaining_open_mm", "finger_gap_mm", "moving_contact", "success")}}
        elif kind == "action":
            execution = data["execution"]
            display = {"step": data["step"], "executed": execution["token"],
                       "controls": execution["environment_step_count"],
                       "tcp_delta_mm": (np.asarray(execution["delta_m"])*1000).tolist(),
                       "contract_violation": execution["execution_contract_violation"]}
        if display is not None:
            try:
                print(f"[demo:{kind}] {json.dumps(display)}", flush=True)
            except (OSError, ValueError):
                # A closed presentation pipe must not interrupt physical execution.
                pass
        return record_id


class DemoView:
    """Compact presentation; authorization identities remain the live snapshot's.

    Natural soft direction scores stay in the audit, not this no-effect model
    view. No extra action is removed, ranked or introduced by this bridge.
    """
    def __init__(self, snapshot, query):
        self.snapshot = snapshot
        candidates = tuple(c for c in shared_atomic_candidates() if c.token in snapshot.allowed())
        if {c.token for c in candidates} != snapshot.allowed() or not candidates:
            raise ValueError("demo requires nonempty supported natural candidates")
        self.canonical = CanonicalDecisionInput(
            project_belief(snapshot, query), candidates, CandidateEffectBundle(candidate_id(candidates)))

    def __getattr__(self, key):
        return getattr(self.snapshot, key)

    def provider_input(self):
        return self.canonical.provider_input()

    def model_questions(self):
        questions = self.canonical.model_questions()
        questions["action"]["instructions"] = INSTRUCTION
        return questions


class RecordingAgent:
    def __init__(self, agent, sink):
        self.agent, self.sink, self.snapshot_id = agent, sink, None

    def __getattr__(self, key):
        return getattr(self.agent, key)

    def system_one(self, state, questions):
        audit = encoding_audit(self.agent, state, questions)
        if not audit.get("available") or audit.get("truncated"):
            raise ValueError("demo refuses unavailable or clipped model input")
        traces = []
        handle = observe_forward(self.agent, traces)
        started = time.perf_counter()
        try:
            result = self.agent.system_one(state, questions)
            self.sink("demo_model_response", {
                "snapshot_id": self.snapshot_id, "raw_response": result,
                "forward_traces": traces, "latency_ms": (time.perf_counter()-started)*1000,
                "device": str(self.agent.device), "dtype": str(self.agent.dtype)})
            expected = audit["questions"]["action"]
            if len(traces) != 1 or traces[0]["input_ids"] != [expected["effective_input_ids"]] or traces[0]["option_markers"] != [expected["option_markers"]]:
                raise ValueError("demo consumed tokens do not match audited input")
            return result
        finally:
            if handle is not None:
                handle.remove()


class DemoProvider:
    version = VERSION

    def __init__(self, agent, query, sink):
        self.query, self.sink = query, sink
        self.agent = RecordingAgent(agent, sink)
        self.provider = LayaProvider(self.agent)

    def decide(self, snapshot):
        view = DemoView(snapshot, self.query)
        self.agent.snapshot_id = snapshot.snapshot_id()
        audit = encoding_audit(self.agent, view.provider_input(), view.model_questions())
        self.sink("demo_model_input", {
            "snapshot_id": snapshot.snapshot_id(), "belief_id": snapshot.belief_id(),
            "natural_candidate_set_id": snapshot.candidate_set_id(),
            "canonical_input_id": view.canonical.snapshot_id(), "canonical": asdict(view.canonical),
            "state": view.provider_input(), "questions": view.model_questions(), "audit": audit,
            "singleton_forced_not_model": len(snapshot.allowed()) == 1,
            "oracle": False, "effects": "none", "history": "empty",
            "soft_candidate_evidence": "audit_only_not_model_input"})
        if not audit.get("available") or audit.get("truncated"):
            raise ValueError("demo refuses unavailable or clipped model input")
        return self.provider.decide(view)


class RecordingBackend(LiberoWorldBackend):
    """Only enable World's existing recording; native controls are unchanged."""
    def _execute(self, name):
        self.last_execution = self.world.execute(name, grip=self._grip_cmd, record=True)


def save_trajectory(backend, directory, step, recorder):
    relative = Path("trajectory") / f"action-{step:03d}.npz"
    path = directory / relative
    path.parent.mkdir(exist_ok=True)
    result = backend.last_execution
    with path.open("xb") as stream:
        np.savez_compressed(stream, commands=np.asarray(result["commands"]),
                            states_before=np.asarray(result["states"]), frames=np.asarray(result["frames"]),
                            state_after=backend.world.env.sim.get_state().flatten())
    recorder.record("demo_trajectory", {"step": step, "artifact": str(relative),
                                       "sha256": file_hash(path), "frames": len(result["frames"]),
                                       "frame_timing": "after each 0.05 s control"})


def run(args):
    import torch
    out = Path(args.output)
    temporal = TemporalConfig()
    builder = VisionCandidateBuilder(target_track=QUERY)
    recorder = RunRecorder(out, {**vars(args), "version": VERSION, "oracle": False,
        "effects": "none", "query": QUERY, "temporal": asdict(temporal),
        "candidates": builder.resolved_config(), "scheduling": "synchronous fresh capture per decision",
        "no_formal_experiment": True, "tracking_active": False, "covariance_calibrated": False},
        {"run_id": out.name, "code": code_identity(), "versions": versions()})
    backend = None
    emit = DemoTelemetry(recorder)
    old_handlers = {}
    success = False
    step = None
    last_action_step = None

    def interrupted(signum, _frame):
        raise TimeoutError(f"demo interrupted by signal {signum}")

    try:
        recorder.record("demo_invocation", {"argv": sys.argv, "cwd": str(Path.cwd()),
            "python": sys.executable, "environment": {key: os.environ.get(key) for key in
                ("CUDA_VISIBLE_DEVICES", "MUJOCO_GL", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}})
        for sig in (signal.SIGALRM, signal.SIGTERM):
            old_handlers[sig] = signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, args.timeout_s)
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        recorder.manifest_update({"models": {"decision": model_identity(args.laya_path),
                                            "vision": model_identity(args.locateanything_path)}})
        inventory = initial_state_inventory("top_drawer", args.libero_root, args.config_dir)
        if args.init_state_id >= inventory["count"]:
            raise ValueError("benchmark initial state out of range")
        recorder.record("demo_initial_identity", {"task": "top_drawer", "binding": inventory["binding"],
            "init_state_id": args.init_state_id, "seed": args.seed,
            "benchmark_state_id": inventory["state_ids"][args.init_state_id]})
        backend = RecordingBackend.from_task("top_drawer", seed=args.seed, init_state_id=args.init_state_id,
            render=True, libero_root=args.libero_root, config_dir=args.config_dir)
        world = backend.world
        import jev_libero.world
        import libero
        recorder.manifest_update({"environment_repositories": {
            "jev": repository_identity(package_directory(jev_libero.world)),
            "libero": repository_identity(package_directory(libero))}})
        recorder.record("environment", {"purpose": "execution_and_evaluation_only", "task_config": world.config,
            "instruction": world.task, "sim_state": world.env.sim.get_state().flatten(),
            "initial_state": backend.execution_state()})
        agent = load_laya_provider(args.laya_path, subfolder=None, device=args.device).agent
        provider = DemoProvider(agent, QUERY, emit)
        runtime = Runtime(f"demo-top_drawer-init{args.init_state_id}-seed{args.seed}", provider, backend, builder,
            fusion=MultiRateFusion(config=temporal), event_sink=emit,
            sim_clock=lambda: world.data.time, oracle=False)
        locator = LocateAnythingWorker(args.locateanything_path, device=args.device)
        source = LiberoRgbdSource(world)
        vision = None
        for step in range(args.steps + int(args.observe_final)):
            terminal_observation = step == args.steps or success
            frame = source.capture()
            recorder.capture(frame)
            emit("demo_boundary", {"step": step, "capture_seq": frame["capture_seq"],
                                  "capture_sim_time": frame["capture_sim_time"],
                                  "phase": "terminal_observation" if terminal_observation else "sensing"})
            if vision is None:
                vision = LocateAnythingProvider(lambda _rgb, _query: {}, frame["intrinsics"])
            before = world.env.sim.get_state().flatten().copy()
            recorder.record("vision_started", {"capture_seq": frame["capture_seq"], "capture_sim_time": frame["capture_sim_time"]})
            result = locator.infer(frame["rgb"], QUERY)
            event = vision.observe(frame["rgb"], frame["depth_m"], QUERY,
                episode_id=runtime.store.episode_id, source_seq=frame["capture_seq"],
                capture_sim_time=frame["capture_sim_time"], track_id=QUERY,
                camera_to_world_matrix=frame["camera_to_world"], inference_result=result)
            recorder.record("vision_completed", {"capture_seq": frame["capture_seq"], "result": result, "event": event})
            if not np.array_equal(before, world.env.sim.get_state().flatten()):
                raise RuntimeError("physical state moved during paused perception")
            visual_admitted = False
            if event is None:
                emit("failure", {"category": "vision_missing", "step": step})
            else:
                visual_admitted = runtime.ingest(event, now_sim=float(world.data.time))
            proprio_admitted = runtime.observe("proprio", float(world.data.time), backend.proprioception())
            emit("demo_sensing_complete", {"step": step, "capture_seq": frame["capture_seq"],
                "capture_sim_time": frame["capture_sim_time"], "proprio_source_seq": runtime.source_seq,
                "visual_event_admitted": visual_admitted, "proprio_event_admitted": proprio_admitted,
                "after_action_step": last_action_step, "terminal_observation": terminal_observation})
            if terminal_observation:
                break  # Observe the final outcome without inventing another model decision.
            recorder.record("evaluation", {"step": step, "phase": "before", "oracle_evaluator": True,
                                            "features": world.features()})
            row = runtime.step(float(world.data.time), goal={"task": "top_drawer", "instruction": world.task,
                               "target_query": QUERY, "satisfied": False})
            save_trajectory(backend, out, step, recorder)
            emit("evaluation", {"step": step, "phase": "after", "oracle_evaluator": True,
                                            "features": world.features()})
            success = row["result"]["success"]
            last_action_step = step
            if success and not args.observe_final:
                break
        emit("termination", {"reason": "success" if success else "action_budget", "success": success,
                             "step": last_action_step})
    except BaseException as exc:
        emit("failure", {"category": "demo_error", "step": step, "exception": repr(exc)})
        emit("termination", {"reason": "demo_error", "success": success, "step": step})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        try:
            if backend is not None:
                backend.close()
        finally:
            recorder.close()
            summarize(out)
    return out


def replay_check(directory):
    """Replay actual controls, not model decisions; report every boundary error."""
    directory = Path(directory)
    rows, errors = load_records(directory / "episodes.jsonl")
    if errors:
        raise ValueError("cannot verify an incomplete record chain")
    config = next(r["data"]["resolved_config"] for r in rows if r["kind"] == "run_start")
    backend = LiberoWorldBackend.from_task("top_drawer", seed=config["seed"], init_state_id=config["init_state_id"],
        render=False, libero_root=config["libero_root"], config_dir=config["config_dir"])
    checks = []
    try:
        world = backend.world
        initial = next(r["data"]["sim_state"] for r in rows if r["kind"] == "environment")
        checks.append({"boundary": "initial", "max_error": float(np.max(np.abs(world.env.sim.get_state().flatten()-initial)))})
        for row in rows:
            if row["kind"] != "demo_trajectory":
                continue
            data = row["data"]
            path = directory / data["artifact"]
            if file_hash(path) != data["sha256"]:
                raise ValueError("trajectory artifact hash mismatch")
            with np.load(path) as archive:
                for j, (command, expected) in enumerate(zip(archive["commands"], archive["states_before"], strict=True)):
                    checks.append({"boundary": f"{data['step']}:{j}:before",
                        "max_error": float(np.max(np.abs(world.env.sim.get_state().flatten()-expected)))})
                    world.obs, _, _, _ = world.env.step(command)
                    backend._grip_cmd = float(command[-1])
                checks.append({"boundary": f"{data['step']}:after", "max_error": float(np.max(
                    np.abs(world.env.sim.get_state().flatten()-archive["state_after"])))})
        result = {"kind": "control_replay_not_independent_policy_run", "checks": checks,
                  "passed": len(checks) > 1 and all(c["max_error"] <= 1e-8 for c in checks),
                  "raw_source_sha256": file_hash(directory / "episodes.jsonl"), "tolerance": 1e-8}
        (directory / "replay-check.json").write_text(json.dumps(result, indent=2)+"\n")
        return result
    finally:
        backend.close()


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--steps", type=int, default=4)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--init-state-id", type=int, default=0)
    p.add_argument("--device", default="cuda")
    p.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    p.add_argument("--locateanything-path", default="/home/junhongli/models/huggingface/LocateAnything-3B")
    p.add_argument("--libero-root", default="/home/junhongli/projects/LIBERO")
    p.add_argument("--config-dir", default="/home/junhongli/runs/libero-config")
    p.add_argument("--timeout-s", type=float, default=300.)
    p.add_argument("--observe-final", action="store_true",
                   help="capture and fuse the final physical outcome after the action budget or success")
    p.add_argument("--replay-check", action="store_true")
    p.add_argument("--render-report", action="store_true")
    return p


def main():
    args = parser().parse_args()
    if args.replay_check:
        result = replay_check(args.output)
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
    elif args.render_report:
        from .demo_report import render_report
        print(render_report(args.output))
    else:
        if not 1 <= args.steps <= 8 or args.init_state_id < 0 or args.timeout_s <= 0:
            raise ValueError("demo requires 1..8 actions and positive timeout")
        print(run(args))


if __name__ == "__main__":
    main()
