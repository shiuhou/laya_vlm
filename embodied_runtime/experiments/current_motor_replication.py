"""Ten unchanged calls at preregistered current privileged motor boundaries."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..runtime_core import _sha256_json, load_laya_provider
from .predicate_verification import environment_difference, one_record, recover_calls, validate_response
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import payload_id, run_call

VERSION = "current-motor-replication-v0.1"
SOURCE_SHA256 = "9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2"
STEPS = (0, 1, 9, 10, 87)
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/current_motor_replication_protocol.md"


def select_boundaries(inputs, outcomes):
    """First two genuine calls per objective plus first lookahead, not by answer."""
    indexed = {d["snapshot_id"]: d for d in outcomes}
    seen, chosen, lookahead_seen = {}, set(), False
    for data in inputs:
        outcome = indexed[data["snapshot_id"]]
        if not outcome["genuine_laya_decision"] or data["candidate_count"] < 2:
            raise ValueError("model input must identify a genuine multi-option decision")
        objective = data["local_objective"]
        seen[objective] = seen.get(objective, 0) + 1
        if seen[objective] <= 2:
            chosen.add(outcome["step"])
        if data["pool_source"] == "lookahead" and not lookahead_seen:
            chosen.add(outcome["step"])
            lookahead_seen = True
    return sorted(chosen)


def make_fixture(saved, response, outcome, preview, record_ids):
    state, questions = deepcopy(saved["state"]), deepcopy(saved["questions"])
    order = saved["option_order"]
    criteria = questions["action"]["criteria"]
    if len(order) != len(set(order)) or set(criteria) != set(order):
        raise ValueError("invalid canonical option order")
    questions["action"]["criteria"] = {key: criteria[key] for key in order}
    if (len(order) != saved["candidate_count"] or len(order) < 2
            or saved["forced_singleton"] or not saved["model_called"]
            or saved["effect_source"] != "oracle_sim" or not saved["privileged"]
            or saved["objective_routing"]["motor_pool"] != order
            or preview["objective_routing"] != saved["objective_routing"]):
        raise ValueError("source pool or provenance mismatch")
    audit = saved["audit"]
    if not audit.get("available") or audit.get("truncated"):
        raise ValueError("source presentation must be complete")
    answer = response["raw_response"]["answers"]["action"]
    if (answer["choice"] not in order or set(answer["probabilities"]) != set(order)
            or answer["choice"] != outcome["action"] or not outcome["comparison"]["passed"]):
        raise ValueError("source response or execution mismatch")
    traces = response.get("forward_traces", [])
    if traces and (len(traces) != 1
                   or traces[0]["input_ids"] != [audit["questions"]["action"]["effective_input_ids"]]
                   or traces[0]["option_markers"] != [audit["questions"]["action"]["option_markers"]]):
        raise ValueError("source consumed input differs from audit")
    fixture = {"condition": "unchanged_current_motor", "state": state, "questions": questions,
               "option_order": list(order), "option_to_canonical": {key: key for key in order},
               "payload_id": payload_id(state, questions),
               "source": {"step": outcome["step"], "snapshot_id": saved["snapshot_id"],
                          "record_ids": record_ids, "objective": saved["local_objective"],
                          "pool_source": saved["pool_source"], "archived_audit": audit,
                          "archived_response": response, "archived_outcome": outcome,
                          "predictions": {key: preview["predictions"][key] for key in order}},
               "diagnostic_reference_not_model_input": {"scored_expected_tokens": None}}
    fixture["fixture_id"] = _sha256_json(fixture)
    return fixture


def frozen_source(path):
    path = Path(path)
    if file_hash(path / "episodes.jsonl") != SOURCE_SHA256:
        raise ValueError("not the preregistered frozen current motor source")
    rows, errors = load_records(path / "episodes.jsonl")
    if errors or one_record(rows, "termination").get("reason") != "success":
        raise ValueError("complete successful source required")
    by_kind = {}
    for row in rows:
        by_kind.setdefault(row["kind"], []).append(row)
    inputs = by_kind["reference_model_input"]
    outcomes = by_kind["reference_outcome"]
    steps = select_boundaries([r["data"] for r in inputs], [r["data"] for r in outcomes])
    if tuple(steps) != STEPS:
        raise ValueError("algorithmic selection differs from preregistered boundaries")
    fixtures = []
    for step in steps:
        outcome = next(r for r in outcomes if r["data"]["step"] == step)
        saved = next(r for r in inputs if r["data"]["snapshot_id"] == outcome["data"]["snapshot_id"])
        response = next(r for r in by_kind["demo_model_response"]
                        if r["data"]["snapshot_id"] == saved["data"]["snapshot_id"])
        preview = next(r for r in by_kind["reference_preview"]
                       if r["data"]["belief_id"] == saved["data"]["belief_id"])
        records = [saved, response, outcome, preview]
        fixtures.append(make_fixture(*(r["data"] for r in records),
                                     {r["kind"]: r["record_id"] for r in records}))
    return fixtures, rows, json.loads((path / "manifest.json").read_text())


def immediate_comparison(fixture, choice):
    source, effects = fixture["source"], {}
    for token in fixture["option_order"]:
        prediction = source["predictions"][token]
        effects[token] = {"closure_mm": prediction["closing_mm"],
                          "gap_reduction_mm": prediction["geometry_approach_mm"],
                          "target_contact": prediction["after"]["moving_contact"],
                          "obstacle_peak_N": prediction["peak_obstacle_force_N"],
                          "success": prediction["after"]["success"], "controls": prediction["steps"]}
        if "reposition_witness" in prediction:
            effects[token]["hypothetical_witness_not_executed"] = prediction["reposition_witness"]
    selected = effects[choice]
    alternatives = [token for token, effect in effects.items()
                    if effect["closure_mm"] > selected["closure_mm"] + 1e-9
                    and effect["gap_reduction_mm"] >= selected["gap_reduction_mm"] - 1e-9
                    and effect["target_contact"] >= selected["target_contact"]
                    and all(effect[key] == selected[key] for key in ("obstacle_peak_N", "success", "controls"))]
    return {"step": source["step"], "objective": source["objective"], "pool_source": source["pool_source"],
            "choice": choice, "candidate_order": fixture["option_order"], "effects": effects,
            "chosen_effect": selected, "maximum_gap_reduction_mm": max(e["gap_reduction_mm"] for e in effects.values()),
            "greater_closure_with_no_worse_reported_fields": alternatives,
            "strict_argmax_is_not_a_correctness_label": True,
            "witness_is_not_executed_sequence": source["pool_source"] == "lookahead",
            "source_executed_outcome": source["archived_outcome"], "new_execution": False}


def checked_call(agent, fixture, recorder, *, repeat, ordinal):
    captured = {}

    def record(kind, data):
        if kind in ("model_call_intent", "model_raw_response"):
            captured[kind] = data
        return recorder.record(kind, data)

    run_call(agent, fixture, SimpleNamespace(record=record), repeat=repeat, ordinal=ordinal)
    # Fail at this boundary, not only when the final independent report is built.
    return validate_response(fixture, captured["model_call_intent"], captured["model_raw_response"])


def run(args, *, preflight=False):
    fixtures, source_rows, manifest = frozen_source(args.source)
    current_code = code_identity()
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "current_motor_preflight_complete"}
                or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
            raise ValueError("completed matching preflight required")
        start = one_record(prior, "run_start")
        if (start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or start["manifest"]["code"]["source_sha256"] != current_code["source_sha256"]):
            raise ValueError("code or protocol changed after preflight")
    config = {"version": VERSION, "source": str(Path(args.source).resolve()),
              "source_artifacts": {name: file_hash(Path(args.source) / name) for name in
                                   ("episodes.jsonl", "manifest.json", "resolved_config.yaml")},
              "protocol_sha256": file_hash(PROTOCOL), "fixture_ids": [f["fixture_id"] for f in fixtures],
              "preflight_only": preflight, "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "planned_calls": 10, "repeats": 2, "seed": 1, "device_requested": args.device,
              "no_execution": True, "effect_source": "oracle_sim", "privileged": True}
    output = args.preflight if preflight else args.output
    recorder = RunRecorder(output, config, {"run_id": Path(output).name, "code": current_code,
                                          "versions": versions(), "source_code": manifest["code"]})
    try:
        for fixture in fixtures:
            recorder.record("search_fixture", fixture)
        identity = model_identity(manifest["models"]["decision"]["path"])
        if identity != manifest["models"]["decision"]:
            raise ValueError("checkpoint bytes differ from archive")
        recorder.manifest_update({"model": identity})
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(identity["path"], subfolder=None, device=args.device).agent
        loaded = jsonable({"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        recorder.record("model_loaded", loaded)
        if any(loaded[k] != manifest["model_execution"][k] for k in ("config", "dtype")):
            raise ValueError("model configuration/dtype differs from archive")
        environment = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                       "torch_threads": torch.get_num_threads(), "device": str(agent.device),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                       "gpu_name": torch.cuda.get_device_name(agent.device) if str(agent.device).startswith("cuda") else None}
        recorder.record("inference_environment", environment)
        archive_environment = {"cuda_visible_devices": one_record(source_rows, "reference_invocation")["environment"].get("CUDA_VISIBLE_DEVICES"),
                               "device": manifest["model_execution"]["device"],
                               "deterministic_algorithms": manifest["model_execution"]["torch_deterministic"]}
        recorder.record("source_environment_difference", environment_difference(archive_environment, environment))
        if prior and (one_record(prior, "model_loaded") != loaded
                      or one_record(prior, "inference_environment") != environment):
            raise ValueError("model/environment differs from preflight")
        prepared = []
        for fixture in fixtures:
            audit = encoding_audit(agent, fixture["state"], fixture["questions"])
            if audit != fixture["source"]["archived_audit"] or not audit.get("available") or audit.get("truncated"):
                raise ValueError("presentation differs from complete archive audit")
            presentation = {"fixture_id": fixture["fixture_id"], **audit}
            recorder.record("provider_presentation", presentation)
            prepared.append(presentation)
        if prior and prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
            raise ValueError("presentation differs from preflight")
        if preflight:
            recorder.record("termination", {"reason": "current_motor_preflight_complete"})
        else:
            for repeat in range(2):
                for ordinal, fixture in enumerate(fixtures if repeat == 0 else list(reversed(fixtures))):
                    checked_call(agent, fixture, recorder, repeat=repeat, ordinal=ordinal)
            recorder.record("termination", {"reason": "current_motor_replication_complete", "calls": 10})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    fixtures, _, manifest = frozen_source(config["source"])
    if [r["data"] for r in rows if r["kind"] == "search_fixture"] != fixtures:
        raise ValueError("recorded fixtures differ from source")
    if config["fixture_ids"] != [f["fixture_id"] for f in fixtures]:
        raise ValueError("planned fixtures differ")
    for name, digest in config["source_artifacts"].items():
        if file_hash(Path(config["source"]) / name) != digest:
            raise ValueError("source artifact changed")
    preflight_path = Path(config["preflight_source"])
    if file_hash(preflight_path / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight evidence changed")
    prior, diagnostics = load_records(preflight_path / "episodes.jsonl")
    if diagnostics or one_record(prior, "termination") != {"reason": "current_motor_preflight_complete"}:
        raise ValueError("invalid preflight")
    if one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]:
        raise ValueError("protocol lineage changed")
    for kind in ("model_loaded", "inference_environment", "manifest_update"):
        if one_record(rows, kind) != one_record(prior, kind):
            raise ValueError("model/environment changed after preflight")
    loaded = one_record(rows, "model_loaded")
    if (any(loaded[k] != manifest["model_execution"][k] for k in ("config", "dtype"))
            or one_record(rows, "manifest_update")["model"] != manifest["models"]["decision"]):
        raise ValueError("archive model identity changed")
    presentations = [r["data"] for r in rows if r["kind"] == "provider_presentation"]
    if presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
        raise ValueError("presentation differs from preflight")
    prepared = {p["fixture_id"]: {k: v for k, v in p.items() if k != "fixture_id"} for p in presentations}
    if prepared != {f["fixture_id"]: f["source"]["archived_audit"] for f in fixtures}:
        raise ValueError("presentation differs from archive")
    calls, invalid, unmatched = recover_calls(rows, fixtures, prepared)
    by_key = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(by_key) != len(calls):
        raise ValueError("duplicate fixture/repeat result")
    comparisons, repeats, effects = [], [], []
    for fixture in fixtures:
        archived = fixture["source"]["archived_response"]
        answer = archived["raw_response"]["answers"]["action"]
        logits = archived.get("forward_traces", [])
        a, b = [by_key.get((fixture["fixture_id"], rep)) for rep in (0, 1)]
        repeats.append({"step": fixture["source"]["step"], "available": a is not None and b is not None,
                        **{key + "_equal": a is not None and b is not None and a[key] == b[key]
                           for key in ("choice", "probabilities", "raw_logits")}})
        for repeat, call in enumerate((a, b)):
            comparisons.append({"step": fixture["source"]["step"], "repeat": repeat, "available": call is not None,
                                "choice_equal": call is not None and call["choice"] == answer["choice"],
                                "probabilities_equal": call is not None and call["probabilities"] == answer["probabilities"],
                                "archived_logits_available": bool(logits),
                                "raw_logits_equal": call["raw_logits"] == logits[0]["raw_option_logits"] if call and logits else None})
            if call:
                effects.append({"repeat": repeat, **immediate_comparison(fixture, call["choice"])})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    return {"version": VERSION, "raw_sha256": file_hash(output / "episodes.jsonl"), "planned_calls": 10,
            "valid_calls": len(calls), "calls": calls, "invalid_calls": invalid, "unmatched_intents": unmatched,
            "failures": failures, "record_diagnostics": errors, "archive_comparisons": comparisons,
            "repeat_comparisons": repeats, "immediate_effect_comparisons": effects,
            "archive_choices_and_probabilities_reproduced": all(c["choice_equal"] and c["probabilities_equal"] for c in comparisons),
            "all_repeats_exact": all(r["choice_equal"] and r["probabilities_equal"] and r["raw_logits_equal"] for r in repeats),
            "source_environment_difference": one_record(rows, "source_environment_difference"),
            "complete": len(calls) == 10 and not invalid and not unmatched and not failures and not errors
                        and terminal == [{"reason": "current_motor_replication_complete", "calls": 10}],
            "no_execution": True, "oracle_sim": True, "interaction_validity_not_established": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="runs/privileged-reference/local-objective-task-adapter-episode-01")
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
        print(json.dumps([{ "step": f["source"]["step"], "objective": f["source"]["objective"],
                           "pool_source": f["source"]["pool_source"], "candidates": f["option_order"],
                           "archived_choice": f["source"]["archived_response"]["raw_response"]["answers"]["action"]["choice"],
                           "payload_id": f["payload_id"]} for f in fixtures], indent=2))
    elif args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output and not args.preflight_source:
        parser.error("--output requires a complete --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
