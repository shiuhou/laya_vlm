# Frozen step-0 local-objective diagnostic

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized follow-up to the
[distance-effect diagnostic](frozen_step0_distance_effects.md). Exactly one
offline pair: original call, then the requested local-objective instruction.
No execution, simulator construction, live-demo change or formal E0.

The subsequent [translation-only geometry pair](frozen_step0_translations_only.md)
removes nontranslation choices and compares the original/reflected geometry,
using the original instructions without this local-objective addition.

**GRASP remains top-1 and increases from 28.86% to 31.22%.** The nominal approach
translations do not gain useful preference. MV_UP, which increases target
distance in this state, becomes the highest-ranked translation. This exact
local-objective instruction does not rescue the original decision.

## Exact intervention and information boundary

Baseline: archived step-0 model input/response records 15/16 from
`runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/episodes.jsonl`.
It uses the original candidate descriptions, with no distance annotations from
the preceding diagnostic. Original order remains:

```text
MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN,
ROTATE_CW, ROTATE_CCW, STOP, GRASP
```

The original instructions remain intact:

```text
Choose one allowed atomic action for the task. Null means unknown. Moves retain orientation/grip; rotations retain position/grip. Collision freedom is not established.
```

The intervention appends one space and the user's exact requested text, with
line wrapping normalized to spaces:

```text
The current objective is to approach / establish useful contact with the drawer target. The gripper is not currently in contact. Choose the atomic action that best advances this local objective.
```

All state bytes, candidate identities/order/descriptions, empty history, empty
effects, model configuration and temperature remain fixed. No phase field or
preferred action label is introduced. The entire consumed token suffix covering
candidates and state is identical; only the instruction prefix grows.

**This addition contains both a local objective and a new contact premise.**
The original visual state has `interaction.target_contact=null`, and that field
stays null in both calls. “The gripper is not currently in contact” is a manually
supplied diagnostic assertion, not knowledge established by this visual interface.
Archived evaluator record 13 corroborates no target contact, but remains
evaluator-only evidence. The premise and its origin are explicitly labeled in
the audit. This condition must not be presented as an ordinary sensor-only input
or silently transferred into live visual behavior.

Thus the pair tests the requested **objective-plus-contact-premise wording**.
It cannot separately identify the objective's contribution, the added contact
fact's contribution or effects of wording/length. No additional controls were run.

## Complete returned probabilities

The baseline's full API response and forward trace exactly match the archive.
Both calls use the same hashed checkpoint/config/tokenizer and CUDA/bfloat16
path on GPU 6. There are ten options and unchanged temperature
`1.0000158548355103` throughout.

Probabilities are API values displayed as percentages; changes are percentage
points. They are not calibrated probabilities of physical success.

| Action | Original | Added objective | Change, pp |
|---|---:|---:|---:|
| MV_FWD | 10.07% | 9.35% | -0.72 |
| MV_BACK | 7.19% | 6.79% | -0.40 |
| MV_LEFT | 9.39% | 9.30% | -0.09 |
| MV_RIGHT | 6.38% | 6.12% | -0.26 |
| MV_UP | 9.67% | 9.98% | +0.31 |
| MV_DOWN | 8.97% | 8.97% | 0.00 |
| ROTATE_CW | 5.59% | 5.33% | -0.26 |
| ROTATE_CCW | 4.94% | 4.36% | -0.58 |
| STOP | 8.94% | 8.58% | -0.36 |
| GRASP | **28.86%** | **31.22%** | +2.36 |

- **GRASP decreases?** No; it increases by 2.36 pp and remains the winner.
- **Approaching translations increase?** No. At this geometry, MV_FWD,
  MV_RIGHT and MV_DOWN reduce nominal TCP-target distance. FWD and RIGHT decrease;
  DOWN is unchanged at API rounding precision (its unrounded probability actually
  decreases by approximately .00417 pp). Their combined API mass falls from
  **25.42% to 24.44%**.
