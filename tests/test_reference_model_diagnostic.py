from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.decision_interface import project_belief, project_oracle, shared_atomic_candidates
from embodied_runtime.experiments import reference_model_diagnostic as diagnostic
from embodied_runtime.experiments.equivalence import make_pair, paired_inputs
from embodied_runtime.experiments.records import RunRecorder, load_records
from embodied_runtime.runtime_core import BeliefSnapshot


def pair(step=0):
    belief = BeliefSnapshot("ep", 1, .5, {"tcp_pos_world_m": [0., 0., 1.],
        "gripper_width_m": .08, "gripper_command": "OPEN", "holding": None,
        "vision:drawer:position_world_m": [.18, .02, 1.03]}, {}, {"instruction": "close top drawer"})
    perceptual = project_belief(belief, "drawer")
    oracle = project_oracle(perceptual, {"source_id": "physical", "target_position_m": [.2, .03, 1.02],
                           "position_definition": "test-point", "moving_contact": False, "remaining_open_mm": 150.})
    return make_pair(oracle, perceptual, shared_atomic_candidates(),
                     physical={"task": "top_drawer", "init_state_id": 0, "seed": 1,
                               "environment_step": step, "sim_time": .5, "physical_state_id": "physical"},
                     history=({"action": {"recorded_robosuite_control": [0., 0., 0., 0., 0., 0., -1.]},
                               "tcp_delta_m": [.001, 0., 0.], "elapsed_sim_s": .05,
                               "gripper_command": "OPEN", "source": "proprioception"},))


def test_baseline_is_exact_existing_model_payload_without_evaluator_leak():
    source = pair()
    original = deepcopy(source)
    oracle, _ = paired_inputs(source)
    fixture = diagnostic.make_fixture(source, "baseline")
    assert fixture["state"] == oracle.provider_input()
    assert fixture["questions"] == oracle.model_questions()
    assert source == original
    assert fixture["state"]["effects"] == {}
    assert "diagnostic_reference_not_model_input" not in fixture["state"]
    assert fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] is None


def test_reverse_preserves_candidates_but_order_sensitive_identity_changes():
    baseline = diagnostic.make_fixture(pair(), "baseline")
    reverse = diagnostic.make_fixture(pair(), "reverse_options")
    assert baseline["state"] == reverse["state"]
    assert baseline["questions"] == reverse["questions"]  # ordinary dict equality loses ordering
    assert reverse["option_order"] == list(reversed(baseline["option_order"]))
    assert reverse["payload_id"] != baseline["payload_id"]
    assert reverse["source_candidate_set_id"] == baseline["source_candidate_set_id"]


def test_neutral_keys_keep_descriptions_and_map_to_original_physical_tokens():
    baseline = diagnostic.make_fixture(pair(), "baseline")
    neutral = diagnostic.make_fixture(pair(), "neutral_keys")
    assert neutral["option_order"] == [f"A{index:02d}" for index in range(11)]
    assert neutral["state"] == baseline["state"]
    assert list(neutral["option_to_canonical"].values()) == baseline["option_order"]
    for label, token in neutral["option_to_canonical"].items():
        assert neutral["questions"]["action"]["criteria"][label] == baseline["questions"]["action"]["criteria"][token]


def test_null_mask_preserves_exact_task_robot_history_and_empty_effects():
    baseline = diagnostic.make_fixture(pair(), "baseline")
    masked = diagnostic.make_fixture(pair(), "target_evidence_masked")
    for key, value in masked["state"]["state"].items():
        assert value == (baseline["state"]["state"][key] if key in diagnostic.MASK_RETAINED_FIELDS else None)
    assert masked["state"]["previous"] == baseline["state"]["previous"]
    assert masked["state"]["effects"] == {}
    assert masked["questions"] == baseline["questions"]
    masked["state"]["previous"][0]["tcp_delta_m"][0] = 99
    assert baseline["state"]["previous"][0]["tcp_delta_m"][0] == .001


