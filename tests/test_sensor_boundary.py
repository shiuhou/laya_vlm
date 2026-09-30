from dataclasses import asdict, replace

import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.evaluation import EvaluationRecord, IndependentEvaluator
from embodied_runtime.policy_observation import PolicyObservation
from embodied_runtime.sensor_api import Proprioception, SensorBackend, SensorPort


def proprio(**changes):
    return Proprioception.from_mapping({
        "capture_sim_time_s": 1.0, "capture_monotonic_ns": 1_000_000_000,
        "eef_position_base_m": [0.1, 0.2, 0.3], "eef_quaternion_xyzw": [0, 0, 0, 1],
        "joint_position_rad": [0, 0, 0, 0, 0, 0, 0], "gripper_width_m": .04,
        "gripper_width_calibration_id": "jaw-calibration-fixture-v1", "valid": True,
        "source_ids": ["robot-fixture-1"], **changes,
    })


def policy_input():
    return {"source_snapshot_id": "snapshot-1", "proprio": proprio().to_dict(),
            "stage": "APPROACH", "operation": "push_visible_front",
            "relative_error": [.01, 0, 0], "geometry_age": .05}


@pytest.mark.parametrize("field,value", [
    ("target_body_pose", [1, 2, 3]), ("contacts", []), ("official_success", True),
    ("holding", True), ("tcp_pos_world_m", [0, 0, 0]), ("joint_axis", [1, 0, 0]),
    ("provenance", "simulator_oracle"), ("frame", "world"),
])
def test_proprio_whitelist_rejects_hidden_world_and_unknown_fields(field, value):
    with pytest.raises(ProtocolError):
        proprio(**{field: value})


def test_width_is_measured_and_calibrated_separately_from_retained_command():
    p = proprio(gripper_command="CLOSE", gripper_width_m=None,
                gripper_width_calibration_id=None, reason_codes=["WIDTH_UNCALIBRATED"])
    assert p.gripper_width_m is None and p.holding is None
    assert p.gripper_command == "CLOSE"
    with pytest.raises(ProtocolError):
        proprio(gripper_width_calibration_id=None)
    with pytest.raises(ProtocolError):
        proprio(gripper_width_m=None)
    with pytest.raises(ProtocolError):
        proprio(eef_quaternion_xyzw=[0, 0, 0, 2])
    invalid = proprio(valid=False, eef_position_base_m=None, eef_quaternion_xyzw=None,
                      joint_position_rad=None, reason_codes=["ROBOT_SENSOR_INVALID"])
    assert invalid.eef_position_base_m is None


def test_proprio_is_deeply_immutable_and_fk_requires_robot_identity():
    values = [0, 0, 0]
    p = proprio(eef_position_base_m=values)
    values[0] = 10
    assert p.eef_position_base_m == (0, 0, 0)
    with pytest.raises(ProtocolError):
        proprio(eef_pose_source="robot_fk")
    assert proprio(eef_pose_source="robot_fk", robot_model_id="fixture").robot_model_id == "fixture"


def test_restricted_backend_does_not_touch_truth_and_hold_retains_command():
    class BackendSpy:
        def __init__(self):
            self.grip = "OPEN"
            self.commands = []

        def read(self):
            return proprio(gripper_command=self.grip)

        def command(self, position, rotation, grip, dt):
            if grip != "KEEP":
                self.grip = grip
            self.commands.append((position, rotation, self.grip, dt))

        def hold(self):
            self.commands.append(((0, 0, 0), (0, 0, 0), self.grip, 0))

        def __getattr__(self, name):
            raise AssertionError(f"forbidden simulator access: {name}")

    spy = BackendSpy()
    port = SensorPort(read=spy.read, command=spy.command, hold=spy.hold, close=lambda: None)
    assert isinstance(port, SensorBackend)
    for name in ("world", "success", "features", "predict_all", "contacts"):
        assert not hasattr(port, name)
    port.command_tick((0, 0, 0), (0, 0, 0), "CLOSE", .05)
    port.command_tick((.001, 0, 0), (0, 0, 0), "KEEP", .05)
    port.hold()
    assert port.read_proprioception().gripper_command == "CLOSE"
    assert all(command[2] == "CLOSE" for command in spy.commands)
    with pytest.raises(ProtocolError):
        port.command_tick((0, 0, 0), (0, 0, 0), "GRASP", .05)
    with pytest.raises(ProtocolError):
        port.command_tick((0, 0, 0), (0, 0, 0), "KEEP", .2)


