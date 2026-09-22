"""Regenerate smoke decision-equivalence evidence from raw, hash-checked records.

Reported comparisons are diagnostics, not independent samples or statistical
claims. Saved ``equivalence_diagnostic`` rows are deliberately not trusted.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from ..runtime_core import Decision, _sha256_json
from .equivalence import compare_decisions, distribution, field_differences, paired_inputs
from .records import load_records

BRANCHES = ("oracle", "perceptual")
PROVIDERS = {"rule": ("RuleProvider",), "laya": ("LayaProvider",), "both": ("RuleProvider", "LayaProvider")}
CSV_FIELDS = [
    "pair_id", "provider", "repeat", "status", "missing_branches", "task", "init_state_id", "seed",
    "physical_state_id", "sim_time", "variant", "candidate_set_id", "shared_candidate_count",
    "natural_perceptual_candidate_count", "natural_perceptual_feasible_count",
    "natural_oracle_candidate_count", "natural_oracle_feasible_count", "natural_candidate_set_agreement",
    "perceptual_geometry_age_s", "oracle_geometry_age_s", "position_comparison_status", "position_error_m",
    "oracle_choice", "perceptual_choice", "oracle_choice_allowed", "perceptual_choice_allowed",
    "oracle_latency_ms", "perceptual_latency_ms", "top1_agreement", "top2_set_agreement",
    "top2_boundary_tie", "js_divergence_nats", "oracle_margin",
]


def _pair_evidence(pair, inputs):
    oracle, perceptual = inputs
    if (oracle.state.meta.get("branch") != "oracle" or perceptual.state.meta.get("branch") != "perceptual"
            or not oracle.state.privileged or perceptual.state.privileged):
        raise ValueError("pair branch identity mismatch")
    physical = pair["physical"]
    if oracle.asof_sim_time != perceptual.asof_sim_time or physical["sim_time"] != perceptual.asof_sim_time:
        raise ValueError("pair physical boundary mismatch")
    natural_p, natural_o = pair["natural_perceptual_candidates"], pair["natural_oracle_candidates"]
    for candidates in (natural_p, natural_o):
        if candidates is not None and len({c["token"] for c in candidates}) != len(candidates):
            raise ValueError("duplicate natural candidate identity")
    agreement = None if natural_o is None else (
        {c["token"] for c in natural_p if c["feasible"]} == {c["token"] for c in natural_o if c["feasible"]})
    differences = field_differences(oracle.state, perceptual.state)
    position = differences["target.position_m"]
    row = {key: physical.get(key) for key in ("task", "init_state_id", "seed", "physical_state_id", "sim_time", "variant")}
    row.update({
        "pair_id": pair["pair_id"], "candidate_set_id": pair["candidate_set_id"],
        "shared_candidate_count": len(oracle.candidates),
        "natural_perceptual_candidate_count": len(natural_p),
        "natural_perceptual_feasible_count": sum(c["feasible"] for c in natural_p),
        "natural_oracle_candidate_count": None if natural_o is None else len(natural_o),
        "natural_oracle_feasible_count": None if natural_o is None else sum(c["feasible"] for c in natural_o),
        "natural_candidate_set_agreement": agreement,
        "perceptual_geometry_age_s": perceptual.state.fields["quality.geometry_age_s"].value,
        "oracle_geometry_age_s": oracle.state.fields["quality.geometry_age_s"].value,
        "position_comparison_status": position["status"], "position_error_m": position.get("difference_l2"),
    })
    return row, differences


def _validate_decision(data, inputs):
    if data["branch"] not in BRANCHES:
        raise ValueError("unknown decision branch")
    if type(data["repeat"]) is not int or data["repeat"] < 0:
        raise ValueError("invalid repeat index")
    inp = inputs[BRANCHES.index(data["branch"])]
    decision = Decision(**data["decision"])
    expected = (inp.snapshot_id(), inp.belief_id(), inp.candidate_set_id(), inp.revision, inp.asof_sim_time)
    actual = (decision.input_snapshot_id, decision.input_belief_id, decision.candidate_set_id,
              decision.input_revision, decision.input_sim_time)
    if actual != expected:
        raise ValueError("decision input identity mismatch")
    payload = {"state": inp.provider_input(), "question": inp.questions()}
    if data["model_input_id"] != _sha256_json(payload):
        raise ValueError("model input identity mismatch")
    if type(data["choice_allowed"]) is not bool or data["choice_allowed"] != (decision.token in inp.allowed()):
        raise ValueError("choice allowance mismatch")
    if not np.isfinite(data["latency_ms"]) or data["latency_ms"] < 0:
        raise ValueError("invalid decision latency")
    return decision


def summarize_equivalence(output):
    """Write deterministic CSV/JSON, preserving missing output as incomplete.

    Invalid complete evidence fails validation. Interrupted trailing records are
    reported by ``load_records``; absent outputs never become model decisions.
    """
    output = Path(output)
    records, diagnostics = load_records(output / "episodes.jsonl")
    pairs, decisions, inputs, config, terminations = {}, {}, {}, {}, []
    for record in records:
        kind, data = record["kind"], record["data"]
        if kind == "run_start":
            config = data["resolved_config"]
        elif kind == "paired_state":
            if data["pair_id"] in pairs:
                raise ValueError("duplicate paired-state observation")
            inputs[data["pair_id"]] = paired_inputs(data)
            pairs[data["pair_id"]] = data
        elif kind == "equivalence_decision":
            if data["pair_id"] not in inputs:
                raise ValueError("decision lacks preceding paired state")
            decision = _validate_decision(data, inputs[data["pair_id"]])
            key = (data["pair_id"], data["provider"], data["branch"], data["repeat"])
            if key in decisions:
                raise ValueError("duplicate decision observation")
            decisions[key] = (data, decision)
        elif kind == "failure":
            diagnostics.append({"category": data.get("category", "failure"), "detail": data})
        elif kind == "termination":
            terminations.append(data)
        # equivalence_diagnostic is a derived cache, never an analysis input.
    if not terminations:
        diagnostics.append({"category": "run_incomplete", "detail": "no terminal record"})
    expected_repeats = config.get("repeats")
    if expected_repeats is not None and (type(expected_repeats) is not int or expected_repeats < 1):
        raise ValueError("invalid configured repeat count")
    providers = set(PROVIDERS.get(config.get("provider"), ())) | {k[1] for k in decisions}
    if expected_repeats is not None and any(k[3] >= expected_repeats for k in decisions):
        raise ValueError("decision repeat exceeds resolved configuration")
    comparisons, pair_summaries, stability = [], [], []
    for pair_id, pair in pairs.items():
        pair_inputs = inputs[pair_id]
        metadata, differences = _pair_evidence(pair, pair_inputs)
        pair_summaries.append({**metadata, "field_differences": differences})
        tokens = sorted(pair_inputs[0].allowed())
        for provider in sorted(providers):
            observed = [k[3] for k in decisions if k[:2] == (pair_id, provider)]
            repeats = expected_repeats if expected_repeats is not None else max(observed, default=-1) + 1
            for repeat in range(repeats):
                selected = {branch: decisions.get((pair_id, provider, branch, repeat)) for branch in BRANCHES}
                missing = [branch for branch, value in selected.items() if value is None]
                row = {**dict.fromkeys(CSV_FIELDS), **metadata, "provider": provider, "repeat": repeat,
                       "status": "incomplete" if missing else "complete", "missing_branches": ",".join(missing)}
                for branch, item in selected.items():
                    if item is not None:
                        data, decision = item
                        row.update({f"{branch}_choice": decision.token, f"{branch}_choice_allowed": data["choice_allowed"],
                                    f"{branch}_latency_ms": data["latency_ms"]})
                if not missing:
                    row.update(compare_decisions(selected["oracle"][1], selected["perceptual"][1], tokens))
                comparisons.append(row)
            for branch in BRANCHES:
                samples = [decisions[(pair_id, provider, branch, i)] for i in range(repeats)
                           if (pair_id, provider, branch, i) in decisions]
                probs = [distribution(d, tokens) for _, d in samples]
                input_ids = {d["model_input_id"] for d, _ in samples}
                if len(input_ids) > 1:
                    raise ValueError("same-branch repeated model input changed")
                stability.append({"pair_id": pair_id, "provider": provider, "branch": branch,
                                  "observed_repeats": len(samples), "expected_repeats": expected_repeats,
                                  "complete": None if expected_repeats is None else len(samples) == expected_repeats,
                                  "repeatability_measured": len(samples) >= 2,
                                  "model_input_id": next(iter(input_ids), None),
                                  "unique_choices": sorted({d.token for _, d in samples}),
                                  "all_choices_allowed": all(d["choice_allowed"] for d, _ in samples) if samples else None,
                                  "max_probability_difference": None if len(samples) < 2 or any(p is None for p in probs)
                                  else float(np.max(np.ptp(np.stack(probs), axis=0)))})
    summary = {"version": "equivalence-summary-v0.1", "purpose": "descriptive_smoke_diagnostics_not_statistical_evidence",
               "terminated": bool(terminations), "terminations": terminations,
               "expected_repeats": expected_repeats, "pair_count": len(pairs), "decision_count": len(decisions),
               "complete_comparisons": sum(r["status"] == "complete" for r in comparisons),
               "incomplete_comparisons": sum(r["status"] == "incomplete" for r in comparisons),
               "diagnostics": diagnostics, "pairs": pair_summaries, "comparisons": comparisons, "stability": stability}
    with (output / "equivalence_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(comparisons)
    (output / "equivalence_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    args = parser.parse_args()
    result = summarize_equivalence(args.run_directory)
    print(json.dumps({k: result[k] for k in ("pair_count", "decision_count", "complete_comparisons", "incomplete_comparisons", "terminated")}))


if __name__ == "__main__":
    main()
