"""Offline predicate recognition versus frozen eleven-option Laya ranking."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..runtime_core import _sha256_json, load_laya_provider
from . import explicit_consequence as explicit
from .effect_binding import presented_support
from .interface_search import TOKENS, summarize
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import payload_id, run_call

VERSION = "predicate-verification-v0.1"
SOURCE_SHA256 = "d4e58fce0d961594090cf4124942e90cd6c044824951429d8ea8ee22e57acb0c"
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/predicate_verification_protocol.md"
ANSWER_LABELS = {"V0": "satisfies", "V1": "does_not_satisfy"}
TRAVERSAL = "parent_archive_order_control_then_11_canonical_tokens_alternating_answer_order_then_full_reverse"


def verification_fixture(parent, token, reverse=False):
    """Present one unchanged candidate bundle; evaluator labels never enter inputs."""
    if (parent.get("intervention", {}).get("version") != explicit.VERSION
            or parent["source"]["reverse"] or token not in TOKENS
            or parent["questions"]["action"]["instructions"] != explicit.QUESTIONS[parent["source"]["goal"]]
            or set(parent["option_to_canonical"].values()) != set(TOKENS)):
        raise ValueError("frozen explicit original-order eleven-option parent required")
    option = next(k for k, v in parent["option_to_canonical"].items() if v == token)
    description = parent["questions"]["action"]["criteria"][option]
    criterion = parent["questions"]["action"]["instructions"]
    order = list(reversed(ANSWER_LABELS)) if reverse else list(ANSWER_LABELS)
    result = deepcopy(parent)
    result.pop("fixture_id")
    result["condition"] = "predicate_verification"
    result["questions"] = {"action": {"type": "choice", "instructions": (
        "Determine whether this candidate satisfies the stated criterion. Criterion: "
        + criterion + "\nCandidate: " + description),
        "criteria": {key: ANSWER_LABELS[key] for key in order}}}
    result["option_order"] = order
    result["option_to_canonical"] = dict(ANSWER_LABELS)
    result["verification"] = {"version": VERSION, "parent_fixture_id": parent["fixture_id"],
                              "parent_payload_id": parent["payload_id"], "tested_token": token,
                              "tested_option": option, "answer_order_reversed": bool(reverse)}
    truth = presented_support(parent["source"], token)
    result["diagnostic_reference_not_model_input"] = {
        "scored_expected_tokens": ["satisfies" if truth else "does_not_satisfy"]}
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def frozen_source(path):
    path = Path(path)
    if file_hash(path / "episodes.jsonl") != SOURCE_SHA256:
        raise ValueError("not the frozen explicit-consequence source")
    rows, errors = load_records(path / "episodes.jsonl")
    baseline = summarize(path)
    if errors or not baseline["complete"] or not all(
            p["choice_equal"] and p["probabilities_equal"] and p["raw_logits_equal"]
            for p in baseline["repeat_comparisons"]):
        raise ValueError("complete stable source required")
    parents = [deepcopy(r["data"]) for r in rows if r["kind"] == "search_fixture"
               and r["data"].get("intervention", {}).get("version") == explicit.VERSION]
    if len(parents) != 32 or sum(not f["source"]["reverse"] for f in parents) != 16:
        raise ValueError("32 explicit controls and 16 original-order parents required")
    for f in parents:
        q = f["questions"]["action"]
        q["criteria"] = {k: q["criteria"][k] for k in f["option_order"]}
        if payload_id(f["state"], f["questions"]) != f["payload_id"]:
            raise ValueError("source payload/order mismatch")
    ids = {f["fixture_id"] for f in parents}
    return parents, [c for c in baseline["calls"] if c["fixture_id"] in ids], rows


def design(parents):
    fixtures = []
    for parent in parents:
        fixtures.append(deepcopy(parent))
        if not parent["source"]["reverse"]:
            for index, token in enumerate(TOKENS):
                for reverse in ((False, True) if index % 2 == 0 else (True, False)):
                    fixtures.append(verification_fixture(parent, token, reverse))
    return fixtures


def recorded_design(path, expected):
    rows, errors = load_records(Path(path) / "episodes.jsonl")
    if errors or [r["data"] for r in rows if r["kind"] == "search_fixture"] != expected:
        raise ValueError("recorded fixtures differ from frozen design")
    return rows


def one_record(rows, kind):
    values = [r["data"] for r in rows if r["kind"] == kind]
    if len(values) != 1:
        raise ValueError(f"exactly one {kind} required")
    return values[0]


def environment_difference(old, new):
    return {key: {"archived": old.get(key), "current": new.get(key)}
            for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)}


def run(args, *, preflight=False):
    parents, _, source_rows = frozen_source(args.source)
    fixtures = design(parents)
    if len(fixtures) != 384:
        raise ValueError("expected 352 binary and 32 control fixtures")
    current_code = code_identity()
    source_manifest = json.loads((Path(args.source) / "manifest.json").read_text())
    loaded_before = one_record(source_rows, "model_loaded")
    prior = None
    if not preflight:
        prior = recorded_design(args.preflight_source, fixtures)
        if one_record(prior, "termination") != {"reason": "predicate_verification_preflight_complete"}:
            raise ValueError("complete preflight required")
        start = one_record(prior, "run_start")
        if (start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or start["manifest"]["code"]["source_sha256"] != current_code["source_sha256"]):
            raise ValueError("protocol or code changed after preflight")
    source_artifacts = {name: file_hash(Path(args.source) / name)
                        for name in ("episodes.jsonl", "manifest.json", "resolved_config.yaml")}
    config = {"version": VERSION, "source": str(Path(args.source).resolve()),
              "source_sha256": SOURCE_SHA256, "source_artifacts": source_artifacts,
              "protocol_sha256": file_hash(PROTOCOL), "preflight_only": preflight,
              "fixture_ids": [f["fixture_id"] for f in fixtures], "repeats": 2, "seed": 1,
              "planned_binary_calls": 704, "planned_control_calls": 64,
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "no_execution": True, "privileged_effects": True, "traversal": TRAVERSAL,
              "device_requested": args.device}
    output = args.preflight if preflight else args.output
    recorder = RunRecorder(output, config, {"run_id": Path(output).name, "code": current_code, "versions": versions()})
    try:
        for fixture in fixtures:
            recorder.record("search_fixture", fixture)
        identity = model_identity(source_manifest["model"]["path"])
        recorder.manifest_update({"model": identity})
        if identity != source_manifest["model"]:
            raise ValueError("checkpoint differs from frozen source")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(identity["path"], subfolder=None, device=args.device).agent
        loaded = jsonable({"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        recorder.record("model_loaded", loaded)
        if any(loaded[k] != loaded_before[k] for k in ("config", "dtype")):
            raise ValueError("model configuration or dtype changed")
        environment = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                       "torch_threads": torch.get_num_threads(),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                       "device": str(agent.device),
                       "gpu_name": torch.cuda.get_device_name(agent.device) if str(agent.device).startswith("cuda") else None}
        recorder.record("inference_environment", environment)
        recorder.record("source_environment_difference", environment_difference(
            one_record(source_rows, "inference_environment"), environment))
        if prior and (one_record(prior, "model_loaded") != loaded
                      or one_record(prior, "inference_environment") != environment):
            raise ValueError("run environment differs from its preflight")
        prepared = []
        for fixture in fixtures:
            audit = encoding_audit(agent, fixture["state"], fixture["questions"])
            if not audit.get("available") or audit.get("truncated"):
                raise ValueError("complete unclipped presentation required")
            presentation = {"fixture_id": fixture["fixture_id"], **audit}
            prepared.append(presentation)
            recorder.record("provider_presentation", presentation)
        if prior and prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
            raise ValueError("presentation differs from preflight")
        if preflight:
            recorder.record("termination", {"reason": "predicate_verification_preflight_complete"})
        else:
            for repeat in range(2):
                traversal = fixtures if repeat == 0 else list(reversed(fixtures))
                for ordinal, fixture in enumerate(traversal):
                    run_call(agent, fixture, recorder, repeat=repeat, ordinal=ordinal)
            recorder.record("termination", {"reason": "predicate_verification_complete", "calls": len(fixtures)*2})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def validate_response(fixture, intent, response):
    """Recover only checked raw responses; never consume cached call analysis."""
    answer = response["raw_response"]["answers"]["action"]
    order, mapping = fixture["option_order"], fixture["option_to_canonical"]
    if answer["choice"] not in mapping or set(answer["probabilities"]) != set(mapping):
        raise ValueError("malformed answer/options")
    probabilities = np.asarray([answer["probabilities"][key] for key in order], dtype=float)
    if (not np.isfinite(probabilities).all() or (probabilities < 0).any()
            or abs(probabilities.sum()-1.) > .0006):
        raise ValueError("invalid probability distribution")
    traces = response["forward_traces"]
    if len(traces) != 1:
        raise ValueError("exactly one observed forward required")
    trace = traces[0]
    audit = intent["input_encoding"]["questions"]["action"]
    if trace["input_ids"] != [audit["effective_input_ids"]] or trace["option_markers"] != [audit["option_markers"]]:
        raise ValueError("consumed tokens or markers differ")
    if response["actual_device"] != intent["device_before"] or response["actual_dtype"] != intent["dtype_before"]:
        raise ValueError("device or dtype changed during inference")
    logits = np.asarray(trace["raw_option_logits"], dtype=float)
    temperature = intent["temperature"]
    if (logits.shape != (1, len(order)) or not np.isfinite(logits).all()
            or not np.isfinite(temperature["configured"])
            or temperature["effective"] != max(.001, temperature["configured"])):
        raise ValueError("invalid observed logits or temperature")
    if answer["choice"] != order[int(logits[0].argmax())]:
        raise ValueError("choice does not match observed scorer")
    scaled = logits[0] / temperature["effective"]
    observed = np.exp(scaled-scaled.max())
    observed /= observed.sum()
    if np.max(np.abs(observed-probabilities)) > .00006:
        raise ValueError("probabilities do not match observed scorer")
    return {"fixture_id": fixture["fixture_id"], "repeat": intent["repeat"],
            "choice": mapping[answer["choice"]], "probabilities": {mapping[k]: answer["probabilities"][k] for k in order},
            "raw_logits": trace["raw_option_logits"], "call_id": intent["call_id"]}


def recover_calls(rows, fixtures, presentations):
    by_id = {f["fixture_id"]: f for f in fixtures}
    intents, responses, calls, invalid = {}, {}, [], []
    for row in rows:
        kind, data = row["kind"], row["data"]
        if kind == "model_call_intent":
            cid = data["call_id"]
            fixture = by_id.get(data["fixture_id"])
            if fixture is None or cid in intents or cid != _sha256_json({
                    key: data[key] for key in ("fixture_id", "repeat", "ordinal")}):
                raise ValueError("invalid or duplicate call intent")
            repeat, ordinal = data["repeat"], data["ordinal"]
            traversal = fixtures if repeat == 0 else list(reversed(fixtures))
            if repeat not in (0, 1) or not 0 <= ordinal < len(fixtures) or traversal[ordinal]["fixture_id"] != data["fixture_id"]:
                raise ValueError("call traversal differs from protocol")
            if (data["payload_id"] != fixture["payload_id"]
                    or data["input_encoding"] != presentations[data["fixture_id"]]
                    or not data["input_encoding"].get("available") or data["input_encoding"].get("truncated")):
                raise ValueError("call input differs from complete preflight")
            intents[cid] = data
        elif kind == "model_raw_response":
            cid = data["call_id"]
            if cid not in intents or cid in responses:
                raise ValueError("orphan or duplicate response")
            responses[cid] = data
            intent = intents[cid]
            try:
                calls.append(validate_response(by_id[intent["fixture_id"]], intent, data))
            except (KeyError, ValueError, TypeError, IndexError) as exc:
                invalid.append({"call_id": cid, "fixture_id": intent["fixture_id"], "repeat": intent["repeat"], "reason": str(exc)})
    return calls, invalid, sorted(set(intents)-set(responses))


def confusion(fixtures, calls):
    """First-repeat counts; missing/invalid judgments never count as correct."""
    by_id = {c["fixture_id"]: c for c in calls if c["repeat"] == 0}
    result = {key: 0 for key in ("tp", "tn", "fp", "fn", "missing_positive", "missing_negative")}
    for fixture in fixtures:
        truth = presented_support(fixture["source"], fixture["verification"]["tested_token"])
        call = by_id.get(fixture["fixture_id"])
        if call is None:
            result["missing_positive" if truth else "missing_negative"] += 1
        else:
            positive = call["choice"] == "satisfies"
            result[("tp" if positive else "fn") if truth else ("fp" if positive else "tn")] += 1
    positives = result["tp"] + result["fn"] + result["missing_positive"]
    negatives = result["tn"] + result["fp"] + result["missing_negative"]
    result.update(planned=len(fixtures), positive_count=positives, negative_count=negatives,
                  sensitivity=result["tp"]/positives if positives else None,
                  specificity=result["tn"]/negatives if negatives else None)
    result["balanced_accuracy"] = ((result["sensitivity"]+result["specificity"])/2
                                   if positives and negatives else None)
    return result


def metrics(fixtures, calls, archived):
    binary = [f for f in fixtures if "verification" in f]
    controls = [f for f in fixtures if "verification" not in f]
    current = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(current) != len(calls):
        raise ValueError("duplicate fixture/repeat results")
    old = {(c["fixture_id"], c["repeat"]): c for c in archived}
    repeats, reproductions, orders, rankings = [], [], [], []
    for f in fixtures:
        a, b = (current.get((f["fixture_id"], rep)) for rep in (0, 1))
        repeats.append({"fixture_id": f["fixture_id"], "available": a is not None and b is not None,
                        **{f"{key}_equal": a is not None and b is not None and a[key] == b[key]
                           for key in ("choice", "probabilities", "raw_logits")}})
    for f in controls:
        for rep in (0, 1):
            a, b = old.get((f["fixture_id"], rep)), current.get((f["fixture_id"], rep))
            reproductions.append({"fixture_id": f["fixture_id"], "repeat": rep,
                                  "available": a is not None and b is not None,
                                  **{f"{key}_equal": a is not None and b is not None and a[key] == b[key]
                                     for key in ("choice", "probabilities", "raw_logits")}})
    indexed = {(f["verification"]["parent_fixture_id"], f["verification"]["tested_token"],
                f["verification"]["answer_order_reversed"]): f for f in binary}
    for parent_id, token, reverse in indexed:
        if reverse:
            continue
        a, b = (current.get((indexed[(parent_id, token, rev)]["fixture_id"], 0)) for rev in (False, True))
        orders.append({"parent_fixture_id": parent_id, "tested_token": token,
                       "available": a is not None and b is not None,
                       "choice_equal": a is not None and b is not None and a["choice"] == b["choice"]})
    for f in controls:
        if f["source"]["reverse"]:
            continue
        selected = old[(f["fixture_id"], 0)]["choice"]
        judgments = {}
        for rev in (False, True):
            binary_f = indexed[(f["fixture_id"], selected, rev)]
            call = current.get((binary_f["fixture_id"], 0))
            judgments[str(rev)] = call["choice"] if call else None
        rankings.append({"parent_fixture_id": f["fixture_id"], "goal": f["source"]["goal"],
                         "assignment": f["source"]["assignment"], "original_selected_token": selected,
                         "selected_satisfies_presented_predicate": presented_support(f["source"], selected),
                         "binary_judgments_of_selected": judgments})
    return {"binary_first_repeat": confusion(binary, calls),
            "per_goal_first_repeat": {goal: confusion([f for f in binary if f["source"]["goal"] == goal], calls)
                                      for goal in ("closed", "open")},
            "per_goal_assignment_first_repeat": {
                f"{goal}/{assignment}": confusion([f for f in binary if f["source"]["goal"] == goal
                                                  and f["source"]["assignment"] == assignment], calls)
                for goal in ("closed", "open") for assignment in ("true", "shift4")},
            "answer_order_comparisons_first_repeat": orders,
            "answer_order_stable": all(c["choice_equal"] for c in orders),
            "repeat_comparisons": repeats,
            "all_repeats_stable": all(c["choice_equal"] and c["probabilities_equal"] and c["raw_logits_equal"] for c in repeats),
            "archive_controls": reproductions,
            "archive_controls_reproduced": all(c["choice_equal"] and c["probabilities_equal"] and c["raw_logits_equal"] for c in reproductions),
            "binary_vs_original_ranking": rankings}


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    parents, archived, source_rows = frozen_source(config["source"])
    fixtures = design(parents)
    recorded_design(output, fixtures)
    if config["fixture_ids"] != [f["fixture_id"] for f in fixtures] or config["source_sha256"] != SOURCE_SHA256:
        raise ValueError("planned design identity differs")
    for name, digest in config["source_artifacts"].items():
        if file_hash(Path(config["source"]) / name) != digest:
            raise ValueError("source evidence changed")
    prior_path = Path(config["preflight_source"])
    if file_hash(prior_path / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight evidence changed")
    prior = recorded_design(prior_path, fixtures)
    if one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]:
        raise ValueError("protocol changed after preflight")
    presentations = [r["data"] for r in rows if r["kind"] == "provider_presentation"]
    if presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"] or len(presentations) != len(fixtures):
        raise ValueError("incomplete or changed presentations")
    prepared = {d["fixture_id"]: {k: v for k, v in d.items() if k != "fixture_id"} for d in presentations}
    for kind in ("model_loaded", "inference_environment"):
        if one_record(rows, kind) != one_record(prior, kind):
            raise ValueError("configuration/environment differs from preflight")
    loaded, baseline = one_record(rows, "model_loaded"), one_record(source_rows, "model_loaded")
    if any(loaded[k] != baseline[k] for k in ("config", "dtype")):
        raise ValueError("configuration or dtype differs from archived model")
    model = one_record(rows, "manifest_update")["model"]
    if model != one_record(source_rows, "manifest_update")["model"] or model["content_id"] != _sha256_json(model["files_sha256"]):
        raise ValueError("model identity differs")
    calls, invalid, unmatched = recover_calls(rows, fixtures, prepared)
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    result = metrics(fixtures, calls, archived)
    result.update(raw_sha256=file_hash(output / "episodes.jsonl"), calls=calls, invalid_calls=invalid,
                  unmatched_intents=unmatched, failures=failures, record_diagnostics=errors,
                  planned_calls=768, valid_calls=len(calls), missing_or_invalid_calls=768-len(calls),
                  complete=(len(calls) == 768 and not invalid and not unmatched and not failures and not errors
                            and terminal == [{"reason": "predicate_verification_complete", "calls": 768}]),
                  source_environment_difference=one_record(rows, "source_environment_difference"),
                  interpretation={"physical_utility_test": False, "execution_authorized": False,
                                  "cross_cardinality_probability_comparison": False,
                                  "all_frozen_obstacle_flags_false": True,
                                  "missing_judgments_count_as_incorrect": True})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="runs/explicit-consequence/laya-v01")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight")
    group.add_argument("--output")
    group.add_argument("--summarize")
    parser.add_argument("--preflight-source")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output and not args.preflight_source:
        parser.error("--output requires a completed --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
