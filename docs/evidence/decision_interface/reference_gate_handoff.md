> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# A paired missing-information result, not a manipulation E0

2026-09-23. Baseline `a7da3d8`. Protocol:
[reference_gate_protocol.md](reference_gate_protocol.md). No formal E0/E1 or tag.

## Decision after reviewing the evidence

The atomic reference remains unvalidated: Stage 4's GRASP/RELEASE choices, loaded
action semantics, failed quantitative/goal-reversal controls, and the later
minimal-interface search do not support a useful manipulation reference. The
prior successful DONE/CONTINUE mapping supports a **narrow known-state task-status
reference**, with independent cabinet predicates. Its perceptual articulation
field is missing, not noisy or merely stale.

We therefore ran a three-boundary paired **missing-information** pilot, and
separately tested the outstanding consequence-use hypothesis. The former gives
an interpretable input intervention; the latter fails the physical reference gate.
Do not call either a completed formal manipulation benchmark.

## 1. Matched status pilot: what changed and why

Same archived top-drawer init 0 / seed 1 boundaries, checkpoint, question, candidate
meanings/order, rendering and empty history/effects on each comparison. Only the
observed-articulation phrase changes. No new image, estimate or simulator state
was generated. The candidate outputs are status judgments, never atomic STOP.

Oracle category uses archived **before.qpos_m**: open if < -.14 m, closed if > 0 m,
otherwise intermediate. Close labels agree with the native physical success flag.
Perceptual `progress.remaining_open_mm` is explicitly unknown; the projection
refuses to invent an articulation estimate from target XYZ or oracle state.

```text
Oracle:     The drawer is currently open. The requested state is closed.
Perceptual: The drawer is currently unknown. The requested state is closed.

Question: Does the observed drawer state satisfy the requested goal?
A: DONE: goal satisfied
B: CONTINUE: goal not satisfied
```

Representative original-order results (the second repeat is identical):

| Boundary / pair prefix | Oracle current state | Oracle choice / P(DONE) | Perceptual choice / P(DONE) | JS, nats |
|---|---|---|---|---:|
| 0 / `a99f0c0ae6f3` | open; qpos −.151659 m | CONTINUE / .4437 | DONE / .5891 | .010620 |
| 48 / `80a7b0d86ac8` | partly open; qpos −.113550 m | CONTINUE / .4350 | DONE / .5891 | .011928 |
| 155 / `85f0072fedaf` | closed; qpos +.001157 m | DONE / .6281 | DONE / .5891 | .000798 |

All oracle known-state judgments are correct in both option orders and repeats.
The missing-state input returns DONE in both orders (.5891/.5565). These are modest
probabilities, not calibrated certainty. The API act probability nevertheless
equals 1.0. No status output is executed or used as a termination predicate.

For each physical boundary, a third branch masks only the oracle articulation to
unknown. Its payload hash, consumed input and output probabilities match the
perceptual branch. This is the causal check: the flip is reproducible from that
single field's missingness, not model stochasticity, candidate mismatch, effects,
camera referent error or a changed goal. All three perceptual inputs collapse to
the same sentence; agreement at the terminal boundary does **not** demonstrate
that the model detected completion from the image.

Scope: 3 physical pairs × 3 branches × 2 option orders × 2 repeats = **36 calls**.
These are correlated trajectory boundaries, not independent episodes. We do not
score unknown inputs as inaccurate articulation measurements; there is no estimator.
The result is about **information availability and response to missingness**, not
RGB-D accuracy or generalization across initial states.

### Is the binary output part of the problem?

A separately declared diagnostic adds `C: UNKNOWN: current state unavailable`.
State sentences and question remain unchanged. The three known inputs and one
unique unknown input, two orders, two repeats give **16 calls**.

| Input | Original-order choice | Returned probabilities |
|---|---|---|
| open → requested closed | CONTINUE | DONE .3034, CONTINUE .3773, UNKNOWN .3193 |
| partly open → requested closed | CONTINUE | .3108, .3784, .3108 |
| closed → requested closed | DONE | .5943, .2085, .1972 |
| unknown → requested closed | UNKNOWN | .3062, .2623, .4315 |

