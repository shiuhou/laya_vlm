> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Frozen step-0 candidate semantics and nominal distance effects

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized engineering follow-up to the
[geometry reflection](frozen_step0_geometry_sensitivity.md). Exactly two model
calls, zero execution. No live demo or shared-runtime behavior changed.

The later [local-objective diagnostic](frozen_step0_local_objective.md) tests the
user's requested approach/contact instruction with the original candidate descriptions.

**The existing descriptions already specify each translation's nominal physical
direction and displacement.** Adding an explicit geometric consequence gives
MV_FWD a small probability gain, but does not produce a consistent preference for
approach. Its lead over MV_BACK shrinks, its translation rank drops, and an action
annotated as increasing target distance becomes the highest-ranked translation.
GRASP remains top-1.

## Inspection: what each candidate actually means

These are the exact model-facing strings from archived step 0, not the separate
natural-candidate audit descriptions:

| Token | Exact existing description | Commanded world TCP displacement, m |
|---|---|---|
| MV_FWD | world +X 10mm | [+0.01, 0, 0] |
| MV_BACK | world -X 10mm | [-0.01, 0, 0] |
| MV_LEFT | world +Y 10mm | [0, +0.01, 0] |
| MV_RIGHT | world -Y 10mm | [0, -0.01, 0] |
| MV_UP | world +Z 10mm | [0, 0, +0.01] |
| MV_DOWN | world -Z 10mm | [0, 0, -0.01] |

The unchanged instruction also says: `Moves retain orientation/grip; rotations
retain position/grip.` These mappings agree with shared `MOVE`, the executor's
use of `backend.step_m`, the LIBERO backend's 10 mm default, and its mapping to
native `x/y/z±10mm` commands. They are explicit nominal commands, not promises of
exact realized motion under every controller/contact condition.

The state supplies absolute target/TCP coordinates plus the relative vector
`[.186186, -.0526391, -.100545]` m. There is enough numeric information to compute
nominal consequences; no physical direction or step size is missing. However,
the description does not explicitly bind a candidate to the update
`d_after = d_before - displacement` or compute the resulting norm. The
target-minus-TCP convention is explicit in the audit provenance rather than an
extra explanatory sentence in the compact input. The model must bind coordinate
semantics, convert mm to m and perform arithmetic itself. Explicit descriptions
do not establish that this checkpoint successfully performs that binding.

Following the user's conditional instruction, this pair therefore tests a minimal
**geometry-only consequence annotation**, not a rewording of already specified
axes. It does not add a new physical action, policy rule or recommended token.

## Single intervention

Use the original archived step-0 state and original ten-option order, with
MV_FWD first and GRASP last. Append one nominal distance change to each of the six
translation descriptions; retain all original text and all other candidate entries:

```text
MV_FWD: world +X 10mm; nominal TCP-target distance decreases 8.474mm
MV_BACK: world -X 10mm; nominal TCP-target distance increases 8.598mm
MV_LEFT: world +Y 10mm; nominal TCP-target distance increases 2.628mm
MV_RIGHT: world -Y 10mm; nominal TCP-target distance decreases 2.196mm
MV_UP: world +Z 10mm; nominal TCP-target distance increases 4.788mm
MV_DOWN: world -Z 10mm; nominal TCP-target distance decreases 4.427mm
```

Each number is `1000 * (norm(d - displacement) - norm(d))`, computed by the
existing `geometric_effects` helper using **exactly the rounded relative geometry
already visible to Laya**, not hidden extra coordinate precision. The wording
renders the sign as “increases/decreases” and the magnitude to .001 mm. The
assumptions are a stationary target and an exact nominal 10 mm displacement;
“nominal” appears in every annotation. No contact, collision, grasp success,
drawer progress, learned dynamics or simulator future is predicted.

Only these six criterion strings change. State bytes, candidate order/identities,
physical actions, instructions, history, model configuration and temperature stay
fixed. The state-side `effects` object stays empty; **the annotated condition is
effect-bearing through its candidate descriptions**, and is not called a no-effect
input. Full derivation/provenance is in the audit, not appended to the model state.

The largest nominal reduction is MV_FWD. MV_RIGHT and MV_DOWN also approach;
MV_BACK, MV_LEFT and MV_UP recede. These expectations and comparison metrics were
recorded before inference. The diagnostic does not turn the task instruction into
“minimize distance”; closeness is an engineering check on action grounding, not a
complete drawer policy or task-success criterion.

## Complete returned probabilities

Exactly one original call and one annotated call ran in the same model session.
The original response and full forward trace exactly reproduce the archive. All
checkpoint files, including weights, match the original manifest. Device/dtype:
CUDA/bfloat16, GPU 6. Temperature remains `1.0000158548355103`; ten options remain.

API probabilities are displayed as percentages; deltas are percentage points.
They are not calibrated physical-success probabilities.

