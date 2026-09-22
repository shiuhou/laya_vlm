"""Bounded presentation/state controls for the existing oracle decision reference.

No simulator is constructed and no model choice is executed. This is not primary
E0 replay: label, ordering, masking and objective interventions are explicitly
named. The checkpoint/API and eleven physical alternatives remain unchanged.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import time

import numpy as np

from ..adapters.laya_input import encoding_audit
from ..runtime_core import MOVE, _sha256_json, load_laya_provider
from .equivalence import paired_inputs
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

VERSION = "reference-model-diagnostic-v0.1"
STEPS = (0, 29, 48, 140)
CONDITIONS = ("baseline", "reverse_options", "neutral_keys", "target_evidence_masked",
              "approach_objective", "approach_mirrored_geometry")
APPROACH_INSTRUCTION = (
    "Minimize TCP-to-target Euclidean distance with one nominal 10mm world translation. "
    "Leave the gripper unchanged. Choose STOP only if no translation improves distance. "
    "This is a geometric command test, not a contact or dynamics prediction."
)
MASK_RETAINED_FIELDS = frozenset({"task.instruction", "task.target_identity", "robot.tcp_position_m",
                                 "robot.gripper_width_m", "robot.gripper_command"})


def payload_id(state, questions):
    # A sorted-JSON hash alone loses criterion insertion order, which Laya uses.
    return _sha256_json({"state": state, "questions": questions,
                         "option_order": {key: list(q["criteria"]) for key, q in questions.items()}})


def _six(value):
    return float(f"{float(value):.6g}")


def mirror_geometry(state):
    """Instantaneous counterfactual, not a new physical trajectory.

