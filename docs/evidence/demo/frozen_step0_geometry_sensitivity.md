> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Frozen step-0 geometry sensitivity

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized engineering diagnostic following the
[decision autopsy](decision_autopsy.md) and [position swap](frozen_step0_position_swap.md).
Exactly two Laya calls: original step 0, then one coherent geometry reflection.
Zero executed actions; no simulator or executor constructed.

The later [candidate-semantics inspection and distance-effect pair](frozen_step0_distance_effects.md)
tests whether explicit nominal consequences help at the original geometry.

**The result supports weak, non-useful sensitivity in this pair.** Changing only
geometry changes scores and some ranks, but they do not track the reversed
approach directions. GRASP remains top-1 and gains probability. The newly best
nominal translation, MV_BACK, does not gain probability; MV_FWD remains the
highest-ranked translation although it now points away from the target.

This is not evidence of complete input independence: distributions and logits
do change. It is also not evidence of useful geometric reasoning, task competence
or a generally sufficient interface. No demo behavior was modified.

## One consistent counterfactual, fixed presentation

Source: raw input record 15 and response record 16 in
`runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/episodes.jsonl`.
The baseline uses the archived original order, not the earlier swapped order:

```text
MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN,
ROTATE_CW, ROTATE_CCW, STOP, GRASP
```

Using the archived full-precision proprioceptive TCP `p` and visual target `t`,
construct `t' = 2p - t`. The TCP stays fixed, and the relative vector becomes
`d' = t' - p = -(t - p)`. The shared `derive_relations` helper recomputes the
relative XYZ vector, Euclidean distance, XY norm and signed height error from
the reflected absolute target. The unchanged compact serializer then rounds
values to six significant digits.

| Model geometry field | Original | Reflected |
|---|---|---|
| robot.tcp_position_m | [-.207912, -.0144588, 1.17826] | unchanged |
| target.position_m | [-.0217258, -.0670979, 1.07772] | [-.394098, .0381803, 1.27881] |
| relations.tcp_target_delta_m | [.186186, -.0526391, -.100545] | [-.186186, .0526391, .100545] |
| relations.height_error_m | -.100545 | .100545 |
| relations.distance_m | .218049 | .218049 |
| relations.xy_error_m | .193484 | .193484 |

Only three model fields change numerically. Both distance norms are recomputed
and remain identical because reflection preserves them. Relations are consistent
at full precision; ordinary six-significant-digit display rounding can leave
micrometre-scale differences when subtracting the displayed coordinates. No
dependent field is left with geometry from the original side.

Target velocity is zero and stays zero. Central reflection transforms covariance
as `(-I) C (-I)^T = C`, so its unchanged value is consistent. Robot state,
quality/age/validity, task and target identity, unknown contact/holding/progress,
empty history and empty effects remain unchanged. Candidate order, membership,
labels, descriptions and instructions are byte-for-byte identical. Heading,
candidate token spans and option-marker offsets are identical in both calls.

The reflection is labeled **synthetic, not observed**, in the audit only. No
diagnostic labels or expected answers enter the model state. The full-precision
counterfactual uses archived visual/proprioceptive values, with no oracle state,
new sensor capture, simulator future or new candidate effects. It is internally
consistent decision geometry, not a claim that this scene was physically observed
or validated in MuJoCo. The prompt continues to request the original drawer task;
no approach instruction is added.

## Expected reversal, recorded before inference

The diagnostic expectation uses only the nominal 10 mm world-axis translations
already described in the candidates. Positive distance reduction means movement
toward the target point, assuming a fixed target and exact nominal displacement.
These audit calculations never enter either model input.

| Translation | Original distance reduction, mm | Reflected distance reduction, mm |
|---|---:|---:|
| MV_FWD | +8.474087 | -8.598499 |
| MV_BACK | -8.598499 | +8.474087 |
| MV_LEFT | -2.627568 | +2.195844 |
| MV_RIGHT | +2.195844 | -2.627568 |
| MV_UP | -4.787844 | +4.426731 |
| MV_DOWN | +4.426731 | -4.787844 |

The strongest nominal approach reverses **MV_FWD → MV_BACK**. LEFT and UP also
become approaching choices; RIGHT and DOWN become receding choices. This is an
interpretable geometric expectation, not a claim that distance reduction alone
solves the drawer task, predicts contact dynamics or certifies safe movement.

## Full probability comparison

The original call exactly matches the archived API response and full forward
trace, including all logits. Both calls use the same checkpoint/config/tokenizer
hashes, original CUDA/bfloat16 path on GPU 6 and temperature
`1.0000158548355103`. There are ten options throughout. The original/reflected
inputs consume 591/587 tokens, including 446/442 state tokens; numeric changes
alter tokenization length, with no heading, option or state clipping.