| Action | Original | Annotated | Change, pp |
|---|---:|---:|---:|
| MV_FWD | 10.07% | 10.77% | +0.70 |
| MV_BACK | 7.19% | 9.51% | +2.32 |
| MV_LEFT | 9.39% | 8.76% | -0.63 |
| MV_RIGHT | 6.38% | 5.35% | -1.03 |
| MV_UP | 9.67% | 12.09% | +2.42 |
| MV_DOWN | 8.97% | 7.41% | -1.56 |
| ROTATE_CW | 5.59% | 6.15% | +0.56 |
| ROTATE_CCW | 4.94% | 6.05% | +1.11 |
| STOP | 8.94% | 9.77% | +0.83 |
| GRASP | **28.86%** | **24.14%** | -4.72 |

## Does the appropriate translation gain relative preference?

There is a small gain on some measures, but no consistent geometric improvement:

| Measure | Original | Annotated |
|---|---:|---:|
| P(MV_FWD) | 10.07% | 10.77% |
| MV_FWD share of all translation probability | 19.49% | 19.99% |
| P(MV_FWD) - P(MV_BACK) | +2.88 pp | +1.26 pp |
| P(MV_FWD) - P(GRASP) | -18.79 pp | -13.37 pp |
| MV_FWD rank among translations / all candidates | 1 / 2 | 2 / 3 |
| Highest-ranked translation | MV_FWD | MV_UP |
| Total approaching-translation probability | 25.42% | 23.53% |
| Total receding-translation probability | 26.25% | 30.36% |
| Approaching share of translation probability | 49.20% | 43.66% |

MV_FWD gains .70 pp and closes part of its gap to GRASP, but its opposite MV_BACK
gains 2.32 pp. MV_UP, explicitly annotated as **increasing** target distance, gains
the most among translations and overtakes MV_FWD. The other approaching actions,
RIGHT and DOWN, both lose probability. An absolute MV_FWD increase alone would
therefore overstate the result.

Unrounded distribution total variation is .0794654. API entropy-based confidence
falls from .0686 to .0473; `act_probability` remains 1.0. These are descriptive
values for one pair; no repeatability or statistical claim follows.

## What the evidence distinguishes

| Explanation | Conclusion from inspection and this pair |
|---|---|
| Missing/ambiguous physical displacement definitions | Not supported as a literal omission: signed world axes and 10 mm magnitudes are already stated and match executor mappings. Whether Laya binds them to state correctly remains unresolved. |
| Missing candidate-effect information | The original has no explicit candidate distance consequences. Supplying that one missing quantity does not produce a coherent approach preference here, so its absence alone is not an established explanation or demonstrated remedy. |
| Model still fails to use the available information usefully | Under this fixed state/prompt, neither the original semantics nor this added consequence presentation yields consistent geometric ranking. This is a model/input-use limitation in the tested condition, not proof of failure under every interface. |

A positive or negative annotation response cannot by itself isolate understanding
of the numbers from wording, length or positional/context effects. The extra 67
tokens shift absolute option/state offsets despite identical candidate order;
the earlier position-swap result makes that caveat concrete. Both the original
state-to-action binding and the interpretation of these effects may remain weak.
The unchanged task question also lacks an explicit local distance objective.
This pair does not separate model weights from representation or task framing,
and does not prove the model ignores effects: the distribution demonstrably changes.

No oracle state, future rollout or selected-answer hint was introduced. No new
episode, live policy change, shared-component fix or formal E0 was performed.

## Evidence and verification

Local ignored directory: `runs/engineering-demo/frozen-step0-distance-effects-v01/`.

- [Both distributions, raw logits, token traces and full derivation](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/comparison.json)
- [Original input](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/0-original-input.json)
- [Annotated input](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/1-nominal_distance_annotations-input.json)
- [Effect provenance and exact annotations](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/effect-audit.json)
- [Relative-preference calculations](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/analysis.json)
- [Raw chained records](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/episodes.jsonl)
- [Manifest](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/manifest.json), [configuration](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/resolved_config.yaml), [exact runner](../../../runs/engineering-demo/frozen-step0-distance-effects-v01/run_pair.py)
- [Console log](../../../runs/engineering-demo/frozen-step0-distance-effects-v01.console.log)

Pair JSONL SHA-256:
`05fedba5cb06ec41106144f6155cf16f0a11db133e943af556391c85cd59d385`.
Source episode remains unchanged:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.

Verification: exit 0; 11 chained records validate; exactly two model calls and
forward traces, no retries/warm-up calls and no execution. Consumed lengths are
591/658 tokens with the identical 446-token state. Heading/state tokens and all
unmodified candidate text match; all original translation token blocks remain
prefixes of the annotated blocks. No heading/option/state clipping occurred.
Every returned probability recomputes from captured logits at the fixed
temperature. Baseline response and complete trace match the archive exactly.
All six effects recompute from the unchanged model-facing vector and shared
10 mm action directions. Relevant runtime source hashes still match the source
episode. Existing uncommitted demo work and historical artifacts are preserved.
