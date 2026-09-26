"""Twelve Laya choices versus the existing nominal rule on sensor-only inputs."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..adapters.physics_preview import VisionCandidateBuilder
from ..decision_interface import (CanonicalDecisionInput, CanonicalDecisionState, geometric_effects,
                                  project_belief, shared_atomic_candidates)
from ..runtime_core import MOVE, _sha256_json, load_laya_provider
from .current_motor_replication import checked_call
from .predicate_verification import one_record, recover_calls
from .records import (RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity,
                      restore_snapshot, versions)
from .reference_model_diagnostic import APPROACH_INSTRUCTION, active_temperature, payload_id

VERSION = "approach-selector-probe-v0.1"
MODEL_PATH = "/home/junhongli/models/huggingface/laya/typed-decisions"
MODEL_ID = "9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704"
SOURCES = ((0, (0, 20, 24, 29), "d24b0d3d1d73c7618f69bb806168a719301e5806ddf6b68fec2dcc1e3e6a8b58"),
           (1, (0,), "95dc765928d5af123035a248efc7a89a6d590079d927ee59f8524e0c3d07432a"),
           (2, (0,), "41d07e9c6ed5db0bc28404ba5856ae71338981935852a12ef2aed180679ac1a5"))
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/approach_selector_probe_protocol.md"


def make_fixture(perceptual_state, natural_candidates, belief_record, projection, history, lineage):
    """No oracle argument: source labels cannot affect state, effects or selection."""
    state = CanonicalDecisionState.from_dict(perceptual_state)
    snapshot = restore_snapshot(belief_record["snapshot"])
    if (state.privileged or state.meta["branch"] != "perceptual"
            or state.meta["belief_id"] != snapshot.belief_id() or snapshot.belief_id() != belief_record["belief_id"]):
        raise ValueError("sensor/proprioceptive belief identity required")
    baseline_state = project_belief(snapshot, projection["target_query"])
    # The collector explicitly changed only the sensor estimand name after projection.
    if any(asdict(state.fields[key]) != asdict(value) for key, value in baseline_state.fields.items()
           if key != "target.position_definition"):
        raise ValueError("perceptual fields differ from reconstructed source belief")
    config = deepcopy(projection["natural_candidates"])
    if config.pop("version") != VisionCandidateBuilder.VERSION:
        raise ValueError("source candidate builder version changed")
    builder = VisionCandidateBuilder(**config)
    rebuilt = [candidate.canonical() for candidate in builder.build(snapshot)]
    if rebuilt != natural_candidates:
        raise ValueError("source natural allowed mask or gate evidence changed")
    allowed = [c["token"] for c in natural_candidates if c["feasible"]]
    candidates = tuple(c for c in shared_atomic_candidates() if c.token in allowed)
    if [c.token for c in candidates] != allowed or len(allowed) < 2:
        raise ValueError("non-singleton canonical natural pool required")
    raw_effects = geometric_effects(state, candidates)
    if raw_effects.privileged:
        raise ValueError("sensor-only geometric effects required")
    canonical = CanonicalDecisionInput(state, candidates, raw_effects, tuple(history))
    model_state = canonical.provider_input()
    full_presented_effects = model_state.pop("effects")
    assumptions = {e["assumptions"] for e in full_presented_effects.values() if e["source"] == "geometry"}
    if len(assumptions) != 1:
        raise ValueError("known common nominal geometry assumptions required")
    model_state["effects"] = {"source": "geometry", "privileged": False, "assumptions": next(iter(assumptions)),
                              "columns": ["distance_change_m", "xy_error_change_m"],
                              "rows": {token: [full_presented_effects[token]["values"][key] for key in
                                               ("distance_change_m", "xy_error_change_m")]
                                       if full_presented_effects[token]["source"] == "geometry" else None
                                       for token in allowed}}
    questions = canonical.model_questions()
    questions["action"]["instructions"] = APPROACH_INSTRUCTION
    rounded = replace(state, fields={key: replace(value, value=model_state["state"][key]) for key, value in state.fields.items()})
    rounded_canonical = CanonicalDecisionInput(rounded, candidates, geometric_effects(rounded, candidates), tuple(history))
    rule = canonical.rule_token()
    if rule != rounded_canonical.rule_token() or rule not in allowed:
        raise ValueError("rule differs with rounded model-visible geometry or is invalid")
    result = {"condition": "sensor_nominal_approach", "state": model_state, "questions": questions,
              "option_order": allowed, "option_to_canonical": {token: token for token in allowed},
              "payload_id": payload_id(model_state, questions),
              "source": {**lineage, "perceptual_state": perceptual_state,
                         "natural_candidates": natural_candidates, "canonical": asdict(canonical),
                         "rule_token": rule, "rule_is_deterministic_policy_not_expert_label": True,
                         "historically_accepted_sensor_estimate_not_verified_target": True},
              "diagnostic_reference_not_model_input": {"scored_expected_tokens": None}}
    result = jsonable(result)
    result["fixture_id"] = _sha256_json(result)
    return result


def frozen_sources(root):
    fixtures, hashes = [], {}
    for init, steps, expected_hash in SOURCES:
        path = Path(root) / f"init{init}-raycast-v02" / "episodes.jsonl"
        if file_hash(path) != expected_hash:
            raise ValueError("frozen sensor source identity mismatch")
        rows, errors = load_records(path)
        if errors or one_record(rows, "termination")["reason"] != "collection_smoke_complete":
            raise ValueError("complete source collection required")
        projection = one_record(rows, "projection_config")
        beliefs = {r["data"]["belief_id"]: r for r in rows if r["kind"] == "belief_fixture"}
        pairs = {r["data"]["physical"]["environment_step"]: r for r in rows if r["kind"] == "paired_state"}
        hashes[str(path.resolve())] = expected_hash
        for step in steps:
            row = pairs[step]
            pair = row["data"]
            if pair["pair_id"] != _sha256_json({k: v for k, v in pair.items() if k != "pair_id"}):
                raise ValueError("pair content identity changed")
            if pair["physical"]["init_state_id"] != init or pair["physical"]["variant"] != "fresh_capture":
                raise ValueError("registered physical source changed")
            perceptual = pair["perceptual_state"]
            belief = beliefs[perceptual["meta"]["belief_id"]]
            # Deliberately pass no oracle state or evaluator features to fixture construction.
            fixtures.append(make_fixture(perceptual, pair["natural_perceptual_candidates"], belief["data"],
                                         projection, pair["shared_history"],
                                         {"source_path": str(path.resolve()), "pair_id": pair["pair_id"],
                                          "pair_record_id": row["record_id"], "belief_record_id": belief["record_id"],
                                          "init_state_id": init, "environment_step": step}))
    if len(fixtures) != 6:
        raise ValueError("six registered sensor fixtures required")
    return fixtures, hashes


def tokenizer_agent():
    from transformers import AutoTokenizer
    return SimpleNamespace(tok=AutoTokenizer.from_pretrained(Path(MODEL_PATH) / "tokenizer", local_files_only=True),
                           cfg=json.loads((Path(MODEL_PATH) / "rl_agent_config.json").read_text()))


def presentations(agent, fixtures):
    result = []
    for fixture in fixtures:
        audit = encoding_audit(agent, fixture["state"], fixture["questions"])
        if not audit.get("available") or audit.get("truncated"):
            raise ValueError("complete state, effects and all natural candidates must fit")
        result.append({"fixture_id": fixture["fixture_id"], **audit})
    return result


def run(args, *, preflight=False):
    fixtures, source_hashes = frozen_sources(args.source_root)
    code = code_identity()
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "approach_selector_preflight_complete"}
                or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
            raise ValueError("complete matching CPU preflight required")
        start = one_record(prior, "run_start")
        if (start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or start["manifest"]["code"]["source_sha256"] != code["source_sha256"]):
            raise ValueError("code/protocol changed after CPU preflight")
    config = {"version": VERSION, "source_root": str(Path(args.source_root).resolve()), "source_hashes": source_hashes,
              "protocol_sha256": file_hash(PROTOCOL), "fixture_ids": [f["fixture_id"] for f in fixtures],
              "planned_calls": 12, "repeats": 2, "seed": 1, "preflight_only": preflight,
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "no_execution": True, "model_facing_privileged": False, "effect_source": "geometry",
              "oracle_evaluation_only_after_choice": True}
    output = Path(args.preflight if preflight else args.output)
    recorder = RunRecorder(output, config, {"run_id": output.name, "code": code, "versions": versions()})
    try:
        for fixture in fixtures:
            recorder.record("search_fixture", fixture)
        identity = model_identity(MODEL_PATH)
        if identity["content_id"] != MODEL_ID:
            raise ValueError("frozen Laya checkpoint changed")
        recorder.manifest_update({"model": identity})
        token_agent = tokenizer_agent()
        recorder.record("tokenizer_loaded", {"config": token_agent.cfg, "model_content_id": MODEL_ID})
        prepared = presentations(token_agent, fixtures)
        for item in prepared:
            recorder.record("provider_presentation", item)
        if preflight:
            recorder.record("termination", {"reason": "approach_selector_preflight_complete"})
            return
        if (prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]
                or one_record(prior, "tokenizer_loaded")["config"] != token_agent.cfg):
            raise ValueError("input/tokenizer differs from CPU preflight")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(MODEL_PATH, subfolder=None, device=args.device).agent
        loaded = jsonable({"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        recorder.record("model_loaded", loaded)
        if agent.cfg != token_agent.cfg or str(agent.dtype) != "torch.bfloat16":
            raise ValueError("model configuration or dtype differs from frozen Laya")
        recorder.record("inference_environment", {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                        "torch_threads": torch.get_num_threads(), "device": str(agent.device),
                        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                        "gpu_name": torch.cuda.get_device_name(agent.device) if str(agent.device).startswith("cuda") else None})
        if presentations(agent, fixtures) != prepared:
            raise ValueError("loaded model tokenizer differs from CPU preflight")
        for repeat in range(2):
            for ordinal, fixture in enumerate(fixtures if repeat == 0 else reversed(fixtures)):
                checked_call(agent, fixture, recorder, repeat=repeat, ordinal=ordinal)
        recorder.record("termination", {"reason": "approach_selector_complete", "calls": 12})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def nominal_gains(delta, allowed):
    vector = np.asarray(delta, dtype=float)
    return {token: 1000*(float(np.linalg.norm(vector))-float(np.linalg.norm(vector-.01*np.asarray(MOVE[token]))))
            if token in MOVE else None for token in allowed}


def evaluate_choice(fixture, choice, oracle_delta):
    """Evaluator receives the already made choice; never constructs a model input."""
    sensor = nominal_gains(fixture["state"]["state"]["relations.tcp_target_delta_m"], fixture["option_order"])
    oracle = nominal_gains(oracle_delta, fixture["option_order"])
    rule = fixture["source"]["rule_token"]
    best = max(value for value in sensor.values() if value is not None)
    oracle_best = max(value for value in oracle.values() if value is not None)
    return {"init_state_id": fixture["source"]["init_state_id"], "environment_step": fixture["source"]["environment_step"],
            "choice": choice, "rule_token": rule, "agrees_with_rule": choice == rule,
            "candidate_order": fixture["option_order"], "sensor_nominal_gains_mm": sensor,
            "selected_sensor_gain_mm": sensor[choice], "rule_sensor_gain_mm": sensor[rule],
            "sensor_nominal_regret_mm": None if sensor[choice] is None else best-sensor[choice],
            "effect_unknown": sensor[choice] is None, "gripper_change_contrary_to_objective": choice in ("GRASP", "RELEASE"),
            "oracle_evaluator_only_nominal_gains_mm": oracle,
            "selected_oracle_nominal_gain_mm": oracle[choice], "rule_oracle_nominal_gain_mm": oracle[rule],
            "oracle_nominal_best_tokens": [t for t, value in oracle.items() if value is not None and abs(value-oracle_best) <= 1e-9],
            "rule_matches_oracle_nominal_best": oracle[rule] is not None and abs(oracle[rule]-oracle_best) <= 1e-9,
            "physical_effect_measured": False, "rule_is_not_expert_label": True}


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    fixtures, hashes = frozen_sources(config["source_root"])
    if (hashes != config["source_hashes"] or [f["fixture_id"] for f in fixtures] != config["fixture_ids"]
            or [r["data"] for r in rows if r["kind"] == "search_fixture"] != fixtures):
        raise ValueError("source fixture design changed")
    prior_path = Path(config["preflight_source"])
    if file_hash(prior_path / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight evidence changed")
    prior, diagnostics = load_records(prior_path / "episodes.jsonl")
    if diagnostics or one_record(prior, "termination") != {"reason": "approach_selector_preflight_complete"}:
        raise ValueError("invalid preflight")
    if one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]:
        raise ValueError("protocol differs from preflight")
    model = one_record(rows, "manifest_update")["model"]
    if (model != one_record(prior, "manifest_update")["model"] or model["content_id"] != MODEL_ID
            or _sha256_json(model["files_sha256"]) != MODEL_ID):
        raise ValueError("frozen model lineage changed")
    for name, sha in model["files_sha256"].items():
        if not name.endswith((".safetensors", ".bin")) and file_hash(Path(model["path"]) / name) != sha:
            raise ValueError("local tokenizer/config changed")
    prepared = presentations(tokenizer_agent(), fixtures)
    if any([r["data"] for r in log if r["kind"] == "provider_presentation"] != prepared for log in (rows, prior)):
        raise ValueError("presentation differs from complete CPU preflight")
    loaded = one_record(rows, "model_loaded")
    if loaded["config"] != one_record(prior, "tokenizer_loaded")["config"] or loaded["dtype"] != "torch.bfloat16":
        raise ValueError("model settings changed")
    by_id = {fixture["fixture_id"]: fixture for fixture in fixtures}
    for row in rows:
        if row["kind"] == "model_call_intent":
            intent = row["data"]
            fixture = by_id[intent["fixture_id"]]
            if intent["temperature"] != active_temperature(SimpleNamespace(cfg=loaded["config"]), len(fixture["option_order"])):
                raise ValueError("recorded call temperature differs from frozen model configuration")
    audits = {p["fixture_id"]: {k: v for k, v in p.items() if k != "fixture_id"} for p in prepared}
    calls, invalid, unmatched = recover_calls(rows, fixtures, audits)
    indexed = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(indexed) != len(calls):
        raise ValueError("duplicate fixture/repeat result")
    comparisons, repeats = [], []
    for fixture in fixtures:
        a, b = [indexed.get((fixture["fixture_id"], repeat)) for repeat in (0, 1)]
        repeats.append({"fixture_id": fixture["fixture_id"], **{k+"_equal": a is not None and b is not None and a[k] == b[k]
                                                                for k in ("choice", "probabilities", "raw_logits")}})
        source_rows, _ = load_records(fixture["source"]["source_path"])
        pair = next(r["data"] for r in source_rows if r["kind"] == "paired_state" and r["data"]["pair_id"] == fixture["source"]["pair_id"])
        for repeat, call in enumerate((a, b)):
            if call:
                # Oracle fields are accessed only after a recorded choice exists.
                oracle_delta = pair["oracle_state"]["fields"]["relations.tcp_target_delta_m"]["value"]
                comparisons.append({"repeat": repeat, **evaluate_choice(fixture, call["choice"], oracle_delta)})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    return {"version": VERSION, "raw_sha256": file_hash(output / "episodes.jsonl"), "planned_calls": 12,
            "valid_calls": len(calls), "missing_or_invalid_calls": 12-len(calls), "calls": calls,
            "invalid_calls": invalid, "unmatched_intents": unmatched, "record_diagnostics": errors, "failures": failures,
            "repeat_comparisons": repeats, "all_repeats_exact": all(all(v for k, v in r.items() if k.endswith("_equal")) for r in repeats),
            "comparisons": comparisons, "no_execution": True, "model_facing_privileged": False,
            "complete": len(calls) == 12 and not invalid and not unmatched and not errors and not failures
                        and terminal == [{"reason": "approach_selector_complete", "calls": 12}],
            "scope": "nominal approach ranking using historically accepted sensor estimates; no physical utility guarantee"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default="runs/reference-pilot")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight")
    group.add_argument("--output")
    group.add_argument("--summarize")
    group.add_argument("--inspect-source", action="store_true")
    parser.add_argument("--preflight-source")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.inspect_source:
        fixtures, hashes = frozen_sources(args.source_root)
        prepared = presentations(tokenizer_agent(), fixtures)
        print(json.dumps({"source_hashes": hashes, "fixtures": [{"init": f["source"]["init_state_id"],
            "step": f["source"]["environment_step"], "options": f["option_order"], "rule": f["source"]["rule_token"],
            "tokens": p["questions"]["action"]["effective_token_count"]} for f, p in zip(fixtures, prepared)]}, indent=2))
    elif args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output and not args.preflight_source:
        parser.error("--output requires a complete CPU --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
