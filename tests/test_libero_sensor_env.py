from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.adapters.libero_rgbd import rotation_from_xyzw
from embodied_runtime.adapters.libero_sensor_env import LiberoSensorEnv, quaternion_xyzw
from embodied_runtime.contracts import ProtocolError


class OwnRegisters:
    def __init__(self, values):
        self.values, self.reads = values, []

    def __getitem__(self, key):
        assert type(key) is int and key in self.values, f"undeclared robot register: {key}"
        self.reads.append(key)
        return self.values[key]


def fixture():
    qpos, qvel = OwnRegisters({2: .1, 4: .2}), OwnRegisters({1: .01, 3: .02})
    site_pos = OwnRegisters({7: [1., 3., 3.]})
    site_rot = OwnRegisters({7: np.eye(3).reshape(-1)})
    data = SimpleNamespace(qpos=qpos, qvel=qvel, site_xpos=site_pos, site_xmat=site_rot, time=1.)
    class World:
        render_enabled = True
        closed = False
        def __getattr__(self, name):
            raise AssertionError(f"forbidden world access: {name}")
        def close(self):
            self.closed = True
    robot = SimpleNamespace(base_pos=[1., 2., 3.], base_ori=[0., 0., 0., 1.],
                            _ref_joint_pos_indexes=[2, 4], _ref_joint_vel_indexes=[1, 3], eef_site_id=7,
                            robot_model=SimpleNamespace(root_body="robot0_base"))
    sim = SimpleNamespace(data=data, render=lambda **kw: (np.zeros((4, 7, 3), np.uint8), np.ones((4, 7), np.float32)))
    world = World()
    world.data, world.env = data, SimpleNamespace(sim=sim, env=SimpleNamespace(robots=[robot]))
    utils = SimpleNamespace(get_camera_intrinsic_matrix=lambda *args: np.eye(3),
                            get_camera_extrinsic_matrix=lambda *args: np.eye(4), get_real_depth_map=lambda sim, raw: raw)
    ticks = iter(range(1000, 2000))
    env = LiberoSensorEnv(world, width=7, height=4, calibration_versions={"agentview": "cal-a", "robot0_eye_in_hand": "cal-b"},
                          monotonic_ns=lambda: next(ticks), camera_utils=utils, retained_gripper_command=lambda: "CLOSE")
    return world, env, qpos, qvel, site_pos, site_rot


def test_only_robot_encoder_and_registered_eef_fk_access_with_unknown_jaw():
    world, env, qpos, qvel, pos, rot = fixture()
    p = env.read_proprioception()
    assert qpos.reads == [2, 4] and qvel.reads == [1, 3]
    assert pos.reads == rot.reads == [7]
    assert p.joint_position_rad == (.1, .2) and p.joint_velocity_rad_s == (.01, .02)
    assert p.eef_position_base_m == (0., 1., 0.)
    assert p.eef_pose_source == "robot_fk" and p.robot_model_id
    assert p.gripper_command == "CLOSE" and p.gripper_width_m is None and p.holding is None
    assert p.gripper_joint_position_rad is None  # Panda finger sliders are meters, not radians.
    assert p.reason_codes == ("WIDTH_UNCALIBRATED",)
    assert world.data.time == 1.


def test_port_exposes_sensing_only_and_bundle_preserves_per_view_clocks():
    world, env, *_ = fixture()
    port = env.sensor_port()
    for forbidden in ("world", "features", "predict_all", "contacts", "success", "command_tick", "hold", "step"):
        assert not hasattr(port, forbidden)
    bundle = port.capture()
    assert bundle["bundle_id"] == "sensor-bundle:1"
    assert [v["camera_id"] for v in bundle["views"]] == ["agentview", "robot0_eye_in_hand"]
    assert [v["calibration_version"] for v in bundle["views"]] == ["cal-a", "cal-b"]
    times = [v["capture_monotonic_ns"] for v in bundle["views"]]
    assert times[0] < times[1] < bundle["proprio"]["capture_monotonic_ns"] < bundle["capture_monotonic_ns"]
    assert {v["capture_sim_time_s"] for v in bundle["views"]} == {1.}
    assert bundle["proprio"]["frame"] == "robot_base"
    assert world.data.time == 1


def test_rotated_fixed_base_transforms_robot_and_camera_consistently():
    world, old, *_ = fixture()
    old.close()
    q = [0, 0, np.sin(np.pi/4), np.cos(np.pi/4)]
    world.env.env.robots[0].base_ori = q
    env = LiberoSensorEnv(world, camera_names=("agentview",), width=7, height=4,
                          calibration_versions={"agentview": "cal"},
                          camera_utils=SimpleNamespace(get_camera_intrinsic_matrix=lambda *a: np.eye(3),
                              get_camera_extrinsic_matrix=lambda *a: np.eye(4), get_real_depth_map=lambda s, d: d))
    sample = env.capture()
    np.testing.assert_allclose(sample["proprio"]["eef_position_base_m"], [1, 0, 0], atol=1e-12)
    np.testing.assert_allclose(rotation_from_xyzw(sample["proprio"]["eef_quaternion_xyzw"]), rotation_from_xyzw(q).T, atol=1e-12)
    np.testing.assert_allclose(sample["views"][0]["T_base_camera"][:3, :3], rotation_from_xyzw(q).T, atol=1e-12)


@pytest.mark.parametrize("axis", range(3))
def test_quaternion_conversion_halfturns_are_normalized(axis):
    q = np.zeros(4)
    q[axis] = 1
    rotation = rotation_from_xyzw(q)
    np.testing.assert_allclose(rotation_from_xyzw(quaternion_xyzw(rotation)), rotation, atol=1e-12)


def test_invalid_robot_measurement_is_rejected_not_replaced_with_truth():
    world, env, qpos, *_ = fixture()
    qpos.values[2] = float("nan")
    with pytest.raises(ProtocolError):
        env.read_proprioception()
    assert world.data.time == 1


def test_context_shutdown_does_not_step_or_close_borrowed_world():
    world, env, *_ = fixture()
    with env:
        env.read_proprioception()
    assert not world.closed and world.data.time == 1
    with pytest.raises(ProtocolError, match="SENSOR_CLOSED"):
        env.capture()
    with LiberoSensorEnv(world, camera_names=("agentview",), owns_world=True):
        pass
    assert world.closed


def test_proprio_capture_race_rejected_without_reading_other_scene_state():
    world, env, qpos, *_ = fixture()
    original = qpos.__class__.__getitem__
    class RacingRegisters(OwnRegisters):
        def __getitem__(self, key):
            value = original(self, key)
            world.data.time += .01
            return value
    qpos.__class__ = RacingRegisters
    with pytest.raises(ProtocolError, match="UNSYNCHRONIZED_PROPRIO"):
        env.read_proprioception()


def test_unknown_retained_command_is_not_reported_as_measured_open_or_closed():
    world, _, *_ = fixture()
    env = LiberoSensorEnv(world, camera_names=("agentview",))
    p = env.read_proprioception()
    assert p.gripper_command == "KEEP" and p.gripper_width_m is None
    assert "GRIPPER_COMMAND_NOT_OBSERVED" in p.reason_codes
