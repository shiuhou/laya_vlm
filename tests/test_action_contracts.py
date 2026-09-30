from dataclasses import replace
from math import pi, sqrt

import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.control.action_catalog import ACTION_IDS
from embodied_runtime.control.action_contracts import (
    ActionProposal, EefPose, LayaRequest, ValidationContext,
    instantiate_contract, validate_proposal,
)
from embodied_runtime.control.local_candidates import ContextIdentity, HardEvidence, build_candidate_set


def setup(action="X+40"):
    identity = ContextIdentity("episode", 1, 1, "intent", 1, "front", 1, "patch", 1, ("camera-v1",))
    evidence = HardEvidence("ALLOWED", ("HARD_CONSTRAINTS_SATISFIED",), ("fixture",), "synthetic")
    pool = build_candidate_set(
        candidate_set_id="set", identity=identity, source_snapshot_id="snapshot-1",
        hard_evidence={action: evidence for action in ACTION_IDS},
        generated_monotonic_ns=0, proposal_deadline_monotonic_ns=1_200_000_000,
    )
    request = LayaRequest("request", pool, pool.proposal_deadline_monotonic_ns)
    proposal = ActionProposal(
        request.request_id, "decision", pool.candidate_set_id, pool.candidate_hash,
        identity, pool.source_snapshot_id, action,
        {action_id: 1.0 if action_id == action else 0.0 for action_id in ACTION_IDS},
        "fake-p0", 2.0,
    )
    latest = ValidationContext(
        identity, "snapshot-2", ("snapshot-1",), True, True, True,
        {action: "ALLOWED" for action in ACTION_IDS}, EefPose((.1, .2, .3), (0, 0, 0, 1)),
    )
    return request, proposal, latest


def contract(action="X+40", **kwargs):
    request, proposal, latest = setup(action)
    return instantiate_contract(
        request, proposal, latest=latest, contract_id="contract", now_sim_time_s=3.0,
        now_monotonic_ns=100_000_000, controller_config_id="fixture-control", **kwargs,
    )


def test_large_intent_authorizes_only_one_short_segment_with_explicit_remaining():
    c = contract()
    assert c.action_id == "X+40" and c.delta_position_m == (.005, 0, 0)
    assert c.target_eef_pose.position_m == pytest.approx((.105, .2, .3))
    assert c.requested_magnitude == .040
    assert c.remaining_requested_magnitude == pytest.approx(.035)
    assert c.nominal_completion_status == "PARTIAL"
    assert c.valid_until_sim_s - c.issued_sim_time_s == pytest.approx(.1)
    assert c.expires_monotonic_ns - c.issued_monotonic_ns == 100_000_000
    assert c.source_snapshot_id == "snapshot-1" and c.validated_snapshot_id == "snapshot-2"
    assert not hasattr(c, "continuation")


def test_contact_and_rotation_bounds():
    assert contract(contact=True).delta_position_m == (.002, 0, 0)
    assert contract(contact=True, contact_translation_limit_m=.001).delta_position_m == (.001, 0, 0)
    rotation = contract("RY-10")
    assert rotation.delta_rotation_rad == (0, -pi/90, 0)
    assert rotation.remaining_requested_magnitude == pytest.approx(pi/18-pi/90)
    assert rotation.magnitude_unit == "rad"
    with pytest.raises(ProtocolError):
        contract(contact=True, contact_translation_limit_m=.003)
    with pytest.raises(ProtocolError):
        contract(segment_duration_s=.101)


def test_stricter_config_caps_apply_to_translation_rotation_and_contact():
    small = contract(segment_translation_limit_m=.001)
    assert small.delta_position_m == (.001, 0, 0)
    assert small.remaining_requested_magnitude == pytest.approx(.039)
    assert contract(contact=True, segment_translation_limit_m=.0005).delta_position_m == (.0005, 0, 0)
    rotation = contract("RX+10", segment_rotation_limit_rad=pi/360)
    assert rotation.delta_rotation_rad == (pi/360, 0, 0)
    assert rotation.remaining_requested_magnitude == pytest.approx(pi/18-pi/360)


@pytest.mark.parametrize("kwargs", [
    {"segment_translation_limit_m": .006}, {"segment_translation_limit_m": 0},
    {"segment_rotation_limit_rad": pi/89}, {"segment_rotation_limit_rad": -1},
    {"segment_translation_limit_m": float("nan")}, {"segment_rotation_limit_rad": float("inf")},
])
def test_config_cannot_weaken_protocol_caps(kwargs):
    with pytest.raises(ProtocolError):
        contract(**kwargs)


def test_same_first_segment_keeps_distinct_nominal_action_identity():
    short, long = contract("X+10"), contract("X+40")
    assert short.delta_position_m == long.delta_position_m
    assert short.action_id != long.action_id
    assert short.remaining_requested_magnitude != long.remaining_requested_magnitude
    assert contract("X+03").nominal_completion_status == "COMPLETED"


@pytest.mark.parametrize("action,grip", [("OPEN", "OPEN"), ("CLOSE", "CLOSE"), ("HOLD", "KEEP"), ("X-40", "KEEP"), ("RX+10", "KEEP")])
def test_grip_commands_are_explicit_and_hold_retains(action, grip):
    c = contract(action)
    assert c.gripper_command == grip
    if action in ("OPEN", "CLOSE", "HOLD"):
        assert c.delta_position_m == c.delta_rotation_rad == (0, 0, 0)
        assert c.target_eef_pose == EefPose((.1, .2, .3), (0, 0, 0, 1))


