from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from embodied_runtime.experiments import approach_family_control as family
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records
from embodied_runtime.experiments.reference_model_diagnostic import active_temperature, payload_id
from embodied_runtime.runtime_core import MOVE, _sha256_json


def original_fixture():
    order = list(family.NATURAL_ORDER)
    state = {"state": {"quality.geometry_valid": True, "relations.tcp_target_delta_m": [.2, .05, .03],
                       "interaction.holding": None, "progress.remaining_open_mm": None},
             "previous": [{"source": "proprioception", "action": "STOP", "tcp_delta_m": [0., 0., 0.]}],
             "effects": {"source": "geometry", "privileged": False, "assumptions": "nominal geometry only",
                         "columns": ["distance_change_m", "xy_error_change_m"],
                         "rows": {token: [-.00123, -.000987] if token in MOVE else None for token in order}}}
    questions = {"action": {"type": "choice", "instructions": family.parent.APPROACH_INSTRUCTION,
                            "criteria": {token: f"original description of {token}" for token in order}}}
    result = {"condition": "sensor_nominal_approach", "state": state, "questions": questions,
              "option_order": order, "option_to_canonical": {token: token for token in order},
              "source": {"rule_token": "MV_FWD", "init_state_id": 0, "environment_step": 0,
                         "canonical": {"raw_effects": {"MV_FWD": -.001234567891}},
                         "natural_candidates": [{"token": token, "feasible": True} for token in order]},
              "diagnostic_reference_not_model_input": {"scored_expected_tokens": None},
              "payload_id": payload_id(state, questions)}
    result["fixture_id"] = _sha256_json(result)
    return result


def reidentify(fixture):
    fixture["payload_id"] = payload_id(fixture["state"], fixture["questions"])
    fixture["fixture_id"] = _sha256_json({k: v for k, v in fixture.items() if k != "fixture_id"})


def test_only_menu_and_removed_unknown_effect_rows_change_in_model_input():
    original = original_fixture()
    before = deepcopy(original)
    result = family.family_fixture(original)
    assert original == before
    assert result["option_order"] == [*MOVE, "STOP"]
    assert list(result["questions"]["action"]["criteria"]) == result["option_order"]
    expected_state = deepcopy(original["state"])
    expected_questions = deepcopy(original["questions"])
    for token in family.REMOVED:
        del expected_state["effects"]["rows"][token]
        del expected_questions["action"]["criteria"][token]
    assert result["state"] == expected_state
    assert result["questions"] == expected_questions
    assert result["state"]["effects"]["rows"]["STOP"] is None
    assert result["state"]["state"] == original["state"]["state"]
    assert result["state"]["previous"] == original["state"]["previous"]


def test_complete_parent_and_raw_natural_pool_preserved_outside_model_payload():
    original = original_fixture()
    result = family.family_fixture(original)
    assert result["parent_fixture"] == original
    assert result["source"] == original["source"]
    assert result["intervention"]["natural_pool"] == list(family.NATURAL_ORDER)
    assert result["intervention"]["kind"] == "objective_family_admission"
    assert result["intervention"]["not_a_natural_gate_or_collision_certificate"]
    assert result["intervention"]["parent_fixture_id"] == original["fixture_id"]
    assert result["payload_id"] != original["payload_id"]
    assert result["fixture_id"] != original["fixture_id"]
    assert json.loads(json.dumps(result)) == result
    text = json.dumps([result["state"], result["questions"]])
    assert all(key not in text for key in ("rule_token", "parent_fixture", "natural_pool", "oracle_sim"))


@pytest.mark.parametrize("mutation", [
    lambda f: f["questions"]["action"].update(instructions="choose an action"),
    lambda f: f["option_order"].reverse(),
    lambda f: f.update(condition="different-condition"),
    lambda f: f["option_to_canonical"].update(MV_FWD="MV_BACK"),
    lambda f: f["state"]["effects"]["rows"].update(GRASP=[0., 0.]),
    lambda f: f["state"]["effects"]["rows"].update(STOP=[0., 0.]),
    lambda f: f["source"].update(rule_token="GRASP"),
])
def test_incompatible_parent_conditions_cannot_be_silently_changed(mutation):
    original = original_fixture()
    mutation(original)
    reidentify(original)
    with pytest.raises(ValueError):
        family.family_fixture(original)


def test_changed_parent_content_without_hash_update_rejected():
    original = original_fixture()
    original["state"]["state"]["relations.tcp_target_delta_m"][0] = -.2
    with pytest.raises(ValueError, match="frozen ten-option"):
        family.family_fixture(original)


