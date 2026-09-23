# Explicit consequence criteria leave candidate matching unreliable

2026-09-23. `research/decision-interface`, baseline
`eddbcde04649419d8d5d44e62e433882578328eb`, with working-source hashes.
[Pre-inference protocol](explicit_consequence_protocol.md). Laya only; offline
diagnostic, no physical execution, new provider, CDS/perception/effect/controller
change or formal E0. Continue from [selective grip](selective_grip_handoff.md).

## Decision

**Outcome (3): explicit consequence criteria do not materially help.** They change
only **2/32 choices**, with no corrected errors and one lost success. True-effect
utility falls **5/16 → 4/16**; true closing stays **0/8**. Appropriate paired
goal/consequence/action reversal remains **1/16**. Selected opening consequences
still dominate **24/32**, including **12/16 closing requests**. The finite matching
gate fails. No useful manipulation reference exists; formal E0 remains blocked.

This weakens an **upstream-only goal-to-desired-consequence explanation**. Supplying
that intermediate predicate is insufficient: desired-consequence-to-candidate
matching itself remains unreliable in this presentation. It does not establish
that upstream goal interpretation is competent, or identify an internal mechanism.

## Exact intervention and matched control

Change only `questions.action.instructions` on all 32 frozen selective-grip,
goal-last fixtures:

| Condition | Exact question |
|---|---|
| Unchanged control | `Choose an intervention for the requested goal.` |
| Explicit closing criterion | `Choose an intervention with opening decreases, vs STOP lower, and obstacle no.` |
| Explicit opening criterion | `Choose an intervention with opening increases, vs STOP higher, and obstacle no.` |

These conjunctions are derived from `effect_binding.effect_facts` and
`presented_support`: more than 0.25 mm absolute progress AND more than 0.25 mm
progress beyond the STOP endpoint, in the requested direction, with no measured
sampled/endpoint obstacle violation. Independent parsing of every candidate suffix
agrees with the numeric predicate. No winning identity, ranking, utility label or
new physical fact is supplied. No `criteria` entry changes.

The complete state, goal-last sentence, decision rules and STOP-clause order are
byte-identical within pairs. Selectively anonymous GRASP/RELEASE prefixes, nine
native descriptions, neutral A00–A10 option IDs, physical action mappings, order,
effects, history and evaluator remain unchanged. Full parent lineage is retained.
Inputs increase **336 → 344 tokens** in every pair; no clipping. This isolates the
question field, not semantic specificity independently of its eight-token increase.

Four boundaries: init 0/1/2 step 48 and init 0 step 140. Cross true/shift-four effects,
closed/open goals, original/reversed option order. Eleven actual actions retain
archived eight-control/0.4-second outcomes. Opening remains a counterfactual local
objective at closing-task states, not a new opening rollout. These sentence fixtures
do not validate full CDS or no-effect sufficiency.

**32 unchanged selective controls + 32 explicit variants, each twice = 128 calls**.
Interleave pairs, alternate the first condition by fixture index, reverse the whole
traversal on repeat two. Compare all 64 controls to the selective-grip archive.
Separate full preflight precedes inference. No retry, fallback or prompt search.

Unchanged local Laya typed-decisions, CUDA/bfloat16, CUDA_VISIBLE_DEVICES=1, seed
one set once, eleven-option temperature `0.10058280825614929`, identical adapter,
loaded configuration and recorded inference environment. Checkpoint content ID:
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.

## Direction-specific results

First repeats only; all second repeats exactly match. These are correlated
factorial variants of four archived contexts, not independent task episodes.

| Assignment / request | Control facts correct | Explicit facts correct | Control actual utility | Explicit actual utility |
|---|---:|---:|---:|---:|
| True / closing | 0/8 | **0/8** | 0/8 | **0/8** |
| True / opening | 5/8 | **4/8** | 5/8 | **4/8** |
| Shift-four / closing | 1/8 | **1/8** | 0/8 | **0/8** |
| Shift-four / opening | 8/8 | **8/8** | 2/8 | **1/8** |

Supplied-fact correctness is **14/32 → 13/32**: 13 retained successes, 18 retained
failures, one regression, no corrections. Shifted effects are intentionally false;
following them is distinct from actual usefulness. The two changed actions are:

- Init 0/48, true/open/original: MV_LEFT → GRASP. The supplied direction changes
  opening → mixed/neutral; a useful choice becomes incorrect. Probability on the
  sole supported candidate MV_LEFT falls **0.5123 → 0.3673**.
- Init 0/140, shifted/open/reversed: GRASP → MV_DOWN. Both have supplied opening
  consequences, so fact correctness is preserved. Actual physical utility is lost
  because MV_DOWN's real effects differ from the deliberately reassigned effects.

