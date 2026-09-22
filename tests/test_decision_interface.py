from copy import deepcopy
from dataclasses import asdict, replace
from types import SimpleNamespace
import sys

import numpy as np
import pytest

from embodied_runtime.decision_interface import (
    CanonicalDecisionInput, CanonicalDecisionState, CandidateEffectBundle, Evidence,
    candidate_id, geometric_effects, oracle_effects, project_belief, project_oracle, shared_atomic_candidates,
)
from embodied_runtime.experiments.equivalence import compare_decisions, make_pair, paired_inputs, replay_pair
from embodied_runtime.experiments.records import RunRecorder, load_records
from embodied_runtime.runtime_core import BeliefSnapshot, LayaProvider, RuleProvider, _sha256_json


def belief():
    return BeliefSnapshot("ep", 2, .5, {"tcp_pos_world_m": [0., 0., 1.], "gripper_width_m": .08,
        "gripper_command": "OPEN", "holding": None, "vision:drawer:position_world_m": [.2, 0., 1.],
        "vision:drawer:velocity_mps": [0., 0., 0.]}, {"drawer": {"drawer": .9, "unknown": .1}},
        {"instruction": "close drawer"}, validity={"drawer": {"geometry_valid": True, "geometry_age_s": .1,
        "position_covariance": (np.eye(3) * .001).tolist(), "semantic_valid": True, "semantic_age_s": .1,
        "temporal_consistency_ok": True, "provenance": [{"position_world_m": [.2, 0, 1], "position_covariance_calibrated": False}]}})


def states():
    p = project_belief(belief(), "drawer")
    o = project_oracle(p, {"source_id": "physical", "target_position_m": [-.2, 0, 1],
                           "position_definition": "moving_collision_geometry_world_aabb_center",
                           "moving_contact": False, "remaining_open_mm": 150})
    return o, p


def pair():
    o, p = states()
    return make_pair(o, p, shared_atomic_candidates(), physical={"sim_time": .5, "physical_state_id": "physical",
                     "task": "top_drawer", "init_state_id": 0, "seed": 1}, history=())


def test_projection_unknown_relations_provenance_and_no_mutation():
    b = belief()
    before = b.belief_id()
    o, p = states()
    assert project_belief(b, "drawer").identity() == p.identity()
    assert b.belief_id() == before
    assert p.fields["relations.distance_m"].value == .2
    assert p.fields["relations.height_error_m"].value == 0
    assert p.fields["interaction.target_contact"].value is None
    assert p.fields["progress.remaining_open_mm"].source == "unknown"
    assert p.fields["target.visible_now"].value is None
    assert p.fields["quality.covariance_calibrated"].value is False
    assert not p.privileged and o.privileged
    assert o.fields["progress.remaining_open_mm"].source == "oracle_sim"
    assert o.fields["quality.position_covariance_m2"].value is None
    assert o.fields["relations.distance_m"].privileged
    assert CanonicalDecisionState.from_dict(asdict(p)).identity() == p.identity()
    polluted = replace(b, continuous={**b.continuous, "remaining_open_mm": 150})
    with pytest.raises(ValueError, match="privileged"):
        project_belief(polluted, "drawer")


def test_missing_geometry_stays_unknown_not_zero():
    p = project_belief(replace(belief(), continuous={}), "drawer")
    assert p.fields["target.position_m"].value is None
    assert p.fields["relations.distance_m"].value is None


def test_primary_pair_preserves_candidates_questions_history_effects():
    record = pair()
    a, b = paired_inputs(record)
    assert a.candidates is b.candidates
    assert a.effects is b.effects
    assert a.effects.effects == {}
    assert a.questions() == b.questions()
    assert a.history == b.history
    x, y = a.provider_input(), b.provider_input()
    x.pop("state")
    y.pop("state")
    assert x == y
    assert record["field_differences"]["target.position_m"]["status"] == "incomparable_definition"
    assert "difference_l2" not in record["field_differences"]["target.position_m"]
    assert record["field_differences"]["progress.remaining_open_mm"]["status"] == "missing"


