"""Bounded offline interface capability search; never changes the runtime policy."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random

import numpy as np

from ..runtime_core import MOVE, _sha256_json, load_laya_provider
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions
from .reference_model_diagnostic import payload_id, run_call
from .equivalence import paired_inputs

VERSION = "interface-search-v0.1"
TOKENS = list(MOVE) + ["ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP", "RELEASE"]
COMPACT = ["world +X 10mm", "world -X 10mm", "world +Y 10mm", "world -Y 10mm",
           "world +Z 10mm", "world -Z 10mm", "world Z -10deg", "world Z +10deg",
           "hold pose and grip", "close grip; hold pose", "open grip; hold pose"]
ENGLISH = ["move in positive X", "move in negative X", "move in positive Y", "move in negative Y",
           "move upward in positive Z", "move downward in negative Z", "rotate clockwise",
           "rotate counterclockwise", "stay still", "close gripper", "open gripper"]
OBJECTIVE = "Approach the target with one 10mm translation. Keep grip unchanged. Stop if already there."
CONDITIONS = ("coordinates", "delta", "spatial", "spatial_english", "spatial_neutral")


def expected(delta):
    """Nominal arithmetic label; never a physics prediction or model feature."""
    d = np.asarray(delta, dtype=float)
    if d.shape != (3,) or not np.isfinite(d).all():
        raise ValueError("finite XYZ displacement required")
    scores = {t: float(np.linalg.norm(d - .01 * np.asarray(v))) for t, v in MOVE.items()}
    best = min(scores.values())
    if best >= float(np.linalg.norm(d)) - 1e-12:
        return ["STOP"]
    return [t for t, value in scores.items() if abs(value - best) < 1e-12]


def spatial(delta):
    clauses = [f"{abs(x)*1000:g} mm in {'positive' if x > 0 else 'negative'} {axis}"
               for axis, x in zip("XYZ", delta) if x]
    return ("The target is " + ", ".join(clauses) + " relative to the tool."
            if clauses else "The target and tool are at the same position.")


def fixture(state, instruction, criteria, *, condition, sample, answer, source=None, mapping=None):
    mapping = mapping or {t: t for t in criteria}
    result = {"condition": condition, "sample": sample, "source": source,
              "state": state, "questions": {"action": {"type": "choice", "instructions": instruction,
                                                        "criteria": criteria}},
              "option_order": list(criteria), "option_to_canonical": mapping,
              "diagnostic_reference_not_model_input": {"scored_expected_tokens": answer},
              "effects_supplied": False}
    result["payload_id"] = payload_id(state, result["questions"])
    result["fixture_id"] = _sha256_json(result)
    return result


def geometry_fixture(delta, condition, sample, *, reverse=False, neutral=False, source=None):
    delta = np.asarray(delta, dtype=float)
    if condition == "coordinates":
        tcp = np.array([.21, -.13, .95])
        state = {"tool_xyz_m": tcp.tolist(), "target_xyz_m": (tcp + delta).tolist()}
    elif condition == "delta":
        state = {"target_minus_tool_xyz_m": delta.tolist()}
    elif condition in {"spatial", "spatial_english", "spatial_neutral"}:
        state = spatial(delta)
    else:
        raise ValueError("unknown geometry condition")
    descriptions = ENGLISH if condition in {"spatial_english", "spatial_neutral"} else COMPACT
    neutral = neutral or condition == "spatial_neutral"
    mapping = {f"A{i:02d}" if neutral else t: t for i, t in enumerate(TOKENS)}
    criteria = dict(zip(mapping, descriptions))
    if reverse:
        criteria = dict(reversed(list(criteria.items())))
    return fixture(state, OBJECTIVE, criteria, condition=condition, sample=sample,
                   answer=expected(delta), mapping=mapping, source=source)


def discovery():
    result = []
    for t, direction in MOVE.items():
        result.append(fixture(f"Request: {ENGLISH[TOKENS.index(t)]}.",
                      "Which command matches the request?", dict(zip(TOKENS, COMPACT)),
                      condition="request", sample=t, answer=[t]))
    for sample, delta in [(t, .03*np.asarray(d)) for t, d in MOVE.items()] + [("zero", np.zeros(3))]:
        result.extend(geometry_fixture(delta, c, sample) for c in CONDITIONS)
    return result


def transform(f, condition, *, reverse=False, shift=0, instruction=None, answer=None):
    """Presentation-only alternative; remap through physical identity, not index."""
    criteria = f["questions"]["action"]["criteria"]
    keys = list(criteria)
    renamed = {k: keys[(i+shift) % len(keys)] for i, k in enumerate(keys)}
    entries = [(renamed[k], criteria[k]) for k in keys]
    if reverse:
        entries.reverse()
    return fixture(deepcopy(f["state"]), instruction or f["questions"]["action"]["instructions"],
                   dict(entries), condition=condition, sample=f["sample"], source=f["source"],
                   answer=answer if answer is not None else f["diagnostic_reference_not_model_input"]["scored_expected_tokens"],
                   mapping={renamed[k]: f["option_to_canonical"][k] for k in keys})


def validation(pilot_root):
    result = []
    axes = [(f"{t}_{size:g}mm", size/1000*np.asarray(d)) for size in (12., 65.) for t, d in MOVE.items()]
    axes += [("zero", np.zeros(3))]
    mixed = [(f"mixed_{axis}_{sign}", sign*np.roll([.065, .012, -.021], axis))
             for axis in range(3) for sign in (1, -1)]
    for sample, delta in axes + mixed:
        f = geometry_fixture(delta, "spatial_neutral", sample)
        result.extend([transform(f, "holdout_spatial"), transform(f, "holdout_reversed", reverse=True),
                       transform(f, "holdout_alias_shift", shift=4)])
    for sample, delta in axes:
        for condition in ("coordinates", "delta"):
            f = geometry_fixture(delta, condition, sample, neutral=True)
            # Candidate text is matched to the selected sentence presentation.
            result.append(fixture(f["state"], OBJECTIVE, dict(zip(f["option_order"], ENGLISH)),
                          condition="holdout_"+condition, sample=sample,
                          answer=expected(delta), mapping=f["option_to_canonical"]))
    for token, direction in MOVE.items():
        delta = .065*np.asarray(direction)
        f = geometry_fixture(delta, "spatial_neutral", f"away_{token}")
        for label, reverse, shift in (("away", False, 0), ("away_reversed", True, 0), ("away_alias_shift", False, 4)):
            result.append(transform(f, label, reverse=reverse, shift=shift,
                          instruction="Move away from the target with one 10mm translation. Keep grip unchanged.",
                          answer=expected(-delta)))
    for init in range(3):
        path = Path(pilot_root) / f"init{init}-raycast-v02" / "episodes.jsonl"
        rows, errors = load_records(path)
        if errors or not any(r["kind"] == "termination" and r["data"].get("reason") == "collection_smoke_complete" for r in rows):
            raise ValueError("accepted complete paired source required")
        for row in rows:
            if row["kind"] != "paired_state":
                continue
            pair = row["data"]
            oracle, perceptual = paired_inputs(pair)
            for branch, inp in (("oracle", oracle), ("perceptual", perceptual)):
                delta = inp.provider_input()["state"]["relations.tcp_target_delta_m"]
                if delta is None:
                    raise ValueError("selected projection requires available geometry")
                f = geometry_fixture(delta, "spatial_neutral", f"init{init}_step{pair['physical']['environment_step']}",
                                     source={"pair_id": pair["pair_id"], "physical": pair["physical"],
                                             "source_sha256": file_hash(path), "branch": branch,
                                             "projection": "relative XYZ only; no history, progress, contact, quality or effects"})
                result.append(transform(f, "archived_"+branch))
    return result


def completion_fixture(qpos, goal, presentation, sample, *, source=None, reverse=False):
    if goal not in {"open", "close"} or not np.isfinite(qpos):
        raise ValueError("known goal and finite joint position required")
    observed = "open" if qpos < -.14 else "closed" if qpos > 0 else "partly open"
    achieved = qpos < -.14 if goal == "open" else qpos > 0
    if presentation == "numeric":
        state = {"drawer_joint_position_m": qpos}
        definition = "Open means joint position below -0.14m; closed means above 0m. "
    elif presentation == "categorical":
        state = f"The drawer is {observed}."
        definition = ""
    else:
        raise ValueError("unknown completion presentation")
    criteria = {"A": "DONE: requested goal achieved", "B": "CONTINUE: requested goal not achieved"}
    if reverse:
        criteria = dict(reversed(list(criteria.items())))
    return fixture(state, f"Goal: {goal} the drawer. {definition}Is the requested goal achieved?", criteria,
                   condition="completion_"+presentation+("_reversed" if reverse else ""),
                   sample=sample+"_goal_"+goal, answer=["DONE" if achieved else "CONTINUE"],
                   source=source, mapping={"A": "DONE", "B": "CONTINUE"})


def final_diagnostic(pilot_root):
    result = []
    for qpos in (-.15, -.08, .002):
        for goal in ("open", "close"):
            for presentation in ("numeric", "categorical"):
                for reverse in (False, True):
                    result.append(completion_fixture(qpos, goal, presentation, f"synthetic_{qpos}", reverse=reverse))
    for init in range(3):
        path = Path(pilot_root) / f"init{init}-raycast-v02" / "episodes.jsonl"
        rows, errors = load_records(path)
        if errors or not any(r["kind"] == "termination" for r in rows):
            raise ValueError("complete source required")
        current = {r["data"]["physical_state_id"]: r["data"]["before"]
                   for r in rows if r["kind"] == "reference_evaluator"}
        for row in rows:
            if row["kind"] != "paired_state":
                continue
            pair = row["data"]
            oracle, _ = paired_inputs(pair)
            physical = pair["physical"]
            # Only before-state measurement is read; future probe outcomes excluded.
            before = current[physical["physical_state_id"]]
            source = {"physical": physical, "source_sha256": file_hash(path),
                      "current_state_field": "before.qpos_m", "privileged": True}
            sample = f"init{init}_step{physical['environment_step']}"
            for goal in ("open", "close"):
                for presentation in ("numeric", "categorical"):
                    f = completion_fixture(before["qpos_m"], goal, presentation, sample, source=source)
                    result.append(transform(f, "archived_"+f["condition"]))
            delta = oracle.provider_input()["state"]["relations.tcp_target_delta_m"]
            result.extend(rubric_fixtures(delta, sample, source))
    mixed = [(f"mixed_{axis}_{sign}", sign*np.roll([.065, .012, -.021], axis))
             for axis in range(3) for sign in (1, -1)] + [("zero", np.zeros(3))]
    for sample, delta in mixed:
        result.extend(rubric_fixtures(delta, sample))
    return result


def rubric_fixtures(delta, sample, source=None):
    descriptions = ["positive X error largest", "negative X error largest", "positive Y error largest",
                    "negative Y error largest", "positive Z error largest", "negative Z error largest",
                    "rotation requested clockwise", "rotation requested counterclockwise", "no separation",
                    "grip closing requested", "grip opening requested"]
    f = geometry_fixture(delta, "spatial_neutral", sample, source=source)
    result = []
    for ranked in (False, True):
        if ranked:
            # Explicit answer-equivalent upper bound, NOT a proposed state interface.
            axis = int(np.argmax(np.abs(delta)))
            largest = np.zeros(3)
            largest[axis] = delta[axis]
            state = spatial(largest)
        else:
            state = f["state"]
        condition = "policy_rubric_ranked" if ranked else "policy_rubric_unranked"
        result.append(fixture(state, "Choose the command matching the largest separation. Keep grip unchanged.",
                      dict(zip(f["option_order"], descriptions)), condition=condition, sample=sample,
                      answer=expected(delta), mapping=f["option_to_canonical"],
                      source={"parent": source, "handwritten_policy_in_criteria": True,
                              "answer_equivalent_projection": ranked}))
    return result


def goal_state_fixture(observed, desired, presentation):
    if observed not in {"open", "partly open", "closed"} or desired not in {"open", "closed"}:
        raise ValueError("known articulation and requested state required")
    if presentation not in {"structured", "sentence"}:
        raise ValueError("unknown goal presentation")
    state = ({"observed_drawer_state": observed, "desired_drawer_state": desired}
             if presentation == "structured" else
             f"The drawer is currently {observed}. The requested state is {desired}.")
    return fixture(state, "Does the observed drawer state satisfy the requested goal?",
                   {"A": "DONE: goal satisfied", "B": "CONTINUE: goal not satisfied"},
                   condition="state_goal_"+presentation, sample=observed+"_to_"+desired,
                   answer=["DONE" if observed == desired else "CONTINUE"],
                   mapping={"A": "DONE", "B": "CONTINUE"})


def goal_placement():
    result = []
    for observed in ("open", "partly open", "closed"):
        for desired in ("open", "closed"):
            for presentation in ("structured", "sentence"):
                f = goal_state_fixture(observed, desired, presentation)
                result.extend([f, transform(f, f["condition"]+"_reversed", reverse=True)])
    for token, direction in MOVE.items():
        for goal in ("toward", "away"):
            delta = .065*np.asarray(direction)
            f = geometry_fixture(delta, "spatial_neutral", f"{token}_{goal}")
            result.append(fixture(f"Goal: move {goal} the target. " + f["state"],
                                  "Choose one 10mm translation for the goal. Keep grip unchanged.",
                                  f["questions"]["action"]["criteria"], condition="state_goal_motion",
                                  sample=f["sample"], answer=expected(delta if goal == "toward" else -delta),
                                  mapping=f["option_to_canonical"]))
            result.append(transform(result[-1], "state_goal_motion_reversed", reverse=True))
    return result


def execute(fixtures, args):
    config = {"version": VERSION, "suite": args.suite, "repeats": args.repeats, "seed": args.seed,
              "fixture_ids": [f["fixture_id"] for f in fixtures], "no_execution": True,
              "effects": "none", "not_formal_e0": True}
    recorder = RunRecorder(args.output, config, {"run_id": Path(args.output).name,
                           "code": code_identity(), "versions": versions()})
    try:
        for f in fixtures:
            recorder.record("search_fixture", f)
        if not Path(args.laya_path).is_dir():
            raise ValueError("existing local checkpoint required")
        import torch
        random.seed(args.seed)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        recorder.manifest_update({"model": model_identity(args.laya_path)})
        agent = load_laya_provider(args.laya_path, subfolder=None, device=args.device).agent
        recorder.record("model_loaded", {"config": agent.cfg, "device": str(agent.device), "dtype": str(agent.dtype)})
        for repeat in range(args.repeats):
            for ordinal, f in enumerate(fixtures if repeat % 2 == 0 else list(reversed(fixtures))):
                run_call(agent, f, recorder, repeat=repeat, ordinal=ordinal)
        recorder.record("termination", {"reason": "interface_search_complete",
                                         "calls": len(fixtures)*args.repeats})
    except BaseException as exc:
        recorder.record("failure", {"exception": repr(exc)})
        raise
    finally:
        recorder.close()


def summarize(path):
    path = Path(path)
    path = path / "episodes.jsonl" if path.is_dir() else path
    rows, errors = load_records(path)
    fixtures, intents, calls, failures = {}, {}, [], []
    completed = set()
    terminated, planned, terminal_count = False, None, None
    for row in rows:
        d = row["data"]
        if row["kind"] == "run_start":
            planned = d["resolved_config"]
        elif row["kind"] == "search_fixture":
            original = deepcopy(d)
            fid = original.pop("fixture_id")
            if fid != _sha256_json(original) or fid in fixtures:
                raise ValueError("invalid or duplicate fixture")
            d["questions"]["action"]["criteria"] = {k: d["questions"]["action"]["criteria"][k]
                                                      for k in d["option_order"]}
            if payload_id(d["state"], d["questions"]) != d["payload_id"]:
                raise ValueError("invalid payload")
            fixtures[fid] = d
        elif row["kind"] == "model_call_intent":
            if d["call_id"] in intents or d["fixture_id"] not in fixtures:
                raise ValueError("orphan or duplicate intent")
            f = fixtures[d["fixture_id"]]
            if d["payload_id"] != f["payload_id"] or d["input_encoding"]["truncated"]:
                raise ValueError("invalid intent input")
            if d["call_id"] != _sha256_json({"fixture_id": d["fixture_id"], "repeat": d["repeat"], "ordinal": d["ordinal"]}):
                raise ValueError("invalid call identity")
            intents[d["call_id"]] = d
        elif row["kind"] == "model_raw_response":
            cid = d["call_id"]
            if cid not in intents or cid in completed:
                raise ValueError("orphan or duplicate response")
            intent = intents[cid]
            f = fixtures[intent["fixture_id"]]
            a = d["raw_response"]["answers"]["action"]
            mapping = f["option_to_canonical"]
            if set(a["probabilities"]) != set(mapping):
                raise ValueError("incomplete distribution")
            probs = np.asarray(list(a["probabilities"].values()), dtype=float)
            if not np.isfinite(probs).all() or (probs < 0).any() or abs(probs.sum()-1.) > .0006:
                raise ValueError("invalid distribution")
            trace = d["forward_traces"][-1]
            audit = intent["input_encoding"]["questions"]["action"]
            if trace["input_ids"] != [audit["effective_input_ids"]] or trace["option_markers"] != [audit["option_markers"]]:
                raise ValueError("consumed tokens differ")
            if d["actual_device"] != intent["device_before"] or d["actual_dtype"] != intent["dtype_before"]:
                raise ValueError("inference device or dtype changed")
            logits = np.asarray(trace["raw_option_logits"])
            if logits.shape != (1, len(mapping)) or not np.isfinite(logits).all():
                raise ValueError("invalid raw logits")
            if a["choice"] != f["option_order"][int(logits[0].argmax())]:
                raise ValueError("choice does not match scorer output")
            scaled = logits[0] / intent["temperature"]["effective"]
            predicted = np.exp(scaled-scaled.max())
            predicted /= predicted.sum()
            ordered_probabilities = np.array([a["probabilities"][k] for k in f["option_order"]])
            if np.max(np.abs(predicted-ordered_probabilities)) > .00006:
                raise ValueError("probabilities do not match calibrated scorer output")
            choice = mapping[a["choice"]]
            p = {mapping[k]: v for k, v in a["probabilities"].items()}
            expected_tokens = f["diagnostic_reference_not_model_input"]["scored_expected_tokens"]
            calls.append({"fixture_id": f["fixture_id"], "condition": f["condition"], "sample": f["sample"],
                          "repeat": intent["repeat"], "choice": choice, "probabilities": p,
                          "correct": choice in expected_tokens if expected_tokens is not None else None,
                          "expected": expected_tokens, "state_tokens": audit["state_tokens"],
                          "total_tokens": audit["effective_token_count"], "raw_logits": trace["raw_option_logits"],
                          "temperature": intent["temperature"], "device": d["actual_device"],
                          "dtype": d["actual_dtype"], "latency_ms": d["latency_ms"]})
            completed.add(cid)
        elif row["kind"] == "failure":
            failures.append(d)
        elif row["kind"] == "termination":
            terminated = d.get("reason") == "interface_search_complete"
            terminal_count = d.get("calls")
    groups = {}
    for call in calls:
        if call["repeat"] == 0:
            group = groups.setdefault(call["condition"], {"correct": 0, "scored": 0, "calls": 0})
            group["calls"] += 1
            group["correct"] += call["correct"] is True
            group["scored"] += call["correct"] is not None
    expected_calls = (len(planned["fixture_ids"])*planned["repeats"]) if planned else None
    actual_keys = [(c["fixture_id"], c["repeat"]) for c in calls]
    planned_keys = {(fid, rep) for fid in planned["fixture_ids"] for rep in range(planned["repeats"])} if planned else set()
    coverage = (set(fixtures) == set(planned["fixture_ids"]) and set(actual_keys) == planned_keys
                and len(actual_keys) == len(set(actual_keys)) and terminal_count == expected_calls) if planned else False
    repeats = []
    for fid in fixtures:
        matched = [c for c in calls if c["fixture_id"] == fid]
        for c in matched[1:]:
            first = matched[0]
            repeats.append({"fixture_id": fid, "choice_equal": first["choice"] == c["choice"],
                            "probabilities_equal": first["probabilities"] == c["probabilities"],
                            "raw_logits_equal": first["raw_logits"] == c["raw_logits"]})
    return {"raw_sha256": file_hash(path), "groups_first_repeat": groups, "calls": calls,
            "repeat_comparisons": repeats, "planned_coverage_complete": coverage,
            "failures": failures, "record_diagnostics": errors,
            "unmatched_intents": sorted(set(intents)-completed),
            "complete": terminated and coverage and bool(calls) and not errors and not failures and set(intents) == completed}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--suite", default="discovery", choices=["discovery", "validation", "final", "goal-placement"])
    p.add_argument("--pilot-root", default="runs/reference-pilot")
    p.add_argument("--output")
    p.add_argument("--summarize")
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--device", default="cuda")
    p.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    args = p.parse_args()
    if args.summarize:
        print(json.dumps(summarize(args.summarize), indent=2))
    elif args.output and args.repeats > 0:
        fixtures = {"discovery": discovery, "validation": lambda: validation(args.pilot_root),
                    "final": lambda: final_diagnostic(args.pilot_root), "goal-placement": goal_placement}[args.suite]()
        execute(fixtures, args)
    else:
        p.error("new output and positive repeats required")


if __name__ == "__main__":
    main()
