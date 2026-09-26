from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pytest

from embodied_runtime.adapters.physics_preview import VisionCandidateBuilder
from embodied_runtime.decision_interface import CanonicalDecisionInput, CanonicalDecisionState, geometric_effects, project_belief, shared_atomic_candidates
from embodied_runtime.experiments import approach_selector_probe as probe
from embodied_runtime.experiments.records import jsonable
from embodied_runtime.runtime_core import BeliefSnapshot, MOVE


def source_fixture():
    belief = BeliefSnapshot("episode", 2, .5,
        {"tcp_pos_world_m": [0., 0., 1.], "gripper_width_m": .08, "gripper_command": "OPEN",
         "holding": None, "vision:drawer:position_world_m": [.2, .05, 1.03],
         "vision:drawer:velocity_mps": [0., 0., 0.]},
        {"drawer": {"drawer": .9, "unknown": .1}}, {"instruction": "close drawer"},
        validity={"drawer": {"geometry_valid": True, "geometry_age_s": .1,
            "position_covariance": (np.eye(3)*.001).tolist(), "semantic_valid": True,
            "semantic_age_s": .1, "temporal_consistency_ok": True,
            "provenance": [{"position_world_m": [.2, .05, 1.03], "position_covariance_calibrated": False}]}})
    builder = VisionCandidateBuilder(target_track="drawer", allow_unverified_covariance=True)
    return (asdict(project_belief(belief, "drawer")), [c.canonical() for c in builder.build(belief)],
            {"belief_id": belief.belief_id(), "snapshot": jsonable(asdict(belief))},
            {"target_query": "drawer", "natural_candidates": builder.resolved_config()},
            [{"action": "STOP", "tcp_delta_m": [0., 0., 0.], "elapsed_sim_s": .1,
              "gripper_command": "OPEN", "source": "proprioception"}],
            {"init_state_id": 0, "environment_step": 2, "source_path": "audit-only-path"})


def test_fixture_preserves_inputs_and_roundtrips_exactly():
    source = source_fixture()
    original = deepcopy(source)
    fixture = probe.make_fixture(*source)
    assert source == original
    assert json.loads(json.dumps(fixture)) == fixture
    assert fixture["option_order"] == [*MOVE, "ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP"]
    assert list(fixture["questions"]["action"]["criteria"]) == fixture["option_order"]
    assert fixture["source"]["natural_candidates"][-1]["reason_codes"] == ["holding_state_unknown"]
    assert fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] is None


@pytest.mark.parametrize("mutation", [
    lambda s: s[1][0].update(feasible=False),
    lambda s: s[1][0].update(reason_codes=["invented_gate"]),
    lambda s: s[1].reverse(),
    lambda s: s[3]["natural_candidates"].update(version="new-builder"),
    lambda s: s[0]["fields"]["relations.distance_m"].update(value=.001),
    lambda s: s[0]["fields"]["target.position_m"].update(privileged=True),
    lambda s: s[0]["meta"].update(branch="oracle"),
    lambda s: s[2].update(belief_id="wrong-belief"),
])
def test_mutated_gate_state_and_privilege_evidence_rejected(mutation):
    source = source_fixture()
    mutation(source)
    with pytest.raises(ValueError):
        probe.make_fixture(*source)


def test_compact_effects_preserve_every_presented_value_and_unknown():
    fixture = probe.make_fixture(*source_fixture())
    state = CanonicalDecisionState.from_dict(fixture["source"]["perceptual_state"])
    candidates = tuple(c for c in shared_atomic_candidates() if c.token in fixture["option_order"])
    canonical = CanonicalDecisionInput(state, candidates, geometric_effects(state, candidates))
    original = canonical.provider_input()["effects"]
    compact = fixture["state"]["effects"]
    assert list(compact["rows"]) == fixture["option_order"]
    for token, row in compact["rows"].items():
        if token in MOVE:
            assert row == [original[token]["values"][column] for column in compact["columns"]]
            assert compact["assumptions"] == original[token]["assumptions"]
        else:
            assert row is None and original[token]["source"] == "unknown"
    assert compact["privileged"] is False
    assert fixture["source"]["canonical"]["effects"]["effects"] == jsonable(asdict(canonical.effects))["effects"]
    assert fixture["source"]["rule_token"] == canonical.rule_token() == "MV_FWD"