def test_base_frame_rotation_left_multiplies_existing_pose():
    request, proposal, latest = setup("RX+10")
    latest = replace(latest, measured_eef_pose=EefPose((0, 0, 0), (0, 0, 1/sqrt(2), 1/sqrt(2))))
    c = instantiate_contract(request, proposal, latest=latest, contract_id="c", now_sim_time_s=0,
                             now_monotonic_ns=100, controller_config_id="controller")
    # R_x(base) * R_z(90) has negative quaternion y; reversed order has positive y.
    assert c.target_eef_pose.quaternion_xyzw[1] < 0


@pytest.mark.parametrize("field,value", [
    ("request_id", "another-request"), ("candidate_set_id", "another-pool"),
    ("candidate_hash", "bad-hash"), ("source_snapshot_id", "another-source"),
    ("selected_action_id", "0"),
])
def test_invalid_proposal_identity_or_action_is_rejected(field, value):
    request, proposal, _ = setup()
    with pytest.raises(ProtocolError):
        validate_proposal(request, replace(proposal, **{field: value}), now_monotonic_ns=100)


@pytest.mark.parametrize("probabilities", [
    {"X+40": 1.0},
    {**dict.fromkeys(ACTION_IDS, 0), "X+40": .9},
    {**dict.fromkeys(ACTION_IDS, 0), "X+40": 1.0, "UNKNOWN": 0.0},
])
def test_distribution_must_cover_legal_options_and_normalize(probabilities):
    request, proposal, _ = setup()
    with pytest.raises(ProtocolError):
        validate_proposal(request, replace(proposal, probabilities_by_action=probabilities), now_monotonic_ns=100)


@pytest.mark.parametrize("value", [-.1, float("nan"), float("inf")])
def test_invalid_probability_is_rejected_on_construction(value):
    _, proposal, _ = setup()
    with pytest.raises(ProtocolError):
        replace(proposal, probabilities_by_action={"X+40": value})


def test_proposal_deadline_inherited_and_expiry_is_inclusive():
    request, proposal, latest = setup()
    with pytest.raises(ProtocolError):
        replace(request, deadline_monotonic_ns=request.deadline_monotonic_ns + 1)
    with pytest.raises(ProtocolError):
        validate_proposal(request, proposal, now_monotonic_ns=request.deadline_monotonic_ns)
    now = request.deadline_monotonic_ns - 10_000_000
    c = instantiate_contract(request, proposal, latest=latest, contract_id="c", now_sim_time_s=0,
                             now_monotonic_ns=now, controller_config_id="controller")
    assert c.expires_monotonic_ns == request.deadline_monotonic_ns
    assert c.valid_until_sim_s == pytest.approx(.01)
    assert c.expired(sim_time_s=.01, monotonic_ns=now)
    assert c.expired(sim_time_s=0, monotonic_ns=request.deadline_monotonic_ns)


@pytest.mark.parametrize("field,value", [
    ("lineage_source_ids", ()), ("geometry_valid", False), ("proprio_valid", False),
    ("semantics_unchanged", False), ("action_statuses", {"X+40": "UNKNOWN"}),
])
def test_latest_snapshot_requires_valid_lineage_and_hard_constraints(field, value):
    request, proposal, latest = setup()
    with pytest.raises(ProtocolError):
        instantiate_contract(request, proposal, latest=replace(latest, **{field: value}), contract_id="c",
                             now_sim_time_s=0, now_monotonic_ns=100, controller_config_id="controller")


@pytest.mark.parametrize("field,value", [
    ("episode_generation", 2), ("goal_generation", 2), ("intent_generation", 2),
    ("target_track_generation", 2), ("feature_generation", 2),
    ("calibration_versions", ("camera-v2",)),
])
def test_generation_or_calibration_change_cannot_rebind(field, value):
    request, proposal, latest = setup()
    changed = replace(latest, identity=replace(latest.identity, **{field: value}))
    with pytest.raises(ProtocolError):
        instantiate_contract(request, proposal, latest=changed, contract_id="c", now_sim_time_s=0,
                             now_monotonic_ns=100, controller_config_id="controller")


def test_missing_current_action_status_does_not_fall_back_to_original_allowed():
    request, proposal, latest = setup()
    with pytest.raises(ProtocolError):
        instantiate_contract(request, proposal, latest=replace(latest, action_statuses={}), contract_id="c",
                             now_sim_time_s=0, now_monotonic_ns=100, controller_config_id="controller")


@pytest.mark.parametrize("changes", [
    {"delta_position_m": (-.005, 0, 0)},
    {"delta_position_m": (0, .005, 0)},
    {"delta_position_m": (.040, 0, 0)},
    {"delta_rotation_rad": (.001, 0, 0)},
    {"gripper_command": "OPEN"},
    {"reference_frame": "world"},
    {"remaining_requested_magnitude": 0},
    {"valid_until_sim_s": 5.0},
])
def test_contract_itself_rejects_semantic_tampering(changes):
    with pytest.raises(ProtocolError):
        replace(contract(), **changes)
