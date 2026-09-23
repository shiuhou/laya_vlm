# Requested-goal placement: one controlled Laya intervention

2026-09-23. Declared before inference on research/decision-interface, baseline
eddbcde04649419d8d5d44e62e433882578328eb. No formal E0 or physical execution.

## Question and exact intervention

Does moving the unchanged requested-goal sentence after all rules improve Laya's
combination of requested goal and supplied candidate consequences?

Use all 64 full-effect fixtures from the frozen effect-binding archive, SHA-256
3875a25255eeb7880e1168579567758f68d616d39a023cc28c1ddef3e0c5eea5.
Move exactly `The requested state is closed.` or `The requested state is open.`
from immediately after the current-articulation sentence to the end of the state
string, after the original STOP-rule sentence. Preserve the original closed/open
STOP-clause order. Remove the original occurrence; do not duplicate or reword it.
Preserve all other text and single-space sentence separators. Record parent IDs.

Laya's actual logical sequence is question/options followed by state. Thus this
intervention moves the goal later within state; it does not move it closer to the
option list. Audit the actual token sequence and length instead of assuming an
attention mechanism. Token positions necessarily change; no additional words,
physical fields, examples, recommendations or selected-action labels are added.

Keep four archived physical contexts (init 0/1/2 step 48 and init 0 step 140), seed
1, all eleven options, native/anonymous descriptions, true/shift-four assignments,
closed/open goals, original/reversed options, empty history, full absolute and
STOP-relative effects, obstacle flags and evaluator. These sentence projections
are not full CDS. False effect assignments test supplied-fact use, not physics.

## Controls, inference and preservation

Laya alone is the primary experiment. No additional provider is introduced; no
Qwen inference is planned because same-provider paired interventions directly test
the current question. Any later use would require an explicit evidential reason.

Rerun all 64 unchanged originals and all 64 moved-goal fixtures twice: **256 calls**.
Interleave each original/moved pair, alternating which comes first by fixture
index. Reverse the full traversal on repeat two. Compare every unchanged output
with its archived repeat, including logits/probabilities, and every intervention
with its same-session original. These factorial cases/repeats are correlated;
they are not independent episodes or estimates of population performance.

Use existing local Laya typed-decisions, content ID
9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704,
CUDA/bfloat16, seed one set once, unchanged eleven-option temperature and adapter.
Check loaded configuration against the archive. Use the existing run_call recorder,
input/token audits and raw-only evaluators. No retries, fallback, output reranking,
checkpoint modifications, context extension or parameter tuning.

Write a fresh preflight directory containing all planned fixtures and token audits
before inference. Require the inference run to match that preflight. Use a fresh
run directory; retain failures, raw inputs/outputs, scorer logits/probabilities,
actual consumed tokens, model/config/source hashes, protocol and source provenance.
Any material mismatch, clipping or incomplete evidence blocks an unqualified causal
claim. Diagnose it without silently changing additional variables.

## Evaluation and interpretation

Reuse the strict existing numeric predicate: >0.25 mm absolute AND >0.25 mm
STOP-relative progress in the requested direction, with no measured obstacle
violation. Keep controller contract flags; local utility does not waive them.
Separate supplied-fact consistency from actual utility, especially under shift-four.

Report original versus moved placement by native/anonymous descriptions, true/shifted
facts, goal, option order and physical context. Assess:

- Useful choices under true effects and correctness under supplied facts.
- Paired goal reversal: action change alone, selected presented-effect direction,
  and both goals correct with the required close-to-open consequence/action reversal.
- Effect reassignment: identity change, both choices correct for their supplied
  facts, supported-set overlap, and retained versus changed selected direction.
- Opening/closing/mixed selected bundles, independently of requested goal and names.
- Candidate-wording and option-order sensitivity; preserve valid ties.
- Repeats and archive-control equality, including raw logits and probabilities.
- Supplemental returned probability mass on presented closing/opening supported
  sets; it is not a calibrated success probability or an internal mechanism measure.

The bounded native reference gate is unchanged: all native true choices useful,
all native shifted choices fact-consistent, across goals/orders/repeats, with valid,
stable outputs and reproduced controls. Report whether anonymous controls also
support appropriate goal use. A pooled score or a reversed directional bias does
not establish competence. A pass still would not validate a no-effect expert or
authorize formal E0.

Classify the evidence as (1) substantial restoration of goal-conditioned consequence
selection, (2) behavioral effect without explaining the core failure, (3) little
meaningful effect weakening this placement/salience account, or (4) inconclusive
for a concrete integrity/design failure. Base interpretation on paired mechanisms
and disaggregated results, not aggregate accuracy alone. Do not infer a universal
presentation limitation or an internal attention cause from a position intervention.

Stop after this experiment. Recommend exactly one next experiment from its results;
do not execute that recommendation, redesign CDS, add fields or start formal E0.
