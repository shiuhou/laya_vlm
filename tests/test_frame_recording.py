import json

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.perception.recording import FrameRecorder, replay_frames, project_base_points
from embodied_runtime.sensor_api import Proprioception


def view():
    return dict(rgb=np.zeros((8,12,3),dtype=np.uint8),depth_m=np.ones((8,12),dtype=np.float32),
                intrinsics_K=np.array([[20.,0,6],[0,20.,4],[0,0,1]]),T_base_camera=np.eye(4),
                camera_id="front",frame_seq=1,frame_id="e/front/1",calibration_version="cal1",
                capture_sim_time_s=1.,capture_monotonic_ns=10,frame="robot_base")


def sample():
    return Proprioception(1.,10,(0.,0.,0.),(0.,0.,0.,1.),(0.,),None,True,("robot/1",),
                          reason_codes=("WIDTH_UNCALIBRATED",))


def test_roundtrip_arrays_metadata_capture_clock_and_immutability(tmp_path):
    path=tmp_path/"frames"
    original=view()
    with FrameRecorder(path,episode_id="ep",clock_domain="host/boot",condition="test") as rec:
        envelope=rec.append([original],sample(),emitted_monotonic_ns=20)
    restored=list(replay_frames(path))
    env,views=restored[0]
    assert env.message_id == envelope.message_id and env.payload["views"][0]["capture_monotonic_ns"]==10
    np.testing.assert_array_equal(original["rgb"],views[0]["rgb"])
    np.testing.assert_array_equal(original["depth_m"],views[0]["depth_m"])
    with pytest.raises(ValueError):
        views[0]["depth_m"][0,0]=2


def test_corrupted_blob_cannot_be_replayed(tmp_path):
    path=tmp_path/"frames"
    with FrameRecorder(path,episode_id="ep",clock_domain="host/boot",condition="test") as rec:
        env=rec.append([view()],sample(),emitted_monotonic_ns=20)
    blob=path/env.payload["views"][0]["depth_blob"]["uri"]
    blob.write_bytes(b"not-the-recorded-depth")
    with pytest.raises(ProtocolError,match="BLOB_CORRUPT"):
        list(replay_frames(path))


def test_repeated_directory_no_overwrite_and_mixed_camera_capture_not_faked(tmp_path):
    path=tmp_path/"frames"
    second={**view(),"camera_id":"wrist","capture_sim_time_s":.9,"capture_monotonic_ns":9}
    with FrameRecorder(path,episode_id="ep",clock_domain="host/boot",condition="test") as rec:
        env=rec.append([view(),second],sample(),emitted_monotonic_ns=20)
    assert env.payload["views"][1]["capture_sim_time_s"]==.9
    with pytest.raises(FileExistsError):
        FrameRecorder(path,episode_id="ep",clock_domain="host",condition="test")
    record=json.loads((path/"frames.jsonl").read_text())
    assert "camera_to_world" not in record["payload"]["views"][0]


def test_base_projection_non_square_and_nonidentity_transform():
    k=view()["intrinsics_K"]
    t=np.eye(4)
    t[:3,3]=[1.,2.,3.]
    pixels=project_base_points([[1.,2.,4.],[1.1,2.2,4.]],k,t)
    np.testing.assert_allclose(pixels,[[6,4],[8,8]])


def test_proprio_later_than_images_sets_bundle_clock_and_cannot_follow_emission(tmp_path):
    from dataclasses import replace
    late = replace(sample(), capture_sim_time_s=1.1, capture_monotonic_ns=15)
    with FrameRecorder(tmp_path/"valid", episode_id="ep", clock_domain="host", condition="test") as recorder:
        env = recorder.append([view()], late, emitted_monotonic_ns=20)
    assert env.payload["capture_sim_time_s"] == 1.1
    assert env.payload["capture_monotonic_ns"] == 15
    assert env.payload["views"][0]["capture_sim_time_s"] == 1.
    with FrameRecorder(tmp_path/"invalid", episode_id="ep", clock_domain="host", condition="test") as recorder:
        with pytest.raises(ProtocolError, match="emission precedes"):
            recorder.append([view()], late, emitted_monotonic_ns=12)
        assert recorder.seq == 0