def test_pair_alignment_and_integrity():
    o, p = states()
    with pytest.raises(ValueError, match="same physical"):
        make_pair(o, p, shared_atomic_candidates(), physical={"sim_time": 9})
    record = pair()
    record["shared_candidates"][0]["description"] = "different"
    with pytest.raises(ValueError, match="identity"):
        paired_inputs(record)


def test_effect_separation_privilege_and_nominal_prediction():
    o, p = states()
    cs = shared_atomic_candidates()
    geometry = geometric_effects(p, cs)
    assert geometry.effects["MV_FWD"]["values"]["distance_change_m"] == pytest.approx(-.01)
    assert geometry.effects["MV_BACK"]["values"]["distance_change_m"] == pytest.approx(.01)
    assert geometry.effects["GRASP"]["source"] == "unknown"
    assert not geometry.privileged
    oracle = oracle_effects(cs, {"x+10mm": {"closing_mm": 2, "after": {"moving_contact": True}}})
    assert oracle.privileged
    CanonicalDecisionInput(p, cs, geometry)
    with pytest.raises(ValueError, match="privileged"):
        CanonicalDecisionInput(p, cs, oracle)
    with pytest.raises(ValueError, match="privileged"):
        CanonicalDecisionInput(o, cs, geometry)
    diagnostic = CanonicalDecisionInput(p, cs, oracle, diagnostic_only=True)
    assert diagnostic.effects.effects["MV_FWD"]["source"] == "oracle_sim"
    assert geometric_effects(o, cs).privileged  # derived oracle taint propagates
    with pytest.raises(ValueError, match="different candidates"):
        CanonicalDecisionInput(p, cs, CandidateEffectBundle("wrong"))
    embedded = (replace(cs[0], metadata={"predicted_closing": 10}), *cs[1:])
    with pytest.raises(ValueError, match="embed"):
        CanonicalDecisionInput(p, embedded, CandidateEffectBundle(candidate_id(embedded)))
    privileged_text = (replace(cs[0], description=cs[0].description + "; predicted_closing_mm=20", risk=.4), *cs[1:])
    with pytest.raises(ValueError, match="semantics-only"):
        CanonicalDecisionInput(p, privileged_text, CandidateEffectBundle(candidate_id(privileged_text)))


def test_oracle_retains_shared_proprioception_and_missing_target_invalid():
    p = project_belief(replace(belief(), continuous={**belief().continuous, "holding": True}), "drawer")
    o = project_oracle(p, {"source_id": "physical"})
    assert o.fields["quality.geometry_valid"].value is False
    assert o.fields["interaction.holding"] == p.fields["interaction.holding"]


def test_named_field_intervention_changes_only_requested_field():
    o, p = states()
    out = o.intervene({"target.position_m": p.fields["target.position_m"]}, label="literal_position_only")
    assert out.fields["target.position_m"] == p.fields["target.position_m"]
    assert all(v == o.fields[k] for k, v in out.fields.items() if k != "target.position_m")
    assert out.meta["intervention"]["parent_id"] == o.identity()
    assert out.identity() != o.identity()
    with pytest.raises(ValueError):
        Evidence(1, "oracle_sim", privileged=False)


