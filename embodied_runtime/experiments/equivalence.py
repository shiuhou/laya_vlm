"""State-gap pairing, repeatability, and metrics; never executes model choices."""
from copy import deepcopy
from dataclasses import asdict
import time

import numpy as np

from ..decision_interface import CanonicalDecisionInput, CanonicalDecisionState, CandidateEffectBundle, candidate_id
from ..runtime_core import Candidate, _sha256_json


def field_differences(oracle, perceptual):
    same_position_definition = (oracle.fields["target.position_definition"].value ==
                                perceptual.fields["target.position_definition"].value)
    result = {}
    for key, a in oracle.fields.items():
        b = perceptual.fields[key]
        status = ("both_unknown" if a.value is None and b.value is None else
                  "missing" if a.value is None or b.value is None else
                  "incomparable_definition" if not same_position_definition and
                  (key == "target.position_m" or key.startswith("relations.")) else "comparable")
        result[key] = {"status": status, "oracle_available": a.value is not None,
                       "perceptual_available": b.value is not None,
                       "value_equal": a.value == b.value, "evidence_equal": asdict(a) == asdict(b)}
        if status == "comparable" and isinstance(a.value, (float, int, list)) and not isinstance(a.value, bool):
            result[key]["difference_l2"] = float(np.linalg.norm(np.asarray(a.value) - b.value))
    return result


def make_pair(oracle, perceptual, candidates, *, physical, history=(), natural_perceptual=(), natural_oracle=None):
    if perceptual.privileged or perceptual.meta.get("branch") != "perceptual" or oracle.meta.get("branch") != "oracle":
        raise ValueError("pair branch privilege mismatch")
    if oracle.meta["asof_sim_time"] != perceptual.meta["asof_sim_time"] or physical["sim_time"] != perceptual.meta["asof_sim_time"]:
        raise ValueError("pair must reference the same physical boundary")
    if oracle.meta.get("oracle_source") != physical["physical_state_id"]:
        raise ValueError("oracle source does not match paired physical state")
    if set(("task", "init_state_id", "seed")) - set(physical):
        raise ValueError("paired experimental unit requires task, init_state_id and seed")
    effects = CandidateEffectBundle(candidate_id(candidates))
    a = CanonicalDecisionInput(oracle, candidates, effects, history, diagnostic_only=True)
    b = CanonicalDecisionInput(perceptual, candidates, effects, history, diagnostic_only=True)
    assert a.questions() == b.questions()
    result = {"version": "paired-decision-v0.1", "physical": physical,
              "oracle_state": asdict(oracle), "perceptual_state": asdict(perceptual),
              "shared_candidates": [c.canonical() for c in candidates], "candidate_set_id": candidate_id(candidates),
              "shared_effects": asdict(effects), "shared_history": history,
              "question_id": _sha256_json(a.questions()), "effect_mode": "none",
              "field_differences": field_differences(oracle, perceptual),
              "natural_perceptual_candidates": [c.canonical() for c in natural_perceptual],
              "natural_oracle_candidates": None if natural_oracle is None else [c.canonical() for c in natural_oracle],
              "natural_candidate_set_agreement": None if natural_oracle is None else
              {c.token for c in natural_perceptual if c.feasible} == {c.token for c in natural_oracle if c.feasible}}
    result["pair_id"] = _sha256_json(result)
    return result


def paired_inputs(pair):
    if pair["pair_id"] != _sha256_json({k: v for k, v in pair.items() if k != "pair_id"}):
        raise ValueError("pair content identity mismatch")
    candidates = tuple(Candidate(**c) for c in pair["shared_candidates"])
    if candidate_id(candidates) != pair["candidate_set_id"]:
        raise ValueError("candidate identity mismatch")
    effects = CandidateEffectBundle(**pair["shared_effects"])
    if pair["effect_mode"] != "none" or effects.effects:
        raise ValueError("primary State Gap replay requires no effects")
    inputs = [CanonicalDecisionInput(CanonicalDecisionState.from_dict(pair[key]), candidates, effects,
                                     tuple(pair["shared_history"]), diagnostic_only=True)
              for key in ("oracle_state", "perceptual_state")]
    if any(_sha256_json(i.questions()) != pair["question_id"] for i in inputs):
        raise ValueError("question mismatch")
    return inputs


