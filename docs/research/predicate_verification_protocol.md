# Predicate verification protocol v0.1

Registered 2026-09-26 before new inference. Offline privileged diagnostic only.
No physics execution, controller selection, model tuning, or live prompt change.

## Question and frozen source

Does Laya recognize the explicit goal-consequence conjunction for each candidate,
despite previous failure to select a matching candidate among eleven alternatives?
This distinguishes observable capabilities, not internal neural mechanisms.

Source: `runs/explicit-consequence/laya-v01/episodes.jsonl`, SHA-256
`d4e58fce0d961594090cf4124942e90cd6c044824951429d8ea8ee22e57acb0c`.
Use the 32 explicit-consequence fixtures, not their generic-question controls.
They cover four physical contexts, two goals, true/shift-four effects, and two
original motor option orders. Preserve source lineage and verify the record chain.
All 32 explicit multi-option inputs remain exact reproduction controls.

Select the 16 parents whose original motor order is not reversed for the binary
diagnostic. Every one of their eleven candidates appears once per answer order.
Reversing the original motor list does not create new individual-candidate evidence.

## Exact model-facing intervention

Copy each parent's `state` byte-for-byte. For each candidate copy its complete
original description/effect string byte-for-byte. The single choice question is:

```text
Determine whether this candidate satisfies the stated criterion. Criterion: {parent explicit instructions}
Candidate: {original candidate description}
```

The two criteria are `V0: satisfies` and `V1: does_not_satisfy`. Reverse criterion
insertion order in the answer-order condition; do not reverse the V0/V1 mapping.
The task type remains `choice`. Actual action identity, parent IDs, numeric
evaluator effects, and expected labels stay in evidence outside the model input.
The supplied candidate description retains native nominal motion text where the
archive has it, including the archive's selectively neutralized gripper prefixes.

Labels are computed independently from archived full-precision effects and checked
against the presented strings: absolute movement in the requested direction greater
than 0.25 mm, more than 0.25 mm beyond the STOP endpoint in that direction, and no
obstacle flag. Use the source's explicit effect assignment for presented truth.
Actual physical support and intentionally reassigned presented support are distinct.

## Design and fixed model

- Binary: 16 parents × 11 candidates × 2 answer orders × 2 repeats = **704 calls**.
- Original explicit controls: 32 fixtures × 2 repeats = **64 calls**.
- Total: **384 fixtures, 768 calls**, one fixed presentation, no prompt sweep.
- Deterministic registered traversal, with complete reverse traversal on repeat two;
  preserve exact traversal in the preflight configuration.
- Same Laya typed-decisions content ID
  `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`, installed
  model configuration, bfloat16 CUDA, and seed 1. Record GPU identity/environment;
  do not displace the other user's GPU-1 process to mimic an old device ordinal.
- Preserve the checkpoint's existing per-option-count temperature behavior. Binary
  and eleven-option probabilities are not comparable calibrated confidences.

Preflight verifies source, fixtures, local checkpoint/configuration and complete
tokenization before inference. Inference must match preflight sources, protocol,
fixtures and token IDs. Capture actual forward input IDs, option markers, logits,
raw responses, times and failures with the existing hash-chained recorder. Fail
closed on clipping or malformed output; retain incomplete runs in analysis.

## Evaluation and claim boundaries

Recompute results from raw fixture/intent/response records. A separate auditor
derives labels from raw numeric effects and exact presented clauses without calling
the experiment reporter's label/scoring functions. Verify consumed tokens, argmax,
rounded probabilities, completeness, duplicate/missing calls, and control/repeat
reproduction. Record choice, logit and probability repeatability separately.

Report confusion matrices, positive/negative class counts, per-goal sensitivity
and specificity, balanced accuracy, true/reassigned effects, answer-order changes,
and paired original-control choice versus its binary judgment. Do not treat 704
calls as independent physical samples: there are only four source contexts.

All archived obstacle flags are false. This does not test obstacle discrimination,
interaction-valid contact, perceptual competence, or a safe execution policy. Old
execution-envelope flags stay attached; accurate supplied-fact judgments do not
waive those flags. Exact source controls are required for interpreting changes.

Strong recognition with weak original selection supports a bounded interface
distinction. Recognition failure weakens an upstream-only planning explanation.
The presentation and option count also change, so neither result proves a specific
attention mechanism. Do not turn binary probabilities into a live action selector.
Before a live architecture change, test whether the phenomenon transfers to the
current local-objective/27-primitive boundary. Generality remains unproven.
