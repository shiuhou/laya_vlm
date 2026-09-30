from dataclasses import replace

import pytest

from embodied_runtime.contracts import ProtocolError, StageEvidence
from embodied_runtime.experiments.p0_contract_probe import SyntheticRig, fake_choose, fake_choose_wire
from embodied_runtime.workers import ControlEvent, ReliableEvents


def ready(action="X+40", **kwargs):
    rig = SyntheticRig(**kwargs)
    rig.install_intent()
    request, payload = rig.request()
    result = dict(request_id=request.request_id, output=fake_choose(payload, action_id=action), error=None)
    return rig, result


def test_complete_projection_full_pool_and_one_segment_no_implicit_continuation():
    rig, result = ready()
    model = next(e["payload"] for e in rig.events if e["kind"] == "model_input")
    assert len(model["candidates"]) == 27
    assert all(c["execution_status"] == "ALLOWED" for c in model["candidates"])
    assert rig.scheduler.receive_model_result(result)
    rig.tick(0., 0)
    feedback = rig.tick(.05, 50_000_000)
    assert feedback.status == "PARTIAL"
    assert feedback.remaining_requested_magnitude == pytest.approx(.035)
    assert feedback.measured_eef_delta_m == pytest.approx((.005,0,0))
    assert not rig.scheduler.receive_model_result(result)
    for i in range(2, 8):
        rig.tick(i*.05, i*50_000_000)
    assert len(rig.robot.commands) == 2
    assert rig.scheduler.servo.active is None
    result["output"]["decision_id"] = "a-new-id-for-consumed-request"
    assert not rig.scheduler.receive_model_result(result)
    assert rig.scheduler.rejections[-1].reason_code == "REQUEST_CONSUMED"


@pytest.mark.parametrize("failure", ["hash", "id", "probabilities", "error", "nan"])
def test_invalid_model_reply_rejects_before_motion(failure):
    rig, result = ready()
    if failure == "hash":
        result["output"]["candidate_hash"] = "wrong"
    elif failure == "id":
        result["output"]["selected_action_id"] = "1"
    elif failure == "probabilities":
        result["output"]["probabilities_by_action"] = {"X+40": .5}
    elif failure == "error":
        result["error"] = "fake model failure"
    else:
        result["output"]["inference_ms"] = float("nan")
    assert not rig.scheduler.receive_model_result(result)
    rig.tick(0.,0)
    assert not rig.robot.commands


def test_cancel_revokes_active_and_queued_contract_before_next_tick():
    rig, result = ready()
    assert rig.scheduler.receive_model_result(result)
    rig.tick(0.,0)
    rig.scheduler.cancel(event_id="stop/1")
    assert rig.scheduler.servo.active is None
    rig.identity = replace(rig.identity, goal_generation=rig.scheduler.identity.goal_generation)
    rig.router.goal_generation = rig.identity.goal_generation
    rig.tick(.05,50_000_000)
    assert len(rig.robot.commands) == 1
    assert not rig.scheduler.receive_model_result(result)
    assert rig.scheduler.servo.feedback[-1].status == "ABORTED"


@pytest.mark.parametrize("what", ["geometry", "semantics", "target", "calibration", "blocked"])
def test_latest_each_tick_can_abort_without_action_substitution(what):
    rig, result = ready()
    assert rig.scheduler.receive_model_result(result)
    rig.tick(0.,0)
    if what == "geometry":
        rig.geometry_valid = False
    elif what == "semantics":
        rig.semantics_unchanged = False
    elif what == "target":
        rig.identity = replace(rig.identity, target_track_generation=2)
    elif what == "calibration":
        rig.identity = replace(rig.identity, calibration_versions=("cal2",))
    else:
        rig.statuses["X+40"] = "BLOCKED"
    result = rig.tick(.05,50_000_000)
    assert result.status == "ABORTED"
    assert len(rig.robot.commands) == 1


def test_no_refresh_stale_geometry_blocks_proposal_even_with_live_deadline():
    rig, result = ready()
    rig.tick(.35,350_000_000,refresh=False)
    assert not rig.scheduler.receive_model_result(result)
    assert not rig.robot.commands


def test_stage_evidence_unknown_keeps_intent_satisfied_only_requests_new_intent():
    rig, _ = ready()
    intent = rig.scheduler.intent
    source = rig.store.read_snapshot()["snapshot_id"]
    evidence = StageEvidence(intent.intent_id, intent.stage, (source,), intent.completion_template_id,
                             "UNKNOWN", {"gap_m":None}, "fixture-v1")
    rig.scheduler.apply_stage_evidence(evidence)
    assert rig.scheduler.intent is intent
    rig.scheduler.apply_stage_evidence(replace(evidence, result="SATISFIED"))
    assert rig.scheduler.intent is None
    assert not rig.robot.commands