@pytest.mark.parametrize("clock,value", [("capture_sim_time_s", 1.1), ("capture_monotonic_ns", 11)])
def test_frame_contract_rejects_proprio_from_after_bundle(tmp_path, clock, value):
    from embodied_runtime.contracts import thaw, validate_frame_bundle
    with FrameRecorder(tmp_path/"frames", episode_id="ep", clock_domain="host", condition="test") as recorder:
        env = recorder.append([view()], sample(), emitted_monotonic_ns=20)
    payload = thaw(env.payload)
    payload["proprio"][clock] = value
    with pytest.raises(ProtocolError, match="proprio captured after"):
        validate_frame_bundle(payload)


def test_source_frame_id_preserved_with_explicit_canonical_mapping(tmp_path):
    original = {**view(), "frame_id": "source-camera:1"}
    path = tmp_path/"frames"
    with FrameRecorder(path, episode_id="ep", clock_domain="host", condition="test") as recorder:
        recorder.append([original], sample(), emitted_monotonic_ns=20)
    _, views = next(replay_frames(path))
    assert views[0]["frame_id"] == "source-camera:1"
    assert views[0]["canonical_frame_id"] == "ep/front/1"
    assert views[0]["episode_id"] == "ep" and views[0]["clock_domain"] == "host"
    sidecar = json.loads((path/"source-identities.jsonl").read_text())
    assert sidecar["sources"][0]["source_frame_id"] == original["frame_id"]


@pytest.mark.parametrize("corruption", ["metadata", "identity", "missing_identity", "drop_both"])
def test_metadata_identity_or_tail_corruption_is_detected(tmp_path, corruption):
    path = tmp_path/"frames"
    with FrameRecorder(path, episode_id="ep", clock_domain="host", condition="test") as recorder:
        recorder.append([view()], sample(), emitted_monotonic_ns=20)
    frames, sidecar = path/"frames.jsonl", path/"source-identities.jsonl"
    if corruption == "metadata":
        data = json.loads(frames.read_text())
        data["payload"]["views"][0]["T_base_camera"][0][3] = 10
        frames.write_text(json.dumps(data)+"\n")
    elif corruption == "identity":
        data = json.loads(sidecar.read_text())
        data["sources"][0]["source_frame_id"] = "different-frame"
        sidecar.write_text(json.dumps(data)+"\n")
    elif corruption == "missing_identity":
        sidecar.write_text("")
    else:
        frames.write_text("")
        sidecar.write_text("")
    with pytest.raises(ProtocolError, match="RECORDING_"):
        list(replay_frames(path))


@pytest.mark.parametrize("key,value", [("episode_id", "foreign"), ("episode_generation", 9),
                                      ("goal_generation", 9), ("clock_domain", "foreign-clock")])
def test_replay_rejects_mixed_recording_context_even_if_record_is_self_consistent(tmp_path, key, value):
    from embodied_runtime.contracts import content_hash
    path = tmp_path/"frames"
    with FrameRecorder(path, episode_id="ep", clock_domain="host", condition="test") as recorder:
        recorder.append([view()], sample(), emitted_monotonic_ns=20)
    record = json.loads((path/"frames.jsonl").read_text())
    record[key] = value
    identity = json.loads((path/"source-identities.jsonl").read_text())
    identity["envelope_sha256"] = content_hash(record)
    identity["record_sha256"] = content_hash({k: v for k, v in identity.items() if k != "record_sha256"})
    (path/"frames.jsonl").write_text(json.dumps(record)+"\n")
    (path/"source-identities.jsonl").write_text(json.dumps(identity)+"\n")
    with pytest.raises(ProtocolError, match="episode/clock/generation"):
        list(replay_frames(path))
