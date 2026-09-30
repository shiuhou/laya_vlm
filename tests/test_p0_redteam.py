"""Independent adversarial P0 regressions; synthetic only, no robot/model runs."""
from dataclasses import replace
from math import pi
import time

import pytest

from embodied_runtime.contracts import BrainIntent, freeze, load_config
from embodied_runtime.control.action_catalog import ACTION_IDS
from embodied_runtime.control.action_contracts import (
    ActionProposal, EefPose, LayaRequest, ValidationContext, instantiate_contract,
)
from embodied_runtime.control.local_candidates import HardEvidence, build_candidate_set
from embodied_runtime.control.servo import Servo
from embodied_runtime.experiments.p0_contract_probe import SyntheticRig, SyntheticRobot, fake_choose
from embodied_runtime.workers import LatestWorker


def _immutable_result(request):
    return freeze({"echo": request["request_id"], "nested": {"ids": ["X+03"]}})


def _unsupported_result(request):
    return object()


def _context(identity, robot, snapshot_id="snapshot"):
    return ValidationContext(identity, snapshot_id, (), True, True, True,
                             dict.fromkeys(ACTION_IDS, "ALLOWED"),
                             EefPose(robot.position, robot.quaternion))


def _contract(action, rig):
    identity = rig.identity
    hard = HardEvidence("ALLOWED", ("HARD_CONSTRAINTS_SATISFIED",), ("fixture",), "synthetic")
    pool = build_candidate_set(candidate_set_id="set", identity=identity,
                               source_snapshot_id="snapshot", hard_evidence=dict.fromkeys(ACTION_IDS, hard),
                               generated_monotonic_ns=0, proposal_deadline_monotonic_ns=1_200_000_000)
    request = LayaRequest("request", pool, pool.proposal_deadline_monotonic_ns)
    proposal = ActionProposal("request", "decision", "set", pool.candidate_hash,
                              identity, "snapshot", action,
                              {key: float(key == action) for key in ACTION_IDS}, "fake", 0.)
    return instantiate_contract(request, proposal, latest=_context(identity, rig.robot),
                                contract_id="contract", now_sim_time_s=0., now_monotonic_ns=0,
                                controller_config_id="fixture")


def test_duplicate_cancel_cannot_revoke_newly_installed_intent():
    rig = SyntheticRig()
    scheduler = rig.scheduler
    scheduler.cancel("operator_cancel", event_id="cancel-1")
    generation = scheduler.identity.goal_generation
    # Synchronize the synthetic observation owner's goal context after cancellation.
    rig.identity = replace(rig.identity, goal_generation=generation)
    rig.router.goal_generation = generation
    rig.install_intent()
    new_intent = scheduler.intent
    scheduler.cancel("operator_cancel", event_id="cancel-1")
    assert scheduler.identity.goal_generation == generation
    assert scheduler.intent is new_intent


class WrongRotationRobot(SyntheticRobot):
    wrong_axis = False

    def command_tick(self, position, rotation, gripper, duration):
        actual = (0., rotation[0], 0.) if self.wrong_axis else tuple(-value for value in rotation)
        super().command_tick(position, actual, gripper, duration)


@pytest.mark.parametrize("wrong_axis", [False, True])
def test_wrong_direction_or_axis_rotation_is_not_reported_as_requested_progress(wrong_axis):
    rig = SyntheticRig()
    robot = WrongRotationRobot()
    robot.wrong_axis = wrong_axis
    rig.robot = robot
    contract = _contract("RX+10", rig)
    servo = Servo(robot, latest_context=lambda t, n: _context(rig.identity, robot))
    servo.install(contract, sim_time_s=0., monotonic_ns=0)
    servo.tick(sim_time_s=0., monotonic_ns=0)
    feedback = servo.tick(sim_time_s=.05, monotonic_ns=50_000_000)
    assert feedback is not None
    assert feedback.remaining_requested_magnitude == pytest.approx(pi / 18)
    assert feedback.status != "COMPLETED"


