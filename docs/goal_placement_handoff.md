# Later goal placement helps some anonymous choices but preserves native failure

2026-09-23. Research branch `research/decision-interface`, baseline
`eddbcde04649419d8d5d44e62e433882578328eb`, with working-source hashes.
[Pre-inference protocol](goal_placement_protocol.md). Laya only; no new provider,
simulator execution, formal E0, or shared interface/controller changes.

## Decision

**Outcome (2): goal placement affects behavior but does not explain the core
failure.** Moving the unchanged requested-goal sentence after all rules changes
25/64 actions. Appropriate goal/consequence/action reversal improves from **2/32
to 6/32** pairs, entirely in anonymous conditions. Native true-effect utility
stays **0/16**, and no context/assignment passes both goals in both option orders.
The native reference gate still fails. Formal E0 remains blocked.

Goal information is behaviorally active: the anonymous opening bias weakens, while
native choices increasingly track the gripper wording. With the goal last, **all
16 native opening requests select RELEASE**, including all eight shifted-effect
cases where RELEASE explicitly carries closing consequences. This supports
presentation-dependent goal binding to the wrong action meaning as a candidate
mechanism, alongside unresolved goal-conditioned consequence integration. It does
not identify an internal attention process or prove that lexical matching alone
explains the remaining anonymous failures.

## Exact intervention and matched controls

Original state order:

```text
The drawer is currently partly open. The requested state is closed.
Nominal moves are intents. ... [all original rules, ending in the STOP rule]
```

Intervention order:

```text
The drawer is currently partly open.
Nominal moves are intents. ... [all original rules, ending in the STOP rule]
The requested state is closed.
```

These line breaks illustrate order only; actual strings retain single spaces.
The open-goal sentence is moved identically. No sentence is duplicated or reworded.
The STOP rule retains its **original closed-then-open clause order**. Every other
state byte, question, option identity/order/description, effect assignment, physical
identity, history and evaluation field remains unchanged. Independent reconstruction
inverts every sentence move exactly. Full token multisets, counts and option-marker
positions are equal in all 64 pairs; state token order changes as intended.

Laya receives question/options before state. This tests the goal's later position
within state, not reduced distance from the option list. It cannot isolate recency,
relative position or attention as internal mechanisms.

All 64 frozen full-effect fixtures: four boundaries (init 0/1/2 step 48, init 0
step 140), native/anonymous descriptions, true/shift-four assignments, closed/open
goals and original/reversed option order. Eleven actual actions and their archived
eight-control/0.4-second outcomes are unchanged. These are sentence projections,
not full CDS. Opening is a counterfactual local objective at closing-task states.

Reran **all 64 unchanged originals and 64 moved-goal fixtures twice: 256 calls**.
Original/moved pairs are interleaved, alternating first position by fixture index;
repeat two reverses the full traversal. Every original also has an archived exact
control. Complete preflight records precede inference. Laya bytes, loaded config,
CUDA/bfloat16, seed one, adapter and eleven-option temperature
`0.10058280825614929` match the baseline. No response retry, fallback or reranking.

Qwen was not run. Complete same-provider controls resolve the placement contrast;
another provider would not isolate the remaining Laya wording interaction. Laya
remains primary rather than making provider comparison the research objective.

## Useful choices and supplied facts

All counts below use first repeats. Repeats match exactly. The variants are
correlated finite cases, not independent episodes or population success rates.

| Descriptions / effects | Supplied-fact correct, original → moved | Actual local utility, original → moved |
|---|---:|---:|
| Native / true | 0/16 → 0/16 | **0/16 → 0/16** |
| Native / shifted | 3/16 → 2/16 | 0/16 → 0/16 |
| Anonymous / true | 9/16 → 11/16 | **9/16 → 11/16** |
| Anonymous / shifted | 9/16 → 11/16 | 1/16 → 3/16 |

Local utility remains >0.25 mm absolute AND >0.25 mm beyond STOP progress in the
requested direction, with the existing obstacle criterion. Shifted-fact consistency
is distinct from physical usefulness. Across true effects only, actual utility
rises **9/32 → 11/32**. Pooled fact correctness rises **21/64 → 24/64**, comprising
seven corrections and four regressions. These aggregates do not establish a reference.

| Descriptions / assignment | Closing correct, original → moved | Opening correct, original → moved |
|---|---:|---:|
| Native / true | 0/8 → 0/8 | 0/8 → 0/8 |
| Native / shifted | 3/8 → 2/8 | 0/8 → 0/8 |
| Anonymous / true | 1/8 → 3/8 | 8/8 → 8/8 |
| Anonymous / shifted | 1/8 → 4/8 | 8/8 → 7/8 |

