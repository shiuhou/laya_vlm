# Removing grip descriptions exposes an opening bias, not reliable goal binding

2026-09-23. `research/decision-interface`, baseline
`eddbcde04649419d8d5d44e62e433882578328eb`, with working-source hashes.
[Pre-inference protocol](selective_grip_protocol.md). Laya only; no physical
execution, new provider, CDS/perception/effect/controller change or formal E0.

## Decision

**Outcome (2): GRASP/RELEASE descriptions contribute to the failure but do not
explain most of the goal-conditioned binding deficit.** Their joint removal changes
20/32 actions and improves true-effect utility **0/16 → 5/16**, entirely on opening
requests. True closing remains **0/8**. Appropriate goal/consequence/action reversal
improves only **0/16 → 1/16**, with no boundary/assignment passing both goals in
both option orders. The reference gate fails; formal E0 remains blocked.

The previous 16/16 opening→RELEASE pattern disappears, but suppression of gripper
actions is not the explanation: combined GRASP/RELEASE selection barely falls
**28/32 → 26/32**. RELEASE falls **20 → 3**, while GRASP rises **8 → 23**. The
selected supplied consequence is now opening in **25/32** cases, including **12/16
closing requests**. Removing the descriptions resolves many opening-request errors
while leaving a dominant directional preference instead of reliable goal use.

This establishes the joint contribution of the two description prefixes under the
tested intervention. Anonymization also shortens the input by eight tokens; it does
not separately identify lexical meaning, text length or positional attention.

## Exact intervention and controls

Use all 32 **native, goal-last** fixtures from the accepted goal-placement run.
Replace only these nominal prefixes:

| Actual action identity | Original prefix | Intervention prefix |
|---|---|---|
| GRASP | `close grip; hold pose` | `intervention` |
| RELEASE | `open grip; hold pose` | `intervention` |

Each following `; opening ...; vs STOP ...; obstacle ...` suffix is byte-identical.
The other nine descriptions stay exactly native. Neutral model option IDs A00–A10,
canonical mappings and option order are unchanged; action names are not newly
inserted into model text. Goal-last state, original STOP-clause order, requested
goal, physical facts, effects, history, numeric evaluator and physical semantics
are unchanged. Source metadata remains intact; the new presentation condition and
its parent goal-placement intervention are recorded separately.

Four boundaries: init 0/1/2 step 48 and init 0 step 140, seed 1. Cross true/shift-four
effect assignment, closed/open goal and original/reversed option order. All eleven
actual actions retain their archived eight-control/0.4-second outcomes. Opening is
a counterfactual local objective at closing-task states, not a new opening rollout.
These are sentence fixtures, not a validation of full CDS or no-effect sufficiency.

Run **32 native controls + 32 selective variants, each twice = 128 Laya calls**.
Interleave each pair, alternating which comes first by fixture index; reverse the
full traversal on repeat two. All 64 native control calls also compare against their
archived counterparts. Full preflight precedes inference in a separate directory.

Provider is unchanged local Laya typed-decisions, CUDA/bfloat16, seed one set once,
eleven-option temperature `0.10058280825614929`, identical adapter/configuration
and recorded inference environment. No retry, fallback, reranking or prompt search.
No other provider was called. Inputs shorten **344 → 336 tokens** in every pair;
all state/effect text is unchanged and no part is clipped.

## Native versus selective results

First-repeat counts below; all second repeats are exact. These factorial variants
and four archived contexts are correlated, not independent episodes.

| Assignment | Native fact correctness | Selective fact correctness | Native actual utility | Selective actual utility |
|---|---:|---:|---:|---:|
| True | 0/16 | **5/16** | 0/16 | **5/16** |
| Shift-four | 2/16 | **9/16** | 0/16 | 2/16 |

The physical predicate remains >0.25 mm absolute AND >0.25 mm beyond-STOP progress
in the requested direction, with the existing sampled/endpoint obstacle rule.
Shifted facts are intentionally false; following them is distinct from physical
utility. Pooled fact correctness improves **2/32 → 14/32**: 13 corrections, one
regression, one retained success and 17 retained failures. This repairs 12 of 30
baseline errors net, but does not establish goal-conditioned competence.

| Assignment / requested goal | Native facts correct | Selective facts correct |
|---|---:|---:|
| True / closed | 0/8 | **0/8** |
| True / open | 0/8 | **5/8** |
| Shift-four / closed | 2/8 | **1/8** |
| Shift-four / open | 0/8 | **8/8** |

Opening correctness improves across all four boundaries and both assignments.
True useful choices by boundary are **1/4, 1/4, 1/4, 2/4**, respectively; all are
opening-goal choices. Closing correctness does not generalize. Pooled fact scores
by boundary are **1/8 → 3/8**, **0/8 → 3/8**, **0/8 → 3/8**, **1/8 → 5/8**.

All **32/32** transformed first-repeat choices retain execution-contract flags.
Local utility does not waive those flags. All source obstacle flags are false, so
this experiment does not establish obstacle discrimination or execution safety.

