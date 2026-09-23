"""State the desired effect explicitly in frozen selective goal-last Laya questions."""
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
from . import clause_order as clause
from . import goal_placement as placement
from . import provider_comparison as comparison
from . import selective_grip as selective
from .effect_binding import QUESTION, effect_facts, presented_support
from .interface_search import COMPACT, TOKENS, summarize
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import payload_id, run_call

VERSION = "explicit-consequence-v0.1"
SOURCE_SHA256 = "032444bf8fe439e6ac2a84a7e0f7a4c59b760fc64ab5e00bceab28e74b628ad6"
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/explicit_consequence_protocol.md"
QUESTIONS = {
    "closed": "Choose an intervention with opening decreases, vs STOP lower, and obstacle no.",
    "open": "Choose an intervention with opening increases, vs STOP higher, and obstacle no.",
}


def explicit_fixture(parent):
    s = parent["source"]
    goal = s["goal"]
    if (goal not in QUESTIONS or s["descriptions"] != "native" or s["effect_detail"] != "relative"
            or parent.get("intervention", {}).get("version") != selective.VERSION
            or not parent["state"].endswith(clause.ORIGINAL + f" The requested state is {goal}.")):
        raise ValueError("frozen selective goal-last full-effect fixture required")
    if (list(parent["questions"]) != ["action"]
            or parent["questions"]["action"]["instructions"] != QUESTION
            or set(parent["option_to_canonical"].values()) != set(TOKENS)
            or list(parent["questions"]["action"]["criteria"]) != parent["option_order"]):
        raise ValueError("original eleven-option generic question required")
    facts = effect_facts(s)
    for option, token in parent["option_to_canonical"].items():
        nominal = "intervention" if token in selective.PREFIXES else COMPACT[TOKENS.index(token)]
        fact = facts[s["effect_assignment"][token]]
        suffix = (f"; opening {fact['opening']}; vs STOP {fact['vs_stop']}; "
                  f"obstacle {'yes' if fact['obstacle'] else 'no'}")
        if parent["questions"]["action"]["criteria"][option] != nominal + suffix:
            raise ValueError("exact selective descriptions and effect suffixes required")
    # Verify the explicit conjunction against the existing evaluator, offline only.
    required = {"opening": "decreases" if goal == "closed" else "increases",
                "vs_stop": "lower" if goal == "closed" else "higher", "obstacle": False}
    for token in TOKENS:
        if (facts[s["effect_assignment"][token]] == required) != presented_support(s, token):
            raise ValueError("explicit predicate disagrees with the existing evaluator")
    result = deepcopy(parent)
    del result["fixture_id"]
    result["questions"]["action"]["instructions"] = QUESTIONS[goal]
    result["intervention"] = {"version": VERSION, "question_condition": "explicit_consequence",
                              "parent_fixture_id": parent["fixture_id"], "parent_payload_id": parent["payload_id"],
                              "parent_intervention": deepcopy(parent["intervention"])}
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def frozen_source(path):
    path = Path(path)
    if file_hash(path / "episodes.jsonl") != SOURCE_SHA256:
        raise ValueError("not the frozen selective-grip source")
    baseline = selective.report(path)
    if not (baseline["complete"] and baseline["all_repeats_stable"] and baseline["archive_controls_reproduced"]):
        raise ValueError("complete stable selective-grip baseline required")
    rows, _ = load_records(path / "episodes.jsonl")
    originals = [r["data"] for r in rows if r["kind"] == "search_fixture"
                 and r["data"].get("intervention", {}).get("version") == selective.VERSION]
    if len(originals) != 32:
        raise ValueError("all 32 selective goal-last fixtures required")
    for f in originals:
        q = f["questions"]["action"]
        q["criteria"] = {k: q["criteria"][k] for k in f["option_order"]}
        if payload_id(f["state"], f["questions"]) != f["payload_id"]:
            raise ValueError("frozen payload/order mismatch")
    ids = {f["fixture_id"] for f in originals}
    calls = [p["after"] for p in baseline["matched_pairs"] if p["after"]["fixture_id"] in ids]
    return originals, calls


