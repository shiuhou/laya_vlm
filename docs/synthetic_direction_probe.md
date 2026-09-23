# Minimal synthetic direction capability probe

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized follow-up to the
[translation-only diagnostic](frozen_step0_translations_only.md).
Exactly six typed-choice calls: one each for +X, -X, +Y, -Y, +Z and -Z.
No MuJoCo, LIBERO, archived task state, CDS input, execution or E0.

The subsequent [negative-direction ordering diagnostic](synthetic_negative_order_probe.md)
corrects two of the three negative-case failures by swapping complete candidate
pairs alone. It establishes a substantial ordering contribution and updates the
attribution below; the original six-call results remain unchanged.

**Three of six top-1 choices are correct; none of the three opposite-direction
pairs reverses correctly.** All positive-axis cases pass. All negative-axis
cases select the opposite, positive-axis movement. The target sign affects the
probabilities in the expected direction, but not enough to change any winner.
This is partial axis/sign sensitivity, not reliable signed-direction grounding.

## Complete synthetic input

The API state is a plain string. For the first case it is exactly:

```text
The target is 100 mm in the +X direction from the hand.
```

The other cases substitute only `-X`, `+Y`, `-Y`, `+Z` or `-Z` for `+X`.
Within each opposite-direction pair, exactly one character changes: `+` to `-`.
The fixed 100 mm distance makes a 10 mm approach unambiguously closer without
overshooting. It is a manually constructed synthetic fact, not observed geometry.

The question has key `action`, type `choice`, and these exact instructions:

```text
Which single movement moves the hand closer to the target?
```

The criteria dictionary contains exactly these entries in this insertion order:

| Candidate | Exact description |
|---|---|
| MV_FWD | Move the hand 10 mm in the +X direction. |
| MV_BACK | Move the hand 10 mm in the -X direction. |
| MV_LEFT | Move the hand 10 mm in the +Y direction. |
| MV_RIGHT | Move the hand 10 mm in the -Y direction. |
| MV_UP | Move the hand 10 mm in the +Z direction. |
| MV_DOWN | Move the hand 10 mm in the -Z direction. |

There are no other state fields, task context, history, effects, examples or
system/conversational instructions. Expected answers appear only in the audit,
outside the model input. All six cases use the same wording, candidate order
and descriptions. No model-output-driven prompt revision, permutation, repeat,
warm-up inference or extra baseline call was made.

The same local typed-decisions checkpoint is used, with content ID
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.
Model/config/tokenizer are unchanged: Laya 0.3.4, CUDA/bfloat16, GPU 6, seed 1,
six-option temperature `1.0000158548355103`. Every input consumes **129 tokens**,
including a 14-token state; headings, option tokens and marker positions match
across all cases. There is no clipping.

## Full distributions and top-1

API probabilities as percentages; bold is top-1. API rounding can make a row
sum differ slightly from 100%. These are selection scores, not physical-success
probabilities. Full raw logits and unrounded reconstructions are also preserved.

| Target direction | MV_FWD | MV_BACK | MV_LEFT | MV_RIGHT | MV_UP | MV_DOWN |
|---|---:|---:|---:|---:|---:|---:|
| +X | **48.08%** | 10.72% | 13.42% | 5.72% | 13.15% | 8.91% |
| -X | **30.94%** | 14.73% | 14.93% | 6.97% | 20.37% | 12.06% |
| +Y | 22.54% | 15.21% | **28.83%** | 8.04% | 14.58% | 10.80% |
| -Y | 22.04% | 12.90% | **23.46%** | 10.67% | 19.53% | 11.40% |
| +Z | 20.55% | 10.20% | 14.20% | 6.47% | **41.04%** | 7.55% |
| -Z | 17.62% | 9.54% | 13.12% | 6.65% | **40.32%** | 12.76% |

Margins below use API probabilities, in percentage points. A negative
correct-minus-best-other margin means the correct action loses.

| Target | Correct action | Top-1 | P(correct) | Correct minus best other, pp | Winner minus runner-up, pp |
|---|---|---|---:|---:|---:|
| +X | MV_FWD | MV_FWD | 48.08% | +34.66 | +34.66 |
| -X | MV_BACK | MV_FWD | 14.73% | -16.21 | +10.57 |
| +Y | MV_LEFT | MV_LEFT | 28.83% | +6.29 | +6.29 |
| -Y | MV_RIGHT | MV_LEFT | 10.67% | -12.79 | +1.42 |
| +Z | MV_UP | MV_UP | 41.04% | +20.49 | +20.49 |
| -Z | MV_DOWN | MV_UP | 12.76% | -27.56 | +22.70 |

## What changes when the target direction reverses?

Every pair keeps the same top-1, hence **0/3 correct reversals**:

| Pair | Expected winner + → - | Observed winner + → - | Positive-action minus negative-action margin, pp |
|---|---|---|---:|
| X | FWD → BACK | FWD → FWD | +37.36 → +16.21 |
| Y | LEFT → RIGHT | LEFT → LEFT | +20.79 → +12.79 |
| Z | UP → DOWN | UP → UP | +33.49 → +27.56 |

The negative-direction candidates do gain preference. All probability changes
below are the negative-target case minus the positive-target case, in pp:

