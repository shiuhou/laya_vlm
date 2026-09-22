import numpy as np
import pytest

from embodied_runtime import BeliefSnapshot, Candidate, LayaProvider, RuleProvider
from embodied_runtime.adapters.physics_preview import VisionCandidateBuilder


def snapshot(*, valid=True, semantic_valid=True, holding=None, covariance_source="provided"):
    return BeliefSnapshot(
        "ep", 7, 1.0,
        {
            "vision:drawer:position_world_m": [0.2, 0.0, 1.0],
            "vision:drawer:covariance": np.eye(3).tolist(),
            "tcp_pos_world_m": [0.0, 0.0, 1.0],
            "gripper_width_m": 0.08,
            "holding": holding,
        },
        {"drawer": {"drawer": .9, "unknown": .1}},
        {"satisfied": False},
        validity={"drawer": {
            "geometry_valid": valid,
            "geometry_invalid_reasons": [] if valid else ["geometry_too_old"],
            "geometry_age_s": 0.1 if valid else 1.0,
            "position_covariance": (np.eye(3) * .001).tolist(),
            "covariance_summary": {"position_trace_m2": .003},
            "semantic_valid": semantic_valid,
            "semantic_age_s": 0.1,
            "temporal_consistency_ok": valid and semantic_valid,
            "semantic_valid_until_sim": 2.0,
            "provenance": [{"position_covariance_source": covariance_source}],
        }},
        temporal_config={"version": "test"},
    )


def by_token(candidates):
    return {candidate.token: candidate for candidate in candidates}


def test_visual_candidates_use_hard_validity_and_keep_direction_as_soft_evidence():
    builder = VisionCandidateBuilder(target_track="drawer")
    candidates = by_token(builder.build(snapshot()))
    assert all(candidates[token].feasible for token in ("MV_FWD", "MV_BACK", "ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP"))
    assert not candidates["RELEASE"].feasible
    assert candidates["RELEASE"].reason_codes == ("holding_state_unknown",)
    assert candidates["MV_FWD"].metadata["moves_toward_target"]
    assert candidates["MV_BACK"].metadata["moves_toward_target"] is False
    assert candidates["MV_FWD"].metadata["decision_evidence_available"]
    assert builder.last_diagnostics["privileged_state_used"] is False
    assert builder.last_diagnostics["tracking_active"] is False
    assert builder.last_diagnostics["candidate_veto_count"] == 1


def test_stale_geometry_gates_precision_actions_but_retains_safe_stop():
    builder = VisionCandidateBuilder(target_track="drawer")
    candidates = by_token(builder.build(snapshot(valid=False)))
    assert all(not candidates[token].feasible for token in ("MV_FWD", "MV_BACK", "MV_LEFT", "MV_RIGHT", "MV_UP", "MV_DOWN", "ROTATE_CW", "ROTATE_CCW", "GRASP"))
    assert candidates["STOP"].feasible
    assert "geometry_too_old" in candidates["MV_FWD"].reason_codes
    assert builder.last_diagnostics["geometry_usable"] is False


def test_unverified_covariance_can_be_used_but_remains_soft_provenance():
    belief = snapshot()
    belief = BeliefSnapshot(**{**belief.__dict__, "validity": {
        "drawer": {**belief.validity["drawer"], "geometry_valid": False,
                    "geometry_invalid_reasons": ["measurement_covariance_unverified"]}}})
    builder = VisionCandidateBuilder(target_track="drawer", allow_unverified_covariance=True)
    candidates = by_token(builder.build(belief))
    assert candidates["MV_FWD"].feasible
    assert candidates["MV_FWD"].metadata["position_covariance_trace_m2"] == .003
    assert builder.last_diagnostics["geometry_reasons"] == []


def test_rule_and_laya_receive_identical_snapshot_and_candidate_identity():
    builder = VisionCandidateBuilder(target_track="drawer")
    belief = snapshot()
    candidates = builder.build(belief)
    matched = BeliefSnapshot(**{**belief.__dict__, "candidates": candidates})
    observed = {}

    class Agent:
        def system_one(self, state, questions):
            observed.update(state)
            return {"answers": {"action": {"choice": "STOP", "confidence": .5}}}

    rule_decision = RuleProvider().decide(matched)
    laya_decision = LayaProvider(Agent()).decide(matched)
    assert rule_decision.input_belief_id == laya_decision.input_belief_id == matched.belief_id()
    assert rule_decision.candidate_set_id == laya_decision.candidate_set_id == matched.candidate_set_id()
    assert rule_decision.input_snapshot_id == laya_decision.input_snapshot_id == matched.snapshot_id()
    assert observed["belief_id"] == matched.belief_id()
    assert observed["candidate_set_id"] == matched.candidate_set_id()
    assert observed["snapshot_id"] == matched.snapshot_id()
    assert observed["candidate_tokens"] == [candidate.token for candidate in candidates if candidate.feasible]


def test_candidate_hash_changes_when_feasible_set_or_soft_metadata_changes():
    builder = VisionCandidateBuilder(target_track="drawer")
    base = snapshot()
    first = BeliefSnapshot(**{**base.__dict__, "candidates": builder.build(base)})
    second_candidates = tuple(Candidate(candidate.token, candidate.description,
                                        candidate.feasible, candidate.reason_codes,
                                        candidate.risk, {**candidate.metadata, "extra": 1})
                             for candidate in first.candidates)
    second = BeliefSnapshot(**{**base.__dict__, "candidates": second_candidates})
    assert first.belief_id() == second.belief_id()
    assert first.candidate_set_id() != second.candidate_set_id()
    assert first.snapshot_id() != second.snapshot_id()


def test_workspace_gripper_and_target_constraints_do_not_choose_policy():
    base = snapshot()
    builder = VisionCandidateBuilder(target_track="drawer", workspace_bounds_m=((-1, 0), (-1, 1), (0, 2)))
    candidates = by_token(builder.build(base))
    assert candidates["MV_FWD"].reason_codes == ("workspace_limit",)
    assert candidates["MV_BACK"].feasible  # away remains allowed
    closed = BeliefSnapshot(**{**base.__dict__, "continuous": {**base.continuous,
                           "gripper_width_m": .02, "gripper_command": "CLOSED"}})
    candidates = by_token(builder.build(closed))
    assert candidates["RELEASE"].feasible
    assert "gripper_already_closed" in candidates["GRASP"].reason_codes
    wrong_target = by_token(VisionCandidateBuilder(target_track="other").build(base))
    assert not wrong_target["MV_FWD"].feasible
    assert "geometry_missing" in wrong_target["MV_FWD"].reason_codes
    leaking = BeliefSnapshot(**{**base.__dict__, "continuous": {**base.continuous, "hidden_object_xyz": [0, 0, 0]}})
    with pytest.raises(ValueError, match="privileged"):
        builder.build(leaking)


def test_laya_singleton_is_explicit_forced_choice_without_model_call():
    class Agent:
        def system_one(self, *_):
            raise AssertionError("singleton must not call model topk(2)")
    belief = snapshot(valid=False)
    candidates = VisionCandidateBuilder(target_track="drawer").build(belief)
    belief = BeliefSnapshot(**{**belief.__dict__, "candidates": candidates})
    assert belief.allowed() == {"STOP"}
    decision = LayaProvider(Agent()).decide(belief)
    assert decision.token == "STOP"
    assert decision.source == "laya_single_candidate"
    assert decision.latency_ms == 0
    assert decision.input_snapshot_id == belief.snapshot_id()
