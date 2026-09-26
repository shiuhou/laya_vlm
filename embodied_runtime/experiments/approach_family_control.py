"""One registered objective-family intervention on the frozen approach probe."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np

from ..runtime_core import MOVE, _sha256_json, load_laya_provider
from . import approach_selector_probe as parent
from .current_motor_replication import checked_call
from .predicate_verification import one_record, recover_calls
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import active_temperature, payload_id

VERSION = "approach-family-control-v0.1"
SOURCE_SHA256 = "2ed444a6ee96519a60b276df0462c0230f227676365464a5e4df5e72c17a947e"
NATURAL_ORDER = (*MOVE, "ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP")
FAMILY_ORDER = (*MOVE, "STOP")
REMOVED = ("ROTATE_CW", "ROTATE_CCW", "GRASP")
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/approach_family_control_protocol.md"


def family_fixture(original):
    """Only remove three menu entries and their unknown/null effect rows."""
    if (original["condition"] != "sensor_nominal_approach"
            or original["fixture_id"] != _sha256_json({k: v for k, v in original.items() if k != "fixture_id"})
            or tuple(original["option_order"]) != NATURAL_ORDER
            or original["option_to_canonical"] != {token: token for token in NATURAL_ORDER}
            or original["questions"]["action"]["instructions"] != parent.APPROACH_INSTRUCTION
            or original["payload_id"] != payload_id(original["state"], original["questions"])):
        raise ValueError("unchanged frozen ten-option approach fixture required")
    effect_rows = original["state"]["effects"]["rows"]
    if set(effect_rows) != set(NATURAL_ORDER) or any(effect_rows[token] is not None for token in (*REMOVED, "STOP")):
        raise ValueError("removed action effects and STOP effect must remain unknown")
    if original["source"]["rule_token"] not in FAMILY_ORDER:
        raise ValueError("existing deterministic comparator must remain eligible")
    result = deepcopy(original)
    del result["fixture_id"]
    result["condition"] = "sensor_nominal_approach_objective_family"
    result["option_order"] = list(FAMILY_ORDER)
    result["option_to_canonical"] = {token: token for token in FAMILY_ORDER}
    result["questions"]["action"]["criteria"] = {
        token: original["questions"]["action"]["criteria"][token] for token in FAMILY_ORDER}
    result["state"]["effects"]["rows"] = {token: deepcopy(effect_rows[token]) for token in FAMILY_ORDER}
    result["intervention"] = {
        "version": VERSION, "kind": "objective_family_admission",
        "parent_fixture_id": original["fixture_id"], "parent_payload_id": original["payload_id"],
        "natural_pool": list(NATURAL_ORDER), "objective_family_pool": list(FAMILY_ORDER),
        "removed": list(REMOVED), "rule_is_unchanged_comparator_not_selected_action": True,
        "basis": "existing objective requests a nominal 10mm translation with unchanged gripper; retain STOP fallback",
        "not_a_natural_gate_or_collision_certificate": True,
        "source_canonical_is_unchanged_ten_option_evidence": True}
    result["parent_fixture"] = deepcopy(original)
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result = jsonable(result)
    result["fixture_id"] = _sha256_json(result)
    return result


def frozen_source(path):
    path = Path(path)
    if file_hash(path / "episodes.jsonl") != SOURCE_SHA256:
        raise ValueError("frozen completed ten-option source identity mismatch")
    baseline = parent.report(path)
    if not baseline["complete"] or not baseline["all_repeats_exact"] or baseline["valid_calls"] != 12:
        raise ValueError("complete exactly repeated ten-option source required")
    rows, errors = load_records(path / "episodes.jsonl")
    originals, _ = parent.frozen_sources(one_record(rows, "run_start")["resolved_config"]["source_root"])
    if errors or [r["data"] for r in rows if r["kind"] == "search_fixture"] != originals:
        raise ValueError("recorded source fixtures differ from sensor source")
    return [family_fixture(f) for f in originals], baseline, rows


def run(args, *, preflight=False):
    fixtures, _, source_rows = frozen_source(args.source)
    code = code_identity()
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "approach_family_preflight_complete"}
                or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
            raise ValueError("completed matching CPU preflight required")
        start = one_record(prior, "run_start")
        if (start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or start["manifest"]["code"]["source_sha256"] != code["source_sha256"]):
            raise ValueError("code or protocol changed after CPU preflight")
    config = {"version": VERSION, "source": str(Path(args.source).resolve()), "source_sha256": SOURCE_SHA256,
              "protocol_sha256": file_hash(PROTOCOL), "fixture_ids": [f["fixture_id"] for f in fixtures],
              "planned_calls": 12, "repeats": 2, "seed": 1, "preflight_only": preflight,
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "no_execution": True, "model_facing_privileged": False, "effect_source": "geometry",
              "objective_family_intervention": True, "natural_gate_unchanged_in_source": True}
    output = Path(args.preflight if preflight else args.output)
    recorder = RunRecorder(output, config, {"run_id": output.name, "code": code, "versions": versions()})
    try:
        for fixture in fixtures:
            recorder.record("search_fixture", fixture)
        identity = model_identity(parent.MODEL_PATH)
        if identity != one_record(source_rows, "manifest_update")["model"] or identity["content_id"] != parent.MODEL_ID:
            raise ValueError("checkpoint differs from frozen ten-option source")
        recorder.manifest_update({"model": identity})
        token_agent = parent.tokenizer_agent()
        recorder.record("tokenizer_loaded", {"config": token_agent.cfg, "model_content_id": parent.MODEL_ID})
        if token_agent.cfg != one_record(source_rows, "model_loaded")["config"]:
            raise ValueError("model configuration differs from frozen source")
        prepared = parent.presentations(token_agent, fixtures)
        for item in prepared:
            recorder.record("provider_presentation", item)
        if preflight:
            recorder.record("termination", {"reason": "approach_family_preflight_complete"})
            return
        if (prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]
                or one_record(prior, "tokenizer_loaded")["config"] != token_agent.cfg):
            raise ValueError("input or tokenizer differs from CPU preflight")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(parent.MODEL_PATH, subfolder=None, device=args.device).agent
        loaded = jsonable({"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        recorder.record("model_loaded", loaded)
        if loaded != one_record(source_rows, "model_loaded"):
            raise ValueError("model configuration/device/dtype differs from frozen source")
        environment = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                       "torch_threads": torch.get_num_threads(), "device": str(agent.device),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                       "gpu_name": torch.cuda.get_device_name(agent.device) if str(agent.device).startswith("cuda") else None}
        recorder.record("inference_environment", environment)
        if environment != one_record(source_rows, "inference_environment"):
            raise ValueError("inference environment differs from frozen source")
        if parent.presentations(agent, fixtures) != prepared:
            raise ValueError("loaded model tokenizer differs from CPU preflight")
        for repeat in range(2):
            for ordinal, fixture in enumerate(fixtures if repeat == 0 else reversed(fixtures)):
                checked_call(agent, fixture, recorder, repeat=repeat, ordinal=ordinal)
        recorder.record("termination", {"reason": "approach_family_complete", "calls": 12})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    fixtures, baseline, source_rows = frozen_source(config["source"])
    if (config["source_sha256"] != SOURCE_SHA256 or config["fixture_ids"] != [f["fixture_id"] for f in fixtures]
            or [r["data"] for r in rows if r["kind"] == "search_fixture"] != fixtures):
        raise ValueError("registered family design changed")
    prior_path = Path(config["preflight_source"]) / "episodes.jsonl"
    if file_hash(prior_path) != config["preflight_sha256"]:
        raise ValueError("preflight evidence changed")
    prior, diagnostics = load_records(prior_path)
    if (diagnostics or one_record(prior, "termination") != {"reason": "approach_family_preflight_complete"}
            or one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]
            or one_record(prior, "run_start")["manifest"]["code"]["source_sha256"]
               != one_record(rows, "run_start")["manifest"]["code"]["source_sha256"]
            or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
        raise ValueError("complete matching preflight required")
    model = one_record(rows, "manifest_update")["model"]
    if (model != one_record(prior, "manifest_update")["model"]
            or model != one_record(source_rows, "manifest_update")["model"]):
        raise ValueError("model differs from source or preflight")
    for name, sha in model["files_sha256"].items():
        if not name.endswith((".safetensors", ".bin")) and file_hash(Path(model["path"]) / name) != sha:
            raise ValueError("local tokenizer/config changed")
    prepared = parent.presentations(parent.tokenizer_agent(), fixtures)
    if any([r["data"] for r in log if r["kind"] == "provider_presentation"] != prepared for log in (rows, prior)):
        raise ValueError("presentation differs from complete CPU preflight")
    loaded = one_record(rows, "model_loaded")
    if (loaded != one_record(source_rows, "model_loaded")
            or one_record(rows, "inference_environment") != one_record(source_rows, "inference_environment")
            or loaded["config"] != one_record(prior, "tokenizer_loaded")["config"]):
        raise ValueError("model settings or inference environment changed")
    expected_temperature = active_temperature(SimpleNamespace(cfg=loaded["config"]), len(FAMILY_ORDER))
    if any(r["data"]["temperature"] != expected_temperature for r in rows if r["kind"] == "model_call_intent"):
        raise ValueError("call temperature differs from frozen model configuration")
    audits = {p["fixture_id"]: {k: v for k, v in p.items() if k != "fixture_id"} for p in prepared}
    calls, invalid, unmatched = recover_calls(rows, fixtures, audits)
    indexed = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(indexed) != len(calls):
        raise ValueError("duplicate fixture/repeat result")
    parent_calls = {(c["fixture_id"], c["repeat"]): c for c in baseline["calls"]}
    parent_metrics = {(c["init_state_id"], c["environment_step"], c["repeat"]): c for c in baseline["comparisons"]}
    comparisons, repeats = [], []
    for fixture in fixtures:
        a, b = [indexed.get((fixture["fixture_id"], repeat)) for repeat in (0, 1)]
        repeats.append({"fixture_id": fixture["fixture_id"], **{k+"_equal": a is not None and b is not None and a[k] == b[k]
                                                                for k in ("choice", "probabilities", "raw_logits")}})
        for repeat, call in enumerate((a, b)):
            if call is None:
                continue
            # Read evaluator-only oracle geometry after this family's choice exists.
            source, _ = load_records(fixture["source"]["source_path"])
            pair = next(r["data"] for r in source if r["kind"] == "paired_state" and r["data"]["pair_id"] == fixture["source"]["pair_id"])
            oracle_delta = pair["oracle_state"]["fields"]["relations.tcp_target_delta_m"]["value"]
            parent_id = fixture["intervention"]["parent_fixture_id"]
            old = parent_calls[(parent_id, repeat)]
            metrics_key = (fixture["source"]["init_state_id"], fixture["source"]["environment_step"], repeat)
            comparisons.append({"fixture_id": fixture["fixture_id"], "parent_fixture_id": parent_id, "repeat": repeat,
                                "natural_choice": old["choice"], "family_choice": call["choice"],
                                "choice_changed": old["choice"] != call["choice"],
                                "natural_call_id": old["call_id"], "family_call_id": call["call_id"],
                                "natural_metrics": parent_metrics[metrics_key],
                                "family_metrics": parent.evaluate_choice(fixture, call["choice"], oracle_delta)})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    return {"version": VERSION, "raw_sha256": file_hash(output / "episodes.jsonl"), "source_sha256": SOURCE_SHA256,
            "planned_calls": 12, "valid_calls": len(calls), "missing_or_invalid_calls": 12-len(calls), "calls": calls,
            "invalid_calls": invalid, "unmatched_intents": unmatched, "record_diagnostics": errors, "failures": failures,
            "repeat_comparisons": repeats, "all_repeats_exact": all(all(v for k, v in r.items() if k.endswith("_equal")) for r in repeats),
            "comparisons": comparisons, "no_execution": True, "model_facing_privileged": False,
            "complete": len(calls) == 12 and not invalid and not unmatched and not errors and not failures
                        and terminal == [{"reason": "approach_family_complete", "calls": 12}],
            "scope": "one objective-family intervention; nominal geometric choice is not physical approach success"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="runs/autonomous-research/approach-selector-run-01")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight")
    group.add_argument("--output")
    group.add_argument("--summarize")
    group.add_argument("--inspect-source", action="store_true")
    parser.add_argument("--preflight-source")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.inspect_source:
        fixtures, _, _ = frozen_source(args.source)
        prepared = parent.presentations(parent.tokenizer_agent(), fixtures)
        print(json.dumps({"fixtures": [{"init": f["source"]["init_state_id"], "step": f["source"]["environment_step"],
              "options": f["option_order"], "rule": f["source"]["rule_token"],
              "tokens": p["questions"]["action"]["effective_token_count"]} for f, p in zip(fixtures, prepared)]}, indent=2))
    elif args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output and not args.preflight_source:
        parser.error("--output requires a complete CPU --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