## Goal, assignment and order contrasts

| Matched criterion | Native | Selective |
|---|---:|---:|
| Goal reversal changes action | 12/16 | 3/16 |
| Appropriate goal/consequence/action reversal; both goals correct | **0/16** | **1/16** |
| Effect reassignment changes action | 3/16 | 9/16 |
| Both effect assignments followed correctly | **0/16** | **5/16** |
| Option-order reversal changes action | 8/16 | 7/16 |
| Both option orders correct | **0/16** | **5/16** |

**Goal reversal:** 13/16 selective pairs keep the same action. Selected direction
stays opening in 12 pairs and mixed/neutral in three. The sole appropriate reversal
is init 0/140, shifted facts, original order: closing selects RELEASE with assigned
closing facts, opening selects GRASP with assigned opening facts. Its reversed-order
counterpart fails. True-effect goal reversal remains **0/8**; shifted is **1/8**.
Nevertheless all 16 goal pairs change probabilities and raw logits, so this is not
complete goal blindness.

**Effect reassignment:** all five pairs correct under both assignments are opening
requests; closing remains **0/8**. Three step-48 original-order pairs change from
MV_LEFT/MV_UP to GRASP when the opening facts move there. Those supported sets are
disjoint, so these are genuine identity changes tracking supplied facts. The other
two successes, init 0/140 under both orders, retain GRASP; supported sets overlap
and retaining it is legitimate. Do not count every changed identity as successful
binding, or penalize a valid unchanged identity.

**Option order:** all five both-orders-correct pairs are opening requests: four
shifted cases and the true-effect init 0/140 case. Closing remains **0/8**. True-effect
utility is **4/8 original-order versus 1/8 reversed-order**. In the three step-48
contexts, original-order opening choices are useful but reversed-order choices
select mixed/neutral outcomes. No physical boundary/assignment handles both goals
correctly under both orders; no boundary passes all eight goal/assignment/order cases.

## Grip preference and selected effect direction

| First-repeat preference | Native | Selective |
|---|---:|---:|
| RELEASE | 20/32 | **3/32** |
| GRASP | 8/32 | **23/32** |
| GRASP or RELEASE | 28/32 | **26/32** |
| RELEASE under an opening request | 16/16 | **2/16** |
| Mean returned GRASP+RELEASE probability mass | 0.777 | 0.730 |
| Mean returned mass on fact-supported candidates | 0.096 | 0.462 |

The change mostly redistributes preference between gripper candidates instead of
making them unattractive. In shifted opening cases GRASP carries opening facts:
all eight selective choices now choose it correctly. They do not avoid an anonymous
grip action when it has the requested consequences.

However, the same direction dominates closing requests. Selective choices choose
opening bundles in **12/16 closed** and **13/16 open** cases; just one closing bundle
is selected overall, with six mixed/neutral selections. In true-effect cases mean
opening-bundle probability mass is **0.541 for closed** and **0.569 for open** goals.
Mean closing-bundle mass remains only **0.033** under true closing. Probability mass
is descriptive of this fixed scorer, not calibrated physical success probability.

Historical context only: the archived fully anonymous goal-last condition scored
11/16 true utility and 6/16 appropriate goal reversals, versus selective 5/16 and
1/16. No fully anonymous inference was added here. That comparison cautions against
attributing all description interference to the two gripper prefixes; it does not
isolate the remaining nine descriptions or eliminate length/position confounding.

## Hypotheses and scientific gate

| Hypothesis | Update |
|---|---|
| The two descriptions have no meaningful influence | Weakened: 20/32 choices change, 13 errors are corrected, and the opening→RELEASE pattern largely disappears. |
| These two descriptions explain the core goal-conditioned deficit | Weakened: true closing stays 0/8, only one goal pair succeeds, and no context generalizes across both orders. |
| Improvement is merely avoidance of GRASP/RELEASE | Rejected here: combined selection remains 26/32, with correct reassigned facts frequently followed to GRASP. |
| Effects are ignored or choices are a fixed action identity | Inadequate: three disjoint-set opening reassignment pairs change identity correctly; other choices also respond to assignment. |
| Removing the two prefixes restores useful goal binding | Rejected on the tested fixtures. Opening preference largely replaces the previous RELEASE preference. |
| Random instability, clipping, changed model/configuration or evaluator explains the contrast | Not supported by exact repeats/controls, full token audits, unchanged settings and source hashes. |
| Additional physical state is required for this local predicate | Unsupported: the necessary factual consequences remain supplied; missing fields are not the demonstrated problem. |

The strongest explanation is **partial competition from native descriptions plus
an unresolved failure to select supplied consequence direction according to the
requested goal**. Effects influence identity and goal information influences scores,
but their reliable combination is missing. The residual opening preference is a
behavioral description, not proof of its internal cause. Conditional-rule use,
goal-to-direction interpretation and remaining presentation interactions remain
unseparated. This intervention cannot identify word meaning independently of its
eight-token shortening, or separate GRASP from RELEASE contributions.

