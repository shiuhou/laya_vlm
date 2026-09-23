"""One goal-sentence move on frozen Laya fixtures; no physical execution."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import random

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..runtime_core import _sha256_json, load_laya_provider
from . import clause_order as clause
from . import provider_comparison as comparison
from .effect_binding import effect_facts
from .interface_search import summarize
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import payload_id, run_call

VERSION = "goal-placement-v0.1"
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/goal_placement_protocol.md"


def move_fixture(parent):
    goal = parent["source"]["goal"]
    sentence = f"The requested state is {goal}."
    state = parent["state"]
    marker = " " + sentence + " "
    if (goal not in {"closed", "open"} or not isinstance(state, str)
            or state.count("The requested state is ") != 1 or marker not in state
            or not state.endswith(clause.ORIGINAL) or state.count(clause.ORIGINAL) != 1
            or parent["source"]["effect_detail"] != "relative"):
        raise ValueError("exact original full-effect state and goal required")
    observed, rules = state.split(marker)
    if observed != "The drawer is currently partly open." or not rules.startswith("Nominal moves are intents."):
        raise ValueError("goal must immediately follow the frozen articulation sentence")
    result = deepcopy(parent)
    del result["fixture_id"]
    result["state"] = observed + " " + rules + " " + sentence
    result["intervention"] = {"version": VERSION, "goal_position": "after_all_rules",
                              "parent_fixture_id": parent["fixture_id"],
                              "parent_payload_id": parent["payload_id"]}
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def design(original):
    result = []
    for index, f in enumerate(original):
        pair = [f, move_fixture(f)]
        result.extend(pair if index % 2 == 0 else reversed(pair))
    return result


def recorded_design(path, expected):
    rows, errors = load_records(Path(path) / "episodes.jsonl")
    if errors or [r["data"] for r in rows if r["kind"] == "search_fixture"] != expected:
        raise ValueError("recorded design differs from exact sentence move")
    return rows


def run(args, *, preflight=False):
    original, _ = comparison.frozen_source(args.source)
    fs = design(original)
    prior = None
    if not preflight:
        prior = recorded_design(args.preflight_source, fs)
        if [r["data"] for r in prior if r["kind"] == "termination"] != [{"reason": "goal_placement_preflight_complete"}]:
            raise ValueError("completed preflight required")
        if prior[0]["data"]["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL):
            raise ValueError("protocol changed after preflight")
    config = {"version": VERSION, "provider": "laya", "source": str(Path(args.source).resolve()),
              "source_sha256": comparison.SOURCE_SHA256, "protocol_sha256": file_hash(PROTOCOL),
              "preflight_only": preflight, "fixture_ids": [f["fixture_id"] for f in fs],
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "repeats": 2, "seed": 1, "no_execution": True, "not_formal_e0": True,
              "privileged_effects": True, "traversal": "alternating_pair_order_then_full_reverse"}
    output = args.preflight if preflight else args.output
    recorder = RunRecorder(output, config, {"run_id": Path(output).name,
                           "code": code_identity(), "versions": versions()})
    try:
        for f in fs:
            recorder.record("search_fixture", f)
        identity = model_identity(clause.MODEL_PATHS["laya"])
        recorder.manifest_update({"model": identity})
        if identity["content_id"] != clause.MODEL_IDS["laya"]:
            raise ValueError("checkpoint differs from frozen Laya")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(identity["path"], subfolder=None, device=args.device).agent
        loaded = {"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)}
        recorder.record("model_loaded", loaded)
        recorder.record("inference_environment", {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                        "torch_threads": torch.get_num_threads(),
                        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()})
        baseline_rows, _ = load_records(Path(args.source) / "episodes.jsonl")
        old_loaded = next(r["data"] for r in baseline_rows if r["kind"] == "model_loaded")
        if jsonable(loaded) != old_loaded:
            raise ValueError("loaded configuration differs from archived Laya")
        prepared = []
        for f in fs:
            audit = encoding_audit(agent, f["state"], f["questions"])
            if not audit.get("available") or audit.get("truncated"):
                raise ValueError("complete unclipped input required")
            presentation = {"fixture_id": f["fixture_id"], **audit}
            prepared.append(presentation)
            recorder.record("provider_presentation", presentation)
        if prior and prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
            raise ValueError("presentations differ from preflight")
        if preflight:
            recorder.record("termination", {"reason": "goal_placement_preflight_complete"})
        else:
            for repeat in range(2):
                for ordinal, f in enumerate(fs if repeat == 0 else list(reversed(fs))):
                    run_call(agent, f, recorder, repeat=repeat, ordinal=ordinal)
            recorder.record("termination", {"reason": "interface_search_complete", "calls": len(fs)*2})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def binding_metrics(fixtures, calls):
    """Disaggregate goal, fact assignment and ordering; never feeds inference."""
    fs = {f["fixture_id"]: f for f in fixtures}
    first = []
    groups = {}
    for c in comparison.assessments(fixtures, calls):
        if c["repeat"] != 0:
            continue
        f = fs[c["fixture_id"]]
        facts = effect_facts(f["source"])
        masses = {d: sum(c["probabilities"].get(t, 0.) for t in f["option_to_canonical"].values()
                         if clause.direction(f, t)["direction"] == d
                         and not facts[f["source"]["effect_assignment"][t]]["obstacle"])
                  for d in ("closed", "open")}
        row = {**c, **clause.direction(f, c["choice"]), "direction_probability_mass": masses}
        first.append(row)
        group_key = f"{c['descriptions']}/{c['assignment']}/{c['goal']}"
        g = groups.setdefault(group_key, {"n": 0, "facts_correct": 0, "actual_useful": 0,
                                         "directions": {}, "mean_closed_mass": 0., "mean_open_mass": 0.})
        g["n"] += 1
        g["facts_correct"] += c["presented_fact_consistent"]
        g["actual_useful"] += c["local_support"]
        g["directions"][row["direction"]] = g["directions"].get(row["direction"], 0) + 1
        for d in masses:
            g[f"mean_{d}_mass"] += masses[d]
    for g in groups.values():
        for d in ("closed", "open"):
            g[f"mean_{d}_mass"] /= g["n"]
    factors = ("descriptions", "assignment", "goal", "reverse")

    def key(c, overrides=None):
        values = {k: c[k] for k in factors}
        values.update(overrides or {})
        return (c["physical"]["init_state_id"], c["physical"]["environment_step"], *(values[k] for k in factors))

    lookup = {key(c): c for c in first}
    contrasts = {}
    for factor, before, after in (("goal", "closed", "open"), ("assignment", "true", "shift4"),
                                  ("reverse", False, True), ("descriptions", "native", "anonymous")):
        pairs = []
        for a in first:
            if a[factor] != before or key(a, {factor: after}) not in lookup:
                continue
            b = lookup[key(a, {factor: after})]
            pairs.append({"before": a, "after": b, "choice_changed": a["choice"] != b["choice"],
                          "direction_transition": a["direction"] + "->" + b["direction"],
                          "both_fact_consistent": a["presented_fact_consistent"] and b["presented_fact_consistent"],
                          "appropriate_goal_reversal": factor == "goal" and a["direction"] == "closed"
                              and b["direction"] == "open" and a["presented_fact_consistent"]
                              and b["presented_fact_consistent"] and a["choice"] != b["choice"]})
        contrasts[factor] = pairs
    return {"groups": groups, "contrasts": contrasts, "calls": first}


def report(output):
    output = Path(output)
    result = summarize(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = rows[0]["data"]["resolved_config"]
    original, archived = comparison.frozen_source(config["source"])
    fs = design(original)
    recorded_design(output, fs)
    preflight = Path(config["preflight_source"])
    if file_hash(preflight / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight evidence changed")
    prior = recorded_design(preflight, fs)
    presentations = [r["data"] for r in rows if r["kind"] == "provider_presentation"]
    if presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
        raise ValueError("run differs from preflight presentations")
    prepared = {d["fixture_id"]: {k: v for k, v in d.items() if k != "fixture_id"} for d in presentations}
    if len(presentations) != len(fs) or set(prepared) != {f["fixture_id"] for f in fs}:
        raise ValueError("incomplete or duplicate presentations")
    for r in rows:
        if r["kind"] == "model_call_intent" and r["data"]["input_encoding"] != prepared[r["data"]["fixture_id"]]:
            raise ValueError("actual call differs from prepared input")
    model = next(r["data"]["model"] for r in rows if r["kind"] == "manifest_update")
    old_rows, _ = load_records(Path(config["source"]) / "episodes.jsonl")
    loaded = next(r["data"] for r in rows if r["kind"] == "model_loaded")
    if (model["content_id"] != clause.MODEL_IDS["laya"] or _sha256_json(model["files_sha256"]) != model["content_id"]
            or loaded != next(r["data"] for r in old_rows if r["kind"] == "model_loaded")):
        raise ValueError("model identity/configuration mismatch")
    calls = result["calls"]
    original_ids = {f["fixture_id"] for f in original}
    same_session = [c for c in calls if c["fixture_id"] in original_ids]
    _, controls = clause.compare_calls(original, original, archived, same_session)
    pairs, _ = clause.compare_calls(original, fs, same_session, calls)
    repeats = result["repeat_comparisons"]
    stable = len(repeats) == 128 and all(c["choice_equal"] and c["probabilities_equal"] and c["raw_logits_equal"] for c in repeats)
    reproduced = len(controls) == 128 and all(c["choice_equal"] and c["raw_equal"] for c in controls)
    complete = result["complete"] and not errors and len(calls) == 256 and len(pairs) == 128
    new_calls = [c for c in calls if c["fixture_id"] not in original_ids]
    moved = [f for f in fs if "intervention" in f]
    judged = comparison.assessments(moved, new_calls)
    native = [c for c in judged if c["descriptions"] == "native"]
    gate = (complete and stable and reproduced and len(native) == 64
            and all(c["valid"] and c["presented_fact_consistent"] for c in native)
            and all(c["local_support"] for c in native if c["assignment"] == "true"))
    layout = []
    for f in moved:
        a = prepared[f["intervention"]["parent_fixture_id"]]["questions"]["action"]
        b = prepared[f["fixture_id"]]["questions"]["action"]
        layout.append({"fixture_id": f["fixture_id"], "original_tokens": a["effective_token_count"],
                       "moved_tokens": b["effective_token_count"],
                       "token_multiset_equal": Counter(a["effective_input_ids"]) == Counter(b["effective_input_ids"]),
                       "option_markers_equal": a["option_markers"] == b["option_markers"]})
    return {"raw_sha256": file_hash(output / "episodes.jsonl"), "complete": complete,
            "record_diagnostics": result["record_diagnostics"], "failures": result["failures"],
            "all_repeats_stable": stable, "repeat_comparisons": repeats,
            "archive_controls_reproduced": reproduced, "archive_controls": controls,
            "matched_pairs": pairs, "token_layout": layout,
            "original": binding_metrics(original, same_session), "moved": binding_metrics(moved, new_calls),
            "native_bounded_reference_passed": gate, "formal_e0_ready": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="runs/effect-binding/factorial-v01")
    p.add_argument("--preflight")
    p.add_argument("--preflight-source", default="runs/goal-placement/preflight-v01")
    p.add_argument("--output")
    p.add_argument("--summarize")
    p.add_argument("--device", default="cuda")
    args = p.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.preflight or args.output:
        run(args, preflight=bool(args.preflight))
    else:
        p.error("fresh preflight/output or existing run to summarize required")


if __name__ == "__main__":
    main()