No closing-request action changes. Pooled correctness by boundary becomes
**2/8, 3/8, 3/8, 5/8**, compared with **3/8, 3/8, 3/8, 5/8** in controls.
True utility is **0/4, 1/4, 1/4, 2/4**. No boundary passes all assignments/goals/orders,
and no boundary/assignment handles both goals under both orders.

All **32/32** explicit first-repeat selections retain execution-contract flags.
Local numeric utility does not waive these flags. All frozen obstacle flags are
false; this experiment cannot establish obstacle discrimination or safe execution.

## Reversal, reassignment and option order

| Matched criterion | Control | Explicit |
|---|---:|---:|
| Goal reversal changes action | 3/16 | **5/16** |
| Appropriate goal/consequence/action reversal; both correct | 1/16 | **1/16** |
| Effect reassignment changes action | 9/16 | **9/16** |
| Both effect assignments followed correctly | 5/16 | **4/16** |
| Option-order reversal changes action | 7/16 | **7/16** |
| Both option orders correct | 5/16 | **5/16** |

**Goal reversal:** both goals correct remains **0/8 true, 1/8 shifted**. The sole
appropriate reversal is unchanged: init 0/140, shifted effects, original order,
RELEASE with supplied closing facts → GRASP with supplied opening facts. Its
reversed-order counterpart fails closing. Eleven explicit goal pairs retain the
same identity. Direction stays opening in eleven pairs and mixed/neutral in three;
one switches opening → mixed/neutral and one closing → opening. Merely increasing
action changes from three to five does not improve goal-conditioned competence.
All 16 goal pairs nevertheless change logits/probabilities, so this is not complete
insensitivity to the requested direction.

**Reassignment:** both assignments correct is **0/8 closing, 4/8 opening**. Two
step-48 original-order cases (init 1/2) correctly switch MV_UP → GRASP when the
opening consequences move; their supported sets are disjoint. Thus some selections
genuinely follow facts instead of a fixed identity. The init-0/48 equivalent loses
its true-effect success. Two init-0/140 pairs pass with overlapping supported sets:
original order retains GRASP; reversed order switches GRASP → MV_DOWN. The latter
switch is valid but not required to follow facts. Nine identity changes alone would
overstate reliable effect matching.

**Option order:** both orders correct remains **0/8 closing, 5/8 opening**: all
four shifted opening contexts plus the true-effect init-0/140 context. True-effect
utility is **3/8 original versus 1/8 reversed**, compared with control 4/8 versus
1/8. Seven identity changes include valid within-supported-set changes; they are
not all errors. Nevertheless correctness remains order-dependent, including the
only successful closing case. No useful improvement generalizes across directions.

## Consequence and identity preferences

| Measurement | Control | Explicit |
|---|---:|---:|
| Selected opening consequence | 25/32 | **24/32** |
| Selected opening consequence under closing request | 12/16 | **12/16** |
| Selected closing consequence | 1/32 | **1/32** |
| Selected mixed/neutral consequence | 6/32 | **7/32** |
| GRASP / RELEASE choices | 23 / 3 | **23 / 3** |
| Mean returned mass on fact-supported candidates | 0.462 | **0.409** |
| True closing: mean mass on closing consequences | 0.033 | **0.019** |
| True closing: mean mass on opening consequences | 0.541 | **0.572** |

All 32 question interventions change raw logits and returned probabilities, despite
30/32 unchanged choices. This is not a zero-effect manipulation, but it does not
improve the required consequence selection. Probability changes under the fixed
scorer are not calibrated physical-success probabilities. The unchanged opening
preference on closing requests is stronger evidence than the pooled count alone.

## Causal interpretation and gates

| Hypothesis | Update |
|---|---|
| The missing operation is exclusively task goal → desired consequence | Weakened: directly supplying the predicate leaves closing at 1/16 and appropriate reversal at 1/16. |
| Explicit criteria restore reliable consequence → candidate selection | Rejected for this exact criterion and frozen presentation. The finite gate fails. |
| Downstream matching/selection also fails | Strengthened: supplied desired effects still lose to contrary or mixed/neutral effects. |
| Failure is merely aggregate imbalance or a fixed action identity | Inadequate: report is split by direction, and two disjoint-set reassignment pairs correctly move identity with facts. |
| Goal/effect information has no influence | Not supported: both change scores; some effect reassignments change identity appropriately. |
| Instability, clipping, changed provider/configuration/evaluator explain the result | Not supported by exact controls/repeats, consumed-token audits and source hashes. |
| More physical state is needed to determine the local predicate | Unsupported: every required value is already supplied and independently matches the numeric evaluator. |