All four choices remain correct under reversed order and repetition. This supports
an **answer-space limitation** in the binary interface; input missingness alone
did not provide an adequate abstention mechanism. It is not an implemented fix or
proof of robust uncertainty handling. Three options change the checkpoint's
temperature bucket, so cross-vocabulary probability magnitudes are not comparable.
The act/defer head still reports 1.0: explicit UNKNOWN is a typed response, not
abstention by that head.

## 2. Can consequence information establish a manipulation reference?

First, a predeclared two-intervention capability test crosses open/close goals,
effect-to-action assignments and option orders, with two repeats. Future facts
are explicitly synthetic, not physical predictions or sensor evidence.

| Consequence presentation | Correct unique contrasts |
|---|---:|
| Numeric −5/+5 mm opening change in a state-side table | 4/8 |
| Opening decreases/increases in that table | 4/8 |
| Same direction facts attached to candidate descriptions | **8/8** |
| Hypothetical terminal closed/open outcomes attached to descriptions | 4/8 |

Total **64 calls**. The terminal-outcome control has a different horizon/information
content; it is not an equivalent precision variant. No recommended action, score
or rank enters these inputs. Candidate-local placement helps on the elementary
direction task; this suggests a fact-to-option binding/presentation issue, not
proof of an internal model mechanism or of general planning ability.

### Transfer to actual archived consequences

Because one representation passed the finite gate, we tested four independently
chosen bidirectional contact contexts: init 0/1/2 step 48 and init 0 step 140.
Each has all eleven native 0.4-second counterfactuals and verified restoration.

All eleven identities remain offered with neutral IDs and fixed nominal semantics.
The current-state sentence (partly open) and requested goal are held fixed across
no-effects, true-effects and cyclically misassigned-effect conditions. True facts
are goal-independent opening-change categories and measured obstacle flags,
attached to candidate descriptions; exact numeric outcomes stay in the evaluator.
The .25 mm category threshold comes from the existing rubric, not model tuning.

Four states × two goals × three effect conditions × two option orders × two
repeats = **96 calls**. Opening is a counterfactual local goal, not a new successful
opening trajectory. These calls intentionally include privileged future facts and
are **not primary no-effect State Gap comparisons**.

Results per original/reversed order, each covering eight state/goal cases:

| Effects | Locally supported choices, original / reversed |
|---|---:|
| None | 0/8, 0/8 |
| True | 0/8, 1/8 |
| Misassigned | 0/8, 1/8 |

Useful local support requires >.25 mm actual goal-directed movement **and**
>.25 mm beyond STOP, with the existing no-new/endpoint-obstacle-contact check.
It is not a safety certificate or proof of long-horizon optimality.

Representative true-effect selections:

| State / goal / order | Choice | Actual closure | Closure beyond STOP | Interpretation |
|---|---|---:|---:|---|
| init 0/48, close, original | RELEASE | +.253 mm | 0 | Directionally consistent, but STOP alias / no incremental contribution |
| init 1/48, close, original | RELEASE | −.043 mm | 0 | No useful goal progress; effect category unchanged |
| init 0/140, close, original | RELEASE | +6.989 mm | 0 | Large movement is shared drift, not selected-action benefit |
| init 0/140, close, reversed | GRASP | −14.272 mm | −21.261 mm | Wrong physical direction despite true effect facts |
| init 0/140, open, reversed | GRASP | −14.272 mm | −21.261 mm | Locally supported opening; same choice under opposite goal prevents reference qualification |

Important abstraction limitation: absolute sign categories collapse weak drift and
strong active progress into the same phrase. The input does not explicitly expose
the evaluator's STOP-relative quantity. A directionally consistent RELEASE choice
is therefore **not by itself evidence of model incompetence**; the coarse effects
cannot distinguish all actions the evaluator distinguishes. Nevertheless, only
3/16 true-effect choices even match the supplied goal-direction categories, so
that mismatch does not explain all failures. Some goal reversals are unambiguously
wrong even under the information actually supplied.

