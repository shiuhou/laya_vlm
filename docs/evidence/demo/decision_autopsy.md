> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Decision autopsy: why the demo repeats GRASP / RELEASE

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus the existing demo
instrumentation changes. This is an inspection of saved engineering evidence,
not E0, a new rollout, a policy change or a research conclusion.

The subsequently authorized two-call position-swap result is recorded separately
in [frozen_step0_position_swap.md](frozen_step0_position_swap.md), followed by the
[fixed-presentation geometry diagnostic](frozen_step0_geometry_sensitivity.md) and
[nominal distance-effect diagnostic](frozen_step0_distance_effects.md). A later
[local-objective diagnostic](frozen_step0_local_objective.md) preserves the original
state/candidates and adds the user's requested instruction. The subsequent
[translation-only geometry pair](frozen_step0_translations_only.md) tests the
original and reflected states with only the six unchanged translations. A later
[synthetic capability probe](synthetic_direction_probe.md) tests basic signed-axis
choices without any archived task state; its
[ordering follow-up](synthetic_negative_order_probe.md) isolates a substantial
presentation contribution. The autopsy below preserves the evidence and proposed
diagnostic as they stood before those calls.

**The observed mechanism is a deterministic selection-and-gating cycle.** At
each boundary, the available gripper token receives the highest individual Laya
score. The API takes its argmax, validation accepts that permitted token, and the
executor opens/closes the gripper while holding the TCP pose. The resulting robot
state vetoes that same gripper token at the next boundary and permits its opposite.
Laya again ranks the available gripper token above the nine alternatives. All six
translations remain available. The robot never approaches; the drawer never moves.

This identifies how the video is produced, **not why the model internally prefers
these options**. Candidate position, wording, state representation, missing task
information and missing action/outcome context remain entangled. No rationale is
returned by this typed scoring API. The earliest two decisions are reconstructed
below rather than inferring a rationale from later repetitions.

## Evidence identity and reconstruction

Source episode: `runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/`.
LIBERO `top_drawer`, benchmark init 0, seed 1. Raw `episodes.jsonl` SHA-256:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.

The [autopsy bundle](../../../runs/engineering-demo/decision-autopsy-feedback-v02-v01/autopsy.json)
preserves the complete source records for the first two boundaries: sensor events,
full-precision canonical field provenance, natural candidates and rejection reasons,
model payloads, consumed token IDs, raw logits, validation, physical controls and
before/after evaluator measurements. It also reconstructs the scores for all eight
decisions. These are local ignored artifacts; share them with the source run.

| Decision | Before evaluation / snapshot / model input / response / decision / intent / action / after evaluation (raw `seq`) |
|---|---|
| Step 0, GRASP | 13 / 14 / 15 / 16 / 17 / 18 / 19 / 21 |
| Step 1, RELEASE | 29 / 30 / 31 / 32 / 33 / 34 / 35 / 37 |

Snapshot IDs are
`43fa425cf0a3d9e79348f59e2a1a91999845d9c3e05d5b8170e013a2d351c37f`
and `de3fd5273a427926d3ea63a3a9dbc613ca95dab2975abc04755877ee13081e12`.
The [episode inspector](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/demo.html)
and [contact sheet](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/contact-sheet.png)
remain unchanged. The [feedback report](closed_loop_demo.md) describes the whole episode.

The JSONL recorder sorts object keys. **Alphabetical order in its `criteria`
object is not the order Laya consumed.** Reconstruction restores order from the
canonical candidate array and checks the resulting sequence against the recorded
forward-pass token IDs and option markers. Both match exactly for all eight calls.
Use the exported `step-000-model-input.json` / `step-001-model-input.json`, which
include an explicit `option_order`, when reconstructing these calls.

## Exactly what reached Laya

Laya received structured text, not the camera image or video. Agentview RGB-D went
through LocateAnything, the existing first-box/interior-median-depth estimator,
MultiRateFusion and BeliefStore. Captures 1 and 2 were at simulation times 0.5 and
0.9 s. The selected pixel box was `[145,167,167,203]` in both; additional detector
boxes were retained in the audit, not used to oracle-correct that selection.
The fused target point rounded to the same coordinates at both boundaries.

The **complete model-facing states** are in the appendix. Full provenance and
unrounded values stay in the audit and were not prompt fields. The exact question
has key `action`, type `choice`, and these instructions, unchanged between calls:

