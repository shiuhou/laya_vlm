> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Frozen step-0 translation-only geometry diagnostic

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized follow-up to the
[local-objective diagnostic](frozen_step0_local_objective.md). Exactly two offline
model calls, zero execution, no live-demo or shared-component change, and no E0.

A later [minimal synthetic capability probe](synthetic_direction_probe.md)
removes archived task state entirely and tests the six signed-axis directions.
The frozen-pair result below remains unchanged.

**MV_FWD wins in both geometries.** The strongest nominal approach should reverse
from MV_FWD to MV_BACK. Instead, BACK loses probability and loses preference
relative to FWD. The newly approaching direction in each of the three opposing
pairs loses pair-relative preference. Removing gripper, rotation and STOP choices
does not yield useful directional geometric grounding in this pair.

## Frozen conditions

A uses the original model-facing step-0 state from records 15/16 of
`runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/episodes.jsonl`.
B uses exactly the model-facing counterfactual state saved by the prior
[geometry-reflection diagnostic](frozen_step0_geometry_sensitivity.md).
Both use only these six original entries, in this order:

| Candidate | Unchanged description |
|---|---|
| MV_FWD | world +X 10mm |
| MV_BACK | world -X 10mm |
| MV_LEFT | world +Y 10mm |
| MV_RIGHT | world -Y 10mm |
| MV_UP | world +Z 10mm |
| MV_DOWN | world -Z 10mm |

The unchanged question instructions are:

```text
Choose one allowed atomic action for the task. Null means unknown. Moves retain orientation/grip; rotations retain position/grip. Collision freedom is not established.
```

Task remains `close the top drawer of the cabinet`. Target identity remains
`the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground`.
History is `[]` and effects are `{}` in both calls. Neither the distance-effect
annotations nor the later local objective/contact premise are included.

Only the four nontranslation option blocks are removed from the original call.
**A is a new six-option condition, not a reproduction of the archived ten-option
response.** No additional ten-option baseline inference was run. The original
and reflected ten-option tokenizations were checked without inference.

Checkpoint/config/tokenizer match the archive. Laya 0.3.4 runs on CUDA/bfloat16,
GPU 6, seed 1. Both six and ten options use the same configured `choice:6-10`
temperature, `1.0000158548355103`. A/B have identical instructions, candidate
tokens and option-marker positions, and consume 549/545 tokens without clipping.

## Geometry and expected preference

The counterfactual keeps TCP fixed and computes `target' = 2 * TCP - target`
from the archived visual target and proprioceptive TCP. Shared `derive_relations`
recomputes all dependent geometry. The relative vector changes from
`[+0.186186, -0.0526391, -0.100545] m` to
`[-0.186186, +0.0526391, +0.100545] m`.
Target position and signed height change consistently; distance (0.218049 m)
and XY norm (0.193484 m) remain invariant. Zero target velocity and covariance
are consistent under this central reflection. All other model-state fields stay
fixed. This is a labeled synthetic input, not a new observation or simulated world.

Nominal distance reductions for the unchanged 10 mm atomic displacements are
computed for this report only; they were not model inputs:

| Action | A reduction, mm | B reduction, mm |
|---|---:|---:|
| MV_FWD | +8.474 | -8.598 |
| MV_BACK | -8.598 | +8.474 |
| MV_LEFT | -2.628 | +2.196 |
| MV_RIGHT | +2.196 | -2.628 |
| MV_UP | -4.788 | +4.427 |
| MV_DOWN | +4.427 | -4.788 |

Positive means approaching the presented target point. Expected pair preferences
reverse from FWD/RIGHT/DOWN to BACK/LEFT/UP; the largest reduction reverses from
FWD to BACK. These are geometric expectations, not guarantees of collision
freedom, useful contact, drawer progress or task success. No simulator future
state or oracle correction is used.

## Complete returned distributions

API probabilities as percentages; changes are percentage points. They are action
selection scores, not calibrated probabilities of physical success.

| Action | A: original geometry | B: reflected geometry | Change, pp |
|---|---:|---:|---:|
| MV_FWD | **27.19%** | **26.19%** | -1.00 |
| MV_BACK | 14.66% | 13.84% | -0.82 |
| MV_LEFT | 16.75% | 16.01% | -0.74 |
| MV_RIGHT | 13.10% | 13.66% | +0.56 |
| MV_UP | 15.20% | 15.89% | +0.69 |
| MV_DOWN | 13.10% | 14.41% | +1.31 |

Top-1 is **MV_FWD → MV_FWD**. It would nominally reduce distance by 8.474 mm
in A and increase it by 8.598 mm in B. The strongest approaching direction in B,
MV_BACK, loses 0.82 pp and drops from fourth to fifth in the ranking. LEFT also
loses probability. UP gains 0.69 pp, but its newly receding opposite DOWN gains
more, 1.31 pp.

