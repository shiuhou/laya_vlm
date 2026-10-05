"""Unit fixtures below are not real temporal-sequence evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments.p1_temporal_probe import (
    AcquisitionStop, SceneFixture, StepCaptureTap, analyze, file_hash, validate_config,
)
from embodied_runtime.perception.recording import FrameRecorder
from embodied_runtime.sensor_api import Proprioception


def config():
    return dict(revision="temporal/1", case_id="T01", task="top_drawer", seed=1, init_index=0,
                camera_names=["agentview", "robot0_eye_in_hand"], width=384, height=384,
                operations=[dict(phase=phase, primitive="hold") for phase in ("pre", "boundary", "post")],
                static_evidence_sha256="0"*64, max_controls=24, description="unit fixture")


@pytest.mark.parametrize("change", [
    lambda c: c["operations"][1].update(primitive="close"),
    lambda c: c.update(max_controls=23),
    lambda c: c.update(operations=c["operations"][::-1]),
    lambda c: c["operations"][1].update(fixture=dict(kind="reset", name="body", delta=1, ramp_controls=8)),
    lambda c: c.update(camera_names=["agentview"]),
    lambda c: c["operations"][1].update(fixture=dict(kind="body_translation", name="body", delta=[float("nan"),0,0], ramp_controls=8)),
])
def test_config_rejects_unsafe_or_mislabeled_operations(change):
    value = config()
    assert validate_config(value) is value
    change(value)
    with pytest.raises(ProtocolError):
        validate_config(value)


def tap_fixture(contacts):
    commands, captures, journal = [], [], []
    returned = ({"unchanged": object()}, 0., False, {})

    def original(command):
        commands.append(command)
        return returned

    def capture():
        captures.append(len(commands))
        return NS(message_id=f"bundle/{len(captures)}")

    world = NS(env=NS(step=original))
    tap = StepCaptureTap(world, capture=capture, inspect_contacts=lambda: next(contacts), journal=journal.append,
                         max_controls=8, clock_ns=lambda: 100)
    return tap, world, commands, captures, journal, returned, original


def test_tap_forwards_exact_command_and_return_objects_and_restores_method():
    tap, world, commands, captures, log, returned, original = tap_fixture(iter([[], [], []]))
    command = np.arange(7.)
    with tap:
        assert world.env.step(command) is returned
    assert world.env.step is original and commands[0] is command
    assert tap.controls == 1 and captures == [1]
    assert [row["kind"] for row in log] == ["original_control_started", "original_control_completed"]


@pytest.mark.parametrize("observations,count,captured", [
    ([[{"contact": 1}]], 0, []),
    ([[], [{"contact": 1}]], 0, [0]),
    ([[], [], [{"contact": 1}]], 1, [1]),
])
def test_contact_stops_at_first_observable_control_boundary(observations, count, captured):
    tap, world, commands, captures, _, _, original = tap_fixture(iter(observations))
    with pytest.raises(AcquisitionStop):
        with tap:
            world.env.step(np.zeros(7))
    assert world.env.step is original
    assert len(commands) == tap.controls == count and captures == captured


def test_original_method_restored_after_fixture_failure():
    tap, world, commands, _, _, _, original = tap_fixture(iter([[]]))

    def fail():
        raise RuntimeError("fixture broke")

    with pytest.raises(RuntimeError, match="fixture broke"):
        with tap:
            tap.before_control = fail
            world.env.step(np.zeros(7))
    assert not commands and world.env.step is original


def fixture_world():
    model = NS(body_parentid=np.array([0,0,0,2,1]), cam_bodyid=np.array([4]),
               jnt_type=np.array([2,2,0]), jnt_bodyid=np.array([3,4,2]), jnt_qposadr=np.array([0,1,2]),
               jnt_dofadr=np.array([0,1,2]), jnt_limited=np.array([1,1,0]),
               jnt_range=np.array([[-.16,.01],[-1,1],[0,0]]),
               body_jntadr=np.array([-1,-1,2,0,1]), body_jntnum=np.array([0,0,1,1,1]),
               body_pos=np.zeros((5,3)))
    native = NS(joint_name2id=lambda name: {"drawer":0,"robot":1}[name],
                body_name2id=lambda name: {"robot_root":1,"cabinet":2,"drawer":3,"camera":4}[name])
    data = NS(qpos=np.array([-.1,0.,0.,0.,0.,1.,0.,0.,0.]), qvel=np.zeros(8), time=1.)
    robot = NS(robot_model=NS(root_body="robot_root"))
    return NS(model=model, data=data, env=NS(env=NS(robots=[robot]), sim=NS(model=native, forward=lambda: None)),
              mujoco=NS(mjtJoint=NS(mjJNT_SLIDE=2,mjJNT_FREE=0)))


def test_fixture_ramp_is_evaluator_only_and_cannot_modify_robot_or_camera():
    world, rows = fixture_world(), []
    recipe = dict(kind="slide_joint_offset",name="drawer",delta=.01,ramp_controls=2)
    fixture = SceneFixture(world,recipe,rows.append)
    fixture.advance()
    assert world.data.qpos[0] == pytest.approx(-.095)
    fixture.advance()
    assert world.data.qpos[0] == pytest.approx(-.09)
    assert all(row["perception_input"] is False and row["delta_frame"] == "joint_coordinate" for row in rows)
    for changes in ({"name":"robot"},{"delta":1.}):
        with pytest.raises(ProtocolError):
            SceneFixture(world,dict(recipe,**changes),rows.append)
    world.model.cam_bodyid = np.array([3])
    with pytest.raises(ProtocolError,match="camera attachment"):
        SceneFixture(world,recipe,rows.append)


def recording(tmp_path):
    # Two real timestamped unit-fixture frames; never counted as P1 case coverage.
    root = tmp_path/"frames"
    rng = np.random.default_rng(1)
    rgb = rng.integers(0,255,(64,64,3),dtype=np.uint8)
    with FrameRecorder(root,episode_id="unit",clock_domain="unit",condition="unit_fixture") as recorder:
        for i in range(2):
            view = dict(rgb=rgb,depth_m=np.full((64,64),.5,dtype=np.float32),
                        intrinsics_K=np.array([[100.,0,32],[0,100.,32],[0,0,1]]),T_base_camera=np.eye(4),
                        camera_id="agentview",frame_seq=i,frame_id=f"original/{i}",calibration_version="cal",
                        capture_sim_time_s=1+i*.1,capture_monotonic_ns=100+i*100_000_000,frame="robot_base")
            proprio = Proprioception(1+i*.1,100+i*100_000_000,(0.,0.,0.),(0.,0.,0.,1.),(0.,),None,True,("robot",),
                                      reason_codes=("WIDTH_UNCALIBRATED",))
            recorder.append([view],proprio,emitted_monotonic_ns=101+i*100_000_000)
    (tmp_path/"evaluator.jsonl").write_text("INVALID POISON ORACLE JOURNAL\n")
    seed = dict(camera_id="agentview",role="face",source_frame_id="unit/agentview/0",
                roi_xyxy_px=[16.,16.,48.,48.],query="visible feature")
    artifact = tmp_path/"model.json"
    artifact.write_text(json.dumps(dict(seed,seed_source="real_model",evaluation_labels_used=False)))
    seed.update(artifact_uri=str(artifact),artifact_sha256=file_hash(artifact))
    return root,dict(condition="real_model_seed",recording_frames_sha256=file_hash(root/"frames.jsonl"),seeds=[seed])


def test_sensor_only_replay_keeps_independent_unseeded_reference_and_no_truth(tmp_path):
    root,seeds = recording(tmp_path)
    summary = analyze(root,seeds,tmp_path/"analysis")
    assert summary["bundles"] == 2 and not summary["evaluator_truth_read"]
    assert summary["track_counts"]["agentview/reference/UNSEEDED"] == 2
    assert not summary["case_coverage_validated"] and not summary["verify_calibrated"]
    rows = [json.loads(line) for line in (tmp_path/"analysis/perception.jsonl").read_text().splitlines()]
    assert all(row.get("source_frame_id","").startswith("unit/") for row in rows)
    assert all(not row["track"]["semantic_identity_verified"] for row in rows if row["kind"] == "surface")


@pytest.mark.parametrize("mutation", ["artifact", "recording", "source", "label_provenance"])
def test_seed_mismatch_or_evaluation_label_input_rejected(tmp_path,mutation):
    root,seeds = recording(tmp_path)
    seeds = deepcopy(seeds)
    if mutation == "artifact":
        seeds["seeds"][0]["artifact_sha256"] = "0"*64
    elif mutation == "recording":
        seeds["recording_frames_sha256"] = "0"*64
    elif mutation == "source":
        seeds["seeds"][0]["source_frame_id"] = "other/frame"
    else:
        artifact = tmp_path/"model.json"
        value = json.loads(artifact.read_text())
        value["evaluation_labels_used"] = True
        artifact.write_text(json.dumps(value))
        seeds["seeds"][0]["artifact_sha256"] = file_hash(artifact)
    with pytest.raises(ProtocolError):
        analyze(root,seeds,tmp_path/"analysis")
