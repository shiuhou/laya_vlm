"""Suffix-only STOP-rule order diagnostic on frozen fixtures. No execution."""
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
from . import provider_comparison as pc
from .effect_binding import effect_facts
from .interface_search import summarize as laya_report
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions
from .reference_model_diagnostic import payload_id, run_call

VERSION = "clause-order-v0.1"
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/clause_order_protocol.md"
ORIGINAL = ("When a STOP comparison is supplied, also require lower opening than STOP for closed, "
            "or higher opening than STOP for open.")
SWAPPED = ("When a STOP comparison is supplied, also require higher opening than STOP for open, "
           "or lower opening than STOP for closed.")
QWEN_SHA256 = "baf1512634f6a60f74f852ebc3988690555f4af897845dbc930cb81091796dff"
MODEL_IDS = {"laya": "9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704",
             "qwen": "e2b474b2efa21f2dbfc6e6c31de53a54f20eea68942e02d34164526078dc4cf5"}
MODEL_PATHS = {"laya": "/home/junhongli/models/huggingface/laya/typed-decisions",
               "qwen": "/home/junhongli/models/huggingface/Qwen2.5-7B-Instruct"}


def swap_fixture(parent):
    if (not isinstance(parent["state"], str) or not parent["state"].endswith(ORIGINAL)
            or parent["state"].count(ORIGINAL) != 1 or parent["source"]["effect_detail"] != "relative"):
        raise ValueError("exact frozen full-effect suffix required")
    result = deepcopy(parent)
    del result["fixture_id"]
    result["state"] = parent["state"][:-len(ORIGINAL)] + SWAPPED
    result["intervention"] = {"version": VERSION, "final_clause": "closed",
                              "parent_fixture_id": parent["fixture_id"],
                              "parent_payload_id": parent["payload_id"]}
    result["payload_id"] = payload_id(result["state"], result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def design(original):
    controls = [f for f in original if f["source"]["physical"]["init_state_id"] == 0
                and f["source"]["physical"]["environment_step"] == 48
                and f["source"]["assignment"] == "true" and f["source"]["goal"] == "closed"
                and not f["source"]["reverse"]]
    if len(controls) != 2 or {f["source"]["descriptions"] for f in controls} != {"native", "anonymous"}:
        raise ValueError("two predeclared controls required")
    return controls + [swap_fixture(f) for f in original]


def baselines(source, qwen_source):
    original, laya = pc.frozen_source(source)
    if file_hash(Path(qwen_source) / "episodes.jsonl") != QWEN_SHA256:
        raise ValueError("not the frozen Qwen source")
    qwen = pc.report(qwen_source)
    if not qwen["complete"] or not qwen["all_repeats_stable"]:
        raise ValueError("complete stable Qwen baseline required")
    # Retain raw scorer fields for cross-session control comparisons.
    ids = {f["fixture_id"] for f in original}
    laya = [c for c in laya if c["fixture_id"] in ids]
    return original, {"laya": laya, "qwen": qwen["calls"]}


def run(args):
    original, _ = baselines(args.source, args.qwen_source)
    fs = design(original)
    config = {"version": VERSION, "provider": args.provider, "source": str(Path(args.source).resolve()),
              "qwen_source": str(Path(args.qwen_source).resolve()), "source_sha256": pc.SOURCE_SHA256,
              "qwen_source_sha256": QWEN_SHA256, "protocol_sha256": file_hash(PROTOCOL),
              "fixture_ids": [f["fixture_id"] for f in fs], "repeats": 2, "seed": 1,
              "no_execution": True, "not_formal_e0": True, "privileged_effects": True}
    recorder = RunRecorder(args.output, config, {"run_id": Path(args.output).name,
                           "code": code_identity(), "versions": versions()})
    try:
        for f in fs:
            recorder.record("search_fixture", f)
        identity = model_identity(MODEL_PATHS[args.provider])
        recorder.manifest_update({"model": identity})
        if identity["content_id"] != MODEL_IDS[args.provider]:
            raise ValueError("checkpoint changed from frozen baseline")
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        if args.provider == "laya":
            provider = load_laya_provider(identity["path"], subfolder=None, device=args.device).agent
            loaded = {"config": provider.cfg, "device": str(provider.device), "dtype": str(provider.dtype)}
        else:
            torch.set_num_threads(4)
            provider = pc.FrozenTransformersProvider(identity["path"], args.device)
            loaded = {"config": provider.model.config.to_dict(), "generation_config": provider.generation.to_dict(),
                      "device": str(provider.model.device), "dtype": str(provider.model.dtype),
                      "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                      "system_instruction": pc.SYSTEM}
        # The exact model configs must match the corresponding recorded session.
        baseline_path = args.source if args.provider == "laya" else args.qwen_source
        rows, _ = load_records(Path(baseline_path) / "episodes.jsonl")
        baseline_loaded = next(r["data"] for r in rows if r["kind"] == "model_loaded")
        recorder.record("model_loaded", loaded)
        # The recorder converts integer mapping keys (e.g. id2label) to JSON strings.
        if jsonable(loaded) != baseline_loaded:
            raise ValueError("model/decoding configuration differs from baseline")
        prepared = {}
        for f in fs:
            p = (encoding_audit(provider, f["state"], f["questions"]) if args.provider == "laya"
                 else provider.prepare(f["state"], f["questions"]))
            if p.get("truncated") or (args.provider == "laya" and not p.get("available")):
                raise ValueError("complete presentation required")
            prepared[f["fixture_id"]] = p
            recorder.record("provider_presentation", {"fixture_id": f["fixture_id"], **p})
        for repeat in range(2):
            for ordinal, f in enumerate(fs if repeat == 0 else list(reversed(fs))):
                if args.provider == "laya":
                    run_call(provider, f, recorder, repeat=repeat, ordinal=ordinal)
                    continue
                p = prepared[f["fixture_id"]]
                ident = {"fixture_id": f["fixture_id"], "repeat": repeat, "ordinal": ordinal}
                cid = _sha256_json(ident)
                recorder.record("provider_call_intent", {**ident, "call_id": cid, "input_id": p["input_id"]})
                raw, logits = provider.infer(p)
                artifact = Path("logits") / f"{cid}.npz"
                path = Path(args.output) / artifact
                path.parent.mkdir(exist_ok=True)
                with path.open("xb") as stream:
                    np.savez_compressed(stream, logits=logits)
                    stream.flush()
                    os.fsync(stream.fileno())
                recorder.record("provider_raw_response", {"call_id": cid, **raw,
                                "logits_artifact": str(artifact), "logits_sha256": file_hash(path),
                                "logits_values_sha256": pc.values_hash(logits)})
                pc.validate_raw(p, raw, logits, provider.tokenizer, provider.model.config.vocab_size)
        recorder.record("termination", {"reason": "interface_search_complete" if args.provider == "laya"
                                         else "clause_order_complete", "calls": len(fs)*2})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def qwen_calls(output, rows, fs, loaded, model):
    """Reconstruct choices from unmodified generation, with the existing raw audit."""
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model["path"], local_files_only=True, trust_remote_code=False)
    fixtures = {f["fixture_id"]: f for f in fs}
    prepared, intents, completed, calls = {}, {}, set(), []
    for row in rows:
        d, kind = row["data"], row["kind"]
        if kind == "provider_presentation":
            fid = d["fixture_id"]
            f = fixtures[fid]
            msgs = pc.messages(f["state"], f["questions"])
            prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ids = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
            if (fid in prepared or d["messages"] != msgs or d["rendered_prompt"] != prompt
                    or d["input_ids"] != ids or d["input_id"] != _sha256_json(ids)
                    or d["prompt_sha256"] != _sha256_json(prompt) or d["truncated"]
                    or d["payload_id"] != f["payload_id"]):
                raise ValueError("presentation differs from suffix-only intervention")
            prepared[fid] = d
        elif kind == "provider_call_intent":
            cid = d["call_id"]
            ident = {k: d[k] for k in ("fixture_id", "repeat", "ordinal")}
            if cid in intents or cid != _sha256_json(ident) or d["input_id"] != prepared[d["fixture_id"]]["input_id"]:
                raise ValueError("invalid or duplicate provider intent")
            intents[cid] = d
        elif kind == "provider_raw_response":
            cid = d["call_id"]
            if cid not in intents or cid in completed:
                raise ValueError("orphan or duplicate response")
            intent = intents[cid]
            path = output / d["logits_artifact"]
            if file_hash(path) != d["logits_sha256"]:
                raise ValueError("logits artifact integrity failure")
            with np.load(path, allow_pickle=False) as saved:
                logits = saved["logits"]
            if pc.values_hash(logits) != d["logits_values_sha256"]:
                raise ValueError("raw logits value hash mismatch")
            pc.validate_raw(prepared[intent["fixture_id"]], d, logits, tokenizer, loaded["config"]["vocab_size"])
            if d["device"] != loaded["device"] or d["dtype"] != loaded["dtype"]:
                raise ValueError("inference device or dtype changed")
            f = fixtures[intent["fixture_id"]]
            choice = pc.parse_choice(d["decoded_text"], f["option_order"])
            calls.append({"fixture_id": f["fixture_id"], "repeat": intent["repeat"],
                          "choice": f["option_to_canonical"].get(choice), "option_id": choice,
                          "decoded_text": d["decoded_text"], "generated_ids": d["generated_ids"],
                          "logits_values_sha256": d["logits_values_sha256"],
                          "input_tokens": len(prepared[f["fixture_id"]]["input_ids"])})
            completed.add(cid)
    return calls, set(prepared) == set(fixtures) and set(intents) == completed


def direction(f, choice):
    if choice not in f["source"]["effect_assignment"]:
        return {"facts": None, "direction": "unknown"}
    facts = effect_facts(f["source"])[f["source"]["effect_assignment"][choice]]
    pair = facts["opening"], facts["vs_stop"]
    return {"facts": facts, "direction": {("decreases", "lower"): "closed",
            ("increases", "higher"): "open"}.get(pair, "other")}


def compare_calls(original, fs, baseline, calls):
    parents = {f["fixture_id"]: f for f in original}
    base = {(c["fixture_id"], c["repeat"]): c for c in pc.assessments(original, baseline)}
    fixtures = {f["fixture_id"]: f for f in fs}
    pairs, controls = [], []
    for c in pc.assessments(fs, calls):
        f = fixtures[c["fixture_id"]]
        parent_id = f.get("intervention", {}).get("parent_fixture_id", f["fixture_id"])
        before = base[(parent_id, c["repeat"])]
        if "intervention" not in f:
            controls.append({"fixture_id": parent_id, "repeat": c["repeat"],
                             **raw_equal(before, c)})
            continue
        before = {**before, **direction(parents[parent_id], before["choice"])}
        after = {**c, **direction(f, c["choice"])}
        pairs.append({"parent_fixture_id": parent_id, "repeat": c["repeat"],
                      "before": before, "after": after, "choice_changed": before["choice"] != c["choice"],
                      "direction_transition": before["direction"] + "->" + after["direction"],
                      "follows_both_final_clauses": before["direction"] == "open" and after["direction"] == "closed"})
    return pairs, controls


def raw_equal(a, b):
    keys = ("raw_logits", "probabilities", "temperature", "device", "dtype") if "raw_logits" in a else (
        "generated_ids", "logits_values_sha256")
    return {"choice_equal": a["choice"] == b["choice"],
            "raw_equal": all(a.get(k) == b.get(k) for k in keys)}


def report(output):
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = rows[0]["data"]["resolved_config"]
    original, baseline = baselines(config["source"], config["qwen_source"])
    fs = design(original)
    recorded = [r["data"] for r in rows if r["kind"] == "search_fixture"]
    if recorded != fs or config["fixture_ids"] != [f["fixture_id"] for f in fs]:
        raise ValueError("fixtures differ from predeclared suffix-only design")
    provider = config["provider"]
    model = next(r["data"]["model"] for r in rows if r["kind"] == "manifest_update" and "model" in r["data"])
    loaded = next(r["data"] for r in rows if r["kind"] == "model_loaded")
    if model["content_id"] != MODEL_IDS[provider] or _sha256_json(model["files_sha256"]) != model["content_id"]:
        raise ValueError("provider content identity differs")
    for name, sha in model["files_sha256"].items():
        if name.endswith((".json", ".txt", ".model", ".py")) and file_hash(Path(model["path"]) / name) != sha:
            raise ValueError("tokenizer/config changed since inference")
    old_rows, _ = load_records(Path(config["source"] if provider == "laya" else config["qwen_source"]) / "episodes.jsonl")
    if loaded != next(r["data"] for r in old_rows if r["kind"] == "model_loaded"):
        raise ValueError("loaded configuration differs from frozen baseline")
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    if provider == "laya":
        result = laya_report(output)
        calls, audited = result["calls"], result["complete"]
        prepared = {r["data"]["fixture_id"]: r["data"] for r in rows if r["kind"] == "provider_presentation"}
        for row in rows:
            if row["kind"] == "model_call_intent":
                d = row["data"]
                p = {k: v for k, v in prepared[d["fixture_id"]].items() if k != "fixture_id"}
                if p != d["input_encoding"]:
                    raise ValueError("consumed presentation differs from preflight")
    else:
        calls, audited = qwen_calls(output, rows, fs, loaded, model)
    actual = [(c["fixture_id"], c["repeat"]) for c in calls]
    expected = {(f["fixture_id"], rep) for f in fs for rep in (0, 1)}
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    complete = (audited and not errors and not failures and set(actual) == expected
                and len(actual) == len(expected) and config["repeats"] == 2
                and terminal == [{"reason": "interface_search_complete" if provider == "laya" else "clause_order_complete",
                                  "calls": len(expected)}])
    lookup = {(c["fixture_id"], c["repeat"]): c for c in calls}
    repeats = [{"fixture_id": f["fixture_id"], **raw_equal(lookup[(f["fixture_id"], 0)], lookup[(f["fixture_id"], 1)])}
               for f in fs if all((f["fixture_id"], rep) in lookup for rep in (0, 1))]
    pairs, controls = compare_calls(original, fs, baseline[provider], calls)
    stable = len(repeats) == len(fs) and all(r["choice_equal"] and r["raw_equal"] for r in repeats)
    reproduced = len(controls) == 4 and all(r["choice_equal"] and r["raw_equal"] for r in controls)
    native = [p["after"] for p in pairs if p["after"]["descriptions"] == "native"]
    gate = (complete and stable and reproduced and len(native) == 64
            and all(c["valid"] and c["presented_fact_consistent"] for c in native)
            and all(c["local_support"] for c in native if c["assignment"] == "true"))
    return {"provider": provider, "model": model, "raw_sha256": file_hash(output / "episodes.jsonl"),
            "complete": complete, "failures": failures, "record_diagnostics": errors,
            "matched_pairs": pairs, "controls": controls, "controls_reproduced": reproduced,
            "repeat_comparisons": repeats, "all_repeats_stable": stable,
            "original": pc.metrics([p["before"] for p in pairs]),
            "swapped": pc.metrics([p["after"] for p in pairs]),
            "native_bounded_reference_passed": gate, "formal_e0_ready": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="runs/effect-binding/factorial-v01")
    p.add_argument("--qwen-source", default="runs/provider-comparison/qwen-v01")
    p.add_argument("--provider", choices=("laya", "qwen"))
    p.add_argument("--device", default="cuda")
    p.add_argument("--output")
    p.add_argument("--summarize")
    args = p.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output and args.provider:
        run(args)
    else:
        p.error("provider and fresh output, or existing run to summarize required")


if __name__ == "__main__":
    main()