def test_approach_objective_and_coherent_geometry_reflection():
    approach = diagnostic.make_fixture(pair(), "approach_objective")
    mirrored = diagnostic.make_fixture(pair(), "approach_mirrored_geometry")
    assert approach["questions"] == mirrored["questions"]
    a, b = approach["state"]["state"], mirrored["state"]["state"]
    tcp = np.asarray(b["robot.tcp_position_m"])
    target = np.asarray(b["target.position_m"])
    np.testing.assert_allclose(target, 2 * tcp - a["target.position_m"])
    delta = target - tcp
    np.testing.assert_allclose(b["relations.tcp_target_delta_m"], delta)
    assert b["relations.distance_m"] == pytest.approx(np.linalg.norm(delta), rel=1e-5)
    assert b["relations.xy_error_m"] == pytest.approx(np.linalg.norm(delta[:2]), rel=1e-5)
    assert b["relations.height_error_m"] == pytest.approx(delta[2])
    assert mirrored["state"]["previous"] == approach["state"]["previous"]
    assert approach["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["MV_FWD"]
    assert mirrored["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["MV_BACK"]


def test_sentinels_keep_eleven_options_and_baseline_state():
    baseline = diagnostic.make_fixture(pair(), "baseline")
    for token in ("MV_FWD", "MV_BACK"):
        fixture = diagnostic.make_fixture(pair(), f"sentinel_{token}")
        assert fixture["state"] == baseline["state"]
        assert fixture["questions"]["action"]["criteria"] == baseline["questions"]["action"]["criteria"]
        assert len(fixture["option_order"]) == 11
        assert fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == [token]
    assert (len(diagnostic.STEPS) * len(diagnostic.CONDITIONS) + 2) * 2 == 52


def test_nominal_reference_handles_unknown_geometry_and_stop():
    state = diagnostic.make_fixture(pair(), "baseline")["state"]
    state["state"]["target.position_m"] = state["state"]["robot.tcp_position_m"]
    assert diagnostic.nominal_geometry_reference(state)["expected_tokens"] == ["STOP"]
    state["state"]["target.position_m"] = None
    assert diagnostic.nominal_geometry_reference(state)["expected_tokens"] is None
    with pytest.raises(ValueError, match="known TCP"):
        diagnostic.mirror_geometry(state)


class Tensor:
    """Minimal tensor-shaped value, no real model inference in unit tests."""
    def __init__(self, value):
        self.value = np.asarray(value)

    def detach(self):
        return self

    def cpu(self):
        return self

    def float(self):
        return self

    def numpy(self):
        return self.value


class FakeModel:
    def __init__(self):
        self.hook = None

    def register_forward_hook(self, hook):
        self.hook = hook
        return SimpleNamespace(remove=lambda: setattr(self, "hook", None))


class FakeAgent:
    cfg = {"temperature": [1., 1., 1.], "temperature_by_options": {"choice:11+": .1}}
    device = "test-device"
    dtype = "test-dtype"

    def __init__(self, *, fail=False, wrong_tokens=False):
        self.model = FakeModel()
        self.calls = 0
        self.fail = fail
        self.wrong_tokens = wrong_tokens

    def system_one(self, state, questions):
        self.calls += 1
        if self.fail:
            raise RuntimeError("injected model failure")
        tokens = list(questions["action"]["criteria"])
        logits = np.arange(len(tokens)) * .1
        if self.model.hook is not None:
            ids = list(range(30))
            if self.wrong_tokens:
                ids[0] = 100
            assert self.model.hook(self.model, (Tensor([ids]), Tensor([np.ones(30)]), Tensor([list(range(11))])),
                                   (Tensor([logits]), Tensor([[.2, .1]]))) is None
        probabilities = diagnostic._softmax(logits / .1)
        return {"answers": {"action": {"choice": tokens[-1],
                "probabilities": {key: round(value, 4) for key, value in zip(tokens, probabilities)},
                "confidence": .123, "action": {"act_probability": .321}}},
                "usage": {"input_tokens": 30, "output_tokens": 0}}


def fake_audit(*args):
    return {"available": True, "truncated": False, "questions": {
        "action": {"effective_input_ids": list(range(30)), "option_markers": list(range(11))}}}


def test_full_raw_response_logits_and_reversed_mapping_are_retained(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    agent = FakeAgent()
    fixture = diagnostic.make_fixture(pair(), "reverse_options")
    root = tmp_path / "run"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    analysis = diagnostic.run_call(agent, fixture, recorder, repeat=0, ordinal=0)
    recorder.close()
    rows, _ = load_records(root / "episodes.jsonl")
    assert [r["kind"] for r in rows] == ["run_start", "model_call_intent", "model_raw_response", "model_call_analysis"]
    response = rows[2]["data"]
    assert response["raw_response"]["answers"]["action"]["action"]["act_probability"] == .321
    assert response["actual_device"] == "test-device"
    assert response["actual_dtype"] == "test-dtype"
    assert analysis["canonical_choice"] == "MV_FWD"
    assert analysis["canonical_raw_logits"]["MV_FWD"] == 1.
    assert analysis["canonical_raw_logits"]["RELEASE"] == 0.
    assert analysis["temperature"]["effective"] == .1
    assert analysis["post_temperature_unrounded_probabilities"]["MV_FWD"] > analysis["pre_temperature_probabilities"]["MV_FWD"]
    assert agent.model.hook is None


@pytest.mark.parametrize("condition", ["baseline", "neutral_keys"])
def test_direct_api_input_excludes_all_diagnostic_references(monkeypatch, tmp_path, condition):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    fixture = diagnostic.make_fixture(pair(), condition)
    original = deepcopy(fixture)
    agent = FakeAgent()
    recorder = RunRecorder(tmp_path / "run", {}, {"run_id": "test"})
    result = diagnostic.run_call(agent, fixture, recorder, repeat=0, ordinal=0, capture_logits=False)
    recorder.close()
    assert result["canonical_choice"] == "RELEASE"
    assert fixture == original
    assert result["matches_diagnostic_reference"] is None


@pytest.mark.parametrize("mode,message", [("failure", "injected model failure"),
                                          ("wrong_tokens", "actual model tokens")])
def test_model_failures_and_token_mismatches_preserve_intent_and_cleanup(monkeypatch, tmp_path, mode, message):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    agent = FakeAgent(fail=mode == "failure", wrong_tokens=mode == "wrong_tokens")
    root = tmp_path / "run"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    with pytest.raises((ValueError, RuntimeError), match=message):
        diagnostic.run_call(agent, diagnostic.make_fixture(pair(), "baseline"), recorder, repeat=0, ordinal=0)
    recorder.close()
    rows, _ = load_records(root / "episodes.jsonl")
    assert rows[1]["kind"] == "model_call_intent"
    assert rows[-1]["kind"] == "failure"
    assert agent.model.hook is None
    if mode == "wrong_tokens":
        assert rows[-2]["kind"] == "model_raw_response"


def test_truncation_stops_before_model_call(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostic, "encoding_audit", lambda *args: {"available": True, "truncated": True})
    agent = FakeAgent()
    recorder = RunRecorder(tmp_path / "run", {}, {"run_id": "test"})
    with pytest.raises(ValueError, match="complete tokenizer audit"):
        diagnostic.run_call(agent, diagnostic.make_fixture(pair(), "baseline"), recorder, repeat=0, ordinal=0)
    recorder.close()
    assert agent.calls == 0


def test_selected_source_requires_all_boundaries_and_successful_completion(tmp_path):
    root = tmp_path / "source"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    for step in diagnostic.STEPS:
        recorder.record("paired_state", pair(step))
    recorder.close()
    with pytest.raises(ValueError, match="complete accepted"):
        diagnostic.selected_pairs(root / "episodes.jsonl")
    other = tmp_path / "complete"
    recorder = RunRecorder(other, {}, {"run_id": "test"})
    for step in reversed(diagnostic.STEPS):
        recorder.record("paired_state", pair(step))
    recorder.record("termination", {"reason": "collection_smoke_complete"})
    recorder.close()
    assert [p["physical"]["environment_step"] for p in diagnostic.selected_pairs(other / "episodes.jsonl")] == list(diagnostic.STEPS)


def test_summary_rebuilds_from_raw_ignores_cache_and_maps_actual_option_order(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    root = tmp_path / "summary"
    recorder = RunRecorder(root, {}, {"run_id": "test"})
    source = pair()
    recorder.record("paired_source", source)
    fixtures = [diagnostic.make_fixture(source, condition) for condition in ("baseline", "reverse_options", "neutral_keys")]
    for fixture in fixtures:
        recorder.record("diagnostic_fixture", fixture)
    for repeat in range(2):
        for ordinal, fixture in enumerate(fixtures):
            diagnostic.run_call(FakeAgent(), fixture, recorder, repeat=repeat, ordinal=ordinal)
    recorder.record("model_call_analysis", {"call_id": "fabricated", "canonical_choice": "GRASP",
                                            "canonical_probabilities": {"GRASP": 1.}})
    recorder.record("termination", {"reason": "reference_model_diagnostic_complete"})
    recorder.close()
    summary = diagnostic.summarize(root)
    assert summary["termination_recorded"]
    assert not summary["analysis_cache_used"]
    assert summary["completed_response_count"] == 6
    assert summary["unmatched_intent_ids"] == []
    calls = {call["condition"]: call for call in summary["calls"] if call["repeat"] == 0}
    assert calls["baseline"]["choice"] == "RELEASE"
    assert calls["neutral_keys"]["choice"] == "RELEASE"
    reverse = calls["reverse_options"]
    assert reverse["choice"] == "MV_FWD"
    assert reverse["raw_logits"]["MV_FWD"] == 1.
    assert reverse["raw_logits"]["RELEASE"] == 0.
    assert reverse["raw_logit_margin"] == pytest.approx(.1)
    assert reverse["pre_temperature"]["margin"] < reverse["post_temperature"]["margin"]
    assert reverse["act_probability"] == .321
    assert reverse["raw_act_logits"] == [[.2, .1]]
    assert reverse["api_vs_observed_probability_max_error"] < .00005
    assert reverse["choice_matches_observed_argmax"]
    assert len(summary["repeat_comparisons"]) == 3
    for comparison in summary["repeat_comparisons"]:
        assert comparison["choice_agreement"]
        assert comparison["distributions"]["pre_temperature"]["js_divergence_nats"] == 0.
    controls = {item["condition"]: item for item in summary["baseline_control_comparisons"]}
    assert not controls["reverse_options"]["choice_agreement"]
    assert controls["reverse_options"]["distributions"]["post_temperature"]["js_divergence_nats"] > 0.
    assert controls["neutral_keys"]["choice_agreement"]
    assert controls["neutral_keys"]["distributions"]["post_temperature"]["js_divergence_nats"] == 0.


def test_summary_preserves_incomplete_failed_intent(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    recorder = RunRecorder(tmp_path / "summary", {}, {"run_id": "test"})
    source = pair()
    fixture = diagnostic.make_fixture(source, "baseline")
    recorder.record("paired_source", source)
    recorder.record("diagnostic_fixture", fixture)
    with pytest.raises(RuntimeError, match="injected"):
        diagnostic.run_call(FakeAgent(fail=True), fixture, recorder, repeat=0, ordinal=0)
    recorder.close()
    summary = diagnostic.summarize(tmp_path / "summary")
    assert not summary["termination_recorded"]
    assert summary["completed_response_count"] == 0
    assert len(summary["unmatched_intent_ids"]) == 1
    assert summary["failures"][0]["category"] == "model_diagnostic_error"


@pytest.mark.parametrize("corruption", ["fixture", "intent", "tokens"])
def test_summary_rejects_internally_hashed_but_inconsistent_evidence(monkeypatch, tmp_path, corruption):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    recorder = RunRecorder(tmp_path / "summary", {}, {"run_id": "test"})
    source = pair()
    fixture = diagnostic.make_fixture(source, "baseline")
    recorder.record("paired_source", source)
    recorded = deepcopy(fixture)
    if corruption == "fixture":
        recorded["state"]["state"]["target.position_m"] = [99., 99., 99.]
    recorder.record("diagnostic_fixture", recorded)
    if corruption == "intent":
        recorder.record("model_call_intent", {"call_id": "wrong", "fixture_id": fixture["fixture_id"],
                         "repeat": 0, "ordinal": 0, "payload_id": fixture["payload_id"]})
    elif corruption == "tokens":
        with pytest.raises(ValueError, match="actual model tokens"):
            diagnostic.run_call(FakeAgent(wrong_tokens=True), fixture, recorder, repeat=0, ordinal=0)
    recorder.close()
    with pytest.raises(ValueError, match={"fixture": "fixture differs", "intent": "call intent", "tokens": "actual tokens"}[corruption]):
        diagnostic.summarize(tmp_path / "summary")


def test_summary_no_hook_reports_raw_logits_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostic, "encoding_audit", fake_audit)
    recorder = RunRecorder(tmp_path / "summary", {}, {"run_id": "test"})
    source = pair()
    fixture = diagnostic.make_fixture(source, "baseline")
    recorder.record("paired_source", source)
    recorder.record("diagnostic_fixture", fixture)
    diagnostic.run_call(FakeAgent(), fixture, recorder, repeat=0, ordinal=0, capture_logits=False)
    recorder.close()
    summary = diagnostic.summarize(tmp_path / "summary")
    assert summary["calls"][0]["raw_logits"] is None
    assert summary["calls"][0]["pre_temperature"] is None
    assert summary["calls"][0]["api_rounded"]["top1"] == "RELEASE"