def test_model_payload_excludes_rule_evaluator_and_lineage():
    fixture = probe.make_fixture(*source_fixture())
    model_state = fixture["state"]["state"]
    assert model_state["interaction.holding"] is None
    assert model_state["interaction.target_contact"] is None
    assert model_state["progress.remaining_open_mm"] is None
    assert fixture["questions"]["action"]["instructions"] == probe.APPROACH_INSTRUCTION
    serialized = json.dumps([fixture["state"], fixture["questions"]])
    assert all(key not in serialized for key in ("rule_token", "oracle_sim", "audit-only-path", "scored_expected_tokens"))


def test_oracle_evaluation_cannot_change_input_and_unknown_is_not_zero():
    fixture = probe.make_fixture(*source_fixture())
    before = deepcopy(fixture)
    positive = probe.evaluate_choice(fixture, "MV_FWD", [.2, .05, .03])
    negative = probe.evaluate_choice(fixture, "MV_FWD", [-.2, .05, .03])
    assert positive["selected_oracle_nominal_gain_mm"] > 0 > negative["selected_oracle_nominal_gain_mm"]
    assert positive["selected_sensor_gain_mm"] == negative["selected_sensor_gain_mm"]
    for token in ("GRASP", "STOP", "ROTATE_CW"):
        result = probe.evaluate_choice(fixture, token, [.2, .05, .03])
        assert result["selected_sensor_gain_mm"] is None
        assert result["selected_oracle_nominal_gain_mm"] is None
        assert result["sensor_nominal_regret_mm"] is None
        assert result["effect_unknown"] and not result["physical_effect_measured"]
        assert result["gripper_change_contrary_to_objective"] == (token == "GRASP")
    assert fixture == before


@pytest.mark.parametrize("audit", [{"available": False}, {"available": True, "truncated": True}])
def test_no_missing_or_truncated_token_audit_can_pass(monkeypatch, audit):
    monkeypatch.setattr(probe, "encoding_audit", lambda *args: audit)
    with pytest.raises(ValueError, match="all natural candidates"):
        probe.presentations(object(), [probe.make_fixture(*source_fixture())])


def test_source_hash_rejected_before_model_loading(tmp_path, monkeypatch):
    source = tmp_path / "init0-raycast-v02"
    source.mkdir()
    (source / "episodes.jsonl").write_text("{}\n")
    monkeypatch.setattr(probe, "tokenizer_agent", lambda: pytest.fail("must not load tokenizer"))
    monkeypatch.setattr(probe, "load_laya_provider", lambda *a, **k: pytest.fail("must not load model"))
    with pytest.raises(ValueError, match="source identity"):
        probe.frozen_sources(tmp_path)


def test_actual_frozen_six_fixtures_fit_without_truncation_when_available():
    root = Path("runs/reference-pilot")
    if not all((root / f"init{init}-raycast-v02/episodes.jsonl").exists() for init, _, _ in probe.SOURCES):
        pytest.skip("local frozen evidence unavailable")
    fixtures, hashes = probe.frozen_sources(root)
    assert len(hashes) == 3
    assert [(f["source"]["init_state_id"], f["source"]["environment_step"]) for f in fixtures] == [
        (0, 0), (0, 20), (0, 24), (0, 29), (1, 0), (2, 0)]
    assert [f["source"]["rule_token"] for f in fixtures] == ["MV_FWD", "MV_FWD", "MV_DOWN", "MV_DOWN", "MV_FWD", "MV_FWD"]
    assert all(len(f["option_order"]) == 10 for f in fixtures)
    assert all(json.loads(json.dumps(f)) == f for f in fixtures)
    if not (Path(probe.MODEL_PATH) / "tokenizer").exists():
        pytest.skip("local frozen tokenizer unavailable")
    audits = probe.presentations(probe.tokenizer_agent(), fixtures)
    assert [a["questions"]["action"]["effective_token_count"] for a in audits] == [806, 916, 919, 934, 804, 800]
    assert all(not a["truncated"] and len(a["questions"]["action"]["option_markers"]) == 10 for a in audits)