| Pair | MV_FWD | MV_BACK | MV_LEFT | MV_RIGHT | MV_UP | MV_DOWN |
|---|---:|---:|---:|---:|---:|---:|
| +X → -X | -17.14 | +4.01 | +1.51 | +1.25 | +7.22 | +3.15 |
| +Y → -Y | -0.50 | -2.31 | -5.37 | +2.63 | +4.95 | +0.60 |
| +Z → -Z | -2.93 | -0.66 | -1.08 | +0.18 | -0.72 | +5.21 |

Using unrounded probabilities, negative actions' shares within their own axis
pairs increase from **18.228% to 32.253%** for BACK, **21.801% to 31.258%** for
RIGHT, and **15.534% to 24.042%** for DOWN. Thus this probe does not support total
insensitivity to the sign. It shows insufficient sensitivity for the correct
top-1 decision. Winners track the requested axis, but retain its positive sign.

## Ordering and interpretation

**Ordering sensitivity was not independently tested.** Candidate order is fixed
in all six calls. The winning choices occupy positions 1, 3 and 5, each the earlier
member of its axis pair. That pattern is compatible with a within-pair position
preference, label preference or sign-handling limitation; it does not identify
which caused the failure. The choice is not a constant first/last-slot selection,
because the winning position changes with the target axis. No order-invariance
claim follows, and no additional permutation calls were run.

Between the two proposed explanations, this result points primarily toward a
**checkpoint-level signed-direction grounding limitation under the tested simple
presentation**, rather than complexity of the current embodied interface as the
sole blocker. Removing CDS, drawer semantics, uncertainty fields, feedback and
action-family competition still leaves all three negative-direction decisions
wrong. The checkpoint has not passed even this small complete signed-axis test.

This does **not** prove an intrinsic inability under every wording or ordering.
The main unresolved alternative is an interaction between the checkpoint and
the `+X/-X` notation, native action labels or fixed order. The axis-dependent
winners and correctly directed probability changes are evidence of partial
capability. They should not be erased by a claim that the model ignores geometry
entirely. Conversely, 3/6 correct outcomes cannot validate reliable grounding.

This is a bounded engineering capability check, not a research evaluation or a
CDS redesign. Its target direction is given explicitly; even a full pass would
not demonstrate extracting direction from robot/world coordinates, multi-axis
reasoning, contact planning or task competence. No projection or policy that
precomputes an action is installed in the live demo. Historical embodied
connectivity evidence is unaffected.

## Artifacts and verification

Local ignored directory: `runs/engineering-demo/synthetic-direction-probe-v01/`.

- [All six responses, raw logits and consumed token traces](../runs/engineering-demo/synthetic-direction-probe-v01/comparison.json)
- Exact inputs: [+X](../runs/engineering-demo/synthetic-direction-probe-v01/0-plus-x-input.json), [-X](../runs/engineering-demo/synthetic-direction-probe-v01/1-minus-x-input.json), [+Y](../runs/engineering-demo/synthetic-direction-probe-v01/2-plus-y-input.json), [-Y](../runs/engineering-demo/synthetic-direction-probe-v01/3-minus-y-input.json), [+Z](../runs/engineering-demo/synthetic-direction-probe-v01/4-plus-z-input.json), [-Z](../runs/engineering-demo/synthetic-direction-probe-v01/5-minus-z-input.json)
- [Derived metrics and independent verification](../runs/engineering-demo/synthetic-direction-probe-v01/analysis.json)
- [Chained raw records](../runs/engineering-demo/synthetic-direction-probe-v01/episodes.jsonl)
- [Manifest](../runs/engineering-demo/synthetic-direction-probe-v01/manifest.json) and [complete configuration](../runs/engineering-demo/synthetic-direction-probe-v01/resolved_config.yaml)
- [Exact inference runner](../runs/engineering-demo/synthetic-direction-probe-v01/run_probe.py) and [analysis-only verifier](../runs/engineering-demo/synthetic-direction-probe-v01/analyze_probe.py)
- [Console log](../runs/engineering-demo/synthetic-direction-probe-v01.console.log)

Raw JSONL SHA-256:
`d866b11d24b4525de54f59fdc912754f3f039d60a3289dc9ecb64854c8071d13`.

The inference process exited 0. All 18 chained records validate, with exactly six
inputs, outputs and forward traces. Probabilities independently reconstruct from
the saved logits at the unchanged temperature. Matching inputs/order and absence
of clipping are verified. No simulator modules were loaded and no action was
executed. Model bytes and runtime source hashes are unchanged. Report values,
local links and `git diff --check` pass; no runtime tests were rerun for these
documentation/ignored-evidence additions. Existing working changes are preserved.
No shared-component change, live modification, E0, commit or branch change was made.

The saved runner can reproduce the six calls from the repository root using a
fresh output directory; it reads the local checkpoint and no archived task input:

```sh
CUDA_VISIBLE_DEVICES=6 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /home/junhongli/miniforge3/envs/locateanything/bin/python \
  runs/engineering-demo/synthetic-direction-probe-v01/run_probe.py \
  --output runs/engineering-demo/synthetic-direction-probe-v02
```

That reproduction command is provided for collaborators; it was not run as an
additional collection. Ignored artifacts must be shared separately from Git.
