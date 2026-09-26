"""One frozen supplied-situation intervention on current privileged motor calls."""
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
from .approach_selector_probe import MODEL_ID, MODEL_PATH, presentations, tokenizer_agent
from .predicate_verification import environment_difference, one_record, recover_calls
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import active_temperature, payload_id

VERSION = "worldview-sufficiency-v0.1"
STEPS = (0, 1, 9, 10)
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/worldview_sufficiency_protocol.md"
WORLDVIEWS = {
    "approach_target": (
        "Situation: the target is the top drawer moving structure. Phase: approach. "
        "Intent: bring the gripper near that structure so interaction can become possible. "
        "The drawer is open; gripper-to-drawer surface separation matters now. "
        "Gap reduction measures approach; closure measures drawer motion. "
        "Contact means touching, not secure grasp. Rows predict possible next outcomes, not instructions.\n"
    ),
    "advance_target": (
        "Situation: the target is the top drawer moving structure. Phase: advance. "
        "Intent: reduce drawer opening from the present gripper configuration. "
        "The gripper is very near the drawer surface; drawer motion matters now. "
        "Closure measures drawer motion; gap reduction measures approach. "
        "Contact means touching, not secure grasp. Rows predict possible next outcomes, not instructions.\n"
    ),
}


def worldview_prefix(state):
    """Only existing model-visible text is admissible; no evaluator argument."""
    phase = re.match(r"Current local objective: (\w+)\.\n", state)
    current = re.search(r"Current opening=([\d.]+)mm gap=([\d.]+)mm ", state)
    if (phase is None or phase[1] not in WORLDVIEWS or current is None
            or "Task: close top drawer. effect_source=oracle_sim; privileged=true." not in state):
        raise ValueError("known current privileged top-drawer presentation required")
    opening, gap = map(float, current.groups())
    if opening <= 0 or (phase[1] == "advance_target" and gap > .01):
        raise ValueError("supplied situation premise is unsupported by visible state")
    return WORLDVIEWS[phase[1]]


def worldview_fixture(original):
    if (original["condition"] != "unchanged_current_motor"
            or original["payload_id"] != payload_id(original["state"], original["questions"])
            or original["fixture_id"] != _sha256_json({k: v for k, v in original.items() if k != "fixture_id"})):
        raise ValueError("unmodified current motor fixture required")
    prefix = worldview_prefix(original["state"])
    result = deepcopy(original)
    result.pop("fixture_id")
    result["condition"] = "supplied_coherent_situation"
    result["state"] = prefix + original["state"]
    result["intervention"] = {
        "version": VERSION, "parent_fixture_id": original["fixture_id"], "prefix": prefix,
        "provenance": "researcher-authored interpretation of existing model-visible privileged state and schema",
        "new_physical_observation": False, "no_action_ranking_or_direction": True,
        "target_is_moving_structure_not_designated_handle": True,
        "phase_is_existing_privileged_objective_not_model_inference": True,
    }
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def design(source):
    originals, rows, manifest = parent.frozen_source(source)
    selected = [f for f in originals if f["source"]["step"] in STEPS]
    if tuple(f["source"]["step"] for f in selected) != STEPS:
        raise ValueError("four registered first-horizon source boundaries required")
    return [item for f in selected for item in (f, worldview_fixture(f))], rows, manifest


def run(args, *, preflight=False):
    fixtures, source_rows, source_manifest = design(args.source)
    code = code_identity()
    if code["dirty_status"]:
        raise ValueError("commit exact code and protocol before preflight/inference")
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "worldview_preflight_complete"}
                or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
            raise ValueError("complete matching CPU preflight required")
        start = one_record(prior, "run_start")
        if (start["manifest"]["code"] != code
                or start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)):
            raise ValueError("code or protocol changed after preflight")
    config = {
        "version": VERSION, "source": str(Path(args.source).resolve()), "source_sha256": parent.SOURCE_SHA256,
        "protocol_sha256": file_hash(PROTOCOL), "fixture_ids": [f["fixture_id"] for f in fixtures],
        "planned_calls": 16, "repeats": 2, "seed": 1, "preflight_only": preflight,
        "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
        "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
        "no_execution": True, "model_facing_privileged": True, "effect_source": "oracle_sim",
        "worldview_is_supplied_not_perceived": True, "new_oracle_information": False,
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
        token_agent = tokenizer_agent()
        recorder.record("tokenizer_loaded", {"config": token_agent.cfg, "model_content_id": MODEL_ID})
        prepared = presentations(token_agent, fixtures)
        for fixture, audit in zip(fixtures, prepared):
            if fixture["condition"] == "unchanged_current_motor" and {
                    k: v for k, v in audit.items() if k != "fixture_id"} != fixture["source"]["archived_audit"]:
                raise ValueError("baseline tokens differ from source")
            recorder.record("provider_presentation", audit)
            recorder.record("model_facing_text", {
                "fixture_id": fixture["fixture_id"], "state": fixture["state"], "questions": fixture["questions"],
                "decoded_consumed_input": token_agent.tok.decode(audit["questions"]["action"]["effective_input_ids"]),
            })
        if preflight:
            recorder.record("termination", {"reason": "worldview_preflight_complete"})
            return
        if (prepared != [r["data"] for r in prior if r["kind"] == "provider_presentation"]
                or token_agent.cfg != one_record(prior, "tokenizer_loaded")["config"]):
            raise ValueError("input or tokenizer differs from preflight")
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
        recorder.record("termination", {"reason": "worldview_complete", "calls": 16})
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
    if (diagnostics or one_record(prior, "termination") != {"reason": "worldview_preflight_complete"}
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
    prepared = presentations(tokenizer_agent(), fixtures)
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
    effects, repeats, archive = [], [], []
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
            if fixture["condition"] == "unchanged_current_motor":
                old = fixture["source"]["archived_response"]
                answer = old["raw_response"]["answers"]["action"]
                archive.append({"step": fixture["source"]["step"], "repeat": repeat,
                                "choice_equal": call["choice"] == answer["choice"],
                                "probabilities_equal": call["probabilities"] == answer["probabilities"],
                                "raw_logits_equal": call["raw_logits"] == old["forward_traces"][0]["raw_option_logits"]})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    return {"version": VERSION, "raw_sha256": file_hash(output / "episodes.jsonl"), "source_sha256": parent.SOURCE_SHA256,
            "planned_calls": 16, "valid_calls": len(calls), "missing_or_invalid_calls": 16-len(calls),
            "calls": calls, "invalid_calls": invalid, "unmatched_intents": unmatched, "record_diagnostics": errors,
            "failures": failures, "repeat_comparisons": repeats, "archive_comparisons": archive,
            "all_repeats_exact": all(all(v for k, v in r.items() if k.endswith("_equal")) for r in repeats),
            "all_baselines_exact": len(archive) == 8 and all(all(v for k, v in r.items() if k.endswith("_equal")) for r in archive),
            "immediate_effect_comparisons": effects, "source_environment_difference": one_record(rows, "source_environment_difference"),
            "complete": len(calls) == 16 and not invalid and not unmatched and not errors and not failures
                        and terminal == [{"reason": "worldview_complete", "calls": 16}],
            "no_execution": True, "model_facing_privileged": True, "worldview_is_supplied_not_perceived": True,
            "scope": "one coherent situation prefix; no physical success, acquisition, or full-world-model inference"}


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