@pytest.mark.parametrize("injection", [
    {"official_success": True}, {"goal": {"satisfied": True}}, {"oracle_state": {}},
    {"unlisted_extra": 1}, {"quality": {"oracle_joint": .01}},
    {"proprio": {**proprio().to_dict(), "holding": True}},
    {"recent_feedback": {"success": True}},
])
def test_policy_rejects_oracle_or_unlisted_fields(injection):
    with pytest.raises(ProtocolError):
        PolicyObservation.from_mapping({**policy_input(), **injection})


def test_policy_rejects_oracle_effect_even_if_labeled_candidate():
    candidate = {"id": "X+03", "reference_frame": "robot_base",
                 "geometric_effect_estimate": {"effect_source": "oracle_sim"}}
    with pytest.raises(ProtocolError):
        PolicyObservation.from_mapping({**policy_input(), "candidates": [candidate]})


def test_policy_copy_is_immutable_and_calibration_not_guessed():
    source = policy_input()
    source["quality"] = {"calibrated_confidence": None, "status": "TRACKED"}
    policy = PolicyObservation.from_mapping(source)
    source["relative_error"][0] = 10
    assert policy.to_dict()["relative_error"] == [.01, 0, 0]
    with pytest.raises(TypeError):
        policy.payload["proprio"]["holding"] = True
    with pytest.raises(ProtocolError):
        PolicyObservation.from_mapping({**policy_input(), "quality": {"calibrated_confidence": 1}})


def test_official_success_only_changes_evaluator_record_and_scheduler_stop():
    truth = {"success": False}
    records, stops = [], []
    evaluator = IndependentEvaluator(check_success=lambda: truth["success"], record_sink=records.append,
                                     on_stop=stops.append, evaluator_revision="fixture-v1")
    before = PolicyObservation.from_mapping(policy_input()).to_dict()
    for i in range(2):
        truth["success"] = bool(i)
        evaluator.evaluate(evaluation_id=f"eval-{i}", episode_id="episode-1", episode_generation=0,
                           reference_sim_time_s=i, evaluated_monotonic_ns=i)
    after = PolicyObservation.from_mapping(policy_input()).to_dict()
    assert before == after
    assert [record.official_success for record in records] == [False, True]
    assert len(stops) == 1 and stops[0].evaluation_id == "eval-1"
    with pytest.raises(ProtocolError):
        PolicyObservation.from_mapping({**policy_input(), **asdict(records[1])})
    with pytest.raises(ProtocolError):
        replace(records[1], provenance="sensor-derived")
    assert isinstance(records[1], EvaluationRecord)


def test_candidate_projection_keeps_all_actions_and_full_raw_hash_evidence():
    from embodied_runtime.control.action_catalog import ACTION_IDS
    from embodied_runtime.control.local_candidates import ContextIdentity, HardEvidence, build_candidate_set
    from embodied_runtime.policy_observation import project_candidate

    allow = HardEvidence("ALLOWED", ("HARD_CONSTRAINTS_SATISFIED",), ("fixture",), "synthetic")
    pool = build_candidate_set(candidate_set_id="pool", source_snapshot_id="snapshot-1",
                              identity=ContextIdentity("ep", 0, 0, "intent", 0, "front", 0, "patch", 0, ("cal",)),
                              hard_evidence={action: allow for action in ACTION_IDS},
                              generated_monotonic_ns=0, proposal_deadline_monotonic_ns=10)
    before_hash = pool.candidate_hash
    with pytest.raises(ProtocolError):
        project_candidate(pool.candidates[0])
    presented = [project_candidate(candidate, synthetic_condition=True) for candidate in pool.candidates]
    state = PolicyObservation.from_mapping({**policy_input(), "candidates": presented}).to_dict()
    assert tuple(c["id"] for c in state["candidates"]) == ACTION_IDS
    assert next(c for c in state["candidates"] if c["id"] == "CLOSE")["gripper_command"] == "CLOSE"
    assert all("hard_evidence" not in candidate for candidate in state["candidates"])
    assert all(c.to_dict()["hard_evidence"]["provenance"] == "synthetic" for c in pool.candidates)
    assert before_hash == pool.candidate_hash


@pytest.mark.parametrize("update", [
    {"relative_error": {"hidden_pose": [1, 2, 3]}},
    {"geometry_age": -1}, {"covariance_summary": {"source": "oracle_sim"}},
    {"quality": {"support_ratio": {"official_success": True}}},
    {"stage": "CLOSE_BY_ORACLE"}, {"intent_generation": True},
])
def test_policy_rejects_wrong_shapes_and_disguised_truth(update):
    with pytest.raises(ProtocolError):
        PolicyObservation.from_mapping({**policy_input(), **update})