Reflect target position about the current TCP and recompute all four relational
fields. Preserve history, effects, quality and robot state. An existing target
velocity is an independent instantaneous value, not a reconstructed history.
"""
    result = deepcopy(state)
    values = result["state"]
    tcp, target = values["robot.tcp_position_m"], values["target.position_m"]
    if tcp is None or target is None:
        raise ValueError("geometry reflection requires known TCP and target positions")
    tcp, target = np.asarray(tcp, dtype=float), np.asarray(target, dtype=float)
    if tcp.shape != (3,) or target.shape != (3,) or not np.isfinite([tcp, target]).all():
        raise ValueError("invalid geometry for reflection")
    reflected = [_six(x) for x in 2 * tcp - target]
    delta = np.asarray(reflected) - tcp
    values["target.position_m"] = reflected
    values["relations.tcp_target_delta_m"] = [_six(x) for x in delta]
    values["relations.distance_m"] = _six(np.linalg.norm(delta))
    values["relations.xy_error_m"] = _six(np.linalg.norm(delta[:2]))
    values["relations.height_error_m"] = _six(delta[2])
    return result


def nominal_geometry_reference(state):
    """Evaluator-only arithmetic; never part of the model payload or task label."""
    values = state["state"]
    tcp, target = values.get("robot.tcp_position_m"), values.get("target.position_m")
    if tcp is None or target is None:
        return {"kind": "nominal_translation_distance", "expected_tokens": None,
                "reason": "geometry_unknown", "not_task_expert_or_controller_prediction": True}
    delta = np.asarray(target) - tcp
    before = float(np.linalg.norm(delta))
    distances = {token: float(np.linalg.norm(delta - .01 * np.asarray(direction)))
                 for token, direction in MOVE.items()}
    best = min(distances.values())
    preferred = ([token for token, value in distances.items() if abs(value - best) <= 1e-12]
                 if best < before - 1e-12 else ["STOP"])
    return {"kind": "nominal_translation_distance", "expected_tokens": preferred,
            "distance_before_m": before, "nominal_distance_after_m": distances,
            "not_task_expert_or_controller_prediction": True}


def make_fixture(pair, condition):
    oracle, _ = paired_inputs(pair)
    state, questions = oracle.provider_input(), oracle.model_questions()
    if state.get("effects") or oracle.effects.effects:
        raise ValueError("model diagnostic forbids candidate effects")
    criteria = questions["action"]["criteria"]
    if len(criteria) != 11:
        raise ValueError("diagnostic requires the original eleven alternatives")
    mapping = {token: token for token in criteria}
    expected = None
    if condition == "reverse_options":
        questions["action"]["criteria"] = dict(reversed(list(criteria.items())))
    elif condition == "neutral_keys":
        mapping = {f"A{index:02d}": token for index, token in enumerate(criteria)}
        questions["action"]["criteria"] = {label: criteria[token] for label, token in mapping.items()}
    elif condition == "target_evidence_masked":
        state["state"] = {key: value if key in MASK_RETAINED_FIELDS else None
                          for key, value in state["state"].items()}
    elif condition in {"approach_objective", "approach_mirrored_geometry"}:
        questions["action"]["instructions"] = APPROACH_INSTRUCTION
        if condition == "approach_mirrored_geometry":
            state = mirror_geometry(state)
        expected = nominal_geometry_reference(state)["expected_tokens"]
    elif condition in {"sentinel_MV_FWD", "sentinel_MV_BACK"}:
        token = condition.removeprefix("sentinel_")
        questions["action"]["instructions"] = (
            f"Instruction-following sentinel: choose exactly {token}, regardless of the supplied state. "
            "Do not solve the physical task. This choice is not executed."
        )
        expected = [token]
    elif condition != "baseline":
        raise ValueError("unknown diagnostic condition")
    result = {"condition": condition, "pair_id": pair["pair_id"],
              "environment_step": pair["physical"]["environment_step"],
              "source_snapshot_id": oracle.snapshot_id(), "source_candidate_set_id": oracle.candidate_set_id(),
              "state": state, "questions": questions, "option_order": list(questions["action"]["criteria"]),
              "option_to_canonical": mapping, "payload_id": payload_id(state, questions),
              "diagnostic_reference_not_model_input": {"scored_expected_tokens": expected,
                                                        "nominal_geometry": nominal_geometry_reference(state)}}
    result["fixture_id"] = _sha256_json(result)
    return result


def selected_pairs(path):
    rows, diagnostics = load_records(path)
    if diagnostics or not any(r["kind"] == "termination" and
                             r["data"].get("reason") == "collection_smoke_complete" for r in rows):
        raise ValueError("source must be a complete accepted paired collection")
    selected = {}
    for row in rows:
        if row["kind"] != "paired_state":
            continue
        pair = row["data"]
        step = pair["physical"]["environment_step"]
        if step not in STEPS:
            continue
        if pair["physical"]["task"] != "top_drawer" or pair["physical"]["init_state_id"] != 0:
            raise ValueError("diagnostic requires top_drawer init 0 fixtures")
        if step in selected:
            raise ValueError("ambiguous duplicate physical boundary")
        paired_inputs(pair)  # verify content identity, privilege, candidates, effects
        selected[step] = pair
    if set(selected) != set(STEPS):
        raise ValueError(f"source must contain all selected boundaries {STEPS}")
    return [selected[step] for step in STEPS]


def active_temperature(agent, count):
    bucket = "2" if count <= 2 else "3-5" if count <= 5 else "6-10" if count <= 10 else "11+"
    temperatures = getattr(agent, "temperature", agent.cfg.get("temperature", [1., 1., 1.]))
    by_options = getattr(agent, "temperature_by_options", agent.cfg.get("temperature_by_options", {}))
    configured = float(by_options.get("choice:" + bucket, temperatures[0]))
    return {"bucket": "choice:" + bucket, "configured": configured, "effective": max(1e-3, configured)}


def observe_forward(agent, traces):
    """Read-only forward hook; return None, never replacing the model's output."""
    model = getattr(agent, "model", None)
    if not hasattr(model, "register_forward_hook"):
        return None

    def hook(module, inputs, output):
        ids, attention, markers = (item.detach().cpu().numpy() for item in inputs[:3])
        traces.append({"input_ids": [row[mask.astype(bool)].tolist() for row, mask in zip(ids, attention)],
                       "option_markers": markers.tolist(),
                       "raw_option_logits": output[0].detach().float().cpu().numpy().tolist(),
                       "raw_act_logits": output[1].detach().float().cpu().numpy().tolist()})
        return None

    return model.register_forward_hook(hook)


