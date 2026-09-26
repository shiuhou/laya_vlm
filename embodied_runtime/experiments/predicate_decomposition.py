"""Fixed answer-spelling and clause diagnostic; no execution or prompt search."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import random
import re

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..runtime_core import _sha256_json, load_laya_provider
from .interface_search import fixture
from .predicate_verification import environment_difference, one_record, recorded_design, recover_calls
from .predicate_verification_audit import audit as audit_source
from .predicate_verification_audit import audit_response
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import run_call

VERSION = "predicate-decomposition-v0.1"
SOURCE_SHA256 = "47722f42f328af02d3fe534390bd78ad00a682126ea6d8b6886134943b14dd50"
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/predicate_decomposition_protocol.md"
CONDITIONS = ("full_control", "full_spaced", "opening_only", "stop_only")
LABELS = {"V0": "satisfies", "V1": "does_not_satisfy"}
PREFIX = "Determine whether this candidate satisfies the stated criterion. Criterion: "
SUFFIX = re.compile(r".+; opening (decreases|increases|unchanged); vs STOP (lower|higher|same); obstacle (yes|no)")


def clause_labels(source_fixture):
    """Evaluate the presented clauses from text and numerical effects separately."""
    instruction = source_fixture["questions"]["action"]["instructions"]
    if not instruction.startswith(PREFIX) or instruction.count("\nCandidate: ") != 1:
        raise ValueError("exact source wrapper required")
    criterion, candidate = instruction[len(PREFIX):].split("\nCandidate: ")
    match = SUFFIX.fullmatch(candidate)
    if match is None:
        raise ValueError("exact candidate effect suffix required")
    source = source_fixture["source"]
    goal = source["goal"]
    if goal not in ("closed", "open"):
        raise ValueError("known goal required")
    negative, positive = ("decreases", "lower") if goal == "closed" else ("increases", "higher")
    expected = f"Choose an intervention with opening {negative}, vs STOP {positive}, and obstacle no."
    if criterion != expected:
        raise ValueError("source full criterion mismatch")
    token = source_fixture["verification"]["tested_token"]
    effects = source["oracle_effects_not_model_input_as_numeric_table"]
    effect = effects[source["effect_assignment"][token]]
    delta, stop = effect["opening_change_mm"], effects["STOP"]["opening_change_mm"]
    if (not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (delta, stop))
            or type(effect["obstacle"]) is not bool):
        raise ValueError("finite numeric effects and known obstacle required")
    relative = delta - stop
    numeric = ("decreases" if delta < -.25 else "increases" if delta > .25 else "unchanged",
               "lower" if relative < -.25 else "higher" if relative > .25 else "same",
               "yes" if effect["obstacle"] else "no")
    if match.groups() != numeric:
        raise ValueError("presented text/numeric effect mismatch")
    opening, comparison = numeric[0] == negative, numeric[1] == positive
    sign = -1 if goal == "closed" else 1
    if opening != (sign * delta > .25) or comparison != (sign * relative > .25):
        raise ValueError("clause derivations disagree")
    if effect["obstacle"]:
        raise ValueError("registered source contains no obstacle-positive examples")
    return {"opening_only": opening, "stop_only": comparison,
            "full_control": opening and comparison, "full_spaced": opening and comparison}, criterion, candidate


def unique_groups(source_fixtures):
    """Group identical actual content; retain every source identity and order."""
    grouped, forward_count = {}, 0
    indexed = {(f["verification"]["parent_fixture_id"], f["verification"]["tested_token"],
                f["verification"]["answer_order_reversed"]): f for f in source_fixtures if "verification" in f}
    if len(indexed) != sum("verification" in f for f in source_fixtures):
        raise ValueError("duplicate source lineage")
    for (parent, token, reversed_order), f in indexed.items():
        if reversed_order:
            continue
        forward_count += 1
        partner = indexed[(parent, token, True)]
        truths, criterion, candidate = clause_labels(f)
        if clause_labels(partner) != (truths, criterion, candidate) or f["state"] != partner["state"]:
            raise ValueError("source answer-order facts differ")
        content = {"state": f["state"], "candidate": candidate, "criterion": criterion}
        group_id = _sha256_json(content)
        item = grouped.setdefault(group_id, {"group_id": group_id, **content, "goal": f["source"]["goal"],
                                            "truths_not_model_input": truths, "lineage": []})
        if item["truths_not_model_input"] != truths:
            raise ValueError("identical model content has contradictory labels")
        item["lineage"].append({"parent_fixture_id": parent, "tested_token": token,
                                "source_fixture_ids": {"forward": f["fixture_id"], "reversed": partner["fixture_id"]},
                                "physical": {k: f["source"]["physical"][k] for k in ("init_state_id", "environment_step")},
                                "assignment": f["source"]["assignment"]})
    if forward_count != 176 or len(grouped) != 74:
        raise ValueError("registered 176-to-74 content deduplication mismatch")
    if {goal: sum(g["goal"] == goal for g in grouped.values()) for goal in ("closed", "open")} != {"closed": 37, "open": 37}:
        raise ValueError("expected 37 unique inputs per goal")
    return [grouped[key] for key in sorted(grouped)]


def make_fixture(group, condition, reverse):
    if condition not in CONDITIONS or type(reverse) is not bool:
        raise ValueError("unknown condition or answer order")
    closed = group["goal"] == "closed"
    criterion = group["criterion"]
    if condition == "opening_only":
        criterion = "Judge only whether the stated opening " + ("decreases." if closed else "increases.")
    elif condition == "stop_only":
        criterion = "Judge only whether the stated opening is " + ("lower" if closed else "higher") + " than STOP."
    displayed = {"V0": "satisfies", "V1": "does_not_satisfy" if condition == "full_control" else "does not satisfy"}
    order = ["V1", "V0"] if reverse else ["V0", "V1"]
    truth = group["truths_not_model_input"][condition]
    return fixture(deepcopy(group["state"]), PREFIX + criterion + "\nCandidate: " + group["candidate"],
                   {key: displayed[key] for key in order}, condition=condition,
                   sample=group["group_id"] + "_reverse_" + str(int(reverse)),
                   answer=["satisfies" if truth else "does_not_satisfy"],
                   source={"version": VERSION, "group_id": group["group_id"], "goal": group["goal"],
                           "answer_order_reversed": reverse}, mapping=dict(LABELS), effects_supplied=True)


def design(groups):
    return [make_fixture(g, condition, reverse) for g in groups for condition in CONDITIONS for reverse in (False, True)]


def frozen_source(path):
    path = Path(path)
    if file_hash(path / "episodes.jsonl") != SOURCE_SHA256:
        raise ValueError("frozen binary source identity mismatch")
    checked = audit_source(path)
    if not all(checked[k] for k in ("complete", "archive_controls_reproduced", "all_repeats_stable")):
        raise ValueError("complete stable independently audited source required")
    rows, errors = load_records(path / "episodes.jsonl")
    if errors:
        raise ValueError("source has incomplete records")
    fs = [r["data"] for r in rows if r["kind"] == "search_fixture"]
    groups = unique_groups(fs)
    by_id = {f["fixture_id"]: f for f in fs}
    intents = {r["data"]["call_id"]: r["data"] for r in rows if r["kind"] == "model_call_intent"}
    archived = {}
    for row in rows:
        if row["kind"] != "model_raw_response":
            continue
        d = row["data"]
        i = intents[d["call_id"]]
        if "verification" not in by_id[i["fixture_id"]]:
            continue
        archived[(i["fixture_id"], i["repeat"])] = audit_response(by_id[i["fixture_id"]], i, d, i["input_encoding"])
    return groups, rows, archived


def run(args, *, preflight=False):
    groups, source_rows, _ = frozen_source(args.source)
    fixtures = design(groups)
    code = code_identity()
    source_manifest = json.loads((Path(args.source) / "manifest.json").read_text())
    before = one_record(source_rows, "model_loaded")
    prior = None
    if not preflight:
        prior = recorded_design(args.preflight_source, fixtures)
        if one_record(prior, "termination") != {"reason": "predicate_decomposition_preflight_complete"}:
            raise ValueError("complete preflight required")
        start = one_record(prior, "run_start")
        if (start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or start["manifest"]["code"]["source_sha256"] != code["source_sha256"]):
            raise ValueError("protocol/code changed after preflight")
    config = {"version": VERSION, "source": str(Path(args.source).resolve()), "source_sha256": SOURCE_SHA256,
              "protocol_sha256": file_hash(PROTOCOL), "preflight_only": preflight,
              "fixture_ids": [f["fixture_id"] for f in fixtures], "group_ids": [g["group_id"] for g in groups],
              "repeats": 2, "seed": 1, "planned_calls": 1184, "no_execution": True, "privileged_effects": True,
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None}
    output = args.preflight if preflight else args.output
    recorder = RunRecorder(output, config, {"run_id": Path(output).name, "code": code, "versions": versions()})
    try:
        for group in groups:
            recorder.record("predicate_group", group)
        for f in fixtures:
            recorder.record("search_fixture", f)
        identity = model_identity(source_manifest["model"]["path"])
        recorder.manifest_update({"model": identity})
        if identity != source_manifest["model"]:
            raise ValueError("checkpoint changed")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(identity["path"], subfolder=None, device=args.device).agent
        loaded = jsonable({"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        recorder.record("model_loaded", loaded)
        if any(loaded[k] != before[k] for k in ("config", "dtype")):
            raise ValueError("checkpoint configuration/dtype changed")
        environment = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                       "torch_threads": torch.get_num_threads(),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                       "device": str(agent.device),
                       "gpu_name": torch.cuda.get_device_name(agent.device) if str(agent.device).startswith("cuda") else None}
        recorder.record("inference_environment", environment)
        recorder.record("source_environment_difference", environment_difference(one_record(source_rows, "inference_environment"), environment))
        if prior and (one_record(prior, "model_loaded") != loaded or one_record(prior, "inference_environment") != environment):
            raise ValueError("environment differs from preflight")
        presentations = []
        for f in fixtures:
            encoded = encoding_audit(agent, f["state"], f["questions"])
            if not encoded.get("available") or encoded.get("truncated"):
                raise ValueError("complete unclipped input required")
            item = {"fixture_id": f["fixture_id"], **encoded}
            recorder.record("provider_presentation", item)
            presentations.append(item)
        if prior and presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
            raise ValueError("presentations changed after preflight")
        if preflight:
            recorder.record("termination", {"reason": "predicate_decomposition_preflight_complete"})
        else:
            for repeat in range(2):
                for ordinal, f in enumerate(fixtures if repeat == 0 else reversed(fixtures)):
                    run_call(agent, f, recorder, repeat=repeat, ordinal=ordinal)
            recorder.record("termination", {"reason": "predicate_decomposition_complete", "calls": 1184})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def confusion(fixtures, calls):
    indexed = {c["fixture_id"]: c for c in calls if c["repeat"] == 0}
    counts = dict.fromkeys(("tp", "tn", "fp", "fn", "missing_positive", "missing_negative"), 0)
    for f in fixtures:
        truth = f["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == ["satisfies"]
        call = indexed.get(f["fixture_id"])
        if call is None:
            counts["missing_positive" if truth else "missing_negative"] += 1
        else:
            positive = call["choice"] == "satisfies"
            counts[("tp" if positive else "fn") if truth else ("fp" if positive else "tn")] += 1
    positives = counts["tp"] + counts["fn"] + counts["missing_positive"]
    negatives = counts["tn"] + counts["fp"] + counts["missing_negative"]
    sensitivity = counts["tp"] / positives if positives else None
    specificity = counts["tn"] / negatives if negatives else None
    return {**counts, "planned": len(fixtures), "positives": positives, "negatives": negatives,
            "sensitivity": sensitivity, "specificity": specificity,
            "balanced_accuracy": (sensitivity + specificity) / 2 if positives and negatives else None}


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    groups, source_rows, archived = frozen_source(config["source"])
    fixtures = design(groups)
    recorded_design(output, fixtures)
    if [r["data"] for r in rows if r["kind"] == "predicate_group"] != groups:
        raise ValueError("lineage/group evidence changed")
    if config["fixture_ids"] != [f["fixture_id"] for f in fixtures] or config["source_sha256"] != SOURCE_SHA256:
        raise ValueError("registered design identity changed")
    prior_path = Path(config["preflight_source"])
    if file_hash(prior_path / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight source changed")
    prior = recorded_design(prior_path, fixtures)
    if one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]:
        raise ValueError("protocol differs from preflight")
    presentations = [r["data"] for r in rows if r["kind"] == "provider_presentation"]
    if len(presentations) != 592 or presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
        raise ValueError("presentation coverage/preflight mismatch")
    for kind in ("model_loaded", "inference_environment"):
        if one_record(rows, kind) != one_record(prior, kind):
            raise ValueError("environment changed since preflight")
    model = one_record(rows, "manifest_update")["model"]
    if model != one_record(source_rows, "manifest_update")["model"] or model["content_id"] != _sha256_json(model["files_sha256"]):
        raise ValueError("model identity mismatch")
    loaded, before = one_record(rows, "model_loaded"), one_record(source_rows, "model_loaded")
    if any(loaded[k] != before[k] for k in ("config", "dtype")):
        raise ValueError("model configuration/dtype mismatch")
    prepared = {d["fixture_id"]: {k: v for k, v in d.items() if k != "fixture_id"} for d in presentations}
    calls, invalid, unmatched = recover_calls(rows, fixtures, prepared)
    # Use the separate raw auditor for forwarded IDs, usage, cardinality and temperature checks too.
    by_id = {f["fixture_id"]: f for f in fixtures}
    intents = {r["data"]["call_id"]: r["data"] for r in rows if r["kind"] == "model_call_intent"}
    rejected = {c["call_id"] for c in invalid}
    for row in rows:
        if row["kind"] != "model_raw_response" or row["data"]["call_id"] in rejected:
            continue
        d = row["data"]
        i = intents[d["call_id"]]
        try:
            audit_response(by_id[i["fixture_id"]], i, d, prepared[i["fixture_id"]])
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            invalid.append({"call_id": d["call_id"], "reason": str(exc)})
            rejected.add(d["call_id"])
    calls = [c for c in calls if c["call_id"] not in rejected]
    indexed = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(indexed) != len(calls):
        raise ValueError("duplicate fixture/repeat result")
    repeats, controls, orders, contrasts = [], [], [], []
    for f in fixtures:
        a, b = (indexed.get((f["fixture_id"], rep)) for rep in (0, 1))
        repeats.append({"fixture_id": f["fixture_id"], **{k + "_equal": a is not None and b is not None and a[k] == b[k]
                                                        for k in ("choice", "probabilities", "raw_logits")}})
    fs = {(f["source"]["group_id"], f["condition"], f["source"]["answer_order_reversed"]): f for f in fixtures}
    for g in groups:
        for condition in CONDITIONS:
            pair = [indexed.get((fs[(g["group_id"], condition, rev)]["fixture_id"], 0)) for rev in (False, True)]
            orders.append({"group_id": g["group_id"], "condition": condition,
                           "available": all(c is not None for c in pair),
                           "choice_equal": all(c is not None for c in pair) and pair[0]["choice"] == pair[1]["choice"]})
        for rev in (False, True):
            contrasts.append({"group_id": g["group_id"], "goal": g["goal"], "reversed": rev,
                              "truths": g["truths_not_model_input"], "choices": {
                                  cond: indexed.get((fs[(g["group_id"], cond, rev)]["fixture_id"], 0), {}).get("choice")
                                  for cond in CONDITIONS}})
            f = fs[(g["group_id"], "full_control", rev)]
            for lineage in g["lineage"]:
                old_id = lineage["source_fixture_ids"]["reversed" if rev else "forward"]
                for repeat in (0, 1):
                    a, b = indexed.get((f["fixture_id"], repeat)), archived[(old_id, repeat)]
                    # Previous independent auditor stores probabilities by V0/V1; current recovery uses canonical labels.
                    old_prob = {LABELS[k]: v for k, v in b["probabilities"].items()}
                    controls.append({"fixture_id": f["fixture_id"], "source_fixture_id": old_id, "repeat": repeat,
                                     "choice_equal": a is not None and a["choice"] == b["choice"],
                                     "probabilities_equal": a is not None and a["probabilities"] == old_prob,
                                     "raw_logits_equal": a is not None and a["raw_logits"] == b["raw_logits"]})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    def stable(items):
        return all(all(v for k, v in item.items() if k.endswith("_equal")) for item in items)
    return {"raw_sha256": file_hash(output / "episodes.jsonl"), "planned_calls": 1184, "valid_calls": len(calls),
            "missing_or_invalid_calls": 1184 - len(calls), "invalid_calls": invalid, "unmatched_intents": unmatched,
            "failures": failures, "record_diagnostics": errors,
            "complete": len(calls) == 1184 and not invalid and not unmatched and not failures and not errors
                        and terminal == [{"reason": "predicate_decomposition_complete", "calls": 1184}],
            "per_condition_first_repeat": {c: confusion([f for f in fixtures if f["condition"] == c], calls) for c in CONDITIONS},
            "per_goal_condition_first_repeat": {goal + "/" + c: confusion([f for f in fixtures if f["condition"] == c
                                                and f["source"]["goal"] == goal], calls)
                                                for goal in ("closed", "open") for c in CONDITIONS},
            "repeat_comparisons": repeats, "all_repeats_stable": len(repeats) == 592 and stable(repeats),
            "archive_controls": controls, "archive_controls_reproduced": len(controls) == 704 and stable(controls),
            "answer_order_comparisons": orders, "matched_conditions_first_repeat": contrasts,
            "calls": calls, "scope": "deduplicated offline language diagnostic; no physical utility, calibration or execution claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="runs/autonomous-research/predicate-verification-run-01")
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
        parser.error("--output requires completed --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
