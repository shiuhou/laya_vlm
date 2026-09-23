"""Fixed-eleven-option, privileged offline consequence diagnostic. No execution."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from .interface_search import COMPACT, TOKENS, execute, fixture, summarize
from .records import file_hash, load_records
from .reference_gate import physical_assessment, physical_fixtures

VERSION = "effect-binding-v0.1"
TOLERANCE_MM = .25
QUESTION = "Choose an intervention for the requested goal."
PROTOCOL = Path(__file__).resolve().parents[2] / "docs/evidence/decision_interface/effect_binding_protocol.md"


def category(value, negative, positive, zero):
    if value is None or not np.isfinite(value):
        raise ValueError("finite measured effect required; unknown cannot become zero")
    return negative if value < -TOLERANCE_MM else positive if value > TOLERANCE_MM else zero


def effect_facts(source):
    """Goal-independent facts; no preferred action or utility computation."""
    effects = source["oracle_effects_not_model_input_as_numeric_table"]
    if set(effects) != set(TOKENS):
        raise ValueError("all eleven physical effects required")
    if any(e["opening_change_mm"] is None or not np.isfinite(e["opening_change_mm"])
           for e in effects.values()):
        raise ValueError("finite measured effect required; unknown cannot become zero")
    stop = effects["STOP"]["opening_change_mm"]
    result = {}
    for token in TOKENS:
        effect = effects[token]
        if not isinstance(effect["obstacle"], bool):
            raise ValueError("known measured obstacle flag required")
        delta = effect["opening_change_mm"]
        result[token] = {
            "opening": category(delta, "decreases", "increases", "unchanged"),
            "vs_stop": category(delta - stop, "lower", "higher", "same"),
            "obstacle": effect["obstacle"],
        }
    return result


def presented_support(source, token):
    """Evaluator only: test exactly the supplied facts, separately from reality."""
    facts = effect_facts(source)[source["effect_assignment"][token]]
    closed = source["goal"] == "closed"
    absolute = facts["opening"] == ("decreases" if closed else "increases")
    relative = facts["vs_stop"] == ("lower" if closed else "higher")
    return not facts["obstacle"] and absolute and (source["effect_detail"] == "absolute" or relative)


def binding_fixture(base, *, descriptions, detail, assignment, goal, reverse):
    if (descriptions not in {"native", "anonymous"} or detail not in {"absolute", "relative"}
            or assignment not in {"true", "shift4"} or goal not in {"closed", "open"}):
        raise ValueError("unknown factorial level")
    source = deepcopy(base["source"])
    source.update({"diagnostic_version": VERSION, "descriptions": descriptions,
                   "effect_detail": detail, "assignment": assignment, "goal": goal,
                   "reverse": reverse, "effect_mode": "true" if assignment == "true" else "misassigned",
                   "effect_assignment": {t: TOKENS[(i + (4 if assignment == "shift4" else 0)) % len(TOKENS)]
                                         for i, t in enumerate(TOKENS)},
                   "protocol_sha256": file_hash(PROTOCOL),
                   "not_perceptual_or_deployable": True})
    facts = effect_facts(source)
    # Keep the same observed articulation, including under counterfactual goals.
    observed = base["state"].split(". The requested state is ")[0]
    state = (f"{observed}. The requested state is {goal}. "
             "Nominal moves are intents. Stated outcomes cover 0.4 seconds. "
             "Opening change is relative to entry; vs STOP compares final opening to the STOP endpoint. "
             "Same or unchanged means within 0.25 mm. Obstacle means new or endpoint obstacle contact. "
             "Avoid obstacle contact. Decrease opening for closed; increase it for open. "
             "When a STOP comparison is supplied, also require lower opening than STOP for closed, "
             "or higher opening than STOP for open.")
    criteria = {}
    for i, token in enumerate(TOKENS):
        fact = facts[source["effect_assignment"][token]]
        text = COMPACT[i] if descriptions == "native" else "intervention"
        text += f"; opening {fact['opening']}"
        if detail == "relative":
            text += f"; vs STOP {fact['vs_stop']}"
        text += f"; obstacle {'yes' if fact['obstacle'] else 'no'}"
        criteria[f"A{i:02d}"] = text
    if reverse:
        criteria = dict(reversed(list(criteria.items())))
    expected = [t for t in TOKENS if presented_support(source, t)]
    if not expected:
        raise ValueError("diagnostic requires a supported presented choice")
    if detail == "relative" and assignment == "true":
        actual = [t for t in TOKENS if physical_assessment(source, t)["local_support"]]
        if expected != actual:
            raise AssertionError("complete factual abstraction disagrees with physical utility")
    physical = source["physical"]
    return fixture(state, QUESTION, criteria,
                   condition=f"{descriptions}_{detail}_{assignment}",
                   sample=f"init{physical['init_state_id']}_step{physical['environment_step']}_goal_{goal}_reverse_{int(reverse)}",
                   answer=expected, source=source, effects_supplied=True,
                   mapping={f"A{i:02d}": t for i, t in enumerate(TOKENS)})


def fixtures(root):
    # The prior loader verifies accepted sources, pair identity, full native sets,
    # equal horizons and restoration; it derives effects from raw probe endpoints.
    bases = [f for f in physical_fixtures(root)
             if f["condition"] == "physical_true" and f["source"]["goal"] == "closed"]
    if len(bases) != 4:
        raise ValueError("exactly the four predeclared physical contexts required")
    return [binding_fixture(base, descriptions=names, detail=detail, assignment=assignment,
                            goal=goal, reverse=reverse)
            for base in bases for names in ("native", "anonymous")
            for detail in ("absolute", "relative") for assignment in ("true", "shift4")
            for goal in ("closed", "open") for reverse in (False, True)]


def report(path):
    result = summarize(path)  # validates actual consumed tokens, logits and coverage
    path = Path(path)
    path = path / "episodes.jsonl" if path.is_dir() else path
    rows, _ = load_records(path)
    fs = {r["data"]["fixture_id"]: r["data"] for r in rows if r["kind"] == "search_fixture"}
    groups, orders, assessed = {}, {}, []
    for call in result["calls"]:
        f = fs[call["fixture_id"]]
        source = f["source"]
        expected = [t for t in TOKENS if presented_support(source, t)]
        if expected != f["diagnostic_reference_not_model_input"]["scored_expected_tokens"]:
            raise ValueError("cached label disagrees with supplied factual reference")
        physical = physical_assessment(source, call["choice"])
        row = {"fixture_id": call["fixture_id"], "sample": call["sample"],
               "condition": call["condition"], "repeat": call["repeat"], "choice": call["choice"],
               "presented_fact_consistent": call["choice"] in expected,
               "presented_supported_set": expected, **physical,
               "presented_facts": effect_facts(source)[source["effect_assignment"][call["choice"]]]}
        assessed.append(row)
        if call["repeat"] != 0:
            continue
        for table, key in ((groups, call["condition"]),
                           (orders, call["condition"] + ("_reversed" if source["reverse"] else "_original"))):
            g = table.setdefault(key, {"calls": 0, "presented_fact_consistent": 0,
                                      "actual_local_support": 0, "contract_flagged": 0})
            g["calls"] += 1
            g["presented_fact_consistent"] += row["presented_fact_consistent"]
            g["actual_local_support"] += physical["local_support"]
            g["contract_flagged"] += physical["contract_flag"] is True
    stable = bool(result["repeat_comparisons"]) and all(
        c["choice_equal"] and c["probabilities_equal"] and c["raw_logits_equal"]
        for c in result["repeat_comparisons"])
    # Exact design coverage, not merely a termination or a score from a subset.
    factors = {(f["source"]["physical"]["init_state_id"], f["source"]["physical"]["environment_step"],
                f["source"]["descriptions"], f["source"]["effect_detail"], f["source"]["assignment"],
                f["source"]["goal"], f["source"]["reverse"]) for f in fs.values()}
    planned = {(init, step, names, detail, assign, goal, rev)
               for init, step in ((0, 48), (1, 48), (2, 48), (0, 140))
               for names in ("native", "anonymous") for detail in ("absolute", "relative")
               for assign in ("true", "shift4") for goal in ("closed", "open") for rev in (False, True)}
    design_complete = factors == planned and len(fs) == 128 and len(assessed) == 256 and {
        c["repeat"] for c in assessed} == {0, 1}
    gate_calls = [c for c in assessed if c["condition"].startswith("native_relative_")]
    gate = (result["complete"] and design_complete and stable and len(gate_calls) == 64
            and all(c["presented_fact_consistent"] for c in gate_calls)
            and all(c["local_support"] for c in gate_calls if c["condition"] == "native_relative_true"))
    return {**result, "factorial_complete": design_complete, "all_repeats_stable": stable,
            "binding_groups_first_repeat": groups, "order_groups_first_repeat": orders,
            "assessments": assessed, "native_full_effect_local_gate_passed": gate,
            "formal_e0_ready": False,
            "scope": "privileged finite local effect-use diagnostic; no no-effect reference qualification"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot-root", default="../laya-embodied-runtime/runs/reference-pilot")
    p.add_argument("--output")
    p.add_argument("--summarize")
    p.add_argument("--device", default="cuda")
    p.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    args = p.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif args.output:
        args.suite, args.seed, args.repeats = VERSION, 1, 2
        execute(fixtures(args.pilot_root), args)
    else:
        p.error("fresh output or existing run to summarize required")


if __name__ == "__main__":
    main()
