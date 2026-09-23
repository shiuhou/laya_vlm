# STOP-clause order changes choices without explaining the opening bias

2026-09-23. Research branch `research/decision-interface`, baseline `eddbcde`.
[Pre-inference protocol](clause_order_protocol.md). No E0, simulator execution,
new physical fields, CDS/candidate/controller changes or provider search.

## Decision

**Outcome (2): clause order affects behavior but does not explain the failure.**
The specific hypothesis that choices are dominated by the final STOP-rule clause
is strongly weakened. Anonymous opening bias persists under both orderings:
Laya selects opening-effect bundles **30/32 → 32/32**, Qwen **29/32 → 28/32** when
the closing clause moves last. Only **0/64 Laya** and **1/64 Qwen** matched pairs
switch from opening to closing bundles as predicted by final-clause dominance.

This is not complete order insensitivity: Laya changes action in 23/64 pairs,
including seven native shifted-effect choices moving from mixed/neutral bundles
to closing bundles; Qwen changes 2/64. These effects are stable and causal on the
tested presentations, but do not produce reliable requested-goal conditioning.
The strongest current account remains **inadequate binding of the explicit goal
to candidate consequences in this shared presentation, with provider-dependent
wording/order interference**. The internal cause is unresolved. A universal
recency mechanism, a universal provider failure and a missing physical field are
not established. **Neither provider supplies a useful manipulation reference;
formal E0 remains blocked.**

## Exact intervention and matching

Swap only the two clauses in the final STOP-rule sentence:

```text
Original:
When a STOP comparison is supplied, also require lower opening than STOP for closed, or higher opening than STOP for open.

Intervention:
When a STOP comparison is supplied, also require higher opening than STOP for open, or lower opening than STOP for closed.
```

The instruction is embedded in the state string. Its prefix, including the
requested goal, observed partly-open state and preceding absolute-change rule,
is unchanged. Question, all eleven option identities/descriptions/effects, option
order, empty history and evaluator remain unchanged. Each new fixture retains its
parent fixture/payload IDs; source physical/evaluation metadata is identical.
Every recorded fixture matches the independently saved preflight design.

Use all 64 frozen full-effect fixtures: init 0/1/2 step 48 and init 0 step 140,
seed 1, crossed with native/anonymous descriptions, true/shift-four assignments,
closed/open goals and original/reversed option order. Effects retain the same
eight-control / 0.4 s physical probes. These are sentence projections, **not full
CDS v0.1 serializations**. Opening remains a counterfactual local objective at
archived closing-task states. No new physical trajectory is implied.

Run each transformed fixture twice on each existing provider, reversing traversal
on repeat two. Compare against the accepted archived original calls. Two unchanged
controls per provider (init 0/48, closed, true effects, original option order,
native and anonymous) each repeat twice: **264 new calls**, including eight control
calls. There are 64 matched intervention pairs per provider per repeat. Repeats
and factorial variants are correlated contexts, not independent episodes.

Provider settings remain those in the [provider handoff](provider_comparison_handoff.md):
Laya typed-decisions, CUDA/bfloat16, eleven-option temperature
`0.10058280825614929`; Qwen2.5-7B-Instruct revision
`a09a35458c702b33eeacc393d103063234e8bc28`, CUDA/bfloat16, SDPA, greedy batch one,
seed one, maximum 16 new tokens, identical explicit GenerationConfig and chat
template/system instruction. Actual loaded configurations and model bytes match
their original sessions. No fallback, retry of a model response or reranking.

## Matched choices and selected directions

All tables use first repeats; second repeats match exactly. Direction refers to
the **presented assigned effect bundle**, not the action name or its real outcome
under deliberately shifted facts. Opening means `increases/higher`; closing means
`decreases/lower`. Mixed or neutral categories remain separate.

| Provider / descriptions | Action changes | Opening selections, original → swapped | Opening → closing | Closing → opening |
|---|---:|---:|---:|---:|
| Laya / native | 19/32 | 3/32 → 4/32 | 0/32 | 2/32 |
| Laya / anonymous | 4/32 | 30/32 → 32/32 | 0/32 | 2/32 |
| Qwen / native | 0/32 | 20/32 → 20/32 | 0/32 | 0/32 |
| Qwen / anonymous | 2/32 | 29/32 → 28/32 | 1/32 | 0/32 |

Laya additionally has seven `other → closed` transitions, all with native shifted
effects, all STOP → RELEASE. Two improve supplied-fact correctness for a closing
goal, five remain incorrect for an opening goal. Native shifted closing-bundle
selections rise from 6/16 to 11/16, while that condition's requested-goal score
stays 3/16. This is evidence of an order effect in a specific condition; it cannot
be hidden behind the persistent anonymous bias or interpreted as useful goal use.

The only Qwen opening → closing transition occurs at init 0/48, anonymous shifted
effects, closed goal, original options: GRASP → MV_BACK. The other Qwen change is
init 0/140, anonymous shifted, open goal, original options: MV_DOWN → GRASP; both
choices carry opening bundles. All Qwen native choices and anonymous true-effect
choices are unchanged. Both Qwen changes disappear when the option order is
reversed, so neither is a robust goal-reference improvement.

