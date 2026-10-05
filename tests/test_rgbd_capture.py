from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource, fixed_robot_base
from embodied_runtime.contracts import ProtocolError


def fixture():
    data = SimpleNamespace(time=1.25)
    rgb = np.arange(4 * 7 * 3, dtype=np.uint8).reshape(4, 7, 3)
    depth = np.arange(28, dtype=np.float32).reshape(4, 7)/100 + .1
    calls = []
    model = SimpleNamespace(camera_name2id=lambda name: 0, cam_pos=np.array([[0., 0., .2]]),
                            cam_quat=np.array([[1., 0., 0., 0.]]), cam_bodyid=np.array([1]),
                            body_id2name=lambda _: "robot_owned_camera_mount")
    sim = SimpleNamespace(model=model)
    sim.render = lambda **kwargs: (calls.append(kwargs) or (rgb, depth))
    base = SimpleNamespace(base_pos=np.array([1., 2., 3.]), base_ori=np.array([0., 0., 0., 1.]))
    world = SimpleNamespace(render_enabled=True, data=data, env=SimpleNamespace(sim=sim, env=SimpleNamespace(robots=[base])))
    camera_pose = np.eye(4)
    camera_pose[:3, 3] = [2., 3., 4.]
    dimensions = []

    def intrinsic(sim, camera, height, width):
        dimensions.append((height, width))
        return np.array([[height*2, 0., width/2], [0., height*2, height/2], [0., 0., 1.]])
    utils = SimpleNamespace(get_camera_intrinsic_matrix=intrinsic,
                            get_camera_extrinsic_matrix=lambda *args: camera_pose,
                            get_real_depth_map=lambda sim, raw: raw*2)
    return world, utils, rgb, depth, calls, dimensions, camera_pose


def source(world, utils, **kw):
    return LiberoRgbdSource(world, width=7, height=4, camera_utils=utils, monotonic_ns=lambda: 12345, **kw)


def test_single_same_exposure_render_non_square_calibration_flip_and_provenance():
    world, utils, rgb, depth, calls, dimensions, pose = fixture()
    frame = source(world, utils).capture()
    assert calls == [dict(width=7, height=4, camera_name="agentview", depth=True)]
    assert dimensions == [(4, 7)]
    np.testing.assert_array_equal(frame["rgb"], rgb[::-1])
    np.testing.assert_allclose(frame["depth_m"], depth[::-1]*2)
    np.testing.assert_allclose(frame["T_base_camera"][:3, 3], [1, 1, 1])
    assert frame["capture_sim_time_s"] == frame["capture_sim_time"] == 1.25
    assert frame["capture_monotonic_ns"] == 12345
    assert frame["camera_id"] == "agentview" and frame["frame_seq"] == 1
    assert frame["frame_id"] == "agentview:1" and frame["frame"] == "robot_base"
    assert frame["pixel_origin"] == "top_left" and frame["depth_units"] == "m"
    assert frame["synchronization"] == "single_depth_render_tuple"
    assert frame["calibration_version"].startswith("camera-calibration:")
    np.testing.assert_allclose(frame["camera_to_world"], pose)
    for key in ("rgb", "depth_m", "intrinsics_K", "T_base_camera", "camera_to_world"):
        assert not frame[key].flags.writeable
    rgb[:] = 0
    assert frame["rgb"].sum() > 0


def test_non_square_pixel_depth_backprojection_reprojects_in_base_frame():
    world, utils, *_ = fixture()
    frame = source(world, utils).capture()
    K, T = frame["intrinsics_K"], frame["T_base_camera"]
    pixel = np.array([5., 1., 1.])
    point_camera = np.linalg.inv(K) @ pixel * 1.3
    point_base = T @ np.r_[point_camera, 1]
    recovered = np.linalg.inv(T) @ point_base
    projected = K @ recovered[:3]
    np.testing.assert_allclose(projected[:2]/projected[2], pixel[:2], atol=1e-12)


def test_moving_wrist_pose_does_not_relabel_static_camera_calibration():
    world, utils, *_, pose = fixture()
    camera = source(world, utils, camera_name="robot0_eye_in_hand")
    a = camera.capture()
    pose[0, 3] += .1
    b = camera.capture()
    assert a["calibration_version"] == b["calibration_version"]
    assert a["frame_id"] != b["frame_id"]
    assert b["T_base_camera"][0, 3] - a["T_base_camera"][0, 3] == pytest.approx(.1)
    world.env.sim.model.cam_pos[0, 0] += .01
    assert camera.capture()["calibration_version"] != b["calibration_version"]


@pytest.mark.parametrize("bad", [np.ones((4, 7)), (np.zeros((4, 7, 3), np.uint8),),
                                 (np.zeros((7, 4, 3), np.uint8), np.ones((4, 7))),
                                 (np.zeros((4, 7, 3), float), np.ones((4, 7)))])
def test_unpaired_or_wrong_shape_images_rejected_without_fallback_render(bad):
    world, utils, *_ = fixture()
    calls = []
    world.env.sim.render = lambda **kw: (calls.append(kw) or bad)
    camera = source(world, utils)
    with pytest.raises(ProtocolError):
        camera.capture()
    assert len(calls) == 1 and camera.capture_seq == 0


@pytest.mark.parametrize("advance_in", ["render", "calibration"])
def test_capture_rejects_simulation_race_and_does_not_publish(advance_in):
    world, utils, rgb, depth, *_ = fixture()
    def render(**kw):
        world.data.time += .01
        return rgb, depth
    def calibration(*args):
        world.data.time += .01
        return np.eye(4)
    if advance_in == "render":
        world.env.sim.render = render
    else:
        utils.get_camera_extrinsic_matrix = calibration
    camera = source(world, utils)
    with pytest.raises(ProtocolError, match="UNSYNCHRONIZED"):
        camera.capture()
    assert camera.capture_seq == 0


def test_unknown_depth_and_invalid_calibration_remain_explicit():
    world, utils, *_ = fixture()
    utils.get_real_depth_map = lambda sim, depth: np.array([[np.nan, -1, np.inf, 1, 1, 1, 1]]*4)
    frame = source(world, utils).capture()
    assert np.isnan(frame["depth_m"][:, :3]).all()
    assert np.all(frame["depth_m"][:, 3:] == 1)
    world.env.env.robots[0].base_ori = np.eye(3)
    np.testing.assert_allclose(fixed_robot_base(world)[:3, :3], np.eye(3))
    world.env.env.robots[0].base_ori = [0, 0, 0, 0]
    with pytest.raises(ProtocolError):
        fixed_robot_base(world)


def test_source_clock_regression_and_bad_dimensions_rejected():
    world, utils, *_ = fixture()
    camera = source(world, utils)
    camera.capture()
    world.data.time = .25
    with pytest.raises(ProtocolError, match="INVALID_CLOCK"):
        camera.capture()
    with pytest.raises(ProtocolError):
        LiberoRgbdSource(world, width=0, height=4)
