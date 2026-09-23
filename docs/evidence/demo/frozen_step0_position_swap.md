> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Frozen step-0 position swap

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized follow-up to the [decision autopsy](decision_autopsy.md).
Exactly two Laya calls in one model session; zero executed actions or simulator steps.

The subsequently authorized [geometry diagnostic](frozen_step0_geometry_sensitivity.md)
holds the original presentation fixed and tests the ambiguity identified here.

**The winner changes from GRASP to MV_BACK.** Exchanging only the complete
MV_FWD and GRASP entries changes the ranking substantially. GRASP loses 15.55
percentage points; MV_FWD loses 0.54 points despite moving to the last position.
MV_BACK, still the second option, gains 7.60 points and becomes top-1.

This supports a **partial position/order contribution** to the original failure,
large enough to change the decision. It does not support a pure “choose the last
option” rule or a transfer of GRASP's probability to whichever token occupies
its old slot. Order is a causal contributor in this pair; position alone is not
a complete explanation of the action preference. A content-independent fixed
option-slot preference would retain the winning slot, which this pair does not.

## Exact intervention and invariants

The original call reconstructs step 0 of
`runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/` from raw input record
15 and response record 16, using the canonical candidate array to recover order.
The archived recorder alphabetizes object keys; that is not the consumed order.

```text
Original: MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN,
          ROTATE_CW, ROTATE_CCW, STOP, GRASP
Swapped:  GRASP, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN,
          ROTATE_CW, ROTATE_CCW, STOP, MV_FWD
```

The moved entries remain exactly `MV_FWD: world +X 10mm` and
`GRASP: close grip; hold pose`. Every key/description pair, state value, serialized
state byte, instruction, history, effect and candidate membership is unchanged.
Both calls have ten options, 591 consumed tokens, no truncation, and temperature
`1.0000158548355103` (`choice:6-10`). The consumed heading and state token spans
are identical; all option blocks contain identical tokens under the permutation.

The same local checkpoint, tokenizer, configuration, installed Laya source and
CUDA/bfloat16 inference path are used. All checkpoint files, including weights,
match the original manifest hashes. GPU 6 is the same physical RTX 4090 used for
the source episode. No warm-up, retry, repeated condition or extra inference call
was made. The original call's complete API response and captured forward trace
(input IDs, markers, option logits and act logits) exactly match the archive.

## Complete returned distributions

Probabilities below are the API's four-decimal outputs, displayed as percentages;
deltas are percentage points. The swapped rounded probabilities sum to 99.99%
because of rounding. These are not calibrated physical-success probabilities.

| Candidate | Original position → swapped | Original | Swapped | Change, pp |
|---|---|---:|---:|---:|
| MV_FWD | 1 → 10 | 10.07% | 9.53% | -0.54 |
| MV_BACK | 2 → 2 | 7.19% | **14.79%** | +7.60 |
| MV_LEFT | 3 → 3 | 9.39% | 11.77% | +2.38 |
| MV_RIGHT | 4 → 4 | 6.38% | 7.21% | +0.83 |
| MV_UP | 5 → 5 | 9.67% | 12.00% | +2.33 |
| MV_DOWN | 6 → 6 | 8.97% | 11.29% | +2.32 |
| ROTATE_CW | 7 → 7 | 5.59% | 6.99% | +1.40 |
| ROTATE_CCW | 8 → 8 | 4.94% | 6.44% | +1.50 |
| STOP | 9 → 9 | 8.94% | 6.66% | -2.28 |
| GRASP | 10 → 1 | **28.86%** | 13.31% | -15.55 |

The swapped winner's margin over GRASP is only 1.48 percentage points. API
entropy-based confidence falls from .0686 to .0183; `act_probability` remains 1.0.
The total variation distance between the reconstructed unrounded distributions
is .1836841. That is descriptive of this pair, not a statistical population result.

Raw option scores change beyond just redistribution by the softmax denominator:

| Candidate | Original logit | Swapped logit |
|---|---:|---:|
| MV_FWD | .392578125 | .263671875 |
| MV_BACK | .05615234375 | .703125 |
| MV_LEFT | .322265625 | .474609375 |
| MV_RIGHT | -.064453125 | -.014892578125 |
| MV_UP | .3515625 | .494140625 |
| MV_DOWN | .27734375 | .43359375 |
| ROTATE_CW | -.1953125 | -.045654296875 |
| ROTATE_CCW | -.3203125 | -.1279296875 |
| STOP | .2734375 | -.09423828125 |
| GRASP | 1.4453125 | .59765625 |

The eight candidates that keep their option ordinal still acquire different
scores. Swapping entries of different token lengths also shifts intermediate
token offsets and changes their surrounding content. This intervention identifies
sequence-order sensitivity; it does not isolate positional embeddings from
contextual interactions between candidate labels/descriptions and the rest of
the input. A simple fixed-slot explanation is inadequate.

## Most important remaining ambiguity

**Does the supplied target-relative geometry usefully influence action ranking,
or is ranking dominated by action labels and their presentation context?**
Geometry was held fixed, so this pair cannot establish useful state sensitivity.
The new winner is MV_BACK, which moves along world -X. At this frozen state,
target-minus-TCP X is positive; the existing audit-only nominal projection predicts
that MV_BACK increases target distance by about 8.598 mm, while MV_FWD reduces it
by about 8.474 mm. Neither action was executed. These are nominal geometric
calculations, not measured drawer outcomes or a guarantee of safe task progress.

Thus the changed winner does not establish a useful approach policy. Reordering
the live demo is not justified as a fix. This pair does not isolate all model,
prompt, state-sufficiency or action-effect causes and does not validate any
decision interface. No E0 or research-track work was started.

## Preserved evidence and verification

Local ignored directory: `runs/engineering-demo/frozen-step0-position-swap-v01/`.

- [Comparison and both complete responses/traces](../../../runs/engineering-demo/frozen-step0-position-swap-v01/comparison.json)
- [Original complete input](../../../runs/engineering-demo/frozen-step0-position-swap-v01/0-original-input.json)
- [Swapped complete input](../../../runs/engineering-demo/frozen-step0-position-swap-v01/1-swap_mv_fwd_grasp-input.json)
- [Hash-chained call records](../../../runs/engineering-demo/frozen-step0-position-swap-v01/episodes.jsonl)
- [Manifest](../../../runs/engineering-demo/frozen-step0-position-swap-v01/manifest.json), [configuration](../../../runs/engineering-demo/frozen-step0-position-swap-v01/resolved_config.yaml), [exact runner](../../../runs/engineering-demo/frozen-step0-position-swap-v01/run_pair.py)
- [Console log](../../../runs/engineering-demo/frozen-step0-position-swap-v01.console.log)

Pair JSONL SHA-256:
`bd1fad0b330e1a6ce9bbc12ab88646592cee00593c2a3fc211c9e9cede9ee86f`.
Original episode remains unchanged:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.

Verification: process exit 0; ten chained records validate; exactly two input,
output and forward-trace records; token audits and block-permutation invariants
pass; all probabilities recompute from raw logits at the unchanged temperature;
baseline response and full trace match the archive exactly. Relevant runtime
source hashes still match the original run. No demo implementation or shared
component changed. Existing uncommitted demo work is preserved; only diagnostic
artifacts and reporting were added. No simulator or executor was constructed.