def test_episode_budget_counts_hold_ticks():
    rig = SyntheticRig()
    rig.tick(0.,0)
    rig.tick(60.,1_000_000_000)
    assert rig.scheduler.halted and rig.scheduler.stop_reason == "EPISODE_BUDGET"
    assert not rig.robot.commands


def test_control_capacity_ack_deadline_idempotence_and_conflict():
    failures = []
    control = ReliableEvents(capacity=1, on_failure=failures.append)
    e = ControlEvent("c", "cancel", {"reason":"STOP"}, 100)
    assert control.send(e)
    assert not control.send(e)
    with pytest.raises(ProtocolError, match="CONTROL_OVERFLOW"):
        control.send(replace(e,event_id="other"))
    with pytest.raises(ProtocolError, match="CONTROL_ACK_TIMEOUT"):
        control.check(100)
    control.ack("c")
    assert not control.pending
    assert not control.send(e)
    with pytest.raises(ProtocolError, match="CONTROL_ID_CONFLICT"):
        control.send(replace(e, payload={"reason":"DIFFERENT"}))
    assert failures == ["CONTROL_OVERFLOW", "CONTROL_ACK_TIMEOUT", "CONTROL_ID_CONFLICT"]


def test_control_failure_aborts_active_motion():
    rig, result = ready()
    rig.scheduler.receive_model_result(result)
    rig.tick(0.,0)
    rig.scheduler.control.send(ControlEvent("no-ack", "cancel", {}, 20_000_000))
    rig.tick(.05,50_000_000)
    assert rig.scheduler.halted
    assert len(rig.robot.commands) == 1


def test_new_observed_target_can_install_without_validating_as_old_target():
    rig, _ = ready()
    s = rig.scheduler
    source = rig.store.read_snapshot()["snapshot_id"]
    s.register_brain_request("retarget", source_snapshot_id=source, deadline_monotonic_ns=1_000_000_000)
    original = rig.latest
    def resolve(identity, sim, mono):
        context = original(sim,mono)
        return replace(context, identity=replace(context.identity, target_track_id=identity.target_track_id,
                                                feature_id=identity.feature_id))
    s._target_context = resolve  # Explicit synthetic registered-target resolver.
    intent = replace(s.intent, intent_id="intent/new",intent_generation=2,
                     target_track_id="another-observed-target", feature_id="another-observed-patch",
                     expires_monotonic_ns=1_000_000_000)
    assert s.install_intent(intent,request_id="retarget")
    assert s.identity.target_track_id == "another-observed-target"


def test_stricter_config_limits_reach_executor():
    rig = SyntheticRig()
    config = {**rig.config, "segment_translation_m":.001}
    rig, result = ready(config=config)
    assert rig.scheduler.receive_model_result(result)
    rig.tick(0.,0)
    rig.tick(.05,50_000_000)
    assert rig.robot.position[0] == pytest.approx(.001)


def test_wire_reply_identity_check_and_old_result_after_reset():
    rig = SyntheticRig()
    rig.install_intent()
    _, payload = rig.wire_request()
    output = fake_choose_wire(payload)
    bad = replace(output,clock_domain="other-host")
    result = {"request_id":output.payload["request_id"],"output":bad,"error":None}
    assert not rig.receive_wire_result(result)
    assert rig.scheduler.rejections[-1].reason_code == "CLOCK_DOMAIN_MISMATCH"
    new_identity = replace(rig.identity, episode_id="episode/new", episode_generation=2)
    rig.scheduler.reset(new_identity)
    result["output"] = output
    # Even bypassing router for a delivered old process result cannot revive it.
    assert not rig.scheduler.receive_model_result(result)
    assert not rig.robot.commands and rig.scheduler.servo.active is None
    assert rig.scheduler.rejections[-1].reason_code == "REQUEST_CANCELLED"


def test_model_cannot_claim_calibrated_confidence_without_registered_calibration():
    rig, result = ready()
    result["output"]["calibrated_confidence"] = .99
    assert not rig.scheduler.receive_model_result(result)
    assert rig.scheduler.rejections[-1].reason_code == "UNCALIBRATED_CONFIDENCE"


@pytest.mark.parametrize("field,value", [("constraint_template_id","invented"),
                                         ("completion_template_id","oracle-success"),
                                         ("operation","x+40 recipe"),
                                         ("policy_config_revision","other")])
def test_brain_can_only_use_registered_templates(field,value):
    rig, _ = ready()
    s = rig.scheduler
    source = rig.store.read_snapshot()["snapshot_id"]
    s.register_brain_request("new-brain",source_snapshot_id=source,deadline_monotonic_ns=1_000_000_000)
    intent = replace(s.intent,intent_id="new-intent",intent_generation=2,expires_monotonic_ns=1_000_000_000,
                     **{field:value})
    old = s.intent
    assert not s.install_intent(intent,request_id="new-brain")
    assert s.intent is old