class StuckGripperRobot(SyntheticRobot):
    def command_tick(self, position, rotation, gripper, duration):
        before = self.width
        super().command_tick(position, rotation, gripper, duration)
        self.width = before


@pytest.mark.parametrize("action", ["OPEN", "CLOSE"])
def test_measured_width_does_not_invent_gripper_completion_predicate(action):
    rig = SyntheticRig()
    robot = StuckGripperRobot()
    robot.width = .04
    rig.robot = robot
    contract = _contract(action, rig)
    servo = Servo(robot, latest_context=lambda t, n: _context(rig.identity, robot))
    servo.install(contract, sim_time_s=0., monotonic_ns=0)
    servo.tick(sim_time_s=0., monotonic_ns=0)
    feedback = servo.tick(sim_time_s=.05, monotonic_ns=50_000_000)
    assert feedback.measured_gripper_state["gripper_width_m"] == .04
    assert feedback.measured_gripper_state["gripper_command"] == action
    assert feedback.status == "PARTIAL"
    assert "GRIPPER_COMPLETION_UNKNOWN" in feedback.reason_codes


@pytest.mark.parametrize("infer,expect_error", [(_immutable_result, False), (_unsupported_result, True)])
def test_worker_output_is_validated_before_async_queue_serialization(infer, expect_error):
    worker = LatestWorker(infer)
    try:
        worker.submit({"request_id": "request-1"})
        deadline = time.monotonic() + 5.
        result = None
        while result is None and time.monotonic() < deadline:
            result = worker.poll()
            if result is None:
                time.sleep(.01)
        assert result is not None, "bad/immutable output must not strand a live worker in_flight"
        assert result["request_id"] == "request-1"
        if expect_error:
            assert result["error"] is not None
            assert result["output"] is None
        else:
            assert result["error"] is None
            assert result["output"]["nested"]["ids"] == ("X+03",)
        assert worker.in_flight is None
    finally:
        assert not worker.close()["alive"]


@pytest.mark.parametrize("action,key,cap", [
    ("X+40", "segment_translation_m", .001),
    ("RX+10", "segment_rotation_rad", pi / 360),
])
def test_tighter_configured_segment_caps_reach_execution_contract(action, key, cap):
    config = {**load_config("configs/p0_runtime.json"), key: cap}
    rig = SyntheticRig(config=config)
    rig.install_intent()
    _, payload = rig.request()
    assert rig.scheduler.receive_model_result({"request_id": payload["request_id"],
                                               "output": fake_choose(payload, action_id=action), "error": None})
    contracts = [event.payload for event in rig.scheduler.control.pending.values() if event.kind == "contract"]
    assert len(contracts) == 1
    assert contracts[0].segment_magnitude <= cap + 1e-12


def test_new_registered_target_can_replace_old_intent_target():
    rig = SyntheticRig()
    scheduler = rig.scheduler
    new_identity = replace(rig.identity, target_track_id="other-visible-front",
                           feature_id="other-patch", target_track_generation=2, feature_generation=2)
    # A trusted synthetic validator certifies a newly observed target snapshot.
    # It does not certify lineage for any proposal referring to the old target.
    scheduler._latest = lambda t, n: _context(new_identity, rig.robot, "new-target-snapshot")
    scheduler.register_brain_request("retarget", source_snapshot_id="new-target-snapshot",
                                     deadline_monotonic_ns=1_000_000_000)
    intent = BrainIntent("retarget-intent", 1, "new-target-snapshot",
                         new_identity.target_track_id, 2, new_identity.feature_id, 2,
                         "APPROACH", "push", "fixture/constraint", "fixture/completion",
                         "p0-fixture-v1", 1_000_000_000, 5.)
    assert scheduler.install_intent(intent, request_id="retarget")
    assert scheduler.identity.target_track_id == new_identity.target_track_id
    assert scheduler.identity.feature_id == new_identity.feature_id
    assert scheduler.identity.intent_id == intent.intent_id
