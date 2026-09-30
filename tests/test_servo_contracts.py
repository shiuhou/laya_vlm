from dataclasses import replace

import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.control.action_contracts import instantiate_contract
from embodied_runtime.control.servo import Servo
from embodied_runtime.experiments.p0_contract_probe import SyntheticRobot
from test_action_contracts import setup


def servo(action="X+40"):
    request, proposal, latest = setup(action)
    robot = SyntheticRobot()
    robot.position = latest.measured_eef_pose.position_m
    motor = Servo(robot, latest_context=lambda *_: latest)
    contract = instantiate_contract(request,proposal,latest=latest,contract_id="contract",
                                    now_sim_time_s=0.,now_monotonic_ns=0,controller_config_id="fixture")
    motor.install(contract,sim_time_s=0.,monotonic_ns=0)
    return robot,motor,contract


@pytest.mark.parametrize("sim,wall", [(.1,0),(0.,100_000_000)])
def test_either_clock_expiry_inclusive_blocks_command(sim,wall):
    robot,motor,_ = servo()
    result = motor.tick(sim_time_s=sim,monotonic_ns=wall)
    assert result.status == "ABORTED"
    assert not robot.commands


def test_contract_duplicate_does_not_repeat_and_changed_content_rejected():
    robot,motor,c = servo()
    assert not motor.install(c,sim_time_s=0.,monotonic_ns=0)
    motor.tick(sim_time_s=0.,monotonic_ns=0)
    motor.tick(sim_time_s=.05,monotonic_ns=50_000_000)
    assert not motor.install(c,sim_time_s=.1,monotonic_ns=100_000_000)
    assert len(robot.commands) == 2
    with pytest.raises(ProtocolError):
        motor.install(replace(c,contract_id="new-for-same-decision"),sim_time_s=0.,monotonic_ns=0)


@pytest.mark.parametrize("grip,width", [("OPEN",.08),("CLOSE",0.)])
def test_retained_gripper_command_across_move_and_hold(grip,width):
    robot,motor,_ = servo()
    robot.grip,robot.width = grip,width
    motor.tick(sim_time_s=0.,monotonic_ns=0)
    motor.tick(sim_time_s=.05,monotonic_ns=50_000_000)
    motor.tick(sim_time_s=.1,monotonic_ns=100_000_000)
    assert robot.grip == grip and robot.width == width


def test_measured_feedback_does_not_claim_commanded_displacement():
    robot,motor,_ = servo()
    def stalled(position,rotation,grip,duration):
        robot.sim_time_s += duration
        robot.monotonic_ns += round(duration*1e9)
    robot.command_tick = stalled
    motor.tick(sim_time_s=0.,monotonic_ns=0)
    result = motor.tick(sim_time_s=.05,monotonic_ns=50_000_000)
    assert result.measured_eef_delta_m == (0.,0.,0.)
    assert result.remaining_requested_magnitude == .04
    assert result.status == "PARTIAL"


def test_validation_latency_cannot_execute_using_old_tick_entry_time():
    robot,motor,_ = servo()
    current_wall = [0]
    original = motor.latest_context
    def slow_validation(sim,wall):
        current_wall[0] = 100_000_000  # The callback consumed the whole contract.
        return original(sim,wall)
    motor.latest_context = slow_validation
    motor.monotonic_clock = lambda: current_wall[0]
    result = motor.tick(sim_time_s=0.,monotonic_ns=0)
    assert not robot.commands
    assert result.reason_codes == ("CONTRACT_EXPIRED",)
