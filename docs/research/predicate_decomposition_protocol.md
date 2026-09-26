# Predicate decomposition diagnostic v0.1

Registered before inference. This is one bounded follow-up to the failed binary
verification diagnostic, not an adaptive prompt search or live controller.

## Source, unit and hypotheses

Use the complete frozen `predicate-verification-run-01` evidence and require its
independent audit to pass, its repeats stable, and its archived controls reproduced.
Frozen source JSONL SHA-256:
`47722f42f328af02d3fe534390bd78ad00a682126ea6d8b6886134943b14dd50`.
Source source/payload hashes, all numerical effects and effect assignments remain
preserved. The 176 parent/candidate cases reduce to 74 unique model-facing inputs,
37 per goal: deduplicate only identical unchanged state, exact candidate description
and full criterion. Preserve every original lineage and both original answer-order
fixture identities. Distinct physical actions with identical displayed text are
collapsed only for this offline language diagnostic; no runtime pool is changed.

Competing explanations are a negative-answer spelling artifact, difficulty with the
STOP-relative clause, and failure to combine individually understood clauses. The
prior result also permits general task/criterion interpretation failure. These
experiments distinguish observable capabilities, not internal mechanisms.

## Four fixed conditions

For each of the 74 unique source inputs, retain the exact original state and full
candidate description, including irrelevant-to-single-clause effects. Retain this
wrapper:

```
Determine whether this candidate satisfies the stated criterion. Criterion: {criterion}
Candidate: {exact original candidate description}
```

1. `full_control`: original full criterion and original labels `V0: satisfies`,
   `V1: does_not_satisfy`, unchanged byte-for-byte model payload.
2. `full_spaced`: same full criterion; change only V1 display to `does not satisfy`.
3. `opening_only`: labels as condition 2; criterion exactly
   `Judge only whether the stated opening decreases.` for closed, or
   `Judge only whether the stated opening increases.` for open.
4. `stop_only`: labels as condition 2; criterion exactly
   `Judge only whether the stated opening is lower than STOP.` for closed, or
   `Judge only whether the stated opening is higher than STOP.` for open.

All questions remain `choice`. Canonical V0/V1 meaning remains satisfies /
does_not_satisfy in every condition. Reverse displayed insertion order in the
second answer-order condition. Do not reverse label identities. The original
state still contains global task context; a single-clause condition changes the
supplied criterion, not the complete contextual task specification.

Labels are evaluator-only. Independently parse exact candidate effect suffixes and
check against assigned underlying numeric effects. Opening-only tests the strict
requested-direction change >0.25 mm. STOP-only tests the strict requested-direction
difference from the physical STOP endpoint >0.25 mm. Full tests both plus no obstacle.
All archived obstacle flags are false, so this cannot test obstacle discrimination.

## Execution and audit

74 inputs ×4 conditions ×2 answer orders ×2 repeats =592 fixtures /1184 calls.
Sort unique inputs by their model-content hash; use the fixed condition order above,
then forward/reverse answer order. The second repeat reverses all592 fixtures.
Keep the same checkpoint, configuration, dtype, seed1 and binary temperature.
Record device/environment explicitly. No new model settings or simulator calls.

Require model/token preflight; freeze protocol, all Python source hashes and model
content before running. Preserve actual forward IDs, markers, logits, raw answers,
rounded probabilities, failures and every missing judgment. Controls must reproduce
every matching source response, even where several archived identities share one
input. Preserve expected versus actual1184-call coverage and exact two-repeat
reproduction. Do not retry a failed run invisibly.

Report first-repeat per-condition/per-goal confusion, sensitivity, specificity,
balanced accuracy, class counts, answer-order changes and matched changes between
conditions. Deduplicated counts are primary; source lineage permits a clearly labeled
historical weighting secondary analysis.74 inputs are not74 independent physical
samples: only four physical contexts underlie them.

A wording-only improvement supports a presentation artifact, not a physical skill.
Good single-clause performance plus poor full-spaced performance supports a bounded
composition/interface deficit; single-clause failure prevents that inference.
Binary probabilities remain uncalibrated scores despite matched cardinality. No
probability threshold, prompt search, live selector or architectural change follows
automatically. Stop after this registered experiment and inspect the evidence.

Pre-inference independent label audit found an identifiability limit: within these
37 unique cases per goal, closed full-rule truth equals STOP-only truth (9 positives),
and open full-rule truth equals opening-only truth (5 positives). The dataset lacks
all Boolean combinations. A full/single-clause difference therefore demonstrates
bounded instruction/interface sensitivity; it cannot uniquely identify general
conjunction-composition capability. This finding was recorded before new inference.
