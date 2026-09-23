"""Explicit oracle drawer reference: Jev effect-contract union -> one Laya choice.

No hierarchy, winner selection, visual changes or CDS changes. Existing Jev
two-step reposition witnesses are used only when the one-step union is empty.
Contracts perform task-specific candidate-policy filtering, not just safety.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import random
import signal
import sys
import time

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..adapters.libero import LiberoWorldBackend, CONTRACT_TOLERANCES
from ..adapters.physics_preview import PhysicsPreviewCandidateBuilder
from ..runtime import Runtime
from ..runtime_core import AtomicExecutor, Decision, LayaProvider, load_laya_provider
from .collect_pairs import initial_state_inventory
from .engineering_demo import RecordingAgent, save_trajectory, replay_check
from .operating_regime_probe import context_id
from .records import (
    RunRecorder, code_identity, file_hash, load_records, model_identity,
    package_directory, repository_identity, versions,
)

VERSION = "privileged-drawer-reference-v1-lookahead2-forced-singleton"
PRIVILEGE = {"effect_source": "oracle_sim", "privileged": True,
             "candidate_filtering": "task_specific_effect_contract_union"}
INSTRUCTION = (
    "Choose one action to close the drawer using its predicted effects. "
    "Prefer completion, closure, then contact or approach; avoid obstacle force."
)
TOLERANCE = 1e-8


def actions():
    from jev_libero.actions import ACTIONS
    return ACTIONS


def measured_outcome(world, before, token, execution):
    """Fresh live measurements, never taken from candidate predictions."""
    after = world.features()
    joint = float(world.data.qpos[world.qindex])
    success = bool(world.env.check_success())
    if joint != after["qpos_m"] or success != after["success"]:
        raise RuntimeError("independent live evaluator disagrees with feature reading")
    return {"action": token, "before": before, "after": after,
            "actual_joint_qpos_m": joint, "official_success": success,
            "closure_mm": 1000. * (joint - before["qpos_m"]),
            "gap_reduction_mm": before["distance_to_moving_geometry_mm"] - after["distance_to_moving_geometry_mm"],
            "controls": execution["environment_step_count"],
            "obstacle_peak_N": execution["peak_obstacle_force_N"]}


class JevAtomicExecutor(AtomicExecutor):
    """Execute exactly one existing Jev primitive; no policy or goal repair."""

    def execute(self, token):
        if token not in actions():
            raise ValueError(f"unknown Jev primitive: {token}")
        backend, spec = self.backend, actions()[token]
        world = backend.world
        before = backend.execution_state()
        expected_grip = {"open": -1., "close": 1.}.get(token, backend._grip_cmd)
        result = world.execute(token, grip=backend._grip_cmd, record=True)
        backend._grip_cmd = result["grip"]
        backend.last_execution = result
        after = backend.execution_state()
        delta = np.asarray(after["tcp_xyz"]) - before["tcp_xyz"]
        expected_delta = np.zeros(3)
        if "axis" in spec:
            expected_delta[spec["axis"]] = spec["mm"] / 1000.
        rotation = np.asarray(after["orientation"]) @ np.asarray(before["orientation"]).T
        expected_rotation = np.eye(3)
        if "rot_axis" in spec:
            axis = np.eye(3)[spec["rot_axis"]]
            x, y, z = axis
            skew = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
            theta = np.radians(spec["deg"])
            expected_rotation += np.sin(theta) * skew + (1 - np.cos(theta)) * (skew @ skew)
        rotation_error = float(np.degrees(np.arccos(np.clip(
            (np.trace(rotation @ expected_rotation.T) - 1) / 2, -1., 1.))))
        translation_error = float(np.linalg.norm(delta - expected_delta))
        nominal_flags = []
        if translation_error > CONTRACT_TOLERANCES["translation_error_m" if "axis" in spec else "hold_translation_m"]:
            nominal_flags.append("translation_outside_reset_reference_envelope")
        if rotation_error > CONTRACT_TOLERANCES["rotation_error_deg" if "rot_axis" in spec else "hold_rotation_deg"]:
            nominal_flags.append("rotation_outside_reset_reference_envelope")
        command_error = (backend._grip_cmd != expected_grip or
                         any(float(a[-1]) != expected_grip for a in result["commands"]))
        return {"token": token, "before": before["tcp_xyz"], "after": after["tcp_xyz"],
                "delta_m": delta.tolist(), "success": bool(world.env.check_success()),
                "execution_before": before, "execution_after": after,
                "environment_step_count": result["steps"],
                "low_level_commands": [a.tolist() for a in result["commands"]],
                "peak_obstacle_force_N": result["peak_obstacle_force_N"],
                "obstacle_pairs_seen": result["obstacle_pairs_seen"],
                "execution_contract_version": VERSION,
                "execution_contract_violation": command_error,
                "execution_contract_reason": ["gripper_command_mismatch"] if command_error else [],
                "nominal_translation_error_m": translation_error,
                "nominal_rotation_error_deg": rotation_error,
                "nominal_tracking_flags": nominal_flags,
                "nominal_reference_tolerances": CONTRACT_TOLERANCES,
                "reset_envelope_validated_for_all_27": False}


def compare_prediction(world, prediction, outcome, execution):
    error = float(np.max(np.abs(world.env.sim.get_state().flatten() -
                               np.asarray(prediction["sim_state_after"]))))
    comparisons = {
        "state_max_error": error,
        "closure_error_mm": abs(outcome["closure_mm"] - prediction["closing_mm"]),
        "gap_reduction_error_mm": abs(outcome["gap_reduction_mm"] - prediction["geometry_approach_mm"]),
        "obstacle_force_error_N": abs(execution["peak_obstacle_force_N"] - prediction["peak_obstacle_force_N"]),
        "controls_match": outcome["controls"] == prediction["steps"],
        "success_match": outcome["official_success"] == prediction["after"]["success"],
        "target_contact_match": outcome["after"]["moving_contact"] == prediction["after"]["moving_contact"],
        "obstacle_contact_match": outcome["after"]["obstacle_contact"] == prediction["after"]["obstacle_contact"],
        "obstacle_pairs_match": sorted(execution["obstacle_pairs_seen"]) == sorted(prediction["obstacle_pairs_seen"]),
    }
    comparisons["passed"] = (
        all(comparisons[k] <= TOLERANCE for k in
            ("state_max_error", "closure_error_mm", "gap_reduction_error_mm", "obstacle_force_error_N"))
        and all(comparisons[k] for k in ("controls_match", "success_match", "target_contact_match",
                                       "obstacle_contact_match", "obstacle_pairs_match"))
        and not execution["execution_contract_violation"]
    )
    return comparisons


def ensure_real_choice(candidates, grip):
    offered = [c.token for c in candidates if c.feasible]
    # hold/open (or hold/close) are exact native command aliases at retained grip.
    physical = {"hold" if n == ("open" if grip < 0 else "close") else n for n in offered}
    if len(physical) < 2:
        raise RuntimeError("reference requires at least two distinct physical operations")
    return offered


class ReferenceBuilder(PhysicsPreviewCandidateBuilder):
    def __init__(self, backend, sink):
        super().__init__(backend.world, grip_command=backend.gripper_command,
                         action_map={name: name for name in actions()})
        self.backend, self.sink = backend, sink

    def build(self, belief):
        from jev_libero.policy import contracts

        initial = context_id(self.backend)
        candidates = super().build(belief)
        one_step_pools = self.last_preview["pools"]
        one_step_rejected = self.last_preview["rejected"]
        witnesses, evaluations = {}, 0
        if not one_step_pools:
            witnesses, evaluations = self.world.two_step_witnesses(
                self.backend.gripper_command()
            )
            for name, witness in witnesses.items():
                self.last_preview["predictions"][name]["reposition_witness"] = witness
            pools, rejected = contracts(
                self.last_preview["before"], self.last_preview["predictions"],
                collision_aware=self.collision_aware, task_config=self.world.config,
            )
            self.last_preview["pools"] = pools
            self.last_preview["rejected"] = rejected
        self.last_preview.update({
            "one_step_pools": one_step_pools,
            "one_step_rejected": one_step_rejected,
            "lookahead_triggered": not bool(one_step_pools),
            "two_step_evaluations": evaluations,
            "reposition_witnesses": witnesses,
        })
        restored = context_id(self.backend)
        if initial != restored:
            raise RuntimeError("physics preview changed live controller/integration context")
        pools = self.last_preview["pools"]
        eligible = {name for pool in pools.values() for name in pool}
        candidates = tuple(replace(
            c,
            feasible=c.token in eligible,
            reason_codes=() if c.token in eligible else (
                self.last_preview["rejected"].get(c.token, "no_feasible_contract"),
            ),
            metadata={
                **PRIVILEGE,
                "effect_contracts": [k for k, pool in pools.items() if c.token in pool],
                "lookahead_triggered": not bool(one_step_pools),
                "reposition_witness": witnesses.get(c.token),
            },
        ) for c in candidates)
        self.last_diagnostics.update({**PRIVILEGE,
            "lookahead_triggered": not bool(one_step_pools),
            "two_step_evaluations": evaluations,
            "reposition_witness_count": len(witnesses),
            "candidate_veto_count": sum(not c.feasible for c in candidates)})
        self.sink("reference_preview", {"belief_id": belief.belief_id(), **PRIVILEGE,
                  "context_before": initial, "context_after": restored,
                  "restored": True, **self.last_preview})
        if not eligible:
            raise RuntimeError("reference has no candidate after existing two-step witness processing")
        return candidates


def presentation(before, predictions, names, grip, last):
    state = (
        "Task: close top drawer. effect_source=oracle_sim; privileged=true. "
        "Preview up to 8 controls/0.4s. XYZ world mm; rotations world degrees; "
        "nominal commands, predicted dynamics; grip retained except open/close.\n"
        f"Current opening={before['remaining_open_mm']:.3f}mm "
        f"gap={before['distance_to_moving_geometry_mm']:.2f}mm "
        f"target_contact={int(before['moving_contact'])} "
        f"obstacle_contact={int(before['obstacle_contact'])} "
        f"grip={'open' if grip < 0 else 'closed'} finger_gap={before['finger_gap_mm']:.2f}mm.\n"
    )
    if last is None:
        state += "Last actual: none.\n"
    else:
        after = last["after"]
        state += (f"Last actual: {last['action']}; closure={last['closure_mm']:.3f}mm "
                  f"gap_reduction={last['gap_reduction_mm']:.2f}mm "
                  f"target_contact={int(after['moving_contact'])} "
                  f"obstacle_contact={int(after['obstacle_contact'])} "
                  f"success={int(last['official_success'])} controls={last['controls']}.\n")
    has_witnesses = any(predictions[name].get("reposition_witness") for name in names)
    if has_witnesses:
        effect_codes = {"advance_target": "A", "establish_contact": "E",
                        "approach_target": "P", "release_contact": "R",
                        "reposition": "W"}
        common_values = {
            "fp": {f"{predictions[name]['peak_obstacle_force_N']:.1f}" for name in names},
            "fs": {str(int(predictions[name]["after"]["success"])) for name in names},
            "n": {str(predictions[name]["steps"]) for name in names},
            "wp": {f"{predictions[name]['reposition_witness']['peak_obstacle_force_N']:.1f}"
                   for name in names},
            "ws": {str(int(predictions[name]["reposition_witness"]["terminal_success"]))
                   for name in names},
        }
        varying = [key for key, values in common_values.items() if len(values) != 1]
        common = ",".join(f"{key}={next(iter(values))}" for key, values in common_values.items()
                          if len(values) == 1)
        state += (
            "W rows: a c g t > w C G T e"
            f"{' ' + ' '.join(varying) if varying else ''}. "
            "c/g/t=first closure/gap/contact; w=verified second; "
            "C/G/T=two-step net closure/gap/final contact; "
            "e=A advance,E establish,P approach,R release. "
            "Execute a only; replan. "
            "fp/fs/n=first obstacleN/success/controls; "
            "wp/ws=witness obstacleN/success. "
            f"Common: {common}.\n"
        )
    else:
        state += ("Effects: action|closure_mm (positive closes)|gap_reduction_mm (positive approaches)"
                  "|target_contact|obstacle_peak_N|success|controls\n")
    for name in names:
        p = predictions[name]
        witness = p.get("reposition_witness")
        if witness is None:
            state += (f"{name}|{p['closing_mm']:.3f}|{p['geometry_approach_mm']:.2f}|"
                      f"{int(p['after']['moving_contact'])}|{p['peak_obstacle_force_N']:.1f}|"
                      f"{int(p['after']['success'])}|{p['steps']}\n")
            continue
        codes = "".join(effect_codes[value] for value in witness["witnessed_effects"])
        values = {"fp": f"{p['peak_obstacle_force_N']:.1f}",
                  "fs": str(int(p["after"]["success"])), "n": str(p["steps"]),
                  "wp": f"{witness['peak_obstacle_force_N']:.1f}",
                  "ws": str(int(witness["terminal_success"]))}
        suffix = "".join(f" {values[key]}" for key in varying)
        state += (
            f"{name} {p['closing_mm']:.3f} {p['geometry_approach_mm']:.2f} "
            f"{int(p['after']['moving_contact'])} > {witness['second_input']} "
            f"{witness['net_progress']:.3f} {witness['net_gap_reduction_mm']:.2f} "
            f"{int(witness['terminal_contact'])} {codes}{suffix}\n"
        )
    questions = {"action": {"type": "choice", "instructions": INSTRUCTION,
                             "criteria": {name: "" for name in names}}}
    return state, questions


class ReferenceView:
    def __init__(self, snapshot, state, questions):
        self.snapshot, self.state, self.questions = snapshot, state, questions

    def __getattr__(self, name):
        return getattr(self.snapshot, name)

    def provider_input(self):
        return self.state

    def model_questions(self):
        return self.questions


class ReferenceProvider:
    version = VERSION

    def __init__(self, agent, builder, sink):
        self.agent = RecordingAgent(agent, sink)
        self.provider = LayaProvider(self.agent)
        self.builder, self.sink = builder, sink
        self.last = None
        self.last_outcome_id = None

    def decide(self, snapshot):
        backend = self.builder.backend
        names = [c.token for c in snapshot.candidates if c.feasible]
        preview = self.builder.last_preview
        pool_source = "lookahead" if preview.get("lookahead_triggered", False) else "one_step"
        if len(names) == 1:
            token = names[0]
            self.sink("reference_forced_singleton", {**PRIVILEGE,
                "snapshot_id": snapshot.snapshot_id(), "belief_id": snapshot.belief_id(),
                "candidate_set_id": snapshot.candidate_set_id(), "option_order": names,
                "candidate_count": 1, "pool_source": pool_source, "token": token,
                "forced_singleton": True, "model_called": False,
                "previous_outcome_record_id": self.last_outcome_id})
            return Decision(token=token, probabilities={}, confidence=0.0,
                source="forced_singleton", input_revision=snapshot.revision,
                input_sim_time=snapshot.asof_sim_time, completed_wall_time=time.time(),
                valid_until_sim=snapshot.asof_sim_time + .5, latency_ms=0.0,
                input_belief_id=snapshot.belief_id(),
                candidate_set_id=snapshot.candidate_set_id(),
                input_snapshot_id=snapshot.snapshot_id())
        names = ensure_real_choice(snapshot.candidates, backend.gripper_command())
        state, questions = presentation(preview["before"], preview["predictions"], names,
                                        backend.gripper_command(), self.last)
        audit = encoding_audit(self.agent, state, questions)
        self.sink("reference_model_input", {**PRIVILEGE,
            "snapshot_id": snapshot.snapshot_id(), "belief_id": snapshot.belief_id(),
            "candidate_set_id": snapshot.candidate_set_id(),
            "option_order": names, "state": state, "questions": questions, "audit": audit,
            "candidate_count": len(names), "pool_source": pool_source,
            "forced_singleton": False, "model_called": True,
            "previous_outcome_record_id": self.last_outcome_id})
        if not audit.get("available") or audit["truncated"]:
            raise RuntimeError("reference input unavailable or truncated; no choices removed")
        self.agent.snapshot_id = snapshot.snapshot_id()
        decision = self.provider.decide(ReferenceView(snapshot, state, questions))
        if decision.source != "laya" or decision.status != "valid" or decision.token not in names:
            raise RuntimeError("reference refuses invalid, singleton or fallback decision")
        return decision


def make_backend(args, render):
    return LiberoWorldBackend.from_task("top_drawer", seed=args.seed, init_state_id=args.init_state_id,
        render=render, libero_root=args.libero_root, config_dir=args.config_dir)


def run(args):
    import torch
    out = Path(args.output)
    recorder = RunRecorder(out, {**vars(args), "version": VERSION, "oracle": True,
        **PRIVILEGE, "scheduling": "paused observation/preview/inference at action boundary",
        "primitive_order": list(actions()), "lookahead": 2,
        "two_step_reposition_witnesses": True, "hierarchy": False,
        "checkpoint_context_unchanged": True, "success_predicate": "official_LIBERO",
        "candidate_policy_filtering": "union of all task-specific effect contracts; no winner/top-k"},
        {"run_id": out.name, "code": code_identity(), "versions": versions()})
    backend = None
    step, success, termination = None, False, "action_budget"
    previous_handler = signal.getsignal(signal.SIGALRM)

    def timeout(*_):
        raise TimeoutError("reference wall-time budget exceeded")

    try:
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.timeout_s)
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        recorder.record("reference_invocation", {"argv": sys.argv, "cwd": str(Path.cwd()),
            "python": sys.executable, "environment": {k: os.environ.get(k) for k in
            ("CUDA_VISIBLE_DEVICES", "MUJOCO_GL", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}})
        recorder.manifest_update({"models": {"decision": model_identity(args.laya_path)}})
        inventory = initial_state_inventory("top_drawer", args.libero_root, args.config_dir)
        recorder.record("reference_initial_identity", {"task": "top_drawer", "binding": inventory["binding"],
            "init_state_id": args.init_state_id, "seed": args.seed,
            "benchmark_state_id": inventory["state_ids"][args.init_state_id]})
        backend = make_backend(args, render=True)
        world = backend.world
        import jev_libero.world
        import libero
        recorder.manifest_update({"environment_repositories": {
            "jev": repository_identity(package_directory(jev_libero.world)),
            "libero": repository_identity(package_directory(libero))}})
        recorder.record("environment", {"purpose": "explicit_privileged_reference", **PRIVILEGE,
            "task_config": world.config, "sim_state": world.env.sim.get_state().flatten(),
            "initial_state": backend.execution_state(), "features": world.features()})
        if backend.success():
            raise RuntimeError("initial state already successful")
        agent = load_laya_provider(args.laya_path, subfolder=None, device=args.device).agent
        if str(agent.device) != args.device and not str(agent.device).startswith(args.device + ":"):
            raise RuntimeError("unexpected model device fallback")
        recorder.manifest_update({"model_execution": {"device": str(agent.device), "dtype": str(agent.dtype),
            "config": agent.cfg, "torch_deterministic": torch.are_deterministic_algorithms_enabled()}})
        builder = ReferenceBuilder(backend, recorder.record)
        provider = ReferenceProvider(agent, builder, recorder.record)
        runtime = Runtime(out.name, provider, backend, builder, oracle=True,
            sim_clock=lambda: world.data.time, event_sink=recorder.record,
            executor=JevAtomicExecutor(backend))
        previous_after = None
        for step in range(args.steps):
            before = world.features()
            if previous_after is not None and before != previous_after:
                raise RuntimeError("actual outcome not preserved at next observation")
            if not runtime.observe("oracle_sim", float(world.data.time), before):
                raise RuntimeError("oracle observation rejected")
            recorder.record("reference_feedback", {"step": step,
                "previous_outcome_record_id": provider.last_outcome_id,
                "observation_source_seq": runtime.source_seq,
                "matches_previous_outcome": previous_after is None or before == previous_after})
            row = runtime.step(float(world.data.time), goal={"task": "top_drawer",
                "instruction": world.task, "satisfied": False})
            save_trajectory(backend, out, step, recorder)
            outcome = measured_outcome(world, before, row["decision"].token, row["result"])
            comparison = compare_prediction(world,
                builder.last_preview["predictions"][row["decision"].token], outcome, row["result"])
            pool_source = "lookahead" if builder.last_preview["lookahead_triggered"] else "one_step"
            forced_singleton = row["decision"].source == "forced_singleton"
            provider.last_outcome_id = recorder.record("reference_outcome", {
                "step": step, "snapshot_id": row["snapshot_id"], **outcome,
                "comparison": comparison, "nominal_tracking_flags": row["result"]["nominal_tracking_flags"],
                "candidate_count": len(row["snapshot"].allowed()), "pool_source": pool_source,
                "lookahead_recovery": pool_source == "lookahead",
                "forced_singleton": forced_singleton,
                "genuine_laya_decision": row["decision"].source == "laya",
                "decision_source": row["decision"].source, "fallback": row["decision_invalid_reason"]})
            provider.last, previous_after = outcome, outcome["after"]
            print(json.dumps({"step": step, "offered": len(row["snapshot"].allowed()),
                "pool_source": pool_source, "choice_source": row["decision"].source,
                "choice": outcome["action"], "closure_mm": outcome["closure_mm"],
                "gap_mm": outcome["after"]["distance_to_moving_geometry_mm"],
                "contact": outcome["after"]["moving_contact"],
                "remaining_mm": outcome["after"]["remaining_open_mm"],
                "success": outcome["official_success"], "prediction_matches": comparison["passed"]}), flush=True)
            if not comparison["passed"] or row["decision_invalid_reason"]:
                raise RuntimeError("preview/executor mismatch or fallback")
            success = outcome["official_success"]
            if success:
                termination = "success"
                break
        recorder.record("termination", {"reason": termination, "success": success, "step": step})
    except BaseException as exc:
        recorder.record("failure", {"category": "reference_error", "step": step, "exception": repr(exc)})
        recorder.record("termination", {"reason": "reference_error", "success": False, "step": step})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        try:
            if backend is not None:
                backend.close()
        finally:
            recorder.close()
            summarize_reference(out)
    return success


def preflight(args):
    """All 27 branches at three mechanical fixtures; no model loaded or called."""
    from jev_libero.world import Snapshot
    out = Path(args.output)
    recorder = RunRecorder(out, {**vars(args), "version": VERSION, **PRIVILEGE,
        "purpose": "mechanical_preflight_not_policy", "no_model_calls": True},
        {"run_id": out.name, "code": code_identity(), "versions": versions()})
    backend = None
    try:
        for fixture in ("reset", "closed_gripper", "loaded_step48"):
            backend = make_backend(args, render=False)
            world = backend.world
            executor = JevAtomicExecutor(backend)
            if fixture == "closed_gripper":
                executor.execute("close")
            if fixture == "loaded_step48":
                trajectory = Path(args.trajectory) / "sim_trajectory.npz"
                recorder.record("preflight_fixture_source", {"path": str(trajectory),
                    "sha256": file_hash(trajectory), "only_mechanical_test": True})
                with np.load(trajectory) as archive:
                    for command, expected in zip(archive["actions"][:48], archive["states_before"][:48], strict=True):
                        error = float(np.max(np.abs(world.env.sim.get_state().flatten() - expected)))
                        if error > TOLERANCE:
                            raise RuntimeError(f"loaded fixture replay mismatch: {error}")
                        world.obs, _, _, _ = world.env.step(command)
                        backend._grip_cmd = float(command[-1])
            source = Snapshot(world)
            grip, last = backend._grip_cmd, deepcopy(backend.last_execution)
            initial = context_id(backend)
            before, predictions = world.predict_all(grip)
            if context_id(backend) != initial:
                raise RuntimeError("preflight preview changed source context")
            for name in actions():
                source.restore()
                backend._grip_cmd, backend.last_execution = grip, deepcopy(last)
                if context_id(backend) != initial:
                    raise RuntimeError("preflight restore mismatch")
                execution = executor.execute(name)
                outcome = measured_outcome(world, before, name, execution)
                check = compare_prediction(world, predictions[name], outcome, execution)
                recorder.record("preflight_action", {"fixture": fixture, "action": name,
                    "predicted": predictions[name], "actual": outcome,
                    "execution": execution, "comparison": check})
                if not check["passed"]:
                    raise RuntimeError(f"preflight mismatch: {fixture}/{name}: {check}")
            source.restore()
            backend._grip_cmd, backend.last_execution = grip, deepcopy(last)
            if context_id(backend) != initial:
                raise RuntimeError("final preflight restore mismatch")
            recorder.record("preflight_fixture_passed", {"fixture": fixture, "actions": 27, "restored": True})
            print(f"PASS {fixture}: 27 preview/executor matches, context restored", flush=True)
            backend.close()
            backend = None
        recorder.record("termination", {"reason": "preflight_passed", "actions": 81})
    except BaseException as exc:
        recorder.record("failure", {"category": "preflight_error", "exception": repr(exc)})
        raise
    finally:
        if backend is not None:
            backend.close()
        recorder.close()


def summarize_reference(directory):
    """Rebuild a per-step evidence index; preserve full inputs and all failures."""
    directory = Path(directory)
    rows, errors = load_records(directory / "episodes.jsonl")
    if errors:
        raise ValueError(f"incomplete evidence chain: {errors}")
    inputs = {r["data"]["snapshot_id"]: r["data"] for r in rows if r["kind"] == "reference_model_input"}
    forced = {r["data"]["snapshot_id"]: r["data"] for r in rows
              if r["kind"] == "reference_forced_singleton"}
    if set(inputs) & set(forced):
        raise ValueError("snapshot cannot be both model input and forced singleton")
    selections = {**inputs, **forced}
    decisions = {r["data"]["snapshot_id"]: r["data"]["decision"] for r in rows if r["kind"] == "decision"}
    previews = {r["data"]["belief_id"]: r["data"] for r in rows if r["kind"] == "reference_preview"}
    trajectories = {r["data"]["step"]: r["data"] for r in rows if r["kind"] == "demo_trajectory"}
    responses = {r["data"]["snapshot_id"]: r["data"] for r in rows if r["kind"] == "demo_model_response"}
    for kind, mapping in (("reference_model_input", inputs),
                          ("reference_forced_singleton", forced), ("decision", decisions),
                          ("reference_preview", previews), ("demo_trajectory", trajectories),
                          ("demo_model_response", responses)):
        if len(mapping) != sum(r["kind"] == kind for r in rows):
            raise ValueError(f"duplicate {kind} identity")
    trace, previous_id = [], None
    for row in rows:
        if row["kind"] != "reference_outcome":
            continue
        d = row["data"]
        selection, decision = selections[d["snapshot_id"]], decisions[d["snapshot_id"]]
        preview = previews[selection["belief_id"]]
        if selection["previous_outcome_record_id"] != previous_id:
            raise ValueError("broken actual-outcome-to-input feedback link")
        if decision["token"] != d["action"] or d["action"] not in selection["option_order"]:
            raise ValueError("decision/outcome membership mismatch")
        eligible = {name for pool in preview["pools"].values() for name in pool}
        if set(selection["option_order"]) != eligible or len(selection["option_order"]) != len(eligible):
            raise ValueError("offered menu differs from complete effect-contract union")
        is_forced = d["snapshot_id"] in forced
        if is_forced:
            if (len(selection["option_order"]) != 1 or not selection["forced_singleton"]
                    or selection["model_called"] or selection["token"] != d["action"]
                    or decision["source"] != "forced_singleton" or decision["probabilities"]
                    or decision["confidence"] != 0.0 or d["snapshot_id"] in responses):
                raise ValueError("invalid forced-singleton evidence")
        else:
            # Recorder sorts dictionary keys, so option_order and actual forward tokens
            # (rather than serialized criteria order) are authoritative.
            response = responses[d["snapshot_id"]]
            audit = selection["audit"]
            expected = audit["questions"]["action"]
            forwards = response["forward_traces"]
            if (len(selection["option_order"]) < 2 or selection.get("forced_singleton", False)
                    or not selection.get("model_called", True)
                    or audit["truncated"] or not audit["available"] or len(forwards) != 1
                    or forwards[0]["input_ids"] != [expected["effective_input_ids"]]
                    or forwards[0]["option_markers"] != [expected["option_markers"]]
                    or response["raw_response"]["answers"]["action"]["choice"] != d["action"]
                    or decision["source"] != "laya"):
                raise ValueError("invalid model consumption evidence")
        if not preview["restored"]:
            raise ValueError("preview did not restore live context")
        artifact = trajectories[d["step"]]
        path = directory / artifact["artifact"]
        if file_hash(path) != artifact["sha256"]:
            raise ValueError("trajectory artifact hash mismatch")
        selected = preview["predictions"][d["action"]]
        with np.load(path) as saved:
            error = float(np.max(np.abs(saved["state_after"] - selected["sim_state_after"])))
            if error != d["comparison"]["state_max_error"] or len(saved["commands"]) != d["controls"]:
                raise ValueError("cached comparison differs from raw trajectory")
        if (not np.isclose(d["closure_mm"], 1000 * (d["actual_joint_qpos_m"] - d["before"]["qpos_m"]),
                           rtol=0, atol=TOLERANCE)
                or d["official_success"] != d["after"]["success"]):
            raise ValueError("actual physical outcome inconsistent")
        pool_source = "lookahead" if preview.get("lookahead_triggered", False) else "one_step"
        if (selection.get("pool_source", pool_source) != pool_source
                or d.get("pool_source", pool_source) != pool_source
                or d.get("candidate_count", len(selection["option_order"])) != len(selection["option_order"])
                or d.get("forced_singleton", is_forced) != is_forced):
            raise ValueError("choice classification disagrees with candidate evidence")
        trace.append({"step": d["step"], "candidates": selection["option_order"],
            "candidate_count": len(selection["option_order"]), "pool_source": pool_source,
            "choice_source": "forced_singleton" if is_forced else "laya",
            "forced_singleton": is_forced, "lookahead_recovery": pool_source == "lookahead",
            "rejected": preview["rejected"], "selection": selection,
            "model_input": None if is_forced else selection,
            "decision": decision, "selected_prediction": selected,
            "all_predictions": preview["predictions"], "effect_contract_pools": preview["pools"],
            "outcome": d})
        previous_id = row["record_id"]
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminations = [r["data"] for r in rows if r["kind"] == "termination"]
    success = bool(trace and trace[-1]["outcome"]["official_success"])
    qualifies = (success and not failures and bool(terminations) and terminations[-1]["reason"] == "success"
        and any(t["choice_source"] == "laya" for t in trace)
        and all(not t["outcome"]["fallback"] and t["outcome"]["comparison"]["passed"]
                and ((t["choice_source"] == "laya" and t["candidate_count"] >= 2)
                     or (t["choice_source"] == "forced_singleton" and t["candidate_count"] == 1))
                for t in trace))
    counts = {
        "genuine_laya_decisions": sum(t["choice_source"] == "laya" for t in trace),
        "forced_singleton_continuations": sum(t["forced_singleton"] for t in trace),
        "zero_pool_lookahead_recoveries": sum(t["lookahead_recovery"] for t in trace),
    }
    summary = {"version": VERSION, **PRIVILEGE, "raw_sha256": file_hash(directory / "episodes.jsonl"),
        "actual_success": success, "qualifies_single_episode": qualifies,
        "independent_repeatability_not_established_by_one_episode": True,
        **counts, "failures": failures, "terminations": terminations, "trace": trace,
        "unexecuted_previews": [p for p in previews.values()
                               if p["belief_id"] not in {t["selection"]["belief_id"] for t in trace}]}
    (directory / "reference-evidence.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# Privileged reference evidence", "", "Task-specific effect contracts perform candidate-policy filtering.",
             f"Actual success: {success}. Single-episode qualification: {qualifies}.",
             (f"Genuine Laya decisions: {counts['genuine_laya_decisions']}; forced-singleton "
              f"continuations: {counts['forced_singleton_continuations']}; zero-pool lookahead "
              f"recoveries: {counts['zero_pool_lookahead_recoveries']}."), "",
             "| Step | Pool | Candidates | Choice source | Action | Predicted closure mm | Actual closure mm | Remaining mm | Match |",
             "|---|---|---|---|---|---:|---:|---:|---|"]
    for t in trace:
        o = t["outcome"]
        lines.append(f"| {t['step']} | {t['pool_source']} | {', '.join(t['candidates'])} | "
            f"{t['choice_source']} | {o['action']} | "
            f"{t['selected_prediction']['closing_mm']:.6f} | {o['closure_mm']:.6f} | "
            f"{o['after']['remaining_open_mm']:.6f} | {o['comparison']['passed']} |")
    lines += ["", "Full inputs, predictions, feedback links and failures: reference-evidence.json.",
              "This report is not a new model run or a repeatability claim."]
    for preview in summary["unexecuted_previews"]:
        eligible = sorted({name for pool in preview["pools"].values() for name in pool})
        lines += ["", f"Unexecuted boundary: {preview['belief_id']}",
                  f"Eligible actions: {eligible}. No action executed at this boundary.",
                  "| Primitive | Predicted closure mm | Gap reduction mm | Contact | Rejection |",
                  "|---|---:|---:|---|---|"]
        for name, p in preview["predictions"].items():
            lines.append(f"| {name} | {p['closing_mm']:.6f} | {p['geometry_approach_mm']:.6f} | "
                         f"{p['after']['moving_contact']} | {preview['rejected'].get(name, '')} |")
    (directory / "reference-report.md").write_text("\n".join(lines) + "\n")
    return summary


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--mode", choices=("run", "preflight", "summarize", "replay"), default="run")
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--timeout-s", type=float, default=1800.)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--init-state-id", type=int, default=0)
    p.add_argument("--device", default="cuda")
    p.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    p.add_argument("--libero-root", default="/home/junhongli/projects/LIBERO")
    p.add_argument("--config-dir", default="/home/junhongli/runs/libero-config")
    p.add_argument("--trajectory", default="/home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1")
    return p


def main():
    args = parser().parse_args()
    if args.steps <= 0 or args.timeout_s <= 0:
        raise ValueError("positive action/time budgets required")
    if args.mode == "preflight":
        preflight(args)
    elif args.mode == "summarize":
        summary = summarize_reference(args.output)
        print(json.dumps({k: v for k, v in summary.items() if k != "trace"}, indent=2))
    elif args.mode == "replay":
        result = replay_check(args.output)
        print(json.dumps(result, indent=2))
        if not result["passed"]:
            raise SystemExit(1)
    elif not run(args):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
