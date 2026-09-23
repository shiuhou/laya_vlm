# Complete local effects still do not establish a useful reference

2026-09-23. Research branch `research/decision-interface`, baseline
`eddbcde04649419d8d5d44e62e433882578328eb`, with working-source hashes in the run
manifest. [Predeclared protocol](effect_binding_protocol.md). No formal E0.

## Finding

The strongest current explanation is a **stable model/interface competence
failure in selecting consequences conditional on the goal**, compounded by
candidate presentation and independently demonstrated loaded-action semantics.
Missing perceptual state is real, but cannot by itself explain these failures.
Even when supplied all facts needed for a narrow, independently evaluable local
decision, the current checkpoint does not reliably select a supported action.
This identifies a failing checkpoint/presentation pairing, not an internal model
mechanism or proof that every representation or provider would fail.

Removing native descriptions changes behavior and improves some counts, but the
apparent anonymous-option success is predominantly an opening-direction bias.
Adding the previously omitted STOP comparison does not rescue native choices.
There is still **no useful manipulation reference and no readiness for E0**.

## Investigation and controls

Read the state/track/architecture/research documents, the reference gate and
mechanism reports, candidate/executor semantics, raw-record/token audit code and
relevant tests. The initial 244-test suite passed. Reconstructed all four previous
gate suites from raw responses, and regenerated all 106 prior fixtures exactly
from their original sources. Their published results reproduce.

The new experiment uses the same four previously selected loaded boundaries:
init 0/1/2 step 48 and init 0 step 140, seed 1. Their complete eleven-action,
eight-control counterfactuals already exist. No simulator or perception was rerun.
Source validation retains full candidate sets, pair identities, equal horizons,
restoration checks and contract flags. No physical state was settled or filtered.

A fixed factorial crosses native/anonymous descriptions, absolute/full-relative
effects, true/shifted effect assignments, closed/open goals and original/reversed
option order, with two repeats: **128 fixtures, 256 calls**. Eleven options and
the checkpoint's temperature bucket remain fixed. Current articulation, question,
objective and horizon are matched across description/effect interventions. The
shift moves the entire fact bundle four indices while preserving actual action
identities. These intentionally false assignments test reading supplied facts;
they are never scored as valid physical predictions.

Absolute facts say `opening decreases/increases/unchanged`. Full facts additionally
say `vs STOP lower/higher/same`, referring to final opening after the same 0.4 s.
Categories use the existing strict +/-0.25 mm thresholds and are goal-independent.
Each candidate retains its measured obstacle flag. No rank, recommended action or
goal-dependent utility label enters inference. Native descriptions use the existing
compact meanings; anonymous descriptions use `intervention` for each option.
This ablation changes wording and length, so it does not isolate a particular
internal attention mechanism.

The full facts are sufficient to evaluate the **declared local predicate**:
goal-directed absolute change >0.25 mm, goal-directed change beyond STOP >0.25 mm,
and no new sampled/endpoint obstacle contact. For every full/true fixture and all
eleven actions, the factual predicate equals the independent numeric evaluator.
This is a finite information-sufficiency check, not a universal state claim or a
precomputed winning action. All these states are partly open and all their
candidate obstacle flags are false; obstacle discrimination is untested.

Privileged oracle consequences enter only these explicitly labeled offline
diagnostic prompts. They do not enter visual belief, perceptual replay or a live
policy. This is an effect-use capability test, **not** a State Gap experiment or
a formal oracle-versus-nonprivileged Effect Gap comparison.

## Results

First-repeat counts below each cover 4 states × 2 goals × 2 orders = 16 inputs.
Second repeats are identical. These are correlated contexts, not 16 independent
episodes; no population success rate follows.