All three anonymous true closing successes use **reversed options**, at step 48
of init 0/1/2. Original-order true closing remains 0/4. Init 0/140 true closing
fails under both orders. The three unflagged transformed choices are these rotation
successes; **61/64** transformed choices retain controller contract flags. No flag
is waived. All source obstacle flags are false, so obstacle discrimination remains
untested; unflagged finite probes are not a deployment certificate.

## Does goal reversal produce appropriate effect and action reversal?

| Paired goal criterion | Original | Goal last |
|---|---:|---:|
| All action identities change | 11/32 | 21/32 |
| Both goals correct, closing → opening bundle, with changed action | **2/32** | **6/32** |
| Native action identities change | 9/16 | 12/16 |
| Native appropriate consequence/action reversal | **0/16** | **0/16** |
| Anonymous action identities change | 2/16 | 9/16 |
| Anonymous appropriate consequence/action reversal | **2/16** | **6/16** |

The six successful pairs split equally between true and shifted assignments. Five
are newly successful and one old success is lost. No boundary/assignment has correct
goal reversal under both option orders. Thus the causal gain is real but fragile;
counting changed actions would overstate it substantially.

Example: init 0/48, anonymous true effects, reversed options previously selects
MV_LEFT for both goals. Goal last selects ROTATE_CCW for closing and MV_LEFT for
opening, matching the supplied and measured consequences. The same boundary still
fails true closing with original options, and its shifted goal-reversal pairs fail.

## Effects, directional bias and candidate wording

| Effect-reassignment criterion | Original | Goal last |
|---|---:|---:|
| All action identities change | 25/32 | 18/32 |
| Both assigned fact bundles followed correctly | **8/32** | **8/32** |
| Native action identities change / both correct | 10/16 / 0/16 | 3/16 / 0/16 |
| Anonymous action identities change / both correct | 15/16 / 8/16 | 15/16 / 8/16 |

Anonymous paired reassignment gains one closing success and loses one opening
success: both-correct closing **0/8 → 1/8**, opening **8/8 → 7/8**. Moving effects
still changes 15/16 anonymous identities. Effect use remains active, but reliable
combination of goal and assigned consequences is not restored.

Anonymous opening-bundle selections fall **30/32 → 22/32**, comprising closing-goal
inputs **14/16 → 7/16** and opening-goal inputs **16/16 → 15/16**. Closing bundles
rise 2/32 → 7/32; three moved choices are mixed/neutral. This is partial appropriate
goal sensitivity rather than merely a wholesale switch to a closing bias.

Supplemental returned probability mass also separates by goal under anonymity.
For true effects, mean closing-bundle mass changes **0.199 → 0.392** under a closing
request and **0.077 → 0.019** under an opening request. This is evidence of directional
redistribution, not calibrated task-success probability.

Native behavior differs sharply. Placement changes 15/32 native choices and 10/32
anonymous choices. Native opening requests select RELEASE **6/16 → 16/16**; its
description is `open grip; hold pose`. Under shifted effects all eight such choices
carry `opening decreases; vs STOP lower`, the opposite of the requested drawer
goal. Mean closing-bundle mass on those native shifted opening requests rises
**0.478 → 0.929**. Native true opening also picks RELEASE in all eight cases, where
it is a STOP alias and supplies no incremental goal progress.

This locates an observable failure more precisely than "goal ignored": a salient
opening request increasingly chooses an action described as opening the gripper,
even against explicit drawer consequences. In native shifted conditions four goal
pairs actually reverse presented direction **open → closed** when the request
changes **closed → open**. A lexical or action-meaning shortcut is a hypothesis,
not a measured internal mechanism. Full anonymity still does not cure all failures.

Option-order sensitivity persists: all action changes under option reversal rise
18/32 → 21/32, while both orders correct fall 9/32 → 8/32. Anonymous changes rise
8/16 → 13/16. Native/anonymous wording changes 29/32 moved-goal identities; only
one pair is correct under both descriptions. Wording and order remain consequential.

## Integrity and hypotheses

All **256 calls** are valid and unclipped, at **301–344 tokens**. All **128 repeat
comparisons** match choices, returned probabilities and raw scorer logits exactly.
All **128 unchanged-control calls** exactly reproduce their archived counterparts,
including logits/probabilities. All model-facing inputs match preflight, actual
consumed tokens match audit, and raw argmax/probability reconstruction passes.
No failures or unmatched intents occurred. Existing archived failures remain intact.

| Explanation | Evidence update |
|---|---|
| Goal placement has no meaningful behavioral effect | Weakened: 25 action changes, partial anonymous goal-reversal gain and probability redistribution. |
| Early goal placement alone explains the failure | Rejected on these fixtures: native utility stays zero and reassignment correctness does not improve. |
| The goal is simply ignored | Inadequate: anonymous choices partly reverse appropriately; native opening requests systematically choose RELEASE. |
| Native gripper wording competes with drawer consequences | Strengthened as a specific hypothesis by RELEASE selection despite opposite shifted consequences; selective causal test remains pending. |
| A fixed opening preference explains every failure | Weakened: anonymous bias decreases, while native shifted opening requests consistently select closing bundles. |
| Randomness, clipping, changed settings or mismatched inputs explain the contrast | Not supported by complete token audits, exact repeats, all archived controls and hashes. |
| Complete effect blindness or a missing physical field is the needed explanation | Still unsupported: reassignment affects anonymous choices and the finite local predicate has complete supplied facts. |

