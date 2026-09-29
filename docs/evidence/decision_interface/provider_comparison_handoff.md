> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Goal-conditioned reference failure persists under an independent provider

2026-09-23. Research branch `research/decision-interface`, baseline `eddbcde`,
with working-source identities in the manifests. No E0, schema change or robot
execution. [Predeclared protocol](provider_comparison_protocol.md).

## Decision

**Outcome (2) is best supported for the frozen full-effect presentation.** The
failure is not confined to the current Laya pairing. Independently selected
Qwen2.5-7B-Instruct improves native useful choices from 0/16 to 8/16 but fails
goal reversal and the predeclared reference gate. Anonymous choices remain strongly
biased toward opening under both providers. Neither establishes a reliable useful
reference on all the frozen local decisions. **Formal E0 remains blocked.**

This points toward a shared problem in the presentation of the requested goal and
conditional effect-selection instructions, with provider-dependent candidate-wording
interference. It does not identify a specific internal model mechanism, prove that
all providers fail, or establish a need for additional physical state. All facts
needed for the declared finite local predicate are already supplied. Loaded action
semantics remain a separate physical limitation, not an explanation for choosing
against the stated actual effects.

## Controlled comparison and provider choice

Selected **Qwen/Qwen2.5-7B-Instruct**, public revision
`a09a35458c702b33eeacc393d103063234e8bc28`, before any new inference. It is a general
instruction model supported by the installed Transformers and fits one available
24 GiB GPU in bfloat16. Local inventory contained Laya, rule/replay baselines and
the specialized LocateAnything model, but no independent general decision
checkpoint or configured API credentials. Rule/replay would substitute a policy;
the modified localization decoder was unsuitable as a general decision comparator.
Only this one independent model was acquired and evaluated, without screening
providers on these fixtures. Its four weight hashes match the pinned repository.

The provider change includes architecture, training, tokenizer and output adapter:
Laya uses a ModernBERT-based typed scorer; Qwen uses a causal instruction model.
Conclusions concern the **provider/checkpoint/adapter pairing**, not weights alone.

Read all and only the 64 full-effect fixture records from the accepted, hashed
effect-binding archive, retaining their original fixture IDs and payload hashes.
Ran two repeats, with reversed traversal on repeat two: **128 new calls**, compared
with the corresponding 128 archived Laya calls. No new Laya or simulator calls.

Matched conditions:

- Init 0/1/2 step 48 and init 0 step 140, seed 1; identical physical and source-state
  identities, previously restored eleven-action counterfactuals and 0.4 s horizons.
- Identical state text, requested goal, question, all eleven candidate identities,
  nominal descriptions, absolute/STOP-relative facts, obstacle flags and empty history.
- Both native/anonymous descriptions, true/shift-four fact assignments, closed/open
  goals and original/reversed option orders, compared within the same condition.
- The same independent numeric utility criterion: >0.25 mm absolute AND >0.25 mm
  STOP-relative goal progress, plus the existing sampled obstacle rule. False
  assignments are scored for supplied-fact consistency separately from reality.

**Scope correction:** the frozen fixtures use a short sentence projection, not the
full CDS v0.1 serialization. Their original source state/pair linkage is retained;
no CDS fields were added or removed. The comparison is valid on that frozen
effect-conditioned interface. It does not test full CDS or no-effect sufficiency.
This is an explicitly privileged offline provider comparison, not a formal State
Gap or Effect Gap experiment; no consequences enter perceptual/no-effect replay.
Opening is a counterfactual local objective at archived closing-task states, not
a newly collected opening rollout or a test of long-horizon optimality.

The Qwen transport preserves question, options, then state in Laya's logical order.
All original strings and ordered option mappings survive. Its native chat template
adds only the system instruction:

> Return exactly one option ID from the supplied options, with no other text.

This implements the output contract without new task guidance, examples, evaluator
labels or recommendations. Model-specific chat framing/tokenization differs from
Laya's typed markers and is recorded, not concealed as an identical byte sequence.
Greedy decoding, batch one, seed one, CUDA/bfloat16, SDPA, 16-token maximum; no
constrained decoding, output reranking, response retries or fallback. No question
or prompt was adjusted after observing model outputs.

## Useful choices and supplied-fact consistency

Each row uses first-repeat counts over 4 boundaries × 2 goals × 2 orders = 16.
Second repeats are identical. These are correlated contexts, not independent
episodes or population success rates.

| Descriptions / effects | Laya: facts / actual utility | Qwen: facts / actual utility |
|---|---:|---:|
| Native / true | 0/16 / 0/16 | **8/16 / 8/16** |
| Native / shifted | 3/16 / 0/16 | **9/16 / 2/16** |
| Anonymous / true | 9/16 / 9/16 | **8/16 / 8/16** |
| Anonymous / shifted | 9/16 / 1/16 | **8/16 / 3/16** |

