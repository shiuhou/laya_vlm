"""One independent provider on frozen privileged effect fixtures; never executes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import time

import numpy as np

from ..runtime_core import _sha256_json
from .effect_binding import presented_support, report as baseline_report
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from .reference_gate import physical_assessment
from .reference_model_diagnostic import payload_id

VERSION = "frozen-provider-comparison-v0.1"
SOURCE_SHA256 = "3875a25255eeb7880e1168579567758f68d616d39a023cc28c1ddef3e0c5eea5"
MODEL_REPO = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
SYSTEM = "Return exactly one option ID from the supplied options, with no other text."
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/provider_comparison_protocol.md"


def frozen_source(path):
    path = Path(path)
    path = path / "episodes.jsonl" if path.is_dir() else path
    if file_hash(path) != SOURCE_SHA256:
        raise ValueError("not the frozen effect-binding source")
    baseline = baseline_report(path)
    if not baseline["complete"] or not baseline["factorial_complete"]:
        raise ValueError("complete audited baseline required")
    rows, errors = load_records(path)
    if errors:
        raise ValueError("incomplete source")
    fixtures = [r["data"] for r in rows if r["kind"] == "search_fixture"
                and r["data"]["source"]["effect_detail"] == "relative"]
    if len(fixtures) != 64:
        raise ValueError("all 64 full-effect fixtures required")
    for f in fixtures:
        q = f["questions"]["action"]
        q["criteria"] = {key: q["criteria"][key] for key in f["option_order"]}
        if payload_id(f["state"], f["questions"]) != f["payload_id"]:
            raise ValueError("frozen option order or payload mismatch")
    ids = {f["fixture_id"] for f in fixtures}
    return fixtures, [c for c in baseline["calls"] if c["fixture_id"] in ids]


def messages(state, questions):
    """Only provider-facing arguments; no fixture source or evaluator access."""
    if set(questions) != {"action"} or questions["action"]["type"] != "choice":
        raise ValueError("one typed choice question required")
    q = questions["action"]
    content = (f"choice question: {q['instructions']}\n"
               + "\n".join(f"{k}: {v}" for k, v in q["criteria"].items())
               + "\n" + state)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": content}]


def parse_choice(text, allowed):
    # Invalid responses remain invalid; no regex extraction, retry or fallback.
    return text.strip() if text.strip() in allowed else None


def values_hash(values):
    return hashlib.sha256(np.ascontiguousarray(values, dtype=np.float32).tobytes()).hexdigest()


class FrozenTransformersProvider:
    """Offline choice adapter, not registered as a live runtime policy.

    Like the archived Laya diagnostic, accepts only state and typed questions.
    It cannot read numeric evaluation outcomes or choose from a preferred set.
    """

    def __init__(self, path, device):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(
            path, local_files_only=True, trust_remote_code=False, torch_dtype=torch.bfloat16,
            attn_implementation="sdpa").to(device).eval()
        defaults = json.loads((Path(path) / "generation_config.json").read_text())
        # Explicit defaults avoid inheriting checkpoint sampling/repetition penalties.
        self.generation = GenerationConfig(
            do_sample=False, max_new_tokens=16, use_cache=True,
            bos_token_id=defaults["bos_token_id"], eos_token_id=defaults["eos_token_id"],
            pad_token_id=defaults["pad_token_id"], return_dict_in_generate=True, output_logits=True)

    def prepare(self, state, questions):
        msgs = messages(state, questions)
        prompt = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = self.tokenizer(prompt, add_special_tokens=False, truncation=False)["input_ids"]
        direct = self.tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
        if ids != direct or len(ids) + 16 > self.model.config.max_position_embeddings:
            raise ValueError("complete matching chat tokenization required")
        return {"messages": msgs, "rendered_prompt": prompt, "input_ids": ids,
                "input_id": _sha256_json(ids), "prompt_sha256": _sha256_json(prompt),
                "truncated": False, "payload_id": payload_id(state, questions)}

    def infer(self, prepared):
        torch = self.torch
        traces = []

        def observe(module, args, kwargs):
            ids = kwargs.get("input_ids", args[0] if args else None)
            traces.append(ids.detach().cpu().tolist() if ids is not None else None)

        hook = self.model.register_forward_pre_hook(observe, with_kwargs=True)
        inputs = torch.tensor([prepared["input_ids"]], dtype=torch.long, device=self.model.device)
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                result = self.model.generate(input_ids=inputs, attention_mask=torch.ones_like(inputs),
                                             generation_config=self.generation)
            sequence = result.sequences[0].detach().cpu().tolist()
            logits = torch.stack(result.logits)[:, 0, :].float().cpu().numpy()
        finally:
            hook.remove()
        generated = sequence[len(prepared["input_ids"]):]
        return {"sequence_ids": sequence, "generated_ids": generated,
                "decoded_text": self.tokenizer.decode(generated, skip_special_tokens=True),
                "raw_decoded_text": self.tokenizer.decode(generated, skip_special_tokens=False),
                "forward_input_ids": traces, "device": str(self.model.device),
                "dtype": str(self.model.dtype), "latency_ms": (time.perf_counter()-started)*1000,
                "option_probabilities": None,
                "probability_scope": "full vocabulary logits at each generated token; no option distribution"}, logits


def validate_raw(prepared, raw, logits, tokenizer, vocab_size):
    generated = raw["generated_ids"]
    if not 0 < len(generated) <= 16:
        raise ValueError("invalid generation length")
    if raw["sequence_ids"] != prepared["input_ids"] + generated:
        raise ValueError("generated sequence does not preserve the prompt")
    expected_traces = [[prepared["input_ids"]]] + [[[t]] for t in generated[:-1]]
    if raw["forward_input_ids"] != expected_traces:
        raise ValueError("actual consumed tokens differ from audited generation")
    if logits.shape != (len(generated), vocab_size) or not np.isfinite(logits).all():
        raise ValueError("invalid full vocabulary logits")
    if logits.argmax(axis=1).tolist() != generated:
        raise ValueError("generated IDs differ from raw greedy argmax")
    if (raw["decoded_text"] != tokenizer.decode(generated, skip_special_tokens=True)
            or raw["raw_decoded_text"] != tokenizer.decode(generated, skip_special_tokens=False)):
        raise ValueError("decoded output differs from generated token IDs")


def run(args):
    fs, _ = frozen_source(args.source)
    config = {"version": VERSION, "source": str(Path(args.source).resolve()),
              "source_sha256": SOURCE_SHA256, "fixture_ids": [f["fixture_id"] for f in fs],
              "repeats": 2, "seed": 1, "batch_size": 1, "provider": MODEL_REPO,
              "revision": MODEL_REVISION, "protocol_sha256": file_hash(PROTOCOL),
              "no_execution": True, "not_formal_e0": True, "privileged_effects": True}
    recorder = RunRecorder(args.output, config, {"run_id": Path(args.output).name,
                           "code": code_identity(), "versions": versions()})
    try:
        for f in fs:
            recorder.record("search_fixture", f)
        recorder.manifest_update({"model": {**model_identity(args.model_path),
                                           "repo_id": MODEL_REPO, "revision": MODEL_REVISION}})
        import torch
        torch.set_num_threads(4)
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        provider = FrozenTransformersProvider(args.model_path, args.device)
        recorder.record("model_loaded", {"config": provider.model.config.to_dict(),
                                         "generation_config": provider.generation.to_dict(),
                                         "device": str(provider.model.device), "dtype": str(provider.model.dtype),
                                         "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
                                         "system_instruction": SYSTEM})
        # Audit and record every presentation before any model inference.
        prepared = {}
        for f in fs:
            prepared[f["fixture_id"]] = provider.prepare(f["state"], f["questions"])
            recorder.record("provider_presentation", {"fixture_id": f["fixture_id"], **prepared[f["fixture_id"]]})
        for repeat in range(2):
            for ordinal, f in enumerate(fs if repeat == 0 else list(reversed(fs))):
                identity = {"fixture_id": f["fixture_id"], "repeat": repeat, "ordinal": ordinal}
                cid = _sha256_json(identity)
                recorder.record("provider_call_intent", {**identity, "call_id": cid,
                                "input_id": prepared[f["fixture_id"]]["input_id"]})
                raw, logits = provider.infer(prepared[f["fixture_id"]])
                artifact = Path("logits") / f"{cid}.npz"
                path = Path(args.output) / artifact
                path.parent.mkdir(exist_ok=True)
                with path.open("xb") as stream:
                    np.savez_compressed(stream, logits=logits)
                    stream.flush()
                    os.fsync(stream.fileno())
                recorder.record("provider_raw_response", {"call_id": cid, **raw,
                                "logits_artifact": str(artifact), "logits_sha256": file_hash(path),
                                "logits_values_sha256": values_hash(logits)})
                validate_raw(prepared[f["fixture_id"]], raw, logits, provider.tokenizer,
                             provider.model.config.vocab_size)
        recorder.record("termination", {"reason": "provider_comparison_complete", "calls": 128})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def assessments(fixtures, calls):
    fs = {f["fixture_id"]: f for f in fixtures}
    result = []
    for c in calls:
        f = fs[c["fixture_id"]]
        s, token = f["source"], c["choice"]
        valid = token in f["option_to_canonical"].values()
        physical = physical_assessment(s, token) if valid else {
            "local_support": False, "contract_flag": None, "absolute_closure_mm": None,
            "closure_vs_stop_mm": None}
        result.append({**c, "condition": f["condition"], "sample": f["sample"],
                       "goal": s["goal"], "valid": valid, "physical": s["physical"],
                       "assignment": s["assignment"], "reverse": s["reverse"],
                       "descriptions": s["descriptions"],
                       "presented_supported_set": [t for t in f["option_to_canonical"].values() if presented_support(s, t)],
                       "presented_fact_consistent": valid and presented_support(s, token), **physical})
    return result


def metrics(calls):
    first = [c for c in calls if c["repeat"] == 0]
    groups = {}
    for c in first:
        g = groups.setdefault(c["condition"], {"calls": 0, "valid": 0, "presented_fact_consistent": 0,
                                              "actual_local_support": 0, "contract_flagged": 0})
        for key, value in (("calls", 1), ("valid", c["valid"]),
                           ("presented_fact_consistent", c["presented_fact_consistent"]),
                           ("actual_local_support", c["local_support"]),
                           ("contract_flagged", c["contract_flag"] is True)):
            g[key] += value
    keys = ("descriptions", "assignment", "goal", "reverse")

    def key(c, override=None):
        factors = {k: c[k] for k in keys}
        factors.update(override or {})
        return (c["physical"]["init_state_id"], c["physical"]["environment_step"],
                *(factors[k] for k in keys))

    by_key = {key(c): c for c in first}
    contrasts = {}
    for factor, before, after in (("goal", "closed", "open"),
                                  ("assignment", "true", "shift4"), ("reverse", False, True)):
        contrasts[factor] = []
        for c in first:
            if c[factor] != before or key(c, {factor: after}) not in by_key:
                continue
            other = by_key[key(c, {factor: after})]
            contrasts[factor].append({"condition": c["condition"], "sample": c["sample"],
                                     "before_choice": c["choice"], "after_choice": other["choice"],
                                     "choice_changed": c["choice"] != other["choice"],
                                     "requires_change": not set(c["presented_supported_set"]) & set(other["presented_supported_set"]),
                                     "both_fact_consistent": c["presented_fact_consistent"] and other["presented_fact_consistent"],
                                     "both_physically_supported": c["local_support"] and other["local_support"]})
    return {"groups_first_repeat": groups, "contrasts_first_repeat": contrasts}


def report(output):
    from transformers import AutoTokenizer
    output = Path(output)
    rows, errors = load_records(output / "episodes.jsonl")
    config = rows[0]["data"]["resolved_config"]
    original, laya = frozen_source(config["source"])
    expected_fs = {f["fixture_id"]: f for f in original}
    fs, prepared, intents, completed = {}, {}, {}, set()
    calls, failures = [], []
    model = loaded = tokenizer = terminal = None
    for row in rows:
        d, kind = row["data"], row["kind"]
        if kind == "search_fixture":
            fid = d["fixture_id"]
            if fid in fs or d != expected_fs.get(fid):
                raise ValueError("fixture differs from frozen source or is duplicated")
            fs[fid] = d
        elif kind == "manifest_update" and "model" in d:
            model = d["model"]
            if (model["repo_id"], model["revision"]) != (MODEL_REPO, MODEL_REVISION):
                raise ValueError("provider identity differs from protocol")
            for name, sha in model["files_sha256"].items():
                if name.endswith((".json", ".txt", ".model", ".py")) and file_hash(Path(model["path"]) / name) != sha:
                    raise ValueError("tokenizer/config changed since inference")
            tokenizer = AutoTokenizer.from_pretrained(model["path"], local_files_only=True, trust_remote_code=False)
        elif kind == "model_loaded":
            loaded = d
        elif kind == "provider_presentation":
            fid = d["fixture_id"]
            f = expected_fs[fid]
            msgs = messages(f["state"], f["questions"])
            prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            ids = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True)
            if (fid in prepared or d["messages"] != msgs or d["rendered_prompt"] != prompt
                    or d["input_ids"] != ids or d["input_id"] != _sha256_json(ids)
                    or d["prompt_sha256"] != _sha256_json(prompt) or d["truncated"]
                    or d["payload_id"] != f["payload_id"]):
                raise ValueError("provider presentation does not preserve frozen payload")
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
                raise ValueError("orphan or duplicate provider response")
            intent = intents[cid]
            artifact = output / d["logits_artifact"]
            if file_hash(artifact) != d["logits_sha256"]:
                raise ValueError("logits artifact integrity failure")
            with np.load(artifact, allow_pickle=False) as saved:
                logits = saved["logits"]
            if values_hash(logits) != d["logits_values_sha256"]:
                raise ValueError("raw logits value hash mismatch")
            validate_raw(prepared[intent["fixture_id"]], d, logits, tokenizer, loaded["config"]["vocab_size"])
            if d["device"] != loaded["device"] or d["dtype"] != loaded["dtype"]:
                raise ValueError("provider device or dtype changed")
            f = fs[intent["fixture_id"]]
            choice = parse_choice(d["decoded_text"], f["option_order"])
            calls.append({"fixture_id": f["fixture_id"], "repeat": intent["repeat"],
                          "choice": f["option_to_canonical"].get(choice), "option_id": choice,
                          "decoded_text": d["decoded_text"], "generated_ids": d["generated_ids"],
                          "logits_values_sha256": d["logits_values_sha256"],
                          "input_tokens": len(prepared[f["fixture_id"]]["input_ids"]),
                          "latency_ms": d["latency_ms"]})
            completed.add(cid)
        elif kind == "failure":
            failures.append(d)
        elif kind == "termination":
            terminal = d
    planned = {(fid, rep) for fid in expected_fs for rep in (0, 1)}
    actual = [(c["fixture_id"], c["repeat"]) for c in calls]
    complete = (set(fs) == set(prepared) == set(expected_fs) and len(actual) == len(set(actual))
                and set(actual) == planned and set(intents) == completed and not failures and not errors
                and terminal == {"reason": "provider_comparison_complete", "calls": 128}
                and config["fixture_ids"] == list(expected_fs) and config["repeats"] == 2)
    repeats = []
    for fid in expected_fs:
        paired = sorted((c for c in calls if c["fixture_id"] == fid), key=lambda c: c["repeat"])
        if len(paired) == 2:
            a, b = paired
            repeats.append({"fixture_id": fid, "choice_equal": a["choice"] == b["choice"],
                            "generated_ids_equal": a["generated_ids"] == b["generated_ids"],
                            "logits_equal": a["logits_values_sha256"] == b["logits_values_sha256"]})
    judged = assessments(original, calls)
    baseline = assessments(original, laya)
    stable = len(repeats) == 64 and all(c["choice_equal"] and c["generated_ids_equal"] and c["logits_equal"] for c in repeats)
    native = [c for c in judged if c["descriptions"] == "native"]
    gate = (complete and stable and len(native) == 64 and all(c["valid"] and c["presented_fact_consistent"] for c in native)
            and all(c["local_support"] for c in native if c["assignment"] == "true"))
    return {"raw_sha256": file_hash(output / "episodes.jsonl"), "complete": complete,
            "provider": model, "failures": failures, "record_diagnostics": errors,
            "unmatched_intents": sorted(set(intents)-completed), "calls": judged,
            "repeat_comparisons": repeats, "all_repeats_stable": stable,
            "independent": metrics(judged), "laya": metrics(baseline),
            "native_bounded_reference_passed": gate, "formal_e0_ready": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="runs/effect-binding/factorial-v01")
    p.add_argument("--model-path", default="/home/junhongli/models/huggingface/Qwen2.5-7B-Instruct")
    p.add_argument("--device", default="cuda")
    p.add_argument("--output")
    p.add_argument("--summarize")
    args = p.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output:
        run(args)
    else:
        p.error("fresh output or existing run to summarize required")


if __name__ == "__main__":
    main()