```text
Choose one allowed atomic action for the task. Null means unknown. Moves retain orientation/grip; rotations retain position/grip. Collision freedom is not established.
```

The task inside the state is exactly `close the top drawer of the cabinet`.
The target identity is `the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground`.
There is no additional conversational/system prompt or previous conversation in
this `system_one` call. The installed typed encoder constructs:

```text
[CLS]choice question: <instructions>[SEP]
[MASK] <token>: <description> ... [MASK] <last token>: <description>[SEP]
<serialized state>[SEP]
```

All candidates and scores follow. Entries 1–9 keep the shown order; the allowed
gripper entry is **position 10** in both calls. A dash means the option was not
offered, not that Laya assigned it zero probability. Every offered option passed
the existing natural validity gate. No feasibility flag, risk value, rejection
reason or soft direction score was included as an additional model feature.

| Position / token | Exact model description | Step 0 raw logit | Step 0 API P | Step 1 raw logit | Step 1 API P |
|---|---|---:|---:|---:|---:|
| 1 MV_FWD | world +X 10mm | .392578125 | .1007 | .33984375 | .1026 |
| 2 MV_BACK | world -X 10mm | .05615234375 | .0719 | -.053466796875 | .0692 |
| 3 MV_LEFT | world +Y 10mm | .322265625 | .0939 | .234375 | .0923 |
| 4 MV_RIGHT | world -Y 10mm | -.064453125 | .0638 | -.1103515625 | .0654 |
| 5 MV_UP | world +Z 10mm | .3515625 | .0967 | .490234375 | .1192 |
| 6 MV_DOWN | world -Z 10mm | .27734375 | .0897 | .47265625 | .1171 |
| 7 ROTATE_CW | world Z -10deg | -.1953125 | .0559 | -.01361083984375 | .0720 |
| 8 ROTATE_CCW | world Z +10deg | -.3203125 | .0494 | -.2294921875 | .0580 |
| 9 STOP | hold pose and grip | .2734375 | .0894 | .46484375 | .1162 |
| 10 GRASP (step 0 only) | close grip; hold pose | 1.4453125 | **.2886** | — | — |
| 10 RELEASE (step 1 only) | open grip; hold pose | — | — | .9453125 | **.1879** |

The natural candidate list contains 11 tokens. Step 0 excludes only RELEASE:
`holding_state_unknown` (holding is unknown and the retained command is OPEN).
Step 1 excludes only GRASP: `gripper_already_closed` (joint opening is below 30 mm).
All translation/rotation/STOP reason lists are empty at both boundaries. Geometry
is usable, semantic and temporal consistency checks pass, no workspace bounds
are configured, and there is no physics preview. The GRASP gate checks geometry,
semantics, timing and gripper opening; **it has no target-proximity, grasp-alignment
or contact requirement**. It permits closing an empty gripper. Validity is not
task usefulness or collision certification; the instructions explicitly say so.

Both calls contain `"previous": []` and `"effects": {}`. At step 1 the model sees
CLOSED, joint width 0.0218133 m, updated TCP/relative position and changed quality.
It does **not** receive the previous GRASP token, its TCP displacement, elapsed
execution time, contact outcome, drawer progress or a statement that it failed.
`interaction.holding`, `interaction.target_contact`, `target.visible_now` and
`progress.remaining_open_mm` remain null. The recurrent world/belief loop does not
create implicit conversational memory in the stateless `system_one` API.

## Why the available translations lose

Installed Laya 0.3.4 applies `softmax(logits / temperature)` then returns
`keys[p.argmax()]`. This run has **ten** options; its verified configuration uses
`choice:6-10 = 1.0000158548355103`. The much sharper `choice:11+` temperature in
earlier research diagnostics does not apply. A positive temperature cannot change
the argmax anyway. There is no sampling, candidate-family aggregation or exploration.

At step 0, GRASP beats the strongest translation MV_FWD (.2886 vs .1007). At
step 1, RELEASE beats MV_UP (.1879 vs .1192). The six translations' summed rounded
probability is .5167 / .5658, but no individual translation wins; total probability
for a family is not the selection rule. More identical calls would not sample that
combined mass. The API confidence is .0686 / .0270, an entropy-derived statistic,
not P(choice) or a calibrated physical-success estimate. The separate act-head
logits are `[4544,-3696]` / `[4480,-3664]`, giving `act_probability=1.0` in both.
The runtime validates identity, membership and expiry; it does not use confidence
to rerank/abstain. No validation fallback occurred.

