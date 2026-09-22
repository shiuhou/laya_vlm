from copy import deepcopy
from dataclasses import asdict, replace
import json

import pytest

from embodied_runtime.decision_interface import project_belief, project_oracle, shared_atomic_candidates
from embodied_runtime.experiments.equivalence import make_pair, paired_inputs
from embodied_runtime.experiments.inspect_decision_pair import inspect_pair, main, render_text
from embodied_runtime.experiments.records import RunRecorder
from embodied_runtime.experiments.reference_quality import local_reference
from embodied_runtime.runtime_core import BeliefSnapshot, RuleProvider, _sha256_json


def pair_fixture(step=0, init=0, variant="fresh"):
    belief = BeliefSnapshot("ep", 1, .5, {"tcp_pos_world_m": [0., 0., 1.],
        "vision:drawer:position_world_m": [.2, 0., 1.]}, {}, {"instruction": "close the drawer"},
        validity={"drawer": {"geometry_valid": True, "geometry_age_s": .1}})
    perceptual = project_belief(belief, "drawer")
    oracle = project_oracle(perceptual, {"source_id": "physical", "target_position_m": [-.2, 0., 1.],
        "position_definition": "moving_collision_geometry_world_aabb_center", "remaining_open_mm": 100.})
    candidates = shared_atomic_candidates()
    natural = tuple(replace(c, feasible=c.token == "STOP", reason_codes=("geometry_invalid",) if c.token != "STOP" else ())
                    for c in candidates)
    return make_pair(oracle, perceptual, candidates, natural_perceptual=natural, physical={"sim_time": .5,
        "physical_state_id": "physical", "task": "top_drawer", "init_state_id": init, "seed": 1,
        "environment_step": step, "variant": variant})


def decisions(pair, provider="RuleProvider"):
    result = []
    for branch, inp in zip(("oracle", "perceptual"), paired_inputs(pair)):
        for repeat in range(2):
            result.append({"pair_id": pair["pair_id"], "branch": branch, "repeat": repeat, "provider": provider,
                "decision": asdict(RuleProvider().decide(inp)), "latency_ms": 1., "choice_allowed": True,
                "presentation_version": "compact-v0.1", "model_input_id": _sha256_json({
                    "state": inp.provider_input(), "question": inp.model_questions()})})
    return result


def write_run(path, pairs, outputs=(), terminate=True):
    with_recorder = RunRecorder(path, {"provider": "rule", "repeats": 2}, {"run_id": "inspection-test"})
    for pair in pairs:
        with_recorder.record("paired_state", pair)
    for output in outputs:
        with_recorder.record("equivalence_decision", output)
    with_recorder.record("equivalence_diagnostic", {"fabricated": "cache must not be used"})
    if terminate:
        with_recorder.record("termination", {"reason": "smoke_complete"})
    with_recorder.close()


