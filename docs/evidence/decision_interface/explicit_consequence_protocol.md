# Explicit desired-consequence question: pre-inference protocol

2026-09-23. Laya only, research/decision-interface. Offline diagnostic; no
physical execution, new provider, formal E0, CDS/perception/controller change.

## Causal question and single intervention

Can Laya match a supplied desired consequence to candidate effects when the
goal-to-consequence transformation is supplied explicitly? Continue from
selective_grip_handoff.md. Replace only the action question's `instructions`:

- Control: `Choose an intervention for the requested goal.`
- Closed: `Choose an intervention with opening decreases, vs STOP lower, and obstacle no.`
- Open: `Choose an intervention with opening increases, vs STOP higher, and obstacle no.`

Do not change the `criteria` dictionary. The entire goal-last state/rules,
selectively anonymous GRASP/RELEASE descriptions, other nine native descriptions,
neutral option IDs, actual action mappings, order, effects, history and evaluator
remain unchanged. No winning identity, utility label, ranking or new physical
information is supplied. Preserve parent fixture/payload IDs and intervention
lineage. This question is longer; token positions can change as a consequence.
The experiment isolates the question field, not semantics independently of length.

## Predicate derivation

Existing `effect_binding.effect_facts` uses a strict 0.25 mm tolerance for
absolute opening change and for candidate opening change minus STOP opening
change. `presented_support` requires the conjunction of `decreases`, `lower`,
and no measured obstacle for closing, or `increases`, `higher`, and no measured
obstacle for opening. The numeric evaluator requires >0.25 mm progress in both
absolute and STOP-relative terms, with no sampled/endpoint obstacle violation.
Use those existing predicates without changing them. Unknowns stay unknown; reject
missing/nonfinite measurements rather than inventing them. All these frozen
obstacle flags are false, so obstacle discrimination cannot be demonstrated.

## Frozen design and inference

Use all 32 selective variants from `runs/selective-grip/laya-v01/episodes.jsonl`,
SHA-256 `032444bf8fe439e6ac2a84a7e0f7a4c59b760fc64ab5e00bceab28e74b628ad6`.
Select by intervention version, not preserved native source metadata. Four
boundaries: init 0/1/2 step 48 and init 0 step 140; true/shift-four effects;
closed/open goals; original/reversed option order. Eleven actions retain their
archived eight-control/0.4-second outcomes. Opening remains a counterfactual
local objective at closing-task states, not a new opening rollout.

32 unchanged controls + 32 question variants, each twice = 128 calls. Interleave
each pair and alternate its first condition by fixture index; reverse the full
traversal for repeat two. Compare all 64 controls to archived selective outputs,
including logits/probabilities. Count first repeats for rates, not 128 independent
episodes. No retries, fallback, reranking or prompt search.

Local Laya typed-decisions content ID
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`;
CUDA_VISIBLE_DEVICES=1, CUDA/bfloat16, seed one once, eleven-option temperature
`0.10058280825614929`. Require identical loaded configuration and recorded
inference environment. Use the existing adapter and scorer.

Fresh preflight and inference directories only. Save full fixtures, model/config,
protocol and working-source identities, complete token audits, call intents,
raw outputs and scorer logits/probabilities. Preserve failures. Validate no
clipping, unchanged source/evaluator hashes, and exact agreement between preflight
and actual calls. Diagnose any mismatch instead of altering other variables.

## Evaluation and decision rule

Keep supplied-fact correctness separate from actual numeric physical utility;
shifted effects are intentionally false. Retain execution-contract flags and
invalid/missing calls. Reconstruct results from raw records and independently
check against numeric effects. Report:

- Both correctness measures by goal, assignment, option order and boundary.
- Goal reversals: both correct, appropriate consequence/action reversal, scores.
- Reassignment: both correct, moved supported sets and overlap; retaining an
  identity can be legitimate when supported sets overlap.
- Order robustness: both correct versus identity changes and order failures.
- Selected consequence directions, identities, supported probability mass.
- Exact repeat stability and archived-control reproduction.

Reliable finite matching requires all 32 explicit fixtures correct on both
repeats, all true-effect choices numerically useful, complete valid stable calls,
and exactly reproduced controls. Aggregate improvement alone is insufficient.
Any failed direction/assignment/order must be reported. A pass establishes only
bounded explicit-consequence matching; it cannot validate original goal binding,
a full-task/no-effect expert, CDS sufficiency, or formal E0.

Classify as (1) reliable matching restored; (2) improvement with substantial
remaining matching failures; (3) little meaningful benefit; or (4) inconclusive
for an evidenced integrity/design reason. Distinguish an upstream transformation
limitation from downstream matching failures without claiming internal mechanisms.
Stop after this experiment and recommend one next experiment from its results.