Across all 64 fixtures, alignment with the final clause falls from **33/64 to
11/64** for Laya and **49/64 to 8/64** for Qwen. For anonymous inputs specifically,
alignment falls **30/32 → 0/32** and **29/32 → 1/32**. Thus the selected direction
does not generally follow whichever STOP-rule clause comes last.

## Requested-goal correctness and actual utility

The evaluator is unchanged: >0.25 mm absolute AND >0.25 mm beyond STOP progress
in the requested direction, with no measured obstacle violation. Under shifted
effects, following the supplied facts and physical usefulness are separate scores.

| Provider / descriptions / effects | Supplied-fact correct, original → swapped | Actual useful, original → swapped |
|---|---:|---:|
| Laya / native / true | 0/16 → 0/16 | 0/16 → 0/16 |
| Laya / native / shifted | 3/16 → 3/16 | 0/16 → 0/16 |
| Laya / anonymous / true | 9/16 → 8/16 | 9/16 → 8/16 |
| Laya / anonymous / shifted | 9/16 → 8/16 | 1/16 → 2/16 |
| Qwen / native / true | 8/16 → 8/16 | 8/16 → 8/16 |
| Qwen / native / shifted | 9/16 → 9/16 | 2/16 → 2/16 |
| Qwen / anonymous / true | 8/16 → 8/16 | 8/16 → 8/16 |
| Qwen / anonymous / shifted | 8/16 → 9/16 | 3/16 → 5/16 |

Anonymous true effects after the swap: **both providers get closed 0/8 and open
8/8**. With shifted effects Laya also gets closed 0/8, open 8/8; Qwen gets closed
1/8, open 8/8. Native goal-conditioned counts do not change: Laya true 0/8 closed,
0/8 open; shifted 3/8 closed, 0/8 open. Qwen true 2/8 closed, 6/8 open; shifted
3/8 closed, 6/8 open.

| Paired criterion, original → swapped | Laya | Qwen |
|---|---:|---:|
| Goal-reversal pairs with both choices correct | 2/32 → 0/32 | 3/32 → 4/32 |
| Effect-reassignment pairs changing action | 25/32 → 18/32 | 25/32 → 24/32 |
| Effect-reassignment pairs with both choices correct | 8/32 → 8/32 | 13/32 → 13/32 |
| Option-order pairs with both choices correct | 9/32 → 8/32 | 12/32 → 12/32 |

Pooled supplied-fact correctness changes Laya **21/64 → 19/64**, Qwen **33/64 →
34/64**. Those small aggregate changes do not establish a reference. True-effect
utility declines for Laya and is unchanged for Qwen; native utility is unchanged
for both. All 64 first-repeat transformed choices under each provider retain a
controller contract flag. These are not waived by local utility. Every candidate's
obstacle flag is false here, so obstacle discrimination is untested.

## Validity, stability and preserved failure

All **264 new choices are valid**, with no clipping, missing responses or unmatched
intents in the completed runs. Actual consumed tokens match the pre-inference
audits: Laya 301–344 tokens, Qwen 321–378. Every Qwen response generates four tokens
ending in EOS; independent raw-logit argmax and decoding checks pass.

Each provider has **66/66 exact repeat matches**: Laya choices, option logits and
probabilities; Qwen choices, generated IDs and full vocabulary logits. All four
unchanged control calls per provider exactly reproduce their archived counterpart,
including raw logits. Every prior Python source file matches its baseline bytes;
only the separate new diagnostic and documentation were added/updated.

`qwen-v01` failed **before any inference**: an overly literal configuration check
compared in-memory integer `id2label` keys with their JSON string keys. A separate
configuration audit showed these were the only differences and canonical JSON
equality was exact. The check now uses the recorder's existing JSON normalization;
the measured configuration is also recorded before checking. No model, prompt or
decoding setting changed. Failure records and the configuration audit remain in
`qwen-v01`; the 132 successful calls are in fresh `qwen-v02`. This was a harness
setup failure, not an excluded model result. Laya's earlier run retains its original
source hash; the two new-module hashes below identify the guard-only correction.

## Updated hypotheses and next experiment

| Hypothesis | Evidence update |
|---|---|
| Final STOP-clause / recency dominance causes the shared opening bias | Strongly weakened: opening dominates after closing moves last; only one opening → closing pair out of 128 first-repeat provider/fixture contrasts. |
| Clause order has no behavioral effect | Rejected: 23 Laya and two Qwen action changes, stable across repeats, with exact controls. |
| Clause-order reversal repairs requested-goal conditioning | Rejected on these fixtures: both native gates fail, anonymous true closing remains 0/8 for each provider. |
| Random instability, changed models/settings, clipping, bad decoding or mismatched fixtures explain the contrast | Not supported by exact repeats, control reproduction, hashed identities and full input/output audits. |
| Complete effect blindness, a Laya-only failure, or missing STOP-relative effects alone | Remain weakened/rejected by the preceding controlled results and persistent effect-reassignment sensitivity. |
| New physical fields are needed to solve the stated local choice | Still unsupported here: both goal and the facts required by the finite predicate are supplied. Full CDS/no-effect sufficiency is unestablished. |

