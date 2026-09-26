"""One frozen native-criterion duplication of existing printed progress values."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import re
from types import SimpleNamespace

import numpy as np

from ..runtime_core import _sha256_json, load_laya_provider
from . import current_motor_replication as parent
from . import action_semantics_binding as binding
from . import joint_interface_sufficiency as joint
from ..adapters.laya_input import encoding_audit
from .approach_selector_probe import MODEL_ID, MODEL_PATH, presentations, tokenizer_agent
from .predicate_verification import environment_difference, one_record, recover_calls
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import active_temperature, payload_id

VERSION = "native-option-progress-sufficiency-v0.1"
STEPS = (0, 1, 10)
ALL_STEPS = (0, 1, 9, 10)
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/native_option_progress_sufficiency_protocol.md"
DESIGN_PATH = Path("/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/option-progress-binding-design-01.json")
DESIGN_SHA256 = "272dc7c7cf67136f5fa740884560f3327c8a27dd5518b2c6341ac92c32253dc4"
component_audit = binding.component_audit
archive_audit = joint.archive_audit


def criterion_values(state, options):
    """Copy original printed strings using only existing visible state and options."""
    phase = re.match(r"Current local objective: (\w+)\.\n", state)
    fields = {"approach_target": ("gap_reduction_mm", 2), "advance_target": ("closure_mm", 1)}
    if phase is None or phase[1] not in fields:
        raise ValueError("known visible current objective required")
    if "Task: close top drawer. effect_source=oracle_sim; privileged=true." not in state:
        raise ValueError("known privileged top-drawer source required")
    field, index = fields[phase[1]]
    if state.count("Effects: ") != 1:
        raise ValueError("one unchanged visible effect table required")
    lines = state.split("Effects: ", 1)[1].splitlines()
    expected_header = ("action|closure_mm (positive closes)|gap_reduction_mm (positive approaches)|"
                       "target_contact|obstacle_peak_N|success|controls")
    if lines[0] != expected_header:
        raise ValueError("known complete effect schema required")
    rows = [line.split("|") for line in lines[1:] if line]
    if (not options or len(options) != len(set(options)) or any(len(row) != 7 for row in rows)
            or [row[0] for row in rows] != options
            or any(re.fullmatch(r"-?\d+\.\d+", row[index]) is None for row in rows)):
        raise ValueError("exact option-ordered printed effect rows required")
    values = {row[0]: row[index] for row in rows}
    return field, values, {key: f"{field}={values[key]}" for key in options}


def progress_fixture(original):
    if (original["fixture_id"] != _sha256_json({k: v for k, v in original.items() if k != "fixture_id"})
            or original["condition"] != "unchanged_current_motor"
            or original["payload_id"] != payload_id(original["state"], original["questions"])):
        raise ValueError("unmodified baseline identity required")
    question = original["questions"]["action"]
    if (question["type"] != "choice" or list(question["criteria"]) != original["option_order"]
            or any(value != "" for value in question["criteria"].values())):
        raise ValueError("original empty ordered choice criteria required")
    field, values, criteria = criterion_values(original["state"], original["option_order"])
    result = deepcopy(original)
    result.pop("fixture_id")
    result["condition"] = "native_option_progress_duplication"
    result["questions"]["action"]["criteria"] = criteria
    result["intervention"] = {
        "version": VERSION, "parent_fixture_id": original["fixture_id"],
        "criterion_grammar": "<existing task-progress field>=<verbatim original printed row number>",
        "field": field, "original_printed_values": values,
        "provenance": "same value copied from each original visible row into its native criterion",
        "state_unchanged": True, "no_state_prefix": True, "no_new_physical_observation_or_effect": True,
        "no_action_ranking_or_direction_recommendation": True,
        "estimand": "total sufficiency of local progress-value duplication, not isolated semantic binding",
    }
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def design(source):
    originals, rows, manifest = parent.frozen_source(source)
    selected = [f for f in originals if f["source"]["step"] in STEPS]
    if tuple(f["source"]["step"] for f in selected) != STEPS:
        raise ValueError("three registered budget-eligible boundaries required")
    return [progress_fixture(f) for f in selected], rows, manifest


def budget_audit(agent, source):
    """Match the sole CPU design; complete total length alone cannot certify options."""
    from laya.common import render_options, serialize_state
    if file_hash(DESIGN_PATH) != DESIGN_SHA256:
        raise ValueError("one frozen CPU design artifact required")
    prior = json.loads(DESIGN_PATH.read_text())
    if prior["config"] != agent.cfg or prior["source_sha256"] != parent.SOURCE_SHA256:
        raise ValueError("source or tokenizer changed from sole design check")
    by_step = {d["step"]: d for d in prior["rows"]}
    originals, _, _ = parent.frozen_source(source)
    result = []
    for original in originals:
        step = original["source"]["step"]
        if step not in ALL_STEPS:
            continue
        fixture = progress_fixture(original)
        q = fixture["questions"]["action"]
        raw = {"t": q["type"], "ins": q["instructions"], "crit": q["criteria"]}
        tok = agent.tok
        encode = lambda text: tok(text.replace(tok.mask_token, " "), add_special_tokens=False)["input_ids"]
        heading = encode(f"{raw['t']} question: {raw['ins']}")
        options = [[tok.mask_token_id] + encode(" " + text) for text in render_options(raw)]
        state = encode(serialize_state(fixture["state"]))
        expected = [tok.cls_token_id] + heading + [tok.sep_token_id] + sum(options, []) + [tok.sep_token_id] + state + [tok.sep_token_id]
        audit = encoding_audit(agent, fixture["state"], fixture["questions"])
        a = audit["questions"]["action"]
        old = by_step[step]
        if (any(fixture[k] != old[k] for k in ("state", "questions", "option_order", "payload_id"))
                or original["fixture_id"] != old["baseline_fixture_id"]
                or expected != old["full_expected_input_ids"] or audit != old["native_audit"]):
            raise ValueError("input differs from the sole frozen design check")
        eligible = step in STEPS
        if (audit["max_len"] != 1024 or audit["head_max_len"] != 256
                or (eligible and (audit["truncated"] or a["effective_input_ids"] != expected))
                or (not eligible and (step != 9 or not a["options_truncated"] or len(expected) <= 1024))):
            raise ValueError("prospective eligibility changed; stop without redesign")
        result.append({"step": step, "fixture": fixture, "native_audit": audit,
                       "full_expected_input_ids": expected, "full_token_count": len(expected),
                       "raw_heading_token_count": len(heading), "raw_option_token_count": sum(map(len, options)),
                       "maximum_single_option_tokens": max(map(len, options)), "included": eligible,
                       "exclusion_reason": None if eligible else "native option clipping; full raw input also exceeds 1024 tokens",
                       "effective_total_length_alone_is_not_sufficient": True, "inference_permitted": eligible})
    return result


def run(args, *, preflight=False):
    fixtures, source_rows, source_manifest = design(args.source)
    code = code_identity()
    if code["dirty_status"]:
        raise ValueError("commit exact code and protocol before preflight/inference")
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "native_option_progress_preflight_complete"}
                or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
            raise ValueError("complete matching CPU preflight required")
        start = one_record(prior, "run_start")
        if (start["manifest"]["code"] != code
                or start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)):
            raise ValueError("code or protocol changed after preflight")
    config = {
        "version": VERSION, "source": str(Path(args.source).resolve()), "source_sha256": parent.SOURCE_SHA256,
        "protocol_sha256": file_hash(PROTOCOL), "fixture_ids": [f["fixture_id"] for f in fixtures],
        "planned_calls": 6, "repeats": 2, "seed": 1, "preflight_only": preflight,
        "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
        "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
        "no_execution": True, "model_facing_privileged": True, "effect_source": "oracle_sim",
        "original_state_unchanged": True, "no_state_prefix": True, "excluded_steps": [9],
        "single_progress_field_duplicated_from_existing_visible_rows": True,
        "design_source": str(DESIGN_PATH), "design_sha256": DESIGN_SHA256,
        "not_an_isolated_binding_mechanism_test": True,
    }
    output = Path(args.preflight if preflight else args.output)
    recorder = RunRecorder(output, config, {"run_id": output.name, "code": code, "versions": versions()})
    try:
        for fixture in fixtures:
            recorder.record("search_fixture", fixture)
        identity = model_identity(MODEL_PATH)
        if identity != source_manifest["models"]["decision"] or identity["content_id"] != MODEL_ID:
            raise ValueError("frozen model bytes changed")
        recorder.manifest_update({"model": identity})
        controls = archive_audit(args.source, code)
        recorder.record("archive_control_audit", controls)
        if controls["identities"][0]["model"] != identity:
            raise ValueError("checkpoint differs from archived controls")
        token_agent = tokenizer_agent()
        budget = budget_audit(token_agent, args.source)
        recorder.record("prospective_budget_audit", budget)
        recorder.record("tokenizer_loaded", {"config": token_agent.cfg, "model_content_id": MODEL_ID})
        prepared = presentations(token_agent, fixtures)
        for fixture, audit in zip(fixtures, prepared):
            recorder.record("provider_presentation", audit)
            recorder.record("token_component_audit", component_audit(token_agent, fixture, audit))
            recorder.record("model_facing_text", {
                "fixture_id": fixture["fixture_id"], "state": fixture["state"], "questions": fixture["questions"],
                "decoded_consumed_input": token_agent.tok.decode(audit["questions"]["action"]["effective_input_ids"]),
            })
        if preflight:
            recorder.record("termination", {"reason": "native_option_progress_preflight_complete"})
            return
        if (prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]
                or [component_audit(token_agent, f, a) for f, a in zip(fixtures, prepared)]
                != [r["data"] for r in prior if r["kind"] == "token_component_audit"]
                or token_agent.cfg != one_record(prior, "tokenizer_loaded")["config"]):
            raise ValueError("input or tokenizer differs from preflight")
        if (controls != one_record(prior, "archive_control_audit")
                or budget != one_record(prior, "prospective_budget_audit")):
            raise ValueError("control identities or budget audit differ from preflight")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        agent = load_laya_provider(MODEL_PATH, subfolder=None, device=args.device).agent
        loaded = jsonable({"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        recorder.record("model_loaded", loaded)
        if (agent.cfg != token_agent.cfg or str(agent.dtype) != "torch.bfloat16"
                or any(loaded[k] != source_manifest["model_execution"][k] for k in ("config", "dtype"))):
            raise ValueError("model configuration/dtype changed")
        environment = {
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "torch_threads": torch.get_num_threads(),
            "device": str(agent.device), "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "gpu_name": torch.cuda.get_device_name(agent.device) if str(agent.device).startswith("cuda") else None,
        }
        recorder.record("inference_environment", environment)
        if (loaded != controls["identities"][0]["loaded"]
                or environment != controls["identities"][0]["environment"]
                or versions() != controls["identities"][0]["versions"]):
            raise ValueError("execution identity differs from exact archived controls")
        archive_environment = {
            "cuda_visible_devices": one_record(source_rows, "reference_invocation")["environment"].get("CUDA_VISIBLE_DEVICES"),
            "device": source_manifest["model_execution"]["device"],
            "deterministic_algorithms": source_manifest["model_execution"]["torch_deterministic"],
        }
        recorder.record("source_environment_difference", environment_difference(archive_environment, environment))
        if presentations(agent, fixtures) != prepared:
            raise ValueError("loaded model tokens differ from CPU preflight")
        for repeat in range(2):
            for ordinal, fixture in enumerate(fixtures if repeat == 0 else reversed(fixtures)):
                parent.checked_call(agent, fixture, recorder, repeat=repeat, ordinal=ordinal)
        recorder.record("termination", {"reason": "native_option_progress_complete", "calls": 6})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    fixtures, _, source_manifest = design(config["source"])
    if ([r["data"] for r in rows if r["kind"] == "search_fixture"] != fixtures
            or config["fixture_ids"] != [f["fixture_id"] for f in fixtures]):
        raise ValueError("recorded design changed")
    prior_path = Path(config["preflight_source"]) / "episodes.jsonl"
    if file_hash(prior_path) != config["preflight_sha256"]:
        raise ValueError("preflight bytes changed")
    prior, diagnostics = load_records(prior_path)
    if (diagnostics or one_record(prior, "termination") != {"reason": "native_option_progress_preflight_complete"}
            or one_record(prior, "run_start")["manifest"]["code"] != one_record(rows, "run_start")["manifest"]["code"]
            or one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]
            or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
        raise ValueError("preflight identity mismatch")
    model = one_record(rows, "manifest_update")["model"]
    if (model != one_record(prior, "manifest_update")["model"] or model != source_manifest["models"]["decision"]
            or model["content_id"] != MODEL_ID):
        raise ValueError("frozen model identity changed")
    for name, sha in model["files_sha256"].items():
        if not name.endswith((".safetensors", ".bin")) and file_hash(Path(model["path"]) / name) != sha:
            raise ValueError("local config/tokenizer changed")
    controls = archive_audit(config["source"], one_record(rows, "run_start")["manifest"]["code"])
    if any(one_record(log, "archive_control_audit") != controls for log in (rows, prior)):
        raise ValueError("archived control audit changed")
    token_agent = tokenizer_agent()
    budget = budget_audit(token_agent, config["source"])
    if any(one_record(log, "prospective_budget_audit") != budget for log in (rows, prior)):
        raise ValueError("prospective budget audit changed")
    prepared = presentations(token_agent, fixtures)
    components = [component_audit(token_agent, f, a) for f, a in zip(fixtures, prepared)]
    if any([r["data"] for r in log if r["kind"] == "token_component_audit"] != components for log in (rows, prior)):
        raise ValueError("raw or consumed component tokens changed")
    if any([r["data"] for r in log if r["kind"] == "provider_presentation"] != prepared for log in (rows, prior)):
        raise ValueError("recorded presentation changed")
    loaded = one_record(rows, "model_loaded")
    if (loaded["config"] != one_record(prior, "tokenizer_loaded")["config"]
            or any(loaded[k] != source_manifest["model_execution"][k] for k in ("config", "dtype"))):
        raise ValueError("model settings changed")
    audits = {p["fixture_id"]: {k: v for k, v in p.items() if k != "fixture_id"} for p in prepared}
    by_id = {f["fixture_id"]: f for f in fixtures}
    for row in rows:
        if row["kind"] == "model_call_intent":
            intent = row["data"]
            expected = active_temperature(SimpleNamespace(cfg=loaded["config"]), len(by_id[intent["fixture_id"]]["option_order"]))
            if intent["temperature"] != expected:
                raise ValueError("cardinality temperature changed")
    calls, invalid, unmatched = recover_calls(rows, fixtures, audits)
    indexed = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(indexed) != len(calls):
        raise ValueError("duplicate fixture/repeat result")
    effects, repeats = [], []
    for fixture in fixtures:
        a, b = [indexed.get((fixture["fixture_id"], repeat)) for repeat in (0, 1)]
        repeats.append({"fixture_id": fixture["fixture_id"], "step": fixture["source"]["step"],
                        "condition": fixture["condition"], **{
                            k + "_equal": a is not None and b is not None and a[k] == b[k]
                            for k in ("choice", "probabilities", "raw_logits")}})
        for repeat, call in enumerate((a, b)):
            if call is None:
                continue
            effects.append({"fixture_id": fixture["fixture_id"], "repeat": repeat, "condition": fixture["condition"],
                            **parent.immediate_comparison(fixture, call["choice"])})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    return {"version": VERSION, "raw_sha256": file_hash(output / "episodes.jsonl"), "source_sha256": parent.SOURCE_SHA256,
            "planned_calls": 6, "valid_calls": len(calls), "missing_or_invalid_calls": 6-len(calls),
            "calls": calls, "invalid_calls": invalid, "unmatched_intents": unmatched, "record_diagnostics": errors,
            "token_component_audits": components,
            "model_facing_texts": [r["data"] for r in rows if r["kind"] == "model_facing_text"],
            "failures": failures, "repeat_comparisons": repeats, "archive_control_audit": controls,
            "prospective_budget_audit": budget,
            "all_repeats_exact": all(all(v for k, v in r.items() if k.endswith("_equal")) for r in repeats),
            "immediate_effect_comparisons": effects, "source_environment_difference": one_record(rows, "source_environment_difference"),
            "complete": len(calls) == 6 and not invalid and not unmatched and not errors and not failures
                        and terminal == [{"reason": "native_option_progress_complete", "calls": 6}],
            "no_execution": True, "model_facing_privileged": True, "original_visible_progress_values_duplicated": True,
            "scope": "one exact native progress-value duplication on three inspected states; one advance state; cannot isolate association, salience, format or position effects"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="/home/junhongli/projects/laya-embodied-runtime/runs/privileged-reference/local-objective-task-adapter-episode-01")
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
        parser.error("--output requires a complete CPU --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