Actual utility under intentionally false effects is not the criterion for following
those effects; the two columns must not be pooled. Qwen's native true-condition
utility by boundary is init 0/48 **1/4**, init 1/48 **3/4**, init 2/48 **3/4**, and
init 0/140 **1/4**. No boundary passes both goals and orders.

All 64 first-repeat Qwen choices retain execution-contract flags, including every
locally useful choice. These flags are not waived by the local progress score.
All candidate obstacle flags in this source subset are false; obstacle avoidance
competence remains untested.

## Goal reversal, reassignment and order

| Qwen condition | Closing: supplied facts | Opening: supplied facts | Goal pairs with both choices correct |
|---|---:|---:|---:|
| Native / true | 2/8 | 6/8 | 2/8 |
| Native / shifted | 3/8 | 6/8 | 1/8 |
| Anonymous / true | **0/8** | **8/8** | **0/8** |
| Anonymous / shifted | **0/8** | **8/8** | **0/8** |

Across the 32 goal-reversal pairs, Qwen changes identity in **9/32**, and both
choices are correct in only **3/32**. All these pairs require different choices
because their supported sets are disjoint. Laya changes 11/32, with both correct
in 2/32. A changed action is not evidence of appropriate goal sensitivity.

For effect reassignment at fixed goal/order/context:

- Qwen changes native choices in **9/16** pairs, with both choices consistent with
  their presented facts in **5/16**.
- Anonymous choices change in **16/16**, with both consistent in **8/16**, all
  opening-goal cases. Thus binding is demonstrably influential, but not reliably
  combined with the requested goal.
- Combined: changes in **25/32**, both fact-consistent in **13/32**. Twenty pairs
  have disjoint supported sets and require a change; the others can legitimately
  retain an identity. Laya changes 25/32, with both fact-consistent in 8/32.

Across Qwen's 32 anonymous true/shifted inputs, **29 choices select the presented
`opening increases / vs STOP higher` bundle**. The remaining three select decrease
with same/higher opening than STOP; none select decrease/lower. Laya selects the
increase/higher bundle in 30/32. This shared asymmetry is stronger evidence than
the aggregate approximately-half-correct count.

Reversing option order changes Qwen's identity in **22/32** matched pairs; both
orders are correct in only 12/32. Some changes could be valid ties, but others
reverse useful progress. At init 1/48, closed goal, native true effects:

| Order | Choice | Actual closure | Closure beyond STOP | Useful |
|---|---|---:|---:|---|
| Original | MV_DOWN | +0.509 mm | +0.552 mm | Yes |
| Reversed | MV_UP | −0.526 mm | −0.483 mm | No |

At init 0/140, closed goal, original-order Qwen chooses GRASP despite the supplied
increase/higher facts: **−14.272 mm closure, −21.261 mm versus STOP**. Reversed order
chooses RELEASE: +6.989 mm closure but **zero** beyond STOP. These are explicit
failures of the supplied criterion, not a penalty for unknown physics or an
unobserved preparatory strategy; the question requests the local effects.

## Validity and stability

All **128 outputs are valid option IDs**, every generation ends with EOS after
four tokens, and every fixture repeats with identical generated IDs, choices and
full vocabulary logits. **64/64 repeat comparisons match exactly.** There are no
inference failures, unmatched intents, truncations or response substitutions.

All 64 recorded presentations exactly match the pre-inference audit and frozen
logical payloads. Qwen consumes 321–378 prompt tokens; forward hooks verify the
complete initial prompt and subsequent generated-token inputs. Raw-logit argmax
matches every greedy generated token, and independent decoding reproduces every
recorded text. Tokenizer/config hashes match the inference manifest. Every Python
source present during the prior effect-binding run remains byte-identical.

Full next-token vocabulary logits are saved in 128 hashed `.npz` artifacts, about
0.133 GiB compressed. They are **not** an eleven-option probability distribution;
the record explicitly leaves option probabilities unavailable. Do not compare
Qwen token probabilities with Laya's calibrated option probabilities. The raw model
output is preserved before any parsing/evaluation.

## Updated hypotheses and next experiment