All selected physical actions retain reset-envelope flags in these loaded states;
none are hidden or used to silently prune candidates. Misassignment often leaves
coarse categories tied, so unchanged choices are not proof that effects are ignored.
The synthetic-to-physical transfer changes option count, native descriptions and
context together: it does not isolate which causes the transfer failure.

**The predeclared physical reference gate fails.** No outcome-conditioned
oracle/perceptual manipulation replay follows, and no further prompt search was
performed. Correct simulator-derived direction facts in this tested representation
do not establish a useful eleven-action reference. This does not establish that effects are useless
or that a richer observation schema is necessarily required.

## Research implications and next smallest step

1. A bounded paired result is now attributable to **missing articulation plus a
   binary answer vocabulary**, with an exact field-masking control. It is not
   perception error or a result about task success. For the status component, an
   explicit unknown response deserves independent validation, including unseen
   language/boundaries and an actually sensor-derived articulation estimate.
2. For manipulation, stop before E0. The next discriminating test should hold
   **eleven options fixed** while isolating native action-description effects
   from consequence binding. Separately represent absolute and STOP-relative
   change if incremental utility remains the objective. Do not insert preferred
   actions or call a precomputed policy an effect estimator.
3. Preserve State Gap / Effect Gap separation. The status pairs have no effects.
   The consequence tests hold current state fixed and intentionally change
   prospective evidence. No single aggregate disagreement score mixes them.

These tests establish neither the necessity nor the general sufficiency of future
effects for manipulation. Current state suffices for the tested status judgment;
the failed action reference cannot adjudicate what a competent policy would need.

Known-state status reference: **supported only for the tested finite interface**.
Sensor-derived articulation estimator: **absent**.
Useful atomic manipulation reference: **NO**.
Ready to freeze/run formal manipulation E0: **NO**.

## Reproduction, artifacts and repository changes

`experiments/reference_gate.py` adds the small offline suites and raw-only report.
`interface_search.py` now explicitly propagates effect-presence metadata into the
shared recorder; old no-effect fixtures retain their identities. No deployment
CDS, executor, candidate gates, covariance, tracking or threshold changes.

Artifacts under ignored `runs/reference-gate/`:
`status-v01`, `consequences-v01`, `abstention-v01`, `physical-v01`.
All completed, **212 calls / 106 repeat comparisons**, identical repeated choices,
probabilities and raw logits. Actual consumed tokens match audits; no clipping
(47–228 tokens), no missing intents or failures. All calls used CUDA/bfloat16 and
the same local checkpoint content ID:
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.

Source pairs/probes remain in `runs/reference-pilot/init{0,1,2}-raycast-v02/`.
Fixture records contain source hashes, physical/task/init/seed identities and pair
IDs; status fixtures also link the perceptual belief. Source files and prior
invalid/truncated artifacts were not changed. New manifests preserve working-code
hashes; this was not a frozen-release collection.

Runtime: Python 3.10.21, NumPy 1.26.4, torch 2.2.0, transformers 4.57.3,
laya 0.3.4. No new simulator execution, vision inference, dependency changes or downloads.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.reference_gate --suite status \
  --output runs/reference-gate/status-v01
# Same command for suites consequences, abstention, physical, with corresponding fresh output.
$P -m embodied_runtime.experiments.reference_gate --summarize runs/reference-gate/status-v01
$P -m embodied_runtime.experiments.reference_gate --summarize runs/reference-gate/physical-v01
$P -m pytest -q tests/test_reference_gate.py tests/test_interface_search.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Verification: **25 focused tests; 236 full tests passed in 4.86 s; lint and compileall passed**.
Final recheck: 25 focused and 236 full tests passed (4.83 s full suite). All 106
fixture records regenerate identically from their source artifacts, and every
suite passes the raw-response, token-consumption and repeat-coverage audit.