def test_source_hash_failure_precedes_any_model_or_source_analysis(tmp_path, monkeypatch):
    (tmp_path / "episodes.jsonl").write_text("{}\n")
    monkeypatch.setattr(family.parent, "report", lambda *a: pytest.fail("must reject hash before source analysis"))
    monkeypatch.setattr(family, "load_laya_provider", lambda *a, **k: pytest.fail("must not load model"))
    with pytest.raises(ValueError, match="source identity"):
        family.frozen_source(tmp_path)


def test_cpu_preflight_records_roundtrippable_fixtures_without_loading_model(tmp_path, monkeypatch):
    fixture = family.family_fixture(original_fixture())
    fixtures = [fixture]
    model = {"content_id": family.parent.MODEL_ID, "files_sha256": {"fake": "hash"}}
    cfg = {"max_len": 1024, "temperature": [1., 1., 1.]}
    source_rows = [{"kind": "manifest_update", "data": {"model": model}},
                   {"kind": "model_loaded", "data": {"config": cfg}}]
    monkeypatch.setattr(family, "frozen_source", lambda *a: (fixtures, {}, source_rows))
    monkeypatch.setattr(family, "model_identity", lambda *a: model)
    monkeypatch.setattr(family.parent, "tokenizer_agent", lambda: SimpleNamespace(cfg=cfg))
    monkeypatch.setattr(family.parent, "presentations", lambda *a: [{"fixture_id": fixture["fixture_id"], "truncated": False}])
    monkeypatch.setattr(family, "load_laya_provider", lambda *a, **k: pytest.fail("CPU preflight must not load model"))
    args = SimpleNamespace(source="source", preflight_source=None, preflight=tmp_path / "preflight")
    family.run(args, preflight=True)
    rows, errors = load_records(args.preflight / "episodes.jsonl")
    assert not errors
    assert [r["data"] for r in rows if r["kind"] == "search_fixture"] == fixtures
    assert [r["data"] for r in rows if r["kind"] == "termination"] == [{"reason": "approach_family_preflight_complete"}]
    assert not any(r["kind"] in ("model_loaded", "model_call_intent", "model_raw_response") for r in rows)


def test_registered_real_source_has_only_the_six_family_interventions_when_available():
    source = Path("runs/autonomous-research/approach-selector-run-01")
    if not (source / "episodes.jsonl").exists() or not (Path(family.parent.MODEL_PATH) / "tokenizer").exists():
        pytest.skip("local frozen evidence/tokenizer unavailable")
    fixtures, baseline, rows = family.frozen_source(source)
    assert baseline["complete"] and baseline["all_repeats_exact"]
    assert len(fixtures) == 6
    assert all(f["option_order"] == list(family.FAMILY_ORDER) for f in fixtures)
    assert [(f["source"]["init_state_id"], f["source"]["environment_step"]) for f in fixtures] == [
        (0, 0), (0, 20), (0, 24), (0, 29), (1, 0), (2, 0)]
    audit = family.parent.presentations(family.parent.tokenizer_agent(), fixtures)
    assert all(not a["truncated"] and len(a["questions"]["action"]["option_markers"]) == 7 for a in audit)
    cfg = next(r["data"]["config"] for r in rows if r["kind"] == "model_loaded")
    assert active_temperature(SimpleNamespace(cfg=cfg), 7) == active_temperature(SimpleNamespace(cfg=cfg), 10)
    for fixture in fixtures:
        parent = fixture["parent_fixture"]
        for token in family.FAMILY_ORDER:
            assert fixture["state"]["effects"]["rows"][token] == parent["state"]["effects"]["rows"][token]
            assert fixture["questions"]["action"]["criteria"][token] == parent["questions"]["action"]["criteria"][token]
        assert fixture["state"]["state"] == parent["state"]["state"]
        assert fixture["state"]["previous"] == parent["state"]["previous"]