def _softmax(logits):
    values = np.asarray(logits, dtype=float)
    probabilities = np.exp(values - values.max())
    return (probabilities / probabilities.sum()).tolist()


def run_call(agent, fixture, recorder, *, repeat, ordinal, capture_logits=True):
    state, questions = deepcopy(fixture["state"]), deepcopy(fixture["questions"])
    audit = encoding_audit(agent, state, questions)
    temperature = active_temperature(agent, len(fixture["option_order"]))
    call_id = _sha256_json({"fixture_id": fixture["fixture_id"], "repeat": repeat, "ordinal": ordinal})
    recorder.record("model_call_intent", {"call_id": call_id, "fixture_id": fixture["fixture_id"],
                     "repeat": repeat, "ordinal": ordinal, "payload_id": payload_id(state, questions),
                     "input_encoding": audit, "temperature": temperature,
                     "device_before": str(getattr(agent, "device", "unknown")),
                     "dtype_before": str(getattr(agent, "dtype", "unknown"))})
    traces, handle = [], None
    started = None
    try:
        if not audit.get("available") or audit.get("truncated"):
            raise ValueError("complete tokenizer audit required before inference")
        if capture_logits:
            handle = observe_forward(agent, traces)
        started = time.perf_counter()
        response = agent.system_one(state, questions)
        latency_ms = (time.perf_counter() - started) * 1000.
        # Preserve original output before interpreting or validating its contents.
        recorder.record("model_raw_response", {"call_id": call_id, "raw_response": response,
                         "forward_traces": traces, "forward_hook_active": handle is not None,
                         "latency_ms": latency_ms, "latency_includes_observation_hook": handle is not None,
                         "actual_device": str(getattr(agent, "device", "unknown")),
                         "actual_dtype": str(getattr(agent, "dtype", "unknown"))})
        if payload_id(state, questions) != fixture["payload_id"]:
            raise ValueError("agent mutated diagnostic input")
        answer = response["answers"]["action"]
        mapping = fixture["option_to_canonical"]
        choice = mapping.get(answer["choice"])
        probabilities = answer.get("probabilities", {})
        canonical = {mapping[key]: value for key, value in probabilities.items() if key in mapping}
        expected = fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"]
        analysis = {"call_id": call_id, "fixture_id": fixture["fixture_id"], "repeat": repeat,
                    "canonical_choice": choice, "choice_allowed": choice is not None,
                    "canonical_probabilities": canonical, "distribution_complete": set(probabilities) == set(mapping),
                    "matches_diagnostic_reference": None if expected is None else choice in expected,
                    "reference_is_not_task_expert": True, "temperature": temperature}
        if traces:
            actual = traces[-1]
            planned = audit["questions"]["action"]
            if actual["input_ids"] != [planned["effective_input_ids"]] or actual["option_markers"] != [planned["option_markers"]]:
                raise ValueError("actual model tokens or option markers differ from audited input")
            logits = np.asarray(actual["raw_option_logits"])[0]
            if len(logits) != len(mapping) or not np.isfinite(logits).all():
                raise ValueError("invalid observed logits")
            before = _softmax(logits)
            after = _softmax(logits / temperature["effective"])
            analysis.update({"actual_input_id": _sha256_json(actual["input_ids"][0]),
                             "pre_temperature_probabilities": dict(zip(fixture["option_order"], before)),
                             "post_temperature_unrounded_probabilities": dict(zip(fixture["option_order"], after))})
            # Logit order follows the rendered criteria, not mapping insertion order.
            analysis["canonical_raw_logits"] = {mapping[key]: float(logits[index])
                                                for index, key in enumerate(fixture["option_order"])}
        recorder.record("model_call_analysis", analysis)
        return analysis
    except BaseException as exc:
        recorder.record("failure", {"category": "model_diagnostic_error", "call_id": call_id,
                         "fixture_id": fixture["fixture_id"], "exception": repr(exc),
                         "inference_started": started is not None})
        raise
    finally:
        if handle is not None:
            handle.remove()


