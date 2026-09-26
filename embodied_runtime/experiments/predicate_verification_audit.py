"""Independent raw-evidence audit for the offline predicate-verification diagnostic.

No experiment/scoring helpers are imported. Labels are reconstructed twice: from
preserved candidate text and from numeric effects, including the STOP comparison.
The only shared machinery is the append-only record reader and identity hashing.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

import numpy as np

from ..runtime_core import _sha256_json
from .records import file_hash, load_records

SOURCE_SHA256 = "d4e58fce0d961594090cf4124942e90cd6c044824951429d8ea8ee22e57acb0c"
VERSION = "predicate-verification-v0.1"
TOKENS = ("MV_FWD", "MV_BACK", "MV_LEFT", "MV_RIGHT", "MV_UP", "MV_DOWN",
          "ROTATE_CW", "ROTATE_CCW", "STOP", "GRASP", "RELEASE")
SUFFIX = re.compile(r".+; opening (decreases|increases|unchanged); vs STOP (lower|higher|same); obstacle (yes|no)")
ANSWERS = {"V0": "satisfies", "V1": "does_not_satisfy"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _payload(fixture):
    return _sha256_json({"state": fixture["state"], "questions": fixture["questions"],
                         "option_order": {"action": fixture["option_order"]}})


def _fixture_identity(fixture):
    _require(fixture["fixture_id"] == _sha256_json({k: v for k, v in fixture.items()
                                                  if k != "fixture_id"}), "fixture identity mismatch")
    _require(set(fixture["questions"]) == {"action"}, "unexpected model question")
    _require(set(fixture["option_order"]) == set(fixture["questions"]["action"]["criteria"])
             and len(fixture["option_order"]) == len(set(fixture["option_order"])), "option coverage mismatch")
    _require(fixture["payload_id"] == _payload(fixture), "model payload identity mismatch")


def independent_labels(parent):
    """Recompute presented and actual support without trusting stored labels."""
    source = parent["source"]
    effects = source["oracle_effects_not_model_input_as_numeric_table"]
    assignment = source["effect_assignment"]
    _require(set(effects) == set(TOKENS) == set(assignment)
             and set(assignment.values()) == set(TOKENS), "full effect permutation required")
    _require(source["goal"] in {"closed", "open"} and source["effect_detail"] == "relative",
             "full relative-effect goal required")
    _require(set(parent["option_to_canonical"].values()) == set(TOKENS)
             and len(parent["option_to_canonical"]) == 11, "eleven physical identities required")
    for effect in effects.values():
        _require(isinstance(effect["obstacle"], bool)
                 and isinstance(effect["opening_change_mm"], (int, float))
                 and not isinstance(effect["opening_change_mm"], bool)
                 and math.isfinite(effect["opening_change_mm"]), "finite physical effect required")
    closed = source["goal"] == "closed"
    direction = -1 if closed else 1
    stop = effects["STOP"]["opening_change_mm"]
    expected_instruction = ("Choose an intervention with opening "
                            + ("decreases, vs STOP lower" if closed else "increases, vs STOP higher")
                            + ", and obstacle no.")
    _require(parent["questions"]["action"]["instructions"] == expected_instruction,
             "parent goal instruction mismatch")
    result = {}
    for option, token in parent["option_to_canonical"].items():
        match = SUFFIX.fullmatch(parent["questions"]["action"]["criteria"][option])
        _require(match is not None, "unrecognized exact effect suffix")
        text = match.groups()
        effect = effects[assignment[token]]
        delta = effect["opening_change_mm"]
        relative = delta - stop
        numeric = ("decreases" if delta < -.25 else "increases" if delta > .25 else "unchanged",
                   "lower" if relative < -.25 else "higher" if relative > .25 else "same",
                   "yes" if effect["obstacle"] else "no")
        _require(text == numeric, "candidate text disagrees with assigned numeric effects")
        truth = (text[0] == ("decreases" if closed else "increases")
                 and text[1] == ("lower" if closed else "higher") and text[2] == "no")
        _require(truth == (direction * delta > .25 and direction * relative > .25
                           and not effect["obstacle"]), "independent predicate mismatch")
        actual = effects[token]
        physical = (direction * actual["opening_change_mm"] > .25
                    and direction * (actual["opening_change_mm"] - stop) > .25
                    and not actual["obstacle"])
        result[token] = {"presented_truth": truth, "physical_support": physical,
                         "assigned_effect_token": assignment[token]}
    expected = [t for t in TOKENS if result[t]["presented_truth"]]
    _require(parent["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == expected,
             "cached parent labels disagree")
    return result


def audit_binary(fixture, parent):
    """Exact payload reconstruction rejects label leakage and wording changes."""
    verification = fixture["verification"]
    token, option = verification["tested_token"], verification["tested_option"]
    _require(verification["version"] == VERSION
             and verification["parent_fixture_id"] == parent["fixture_id"]
             and verification["parent_payload_id"] == parent["payload_id"], "binary parent mismatch")
    _require(parent["source"]["reverse"] is False, "binary requires forward parent")
    _require(parent["option_to_canonical"].get(option) == token, "tested action identity mismatch")
    reverse = verification["answer_order_reversed"]
    _require(type(reverse) is bool, "answer order must be boolean")
    order = ["V1", "V0"] if reverse else ["V0", "V1"]
    question = {"action": {"type": "choice", "instructions":
                "Determine whether this candidate satisfies the stated criterion. Criterion: "
                + parent["questions"]["action"]["instructions"] + "\nCandidate: "
                + parent["questions"]["action"]["criteria"][option], "criteria": ANSWERS}}
    _require(fixture["state"] == parent["state"] and fixture["questions"] == question,
             "model payload changed or evaluator truth leaked")
    _require(fixture["source"] == parent["source"] and fixture["option_order"] == order
             and fixture["option_to_canonical"] == ANSWERS, "binary evidence/order mismatch")
    label = independent_labels(parent)[token]
    expected = "satisfies" if label["presented_truth"] else "does_not_satisfy"
    _require(fixture["diagnostic_reference_not_model_input"]["scored_expected_tokens"] == [expected],
             "cached binary truth disagrees")
    return {**label, "goal": parent["source"]["goal"], "tested_token": token,
            "parent_fixture_id": parent["fixture_id"], "answer_order_reversed": reverse,
            "assignment": parent["source"]["assignment"]}


def audit_response(fixture, intent, response, presentation):
    """Check actual forwarded tokens and raw logits; do not trust call analysis."""
    _require(intent["fixture_id"] == fixture["fixture_id"]
             and intent["payload_id"] == fixture["payload_id"], "call payload mismatch")
    _require(intent["input_encoding"] == presentation, "call differs from preflight presentation")
    audit = intent["input_encoding"]
    _require(audit.get("available") and not audit.get("truncated"), "missing/truncated token audit")
    encoding = audit["questions"]["action"]
    _require(not any(encoding[k] for k in ("state_truncated", "heading_truncated", "options_truncated")),
             "truncated presentation")
    _require(encoding["effective_input_id"] == _sha256_json(encoding["effective_input_ids"])
             and encoding["effective_token_count"] == len(encoding["effective_input_ids"]),
             "token identity/count mismatch")
    _require(response.get("forward_hook_active") and len(response["forward_traces"]) == 1,
             "exactly one observed forward required")
    trace = response["forward_traces"][0]
    order = fixture["option_order"]
    _require(trace["input_ids"] == [encoding["effective_input_ids"]]
             and trace["option_markers"] == [encoding["option_markers"]]
             and len(encoding["option_markers"]) == len(order), "consumed tokens/markers differ")
    _require(response["actual_device"] == intent["device_before"]
             and response["actual_dtype"] == intent["dtype_before"], "device/dtype drift")
    logits = np.asarray(trace["raw_option_logits"], dtype=float)
    _require(logits.shape == (1, len(order)) and np.isfinite(logits).all(), "raw logit cardinality/value mismatch")
    answer = response["raw_response"]["answers"]["action"]
    _require(set(answer["probabilities"]) == set(order), "probability cardinality mismatch")
    probs = np.asarray([answer["probabilities"][k] for k in order], dtype=float)
    _require(np.isfinite(probs).all() and (probs >= 0).all() and (probs <= 1).all()
             and abs(probs.sum() - 1) <= .0006, "invalid probability distribution")
    _require(answer["choice"] == order[int(logits[0].argmax())], "choice is not raw argmax")
    temperature = intent["temperature"]
    _require(temperature["bucket"] == ("choice:2" if len(order) == 2 else "choice:11+")
             and math.isfinite(temperature["effective"]) and temperature["effective"] > 0
             and temperature["effective"] == max(.001, temperature["configured"]), "temperature/cardinality mismatch")
    scaled = logits[0] / temperature["effective"]
    calculated = np.exp(scaled - scaled.max())
    calculated /= calculated.sum()
    _require(np.max(np.abs(calculated - probs)) <= .00006, "probabilities disagree with raw logits/temperature")
    usage = response["raw_response"].get("usage", {})
    _require(usage.get("input_tokens") == len(encoding["effective_input_ids"]), "provider consumed-token count mismatch")
    return {"fixture_id": fixture["fixture_id"], "repeat": intent["repeat"],
            "choice": fixture["option_to_canonical"][answer["choice"]],
            "probabilities": answer["probabilities"], "raw_logits": trace["raw_option_logits"],
            "temperature": temperature, "input_tokens": len(encoding["effective_input_ids"])}


def audit(output):
    output = Path(output)
    rows, diagnostics = load_records(output / "episodes.jsonl")
    config = rows[0]["data"]["resolved_config"]
    source = Path(config["source"]) / "episodes.jsonl"
    _require(file_hash(source) == SOURCE_SHA256, "frozen parent source hash mismatch")
    source_rows, source_errors = load_records(source)
    _require(not source_errors, "incomplete parent source")
    parents = {r["data"]["fixture_id"]: r["data"] for r in source_rows
               if r["kind"] == "search_fixture"
               and r["data"].get("intervention", {}).get("version") == "explicit-consequence-v0.1"}
    _require(len(parents) == 32, "exactly 32 archived controls required")
    fixtures, presentations, labels = {}, {}, {}
    for row in rows:
        d = row["data"]
        if row["kind"] == "search_fixture":
            _fixture_identity(d)
            fid = d["fixture_id"]
            _require(fid not in fixtures, "duplicate fixture")
            fixtures[fid] = d
            if "verification" in d:
                labels[fid] = audit_binary(d, parents[d["verification"]["parent_fixture_id"]])
            else:
                _require(fid in parents and d == parents[fid], "control changed from archive")
                independent_labels(d)
        elif row["kind"] == "provider_presentation":
            fid = d["fixture_id"]
            _require(fid not in presentations, "duplicate presentation")
            presentations[fid] = {k: v for k, v in d.items() if k != "fixture_id"}
    planned = {(p["fixture_id"], t, reverse) for p in parents.values() if p["source"]["reverse"] is False
               for t in TOKENS for reverse in (False, True)}
    actual = {(v["parent_fixture_id"], v["tested_token"], v["answer_order_reversed"]) for v in labels.values()}
    _require(len(fixtures) == 384 and len(labels) == 352 and actual == planned
             and set(fixtures) - set(labels) == set(parents), "32-control/352-binary design incomplete")
    _require(config["repeats"] == 2 and len(config["fixture_ids"]) == 384
             and set(config["fixture_ids"]) == set(fixtures), "declared design mismatch")
    _require(set(presentations) == set(fixtures), "presentation coverage incomplete")
    intents, responses, analyses, calls = {}, {}, set(), []
    failures = [r["data"] for r in rows if r["kind"] == "failure"]
    for row in rows:
        d, kind = row["data"], row["kind"]
        if kind == "model_call_intent":
            cid = d["call_id"]
            _require(cid not in intents and d["fixture_id"] in fixtures, "duplicate/orphan intent")
            _require(cid == _sha256_json({k: d[k] for k in ("fixture_id", "repeat", "ordinal")}), "call identity mismatch")
            _require(d["repeat"] in (0, 1) and 0 <= d["ordinal"] < 384, "call repeat/ordinal mismatch")
            traversal = config["fixture_ids"] if d["repeat"] == 0 else list(reversed(config["fixture_ids"]))
            _require(d["fixture_id"] == traversal[d["ordinal"]], "call traversal mismatch")
            intents[cid] = d
        elif kind == "model_raw_response":
            cid = d["call_id"]
            _require(cid in intents and cid not in responses, "duplicate/orphan raw response")
            responses[cid] = d
            intent = intents[cid]
            calls.append(audit_response(fixtures[intent["fixture_id"]], intent, d,
                                        presentations[intent["fixture_id"]]))
        elif kind == "model_call_analysis":
            _require(d["call_id"] in responses and d["call_id"] not in analyses, "duplicate/orphan call analysis")
            analyses.add(d["call_id"])
    expected_calls = {(fid, repeat) for fid in fixtures for repeat in (0, 1)}
    seen = [(c["fixture_id"], c["repeat"]) for c in calls]
    _require(len(seen) == len(set(seen)), "duplicate fixture/repeat response")
    terminal = [r["data"] for r in rows if r["kind"] == "termination"]
    complete = (set(seen) == expected_calls and len(calls) == 768 and not failures and not diagnostics
                and set(intents) == set(responses) == analyses
                and terminal == [{"reason": "predicate_verification_complete", "calls": 768}])
    confusion, by_order = {}, {}
    for call in calls:
        if call["fixture_id"] not in labels or call["repeat"] != 0:
            continue
        label = labels[call["fixture_id"]]
        actual_yes = call["choice"] == "satisfies"
        key = ("true_" if actual_yes == label["presented_truth"] else "false_") + ("positive" if actual_yes else "negative")
        for groups, group in ((confusion, label["goal"]),
                              (by_order, label["goal"] + ("_reversed" if label["answer_order_reversed"] else "_forward"))):
            counts = groups.setdefault(group, dict.fromkeys(("true_positive", "false_positive", "true_negative", "false_negative"), 0))
            counts[key] += 1
    indexed = {(c["fixture_id"], c["repeat"]): c for c in calls}
    archived_intents = {r["data"]["call_id"]: r["data"] for r in source_rows
                        if r["kind"] == "model_call_intent" and r["data"]["fixture_id"] in parents}
    controls = []
    for row in source_rows:
        if row["kind"] != "model_raw_response" or row["data"]["call_id"] not in archived_intents:
            continue
        old = row["data"]
        intent = archived_intents[old["call_id"]]
        key = (intent["fixture_id"], intent["repeat"])
        if key not in indexed:
            continue
        previous = audit_response(parents[key[0]], intent, old, intent["input_encoding"])
        current = indexed[key]
        controls.append({"fixture_id": key[0], "repeat": key[1],
                         **{field + "_equal": previous[field] == current[field]
                            for field in ("choice", "probabilities", "raw_logits")}})
    repeats = [{"fixture_id": fid, **{k + "_equal": indexed[(fid, 0)][k] == indexed[(fid, 1)][k]
                                     for k in ("choice", "probabilities", "raw_logits")}}
               for fid in fixtures if (fid, 0) in indexed and (fid, 1) in indexed]
    return {"raw_sha256": file_hash(output / "episodes.jsonl"), "complete": complete,
            "control_fixtures": len(parents), "binary_fixtures": len(labels), "calls": len(calls),
            "missing_calls": sorted(expected_calls - set(seen)), "failures": failures,
            "record_diagnostics": diagnostics, "per_goal_confusion_first_repeat": confusion,
            "answer_order_confusion_first_repeat": by_order, "repeat_comparisons": repeats,
            "all_repeats_stable": len(repeats) == 384 and all(all(v for k, v in r.items() if k.endswith("_equal")) for r in repeats),
            "archive_control_comparisons": controls,
            "archive_controls_reproduced": len(controls) == 64 and all(
                all(v for k, v in item.items() if k.endswith("_equal")) for item in controls),
            "labels": labels, "scope": "offline predicate verification; no execution, causal mechanism or calibration claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(audit(args.output), indent=2))


if __name__ == "__main__":
    main()
