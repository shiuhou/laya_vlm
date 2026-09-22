"""Bounded, privileged atomic-regime diagnostics; never decision-model inputs.

Replay archived controls on real benchmark resets. Preserve native actions, then
compare STOP with explicitly labeled controller-only / feedback-only interventions.
These interventions are NOT fixes, candidates, or replacement collection states.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from ..adapters.libero import LiberoWorldBackend
from ..decision_interface import shared_atomic_candidates
from ..runtime_core import AtomicExecutor, _sha256_json
from .audit_initial_states import phases
from .collect_pairs import initial_state_inventory, physical_evidence
from .records import RunRecorder, code_identity, file_hash, repository_identity, package_directory, versions

SAMPLE_STEPS = {0: (0, 24, 29, 33, 48, 80, 120, 140, 144, 153, 155),
                1: (0, 33, 37, 38, 48, 80, 140, 144, 155),
                2: (0, 35, 36, 37, 48, 80, 140, 144, 155)}
VARIANTS = ("native", "reanchor_orientation", "fk_feedback", "both")


def angle_degrees(rotation):
    return float(np.degrees(np.arccos(np.clip((np.trace(rotation) - 1) / 2, -1., 1.))))


def _fingerprint(value):
    """Stable description of mutable snapshot caches, not Python object addresses."""
    if isinstance(value, np.ndarray):
        return {"shape": value.shape, "dtype": str(value.dtype),
                "bytes_sha256": hashlib.sha256(value.tobytes()).hexdigest()}
    if isinstance(value, np.generic):
        return _fingerprint(value.item())
    if isinstance(value, dict):
        return {str(k): _fingerprint(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_fingerprint(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if callable(value):
        return {"callable": f"{value.__module__}.{value.__qualname__}"}
    if hasattr(value, "__dict__"):
        return {"class": f"{type(value).__module__}.{type(value).__qualname__}", "attributes": _fingerprint(vars(value))}
    raise TypeError(f"unsupported mutable snapshot value: {type(value)}")


def context_id(backend):
    """Fingerprint integration state and Snapshot-covered controller/robot caches.

    Snapshot itself copies full MjData. This signature additionally checks its
    documented mutable caches; it is not a claim to cover arbitrary model mutation.
    """
    from jev_libero.world import Snapshot
    world = backend.world
    snapshot = Snapshot(world)
    spec = world.mujoco.mjtState.mjSTATE_INTEGRATION
    state = np.empty(world.mujoco.mj_stateSize(world.model, spec))
    world.mujoco.mj_getState(world.model, world.data, state, spec)
    return _sha256_json({"integration": _fingerprint(state), "grip": backend._grip_cmd,
        "controller": _fingerprint(snapshot.controller), "robot": _fingerprint(snapshot.robot),
        "gripper": _fingerprint(snapshot.gripper), "clock": _fingerprint(snapshot.clock),
        "observables": _fingerprint(snapshot.observables), "obs": _fingerprint(snapshot.obs),
        "numpy_rng": _fingerprint(snapshot.rng), "python_rng": _fingerprint(snapshot.py_rng)})


class Telemetry:
    """Fresh FK on a scratch MjData; never forward/update the source simulator."""
    def __init__(self, backend):
        self.backend, self.world = backend, backend.world
        self.scratch = self.world.mujoco.MjData(self.world.model)

    def kinematics(self):
        world = self.world
        world.mujoco.mj_copyData(self.scratch, world.model, world.data)
        world.mujoco.mj_forward(world.model, self.scratch)
        site = world.env.robots[0].eef_site_id
        linear, angular = np.zeros((3, world.model.nv)), np.zeros((3, world.model.nv))
        world.mujoco.mj_jacSite(world.model, self.scratch, linear, angular, site)
        return (self.scratch.site_xpos[site].copy(), self.scratch.site_xmat[site].reshape(3, 3).copy(),
                linear @ self.scratch.qvel, angular @ self.scratch.qvel)

    def read(self):
        world, backend = self.world, self.backend
        robot, controller = world.env.robots[0], world.env.robots[0].controller
        position, orientation, velocity, angular = self.kinematics()
        obs = world.env.env._observables["robot0_eef_pos"]
        robot_contacts = []
        for index in range(world.data.ncon):
            contact = world.data.contact[index]
            names = [world.env.sim.model.geom_id2name(int(g)) or "" for g in (contact.geom1, contact.geom2)]
            if any("robot" in name or "gripper" in name for name in names):
                force = np.zeros(6)
                world.mujoco.mj_contactForce(world.model, world.data, index, force)
                robot_contacts.append({"geoms": names, "normal_force_N": float(force[0])})
        return {"sim_time": float(world.data.time), "tcp_observed_m": backend.tcp_pos().tolist(),
                "tcp_fk_m": position.tolist(), "orientation_fk": orientation.tolist(),
                "velocity_fk_mps": velocity.tolist(), "angular_velocity_fk_radps": angular.tolist(),
                "site_cached_m": world.data.site_xpos[robot.eef_site_id].tolist(),
                "controller_goal_pos_m": controller.goal_pos.tolist(),
                "controller_goal_ori": controller.goal_ori.tolist(),
                "controller_goal_ori_error_deg": angle_degrees(controller.goal_ori @ orientation.T),
                "controller_cached_tcp_m": controller.ee_pos.tolist(),
                "robot_qvel": world.data.qvel[controller.qvel_index].tolist(),
                "gripper_command": backend._grip_cmd,
                "gripper_width_joint_m": backend.proprioception()["gripper_width_m"],
                "gripper_actuator_target": robot.gripper.current_action.tolist(),
                "applied_robot_torque": robot.torques.tolist(),
                "robot_constraint_force": world.data.qfrc_constraint[controller.qvel_index].tolist(),
                "robot_contacts": robot_contacts,
                "observable_timer_s": obs._time_since_last_sample, "observable_sampled": obs._sampled}


class ControlTrace:
    """Observe existing calls, preserving their order and return values."""
    def __init__(self, backend, telemetry):
        self.backend, self.telemetry, self.rows = backend, telemetry, []

    def __enter__(self):
        env = self.backend.world.env
        controller = env.robots[0].controller
        self.original_step, self.original_run = env.step, controller.run_controller
        self.step_override = env.__dict__.get("step")
        self.run_override = controller.__dict__.get("run_controller")
        inner = []

        def run_controller():
            torque = self.original_run()
            low, high = env.robots[0].torque_limits
            inner.append({"torque": np.asarray(torque).copy(),
                          "clip": (np.asarray(torque) < low) | (np.asarray(torque) > high),
                          "position_error_m": float(np.linalg.norm(controller.goal_pos - controller.ee_pos)),
                          "orientation_error_deg": angle_degrees(controller.goal_ori @ controller.ee_ori_mat.T),
                          "speed_mps": float(np.linalg.norm(controller.ee_pos_vel))})
            return torque

        def step(action):
            before = self.telemetry.read()
            inner.clear()
            result = self.original_step(action)
            # world.obs is normally assigned by the caller, not env.step.
            # The trace's joint-width field therefore remains the preceding
            # cached width. Use probe endpoints / physical pad gap for aperture
            # changes; retain this convention for existing v0.1 raw evidence.
            after = self.telemetry.read()
            after["tcp_observed_m"] = np.asarray(result[0]["robot0_eef_pos"]).tolist()
            torques = np.asarray([r["torque"] for r in inner])
            dynamics = {"physics_steps": len(inner),
                        "clipped_steps_by_joint": np.sum([r["clip"] for r in inner], axis=0).tolist(),
                        "torque_min": torques.min(axis=0).tolist(), "torque_max": torques.max(axis=0).tolist(),
                        "max_position_tracking_error_m": max(r["position_error_m"] for r in inner),
                        "max_orientation_tracking_error_deg": max(r["orientation_error_deg"] for r in inner),
                        "max_speed_mps": max(r["speed_mps"] for r in inner)}
            self.rows.append({"command": np.asarray(action).tolist(), "before": before, "after": after,
                              "inner": dynamics})
            return result

        env.step, controller.run_controller = step, run_controller
        return self

    def __exit__(self, *_):
        env = self.backend.world.env
        for obj, key, override in ((env, "step", self.step_override), (env.robots[0].controller, "run_controller", self.run_override)):
            if override is None:
                obj.__dict__.pop(key, None)
            else:
                setattr(obj, key, override)


def fk_feedback_hold(world, telemetry, grip):
    """Diagnostic STOP only: identical loop/horizon but scratch-FK feedback.

    Both entry position target and per-control feedback use fresh FK. No oracle
    task geometry/effects enter control. This is NOT the native executor.
    """
    target = telemetry.kinematics()[0]
    commands, obstacles, peak = [], set(), 0.
    for _ in range(8):
        action = np.r_[np.clip((target - telemetry.kinematics()[0]) / .05, -1, 1), [0., 0., 0.], grip]
        commands.append(action.copy())
        world.obs, _, _, _ = world.env.step(action)
        features = world.features()
        peak = max(peak, features["obstacle_force_N"])
        obstacles.update((c["hand"], c["other"]) for c in features["contacts"] if c["obstacle"])
        if features["success"]:
            break
    return {"commands": commands, "steps": len(commands), "features": features,
            "peak_obstacle_force_N": peak, "obstacle_pairs_seen": sorted(obstacles)}


def probe_boundary(backend, recorder, physical, labels, *, diagnostics=True):
    from jev_libero.world import Snapshot
    world = backend.world
    telemetry = Telemetry(backend)
    source = Snapshot(world)
    grip, previous_execution = backend._grip_cmd, deepcopy(backend.last_execution)
    source_id = context_id(backend)
    recorder.record("regime_boundary", {"context_id": source_id, "physical": physical,
                    "phases": labels, "telemetry": telemetry.read(), "not_supplied_to_model": True})
    controller = world.env.robots[0].controller
    if controller.interpolator_ori is not None or controller.interpolator_pos is not None:
        raise ValueError("diagnostic currently requires noninterpolated OSC")

    def restore():
        source.restore()
        backend._grip_cmd, backend.last_execution = grip, deepcopy(previous_execution)

    controls = [(c.token, "native", 0, True) for c in shared_atomic_candidates()]
    controls += [("STOP", "native", 1, False)]  # noninstrumented replay checks tracing/restoration
    if diagnostics:
        controls += [("STOP", v, 0, True) for v in VARIANTS[1:]]
    native_stop = None
    for token, variant, repeat, traced in controls:
        restore()
        if context_id(backend) != source_id:
            raise RuntimeError("source controller/integration context restoration mismatch")
        recorder.record("regime_probe_started", {"context_id": source_id, "token": token, "variant": variant,
                         "repeat": repeat, "traced": traced, "not_supplied_to_model": True})
        before, features_before = telemetry.read(), world.features()
        original_execute = world.execute
        trace = ControlTrace(backend, telemetry)
        try:
            if variant in ("reanchor_orientation", "both"):
                controller.goal_ori = np.asarray(before["orientation_fk"]).copy()
            if variant in ("fk_feedback", "both"):
                def execute(name, grip=-1., record=False):
                    if name != "hold" or record:
                        raise ValueError("FK diagnostic supports hold only")
                    return fk_feedback_hold(world, telemetry, grip)
                world.execute = execute
            if traced:
                with trace:
                    execution = AtomicExecutor(backend).execute(token)
            else:
                execution = AtomicExecutor(backend).execute(token)
            after, features_after = telemetry.read(), world.features()
            endpoint = world.env.sim.get_state().flatten().tolist()
            endpoint_id = context_id(backend)
            replay_error = None
            if token == "STOP" and variant == "native":
                if repeat == 0:
                    native_stop = (endpoint, endpoint_id)
                else:
                    replay_error = float(np.max(np.abs(np.asarray(endpoint) - native_stop[0])))
                    if endpoint_id != native_stop[1]:
                        raise RuntimeError(f"traced/untraced STOP context differs; sim error={replay_error}")
        except BaseException as exc:
            recorder.record("failure", {"category": "regime_probe_error", "context_id": source_id,
                             "token": token, "variant": variant, "repeat": repeat,
                             "exception": repr(exc), "completed_control_trace": trace.rows})
            raise
        finally:
            world.execute = original_execute
            restore()
        match = context_id(backend) == source_id
        state_error = float(np.max(np.abs(world.env.sim.get_state().flatten() - np.asarray(physical["sim_state"]))))
        recorder.record("regime_probe", {"context_id": source_id, "token": token, "variant": variant,
                         "repeat": repeat, "traced": traced, "before": before, "after": after,
                         "features_before": features_before, "features_after": features_after,
                         "execution": execution, "sim_state_after": endpoint, "endpoint_context_id": endpoint_id,
                         "control_trace": trace.rows, "traced_untraced_replay_max_error": replay_error,
                         "restore": {"context_matches": match, "sim_max_error": state_error},
                         "not_supplied_to_model": True})
        if not match or state_error != 0.:
            raise RuntimeError("probe changed source physical/controller context")


def run(args):
    directory = Path(args.trajectory)
    source_config = json.loads((directory / "config.json").read_text())
    from jev_libero.config import load_task
    installed = load_task("top_drawer")
    recorded = json.loads((directory / "task_config.json").read_text())
    migrated = {**recorded, "measurements": recorded.get("measurements", {"joint_position": {"kind": "joint_position"}})}
    if migrated != installed:
        raise ValueError("source task configuration mismatch")
    schedule = {i: args.steps if args.steps is not None else SAMPLE_STEPS[i] for i in args.init_state_ids}
    resolved = {**vars(args), "schedule": schedule, "source_config": source_config,
                "trajectory_sha256": file_hash(directory / "sim_trajectory.npz"), "task_config": installed,
                "purpose": "atomic_operating_regime_diagnostic_not_E0", "oracle": True,
                "variants": VARIANTS, "native_candidates_unchanged": True,
                "probe_semantics": "native first; independent restored STOP interventions; no settling",
                "feedback_intervention": "fresh scratch-FK entry target and feedback; same 8-step max/success stop",
                "snapshot_signature": "integration+controller+robot+gripper+clock+observables+obs+RNG",
                "telemetry": "observed TCP distinct from scratch-FK TCP; scratch forward never mutates world"}
    recorder = RunRecorder(args.output, resolved, {"run_id": Path(args.output).name, "code": code_identity(), "versions": versions()})
    try:
        inventory = initial_state_inventory("top_drawer", args.libero_root, args.config_dir)
        recorder.record("initial_state_inventory", inventory)
        import jev_libero.world
        import libero
        recorder.manifest_update({"repositories": {"jev": repository_identity(package_directory(jev_libero.world)),
                                                   "libero": repository_identity(package_directory(libero))}})
        with np.load(directory / "sim_trajectory.npz") as trajectory:
            for init, samples in schedule.items():
                if not samples or min(samples) < 0 or max(samples) > len(trajectory["actions"]):
                    raise ValueError("invalid control boundary selection")
                backend = None
                try:
                    backend = LiberoWorldBackend.from_task("top_drawer", seed=source_config["seed"], init_state_id=init,
                                libero_root=args.libero_root, config_dir=args.config_dir, render=False)
                    unit = {"task": "top_drawer", "init_state_id": init, "seed": source_config["seed"],
                            "benchmark_state_id": inventory["state_ids"][init], "trajectory_sha256": resolved["trajectory_sha256"]}
                    previous = None
                    for step in range(max(samples) + 1):
                        physical = physical_evidence(backend, unit, step)
                        if init == source_config["initial_state"]:
                            expected = trajectory["states_before"][step] if step < len(trajectory["actions"]) else trajectory["final_state"]
                            error = float(np.max(np.abs(np.asarray(physical["sim_state"]) - expected)))
                            if error > 1e-8:
                                raise RuntimeError(f"archive mismatch {step}: {error}")
                        labels = phases(physical["features"], previous)
                        if physical["features"]["remaining_open_mm"] <= 40 and not physical["features"]["success"]:
                            labels.append("late")  # descriptive only, does not assert near-completion
                        recorder.record("collection_state", {**physical, "phases": labels})
                        if step in samples:
                            probe_boundary(backend, recorder, physical, labels)
                        previous = physical["features"]
                        if step == max(samples):
                            break
                        action = trajectory["actions"][step]
                        recorder.record("collection_control_started", {**unit, "environment_step": step, "control": action})
                        backend.world.obs, _, _, _ = backend.world.env.step(action)
                        backend._grip_cmd = float(action[-1])
                    recorder.record("initial_state_termination", {**unit, "sampled_boundaries": len(samples),
                                     "final_features": backend.world.features()})
                finally:
                    if backend:
                        backend.close()
        recorder.record("termination", {"reason": "operating_regime_complete", "model_calls": 0})
    except BaseException as exc:
        recorder.record("failure", {"category": "operating_regime_error", "exception": repr(exc)})
        raise
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--init-state-ids", type=int, nargs="+", choices=(0, 1, 2), default=[0, 1, 2])
    parser.add_argument("--steps", type=int, nargs="+", help="explicit bounded override, shared by selected resets")
    parser.add_argument("--libero-root", required=True)
    parser.add_argument("--config-dir", required=True)
    args = parser.parse_args()
    if len(set(args.init_state_ids)) != len(args.init_state_ids) or (args.steps is not None and len(set(args.steps)) != len(args.steps)):
        parser.error("duplicate initial-state IDs or boundaries")
    run(args)


if __name__ == "__main__":
    main()
