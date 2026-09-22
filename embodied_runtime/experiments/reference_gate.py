"""Small paired missingness experiment and separate synthetic consequence-use gate.

Neither status outputs nor abstract intervention choices can execute robot actions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .equivalence import paired_inputs
from .interface_search import execute, fixture, summarize
from .interface_search import TOKENS, COMPACT
from .records import file_hash, load_records
from .reference_quality import local_reference

STATUS_STEPS = (0, 48, 155)
FORMATS = ("numeric_table", "direction_table", "direction_criteria", "terminal_criteria")
QUESTION = "Does the observed drawer state satisfy the requested goal?"
STATUS_CRITERIA = {"A": "DONE: goal satisfied", "B": "CONTINUE: goal not satisfied"}


def articulation(qpos):
    if not np.isfinite(qpos):
        raise ValueError("finite oracle articulation required")
    return "open" if qpos < -.14 else "closed" if qpos > 0 else "partly open"


def progress_projection(pair, before, source_hash):
    oracle, perceptual = paired_inputs(pair)
    physical = pair["physical"]
    if physical["task"] != "top_drawer" or physical["init_state_id"] != 0 or physical["seed"] != 1:
        raise ValueError("unexpected paired task/init/seed")
    if physical["environment_step"] not in STATUS_STEPS:
        raise ValueError("unselected boundary")
    missing = perceptual.state.fields["progress.remaining_open_mm"]
    if missing.value is not None or missing.source != "unknown" or missing.privileged:
        raise ValueError("perceptual progress must remain explicitly unknown")
    qpos = before["qpos_m"]
    observed = articulation(qpos)
    if (observed == "closed") != before["success"]:
        raise ValueError("oracle category disagrees with physical success predicate")
    if abs(oracle.state.fields["progress.remaining_open_mm"].value + 1000*qpos) > 1e-6:
        raise ValueError("oracle progress and before-state measurement disagree")
    truth = "DONE" if observed == "closed" else "CONTINUE"
    base_source = {"source_sha256": source_hash, "pair_id": pair["pair_id"], "physical": physical,
                   "perceptual_belief_id": perceptual.state.meta.get("belief_id"),
                   "oracle_current_source": "archived before.qpos_m; not probe endpoint",
                   "oracle_qpos_m": qpos, "physical_status_not_model_input": truth,
                   "perceptual_current_source": "CDS progress.remaining_open_mm is unknown",
                   "no_history_or_effects": True}
    result = []
    for reverse in (False, True):
        criteria = dict(reversed(list(STATUS_CRITERIA.items()))) if reverse else dict(STATUS_CRITERIA)
        for branch in ("oracle", "perceptual", "masked_oracle"):
            value = observed if branch == "oracle" else "unknown"
            result.append(fixture(f"The drawer is currently {value}. The requested state is closed.",
                          QUESTION, criteria, condition="status_"+branch+("_reversed" if reverse else ""),
                          sample=f"step{physical['environment_step']}", answer=[truth] if branch == "oracle" else None,
                          source={**base_source, "branch": branch, "oracle_category": observed},
                          mapping={"A": "DONE", "B": "CONTINUE"}))
        if result[-1]["payload_id"] != result[-2]["payload_id"]:
            raise AssertionError("masked oracle must exactly reproduce perceptual input")
    return result


def status_fixtures(path):
    rows, errors = load_records(path)
    if errors or not any(r["kind"] == "termination" and r["data"].get("reason") == "collection_smoke_complete" for r in rows):
        raise ValueError("accepted complete paired source required")
    digest = file_hash(path)
    before = {r["data"]["physical_state_id"]: r["data"]["before"] for r in rows if r["kind"] == "reference_evaluator"}
    pairs = {}
    for row in rows:
        if row["kind"] != "paired_state":
            continue
        pair = row["data"]
        step = pair["physical"]["environment_step"]
        if step in STATUS_STEPS:
            if step in pairs:
                raise ValueError("duplicate selected boundary")
            pairs[step] = pair
    if set(pairs) != set(STATUS_STEPS):
        raise ValueError("missing selected boundary")
    return [f for step in STATUS_STEPS for f in progress_projection(
        pairs[step], before[pairs[step]["physical"]["physical_state_id"]], digest)]


def consequence_fixture(presentation, goal, swapped, reverse):
    if presentation not in FORMATS or goal not in {"open", "closed"}:
        raise ValueError("unknown consequence presentation or goal")
    changes = {"A": 5. if swapped else -5., "B": -5. if swapped else 5.}
    facts = {k: (f"opening changes by {value:+g} mm" if presentation == "numeric_table" else
                 f"drawer ends {'closed' if value < 0 else 'open'}" if presentation == "terminal_criteria" else
                 f"opening {'decreases' if value < 0 else 'increases'}") for k, value in changes.items()}
    criteria = {k: f"intervention {k}" for k in changes}
    state = f"The drawer is currently partly open. The requested state is {goal}."
    if presentation.endswith("criteria"):
        criteria = {k: f"intervention {k}: {facts[k]}" for k in changes}
    else:
        state += " Stated outcomes: " + "; ".join(f"{k}: {facts[k]}" for k in changes) + "."
    if reverse:
        criteria = dict(reversed(list(criteria.items())))
    answer = [k for k, value in changes.items() if (value < 0) == (goal == "closed")]
    return fixture(state, "Choose the intervention whose stated outcome moves the drawer toward the requested state.",
                   criteria, condition=presentation, sample=f"goal_{goal}_swap_{int(swapped)}_reverse_{int(reverse)}",
                   answer=answer, effects_supplied=True,
                   source={"effect_source": "synthetic_control", "not_physical_simulator_evidence": True,
                           "horizon": "unspecified_hypothetical_terminal" if presentation == "terminal_criteria" else "one_equal_step",
                           "goal": goal, "swapped": swapped, "reverse": reverse,
                           "terminal_control_not_equivalent_to_5mm": presentation == "terminal_criteria"})


def consequence_fixtures():
    return [consequence_fixture(fmt, goal, swapped, reverse) for fmt in FORMATS
            for goal in ("open", "closed") for swapped in (False, True) for reverse in (False, True)]


def abstention_fixtures(path):
    result = []
    for f in status_fixtures(path):
        condition = f["condition"]
        if condition not in {"status_oracle", "status_perceptual"}:
            continue
        if condition == "status_perceptual" and f["sample"] != "step0":
            continue  # one unknown payload, not three pseudo-independent trials
        for reverse in (False, True):
            criteria = {**STATUS_CRITERIA, "C": "UNKNOWN: current state unavailable"}
            if reverse:
                criteria = dict(reversed(list(criteria.items())))
            answer = ["UNKNOWN"] if condition == "status_perceptual" else f["diagnostic_reference_not_model_input"]["scored_expected_tokens"]
            result.append(fixture(f["state"], QUESTION, criteria,
                          condition="abstention"+("_reversed" if reverse else ""),
                          sample=f["sample"]+"_"+f["source"]["branch"], answer=answer, source=f["source"],
                          mapping={"A": "DONE", "B": "CONTINUE", "C": "UNKNOWN"}))
    return result


def physical_fixtures(root):
    result = []
    for init, step in ((0,48), (1,48), (2,48), (0,140)):
        path = Path(root)/f"init{init}-raycast-v02"/"episodes.jsonl"
        rows, errors = load_records(path)
        if errors or not any(r["kind"] == "termination" and r["data"].get("reason") == "collection_smoke_complete" for r in rows):
            raise ValueError("accepted complete source required")
        selected = [r["data"] for r in rows if r["kind"] == "paired_state" and r["data"]["physical"]["environment_step"] == step]
        if len(selected) != 1:
            raise ValueError("unique selected pair required")
        pair = selected[0]
        paired_inputs(pair)
        pid = pair["physical"]["physical_state_id"]
        reference = next(r["data"] for r in rows if r["kind"] == "reference_evaluator" and r["data"]["physical_state_id"] == pid)
        if reference["source_restore_max_error"] > 1e-8 or reference["stop_replay_max_error"] > 1e-8:
            raise ValueError("unreliable counterfactual restoration")
        before = reference["before"]
        probes = {r["data"]["token"]:r["data"] for r in rows if r["kind"] == "evaluator_probe" and r["data"]["physical_state_id"] == pid}
        if set(probes) != set(TOKENS) or any(p["execution"]["environment_step_count"] != 8 for p in probes.values()):
            raise ValueError("complete equal-horizon native probes required")
        measured = local_reference(before, probes)
        effects = {}
        for token in TOKENS:
            delta = probes[token]["after"]["remaining_open_mm"] - before["remaining_open_mm"]
            effects[token] = {"opening_change_mm": delta,
                              "opening_change": "decreases" if delta < -.25 else "increases" if delta > .25 else "unchanged",
                              "obstacle": not measured["candidates"][token]["sampled_obstacle_admissible"]}
        for goal in ("closed", "open"):
            sign = 1 if goal == "closed" else -1
            supported = [t for t,v in measured["candidates"].items() if v["sampled_obstacle_admissible"]
                         and sign*v["closing_mm"] > .25 and sign*v["closing_vs_stop_mm"] > .25]
            if not supported:
                raise ValueError("selected reference must have actual and incremental bidirectional support")
            for effect_mode in ("none", "true", "misassigned"):
                state = (f"The drawer is currently {articulation(before['qpos_m'])}. The requested state is {goal}. "
                         "Nominal moves are intents. Outcomes, when supplied, describe 0.4 seconds. Obstacle means new or endpoint obstacle contact.")
                criteria, bindings = {}, {}
                for i, token in enumerate(TOKENS):
                    bound = TOKENS[(i+1) % len(TOKENS)] if effect_mode == "misassigned" else token
                    bindings[token] = bound
                    effect = effects[bound]
                    desc = COMPACT[i]
                    if effect_mode != "none":
                        desc += f"; opening {effect['opening_change']}; obstacle {'yes' if effect['obstacle'] else 'no'}"
                    criteria[f"A{i:02d}"] = desc
                for reverse in (False, True):
                    ordered = dict(reversed(list(criteria.items()))) if reverse else criteria
                    result.append(fixture(state,
                        "Avoid obstacle contact. Choose an intervention that moves drawer opening toward the requested state.",
                        ordered, condition="physical_"+effect_mode+("_reversed" if reverse else ""),
                        sample=f"init{init}_step{step}_goal_{goal}", answer=supported,
                        mapping={f"A{i:02d}":t for i,t in enumerate(TOKENS)}, effects_supplied=effect_mode != "none",
                        source={"physical": pair["physical"], "pair_id": pair["pair_id"], "source_sha256": file_hash(path),
                                "effect_source": "none" if effect_mode == "none" else "oracle_sim_counterfactual",
                                "effect_assignment": bindings, "goal": goal, "effect_mode": effect_mode,
                                "oracle_effects_not_model_input_as_numeric_table": effects,
                                "independent_evaluation_not_model_input": measured,
                                "contract_flags_not_model_input": {t:p["execution"].get("execution_contract_violation") for t,p in probes.items()}}))
    return result


def js(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float)
    p, q = p/p.sum(), q/q.sum()
    m = (p+q)/2
    return sum(float(np.sum(x[x > 0]*np.log(x[x > 0]/m[x > 0]))) for x in (p, q))/2


def physical_assessment(source, token):
    """Recompute usefulness from raw numeric outcomes, not cached preferred labels."""
    effects = source["oracle_effects_not_model_input_as_numeric_table"]
    chosen, stop = effects[token], effects["STOP"]
    sign = 1 if source["goal"] == "closed" else -1
    absolute = -chosen["opening_change_mm"]
    incremental = stop["opening_change_mm"]-chosen["opening_change_mm"]
    shown = effects[source["effect_assignment"][token]] if source["effect_mode"] != "none" else None
    return {"goal": source["goal"], "absolute_closure_mm": absolute, "closure_vs_stop_mm": incremental,
            "absolute_goal_progress": sign*absolute > .25,
            "local_support": sign*absolute > .25 and sign*incremental > .25 and not chosen["obstacle"],
            "actual_obstacle": chosen["obstacle"],
            "presented_direction_matches_goal": None if shown is None else shown["opening_change"] == (
                "decreases" if source["goal"] == "closed" else "increases"),
            "contract_flag": source["contract_flags_not_model_input"][token]}


def report(path):
    result = summarize(path)
    path = Path(path)
    path = path / "episodes.jsonl" if path.is_dir() else path
    rows, _ = load_records(path)
    fixtures = {r["data"]["fixture_id"]: r["data"] for r in rows if r["kind"] == "search_fixture"}
    calls = result["calls"]
    comparisons = []
    for oracle in calls:
        if oracle["condition"] not in {"status_oracle", "status_oracle_reversed"}:
            continue
        suffix = "_reversed" if oracle["condition"].endswith("_reversed") else ""
        matches = {branch: [c for c in calls if c["sample"] == oracle["sample"] and c["repeat"] == oracle["repeat"]
                    and c["condition"] == "status_"+branch+suffix] for branch in ("perceptual", "masked_oracle")}
        if any(len(v) != 1 for v in matches.values()):
            continue  # incomplete input remains incomplete, never invent a pair
        perceptual, masked = matches["perceptual"][0], matches["masked_oracle"][0]
        p, q = [[c["probabilities"][k] for k in ("DONE", "CONTINUE")] for c in (oracle, perceptual)]
        comparisons.append({"sample": oracle["sample"], "repeat": oracle["repeat"], "reversed": bool(suffix),
                            "pair_id": fixtures[oracle["fixture_id"]]["source"]["pair_id"],
                            "oracle_choice": oracle["choice"], "perceptual_choice": perceptual["choice"],
                            "oracle_probabilities": p, "perceptual_probabilities": q,
                            "oracle_correct": oracle["correct"], "js_nats": js(p,q),
                            "masked_payload_equals_perceptual": fixtures[masked["fixture_id"]]["payload_id"] == fixtures[perceptual["fixture_id"]]["payload_id"],
                            "masked_probabilities_equal_perceptual": masked["probabilities"] == perceptual["probabilities"]})
    stable = all(c["choice_equal"] and c["probabilities_equal"] and c["raw_logits_equal"] for c in result["repeat_comparisons"])
    passed = [fmt for fmt in FORMATS[:-1] if result["complete"] and stable
              and result["groups_first_repeat"].get(fmt, {}).get("correct") == 8
              and sum(c["condition"] == fmt and c["correct"] is True for c in calls) == 16]
    physical = []
    for c in calls:
        if not c["condition"].startswith("physical_"):
            continue
        s = fixtures[c["fixture_id"]]["source"]
        physical.append({"fixture_id": c["fixture_id"], "sample": c["sample"], "condition": c["condition"],
                         "repeat": c["repeat"], "choice": c["choice"], **physical_assessment(s, c["choice"])})
    physical_true = [p for p in physical if p["condition"] in {"physical_true", "physical_true_reversed"}]
    return {**result, "status_comparisons": comparisons, "consequence_gate_passed_presentations": passed,
            "physical_assessments": physical,
            "physical_reference_gate_passed": result["complete"] and stable and len(physical_true) == 32
                and all(p["local_support"] for p in physical_true),
            "does_not_validate_atomic_policy": True}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--suite", choices=["status", "consequences", "abstention", "physical"])
    p.add_argument("--pairs", default="runs/reference-pilot/init0-raycast-v02/episodes.jsonl")
    p.add_argument("--output")
    p.add_argument("--pilot-root", default="runs/reference-pilot")
    p.add_argument("--summarize")
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--device", default="cuda")
    p.add_argument("--laya-path", default="/home/junhongli/models/huggingface/laya/typed-decisions")
    args = p.parse_args()
    if args.summarize:
        print(json.dumps(report(args.summarize), indent=2, allow_nan=False))
    elif args.output and args.suite and args.repeats == 2:
        functions = {"status": lambda: status_fixtures(args.pairs), "consequences": consequence_fixtures,
                     "abstention": lambda: abstention_fixtures(args.pairs), "physical": lambda: physical_fixtures(args.pilot_root)}
        execute(functions[args.suite](), args)
    else:
        p.error("suite, fresh output and exactly two repeats required")


if __name__ == "__main__":
    main()