def _distribution(probabilities):
    values = np.asarray(list(probabilities.values()), dtype=float)
    if len(values) != 11 or not np.isfinite(values).all() or (values < 0).any() or abs(values.sum() - 1.) > .0006:
        raise ValueError("invalid eleven-choice distribution")
    ordered = sorted(probabilities, key=lambda key: -probabilities[key])
    normalized = values / values.sum()
    positive = normalized[normalized > 0]
    return {"probabilities": probabilities, "top1": ordered[0], "top2": ordered[:2],
            "margin": float(probabilities[ordered[0]] - probabilities[ordered[1]]),
            "entropy_nats": float(-(positive * np.log(positive)).sum())}


def _comparison(left, right):
    result = {"left_call_id": left["call_id"], "right_call_id": right["call_id"],
              "choice_agreement": left["choice"] == right["choice"], "distributions": {}}
    for name in ("api_rounded", "pre_temperature", "post_temperature"):
        a, b = left[name], right[name]
        if a is None or b is None:
            result["distributions"][name] = None
            continue
        keys = sorted(a["probabilities"])
        p, q = (np.asarray([dist["probabilities"][key] for key in keys], dtype=float) for dist in (a, b))
        p, q = p / p.sum(), q / q.sum()
        midpoint = (p + q) / 2.
        divergence = sum(float((v[v > 0] * np.log(v[v > 0] / midpoint[v > 0])).sum()) for v in (p, q)) / 2.
        result["distributions"][name] = {"js_divergence_nats": divergence,
                                        "max_abs_difference": float(np.abs(p - q).max())}
    return result