def tree_bytes(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def test_inspection_is_read_only_preserves_provenance_and_unknowns(tmp_path):
    pair = pair_fixture()
    path = tmp_path / "run"
    write_run(path, [pair], decisions(pair))
    before = tree_bytes(path)
    report = inspect_pair(path, show_input=True)
    assert tree_bytes(path) == before
    position = report["fields"]["target.position_m"]
    assert position["status"] == "incomparable_definition" and "difference_l2" not in position
    assert position["oracle"]["privileged"] is True
    assert position["perceptual"]["source"] == "sensor"
    assert report["fields"]["progress.remaining_open_mm"]["status"] == "missing"
    assert report["fields"]["interaction.holding"]["status"] == "both_unknown"
    assert report["candidates"]["natural_oracle"] is None
    assert report["candidates"]["natural_feasible_set_agreement"] is None
    assert sum(c["feasible"] for c in report["candidates"]["natural_perceptual"]) == 1
    assert report["comparisons"][0]["top1_agreement"] is False
    assert all(r["full_input_comparison_valid"] for r in report["comparisons"])
    assert all(s["max_probability_difference"] == 0 for s in report["stability"])
    assert report["validated_model_payloads"]["compact-v0.1"]["oracle"]["state"]["effects"] == {}
    assert "EVALUATOR ONLY" not in render_text(report)
    json.dumps(report, allow_nan=False)


def test_filters_do_not_guess_between_initial_states_and_variants(tmp_path):
    pairs = [pair_fixture(), pair_fixture(init=1), pair_fixture(init=1, variant="stale")]
    write_run(tmp_path / "run", pairs)
    assert len(inspect_pair(tmp_path / "run", list_only=True)["pairs"]) == 3
    with pytest.raises(ValueError, match="matched 3 pairs"):
        inspect_pair(tmp_path / "run", step=0)
    with pytest.raises(ValueError, match="matched 0 pairs"):
        inspect_pair(tmp_path / "run", step=99)
    assert inspect_pair(tmp_path / "run", step=0, init_state_id=1, variant="stale")["boundary"]["pair_id"] == pairs[2]["pair_id"]
    assert inspect_pair(tmp_path / "run", pair_id=pairs[0]["pair_id"][:12])["boundary"]["init_state_id"] == 0


def test_unknown_referents_do_not_make_numeric_geometry_errors_comparable(tmp_path):
    pair = pair_fixture()
    for branch in ("oracle", "perceptual"):
        pair[f"{branch}_state"]["fields"]["target.position_definition"] = {
            "value": None, "source": "unknown", "basis": "unavailable", "privileged": False}
    pair["pair_id"] = _sha256_json({k: v for k, v in pair.items() if k != "pair_id"})
    write_run(tmp_path / "run", [pair], decisions(pair))
    report = inspect_pair(tmp_path / "run")
    for key in ("target.position_m", "relations.distance_m", "relations.tcp_target_delta_m"):
        assert report["fields"][key]["status"] == "incomparable_definition"
        assert "difference_l2" not in report["fields"][key]


def test_interrupted_log_preserves_missing_outputs_without_inference(tmp_path):
    pair = pair_fixture()
    path = tmp_path / "run"
    write_run(path, [pair], decisions(pair)[:1], terminate=False)
    with (path / "episodes.jsonl").open("ab") as stream:
        stream.write(b'{"partial":')
    report = inspect_pair(path)
    assert len(report["decisions"]) == 1
    assert {d["category"] for d in report["diagnostics"]} == {"run_incomplete", "incomplete_record"}
    assert all(not c["full_input_comparison_valid"] for c in report["comparisons"])
    assert all(c["js_divergence_nats"] is None for c in report["comparisons"])
    assert set(inspect_pair(path, show_input=True)["validated_model_payloads"]["compact-v0.1"]) == {"oracle"}


@pytest.mark.parametrize("damage", ["pair", "candidate", "decision", "tokens", "chain"])
def test_rejects_corrupt_evidence_even_when_only_listing(tmp_path, damage):
    pair = pair_fixture()
    outputs = decisions(pair)
    if damage in ("pair", "candidate"):
        pair["shared_candidates"][0]["description"] = "fabricated semantics"
        if damage == "candidate":
            pair["pair_id"] = _sha256_json({k: v for k, v in pair.items() if k != "pair_id"})
    elif damage == "decision":
        outputs[0]["model_input_id"] = "wrong"
    elif damage == "tokens":
        outputs[0]["input_encoding"] = {"available": True, "questions": {
            "action": {"effective_input_ids": [1, 2], "effective_input_id": "wrong"}}}
    path = tmp_path / "run"
    write_run(path, [pair], outputs)
    if damage == "chain":
        raw = path / "episodes.jsonl"
        raw.write_bytes(raw.read_bytes().replace(b'"run_start"', b'"bad_start"', 1))
    with pytest.raises(ValueError):
        inspect_pair(path, list_only=True)


@pytest.mark.parametrize("audit, valid", [(None, False), ({"available": True, "truncated": True}, False),
    ({"available": True, "truncated": False, "questions": {
        "action": {"effective_input_ids": [1, 2], "effective_input_id": _sha256_json([1, 2]),
                   "state_truncated": False, "heading_truncated": False, "options_truncated": False}}}, True)])
def test_laya_metrics_do_not_upgrade_invalid_or_missing_token_evidence(tmp_path, audit, valid):
    pair = pair_fixture()
    outputs = decisions(pair, "LayaProvider")  # synthetic recorded output; no Laya inference
    for output in outputs:
        output["input_encoding"] = audit
    write_run(tmp_path / "run", [pair], outputs)
    report = inspect_pair(tmp_path / "run")
    laya = [r for r in report["comparisons"] if r["provider"] == "LayaProvider"]
    assert all(r["full_input_comparison_valid"] is valid for r in laya)
    assert any("device/dtype" in w for w in report["warnings"])


def test_mixed_presentations_are_not_state_only_comparisons(tmp_path):
    pair = pair_fixture()
    outputs = decisions(pair)
    inp = paired_inputs(pair)[0]
    for output in outputs:
        if output["branch"] == "oracle":
            output["presentation_version"] = "audit-json-v0"
            output["model_input_id"] = _sha256_json({"state": inp.provider_input("audit-json-v0"),
                                                    "question": inp.model_questions("audit-json-v0")})
    write_run(tmp_path / "run", [pair], outputs)
    report = inspect_pair(tmp_path / "run", show_input=True)
    assert all(r["presentation_agreement"] is False and not r["full_input_comparison_valid"] for r in report["comparisons"])
    assert set(report["validated_model_payloads"]["audit-json-v0"]) == {"oracle"}
    assert set(report["validated_model_payloads"]["compact-v0.1"]) == {"perceptual"}


def test_contradictory_clipping_and_incomplete_audits_not_upgraded(tmp_path):
    pair = pair_fixture()
    outputs = decisions(pair, "LayaProvider")
    for output in outputs:
        output["input_encoding"] = {"available": True, "truncated": False, "questions": {
            "action": {"effective_input_id": _sha256_json([1, 2]), "state_truncated": False}}}
    write_run(tmp_path / "partial", [pair], outputs)
    report = inspect_pair(tmp_path / "partial")
    assert all(not r["full_input_comparison_valid"] for r in report["comparisons"])
    outputs[0]["input_encoding"]["questions"]["action"]["state_truncated"] = True
    write_run(tmp_path / "contradictory", [pair], outputs)
    with pytest.raises(ValueError, match="contradictory.*clipping"):
        inspect_pair(tmp_path / "contradictory", list_only=True)


def test_recorded_device_fallback_is_exposed_without_claiming_pilot_fallback(tmp_path):
    pair = pair_fixture()
    outputs = decisions(pair, "LayaProvider")
    for output in outputs:
        output["input_encoding"] = {"actual_device": "cuda" if output["branch"] == "oracle" else "cpu",
                                    "actual_dtype": "torch.bfloat16" if output["branch"] == "oracle" else "torch.float32"}
    write_run(tmp_path / "run", [pair], outputs)
    report = inspect_pair(tmp_path / "run")
    assert all(r["recorded_device_dtype_agreement"] is False for r in report["comparisons"] if r["provider"] == "LayaProvider")
    assert any("device/dtype changed" in w for w in report["warnings"])
    assert not any("lack recorded" in w for w in report["warnings"])


def write_collection(path, pair, *, missing=False, bad_cache=False):
    before = {"remaining_open_mm": 100., "distance_to_moving_geometry_mm": 20.,
              "moving_contact": False, "success": False, "obstacle_contact": False, "contacts": []}
    previews = {c["token"]: {"after": dict(before), "obstacle_pairs_seen": [], "sim_state_after": [1.],
                "execution": {"low_level_commands": [[0., 0., -1.]], "environment_step_count": 8}}
                for c in pair["shared_candidates"]}
    # Only STOP and RELEASE are exact aliases in this synthetic fixture.
    for i, (token, preview) in enumerate(previews.items()):
        if token not in ("STOP", "RELEASE"):
            preview["sim_state_after"] = [10. + i]
    evaluator = {"before": before, **local_reference(before, previews)}
    if bad_cache:
        evaluator["tier"] = "fabricated"
    recorder = RunRecorder(path, {}, {"run_id": "collection"})
    recorder.record("paired_state", pair)
    common = {"physical_state_id": "physical", "not_supplied_to_model": True}
    for token, preview in previews.items():
        if not missing or token != "GRASP":
            recorder.record("evaluator_probe", {**common, "token": token, **preview})
    recorder.record("reference_evaluator", {**common, **evaluator})
    recorder.record("termination", {"reason": "complete"})
    recorder.close()


def test_evaluator_panel_remains_separate_and_aliases_are_boundary_specific(tmp_path):
    pair = pair_fixture()
    write_run(tmp_path / "run", [pair], decisions(pair))
    write_collection(tmp_path / "collection", pair)
    before = tree_bytes(tmp_path)
    report = inspect_pair(tmp_path / "run", collection=tmp_path / "collection", show_input=True)
    assert tree_bytes(tmp_path) == before
    assert report["evaluator"]["identical_command_and_endpoint_groups"] == [["RELEASE", "STOP"]]
    assert report["evaluator"]["local_reference"]["reference_tokens"] == []
    assert "EVALUATOR ONLY" in render_text(report)
    without = inspect_pair(tmp_path / "run", show_input=True)
    assert report["validated_model_payloads"] == without["validated_model_payloads"]
    assert report["shared_effects"]["effects"] == {}


@pytest.mark.parametrize("failure", ["pair", "cache", "missing"])
def test_evaluator_join_does_not_guess_or_trust_cached_labels(tmp_path, failure):
    pair = pair_fixture()
    write_run(tmp_path / "run", [pair], decisions(pair))
    other = pair_fixture(init=1) if failure == "pair" else deepcopy(pair)
    write_collection(tmp_path / "collection", other, missing=failure == "missing", bad_cache=failure == "cache")
    if failure == "missing":
        report = inspect_pair(tmp_path / "run", collection=tmp_path / "collection")
        assert report["evaluator"]["status"] == "incomplete"
        assert report["evaluator"]["local_reference"] is None
        assert report["evaluator"]["missing_probes"] == ["GRASP"]
    else:
        with pytest.raises(ValueError, match="identical paired|cached evaluator"):
            inspect_pair(tmp_path / "run", collection=tmp_path / "collection")


def test_evaluator_before_state_must_match_source_features_when_recorded(tmp_path):
    pair = pair_fixture()
    pair["physical"]["features"] = {"remaining_open_mm": 999.}
    pair["pair_id"] = _sha256_json({k: v for k, v in pair.items() if k != "pair_id"})
    write_run(tmp_path / "run", [pair], decisions(pair))
    write_collection(tmp_path / "collection", pair)
    with pytest.raises(ValueError, match="before-state differs"):
        inspect_pair(tmp_path / "run", collection=tmp_path / "collection")


def test_cli_stdout_only_and_selection_errors(tmp_path, capsys):
    pair = pair_fixture()
    path = tmp_path / "run"
    write_run(path, [pair], decisions(pair))
    before = tree_bytes(path)
    main([str(path), "--list", "--format", "json"])
    assert json.loads(capsys.readouterr().out)["pairs"][0]["pair_id"] == pair["pair_id"]
    main([str(path), "--step", "0"])
    assert "State fields" in capsys.readouterr().out
    assert tree_bytes(path) == before
    with pytest.raises(SystemExit) as exc:
        main([str(path), "--step", "999"])
    assert exc.value.code == 2