Consumed lengths are 591 / 594 tokens, under the 1024-token limit, with 446 / 449
state tokens and room for 879. All heading, option and state clipping flags are
false. Option marker offsets are `[40,51,61,71,81,91,101,113,126,134]` in both.
Reconstructed token IDs and every rounded returned probability match the recorded
forward pass. No score/index/label mismatch is observed. The current installed
API source, checkpoint config/tokenizer hashes and relevant runtime sources were
checked; runtime sources match the episode manifest.

Some task-relative geometry is present: step 0 target-minus-TCP is
`[+0.186186,-0.0526391,-0.100545]` m, with distance 0.218049 m. The existing
audit-only nominal projection gives distance reductions of +8.474 mm for MV_FWD,
+2.196 mm for MV_RIGHT, and +4.427 mm for MV_DOWN; the opposite directions increase
distance. These numbers were **not** passed to Laya. Inferring this nominal
approach from the input requires binding world-axis action descriptions to numeric
relations and doing arithmetic. It does not require oracle information, but it
also does not establish which action is safe or best for closing the drawer.

The model therefore did not demonstrate selection of an available nominal approach.
It is inaccurate to say it had no target-relative state at all. It is equally
unsupported to say the present state is sufficient for task competence: drawer
articulation/axis, grasp affordance, TCP orientation, contact/holding, useful history
and candidate-specific outcomes are missing or unknown. The visual target is an
estimated box/depth point, not a validated grasp pose.

## What actually happened, then fed back

GRASP means backend `close`, with retained gripper command +1; RELEASE means
`open`, with retained command -1. Each ran eight seven-dimensional controller
commands over 0.4 simulation seconds / 200 physics substeps. The initial command
was `[0,0,0,0,0,0,+1]` or `[0,0,0,0,0,0,-1]`; subsequent small translation terms
were controller corrections while holding pose, not model-selected translations.
All sixteen actual command vectors are preserved in the autopsy source records
and match the original trajectory NPZ arrays exactly.

| Physical measure | Step 0 GRASP | Step 1 RELEASE |
|---|---|---|
| Simulation interval, s | 0.5 → 0.9 | 0.9 → 1.3 |
| TCP before, m | [-.2079120125452366, -.014458808099785917, 1.1782619210543612] | [-.207876528280113, -.014340875644753113, 1.1782900311977382] |
| TCP after, m | [-.207876528280113, -.014340875644753113, 1.1782900311977382] | [-.20785703068509676, -.014235350835512644, 1.1783049216684927] |
| TCP delta XYZ, mm | [+.0354843, +.1179325, +.0281101] | [+.0194976, +.1055248, +.0148905] |
| TCP displacement norm, mm | .126323 | .108339 |
| Rotation angle, degrees | .104739 | .015060 |
| Finger-pad gap, mm | 76.445515 → 20.813329 | 20.813329 → 57.434937 |
| Drawer joint position, m | -.15165901295563317 → same | same → same |
| Remaining opening, mm | 151.65901295563316 → same | same → same |
| Target / obstacle contact | false / false throughout recorded boundaries | false / false throughout recorded boundaries |
| Success / execution contract violation | false / false | false / false |

Contact/progress/rotation and other simulator measurements here are **evaluation
only**, not newly supplied model information. Full orientation matrices, contacts,
forces, controller vectors and source snapshot identities are in the bundle.
The original trajectories retain full simulator state vectors before controls and
after each action; their hashes were rechecked, without rerunning simulation.

The next proprioceptive joint openings are 21.8133 mm after GRASP and 58.4349 mm
after RELEASE. The roughly 1 mm offset from the evaluator's finger-pad gaps reflects
different measurements, not a broken feedback connection. Likewise, evaluator
nearest-moving-geometry distances (93.4844 → 100.9699 → 95.1492 mm) are **not** the
same referent as the model's approximately 218 mm TCP-to-visual-point distance.

Fresh captures and admitted/used fusion evidence reach the next input. GRASP's
outcome causes its 30 mm width veto; RELEASE's outcome restores OPEN and removes
RELEASE when holding is unknown. Across all eight boundaries the selected grip
option is last and highest-scoring, with P(choice)
`.2886, .1879, .3220, .1974, .3692, .1853, .3133, .2107`.
All seven choice changes coincide with veto of the previous choice. This is a
faithful physical feedback loop, but it does not isolate useful model sensitivity
to the observed changes. There is zero recorded drawer progress.

