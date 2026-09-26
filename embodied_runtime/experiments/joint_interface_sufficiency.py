"""One frozen interaction of existing situation and action-definition prefixes."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np

from ..runtime_core import _sha256_json, load_laya_provider
from . import current_motor_replication as parent
from . import action_semantics_binding as binding
from . import worldview_sufficiency as worldview
from ..adapters.laya_input import encoding_audit
from .approach_selector_probe import MODEL_ID, MODEL_PATH, presentations, tokenizer_agent
from .predicate_verification import environment_difference, one_record, recover_calls
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import active_temperature, payload_id

VERSION = "joint-interface-sufficiency-v0.1"
STEPS = (0, 1, 10)
ALL_STEPS = (0, 1, 9, 10)
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/joint_interface_sufficiency_protocol.md"
RAW_ROOT = Path("/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research")
ARCHIVES = {
    "worldview-sufficiency-preflight-01": "ca473d33818a5ad21bbd4dfda4c375a564de5b4b691bce9c9e0aafc7749818f5",
    "worldview-sufficiency-run-01": "d1e2950d4e6bcb933d6a97228cc93f88eb15409d370eceedee0ed0767fac969b",
    "action-binding-preflight-01": "bf335e439dbb56786e22a2fc802c3cca8a9ba406055a60e253a182ecaf49f449",
    "action-binding-run-01": "a6c42bf8ef985b4b9185b5a4fcc258b624b31d0d0a68f957d5638042e4449d2b",
}
SEMANTICS_SOURCES = binding.SEMANTICS_SOURCES
component_audit = binding.component_audit


def joint_fixture(original):
    if original["fixture_id"] != _sha256_json({k: v for k, v in original.items() if k != "fixture_id"}):
        raise ValueError("unmodified baseline identity required")
    # Both existing constructors independently check the exact baseline identity.
    w = worldview.worldview_fixture(original)
    a = binding.binding_fixture(original)
    prefix_w, prefix_a = w["intervention"]["prefix"], a["intervention"]["prefix"]
    result = deepcopy(original)
    result.pop("fixture_id")
    result["condition"] = "supplied_situation_then_action_definitions"
    result["state"] = prefix_w + prefix_a + original["state"]
    result["intervention"] = {
        "version": VERSION, "parent_fixture_id": original["fixture_id"],
        "worldview_fixture_id": w["fixture_id"], "action_fixture_id": a["fixture_id"],
        "prefix": prefix_w + prefix_a, "prefix_order": ["W", "A"],
        "worldview_prefix": prefix_w, "action_prefix": prefix_a,
        "provenance": "exact previously registered supplied W then A; unchanged baseline suffix",
        "new_physical_observation": False, "new_wording": False,
        "no_action_ranking_or_direction_recommendation": True,
    }
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def design(source):
    originals, rows, manifest = parent.frozen_source(source)
    selected = [f for f in originals if f["source"]["step"] in STEPS]
    if tuple(f["source"]["step"] for f in selected) != STEPS:
        raise ValueError("three registered budget-eligible boundaries required")
    return [joint_fixture(f) for f in selected], rows, manifest


def archive_audit(source, code):
    """Establish exact archived B/W/A controls before admitting six new calls."""
    for name, digest in ARCHIVES.items():
        if file_hash(RAW_ROOT / name / "episodes.jsonl") != digest:
            raise ValueError("frozen control archive bytes changed")
    controls, identities = [], []
    for module, name in ((worldview, "worldview-sufficiency"), (binding, "action-binding")):
        old, diagnostics = load_records(RAW_ROOT / (name + "-run-01") / "episodes.jsonl")
        start = one_record(old, "run_start")
        rel = str(Path(module.__file__).relative_to(Path(__file__).resolve().parents[2]))
        if (diagnostics or start["resolved_config"]["source_sha256"] != parent.SOURCE_SHA256
                or start["resolved_config"]["seed"] != 1
                or start["manifest"]["code"]["source_sha256"][rel] != code["source_sha256"][rel]
                or start["resolved_config"]["protocol_sha256"] != file_hash(module.PROTOCOL)):
            raise ValueError("control source, prefix code, protocol or seed changed")
        fixtures, _, _ = module.design(source)
        if fixtures != [r["data"] for r in old if r["kind"] == "search_fixture"]:
            raise ValueError("exact control fixture identities changed")
        checked = module.report(RAW_ROOT / (name + "-run-01"))
        if not all(checked[k] for k in ("complete", "all_repeats_exact", "all_baselines_exact")):
            raise ValueError("complete exactly repeated and source-matched controls required")
        identities.append({"archive": name, "model": one_record(old, "manifest_update")["model"],
                           "loaded": one_record(old, "model_loaded"),
                           "environment": one_record(old, "inference_environment"),
                           "versions": start["manifest"]["versions"]})
        by_id = {f["fixture_id"]: f for f in fixtures}
        effects = {r["fixture_id"]: r for r in checked["immediate_effect_comparisons"] if r["repeat"] == 0}
        for call in checked["calls"]:
            f = by_id[call["fixture_id"]]
            if call["repeat"] == 0 and f["source"]["step"] in STEPS:
                controls.append({"archive": name, "step": f["source"]["step"],
                                 "condition": f["condition"], "payload_id": f["payload_id"],
                                 "call": call, "effect": effects[f["fixture_id"]]})
    if any(identities[0][k] != identities[1][k] for k in ("model", "loaded", "environment", "versions")):
        raise ValueError("archived control execution identities differ")
    return {"archive_sha256": ARCHIVES, "all_controls_exact": True,
            "identities": identities, "controls": controls, "no_new_control_calls": True}


def budget_audit(agent, source):
    """Tokenize all four fixed compositions; never submit the excluded state."""
    originals, _, _ = parent.frozen_source(source)
    result = []
    for original in originals:
        step = original["source"]["step"]
        if step not in ALL_STEPS:
            continue
        fixture = joint_fixture(original)
        audit = encoding_audit(agent, fixture["state"], fixture["questions"])
        q = audit["questions"]["action"]
        full_count = q["state_tokens"] + audit["max_len"] - q["state_budget"]
        eligible = step in STEPS
        if (audit["max_len"] != 1024 or audit["head_max_len"] != 256
                or q["heading_truncated"] or q["options_truncated"]
                or (eligible and (audit["truncated"] or full_count > 1024))
                or (not eligible and (step != 9 or full_count <= 1024 or not q["state_truncated"]))):
            raise ValueError("prospective input budget eligibility differs; stop without redesign")
        result.append({"step": step, "fixture": fixture, "native_audit": audit,
                       "full_token_count": full_count, "included": eligible,
                       "exclusion_reason": None if eligible else "complete W+A input exceeds unchanged 1024-token budget",
                       "inference_permitted": eligible})
    return result


def run(args, *, preflight=False):
    fixtures, source_rows, source_manifest = design(args.source)
    code = code_identity()
    if code["dirty_status"]:
        raise ValueError("commit exact code and protocol before preflight/inference")
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "joint_interface_preflight_complete"}
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
        "existing_worldview_and_action_prefixes_supplied": True, "new_physical_observation": False,
        "prefix_order": ["W", "A"], "excluded_steps": [9],
        "semantics_source_sha256": SEMANTICS_SOURCES,
    }
    output = Path(args.preflight if preflight else args.output)
    recorder = RunRecorder(output, config, {"run_id": output.name, "code": code, "versions": versions()})
    try:
        for path, digest in SEMANTICS_SOURCES.items():
            if file_hash(path) != digest:
                raise ValueError("executor semantics source bytes changed")
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
            recorder.record("termination", {"reason": "joint_interface_preflight_complete"})
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
        recorder.record("termination", {"reason": "joint_interface_complete", "calls": 6})
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
    if (diagnostics or one_record(prior, "termination") != {"reason": "joint_interface_preflight_complete"}
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
                        and terminal == [{"reason": "joint_interface_complete", "calls": 6}],
            "no_execution": True, "model_facing_privileged": True, "action_definitions_supplied_not_inferred": True,
            "scope": "one exact W+A interaction on three inspected states; one advance state; no recognition, acquisition, execution, or full-world-model inference"}


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