def summarize(path):
    """Pure recovery from raw source/fixture/intent/response records, never analysis caches.

    Incomplete runs retain completed responses and list unmatched intents. JSONL
    sorting discards dictionary insertion order, so stored option_order is always
    used to reconstruct the actual presentation and align observed model logits.
    """
    path = Path(path)
    if path.is_dir():
        path = path / "episodes.jsonl"
    rows, diagnostics = load_records(path)
    sources, fixtures, intents, responses, failures = {}, {}, {}, {}, []
    complete = False
    for row in rows:
        kind, data = row["kind"], row["data"]
        if kind == "paired_source":
            paired_inputs(data)
            destination, key = sources, data["pair_id"]
        elif kind == "diagnostic_fixture":
            pair = sources.get(data["pair_id"])
            if pair is None or make_fixture(pair, data["condition"]) != data:
                raise ValueError("fixture differs from validated source/control")
            destination, key = fixtures, data["fixture_id"]
        elif kind == "model_call_intent":
            fixture = fixtures.get(data["fixture_id"])
            expected_id = _sha256_json({key: data[key] for key in ("fixture_id", "repeat", "ordinal")})
            if fixture is None or data["call_id"] != expected_id or data["payload_id"] != fixture["payload_id"]:
                raise ValueError("call intent does not match validated fixture")
            if not data["input_encoding"].get("available") or data["input_encoding"].get("truncated"):
                # Invalid preflight is still a preserved attempted call, not an accepted inference.
                failures.append({"category": "input_audit_invalid", "call_id": data["call_id"]})
            destination, key = intents, data["call_id"]
        elif kind == "model_raw_response":
            if data["call_id"] not in intents:
                raise ValueError("response without earlier call intent")
            destination, key = responses, data["call_id"]
        elif kind == "failure":
            failures.append(data)
            continue
        elif kind == "termination":
            complete = data.get("reason") == "reference_model_diagnostic_complete"
            continue
        else:
            continue  # model_call_analysis is deliberately not consumed
        if key in destination:
            raise ValueError(f"duplicate {kind} identity")
        destination[key] = data
    calls = []
    for call_id, response in responses.items():
        intent = intents[call_id]
        fixture = fixtures[intent["fixture_id"]]
        mapping, order = fixture["option_to_canonical"], fixture["option_order"]
        answer = response["raw_response"]["answers"]["action"]
        if answer["choice"] not in mapping or set(answer["probabilities"]) != set(mapping):
            raise ValueError("raw response does not cover fixture options")
        expected = fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"]
        choice = mapping[answer["choice"]]
        result = {"call_id": call_id, "fixture_id": fixture["fixture_id"], "condition": fixture["condition"],
                  "environment_step": fixture["environment_step"], "repeat": intent["repeat"],
                  "ordinal": intent["ordinal"], "choice": choice,
                  "api_rounded": _distribution({mapping[key]: answer["probabilities"][key] for key in order}),
                  "confidence": answer.get("confidence"), "act_probability": answer.get("action", {}).get("act_probability"),
                  "pre_temperature": None, "post_temperature": None, "raw_logits": None,
                  "raw_act_logits": None, "raw_logit_margin": None,
                  "temperature": intent["temperature"], "latency_ms": response["latency_ms"],
                  "actual_device": response["actual_device"], "actual_dtype": response["actual_dtype"],
                  "matches_diagnostic_reference": None if expected is None else choice in expected,
                  "reference_is_not_task_expert": True}
        traces = response["forward_traces"]
        if traces:
            if len(traces) != 1:
                raise ValueError("ambiguous multi-forward response")
            trace = traces[0]
            planned = intent["input_encoding"]["questions"]["action"]
            if trace["input_ids"] != [planned["effective_input_ids"]] or trace["option_markers"] != [planned["option_markers"]]:
                raise ValueError("actual tokens/markers differ from intended input")
            logits = np.asarray(trace["raw_option_logits"], dtype=float)
            temperature = intent["temperature"]
            if (logits.shape != (1, 11) or not np.isfinite(logits).all()
                    or not np.isfinite(temperature["effective"]) or temperature["effective"] <= 0
                    or temperature["effective"] != max(.001, temperature["configured"])):
                raise ValueError("invalid raw logits or temperature")
            logits = logits[0]
            result["raw_logits"] = {mapping[key]: float(logits[index]) for index, key in enumerate(order)}
            result["raw_act_logits"] = trace["raw_act_logits"]
            result["raw_logit_margin"] = float(np.sort(logits)[-1] - np.sort(logits)[-2])
            for name, values in (("pre_temperature", logits), ("post_temperature", logits / temperature["effective"])):
                result[name] = _distribution(dict(zip((mapping[key] for key in order), _softmax(values))))
            result["api_vs_observed_probability_max_error"] = max(
                abs(result["post_temperature"]["probabilities"][token] - probability)
                for token, probability in result["api_rounded"]["probabilities"].items())
            result["choice_matches_observed_argmax"] = choice == mapping[order[int(logits.argmax())]]
        calls.append(result)
    by_fixture, by_boundary = {}, {}
    for call in calls:
        by_fixture.setdefault(call["fixture_id"], []).append(call)
        key = (call["environment_step"], call["repeat"], call["condition"])
        if key in by_boundary:
            raise ValueError("duplicate condition at boundary/repeat")
        by_boundary[key] = call
    repeat_comparisons, control_comparisons = [], []
    for fixture_calls in by_fixture.values():
        fixture_calls.sort(key=lambda item: item["repeat"])
        for later in fixture_calls[1:]:
            repeat_comparisons.append(_comparison(fixture_calls[0], later))
    for (step, repeat, condition), call in by_boundary.items():
        baseline = by_boundary.get((step, repeat, "baseline"))
        if baseline is not None and condition != "baseline":
            control_comparisons.append({"environment_step": step, "repeat": repeat, "condition": condition,
                                        **_comparison(baseline, call)})
    return {"version": VERSION, "raw_sha256": file_hash(path), "termination_recorded": complete,
            "fixture_count": len(fixtures), "completed_response_count": len(calls), "calls": calls,
            "unmatched_intent_ids": sorted(set(intents) - set(responses)),
            "record_diagnostics": diagnostics, "failures": failures,
            "repeat_comparisons": repeat_comparisons, "baseline_control_comparisons": control_comparisons,
            "analysis_cache_used": False}