## Supported explanations and remaining ambiguity

| Possible cause | What this episode establishes | What it does not distinguish |
|---|---|---|
| Model preference / insensitivity | At these exact inputs, available grip actions score above every translation; they are genuine model outputs. | Intrinsic weight preference versus interface mismatch; complete state insensitivity is not proved by alternation with changing gates. |
| Insufficient task-relative state | Goal, target-relative XYZ and distance are present; articulation, affordances, orientation and interaction facts are absent/unknown. | Missing fields as the cause of this first bad choice, or which addition would help. |
| Weak/ambiguous action semantics | Axis, step size and pose/grip retention are explicit. GRASP is described as closing the grip and is executed that way; it is not an automatic reach-and-grasp skill. | Whether the model binds the label to its description, or confuses world axes, units, closure of grip and closure of drawer. |
| Missing action-effect information | Effects are empty; natural soft approach evidence stays audit-only. State and descriptions allow nominal arithmetic but do not state it. | Whether explicit effects would improve this checkpoint's choices; no effects intervention was run. |
| Question / option-order bias | The question specifies a task, not a horizon or local progress criterion. Both winners are position 10. | Last-position preference versus grip/wording preference; lexical overlap with “close” or caution about collision is only a hypothesis. |
| Feedback present but not decision-relevant | New proprioception/geometry/quality are delivered; task progress, prior action and its success/failure are not. | Whether the model uses current feedback, or whether history/outcomes would break the cycle. Missing history alone cannot explain step 0. |
| Gate / execution / decoding defect | Gates allow all translations but allow free-space grip commands too. Tokens, logits, API argmax, validation, controls and observed effects agree. | No evidence of a translation being chosen and lost downstream. Feasibility is not a usefulness filter, and there is no identified executor defect causing this cycle. |

Earlier [mechanism diagnostics](../decision_interface/reference_mechanism_handoff.md) found option-order
and label effects and failed explicit token-selection controls. They also found
controller-semantic problems at other loaded physical states. Those were different
oracle fixtures, histories, instructions and **11-option** conditions. They motivate
caution about blaming only missing perception; they are not matched controls for
these ten-option live inputs. The present two grip actions have no recorded
contract violation. Nothing here promotes a research conclusion or a new interface.

## One smallest next diagnostic — proposed, not run

Run **one frozen step-0 option-position swap**, offline, with no simulator execution:
two calls total in the same model session, baseline then one intervention.

1. Reconstruct the exact step-0 state, question and original ten candidates from
   the exported payload. Use the recorded checkpoint and CUDA/bfloat16 setup.
   Capture actual token IDs, option markers, raw logits and API probabilities.
   Confirm the baseline matches the archived input and GRASP result; if it does
   not, resolve that reproducibility discrepancy before interpreting the pair.
2. Swap only the complete `MV_FWD: world +X 10mm` and
   `GRASP: close grip; hold pose` entries (positions 1 and 10). Leave all other
   entries, state values/bytes, instructions, feasibility and descriptions unchanged.
   Keep ten options and the same temperature. Execute neither returned action.

If MV_FWD (now last) wins, order alone is sufficient to change the choice under
identical world information. That supports positional/context sensitivity, not a
claim of useful geometric reasoning or a universal “always last” rule. If GRASP
still wins in position 1, a pure last-option rule cannot explain this pair; grip
semantics/model-state/question preference remains unresolved. If another token
wins, order still affects the decision, without a simple last-position explanation.
Inspect score changes even if the winner stays GRASP; a stable winner does not
prove order invariance.

This pair is the smallest clean check of the episode's concrete ordering confound.
It will **not** identify all missing-state/effect/prompt causes. Those cannot all be
separated by one intervention; their isolation would require later independent
controls. Do not reorder the live demo, add fields, tighten gates or run a longer
episode on the strength of this proposed diagnostic alone.

## Verification and unchanged scope

This autopsy performed zero inference calls and zero simulator steps. It validated
all 142 chained records, reconstructed all eight exact token sequences and API
probability/confidence results, verified all 17 capture/trajectory artifact hashes
and command-array agreement, and checked the existing replay report's source hash:
73 recorded boundaries, maximum error 0. The latter is a check of preserved replay
evidence, not a newly executed replay or a second policy rollout.