Scientifically defensible useful manipulation reference: **NO**. Selective finite
reference gate: **FAIL**. Full CDS/no-effect sufficiency: **UNESTABLISHED**.
Formal E0: **BLOCKED**. State Gap and Effect Gap remain separate; these privileged
effects do not enter perceptual/model inputs outside the labeled offline diagnostic.

## Single highest-information next experiment

Keep the selective goal-last fixtures fixed and change **only the generic question**
to state the required consequence conjunction explicitly:

- Closed goal: `Choose an intervention with opening decreases, vs STOP lower, and obstacle no.`
- Open goal: `Choose an intervention with opening increases, vs STOP higher, and obstacle no.`

Compare with the current generic question on the same Laya checkpoint, candidates,
goals, true/shifted facts, orders, rules and evaluator, with matched repeats/controls.
Do not change state or effects, and do not provide a winning action ID, ranking or
candidate-specific utility label.

This asks whether Laya can select the correct candidate **when the desired physical
consequence is explicitly specified**, now that removing gripper descriptions
mainly exposed a goal-insensitive opening preference. Success across both directions
and reassigned effects would locate a limitation in mapping the requested drawer
goal through the conditional rules. Persistent failure would instead implicate
selecting/binding the supplied effect conjunction itself. It deliberately supplies
the intermediate goal-to-direction predicate; a pass would not demonstrate that
the original goal-binding interface or a no-effect policy is competent.

This recommendation is **not run**. It is one diagnostic question intervention,
not an instruction to broaden prompt search, change providers or redesign CDS.

## Evidence, implementation and validation

New [selective_grip.py](../embodied_runtime/experiments/selective_grip.py) and
[20 focused test cases](../tests/test_selective_grip.py) reuse the existing recorder,
token/raw-output validators, frozen sources and numeric evaluators. Every previous
Python source, including goal_placement.py, remains byte-identical. No shared live
runtime, dependency, checkpoint, branch or other worktree was modified.

Ignored local artifacts:

- `runs/selective-grip/preflight-v01/`: 64 exact presentations, token audits,
  model/config/source identities, zero inference calls and independent prefix audit.
- `runs/selective-grip/laya-v01/`: all 128 raw calls, complete state/questions/token
  sequences, logits/probabilities, manifest/configuration and raw-derived report.
- `runs/selective-grip/audit.py`, `audit.json`: independent scoring directly from
  raw chosen options and numeric effects, with all factorial contrasts and grip mass.
- `runs/selective-grip/matched_pairs.csv`: all 64 repeated native/selective contrasts.
- `runs/selective-grip/verification.json`: report reproduction and final provenance checks.

All **64/64 repeat pairs** match choices, returned probabilities and raw logits.
All **64/64 unchanged controls** reproduce the archived outputs exactly. Actual
consumed tokens match preflight; raw argmax/probability reconstruction passes. No
failures, missing outputs or unmatched intents occurred. Historical failed attempts
remain preserved. The independent numeric audit agrees with the reusable reporter.

| Identity | SHA-256 |
|---|---|
| Goal-placement source raw | `4f55a7e7bb193fe6856e36c9cfad1179c4bbbd24724dd2ca7605e72a697932cf` |
| New raw calls | `032444bf8fe439e6ac2a84a7e0f7a4c59b760fc64ab5e00bceab28e74b628ad6` |
| Preflight raw | `58a7f89a1a446d12493f967f757b0c79c1798d9ef3ea990b17c8fee501df7cb8` |
| Module at inference | `b978cff9d1e26f9b551e66db2cf80f70a915bd639617d185191cad7cb6f04d99` |
| Protocol | `a4e20cd81475850ee941023a5610916051678977f134b26244b3fdce93c7e3b4` |
| Independent audit | `637f7b7cf8d0dcd6d5f3b636a3bf55eacda273f109cc956aa2f4f90334d9abc7` |
| Matched-pair CSV | `08dc97cc1a333213e7e0ced54d496ea5c91d87c3f11bef7cb959cd0ea284bc5c` |

Laya content ID remains
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.
Physical provenance remains linked through the unchanged goal-placement/effect-binding
archives to the sibling reference-pilot records. Share these ignored artifacts with
the code; a fresh clone does not contain the evidence.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
# Executed paths shown; reproduction must use fresh directories.
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.selective_grip --preflight runs/selective-grip/preflight-v01
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.selective_grip --output runs/selective-grip/laya-v01 \
  --preflight-source runs/selective-grip/preflight-v01
$P -m embodied_runtime.experiments.selective_grip --summarize runs/selective-grip/laya-v01
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Validation: **95 focused and 339 full tests pass**; ruff and compileall pass.
Environment unchanged: Python 3.10.21, torch 2.2.0, transformers 4.57.3,
NumPy 1.26.4, laya 0.3.4. No additional experiment followed this result.
