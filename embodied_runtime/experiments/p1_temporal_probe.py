"""Observation-only temporal acquisition and sensor-only replay analysis.

Acquisition is explicitly an evaluation fixture, not a manipulation policy.
Existing World.execute actions/commands are unchanged. A temporary env.step tap
captures after each original control and aborts on robot/environment contact.
Optional continuous scene perturbations are recorded only in evaluator.jsonl.
The analysis command never opens that file or reads simulator/task truth.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from ..contracts import canonical_json, require, thaw
from ..perception.recording import FrameRecorder, replay_frames
from ..perception.relative_verify import RelativeSurfaceVerifier, SurfaceEvidence
from ..perception.rgbd_geometry import GeometryConfig, estimate_visible_patch
from ..perception.visual_tracker import VisualTracker
from ..perception.surface_association import sensor_view_identity
from .p1_rgbd_probe import identity


CASES = {f"T{i:02d}" for i in range(1, 11)}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_config(config):
    required = {"revision", "case_id", "task", "seed", "init_index", "camera_names", "width", "height",
                "operations", "static_evidence_sha256", "max_controls", "description"}
    require(required <= set(config) <= required | {"predeclared_boundary"}, "temporal acquisition config fields")
    if "predeclared_boundary" in config:
        boundary = config["predeclared_boundary"]
        require(set(boundary) == {"status", "reason_codes"}
                and boundary["status"] == "ACQUISITION_UNSUPPORTED"
                and isinstance(boundary["reason_codes"], list) and bool(boundary["reason_codes"])
                and all(isinstance(reason, str) and reason for reason in boundary["reason_codes"]),
                "explicit unsupported acquisition boundary")
        require(all(op.get("primitive") == "hold" and op.get("fixture") is None for op in config["operations"]),
                "unsupported case may only capture fresh contact-guarded HOLD observations")
    require(config["case_id"] in CASES and config["task"] == "top_drawer", "declared temporal task/case")
    require(type(config["seed"]) is int and type(config["init_index"]) is int and config["init_index"] >= 0,
            "seed and benchmark init")
    require(config["camera_names"] == ["agentview", "robot0_eye_in_hand"], "same-exposure dual RGB-D required")
    for name in ("width", "height", "max_controls"):
        require(type(config[name]) is int and config[name] > 0, name)
    require(config["operations"] and {op["phase"] for op in config["operations"]} == {"pre", "boundary", "post"},
            "pre/boundary/post observation operations required")
    phases = {"pre": 0, "boundary": 1, "post": 2}
    order = [phases[op["phase"]] for op in config["operations"]]
    require(order == sorted(order), "phase order")
    translations = {f"{axis}{amount:+d}mm" for axis in "xyz" for amount in (-40, -10, -3, 3, 10, 40)}
    rotations = {f"rotate_{axis}{amount:+d}deg" for axis in "xyz" for amount in (-10, 10)}
    # Explicit observation-only allowlist; no gripper opening/grasping action.
    for op in config["operations"]:
        require(set(op) <= {"phase", "primitive", "fixture"} and set(op) >= {"phase", "primitive"}, "operation fields")
        require(op["primitive"] in translations | rotations | {"hold"}, "existing observation primitive only")
        if op.get("fixture") is not None:
            f = op["fixture"]
            require(op["primitive"] == "hold", "scene fixture cannot combine with robot motion")
            require(f.get("kind") in {"slide_joint_offset", "body_translation"}, "fixture kind")
            required_fixture = {"kind", "name", "delta", "ramp_controls"}
            require(set(f) == required_fixture and isinstance(f["name"], str) and f["name"], "fixture fields")
            require(type(f["ramp_controls"]) is int and 1 <= f["ramp_controls"] <= 8, "one-primitive fixture ramp")
            delta = np.asarray(f["delta"], dtype=float)
            require(delta.shape == (() if f["kind"] == "slide_joint_offset" else (3,))
                    and np.isfinite(delta).all(), "fixture delta shape/finite")
    require(len(config["operations"])*8 <= config["max_controls"], "declared control budget")
    require(isinstance(config["static_evidence_sha256"], str) and len(config["static_evidence_sha256"]) == 64,
            "static evidence digest")
    return config


class AcquisitionStop(RuntimeError):
    pass


class StepCaptureTap:
    """Experiment-local observer; original env.step receives identical commands.

    Not installed into the reusable runtime. Contact guard and fixture callbacks
    are evaluator capabilities; capture receives no contact/fixture truth.
    """
    def __init__(self, world, *, capture, inspect_contacts, journal, max_controls, clock_ns=time.monotonic_ns):
        self.world, self.capture, self.inspect_contacts, self.journal = world, capture, inspect_contacts, journal
        self.max_controls, self.clock_ns = max_controls, clock_ns
        self.controls = 0
        self.operation_index = None
        self.operation = None
        self.before_control = None

    def __enter__(self):
        self.original = self.world.env.step
        self.world.env.step = self.step
        return self

    def __exit__(self, *_):
        self.world.env.step = self.original

    def step(self, command):
        require(self.controls < self.max_controls, "temporal control budget", "CONTROL_BUDGET")
        contacts = self.inspect_contacts()
        if contacts:
            self.journal({"kind": "contact_boundary", "when": "before_control", "contacts": contacts,
                          "controls_executed": self.controls})
            raise AcquisitionStop("ROBOT_ENVIRONMENT_CONTACT")
        if self.before_control is not None:
            self.before_control()
        # Fixture perturbation must also be contact-free before the next step.
        contacts = self.inspect_contacts()
        if contacts:
            self.capture()
            self.journal({"kind": "contact_boundary", "when": "after_fixture_before_control", "contacts": contacts,
                          "controls_executed": self.controls})
            raise AcquisitionStop("FIXTURE_ROBOT_CONTACT")
        values = np.asarray(command, dtype=float)
        require(values.shape == (7,) and np.isfinite(values).all(), "original control command")
        self.journal({"kind": "original_control_started", "control_index": self.controls,
                      "operation_index": self.operation_index, "operation": self.operation,
                      "command": values.tolist(), "monotonic_ns": self.clock_ns()})
        returned = self.original(command)
        self.controls += 1
        contacts = self.inspect_contacts()
        # Persist the first failure frame before aborting; never continue to the
        # next control after detecting contact at this control boundary.
        receipt = self.capture()
        self.journal({"kind": "original_control_completed", "control_index": self.controls-1,
                      "bundle_message_id": receipt.message_id, "contacts": contacts,
                      "monotonic_ns": self.clock_ns()})
        if contacts:
            raise AcquisitionStop("ROBOT_ENVIRONMENT_CONTACT")
        return returned


def robot_contact_inspector(world):
    """Evaluator-only all-robot contact attribution, never perception input."""
    robot = world.env.env.robots[0]
    names = (*robot.robot_model.contact_geoms, *robot.gripper.contact_geoms)
    ids = {world.env.sim.model.geom_name2id(name) for name in names}
    require(ids, "robot collision geometry mapping required")

    def inspect():
        contacts = []
        for i in range(world.data.ncon):
            c = world.data.contact[i]
            a, b = int(c.geom1), int(c.geom2)
            if (a in ids) != (b in ids) and c.dist <= 0:
                contacts.append({"geom1": a, "geom2": b, "distance_m": float(c.dist),
                                 "source": "evaluator_simulator_contact"})
        return contacts
    return inspect


class SceneFixture:
    """Explicit evaluator-only scene transform ramp, never an executable skill."""
    def __init__(self, world, config, journal):
        self.world, self.config, self.journal, self.step_index = world, config, journal, 0
        model, data = world.model, world.data
        robot = world.env.env.robots[0]
        robot_root = world.env.sim.model.body_name2id(robot.robot_model.root_body)

        def descendant(body, ancestor):
            while body:
                if body == ancestor:
                    return True
                body = int(model.body_parentid[body])
            return False

        if config["kind"] == "slide_joint_offset":
            jid = world.env.sim.model.joint_name2id(config["name"])
            require(jid >= 0 and int(model.jnt_type[jid]) == int(world.mujoco.mjtJoint.mjJNT_SLIDE), "fixture slide joint")
            body = int(model.jnt_bodyid[jid])
            require(not descendant(body, robot_root), "fixture cannot change robot joints")
            require(not any(descendant(int(camera_body), body) for camera_body in model.cam_bodyid),
                    "fixture cannot change camera attachment")
            self.kind, self.index = "slide_joint", int(model.jnt_qposadr[jid])
            self.dof = int(model.jnt_dofadr[jid])
            self.initial = float(data.qpos[self.index])
            target = self.initial+config["delta"]
            require(not model.jnt_limited[jid] or model.jnt_range[jid, 0] <= target <= model.jnt_range[jid, 1],
                    "fixture joint target out of range")
        else:
            body = world.env.sim.model.body_name2id(config["name"])
            require(body > 0 and not descendant(body, robot_root), "fixture cannot move robot/world")
            require(not any(descendant(int(camera_body), body) for camera_body in model.cam_bodyid),
                    "fixture cannot change camera attachment")
            joints = range(int(model.body_jntadr[body]), int(model.body_jntadr[body]+model.body_jntnum[body]))
            joints = list(joints)
            if joints:
                require(len(joints) == 1 and int(model.jnt_type[joints[0]]) == int(world.mujoco.mjtJoint.mjJNT_FREE),
                        "body fixture requires fixed or free root")
                self.kind, self.index = "free_body", int(model.jnt_qposadr[joints[0]])
                self.dof = int(model.jnt_dofadr[joints[0]])
                self.initial = np.array(data.qpos[self.index:self.index+3], copy=True)
            else:
                self.kind, self.index = "fixed_body", body
                self.initial = np.array(model.body_pos[body], copy=True)

    def advance(self):
        self.step_index += 1
        fraction = min(1., self.step_index/self.config["ramp_controls"])
        target = self.initial+fraction*np.asarray(self.config["delta"])
        data, model = self.world.data, self.world.model
        if self.kind == "slide_joint":
            data.qpos[self.index], data.qvel[self.dof] = float(target), 0.
        elif self.kind == "free_body":
            data.qpos[self.index:self.index+3] = target
            data.qvel[self.dof:self.dof+6] = 0.
        else:
            model.body_pos[self.index] = target
        self.world.env.sim.forward()
        self.journal({"kind": "scene_fixture_applied", "provenance": "evaluator_only", "fixture": self.config,
                      "storage_kind": self.kind, "ramp_step": self.step_index, "fraction": fraction,
                      "delta_frame": "joint_coordinate" if self.kind == "slide_joint" else
                                     "world" if self.kind == "free_body" else "body_parent",
                      "actual_assignment": np.asarray(target).tolist(), "sim_time_s": float(data.time),
                      "robot_manipulation": False, "perception_input": False})


def acquire(config, output, *, static_evidence, capture_observer=None, observer_identity=None):
    config = validate_config(config)
    require(file_hash(static_evidence) == config["static_evidence_sha256"], "static evidence revision mismatch")
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    (out/"manifest.json").write_text(canonical_json({"code": identity(), "config": config,
        "condition": "observation_only_temporal_evaluation_fixture", "static_evidence": str(static_evidence),
        "reset_count": 1, "standard_reset_controls": 10, "qwen_calls": 0, "laya_calls": 0,
        "new_executor": False, "contact_checks": "evaluator_only_each_existing_control_boundary",
        "contact_substep_guarantee": False, "capture_observer_identity": observer_identity,
        "acquisition_does_not_certify_case_coverage": True})+"\n")
    from ..adapters.libero import LiberoWorldBackend
    from ..adapters.libero_sensor_env import LiberoSensorEnv
    backend = sensor = None
    summary = {"case_id": config["case_id"], "status": "INCOMPLETE", "case_coverage_validated": False,
               "visual_inspection_required": True, "official_success_evaluated": False}
    try:
        backend = LiberoWorldBackend.from_task(config["task"], seed=config["seed"], init_state_id=config["init_index"], render=True)
        sensor = LiberoSensorEnv(backend.world, camera_names=config["camera_names"], width=config["width"], height=config["height"],
                                retained_gripper_command=lambda: "OPEN" if backend.gripper_command() < 0 else "CLOSE")
        with FrameRecorder(out/"frames", episode_id=f"p1-temporal/{config['case_id']}", clock_domain="live-local-process",
                           condition="temporal_scene_fixture_not_robot_skill") as recorder, (out/"evaluator.jsonl").open("x") as log:
            def journal(row):
                log.write(canonical_json(row)+"\n")
                log.flush()

            def capture():
                bundle = sensor.sensor_port().capture()
                receipt = recorder.append(bundle["views"], bundle["proprio"], emitted_monotonic_ns=time.monotonic_ns())
                if capture_observer is not None:
                    # Optional experiment-only semantic worker gets sensor data,
                    # never the simulator, fixture journal or contact evidence.
                    capture_observer(receipt, bundle)
                return receipt

            capture()
            with StepCaptureTap(backend.world, capture=capture, inspect_contacts=robot_contact_inspector(backend.world),
                                journal=journal, max_controls=config["max_controls"]) as tap:
                try:
                    for index, operation in enumerate(config["operations"]):
                        tap.operation_index, tap.operation = index, operation
                        fixture = SceneFixture(backend.world, operation["fixture"], journal) if operation.get("fixture") else None
                        tap.before_control = fixture.advance if fixture else None
                        before = tap.controls
                        result = backend.world.execute(operation["primitive"], grip=backend.gripper_command(), record=False)
                        journal({"kind": "primitive_completed", "operation_index": index, "operation": operation,
                                 "actual_controls": tap.controls-before, "original_executor_steps": result["steps"]})
                        if tap.controls-before != 8:
                            raise AcquisitionStop("EXISTING_EXECUTOR_EARLY_RETURN")
                    if config.get("predeclared_boundary"):
                        summary.update(status="ACQUISITION_UNSUPPORTED",
                            first_boundary=";".join(config["predeclared_boundary"]["reason_codes"]),
                            unsupported_reason_codes=config["predeclared_boundary"]["reason_codes"],
                            intended_event_occurred=False)
                    else:
                        summary["status"] = "ACQUIRED_UNINSPECTED"
                except AcquisitionStop as exc:
                    summary.update(status="STOPPED_BOUNDARY", first_boundary=str(exc))
                finally:
                    summary["executed_controls"] = tap.controls
                    summary["captured_bundles"] = recorder.seq
    except Exception as exc:
        summary.update(status="RUNTIME_FAILURE", first_boundary=repr(exc))
        raise
    finally:
        if sensor is not None:
            sensor.close()
        if backend is not None:
            backend.world.close()
        (out/"acquisition-summary.json").write_text(canonical_json(summary)+"\n")
    return summary


def surface_from_track(track, patch, env):
    valid = track.status == "TRACKED" and patch is not None and patch.geometry_status == "VALID"
    return SurfaceEvidence(env.episode_id, env.episode_generation, env.goal_generation,
        f"geometry/{track.frame_id}/{track.track_id}", f"{env.message_id}/{track.camera_id}", track.track_id,
        track.track_generation, track.feature_id, track.feature_generation,
        f"{env.episode_id}/{track.track_id}/{track.track_generation}/{track.feature_generation}", track.camera_id,
        track.calibration_version, (track.frame_id,), track.capture_sim_time_s, track.capture_monotonic_ns,
        "TRACKED" if valid else track.status if track.status != "TRACKED" else "UNKNOWN",
        patch.centroid_base_m if valid else None, patch.normal_base if valid else None,
        patch.covariance_m2 if valid else None, patch.normal_covariance if valid else None,
        patch.metrics["covariance_model_id"] if patch is not None else "no_geometry")


def analyze(recording, seeds, output, *, geometry_config=None):
    """Read sensor-only artifacts. Never consume evaluator perturbation logs.

    This is capture-clock association analysis. Original wall capture gaps remain
    effective; it is not online throughput/freshness evidence. Source-bound seeds
    can explicitly reseed after loss, but no recovery is invented here.
    """
    geometry_config = geometry_config or GeometryConfig()
    require(seeds.get("condition") in {"real_model_seed", "declared_diagnostic_seed", "sensor_geometry_seed"}, "seed condition")
    require(set(seeds) == {"condition", "recording_frames_sha256", "seeds"}, "seed file fields")
    require(file_hash(Path(recording)/"frames.jsonl") == seeds["recording_frames_sha256"], "seed recording mismatch")
    indexed = {}
    for seed in seeds["seeds"]:
        require(set(seed) == {"camera_id", "role", "source_frame_id", "roi_xyxy_px", "query", "artifact_uri", "artifact_sha256"},
                "source-bound seed fields")
        require(seed["role"] in {"face", "reference"}, "independent surface role")
        require(isinstance(seed["artifact_uri"], str) and seed["artifact_uri"] and len(seed["artifact_sha256"]) == 64,
                "seed output source identity")
        artifact = Path(seed["artifact_uri"])
        require(artifact.is_absolute() and artifact.is_file(), "seed artifact must resolve to existing absolute path")
        require(file_hash(artifact) == seed["artifact_sha256"], "seed artifact checksum mismatch")
        bound = json.loads(artifact.read_text())
        for field in ("camera_id", "source_frame_id", "roi_xyxy_px", "query"):
            require(bound.get(field) == seed[field], f"seed artifact {field} mismatch")
        if seeds["condition"] == "real_model_seed":
            require(bound.get("seed_source") == "real_model" and bound.get("evaluation_labels_used") is False,
                    "real-model seed provenance required")
        if seeds["condition"] == "sensor_geometry_seed":
            require(bound.get("seed_source") == "sensor_geometry" and bound.get("evaluation_labels_used") is False,
                    "sensor-geometry seed provenance required", "INFORMATION_BOUNDARY")
            require(bound.get("oracle_inputs") is False and bound.get("for_execution") is False,
                    "sensor-only observational seed required", "INFORMATION_BOUNDARY")
            require(isinstance(bound.get("source_identity"), dict)
                    and isinstance(bound.get("feature_candidate_id"), str) and bound["feature_candidate_id"],
                    "source-bound geometry candidate identity required")
            require(bound.get("association_status") == "BOUND_HYPOTHESIS",
                    "unique geometry hypothesis association required")
            evidence_uri = Path(bound.get("association_evidence_uri", ""))
            require(evidence_uri.is_absolute() and evidence_uri.is_file(), "geometry association evidence required")
            require(file_hash(evidence_uri) == bound.get("association_evidence_sha256"),
                    "geometry association evidence checksum mismatch")
            evidence = json.loads(evidence_uri.read_text())
            require(evidence.get("evaluation_labels_used") is False and evidence.get("oracle_inputs") is False,
                    "geometry association evidence cannot use labels or oracle", "INFORMATION_BOUNDARY")
            require(evidence.get("source_identity") == bound["source_identity"]
                    and evidence.get("feature_candidate_id") == bound["feature_candidate_id"]
                    and evidence.get("roi_xyxy_px") == bound["roi_xyxy_px"]
                    and evidence.get("association_status") == "BOUND_HYPOTHESIS",
                    "geometry association evidence binding mismatch")
        key = seed["camera_id"], seed["role"], seed["source_frame_id"]
        require(key not in indexed, "duplicate seed")
        indexed[key] = seed
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    (out/"manifest.json").write_text(canonical_json({"code": identity(), "seeds": seeds,
        "geometry_config": asdict(geometry_config), "processing_clock": "offline_capture_clock_original_gaps",
        "online_freshness_evaluated": False, "evaluator_truth_read": False,
        "semantic_identity_verified": False, "oracle_inputs": False})+"\n")
    trackers, verifiers, counts, used = {}, {}, Counter(), set()
    bundles = 0
    with (out/"perception.jsonl").open("x") as log:
        for env, views in replay_frames(recording):
            bundles += 1
            for original in views:
                # Recording envelope owns the replay episode. Keep the sensor's
                # original source ID in the unchanged recording identity chain.
                view = dict(original, frame_id=original["canonical_frame_id"], episode_id=env.episode_id)
                camera, surfaces = view["camera_id"], {}
                for role in ("face", "reference"):
                    key = camera, role
                    seed_key = camera, role, view["frame_id"]
                    seed = indexed.get(seed_key)
                    tracker = trackers.get(key)
                    start = time.monotonic_ns()
                    if seed is not None:
                        if seeds["condition"] == "sensor_geometry_seed":
                            bound = json.loads(Path(seed["artifact_uri"]).read_text())
                            require(bound["source_identity"] == sensor_view_identity(view),
                                    "geometry seed sensor source mismatch", "SOURCE_MISMATCH")
                        used.add(seed_key)
                        tracker = tracker or VisualTracker(env.episode_id, track_id=f"{camera}/{role}", feature_id="visible-plane")
                        trackers[key] = tracker
                        track = tracker.initialize(view, seed["roi_xyxy_px"], query=seed["query"],
                            seed_source={"real_model_seed": "semantic_query", "declared_diagnostic_seed": "manual_seed",
                                         "sensor_geometry_seed": "sensor_geometry"}[seeds["condition"]],
                            now_sim_time_s=view["capture_sim_time_s"], now_monotonic_ns=view["capture_monotonic_ns"])
                    elif tracker is None:
                        counts[f"{camera}/{role}/UNSEEDED"] += 1
                        log.write(canonical_json({"kind": "surface_unseeded", "camera_id": camera, "role": role,
                                                  "source_frame_id": view["frame_id"]})+"\n")
                        continue
                    else:
                        track = tracker.update(view, now_sim_time_s=view["capture_sim_time_s"],
                                               now_monotonic_ns=view["capture_monotonic_ns"])
                    tracker_ms = (time.monotonic_ns()-start)/1e6
                    patch = None
                    if track.status == "TRACKED":
                        patch = estimate_visible_patch(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
                            roi_xyxy=track.roi_xyxy_px, source_frame_id=view["frame_id"], calibration_version=view["calibration_version"],
                            track_id=track.track_id, feature_id=track.feature_id, capture_sim_time_s=view["capture_sim_time_s"],
                            capture_monotonic_ns=view["capture_monotonic_ns"], config=geometry_config, seed=0,
                            eef_position_base_m=env.payload["proprio"]["eef_position_base_m"])
                    surfaces[role] = surface_from_track(track, patch, env)
                    counts[f"{camera}/{role}/{track.status}"] += 1
                    row = {"kind": "surface", "camera_id": camera, "role": role, "bundle_id": env.message_id,
                           "source_frame_id": view["frame_id"], "seed_event": seed, "track": thaw(track),
                           "patch": patch.to_dict() if patch is not None else None, "tracker_ms": tracker_ms,
                           "publication_pipeline_ms": (time.monotonic_ns()-start)/1e6}
                    log.write(canonical_json(row)+"\n")
                if set(surfaces) == {"face", "reference"}:
                    verifier = verifiers.setdefault(camera, RelativeSurfaceVerifier())
                    result = verifier.update(surfaces["face"], surfaces["reference"],
                        now_sim_time_s=view["capture_sim_time_s"], now_monotonic_ns=view["capture_monotonic_ns"])
                    log.write(canonical_json({"kind": "verify", "camera_id": camera, "bundle_id": env.message_id,
                                              "evidence": thaw(result)})+"\n")
                log.flush()
    summary = {"bundles": bundles, "track_counts": dict(counts), "unused_seed_keys": [list(k) for k in indexed.keys()-used],
               "case_coverage_validated": False, "visual_inspection_required": True,
               "online_freshness_evaluated": False, "verify_calibrated": False, "official_success_evaluated": False,
               "synthetic_sequence": False, "evaluator_truth_read": False,
               "delayed_semantic_reply_evaluated": False}
    (out/"summary.json").write_text(canonical_json(summary)+"\n")
    return summary


def inspect_sequence(recording, output):
    """Export original RGB samples and clock/pose changes, never certify coverage."""
    from PIL import Image, ImageDraw

    bundles = list(replay_frames(recording))
    require(bool(bundles), "empty temporal recording")
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    chosen = sorted(set(np.linspace(0, len(bundles)-1, min(8, len(bundles)), dtype=int)))
    rows = []
    for camera in [view["camera_id"] for view in bundles[0][1]]:
        views = [next(view for view in bundle if view["camera_id"] == camera) for _, bundle in bundles]
        h, w = views[0]["rgb"].shape[:2]
        sheet = Image.new("RGB", (4*w, 2*(h+36)), "white")
        draw = ImageDraw.Draw(sheet)
        for slot, index in enumerate(chosen):
            view = views[index]
            x, y = slot % 4*w, slot//4*(h+36)
            sheet.paste(Image.fromarray(view["rgb"]), (x,y+36))
            draw.text((x+3,y+2), f'{camera} seq={view["frame_seq"]}\nt={view["capture_sim_time_s"]:.3f}s', fill="black")
        path = out/f"{camera}.png"
        sheet.save(path)
        wall = np.array([view["capture_monotonic_ns"] for view in views],dtype=np.int64)/1e9
        sim = np.array([view["capture_sim_time_s"] for view in views])
        transforms = np.array([view["T_base_camera"] for view in views])
        relative_R = transforms[:, :3, :3] @ transforms[0, :3, :3].T
        angles = np.degrees(np.arccos(np.clip((np.trace(relative_R,axis1=1,axis2=2)-1)/2,-1,1)))
        rows.append(dict(camera_id=camera, frames=len(views), selected_source_frame_ids=[views[i]["canonical_frame_id"] for i in chosen],
                         max_capture_gap_wall_s=float(np.diff(wall).max()) if len(wall)>1 else None,
                         max_capture_gap_sim_s=float(np.diff(sim).max()) if len(sim)>1 else None,
                         max_camera_displacement_m=float(np.linalg.norm(transforms[:,:3,3]-transforms[0,:3,3],axis=1).max()),
                         max_camera_rotation_deg=float(angles.max()),
                         max_mean_rgb_change=float(max(np.abs(view["rgb"].astype(float)-views[0]["rgb"]).mean() for view in views)),
                         image=str(path), image_sha256=file_hash(path)))
    summary = dict(cameras=rows, case_coverage_validated=False, evaluator_truth_read=False,
                   visual_inspection_required=True, frames_sha256=file_hash(Path(recording)/"frames.jsonl"))
    (out/"summary.json").write_text(canonical_json(summary)+"\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    acquisition = commands.add_parser("acquire")
    acquisition.add_argument("--config", required=True)
    acquisition.add_argument("--static-evidence", required=True)
    acquisition.add_argument("--output", required=True)
    analysis = commands.add_parser("analyze")
    analysis.add_argument("--recording", required=True)
    analysis.add_argument("--seeds", required=True)
    analysis.add_argument("--geometry-config", default="configs/p1_geometry.json")
    analysis.add_argument("--output", required=True)
    inspection = commands.add_parser("inspect")
    inspection.add_argument("--recording", required=True)
    inspection.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "acquire":
        result = acquire(json.loads(Path(args.config).read_text()), args.output, static_evidence=args.static_evidence)
    elif args.command == "analyze":
        result = analyze(args.recording, json.loads(Path(args.seeds).read_text()), args.output,
                         geometry_config=GeometryConfig.load(args.geometry_config))
    else:
        result = inspect_sequence(args.recording,args.output)
    print(canonical_json(result))


if __name__ == "__main__":
    main()