Run the [extraction script](../../../runs/engineering-demo/decision-autopsy-feedback-v02-v01/extract.py)
in the existing LocateAnything environment to reproduce the audit into a fresh
directory. It loads the local tokenizer/config only, never model weights or the
simulator. The original episode hash is checked before and after extraction.

```sh
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /home/junhongli/miniforge3/envs/locateanything/bin/python \
  runs/engineering-demo/decision-autopsy-feedback-v02-v01/extract.py \
  --output runs/engineering-demo/decision-autopsy-feedback-v02-v02
```

Only this report and an ignored analysis bundle were added for the autopsy. Existing
uncommitted demo work is preserved. No prompt, model input, gate, candidate semantics,
executor or shared component was changed; no action-selection diagnostic was run.
No new task competence, perception accuracy, safety, state sufficiency or formal
research evidence is claimed. The previously demonstrated embodied path and
asynchronous smoke remain valid with their original scope.

## Appendix: complete model-facing states

Pretty printing below changes whitespace for readability; the original one-line
serialized state and exact consumed IDs are in the local bundle. Field values and
key order match the model input. The ordered candidates/question above complete
each call. Audit-only provenance, gates and evaluator values are excluded here.

### Step 0, before GRASP

```json
{
  "effects": {},
  "previous": [],
  "state": {
    "interaction.holding": null,
    "interaction.target_contact": null,
    "progress.remaining_open_mm": null,
    "quality.covariance_calibrated": false,
    "quality.geometry_age_s": 0.0,
    "quality.geometry_valid": true,
    "quality.position_covariance_m2": [
      [
        0.011423,
        0.00112613,
        0.00893404
      ],
      [
        0.00112613,
        0.000115265,
        0.000881641
      ],
      [
        0.00893404,
        0.000881641,
        0.00700553
      ]
    ],
    "quality.semantic_age_s": 0.0,
    "quality.semantic_confidence": 0.909091,
    "quality.semantic_valid": true,
    "quality.temporal_consistency_ok": true,
    "relations.distance_m": 0.218049,
    "relations.height_error_m": -0.100545,
    "relations.tcp_target_delta_m": [
      0.186186,
      -0.0526391,
      -0.100545
    ],
    "relations.xy_error_m": 0.193484,
    "robot.gripper_command": "OPEN",
    "robot.gripper_width_m": 0.0774455,
    "robot.tcp_position_m": [
      -0.207912,
      -0.0144588,
      1.17826
    ],
    "target.position_definition": "query_box_center_with_interior_median_depth",
    "target.position_m": [
      -0.0217258,
      -0.0670979,
      1.07772
    ],
    "target.velocity_mps": [
      0.0,
      0.0,
      0.0
    ],
    "target.visible_now": null,
    "task.instruction": "close the top drawer of the cabinet",
    "task.target_identity": "the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground"
  }
}
```

### Step 1, before RELEASE

```json
{
  "effects": {},
  "previous": [],
  "state": {
    "interaction.holding": null,
    "interaction.target_contact": null,
    "progress.remaining_open_mm": null,
    "quality.covariance_calibrated": false,
    "quality.geometry_age_s": 0.0,
    "quality.geometry_valid": true,
    "quality.position_covariance_m2": [
      [
        0.0112146,
        0.00110557,
        0.00877087
      ],
      [
        0.00110557,
        0.000113237,
        0.000865545
      ],
      [
        0.00877087,
        0.000865545,
        0.00687778
      ]
    ],
    "quality.semantic_age_s": 0.0,
    "quality.semantic_confidence": 0.944164,
    "quality.semantic_valid": true,
    "quality.temporal_consistency_ok": true,
    "relations.distance_m": 0.21806,
    "relations.height_error_m": -0.100573,
    "relations.tcp_target_delta_m": [
      0.186151,
      -0.052757,
      -0.100573
    ],
    "relations.xy_error_m": 0.193482,
    "robot.gripper_command": "CLOSED",
    "robot.gripper_width_m": 0.0218133,
    "robot.tcp_position_m": [
      -0.207877,
      -0.0143409,
      1.17829
    ],
    "target.position_definition": "query_box_center_with_interior_median_depth",
    "target.position_m": [
      -0.0217258,
      -0.0670979,
      1.07772
    ],
    "target.velocity_mps": [
      0.0,
      0.0,
      0.0
    ],
    "target.visible_now": null,
    "task.instruction": "close the top drawer of the cabinet",
    "task.target_identity": "the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground"
  }
}
```