| Descriptions | Effects | Assignment | Consistent with supplied facts | Actual local support |
|---|---|---|---:|---:|
| Native | Absolute | True | 3/16 | 2/16 |
| Native | Absolute | Shifted | 2/16 | 1/16 |
| Native | Absolute + STOP | True | **0/16** | **0/16** |
| Native | Absolute + STOP | Shifted | 3/16 | 0/16 |
| Anonymous | Absolute | True | 7/16 | 6/16 |
| Anonymous | Absolute | Shifted | 11/16 | 2/16 |
| Anonymous | Absolute + STOP | True | **9/16** | **9/16** |
| Anonymous | Absolute + STOP | Shifted | 9/16 | 1/16 |

For absolute-only inputs, supplied-fact consistency tests direction/obstacle only;
it does not penalize missing STOP information. Actual utility always uses the full
numeric predicate. Shifted consistency and actual utility must remain separate.
The new fixed question/context differs from the prior gate; this is not an exact
replication of its native absolute prompt.

The anonymous full-effect count does **not** establish goal-sensitive competence:

- True assignment: open **8/8**, closed **1/8**. The choice is identical under
  opposite goals in **7/8** matched state/order pairs. Only one pair is correct
  under both goals. Original order scores 4/8 overall; reversed scores 5/8.
- Shifted assignment: supplied-fact consistency is again open **8/8**, closed
  **1/8**, with the same-choice result in **7/8** goal pairs.
- Across those 32 anonymous full-effect inputs, **30 choices select the presented
  `increases / higher` fact bundle**, regardless of the requested goal.
- Moving effects changes the anonymous full-effect action identity in **15/16**
  matched inputs and changes probabilities in all 16. The selected opening
  direction stays the same in 14/16. This weakens both total effect insensitivity
  and a fixed option-ID explanation; effects affect which option is selected,
  but goal-conditioned selection remains inadequate.

Native full-effect choices are GRASP/RELEASE/STOP in 15/16 cases, with one MV_UP.
Both option orders score zero. At init 0 step 48, RELEASE is selected for the
closed goal despite the explicit `vs STOP same` fact: +0.253 mm closure, zero
incremental contribution. At init 0 step 140, reversed-order GRASP is selected
for the closed goal despite `opening increases; vs STOP higher`: it reopens by
14.272 mm, 21.261 mm worse than STOP. These fail even the information supplied.

All **128 repeat comparisons** have identical choices, returned probabilities and
raw logits. All 256 token audits match consumed inputs, with **246–344 tokens**,
no clipping, failures or unmatched intents. Actual CUDA/bfloat16 and checkpoint
content match the prior gate. The 11-option temperature is `0.10058280825614929`;
it cannot explain between-condition argmax differences because it is fixed and
order-preserving.

Every native full/true choice is contract-flagged. Eight of nine anonymously
supported full/true choices are also flagged. Local progress is not a waiver of
the reset-calibrated execution envelope or evidence of safe deployment.

## Hypotheses after this test

| Hypothesis | Evidence-supported update |
|---|---|
| Perceptual geometry/missing contact alone explains failure | Weakened as a complete explanation: known outcomes make predicting contact/dynamics unnecessary for this local choice, yet it fails. Their importance to no-effect planning remains unresolved. |
| Missing STOP-relative information alone explains failure | Rejected for these native fixtures: supplying it yields 0/16 and exposes explicit contradictions. It was a genuine omission in the old evaluator/input comparison. |
| Native candidate wording interferes | Supported at fixed option count: full true facts yield 0/16 native versus 9/16 anonymous. Wording/length and checkpoint interactions are not separately identified. |
| Removing native semantics establishes competence | Rejected here: anonymous closing is 1/8 and seven goal-reversal pairs keep the same action. |
| The model ignores effects entirely | Weakened: reassignment changes 15/16 anonymous full-effect choices; the model frequently follows the same presented direction to a different identity. |
| Stochastic instability, clipping, temperature or decoding explains the errors | Unsupported in this run: repetitions, consumed tokens and logits/argmax checks pass; temperature is fixed. Presentation sensitivity is distinct from same-input stochastic instability. |
| Loaded action semantics are misleading | Still supported independently: inherited controller objectives and STOP drift remain in archived probes. This cannot explain failing to select among supplied actual consequences. |
| CDS v0.1 needs an arbitrary larger field list | Not established. No field sufficiency claim can follow from agreement with this unqualified reference. |