def distribution(decision, tokens):
    probabilities = decision.probabilities
    if set(probabilities) != set(tokens):
        return None  # Missing output is not zero probability.
    p = np.asarray([probabilities[k] for k in tokens], dtype=float)
    if not np.isfinite(p).all() or np.any(p < 0) or p.sum() <= 0:
        return None
    # Laya API rounds returned probabilities. Preserve raw; normalize only for metrics.
    return p / p.sum()


def compare_decisions(a, b, tokens):
    result = {"top1_agreement": a.token == b.token, "top2_set_agreement": None,
              "js_divergence_nats": None, "oracle_margin": None}
    p, q = distribution(a, tokens), distribution(b, tokens)
    if p is None or q is None:
        return result
    # Ties at rank 2 are reported, not arbitrarily interpreted as disagreement.
    order_p, order_q = np.argsort(-p, kind="stable"), np.argsort(-q, kind="stable")
    result["oracle_margin"] = float(p[order_p[0]] - p[order_p[1]]) if len(p) > 1 else None
    tie = len(p) > 2 and (np.isclose(p[order_p[1]], p[order_p[2]]) or np.isclose(q[order_q[1]], q[order_q[2]]))
    result["top2_boundary_tie"] = bool(tie)
    if not tie:
        result["top2_set_agreement"] = set(order_p[:2]) == set(order_q[:2])
    m = (p + q) / 2
    def kl(x):
        mask = x > 0
        return float(np.sum(x[mask] * np.log(x[mask] / m[mask])))
    result["js_divergence_nats"] = (kl(p) + kl(q)) / 2
    return result


def replay_pair(pair, provider, recorder, *, repeats=3):
    if repeats < 2:
        raise ValueError("at least two repeats required for stability diagnostic")
    inputs = paired_inputs(pair)
    decisions = {"oracle": [], "perceptual": []}
    for repeat in range(repeats):
        # Alternate order to make order/warmup visible; do not reset RNG each call.
        branches = (0, 1) if repeat % 2 == 0 else (1, 0)
        for index in branches:
            name, inp = ("oracle", "perceptual")[index], inputs[index]
            payload = {"state": inp.provider_input(), "question": inp.questions()}
            started = time.perf_counter()
            decision = provider.decide(deepcopy(inp))
            if decision.input_snapshot_id != inp.snapshot_id():
                raise ValueError("provider input identity mismatch")
            recorder.record("equivalence_decision", {"pair_id": pair["pair_id"], "branch": name,
                            "repeat": repeat, "provider": type(provider).__name__, "decision": asdict(decision),
                            "model_input_id": _sha256_json(payload), "latency_ms": (time.perf_counter() - started) * 1000,
                            "choice_allowed": decision.token in inp.allowed()})
            decisions[name].append(decision)
    tokens = sorted(inputs[0].allowed())
    stability = {}
    for name, ds in decisions.items():
        probs = [distribution(d, tokens) for d in ds]
        stability[name] = {"unique_choices": sorted({d.token for d in ds}),
                           "max_probability_difference": None if any(p is None for p in probs) else
                           float(np.max(np.ptp(np.stack(probs), axis=0))),
                           "all_choices_allowed": all(d.token in tokens for d in ds)}
    result = {"pair_id": pair["pair_id"], "provider": type(provider).__name__, "repeats": repeats,
              "stability": stability, "paired_comparisons": [compare_decisions(a, b, tokens) for a, b in
                                                              zip(decisions["oracle"], decisions["perceptual"])]}
    recorder.record("equivalence_diagnostic", result)
    return result