The strongest current account is **unreliable task-goal-to-consequence integration,
with placement-dependent competition from candidate descriptions**. Native grip
wording now provides a concrete candidate mechanism; anonymous residual errors and
order dependence prevent reducing the whole failure to that mechanism. Current-state
wording and conditional-rule interpretation remain unseparated alternatives.

Useful bounded native manipulation reference: **NO**. Scientifically defensible
full manipulation reference: **NO**. CDS/no-effect sufficiency: **UNESTABLISHED**.
Formal E0: **BLOCKED**. Neither this privileged effect-use diagnostic nor the older
finite status result substitutes for the intended no-effect State Gap reference.

## Single highest-information next experiment

Test **selective removal of GRASP/RELEASE wording** on Laya: keep goal-last state,
all rules, actual option identities/order and supplied effects fixed; replace only
their nominal description prefixes (`close grip; hold pose` and `open grip; hold
pose`) with the already tested anonymous prefix `intervention`. Leave the other
nine nominal descriptions unchanged. Compare with matched native controls across
both goals, assignments and orders, with repeats and full raw audits.

This targets the new 16/16 native opening→RELEASE pattern. If those two descriptions
drive the failure, their removal should reduce RELEASE selection against supplied
facts and improve appropriate goal/consequence/action reversal across assignments.
Mere identity change would not suffice. Persistence would weaken this specific
gripper-wording explanation and favor a broader integration limitation. The test
also retains the acknowledged wording/length limitation of anonymization; it would
not identify an internal lexical mechanism or create a new physical policy.

This recommendation follows the new description interaction, rather than extending
the earlier rule-order/goal-position sequence. It is **not run**. No provider search,
new state fields or broader prompt sweep is recommended.

## Artifacts and verification

Added [goal_placement.py](../embodied_runtime/experiments/goal_placement.py), 25
focused test cases, protocol and handoff. The module reuses existing frozen-source,
inference recorder, raw validation and numeric evaluation functions. Every previous
working Python source remains unchanged. No dependencies or model bytes changed.

Ignored local evidence:

- `runs/goal-placement/preflight-v01/`: exact design, full input token audits,
  manifests/configuration, zero inference calls and independent transformation audit.
- `runs/goal-placement/laya-v01/`: all 256 calls, full strings/token sequences,
  raw logits/probabilities, manifest/configuration and raw-derived `report.json`.
- `runs/goal-placement/audit.py` and `audit.json`: independent raw-response scoring,
  goal/assignment/order/description contrasts and disaggregated probability masses.
- `runs/goal-placement/matched_pairs.csv`: all 128 repeated placement contrasts,
  identities, directions, correctness, physical utility and contract flags.

The independent audit recomputes support directly from numeric source effects and
the raw chosen option, then checks the reusable reporter. Existing physical evidence
remains in the sibling reference-pilot archive. Share ignored evidence with source;
a fresh clone alone is not a reproducible evidence bundle.

| Identity | SHA-256 |
|---|---|
| Raw inference records | `4f55a7e7bb193fe6856e36c9cfad1179c4bbbd24724dd2ca7605e72a697932cf` |
| Preflight records | `e3f34f10d9f2903fe7c62da7e9abf7072fa3c1380c2b030a31bdc1a0d0d12ad6` |
| Module at inference | `5cf96962cb0d1d811d982025dac53912ddc160617338297f6516fc7c5a57855a` |
| Protocol | `516820dc74d30ba8c25ed6ef6b813059649b2abac695b56c090b98623b13d1e6` |
| Independent audit | `e0ecc35eac47807e1ba9865e7a84008c7c46d15be488400ef81b93bedd2ecc35` |
| Matched pairs | `157b09f042c5918d6e083d5f646c99987dd8828df4b86b1a77d6cc05a5935be7` |

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
# These are the executed paths; reproduction must use fresh directories.
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.goal_placement --preflight runs/goal-placement/preflight-v01
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.goal_placement --output runs/goal-placement/laya-v01 \
  --preflight-source runs/goal-placement/preflight-v01
$P -m embodied_runtime.experiments.goal_placement --summarize runs/goal-placement/laya-v01
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Verification: **75 focused tests and 319 full tests pass**, ruff and compileall
pass. Raw-report reproduction and independent scoring pass separately. Environment
unchanged: Python 3.10.21, torch 2.2.0, transformers 4.57.3, NumPy 1.26.4, laya 0.3.4.
The demo worktree and shared reviewed integration branch were not modified.