def test_same_provider_replay_and_stability_records(tmp_path):
    rec = RunRecorder(tmp_path / "run", {}, {"run_id": "test"})
    record = pair()
    rule = replay_pair(record, RuleProvider(), rec, repeats=3)
    assert rule["stability"]["oracle"]["unique_choices"] == ["MV_BACK"]
    assert rule["stability"]["perceptual"]["unique_choices"] == ["MV_FWD"]
    assert rule["stability"]["oracle"]["max_probability_difference"] == 0
    observed = []
    class Agent:
        def system_one(self, state, questions):
            observed.append(deepcopy((state, questions)))
            tokens = list(questions["action"]["criteria"])
            return {"answers": {"action": {"choice": "STOP", "probabilities": {k: float(k == "STOP") for k in tokens}}}}
    laya = replay_pair(record, LayaProvider(Agent()), rec, repeats=3)
    assert laya["stability"]["oracle"]["unique_choices"] == ["STOP"]
    assert observed[0] == observed[3] == observed[4]  # alternating branch order
    assert observed[0][1] == observed[1][1]
    rec.close()
    rows, _ = load_records(rec.output / "episodes.jsonl")
    decisions = [r for r in rows if r["kind"] == "equivalence_decision"]
    assert len(decisions) == 12
    for branch in ["oracle", "perceptual"]:
        assert len({r["data"]["model_input_id"] for r in decisions if r["data"]["branch"] == branch}) == 1


def test_missing_probabilities_not_fabricated_and_js_known_case():
    a, b = paired_inputs(pair())
    da, db = RuleProvider().decide(a), RuleProvider().decide(b)
    metrics = compare_decisions(da, db, sorted(a.allowed()))
    assert metrics["js_divergence_nats"] == pytest.approx(np.log(2))
    assert metrics["oracle_margin"] == 1
    assert metrics["top2_set_agreement"] is None  # ties among zero probabilities
    incomplete = replace(db, probabilities={})
    assert compare_decisions(da, incomplete, sorted(a.allowed()))["js_divergence_nats"] is None


def test_init_state_index_passed_to_libero(monkeypatch):
    from embodied_runtime.adapters.libero import LiberoWorldBackend
    captured = {}
    def world(**kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setitem(sys.modules, "jev_libero.world", SimpleNamespace(World=world))
    monkeypatch.setitem(sys.modules, "jev_libero.config", SimpleNamespace(load_task=lambda task: {}))
    LiberoWorldBackend.from_task(seed=9, init_state_id=3)
    assert captured["seed"] == 9 and captured["init_index"] == 3
    with pytest.raises(ValueError, match="nonnegative"):
        LiberoWorldBackend.from_task(init_state_id=-1)


def test_audit_ids_not_model_features_and_history_allowlist():
    a, _ = paired_inputs(pair())
    changed = replace(a, state=replace(a.state, meta={**a.state.meta, "secret_path": "/oracle/file"}))
    assert changed.snapshot_id() != a.snapshot_id()
    assert _sha256_json(changed.provider_input()) == _sha256_json(a.provider_input())
    with pytest.raises(ValueError, match="unsupported recent"):
        replace(a, history=({"source": "proprioception", "remaining_open_mm": 2},))


def test_compact_presentation_is_order_stable_and_full_audit_remains():
    import json
    a, _ = paired_inputs(pair())
    reversed_state = replace(a.state, fields=dict(reversed(list(a.state.fields.items()))))
    b = replace(a, state=reversed_state)
    assert json.dumps(a.provider_input()) == json.dumps(b.provider_input())
    assert "source" not in a.provider_input()["state"]
    assert "task.instruction" in a.provider_input()["state"]
    assert a.provider_input("audit-json-v0")["decision_state"]["fields"]["target.position_m"]["source"] == "oracle_sim"
    assert a.model_questions()["action"]["criteria"]["MV_UP"] != a.model_questions()["action"]["criteria"]["MV_DOWN"]


def test_laya_rejects_truncated_canonical_input_before_inference(monkeypatch):
    from embodied_runtime.adapters import laya_input
    monkeypatch.setattr(laya_input, "encoding_audit", lambda *args: {"available": True, "truncated": True})
    class Agent:
        def system_one(self, *_):
            raise AssertionError("truncated input must not reach model")
    with pytest.raises(ValueError, match="truncated"):
        LayaProvider(Agent()).decide(paired_inputs(pair())[0])
