# Selective GRASP/RELEASE description removal on goal-last Laya fixtures

2026-09-23. Pre-inference protocol; research/decision-interface at eddbcde.
One bounded offline causal diagnostic. No formal E0, execution or new provider.

## Frozen source and intervention

Use the 32 native-description, goal-last fixtures from the accepted goal-placement
archive, raw SHA-256
`4f55a7e7bb193fe6856e36c9cfad1179c4bbbd24724dd2ca7605e72a697932cf`.
Retain four boundaries (init 0/1/2 step 48, init 0 step 140), true/shift-four effect
assignment, closed/open requested goal and original/reversed option order. Each
fixture offers all eleven original action identities with full absolute and
STOP-relative effects, the same physical horizon, empty history and original rules.

Change exactly two nominal description prefixes:

```text
GRASP:   close grip; hold pose  -> intervention
RELEASE: open grip; hold pose   -> intervention
```

Keep each complete following `; opening ...; vs STOP ...; obstacle ...` suffix
byte-identical. All other nine candidate descriptions, neutral option IDs A00–A10,
canonical mappings, order, state text, requested-goal sentence, history, source
physical/evaluation metadata and evaluator stay unchanged. The nominal prefixes
are the experimental presentation; physical semantics/implementation are not changed.
Use exactly the existing anonymous word `intervention`, without trying alternatives.
Neither GRASP nor RELEASE names are added to model-facing text.

This removes wording and shortens two options. Token positions/lengths can change
as an unavoidable part of this requested anonymization; audit them explicitly.
It tests the contribution of these two descriptions jointly, not GRASP versus
RELEASE separately or lexical content independently of length/position.

## Matched controls and provenance

Run 32 original native goal-last fixtures and 32 selective-anonymization variants
twice: **128 Laya calls**. Interleave paired originals/interventions, alternating
which comes first by fixture index; reverse the entire traversal for repeat two.
Compare all 64 unchanged control calls to their archived counterparts, including
raw logits/probabilities. Retain parent payload/fixture IDs and the goal-placement
lineage. No new inference on fully anonymous fixtures; their archived results may
serve only as an explicitly historical descriptive comparison.

Use unchanged local Laya content ID
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`,
CUDA/bfloat16, seed one set once, eleven-option temperature, adapter and loaded
configuration. No new providers, response retries, fallback, reranking, parameter
tuning, schema, candidate effect, controller or perception changes.

Write all fixtures and complete token audits to a fresh preflight directory before
inference. Require run inputs, model/configuration and sources to match preflight
and the accepted source. Use fresh directories. Preserve every attempt, full prompt,
actual consumed tokens, raw response, scorer logits/probabilities and working-source,
protocol/model/config hashes. Reject clipping and material mismatches; diagnose
them explicitly instead of silently changing additional variables.

## Evaluation

Reuse the numeric predicate: >0.25 mm absolute AND >0.25 mm STOP-relative movement
in the requested direction, with no existing sampled/endpoint obstacle violation.
Keep execution-contract flags. Supplied-fact consistency is scored independently
from actual physical utility under deliberately shifted effects. Invalid outputs
and failures must not disappear from denominators.

Report first repeats and exact repeat comparisons, not correlated calls as
independent episodes. Disaggregate by goal, assignment, option order and boundary:

- True-effect utility and assigned-fact correctness.
- Goal-reversal pairs: changed action, selected effect direction, both goals
  correct, and appropriate closing-to-opening consequence/action reversal.
- Effect-reassignment pairs: changed action, both choices fact-consistent and
  overlap of supported sets (a changed identity is not always necessary).
- Option-order reversal: both orders correct versus order-dependent failure.
- GRASP/RELEASE identities and their combined returned probability mass, compared
  with correct-consequence mass. An improvement must follow facts, not simply
  suppress those two candidates when their assigned consequences are useful.
- Opening/closing/mixed directions; original→selective correctness transitions.
- Coverage: both goals/assignments/orders passing at each physical boundary;
  do not characterize isolated favorable cases as generalization.

The finite reference gate requires all true-effect choices useful and all shifted
choices fact-consistent across goals, orders, boundaries and repeats, with complete
stable valid calls and reproduced controls. A pass would qualify only this bounded
effect-conditioned presentation, not a no-effect/full-task expert or formal E0.

## Interpretation and stopping

Classify whether the two descriptions are (1) a major source, indicated by broad
recovery of goal reversal and reassignment correctness across boundaries/orders;
(2) a contributor with most binding failure unresolved; (3) not a meaningful source
of the binding deficit, despite any identity/probability changes; or (4) inconclusive
because of an evidenced design/integrity problem. Show the disaggregated contrasts
underlying that classification. A large fall in GRASP/RELEASE use alone does not
count as recovery. Do not infer a particular internal attention or lexical mechanism.

Stop after this one intervention. Recommend one next experiment from the observed
results; do not execute it or broaden the project. Keep Laya primary and formal E0
blocked unless its distinct scientific gate is actually satisfied.