- **Top-1 becomes directionally appropriate?** No. GRASP is still first. The
  highest-ranked translation switches from MV_FWD to **MV_UP**, which would
  increase nominal target distance by about 4.788 mm. No action was executed.

The FWD-over-BACK margin shrinks from 2.88 to 2.56 pp; FWD's deficit to GRASP
grows from 18.79 to 21.87 pp. Approaching actions' share of translation probability
falls from 49.20% to 48.39%. These checks use nominal 10 mm geometry, not measured
task progress or a full contact/safety model. The added objective does not supply
an explicit one-step distance-minimization criterion.

Unrounded distribution total variation is .0267281. API entropy-derived
confidence increases from .0686 to .0839; `act_probability` remains 1.0. These
are descriptive measurements from one pair, not a repeatability or significance
claim.

## Does this identify missing task-to-local-objective decomposition?

**No. It does not support that omission as a sufficient explanation of this
failure.** Supplying this explicit approach/contact objective, together with the
no-contact premise, fails to improve the observed action ranking. That does not
prove local-objective decomposition is architecturally unnecessary, nor that
every decomposition or objective wording would fail. It shows this particular
prompt-level addition is not a demonstrated remedy at this boundary.

The remaining ambiguity is whether the checkpoint fails to follow/bind the
objective to the geometry and atomic meanings, or whether this wording and input
representation elicit an unhelpful preference. “Establish useful contact” may
be associated with GRASP without understanding that its primitive only closes
the gripper; that is a hypothesis, not an inferred model rationale. Interaction
affordances remain unspecified. The intervention's contact premise and its extra
35 tokens are also inseparable from its objective in this pair; absolute token
offsets change even though candidate order and contents do not.

**This test does not prove the final interface should contain a scripted phase
label.** It does not justify adding a live phase policy, oracle contact field or
scripted task sequence. Model/interface/task-framing causes remain unresolved;
the user-requested two-call diagnostic is complete without further rollout or tuning.

## Evidence and verification

Local ignored directory: `runs/engineering-demo/frozen-step0-local-objective-v01/`.

- [Both distributions, raw logits and token traces](../runs/engineering-demo/frozen-step0-local-objective-v01/comparison.json)
- [Exact original input](../runs/engineering-demo/frozen-step0-local-objective-v01/0-original-input.json)
- [Exact intervention input](../runs/engineering-demo/frozen-step0-local-objective-v01/1-local_objective-input.json)
- [Objective/contact-premise provenance](../runs/engineering-demo/frozen-step0-local-objective-v01/premise-audit.json)
- [Derived comparison metrics](../runs/engineering-demo/frozen-step0-local-objective-v01/analysis.json)
- [Chained raw records](../runs/engineering-demo/frozen-step0-local-objective-v01/episodes.jsonl)
- [Manifest](../runs/engineering-demo/frozen-step0-local-objective-v01/manifest.json), [configuration](../runs/engineering-demo/frozen-step0-local-objective-v01/resolved_config.yaml), [exact runner](../runs/engineering-demo/frozen-step0-local-objective-v01/run_pair.py)
- [Console log](../runs/engineering-demo/frozen-step0-local-objective-v01.console.log)

Pair JSONL SHA-256:
`68218ff30d8461d57714841e0774cda16faada1d74cc51cb08674eb662bcc552`.
Original episode remains unchanged:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.

Verification: process exit 0; all 11 chained records validate; exactly two model
calls and forward traces, no repeats/retries/warm-ups and zero execution. The
only input edit is the verbatim requested instruction suffix. Inputs consume
591/626 tokens, with the same 446-token state and identical candidate/state
suffix. No heading/option/state clipping occurs. Probabilities independently
recompute from recorded logits and unchanged temperature. Model files, including
weights, and relevant runtime source hashes match the archive. Baseline response
and full trace match exactly. No shared component, live demo or research-track
implementation was changed; existing work and historical evidence are preserved.
