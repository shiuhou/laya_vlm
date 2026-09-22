from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments.operating_regime_probe import (
    ControlTrace, _fingerprint, angle_degrees, fk_feedback_hold,
)
from embodied_runtime.runtime_core import _sha256_json


def test_fingerprint_preserves_array_precision_shape_and_cache_content():
    source = {"array": np.array([1., 2.]), "buffer": SimpleNamespace(value=[3., None])}
    first = _sha256_json(_fingerprint(source))
    assert first == _sha256_json(_fingerprint(source))
    source["array"][0] += 1e-12
    assert first != _sha256_json(_fingerprint(source))
    assert _fingerprint(np.ones((1, 2))) != _fingerprint(np.ones((2,)))
    with pytest.raises(TypeError, match="unsupported"):
        _fingerprint(object())


def test_rotation_angle_uses_full_orientation_not_one_euler_axis():
    assert angle_degrees(np.eye(3)) == 0.
    assert angle_degrees(np.diag([-1., -1., 1.])) == 180.


@pytest.mark.parametrize("success_step, expected_steps", [(None, 8), (1, 1), (3, 3)])
def test_fk_diagnostic_retains_native_horizon_and_grip(success_step, expected_steps):
    position = np.array([1., 2., 3.])
    commands = []
    def step(action):
        commands.append(action.copy())
        position[:] += [.001, 0., 0.]
        return {}, 0, False, {}
    world = SimpleNamespace(env=SimpleNamespace(step=step), obs={})
    world.features = lambda: {"success": len(commands) == success_step, "obstacle_force_N": 0., "contacts": []}
    telemetry = SimpleNamespace(kinematics=lambda: (position.copy(),))
    output = fk_feedback_hold(world, telemetry, 1.)
    assert output["steps"] == expected_steps
    assert all(c[-1] == 1. and np.array_equal(c[3:6], [0., 0., 0.]) for c in commands)
    assert np.array_equal(commands[0], [0., 0., 0., 0., 0., 0., 1.])
    if len(commands) > 1:
        assert commands[1][0] == pytest.approx(-.02)


@pytest.mark.parametrize("fail", [False, True])
def test_trace_calls_original_controller_once_and_restores_methods(fail):
    class Controller:
        def __init__(self):
            self.goal_pos = self.ee_pos = np.zeros(3)
            self.goal_ori = self.ee_ori_mat = np.eye(3)
            self.ee_pos_vel = np.zeros(3)
            self.calls = 0
        def run_controller(self):
            self.calls += 1
            return np.array([2., -.5])
    controller = Controller()
    class Env:
        robots = [SimpleNamespace(controller=controller, torque_limits=(np.array([-1., -1.]), np.ones(2)))]
        def step(self, action):
            for _ in range(25):
                self.robots[0].controller.run_controller()
            if fail:
                raise RuntimeError("injected simulator failure")
            return {"robot0_eef_pos": np.zeros(3)}, 0., False, {}
    env = Env()
    backend = SimpleNamespace(world=SimpleNamespace(env=env))
    telemetry = SimpleNamespace(read=lambda: {"tcp_observed_m": [0., 0., 0.]})
    trace = ControlTrace(backend, telemetry)
    if fail:
        with pytest.raises(RuntimeError, match="injected"):
            with trace:
                env.step(np.zeros(7))
    else:
        with trace:
            env.step(np.zeros(7))
        assert trace.rows[0]["inner"]["physics_steps"] == 25
        assert trace.rows[0]["inner"]["clipped_steps_by_joint"] == [25, 0]
    assert controller.calls == 25
    assert "step" not in env.__dict__
    assert "run_controller" not in controller.__dict__