Strongest explanation: **an unresolved downstream selection deficit remains even
when the desired consequence is explicit**, alongside the previously established
description interference. Upstream goal interpretation may also fail; this result
does not absolve it. Recognizing whether one bundle satisfies the conjunction versus
ranking eleven competing candidates is still unseparated. Remaining descriptions,
option identities/positions and criterion wording may interact. One failed explicit
wording does not establish failure under every possible presentation, or prove a
particular internal attention/lexical mechanism.

Scientifically defensible useful manipulation reference: **NO**. Explicit finite
matching gate: **FAIL**. Original goal-binding interface/full CDS/no-effect
sufficiency: **UNVALIDATED**. Formal E0: **BLOCKED**. State Gap and Effect Gap stay
separate; privileged effects remain confined to labeled offline diagnostics.

## Single highest-information next experiment

**Candidate-by-candidate predicate verification.** With the same explicit desired
conjunction and unchanged candidate description/effect strings, ask Laya whether
each individual bundle satisfies that conjunction, using two neutral answer IDs
for `satisfies` and `does not satisfy`. Test every existing bundle under both desired
directions and both true/reassigned provenance conditions; reverse answer order and
repeat. Keep the state/rules, model and numeric predicate fixed. Predeclare this as
a separate binary diagnostic; selecting one displayed candidate is not the answer,
and no positive/negative label is included in its input.

This follows the present result: making the target explicit barely changes ranked
choices, yet affects every score distribution. Verification tests whether the
required conjunction can be recognized without competition among eleven actions.
Correct verification with failed eleven-way selection would support a bottleneck
in selection among candidates; direction-specific verification failures would
locate a deficit already in recognizing predicate satisfaction. Because the response
format/task is simpler, success would not by itself identify an internal cause or
validate the original interface. Preserve all candidates in the diagnostic coverage,
including wrong-direction and mixed/neutral bundles; account for answer imbalance
and both answer orders. Do not turn these judgments into a controller or an expert.

**Recommended, not run.** No further prompt search, provider comparison or physical
experiment followed this result.

## Evidence and validation

New [explicit_consequence.py](../embodied_runtime/experiments/explicit_consequence.py)
and [23 tests](../tests/test_explicit_consequence.py), reusing the existing recorder,
token/raw-output validators, numeric evaluator and matched-call analysis. All previous
Python sources remain byte-identical. No shared runtime, dependencies, checkpoint,
branch or sibling worktree was modified.

Fresh local ignored artifacts:

- `runs/explicit-consequence/preflight-v01/`: all 64 presentations/token audits,
  source/model/config/protocol identities; zero calls; independent one-field and
  text-versus-numeric predicate audit.
- `runs/explicit-consequence/laya-v01/`: 128 full raw calls, logits/probabilities,
  actual consumed tokens, manifests/configuration and raw-derived `report.json`.
- `runs/explicit-consequence/audit.py` / `audit.json`: independent numeric scoring
  from raw responses, directions, probability mass and all factorial contrasts.
- `runs/explicit-consequence/matched_pairs.csv`: all 64 repeated control/explicit pairs.
- `runs/explicit-consequence/verification.json`: report reproduction, source,
  protocol, model and configuration checks.

All **64/64 repeat pairs** match choices, probabilities and raw logits. All **64/64
unchanged controls** reproduce their archive exactly. Raw argmax/probability
reconstruction and actual-consumed-token checks pass; independent numeric scoring
agrees with the reusable reporter. No inference failures, missing outputs, unmatched
intents or clipping. Historical failures/evidence remain preserved. Share ignored
artifacts with the code; they are not present in a fresh clone.

Source selective raw SHA-256:
`032444bf8fe439e6ac2a84a7e0f7a4c59b760fc64ab5e00bceab28e74b628ad6`.
New raw SHA-256:
`d4e58fce0d961594090cf4124942e90cd6c044824951429d8ea8ee22e57acb0c`.
Preflight raw SHA-256:
`7ead92e0fb1a3f260576ed8b3d9872abca3d1bc4efd871249d6481584a866307`.
Remaining file hashes are recorded in `verification.json` and the manifests.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
# Executed paths shown; reproduction must use fresh directories.
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.explicit_consequence --preflight runs/explicit-consequence/preflight-v01
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.explicit_consequence --output runs/explicit-consequence/laya-v01 \
  --preflight-source runs/explicit-consequence/preflight-v01
$P -m embodied_runtime.experiments.explicit_consequence --summarize runs/explicit-consequence/laya-v01
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Validation: **118 focused and 362 full tests pass**; ruff and compileall pass.
Sandboxed GPU discovery and a full-suite Numba cache access failed; rerunning with
the required external access succeeded without configuration/source changes.
These were environment-access issues, not discarded model trials. Python 3.10.21,
torch 2.2.0, transformers 4.57.3, NumPy 1.26.4, laya 0.3.4 remain unchanged.