The narrow known-state DONE/CONTINUE/UNKNOWN findings remain intact. They are not
an atomic manipulation expert. Nor do these local action failures rule out every
long-horizon preparatory policy; the new prompts explicitly requested local effects.

## Single next experiment

Replay the **frozen full-effect eleven-option fixtures with one independently
selected DecisionProvider**, keeping logical state, strings, candidates, true/false
bindings, goals, order, repeats and evaluator fixed. Audit that provider's complete
input and output identities; do not tune prompts or choose the provider based on
these outputs. The current Laya run is the matched comparison.

A provider that passes all native true-effect choices and the goal/binding controls
would support a bounded effect-conditioned reference and locate a limitation in
the present checkpoint/presentation pairing. Failure would leave provider and
representation competence unresolved, not prove that more physical state is needed.
Either outcome is more discriminating than adding untested CDS fields now. A pass
would still require independent physical validation and would not qualify the
no-effect reference or authorize formal E0.

## Reproduction and provenance

Added `experiments/effect_binding.py`, nine focused tests and this dated protocol/
handoff. Updated research/index/architecture/track pointers. No shared runtime,
schema, executor, gate, model weights, dependency or upstream repository changes.
Preflight found no clipping; no wording adjustment or further prompt search occurred.

New local evidence in this worktree:
`runs/effect-binding/factorial-v01/{manifest.json,resolved_config.yaml,episodes.jsonl,report.json,audit.json}`.
Source evidence remains in the sibling
`/home/junhongli/projects/laya-embodied-runtime/runs/reference-pilot/` and
`runs/reference-gate/`. These ignored artifacts are not included in a fresh clone.
The raw fixtures preserve source hashes, physical/task/init/seed identities, actual
action mappings, numeric outcomes and contract flags; the manifest hashes every
working Python source. Share the source records with the run for independent audit.

| Identity | SHA-256 |
|---|---|
| New raw records | `3875a25255eeb7880e1168579567758f68d616d39a023cc28c1ddef3e0c5eea5` |
| Model content | `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704` |
| Diagnostic module at inference | `49592aed7ac9c1d472a1092d2493db3f39a8c090e2b96ed589721cb5ea5c2e09` |
| Source init 0 raw | `d24b0d3d1d73c7618f69bb806168a719301e5806ddf6b68fec2dcc1e3e6a8b58` |
| Source init 1 raw | `95dc765928d5af123035a248efc7a89a6d590079d927ee59f8524e0c3d07432a` |
| Source init 2 raw | `41d07e9c6ed5db0bc28404ba5856ae71338981935852a12ef2aed180679ac1a5` |

All 128 new fixtures regenerate exactly. `report.json` is reproduced by the
summary command; `audit.json` records prior fixture regeneration and matched
goal/assignment contrasts derived from the raw-linked report. No cached model
analysis rows are trusted. Runtime: Python 3.10.21, NumPy 1.26.4, torch 2.2.0,
transformers 4.57.3, laya 0.3.4.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.effect_binding \
  --pilot-root /home/junhongli/projects/laya-embodied-runtime/runs/reference-pilot \
  --output runs/effect-binding/factorial-v01
# Use a fresh output directory for another run; never overwrite this evidence.
$P -m embodied_runtime.experiments.effect_binding \
  --summarize runs/effect-binding/factorial-v01
$P -m pytest -q tests/test_effect_binding.py tests/test_reference_gate.py tests/test_interface_search.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Verification: **34 focused tests and 253 full tests pass**; ruff and compileall
pass. Raw inference and fixture regeneration pass independently of those tests.
