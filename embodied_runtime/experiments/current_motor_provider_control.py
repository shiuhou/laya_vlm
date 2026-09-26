"""One frozen Qwen provider on the five unchanged current motor fixtures."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random

import numpy as np

from ..runtime_core import _sha256_json
from . import current_motor_replication as motor
from . import provider_comparison as pc
from .predicate_verification import environment_difference, one_record
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions

VERSION = "current-motor-provider-control-v0.1"
MODEL_PATH = "/home/junhongli/models/huggingface/Qwen2.5-7B-Instruct"
MODEL_ID = "e2b474b2efa21f2dbfc6e6c31de53a54f20eea68942e02d34164526078dc4cf5"
QWEN_SOURCE_SHA256 = "baf1512634f6a60f74f852ebc3988690555f4af897845dbc930cb81091796dff"
LAYA_SOURCE_SHA256 = "afe0c64acf7b82d7a0a3c99ed50bd09b02db67cbccbd6fa3466ae71e53fb0804"
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/research/current_motor_provider_control_protocol.md"


def sources(args):
    fixtures, _, _ = motor.frozen_source(args.source)
    if file_hash(Path(args.laya_source) / "episodes.jsonl") != LAYA_SOURCE_SHA256:
        raise ValueError("frozen fresh Laya source identity mismatch")
    laya = motor.report(args.laya_source)
    if not all(laya[key] for key in ("complete", "all_repeats_exact", "archive_choices_and_probabilities_reproduced")):
        raise ValueError("complete exact Laya replication required")
    path = Path(args.qwen_source) / "episodes.jsonl"
    if file_hash(path) != QWEN_SOURCE_SHA256:
        raise ValueError("frozen Qwen configuration source identity mismatch")
    rows, errors = load_records(path)
    if errors or one_record(rows, "termination") != {"reason": "provider_comparison_complete", "calls": 128}:
        raise ValueError("complete original Qwen provider source required")
    if one_record(rows, "manifest_update")["model"]["content_id"] != MODEL_ID:
        raise ValueError("Qwen source checkpoint identity mismatch")
    return fixtures, laya, one_record(rows, "model_loaded")


def option_audit(tokenizer, fixtures):
    names = dict.fromkeys(name for f in fixtures for name in f["option_order"])
    for name in names:
        ids = tokenizer(name, add_special_tokens=False, truncation=False)["input_ids"]
        if not ids or len(ids) + 1 > 16 or tokenizer.decode(ids, skip_special_tokens=True) != name:
            raise ValueError(f"native option cannot be losslessly returned within budget: {name}")
        names[name] = {"input_ids": ids, "tokens_including_eos": len(ids) + 1}
    return names


def validate_answer(prepared, raw, logits, tokenizer, loaded, allowed):
    pc.validate_raw(prepared, raw, logits, tokenizer, loaded["config"]["vocab_size"])
    if raw["device"] != loaded["device"] or raw["dtype"] != loaded["dtype"]:
        raise ValueError("provider device/dtype changed during generation")
    eos = loaded["generation_config"]["eos_token_id"]
    eos = {eos} if isinstance(eos, int) else set(eos)
    generated = raw["generated_ids"]
    if generated[-1] not in eos or any(token in eos for token in generated[:-1]):
        raise ValueError("answer lacks one terminal EOS")
    if any(token in tokenizer.all_special_ids for token in generated[:-1]):
        raise ValueError("answer contains unexpected special tokens")
    choice = pc.parse_choice(raw["decoded_text"], allowed)
    if choice is None:
        raise ValueError("malformed native option answer; no retry or extraction")
    return choice


def run(args, *, preflight=False):
    fixtures, _, archived_model = sources(args)
    code = code_identity()
    prior = None
    if not preflight:
        prior, errors = load_records(Path(args.preflight_source) / "episodes.jsonl")
        if (errors or one_record(prior, "termination") != {"reason": "current_motor_provider_preflight_complete"}
                or [r["data"] for r in prior if r["kind"] == "search_fixture"] != fixtures):
            raise ValueError("completed matching preflight required")
        start = one_record(prior, "run_start")
        if (start["resolved_config"]["protocol_sha256"] != file_hash(PROTOCOL)
                or start["manifest"]["code"]["source_sha256"] != code["source_sha256"]):
            raise ValueError("code or protocol changed after preflight")
    config = {"version": VERSION, "source": str(Path(args.source).resolve()),
              "laya_source": str(Path(args.laya_source).resolve()), "qwen_source": str(Path(args.qwen_source).resolve()),
              "source_sha256": motor.SOURCE_SHA256, "laya_source_sha256": LAYA_SOURCE_SHA256,
              "qwen_source_sha256": QWEN_SOURCE_SHA256, "protocol_sha256": file_hash(PROTOCOL),
              "fixture_ids": [f["fixture_id"] for f in fixtures], "preflight_only": preflight,
              "preflight_source": str(Path(args.preflight_source).resolve()) if prior else None,
              "preflight_sha256": file_hash(Path(args.preflight_source) / "episodes.jsonl") if prior else None,
              "provider": pc.MODEL_REPO, "provider_revision": pc.MODEL_REVISION,
              "planned_calls": 10, "repeats": 2, "seed": 1, "batch_size": 1, "torch_threads": 4,
              "no_execution": True, "effect_source": "oracle_sim", "privileged": True}
    output = Path(args.preflight if preflight else args.output)
    recorder = RunRecorder(output, config, {"run_id": output.name, "code": code, "versions": versions()})
    try:
        for fixture in fixtures:
            recorder.record("search_fixture", fixture)
        identity = model_identity(MODEL_PATH)
        if identity["content_id"] != MODEL_ID:
            raise ValueError("local Qwen checkpoint differs from frozen bytes")
        recorder.manifest_update({"model": identity})
        import torch
        torch.set_num_threads(4)
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        provider = pc.FrozenTransformersProvider(MODEL_PATH, args.device)
        loaded = jsonable({"config": provider.model.config.to_dict(),
                          "generation_config": provider.generation.to_dict(), "device": str(provider.model.device),
                          "dtype": str(provider.model.dtype), "system_instruction": pc.SYSTEM})
        recorder.record("model_loaded", loaded)
        if any(loaded[k] != archived_model[k] for k in ("config", "generation_config", "dtype", "system_instruction")):
            raise ValueError("Qwen settings differ from existing archived provider")
        environment = {"cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                       "torch_threads": torch.get_num_threads(), "device": str(provider.model.device),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                       "gpu_name": torch.cuda.get_device_name(provider.model.device) if str(provider.model.device).startswith("cuda") else None}
        recorder.record("inference_environment", environment)
        recorder.record("source_environment_difference", environment_difference(
            {k: archived_model[k] for k in ("device", "cuda_visible_devices")}, environment))
        native_options = option_audit(provider.tokenizer, fixtures)
        recorder.record("native_option_audit", native_options)
        prepared = {}
        for fixture in fixtures:
            item = provider.prepare(fixture["state"], fixture["questions"])
            if item["payload_id"] != fixture["payload_id"] or item["truncated"]:
                raise ValueError("logical payload changed or presentation truncated")
            prepared[fixture["fixture_id"]] = item
            recorder.record("provider_presentation", {"fixture_id": fixture["fixture_id"], **item})
        if prior:
            for kind, actual in (("model_loaded", loaded), ("inference_environment", environment),
                                 ("native_option_audit", native_options)):
                if one_record(prior, kind) != actual:
                    raise ValueError("provider/environment differs from preflight")
            if [r["data"] for r in prior if r["kind"] == "provider_presentation"] != [
                    {"fixture_id": fid, **item} for fid, item in prepared.items()]:
                raise ValueError("presentations differ from preflight")
        if preflight:
            recorder.record("termination", {"reason": "current_motor_provider_preflight_complete"})
        else:
            for repeat in range(2):
                for ordinal, fixture in enumerate(fixtures if repeat == 0 else reversed(fixtures)):
                    fid = fixture["fixture_id"]
                    ident = {"fixture_id": fid, "repeat": repeat, "ordinal": ordinal}
                    cid = _sha256_json(ident)
                    recorder.record("provider_call_intent", {**ident, "call_id": cid, "input_id": prepared[fid]["input_id"]})
                    raw, logits = provider.infer(prepared[fid])
                    artifact = Path("logits") / f"{cid}.npz"
                    path = output / artifact
                    path.parent.mkdir(exist_ok=True)
                    with path.open("xb") as stream:
                        np.savez_compressed(stream, logits=logits)
                        stream.flush()
                        os.fsync(stream.fileno())
                    recorder.record("provider_raw_response", {"call_id": cid, **raw, "logits_artifact": str(artifact),
                                    "logits_sha256": file_hash(path), "logits_values_sha256": pc.values_hash(logits)})
                    validate_answer(prepared[fid], raw, logits, provider.tokenizer, loaded, fixture["option_order"])
            recorder.record("termination", {"reason": "current_motor_provider_complete", "calls": 10})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def recover_calls(output, rows, fixtures, prepared, tokenizer, loaded):
    indexed = {f["fixture_id"]: f for f in fixtures}
    intents, responses, calls, invalid = {}, set(), [], []
    for row in rows:
        data, kind = row["data"], row["kind"]
        if kind == "provider_call_intent":
            cid = data["call_id"]
            ident = {k: data[k] for k in ("fixture_id", "repeat", "ordinal")}
            traversal = fixtures if data["repeat"] == 0 else list(reversed(fixtures))
            if (cid in intents or cid != _sha256_json(ident) or data["repeat"] not in (0, 1)
                    or not 0 <= data["ordinal"] < len(fixtures)
                    or traversal[data["ordinal"]]["fixture_id"] != data["fixture_id"]
                    or data["input_id"] != prepared[data["fixture_id"]]["input_id"]):
                raise ValueError("call identity, traversal or input changed")
            intents[cid] = data
        elif kind == "provider_raw_response":
            cid = data["call_id"]
            if cid not in intents or cid in responses:
                raise ValueError("orphan or duplicate provider response")
            responses.add(cid)
            intent = intents[cid]
            try:
                path = Path(output) / data["logits_artifact"]
                if file_hash(path) != data["logits_sha256"]:
                    raise ValueError("logit artifact changed")
                with np.load(path, allow_pickle=False) as saved:
                    logits = saved["logits"]
                if pc.values_hash(logits) != data["logits_values_sha256"]:
                    raise ValueError("logit values changed")
                f = indexed[intent["fixture_id"]]
                choice = validate_answer(prepared[f["fixture_id"]], data, logits, tokenizer, loaded, f["option_order"])
                calls.append({"fixture_id": f["fixture_id"], "repeat": intent["repeat"], "call_id": cid,
                              "choice": choice, "generated_ids": data["generated_ids"],
                              "decoded_text": data["decoded_text"], "logits_values_sha256": data["logits_values_sha256"],
                              "input_tokens": len(prepared[f["fixture_id"]]["input_ids"])})
            except (ValueError, KeyError, TypeError, IndexError, OSError) as exc:
                invalid.append({"call_id": cid, "fixture_id": intent["fixture_id"], "repeat": intent["repeat"], "reason": str(exc)})
    return calls, invalid, sorted(set(intents)-responses)


def report(output):
    from transformers import AutoTokenizer
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = one_record(rows, "run_start")["resolved_config"]
    fixtures, laya, archived_model = sources(argparse.Namespace(**config))
    if ([r["data"] for r in rows if r["kind"] == "search_fixture"] != fixtures
            or config["fixture_ids"] != [f["fixture_id"] for f in fixtures]):
        raise ValueError("recorded fixture design changed")
    prior_path = Path(config["preflight_source"])
    if file_hash(prior_path / "episodes.jsonl") != config["preflight_sha256"]:
        raise ValueError("preflight source changed")
    prior, prior_errors = load_records(prior_path / "episodes.jsonl")
    if prior_errors or one_record(prior, "termination") != {"reason": "current_motor_provider_preflight_complete"}:
        raise ValueError("invalid preflight")
    if one_record(prior, "run_start")["resolved_config"]["protocol_sha256"] != config["protocol_sha256"]:
        raise ValueError("protocol lineage changed")
    for kind in ("manifest_update", "model_loaded", "inference_environment", "native_option_audit"):
        if one_record(rows, kind) != one_record(prior, kind):
            raise ValueError("provider identity/settings differ from preflight")
    model = one_record(rows, "manifest_update")["model"]
    if model["content_id"] != MODEL_ID or _sha256_json(model["files_sha256"]) != MODEL_ID:
        raise ValueError("wrong checkpoint identity")
    for name, sha in model["files_sha256"].items():
        if not name.endswith((".safetensors", ".bin")) and file_hash(Path(model["path"]) / name) != sha:
            raise ValueError("tokenizer/config bytes changed")
    loaded = one_record(rows, "model_loaded")
    if any(loaded[k] != archived_model[k] for k in ("config", "generation_config", "dtype", "system_instruction")):
        raise ValueError("archived provider settings changed")
    tokenizer = AutoTokenizer.from_pretrained(model["path"], local_files_only=True, trust_remote_code=False)
    if option_audit(tokenizer, fixtures) != one_record(rows, "native_option_audit"):
        raise ValueError("native option encoding changed")
    presentations = [r["data"] for r in rows if r["kind"] == "provider_presentation"]
    if len(presentations) != 5 or presentations != [r["data"] for r in prior if r["kind"] == "provider_presentation"]:
        raise ValueError("presentation coverage/preflight mismatch")
    prepared = {}
    for fixture, data in zip(fixtures, presentations):
        msgs = pc.messages(fixture["state"], fixture["questions"])
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
        expected = {"fixture_id": fixture["fixture_id"], "messages": msgs, "rendered_prompt": prompt,
                    "input_ids": ids, "input_id": _sha256_json(ids), "prompt_sha256": _sha256_json(prompt),
                    "truncated": False, "payload_id": fixture["payload_id"]}
        if data != expected or len(ids)+16 > loaded["config"]["max_position_embeddings"]:
            raise ValueError("consumed presentation differs from common logical payload")
        prepared[fixture["fixture_id"]] = data
    calls, invalid, unmatched = recover_calls(output, rows, fixtures, prepared, tokenizer, loaded)
    indexed = {(c["fixture_id"], c["repeat"]): c for c in calls}
    if len(indexed) != len(calls):
        raise ValueError("duplicate fixture/repeat response")
    laya_calls = {(c["fixture_id"], c["repeat"]): c for c in laya["calls"]}
    comparisons, repeats = [], []
    for f in fixtures:
        a, b = [indexed.get((f["fixture_id"], repeat)) for repeat in (0, 1)]
        repeats.append({"step": f["source"]["step"], **{key+"_equal": a is not None and b is not None and a[key] == b[key]
                                                        for key in ("choice", "generated_ids", "logits_values_sha256")}})
        for repeat, current in enumerate((a, b)):
            old_choice = f["source"]["archived_response"]["raw_response"]["answers"]["action"]["choice"]
            laya_choice = laya_calls[(f["fixture_id"], repeat)]["choice"]
            comparisons.append({"step": f["source"]["step"], "repeat": repeat,
                                "laya_archived_choice": old_choice, "laya_reproduced_choice": laya_choice,
                                "qwen_choice": current["choice"] if current else None,
                                "laya": motor.immediate_comparison(f, laya_choice),
                                "qwen": motor.immediate_comparison(f, current["choice"]) if current else None})
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    return {"version": VERSION, "raw_sha256": file_hash(output / "episodes.jsonl"), "planned_calls": 10,
            "valid_calls": len(calls), "missing_or_invalid_calls": 10-len(calls), "calls": calls,
            "invalid_calls": invalid, "unmatched_intents": unmatched, "failures": failures, "record_diagnostics": errors,
            "repeat_comparisons": repeats, "all_repeats_exact": all(all(value for key, value in r.items() if key.endswith("_equal")) for r in repeats),
            "comparisons": comparisons, "no_execution": True, "cross_provider_probability_comparison": False,
            "complete": len(calls) == 10 and not invalid and not unmatched and not failures and not errors
                        and terminal == [{"reason": "current_motor_provider_complete", "calls": 10}],
            "scope": "provider-plus-adapter immediate-effect control; not trajectory or interaction-valid competence"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="runs/privileged-reference/local-objective-task-adapter-episode-01")
    parser.add_argument("--laya-source", default="runs/autonomous-research/current-motor-replication-01")
    parser.add_argument("--qwen-source", default="runs/provider-comparison/qwen-v01")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight")
    group.add_argument("--output")
    group.add_argument("--summarize")
    parser.add_argument("--preflight-source")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output and not args.preflight_source:
        parser.error("--output requires completed --preflight-source")
    else:
        run(args, preflight=bool(args.preflight))


if __name__ == "__main__":
    main()
