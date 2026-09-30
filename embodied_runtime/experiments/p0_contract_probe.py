"""Synthetic P0 protocol/control evidence. No model weights or simulator.

Run: python -m embodied_runtime.experiments.p0_contract_probe --output runs/p0/NAME
The output must not already exist. Neither movement nor outcome in this fixture
is evidence of robotic competence; the deliberately fake selector is labeled.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from functools import partial
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

from ..contracts import BrainIntent, Envelope, canonical_json, content_hash, load_config, thaw
from ..control.action_catalog import ACTION_IDS
from ..control.action_contracts import EefPose, LayaRequest, ValidationContext, _rotate_base
from ..control.local_candidates import ContextIdentity, HardEvidence, build_candidate_set
from ..control.scheduler import Scheduler
from ..router import MessageRouter
from ..sensor_api import Proprioception, SensorPort
from ..state_store import PerceptionStateStore
from ..workers import LatestWorker


class SyntheticRobot:
    """Exact kinematic fixture, not a physical controller or grasp model."""
    def __init__(self):
        self.position = (0., 0., 0.)
        self.quaternion = (0., 0., 0., 1.)
        self.grip = "OPEN"
        self.width = .08
        self.sim_time_s, self.monotonic_ns = 0., 0
        self.commands = []
        self.holds = 0
        self.closed = False

    def read_proprioception(self):
        return Proprioception(self.sim_time_s, self.monotonic_ns, self.position,
                              self.quaternion, (0.,)*7, self.width, True, ("synthetic/robot",),
                              gripper_width_calibration_id="synthetic/calibration",
                              gripper_command=self.grip)

    def command_tick(self, delta_position_m, delta_rotation_rad, gripper_command, duration_s):
        self.commands.append(dict(delta_position_m=delta_position_m, delta_rotation_rad=delta_rotation_rad,
                                  gripper_command=gripper_command, duration_s=duration_s,
                                  sim_time_s=self.sim_time_s, monotonic_ns=self.monotonic_ns))
        self.position = tuple(a+b for a,b in zip(self.position, delta_position_m))
        self.quaternion = _rotate_base(self.quaternion, delta_rotation_rad)
        if gripper_command != "KEEP":
            self.grip = gripper_command
            self.width = .08 if gripper_command == "OPEN" else 0.
        self.sim_time_s += duration_s
        self.monotonic_ns += round(duration_s*1e9)

    def hold(self):
        self.holds += 1

    def close(self):
        self.closed = True


class SyntheticRig:
    """Wire-ingress geometry -> existing fusion -> bounded decision -> fake servo."""
    def __init__(self, *, config=None, sink=None, episode_id="p0", real_clock=False):
        self.config = config or load_config("configs/p0_runtime.json")
        self.sink = sink
        self.events = []
        self.identity = ContextIdentity(episode_id, 1, 1, "none", 0, "front", 1, "patch", 1, ("cal1",))
        self.robot = SyntheticRobot()
        self.store = PerceptionStateStore(episode_id, history_s=self.config["image_history_s"])
        self.store.register_track("front", 1, "patch", 1, {"camera": "cal1"})
        self.seq = 0
        self.snapshots = []
        self.geometry_valid = True
        self.semantics_unchanged = True
        self.statuses = dict.fromkeys(ACTION_IDS, "ALLOWED")
        self.router = MessageRouter(episode_id, 1, 1, "synthetic/clock", sink=self._receipt)
        self.router.register_handler("GeometryObservation", lambda e: self.store.ingest_geometry(e.payload),
                                     validator=lambda p: None)  # Store validates before ingestion.
        self.router.register_handler("PerceptionSnapshot", lambda e: None, validator=lambda p: None)
        self.router.register_handler("LayaRequest", lambda e: None, validator=lambda p: None)
        port = SensorPort(read=self.robot.read_proprioception, command=self.robot.command_tick,
                          hold=self.robot.hold, close=self.robot.close)
        self.scheduler = Scheduler(port, initial_identity=self.identity, latest_context=self.latest,
                                   config=self.config, constraint_templates=("fixture/constraint",),
                                   completion_templates=("fixture/completion",), operations=("push",),
                                   policy_config_revision="p0-fixture-v1", clock_domain=self.router.clock_domain,
                                   sink=self.emit, monotonic_clock=time.monotonic_ns if real_clock else None)
        self.router.register_handler("ActionProposal", self._wire_reply, validator=lambda p: None)
        self.emit("case_configuration", self.config)
        self.at(0., 0)

    def emit(self, kind, payload):
        event = {"kind": kind, "payload": thaw(payload)}
        self.events.append(event)
        if self.sink:
            self.sink(event)

    def _receipt(self, envelope, receipt):
        self.emit("ingress", {"envelope": thaw(envelope), "receipt": thaw(receipt)})

    def at(self, sim_time_s, monotonic_ns, *, refresh=True):
        self.robot.sim_time_s, self.robot.monotonic_ns = sim_time_s, monotonic_ns
        self.store.advance_to(sim_time_s)
        if refresh:
            self.seq += 1
            frame = f"{self.identity.episode_id}/synthetic/frame/{self.seq}"
            self.store.register_frame(frame, "camera", self.seq, "cal1", sim_time_s)
            self.router.register_frame(frame, camera_id="camera", frame_seq=self.seq, calibration_version="cal1",
                                       capture_sim_time_s=sim_time_s, frame_ref=f"events.jsonl#{frame}")
            self.emit("synthetic_frame", {"frame_id":frame, "camera_id":"camera", "frame_seq":self.seq,
                                           "calibration_version":"cal1", "capture_sim_time_s":sim_time_s,
                                           "capture_monotonic_ns":monotonic_ns,
                                           "condition":"synthetic_geometry_fixture_no_image"})
            covariance = [[1e-4,0.,0.],[0.,1e-4,0.],[0.,0.,1e-4]]
            geometry = dict(track_id="front", track_generation=1, feature_id="patch", feature_generation=1,
                            source_frame_ids=[frame], camera_calibration_ids={"camera":"cal1"},
                            capture_sim_time_s=sim_time_s, frame="robot_base", position_m=[.1,0.,0.],
                            position_covariance_m2=covariance, normal_unit=[-1.,0.,0.],
                            normal_covariance=covariance, visible_patch_ref=frame,
                            edge_margin_m=.03, plane_residual_m=.001, support_ratio=.9,
                            status="TRACKED", reason_codes=[])
            envelope = Envelope("GeometryObservation", f"{self.identity.episode_id}/geometry/{self.seq}", "synthetic_geometry", self.seq,
                                self.identity.episode_id, 1, self.router.goal_generation, "synthetic/clock", sim_time_s,
                                monotonic_ns, (frame,), geometry)
            receipt = self.router.receive(envelope, monotonic_ns)
            if receipt.status != "ACCEPTED":
                raise RuntimeError(canonical_json(receipt))
        snapshot = self.store.publish_snapshot(proprio=self.robot.read_proprioception().to_dict(),
                                                safety_state={"valid":True,"reason":"SYNTHETIC_FIXTURE"})
        self.snapshots.append(snapshot["snapshot_id"])
        self.emit("snapshot", snapshot)
        if snapshot["snapshot_id"] not in self.router.seen:
            envelope = Envelope("PerceptionSnapshot", snapshot["snapshot_id"], "fusion", len(self.snapshots),
                                self.identity.episode_id, 1, self.router.goal_generation, "synthetic/clock", sim_time_s,
                                monotonic_ns, (), snapshot)
            self.router.receive(envelope, monotonic_ns)

    def latest(self, sim_time_s, monotonic_ns):
        snapshot = self.store.read_snapshot()
        capture = snapshot["tracks"][0]["last_geometry_capture_sim_time_s"]
        contact = self.scheduler.intent is not None and self.scheduler.intent.stage == "INTERACT"
        cap = self.config["contact_geometry_age_s" if contact else "free_geometry_age_s"]
        age = sim_time_s-capture if capture is not None else float("inf")
        sample = self.robot.read_proprioception()
        return ValidationContext(self.identity, snapshot["snapshot_id"], tuple(self.snapshots),
                                 self.geometry_valid and 0 <= age <= cap, sample.valid,
                                 self.semantics_unchanged, self.statuses,
                                 EefPose(sample.eef_position_base_m, sample.eef_quaternion_xyzw))

    def install_intent(self, stage="APPROACH"):
        source = self.store.read_snapshot()["snapshot_id"]
        s = self.scheduler
        deadline = s.now_ns + int(self.config["brain_request_ttl_s"]*1e9)
        request_id = f"brain/{s.identity.intent_generation+1}"
        s.register_brain_request(request_id, source_snapshot_id=source, deadline_monotonic_ns=deadline)
        intent = BrainIntent(f"intent/{s.identity.intent_generation+1}", s.identity.intent_generation+1,
                             source, "front", 1, "patch", 1, stage, "push", "fixture/constraint",
                             "fixture/completion", "p0-fixture-v1", deadline, 30.)
        if not s.install_intent(intent, request_id=request_id):
            raise RuntimeError(canonical_json(s.rejections[-1]))

    def request(self, request_id="request/1"):
        s = self.scheduler
        source = self.store.read_snapshot()["snapshot_id"]
        evidence = HardEvidence("ALLOWED", ("HARD_CONSTRAINTS_SATISFIED",), (source,), "synthetic")
        deadline = s.now_ns+int(self.config["proposal_ttl_s"]*1e9)
        pool = build_candidate_set(candidate_set_id=f"pool/{request_id}", identity=s.identity,
                                   source_snapshot_id=source,
                                   hard_evidence=dict.fromkeys(ACTION_IDS, evidence),
                                   generated_monotonic_ns=s.now_ns, proposal_deadline_monotonic_ns=deadline)
        request = LayaRequest(request_id, pool, deadline, {"relative_error":[.1,0.,0.], "geometry_age":0.})
        observation = s.register_request(request)
        return request, {"request_id":request_id, "model_input":observation.to_dict(),
                         "identity":asdict(s.identity)}

    def wire_request(self, request_id="request/1"):
        request, internal = self.request(request_id)
        s = self.scheduler
        envelope = Envelope("LayaRequest", request_id, "scheduler", len(s.requests),
                            s.identity.episode_id, s.identity.episode_generation, s.identity.goal_generation,
                            self.router.clock_domain, s.now_sim, s.now_ns,
                            (request.candidate_set.source_snapshot_id,), internal["model_input"])
        receipt = self.router.receive(envelope, s.now_ns)
        if receipt.status != "ACCEPTED":
            raise RuntimeError(canonical_json(receipt))
        expected = {key:internal["model_input"][key] for key in (
            "candidate_set_id", "candidate_hash", "source_snapshot_id", "intent_id", "intent_generation",
            "target_track_id", "target_track_generation", "feature_id", "feature_generation")}
        self.router.register_request(request_id, message_type="ActionProposal",
                                     deadline_monotonic_ns=request.deadline_monotonic_ns,
                                     expected=expected, source_ids=(request.candidate_set.source_snapshot_id,))
        return request, thaw(envelope)

    def _wire_reply(self, envelope):
        return self.scheduler.receive_model_result({"request_id":envelope.payload["request_id"],
                                                     "output":thaw(envelope), "error":None})

    def receive_wire_result(self, result):
        if result["error"] is not None:
            return self.scheduler.receive_model_result(result)
        receipt = self.router.receive(result["output"], self.scheduler.now_ns)
        if receipt.rejection:
            self.scheduler.rejections.append(receipt.rejection)
        return receipt.status == "ACCEPTED"

    def tick(self, sim_time_s, monotonic_ns, *, refresh=True):
        self.at(sim_time_s, monotonic_ns, refresh=refresh)
        return self.scheduler.tick(sim_time_s=sim_time_s, monotonic_ns=monotonic_ns)


def fake_choose(request, *, delay_s=0., action_id="X+40"):
    time.sleep(delay_s)
    model = request["model_input"]
    allowed = [c["id"] for c in model["candidates"] if c["execution_status"] == "ALLOWED"]
    return dict(request_id=request["request_id"], decision_id=f"decision/{request['request_id']}",
                candidate_set_id=model["candidate_set_id"], candidate_hash=model["candidate_hash"],
                identity=request["identity"], source_snapshot_id=model["source_snapshot_id"],
                selected_action_id=action_id, probabilities_by_action={a:float(a==action_id) for a in allowed},
                model_revision="synthetic-fixed-selector-v1", inference_ms=delay_s*1000,
                raw_confidence=None, calibrated_confidence=None)


def fake_choose_wire(request, *, delay_s=0., action_id="X+40", real_clock=False):
    env = Envelope.from_mapping(request)
    time.sleep(delay_s)
    p = env.payload
    allowed = [c["id"] for c in p["candidates"] if c["execution_status"] == "ALLOWED"]
    reply = {key:p[key] for key in ("request_id", "candidate_set_id", "candidate_hash", "source_snapshot_id",
                                   "intent_id", "intent_generation", "target_track_id", "target_track_generation",
                                   "feature_id", "feature_generation")}
    reply.update(decision_id=f"decision/{p['request_id']}", selected_action_id=action_id,
                 probabilities_by_action={a:float(a==action_id) for a in allowed},
                 model_revision="synthetic-fixed-selector-v1", inference_ms=delay_s*1000,
                 raw_confidence=None, calibrated_confidence=None)
    emitted = time.monotonic_ns() if real_clock else env.emitted_monotonic_ns+round(delay_s*1e9)
    return Envelope("ActionProposal", reply["decision_id"], "fake_laya", env.producer_seq,
                    env.episode_id, env.episode_generation, env.goal_generation, env.clock_domain,
                    env.reference_sim_time_s, emitted, (env.message_id,), reply)


def probe_virtual(config, sink=None):
    summaries, events = [], []
    for name, ttl in (("late_valid", 3.), ("late_expired", config["proposal_ttl_s"])):
        rig = SyntheticRig(config={**config, "proposal_ttl_s":ttl}, episode_id=f"p0/{name}",
                           sink=(lambda event: sink({"case":name, **event})) if sink else None)
        rig.install_intent()
        _, payload = rig.wire_request(f"{name}/request")
        # Virtual two-second inference; geometry/control keep progressing at 20Hz.
        for i in range(41):
            rig.tick(i/20, i*50_000_000)
        output = fake_choose_wire(payload)
        output = replace(output, emitted_monotonic_ns=2_000_000_000,
                         payload={**output.payload, "inference_ms":2000.})
        accepted = rig.receive_wire_result(dict(request_id=payload["payload"]["request_id"], output=output, error=None))
        rig.tick(2., 2_000_000_000)
        rig.tick(2.05, 2_050_000_000)
        summary = dict(case=name, proposal_ttl_s=ttl, synthetic=True, accepted=accepted,
                       commands=len(rig.robot.commands), position_m=rig.robot.position,
                       rejections=[r.reason_code for r in rig.scheduler.rejections],
                       feedback=thaw(rig.scheduler.servo.feedback))
        rig.scheduler.close()
        summaries.append(summary)
        events.extend({"case":name, **e} for e in rig.events)
    return summaries, events


def probe_wall(config, sink=None):
    rig = SyntheticRig(config={**config, "proposal_ttl_s":10., "brain_request_ttl_s":15.}, episode_id="p0/wall", real_clock=True,
                       sink=(lambda event: sink({"case":"real_wall_fake_worker", **event})) if sink else None)
    start = time.monotonic_ns()
    rig.tick(0., start)
    rig.install_intent()
    _, payload = rig.wire_request("wall/request")
    worker = LatestWorker(partial(fake_choose_wire, delay_s=2., real_clock=True))
    rig.scheduler.workers.append(worker)
    worker.submit(payload)
    times, output = [], None
    try:
        while output is None:
            now = time.monotonic_ns()
            if now-start > 8_000_000_000:
                raise RuntimeError("synthetic worker failed to return within 8s")
            t = (now-start)/1e9
            rig.tick(t, now)
            times.append(now)
            output = worker.poll()
            if output is None:
                time.sleep(.05)
        # Receipt time is the actual delivery clock, not the preceding servo tick.
        rig.scheduler.now_ns = time.monotonic_ns()
        accepted = rig.receive_wire_result(output)
        now = time.monotonic_ns()
        rig.tick((now-start)/1e9, now)
        time.sleep(.05)
        now = time.monotonic_ns()
        rig.tick((now-start)/1e9, now)
        summary = dict(case="real_wall_fake_worker", synthetic=True, accepted=accepted,
                       deliberately_configured_proposal_ttl_s=10.,
                       ticks_while_pending=len(times), max_tick_gap_s=max((b-a)/1e9 for a,b in zip(times,times[1:])),
                       mean_tick_hz=(len(times)-1)/((times[-1]-times[0])/1e9),
                       commands=len(rig.robot.commands), worker_completed=worker.completed,
                       feedback=thaw(rig.scheduler.servo.feedback))
    finally:
        shutdown = rig.scheduler.close()
    summary["shutdown"] = shutdown
    return summary, [{"case":"real_wall_fake_worker", **e} for e in rig.events]


def probe_interrupts(config, sink=None):
    summaries, events = [], []
    for name in ("cancel_active", "wall_only_expiry", "sim_only_expiry"):
        rig = SyntheticRig(config=config, episode_id=f"p0/{name}",
                           sink=(lambda event: sink({"case":name, **event})) if sink else None)
        rig.install_intent()
        _, payload = rig.wire_request(f"{name}/request")
        output = fake_choose_wire(payload)
        assert rig.receive_wire_result(dict(request_id=payload["payload"]["request_id"], output=output, error=None))
        rig.tick(0.,0)
        if name == "cancel_active":
            rig.scheduler.cancel(event_id="operator/cancel")
            # Resend must not advance generation or revoke an unrelated new intent.
            rig.scheduler.cancel(event_id="operator/cancel")
            rig.scheduler.tick(sim_time_s=.05,monotonic_ns=50_000_000)
        elif name == "wall_only_expiry":
            rig.tick(.05,100_000_000)
        else:
            rig.tick(.1,50_000_000)
        feedback = rig.scheduler.servo.feedback[-1]
        assert len(rig.robot.commands) == 1 and feedback.status == "ABORTED"
        summary = dict(case=name,synthetic=True,commands=len(rig.robot.commands),feedback=thaw(feedback))
        rig.scheduler.close()
        summaries.append(summary)
        events.extend({"case":name,**e} for e in rig.events)
    return summaries, events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/p0_runtime.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(condition="synthetic_p0_no_models_no_simulator", config=thaw(config),
                    config_hash=content_hash(config), python=sys.version,
                    commit=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
                    dirty=bool(subprocess.check_output(["git","status","--porcelain"],text=True)),
                    dependencies={p:importlib.metadata.version(p) for p in ("numpy","pytest","ruff","setuptools")},
                    source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path("embodied_runtime").rglob("*.py")})
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    with (out/"events.jsonl").open("x") as f:
        def append(event):
            f.write(canonical_json(event)+"\n")
            f.flush()
        try:
            summaries, events = probe_virtual(config, append)
            interruptions, interrupt_events = probe_interrupts(config, append)
            summaries.extend(interruptions)
            events.extend(interrupt_events)
            wall, wall_events = probe_wall(config, append)
        except Exception as exc:
            (out/"failure.json").write_text(json.dumps({"exception":repr(exc),"incomplete":True})+"\n")
            raise
    summaries.append(wall)
    events.extend(wall_events)
    frames = [e for e in events if e["kind"] == "synthetic_frame"]
    (out/"synthetic_frames.json").write_text(json.dumps(frames, indent=2)+"\n")
    (out/"summary.json").write_text(json.dumps(summaries, indent=2)+"\n")
    assert summaries[0]["accepted"] and summaries[0]["commands"] == 2
    assert not summaries[1]["accepted"] and summaries[1]["commands"] == 0
    assert wall["accepted"] and wall["ticks_while_pending"] >= 20
    assert all(not s["alive"] for s in wall["shutdown"])
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