@pytest.mark.parametrize("wrong_temperature", [False, True])
def test_report_pairs_native_raw_calls_and_rejects_configuration_drift(tmp_path, monkeypatch, wrong_temperature):
    # Synthetic evidence exercises reporting/validation only; no model is invoked.
    source = RunRecorder(tmp_path / "sensor", {}, {"run_id": "synthetic-sensor"})
    source.record("paired_state", {"pair_id": "pair", "oracle_state": {
        "fields": {"relations.tcp_target_delta_m": {"value": [.2, .05, .03]}}}})
    source.close()
    fixtures = []
    for i in range(6):
        original = original_fixture()
        original["source"].update(environment_step=i, pair_id="pair", source_path=str(source.output / "episodes.jsonl"))
        reidentify(original)
        fixtures.append(family.family_fixture(original))
    config = {"temperature": [1., 1., 1.]}
    loaded = {"config": config, "device": "cpu", "dtype": "torch.bfloat16"}
    model = {"path": str(tmp_path), "files_sha256": {}}
    source_rows = [{"kind": "model_loaded", "data": loaded}, {"kind": "inference_environment", "data": {}},
                   {"kind": "manifest_update", "data": {"model": model}}]
    baseline = {"calls": [{"fixture_id": f["parent_fixture"]["fixture_id"], "repeat": r,
                           "choice": "GRASP", "call_id": f"parent-{i}-{r}"}
                          for i, f in enumerate(fixtures) for r in range(2)],
                "comparisons": [{"init_state_id": 0, "environment_step": i, "repeat": r, "choice": "GRASP"}
                                for i in range(6) for r in range(2)]}
    monkeypatch.setattr(family, "frozen_source", lambda *a: (fixtures, baseline, source_rows))
    monkeypatch.setattr(family.parent, "tokenizer_agent", lambda: SimpleNamespace(cfg=config))
    audit = {"available": True, "truncated": False, "questions": {"action": {
        "effective_input_ids": [1, 2, 3], "option_markers": list(range(7))}}}
    prepared = [{"fixture_id": f["fixture_id"], **audit} for f in fixtures]
    monkeypatch.setattr(family.parent, "presentations", lambda *a: prepared)
    common = {"source": "frozen-source", "source_sha256": family.SOURCE_SHA256,
              "fixture_ids": [f["fixture_id"] for f in fixtures], "protocol_sha256": "protocol"}
    manifest = {"run_id": "synthetic-evidence", "code": {"source_sha256": {"probe": "frozen-code"}}}
    prior = RunRecorder(tmp_path / "preflight", common, manifest)
    for f in fixtures:
        prior.record("search_fixture", f)
    prior.record("manifest_update", {"model": model})
    prior.record("tokenizer_loaded", {"config": config})
    for p in prepared:
        prior.record("provider_presentation", p)
    prior.record("termination", {"reason": "approach_family_preflight_complete"})
    prior.close()
    run = RunRecorder(tmp_path / "run", {**common, "preflight_source": str(prior.output),
                      "preflight_sha256": file_hash(prior.output / "episodes.jsonl")}, manifest)
    for f in fixtures:
        run.record("search_fixture", f)
    for row in source_rows:
        run.record(row["kind"], row["data"])
    for p in prepared:
        run.record("provider_presentation", p)
    for repeat in range(2):
        for ordinal, f in enumerate(fixtures if repeat == 0 else reversed(fixtures)):
            ident = {"fixture_id": f["fixture_id"], "repeat": repeat, "ordinal": ordinal}
            call_id = _sha256_json(ident)
            temperature = active_temperature(SimpleNamespace(cfg=config), 7)
            if wrong_temperature:
                temperature = {**temperature, "configured": 2., "effective": 2.}
            run.record("model_call_intent", {**ident, "call_id": call_id, "payload_id": f["payload_id"],
                "input_encoding": audit, "temperature": temperature, "device_before": "cpu", "dtype_before": "torch.bfloat16"})
            run.record("model_raw_response", {"call_id": call_id, "actual_device": "cpu", "actual_dtype": "torch.bfloat16",
                "raw_response": {"answers": {"action": {"choice": "MV_FWD", "probabilities": {t: 1/7 for t in family.FAMILY_ORDER}}}},
                "forward_traces": [{"input_ids": [[1, 2, 3]], "option_markers": [list(range(7))], "raw_option_logits": [[0.]*7]}]})
    run.record("termination", {"reason": "approach_family_complete", "calls": 12})
    run.close()
    if wrong_temperature:
        with pytest.raises(ValueError, match="temperature differs"):
            family.report(run.output)
    else:
        report = family.report(run.output)
        assert report["complete"] and report["all_repeats_exact"]
        assert len(report["comparisons"]) == report["valid_calls"] == 12
        assert all(p["natural_choice"] == "GRASP" and p["family_choice"] == "MV_FWD" for p in report["comparisons"])
        assert all(p["family_metrics"]["agrees_with_rule"] for p in report["comparisons"])