| Pair | Expected preference A → B | Observed preference A → B | First-minus-second margin A → B, pp |
|---|---|---|---:|
| FWD / BACK | FWD → BACK | FWD → FWD | +12.53 → +12.35 |
| LEFT / RIGHT | RIGHT → LEFT | LEFT → LEFT | +3.65 → +2.35 |
| UP / DOWN | DOWN → UP | UP → UP | +2.10 → +1.48 |

Pair-conditional shares remove normalization effects from the other four options.
Using unrounded probabilities, each direction that becomes approaching in B
**loses** share within its own pair:

| Newly approaching direction | Pair-conditional share A | Share B | Change, pp |
|---|---:|---:|---:|
| BACK / (FWD + BACK) | 35.020% | 34.577% | -0.443 |
| LEFT / (LEFT + RIGHT) | 56.121% | 53.971% | -2.150 |
| UP / (UP + DOWN) | 53.704% | 52.439% | -1.265 |

The slight shrinkage in FWD's absolute probability margin is not improvement in
BACK's relative preference: the FWD-minus-BACK raw logit margin actually grows
from 0.618164 to 0.637695. None of the three pair orderings reverses. LEFT and UP
already led their pairs when they pointed away in A; retaining those leads in B
is not evidence of an appropriate response to geometry.

## Conclusion and remaining ambiguity

There is numerical sensitivity (total variation 0.0255715), but **no useful
directional geometric sensitivity demonstrated by this pair**. The model does
not rank the six translations coherently according to the reversing target
geometry. FWD's correct top-1 in A alone cannot establish grounding when it also
wins in B.

**Cross-family competition is not a sufficient explanation.** The directional
failure persists with no gripper, rotation or STOP candidate to compete against.
The evidence points to a deeper geometry-to-action binding problem for this
checkpoint and presentation, rather than only suppression of useful translations
by the gripper family. Competition may still contribute to the original
GRASP/RELEASE behavior; this pair does not measure its causal contribution there.

The most important ambiguity remains whether the limitation is in the checkpoint's
geometric reasoning or in how this fixed wording/schema/order elicits that
reasoning. The preserved task asks to close a drawer, not explicitly to minimize
point distance; task interpretation and static position/label preferences remain
possible contributors. One state and its reflection cannot establish model-wide
incapability. Removing choices also changes the encoder's menu context; this is
not merely renormalizing the ten-option scores. No live translation filter,
scripted sequence, revised prompt or phase label is justified or installed by
this diagnostic. No further inference or episode was run.

## Evidence and verification

Local ignored directory: `runs/engineering-demo/frozen-step0-translations-only-v01/`.

- [Full API distributions, raw logits and consumed token traces](../../../runs/engineering-demo/frozen-step0-translations-only-v01/comparison.json)
- [Exact A input](../../../runs/engineering-demo/frozen-step0-translations-only-v01/0-original-input.json)
- [Exact B input](../../../runs/engineering-demo/frozen-step0-translations-only-v01/1-reflected_geometry-input.json)
- [Geometry/provenance audit](../../../runs/engineering-demo/frozen-step0-translations-only-v01/geometry-audit.json)
- [Derived pair metrics and verification results](../../../runs/engineering-demo/frozen-step0-translations-only-v01/analysis.json)
- [Chained raw records](../../../runs/engineering-demo/frozen-step0-translations-only-v01/episodes.jsonl)
- [Manifest](../../../runs/engineering-demo/frozen-step0-translations-only-v01/manifest.json), [configuration](../../../runs/engineering-demo/frozen-step0-translations-only-v01/resolved_config.yaml), [exact runner](../../../runs/engineering-demo/frozen-step0-translations-only-v01/run_pair.py)
- [Analysis-only verifier](../../../runs/engineering-demo/frozen-step0-translations-only-v01/analyze_pair.py)
- [Console log](../../../runs/engineering-demo/frozen-step0-translations-only-v01.console.log)

Pair JSONL SHA-256:
`2c1d2b87238a5d6b913e438ee2c92dbe46fd060bbfad8103e7db6d36bd0ac2b4`.
Original episode remains unchanged:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.
Prior geometry-pair evidence remains unchanged:
`6359831fa8b6f34235b5567a1c5b7e18b3804056e313ab476b8e85317de30e36`.

Verification: inference process exited 0; all 11 chained records validate;
exactly two inputs, outputs and forward traces, no repeats/retries/warm-ups and
zero execution. A state equals the archive; B equals the prior reflected state.
Original descriptions and six-option order are preserved. All probabilities
independently recompute from raw logits and fixed temperature. Model files and
relevant runtime source hashes match the archive. Analysis-only verification,
report/link checks and `git diff --check` pass. Generated evidence remains ignored.
This phase changes documentation and ignored evidence only; no runtime, shared
decision-interface semantics or live behavior changed, and no commit was made.