Probabilities are the API's four-decimal outputs displayed as percentages.
Changes are percentage points. Rounded reflected probabilities sum to 100.01%.
They are not calibrated probabilities of successful physical execution.

| Action | Original | Reflected | Change, pp |
|---|---:|---:|---:|
| MV_FWD | 10.07% | 9.98% | -0.09 |
| MV_BACK | 7.19% | 7.17% | -0.02 |
| MV_LEFT | 9.39% | 8.05% | -1.34 |
| MV_RIGHT | 6.38% | 5.81% | -0.57 |
| MV_UP | 9.67% | 8.50% | -1.17 |
| MV_DOWN | 8.97% | 8.62% | -0.35 |
| ROTATE_CW | 5.59% | 6.79% | +1.20 |
| ROTATE_CCW | 4.94% | 5.68% | +0.74 |
| STOP | 8.94% | 8.62% | -0.32 |
| GRASP | **28.86%** | **30.79%** | +1.93 |

- **Does the newly appropriate translation gain?** No. MV_BACK falls 0.02 pp.
  The other newly approaching translations, LEFT and UP, also lose probability.
- **Does the opposite translation lose?** Yes, MV_FWD falls 0.09 pp, but it still
  outranks MV_BACK by 2.81 pp. RIGHT and DOWN also fall, without corresponding
  gains in their now-approaching counterparts.
- **Does top-1 change in the expected direction?** No. GRASP remains first and
  MV_FWD remains the best-ranked translation. No action was executed.

Pairwise margins help distinguish useful preference changes from all translations
losing mass to grip/rotation options. Below, positive means preference for the
translation that approaches in the reflected geometry:

| Margin | Original, pp | Reflected, pp | Change, pp |
|---|---:|---:|---:|
| P(MV_BACK) - P(MV_FWD) | -2.88 | -2.81 | +0.07 |
| P(MV_LEFT) - P(MV_RIGHT) | +3.01 | +2.24 | -0.77 |
| P(MV_UP) - P(MV_DOWN) | +0.70 | -0.12 | -0.82 |

Only the X-pair margin moves slightly in the expected direction, without reversing
its preference. The Y margin moves against the expected change. The Z preference
actually reverses toward the now-receding DOWN action. All six translations lose
absolute probability; combined mass falls from 51.67% to 48.13%.

Total variation distance between the unrounded distributions reconstructed from
logits is .0387506. API entropy-based confidence changes from .0686 to .0761;
`act_probability` remains 1.0. These are descriptive measurements from one pair,
not a repeatability estimate or a significance test.

## What the pair answers

The geometry-field intervention changes the model's output while candidate and
question presentation remain fixed. Thus strict insensitivity to these input
fields is not supported. However, the probability shifts and translation ranking
provide **no coherent useful adaptation to the reversed directions**. The appropriate
classification is **weak, non-useful sensitivity in this contrast**, rather than
useful geometric sensitivity or literally no output effect.

This pair does not identify whether the model interprets geometry numerically,
reacts to changed numeric/sign tokens, or has a geometry signal overwhelmed by
other preferences. Nor does it isolate target-relative relations from the changed
absolute target coordinates: they were changed together to keep the state
consistent. Model/interface limitations, weak semantic binding and the task's
unspecified local objective remain unresolved. No prompt, interface or policy fix
is justified by this result alone; no E0 or research claim is made.

## Evidence and verification

Local ignored directory: `runs/engineering-demo/frozen-step0-geometry-reflection-v01/`.

- [Comparison, full distributions, raw logits and traces](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/comparison.json)
- [Original model input](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/0-original-input.json)
- [Reflected model input](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/1-reflected_geometry-input.json)
- [Full-precision geometry, provenance and consistency audit](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/geometry-audit.json)
- [Raw chained records](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/episodes.jsonl)
- [Manifest](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/manifest.json), [configuration](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/resolved_config.yaml), [exact runner](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01/run_pair.py)
- [Console log](../../../runs/engineering-demo/frozen-step0-geometry-reflection-v01.console.log)

Pair JSONL SHA-256:
`6359831fa8b6f34235b5567a1c5b7e18b3804056e313ab476b8e85317de30e36`.
Source episode remains unchanged:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.

Verification: exit 0; all 11 chained records validate; exactly two call inputs,
outputs and forward traces; no retries/warm-ups or simulation. Full-precision
target/delta/norm/height consistency and nominal reversal checks pass. Fixed
question/order/token-prefix checks pass. Both distributions recompute from raw
logits at the unchanged temperature. All model files, including weights, and
relevant runtime sources match the archive; the baseline response/trace matches
exactly. No shared component, demo behavior or research-track file was changed.