| Explanation | Update |
|---|---|
| Failure is exclusive to Laya's provider/checkpoint pairing | Weakened decisively on this presentation: a separately selected instruction model also fails the gate, although native performance improves. |
| Native descriptions alone cause the problem | Insufficient: anonymous Qwen still fails every closing-goal case. |
| Effects are ignored | Rejected as a complete explanation: all 16 anonymous reassignment pairs change identity, and all eight opening pairs track the supplied facts correctly. |
| More physical fields or STOP-relative effects alone are needed | Not supported as a remedy here: the required local facts and requested goal are already present on both providers. Full CDS sufficiency remains untested. |
| Random instability, clipping, bad decoding or mismatched fixtures | Not supported: complete audited inputs, strict outputs, pinned weights, raw argmax checks and exact repeats all pass. |
| Shared goal/instruction presentation interferes with consequence selection | Strengthened by cross-provider opening bias and failed opposite-goal pairs. Exact mechanism is unresolved; two providers do not establish universal impossibility. |

**Single next experiment:** reverse only the two clauses in the **final STOP-rule
sentence**, retaining the actual requested-goal sentence, all candidate/effect
facts, state, question, history and provider settings. Compare this one alternative
with the frozen original on both existing providers, preserving all goals, bindings,
option orders and repetitions. No new fields or task-specific winning-action code.

Original: `... lower opening than STOP for closed, or higher opening than STOP for open.`
Control: `... higher opening than STOP for open, or lower opening than STOP for closed.`

Both convey the same rule. If selected direction follows the last rule clause
instead of the unchanged requested goal, this would causally implicate instruction
ordering. If it does not, that specific recency hypothesis is weakened. The shared
opening bias and the original ending in the opening-goal clause motivate this
test, but **no such causal effect has yet been measured**. Do not treat it as a
validated fix or broaden into prompt search. No additional inference followed the
present comparison. All four observed articulation states are partly open; the
present comparison does not separate rule-order sensitivity from confusion between
current and requested articulation, or other shared presentation effects.

Useful bounded manipulation reference: **NO**. Full CDS sufficiency: **UNESTABLISHED**.
Scientifically defensible full-task reference: **NO**. Formal E0: **BLOCKED**.

## Artifacts and reproduction

New module: `experiments/provider_comparison.py`, an offline choice adapter and
raw-derived reporter; 17 focused tests. It is not wired into the runtime. No changes
to CDS, candidate meanings, controllers, gates, existing model weights, dependencies
or upstream repositories. One new pinned checkpoint was downloaded separately.

Local ignored evidence:

- `runs/provider-comparison/qwen-v01/`: manifest, configuration, raw records, full
  vocabulary logits, `report.json` and independent `audit.json`.
- `runs/provider-comparison/preflight-v01/`: all presentations and baseline audit
  recorded before independent inference.
- `runs/provider-comparison/acquisition-v01/`: slow initial Hugging Face transfer,
  preserved KeyboardInterrupt/failure and partial files, pinned public shard hashes.
- `acquisition-v02/`: resumable HTTP transfer, stopped to increase concurrency;
  interruption and logs preserved. `acquisition-v03/`: completed transfer, four
  successful SHA-256 checks and result record. These are acquisition attempts,
  **not** discarded model trials. There was one model-inference run.

| Identity | Value |
|---|---|
| Frozen Laya raw SHA-256 | `3875a25255eeb7880e1168579567758f68d616d39a023cc28c1ddef3e0c5eea5` |
| Qwen raw SHA-256 | `baf1512634f6a60f74f852ebc3988690555f4af897845dbc930cb81091796dff` |
| Qwen model content ID | `e2b474b2efa21f2dbfc6e6c31de53a54f20eea68942e02d34164526078dc4cf5` |
| Comparison module at inference | `3be6c45e5dca7d08f2357f5fca3a9e6456253b3153cc696599a05e50ad90abf7` |
| Independent audit SHA-256 | `b80aef98d61b2bc2eb013a92833c26d7533fef748793a1652763307d4e39ad3a` |

The manifest includes every working Python source hash and all model/tokenizer
file hashes. Original physical evidence remains in the sibling worktree at
`/home/junhongli/projects/laya-embodied-runtime/runs/reference-pilot/`. The unchanged
effect-binding archive retains those source hashes and physical identities. Share
these ignored evidence files and logits alongside the code for independent audit;
a fresh clone does not contain them.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.provider_comparison \
  --source runs/effect-binding/factorial-v01 \
  --output runs/provider-comparison/qwen-v01
# Use a new output directory for another run; existing evidence is never overwritten.
$P -m embodied_runtime.experiments.provider_comparison \
  --summarize runs/provider-comparison/qwen-v01
$P -m pytest -q tests/test_provider_comparison.py tests/test_effect_binding.py tests/test_interface_search.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Environment unchanged: Python 3.10.21, torch 2.2.0, transformers 4.57.3, NumPy 1.26.4,
laya 0.3.4. Verification: **41 focused and 270 full tests passed**, ruff and
compileall passed. Raw report, presentation equality, pinned shard identities and
repeat stability are verified separately from unit tests.