def run(args):
    if args.repeats != 2:
        raise ValueError("bounded diagnostic requires exactly two repeats (52 calls)")
    config = {**vars(args), "experiment_version": VERSION, "oracle": True, "selected_steps": STEPS,
              "conditions": CONDITIONS, "calls_planned": 52, "presentation": "compact-v0.1 + declared controls",
              "mask_retained_fields": sorted(MASK_RETAINED_FIELDS),
              "mask_preserves": "robot/task fields above; entire original history and empty effects",
              "approach_instruction": APPROACH_INSTRUCTION, "seed_scope": "once before model load",
              "source_sha256": file_hash(args.pairs_jsonl),
              "purpose": "reference interpretation diagnostic, not E0 or policy evaluation"}
    recorder = RunRecorder(args.output, config, {"run_id": Path(args.output).name, "code": code_identity(),
                                                "versions": versions(), "oracle": True})
    try:
        pairs = selected_pairs(args.pairs_jsonl)
        fixtures = [make_fixture(pair, condition) for pair in pairs for condition in CONDITIONS]
        fixtures += [make_fixture(pairs[0], f"sentinel_{token}") for token in ("MV_FWD", "MV_BACK")]
        for pair in pairs:
            recorder.record("paired_source", pair)
        for fixture in fixtures:
            recorder.record("diagnostic_fixture", fixture)
        if not Path(args.laya_path).is_dir():
            raise ValueError("diagnostic only loads existing local checkpoints")
        import torch
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        recorder.manifest_update({"model": model_identity(args.laya_path)})
        agent = load_laya_provider(args.laya_path, subfolder=None, device=args.device).agent
        recorder.record("model_loaded", {"config": agent.cfg, "temperature": agent.temperature,
                        "temperature_by_options": agent.temperature_by_options,
                        "actual_device": str(agent.device), "actual_dtype": str(agent.dtype),
                        "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                        "cuda_version": torch.version.cuda,
                        "api": "same installed Agent.system_one; direct raw response retained"})
        for repeat in range(args.repeats):
            ordered = fixtures if repeat == 0 else list(reversed(fixtures))
            for ordinal, fixture in enumerate(ordered):
                run_call(agent, fixture, recorder, repeat=repeat, ordinal=ordinal,
                         capture_logits=not args.no_logit_hook)
        recorder.record("termination", {"reason": "reference_model_diagnostic_complete",
                                         "model_calls": len(fixtures) * args.repeats, "executed_actions": 0})
    except BaseException as exc:
        recorder.record("failure", {"category": "diagnostic_error", "exception": repr(exc)})
        raise
    finally:
        recorder.close()
    print(args.output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs_jsonl", nargs="?")
    parser.add_argument("--output")
    parser.add_argument("--summarize", metavar="JSONL_OR_DIRECTORY")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    parser.add_argument("--no-logit-hook", action="store_true")
    args = parser.parse_args()
    if args.summarize:
        print(json.dumps(summarize(args.summarize), indent=2, allow_nan=False))
    elif not args.pairs_jsonl or not args.output:
        parser.error("pairs_jsonl and --output are required for inference")
    else:
        run(args)


if __name__ == "__main__":
    main()