def design(originals):
    result = []
    for index, f in enumerate(originals):
        pair = [f, explicit_fixture(f)]
        result.extend(pair if index % 2 == 0 else reversed(pair))
    return result


def recorded_design(path, expected):
    rows, errors = load_records(Path(path) / "episodes.jsonl")
    if errors or [r["data"] for r in rows if r["kind"] == "search_fixture"] != expected:
        raise ValueError("recorded design differs from question-only intervention")
    return rows


def run(args, *, preflight=False):
    originals, _ = frozen_source(args.source)
    fs = design(originals)
    source_rows, _ = load_records(Path(args.source) / "episodes.jsonl")
    baseline_loaded = next(r["data"] for r in source_rows if r["kind"] == "model_loaded")
    baseline_manifest = json.loads((Path(args.source) / "manifest.json").read_text())
    current_code = code_identity()
    if any(current_code["source_sha256"].get(k) != v for k, v in baseline_manifest["code"]["source_sha256"].items()):
        raise ValueError("an existing inference/evaluator source changed")
    prior = None
    if not preflight:
        prior = recorded_design(args.preflight_source, fs)
        if [r["data"] for r in prior if r["kind"] == "termination"] != [{"reason": "explicit_consequence_preflight_complete"}]:
            raise ValueError("complete preflight required")
        if (prior[0]["data"]["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or prior[0]["data"]["manifest"]["code"]["source_sha256"] != current_code["source_sha256"]):
            raise ValueError("protocol or inference sources changed after preflight")
    config = {"version": VERSION, "provider": "laya", "source": str(Path(args.source).resolve()),
              "source_sha256": SOURCE_SHA256, "protocol_sha256": file_hash(PROTOCOL),
              "preflight_only": preflight, "fixture_ids": [f["fixture_id"] for f in fs],
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "repeats": 2, "seed": 1, "no_execution": True, "not_formal_e0": True,
              "privileged_effects": True, "traversal": "alternating_pair_order_then_full_reverse"}
    output = args.preflight if preflight else args.output
    recorder = RunRecorder(output, config, {"run_id": Path(output).name, "code": current_code, "versions": versions()})
    try:
        for f in fs:
            recorder.record("search_fixture", f)
        identity = model_identity(clause.MODEL_PATHS["laya"])
        recorder.manifest_update({"model": identity})
        if identity != baseline_manifest["model"] or identity["content_id"] != clause.MODEL_IDS["laya"]:
            raise ValueError("checkpoint differs from frozen Laya")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(identity["path"], subfolder=None, device=args.device).agent
        loaded = {"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)}
        recorder.record("model_loaded", loaded)
        environment = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                       "torch_threads": torch.get_num_threads(),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()}
        recorder.record("inference_environment", environment)
        old_environment = next(r["data"] for r in source_rows if r["kind"] == "inference_environment")
        if jsonable(loaded) != baseline_loaded or environment != old_environment:
            raise ValueError("configuration/environment differs from selective-grip baseline")
        prepared = []
        for f in fs:
            audit = encoding_audit(agent, f["state"], f["questions"])
            if not audit.get("available") or audit.get("truncated"):
                raise ValueError("complete unclipped presentation required")
            presentation = {"fixture_id": f["fixture_id"], **audit}
            prepared.append(presentation)
            recorder.record("provider_presentation", presentation)
        if prior and prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
            raise ValueError("presentation differs from preflight")
        if preflight:
            recorder.record("termination", {"reason": "explicit_consequence_preflight_complete"})
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


def report(output):
    output = Path(output)
    result = summarize(output)
    rows, _ = load_records(output / "episodes.jsonl")
    config = rows[0]["data"]["resolved_config"]
    originals, archived = frozen_source(config["source"])
    fs = design(originals)
    recorded_design(output, fs)
    if config["fixture_ids"] != [f["fixture_id"] for f in fs] or config["source_sha256"] != SOURCE_SHA256:
        raise ValueError("planned fixtures/source identity mismatch")
    prior_path = Path(config["preflight_source"])
    if file_hash(prior_path / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight evidence changed")
    prior = recorded_design(prior_path, fs)
    if config["protocol_sha256"] != prior[0]["data"]["resolved_config"]["protocol_sha256"]:
        raise ValueError("protocol changed after preflight")
    presentations = [r["data"] for r in rows if r["kind"] == "provider_presentation"]
    if presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
        raise ValueError("run presentations differ from preflight")
    prepared = {d["fixture_id"]: {k: v for k, v in d.items() if k != "fixture_id"} for d in presentations}
    if len(presentations) != len(fs) or set(prepared) != {f["fixture_id"] for f in fs}:
        raise ValueError("incomplete or duplicate presentations")
    for r in rows:
        if r["kind"] == "model_call_intent" and r["data"]["input_encoding"] != prepared[r["data"]["fixture_id"]]:
            raise ValueError("actual call differs from preflight")
    source_rows, _ = load_records(Path(config["source"]) / "episodes.jsonl")
    for kind in ("model_loaded", "inference_environment"):
        if [r["data"] for r in rows if r["kind"] == kind] != [r["data"] for r in source_rows if r["kind"] == kind]:
            raise ValueError("provider configuration/environment differs")
    model = next(r["data"]["model"] for r in rows if r["kind"] == "manifest_update")
    old_model = next(r["data"]["model"] for r in source_rows if r["kind"] == "manifest_update")
    if model != old_model or model["content_id"] != _sha256_json(model["files_sha256"]):
        raise ValueError("model content identity differs")
    calls = result["calls"]
    pairs, controls = selective.matched_calls(originals, fs, archived, calls)
    repeats = result["repeat_comparisons"]
    stable = len(repeats) == 64 and all(c["choice_equal"] and c["probabilities_equal"] and c["raw_logits_equal"] for c in repeats)
    reproduced = len(controls) == 64 and all(c["choice_equal"] and c["raw_equal"] for c in controls)
    complete = result["complete"] and len(calls) == 128 and len(pairs) == 64
    original_ids = {f["fixture_id"] for f in originals}
    control_calls = [c for c in calls if c["fixture_id"] in original_ids]
    explicit_calls = [c for c in calls if c["fixture_id"] not in original_ids]
    explicit_fs = [f for f in fs if f["fixture_id"] not in original_ids]
    assessed = comparison.assessments(explicit_fs, explicit_calls)
    gate = (complete and stable and reproduced and len(assessed) == 64
            and all(c["valid"] and c["presented_fact_consistent"] for c in assessed)
            and all(c["local_support"] for c in assessed if c["assignment"] == "true"))
    metrics = {}
    for label, fixtures, subset in (("control", originals, control_calls), ("explicit", explicit_fs, explicit_calls)):
        m = placement.binding_metrics(fixtures, subset)
        for c in m["calls"]:
            c["grip_probability_mass"] = sum(c["probabilities"].get(t, 0.) for t in selective.PREFIXES)
        m["reassignment_overlap"] = comparison.metrics(comparison.assessments(fixtures, subset))["contrasts_first_repeat"]["assignment"]
        metrics[label] = m
    return {"raw_sha256": file_hash(output / "episodes.jsonl"), "complete": complete,
            "failures": result["failures"], "record_diagnostics": result["record_diagnostics"],
            "all_repeats_stable": stable, "repeat_comparisons": repeats,
            "archive_controls_reproduced": reproduced, "archive_controls": controls,
            "matched_pairs": pairs, **metrics,
            "explicit_matching_gate_passed": gate, "formal_e0_ready": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="runs/selective-grip/laya-v01")
    p.add_argument("--preflight")
    p.add_argument("--preflight-source", default="runs/explicit-consequence/preflight-v01")
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