This swaps the first and final STOP-clause positions together; it does not isolate
an internal attention mechanism. The earlier absolute-change rule still ends in
the opening rule, and all observed articulations remain partly open. This experiment
does not distinguish their influence from early requested-goal placement, lexical
priors or conditional-rule integration. Do not call the unchanged shared failure
proof of one of these untested mechanisms.

**Single next experiment:** move the existing requested-goal sentence, unchanged,
from its early state position to immediately after all rule sentences. Use the
original STOP-clause order and the same frozen fixtures/providers/settings, with
matched repeats and controls. Add no words, new fields, examples or selected-action
labels. This directly tests whether early goal placement prevents the providers
from applying an otherwise available requested goal, now that the final STOP-rule
clause itself is not a sufficient explanation. Score both goals and assignments;
an improvement only for one direction does not pass the reference gate. This is
a proposed single placement intervention, not an implemented repair or prompt search.

Useful bounded manipulation reference: **NO**. Full CDS sufficiency: **UNESTABLISHED**.
Formal E0: **BLOCKED**. State Gap and Effect Gap remain separate; privileged effects
stay in these offline diagnostics and never enter perceptual/live inputs.

## Artifacts and reproduction

New module: [clause_order.py](../embodied_runtime/experiments/clause_order.py), using
the unchanged inference adapters, raw validators and utility scorers. New tests:
[test_clause_order.py](../tests/test_clause_order.py). No dependency or weight changes.

Ignored evidence in this worktree:

- `runs/clause-order/preflight-v01/`: exact planned fixtures and source audit,
  written before inference.
- `runs/clause-order/laya-v01/`: manifests, 132 raw calls with option logits and
  probabilities, every full logical presentation/token sequence, raw-derived report.
- `runs/clause-order/qwen-v01/`: zero-inference failure and configuration audit.
- `runs/clause-order/qwen-v02/`: manifests, 132 raw calls and hashed vocabulary
  logits (147,532,734 compressed bytes), full messages/prompts/token sequences,
  raw-derived report. Option probabilities remain explicitly unavailable.
- `runs/clause-order/audit.py` and `audit.json`: independent fixture/prefix/source/
  model checks and disaggregated tables, including both candidate orders.
- `runs/clause-order/matched_pairs.csv`: all 256 repeated provider/fixture contrasts,
  parent/new IDs, selected actions/effects, correctness, physical utility and flags.

| Identity | SHA-256 |
|---|---|
| Frozen Laya source | `3875a25255eeb7880e1168579567758f68d616d39a023cc28c1ddef3e0c5eea5` |
| Frozen Qwen source | `baf1512634f6a60f74f852ebc3988690555f4af897845dbc930cb81091796dff` |
| New Laya raw | `e41bedd2b79de4caaefdbbb8b90866f63eaffa080e11b1586a2233c24bb91600` |
| New Qwen raw | `e2be880864621f260c1f572cff973c5f0a03e94e852345daf520115cd07b0a7a` |
| Laya model content ID | `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704` |
| Qwen model content ID | `e2b474b2efa21f2dbfc6e6c31de53a54f20eea68942e02d34164526078dc4cf5` |
| New module at Laya inference | `d0cc37ea635ced67a6bed49f4adf02d5fb7522228ac5914b6a23b02a35b474bf` |
| New module at Qwen inference | `fbd833b7c4477ea6ee886e3e7982e066200359681c82558865f6c305498a70a6` |
| Protocol | `d52883ec1de008698c5fe64f117e3b0b1dc795196f947445de27e95e832915b4` |
| Independent audit | `bdaec29b3aa95bb052784cbc92927491c57e1fcf930349fb74e529cc7c01d208` |
| Matched-pair CSV | `b5bb2be32aa784a846a7d9cea5c8ae9b0897f1285516b390be20e9ac0b5ae7a2` |

Share these ignored records and logits alongside code; a clone does not contain
the evidence. Original physical provenance remains in the sibling worktree's
`runs/reference-pilot/init{0,1,2}-raycast-v02/` and the unchanged effect archive.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
# Reproduction requires a NEW output directory; do not overwrite evidence.
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.clause_order --provider laya --output NEW_LAYA_RUN
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.clause_order --provider qwen --output NEW_QWEN_RUN
$P -m embodied_runtime.experiments.clause_order --summarize runs/clause-order/laya-v01
$P -m embodied_runtime.experiments.clause_order --summarize runs/clause-order/qwen-v02
PYTHONPATH=. $P runs/clause-order/audit.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Verification: **65 focused and 294 full tests pass**, ruff and compileall pass.
The initial new-test fixture omitted an existing evaluator category and was fixed
before inference; no evaluator code changed. Environment is unchanged: Python
3.10.21, torch 2.2.0, transformers 4.57.3, NumPy 1.26.4, laya 0.3.4.
