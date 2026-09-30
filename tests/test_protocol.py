import json
from dataclasses import replace

import pytest

from embodied_runtime.contracts import (BlobRef, Envelope, ProtocolError, canonical_json,
                                        freeze, load_config, thaw, validate_frame_bundle)


def envelope(**changes):
    data = dict(message_type="GeometryObservation", message_id="ep/g/1", producer="g",
                producer_seq=1, episode_id="ep", episode_generation=1, goal_generation=1,
                clock_domain="host/boot", reference_sim_time_s=.1, emitted_monotonic_ns=100,
                source_ids=(), payload={"position_m": [1, 2, 3]})
    data.update(changes)
    return Envelope(**data)


def test_roundtrip_deep_immutability_and_input_alias():
    payload = {"nested": [{"value": [1, 2]}]}
    msg = envelope(payload=payload)
    before = canonical_json(msg)
    payload["nested"][0]["value"][0] = 9
    assert canonical_json(msg) == before
    with pytest.raises(TypeError):
        msg.payload["nested"][0]["value"][0] = 9
    assert canonical_json(Envelope.from_mapping(json.loads(before))) == before


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), object()])
def test_nonfinite_or_unsupported_payload(value):
    with pytest.raises(ProtocolError):
        envelope(payload={"x": value})


def test_strict_schema_and_missing_value():
    with pytest.raises(ProtocolError):
        Envelope.from_mapping({**thaw(envelope()), "unknown": 1})
    with pytest.raises(ProtocolError):
        replace(envelope(), producer_seq=True)
    assert thaw(freeze({"position": None, "valid": False, "reason": "LOST"}))["position"] is None


def frame_bundle():
    from embodied_runtime.sensor_api import Proprioception
    proprio = Proprioception.from_mapping(dict(
        capture_sim_time_s=0., capture_monotonic_ns=0,
        eef_position_base_m=[0., 0., 0.], eef_quaternion_xyzw=[0., 0., 0., 1.],
        joint_position_rad=[0.], gripper_width_m=None, valid=True,
        source_ids=["robot/encoder/0"], reason_codes=["WIDTH_UNCALIBRATED"],
    ))
    view = dict(camera_id="front", frame_seq=1, calibration_version="cal1",
                width_px=640, height_px=480, depth_units="m", pixel_origin="top_left",
                capture_sim_time_s=0., capture_monotonic_ns=0,
                rgb_blob=thaw(BlobRef("frames/rgb.npy", "a"*64, (480,640,3), "uint8", "HWC")),
                depth_blob=thaw(BlobRef("frames/depth.npy", "b"*64, (480,640), "float32", "HW", 1.)),
                intrinsics_K=[[100.,0.,320.],[0.,100.,240.],[0.,0.,1.]],
                T_base_camera=[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]])
    return dict(bundle_id="frame/1", capture_sim_time_s=0., capture_monotonic_ns=0,
                views=[view], proprio=thaw(proprio))


def test_frame_shapes_non_square_metric_depth_and_transform():
    p = frame_bundle()
    validate_frame_bundle(p)
    p["views"][0]["depth_blob"]["shape"] = [640,480]
    with pytest.raises(ProtocolError):
        validate_frame_bundle(p)
    p = frame_bundle()
    p["views"][0]["T_base_camera"][0][0] = -1
    with pytest.raises(ProtocolError, match="proper"):
        validate_frame_bundle(p)


def test_config_strictness(tmp_path):
    config = load_config("configs/p0_runtime.json")
    assert config["segment_duration_s"] == .1
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({**thaw(config), "surprise": True}))
    with pytest.raises(ProtocolError):
        load_config(path)


def test_blob_cannot_reference_recycled_ring():
    with pytest.raises(ProtocolError):
        BlobRef("ring:slot3", "a"*64, (1,), "uint8", "H")
