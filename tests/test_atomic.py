from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.adapters.libero import LiberoWorldBackend
from embodied_runtime.runtime_core import MOVE, AtomicExecutor


class World:
    def __init__(self):
        self.obs = {"robot0_eef_pos": np.zeros(3)}
        self.data = SimpleNamespace(time=0.0)
        self.model = SimpleNamespace(opt=SimpleNamespace(timestep=0.002))
        self.calls = []

    def features(self):
        return {"finger_gap_mm": 80.0, "success": False, "contacts": [],
                "eef_rotation_matrix": np.eye(3).tolist()}

    def execute(self, name, grip, record):
        self.calls.append((name, grip))
        self.data.time += .4
        if name[0] in "xyz" and name.endswith("mm"):
            self.obs["robot0_eef_pos"]["xyz".index(name[0])] += float(name[1:-2]) / 1000
        return {"commands": [np.r_[np.zeros(6), grip]] * 8, "steps": 8}


@pytest.mark.parametrize("token", list(MOVE) + ["STOP", "ROTATE_CW", "ROTATE_CCW"])
def test_pose_tokens_preserve_backend_gripper_after_open_close_and_new_executor(token):
    world = World()
    backend = LiberoWorldBackend(world)
    for gripper_token, command in (("RELEASE", -1), ("GRASP", 1), ("RELEASE", -1)):
        AtomicExecutor(backend).execute(gripper_token)
        result = AtomicExecutor(backend).execute(token)
        assert world.calls[-1][1] == command
        assert result["execution_before"]["gripper_command"] == command
        assert result["execution_after"]["gripper_command"] == command
        assert "gripper_command_changed_unexpectedly" not in result["execution_contract_reason"]
        assert result["environment_step_count"] == 8
        assert result["low_level_step_count"] == 200


def test_translation_scale_and_gripper_override_are_not_silently_approximated():
    backend = LiberoWorldBackend(World())
    for delta in ([.02, 0, 0], [0, 0, 0], [.01, .01, 0], [float("nan"), 0, 0]):
        with pytest.raises(ValueError):
            backend.apply_delta(delta)
    with pytest.raises(ValueError, match="cannot change gripper"):
        backend.apply_delta([.01, 0, 0], grip_cmd=1)
    assert backend.world.calls == []


def test_execution_contract_detects_wrong_translation():
    backend = LiberoWorldBackend(World())
    before = backend.execution_state()
    backend.apply_delta([-.01, 0, 0])
    result = backend.execution_evidence("MV_FWD", before)
    assert result["execution_contract_violation"]
    assert result["execution_contract_reason"] == ["translation_error"]


def test_stop_is_a_hold_with_retained_command_and_done_does_not_reuse_trace():
    backend = LiberoWorldBackend(World())
    executor = AtomicExecutor(backend)
    result = executor.execute("STOP")
    assert backend.world.calls == [("hold", -1)]
    assert not result["execution_contract_violation"]
    original = backend.world.features
    backend.world.features = lambda: {**original(), "success": True}
    result = executor.execute("DONE")
    assert result["low_level_step_count"] == 0
    assert result["low_level_commands"] == []
