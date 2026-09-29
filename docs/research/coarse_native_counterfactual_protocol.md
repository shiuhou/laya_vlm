# Seven original native options at the archived pre-contact boundary

Frozen before any diagnostic arm execution, 2026-09-27. This evaluator-only
counterfactual asks whether the original seven-option pool contains a one-step
contact-free designated-handle approach at one inspected state. It is independent
of the ongoing passive scene-visibility/robot-FK audits and Qwen capability probe.
It provides no live gate, selected action, ranking, recovery or autonomous policy.

## Exact source and seven conditions

Source: `coarse-initial-point-02/episodes.jsonl`, SHA-256
`e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf`.
Use pre-action boundary25, after the first25 original primitives /200 controls.
The archived initial visually grounded world point remains exactly
`[0.003321375780614755,-0.06019141953353715,1.0961857009378837]` m. No new model call,
point correction, current-visibility claim, target update or action definition is
introduced. Freeze source bytes, original point/candidates/effects, benchmark,
controller-facing code, simulator repositories, versions and protocol in recorded
preflight after a clean code/protocol/test commit.

Execute exactly seven independent arms, in original candidate order:
`MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN, STOP`. Each arm creates its own
fresh top_drawer init0 / seed1 world with the standard10 settling controls, then
replays the exact archived200 low-level commands. This is diagnostic archived
control replay, not a fresh autonomous policy. Restore no archived state or
controller snapshot. Require exact initial and all200 before/after flattened
simulator-state matches, and exact preboundary execution state and returned robot
proprioception. Controller/observable history is produced by the actual replay;
flattened-state equality alone is not described as full controller-state identity.

From that boundary execute exactly one original candidate through the same
`AtomicExecutor` and `RecordingBackend` native implementation: eight native
0.05-second controls, original nominal10mm translations or native hold, unchanged
open gripper command and orientation behavior. STOP is a native hold action with
simulation continuing. All seven candidates execute regardless of preceding arm
outcomes, from their own fresh resets. No winner, candidate admission/filter,
physics-preview selection, target-pose change, new primitive or continuation is
constructed. The original selected `MV_RIGHT` arm must reproduce all eight
archived commands/states/contacts and its original result/evaluator endpoint.
Any mismatch or infrastructure failure stops the experiment, records missing
arms, and earns no retry. Contact and execution-contract violations are measured
outcomes, not retry or tuning triggers.

Use GPU6 for rendering with `CUDA_VISIBLE_DEVICES=6`, `MUJOCO_GL=egl`, and
`MUJOCO_EGL_DEVICE_ID=6`; no model is loaded. The source rendered on GPU4. Keep
native actual-observation assignment timing: an env.step observer may record the
returned observation but must not update `world.obs` before the native caller.
Record RGB-D before/after each arm and native after-control trajectory RGB.
Rendering/read-only evaluation must leave flattened simulator state unchanged.

## Measurements and audit

Retain every own prefix command and before/after state, preboundary robot state,
original point/candidate/effect, each new native control/returned robot observation,
all MuJoCo contacts involving any robot geom with unfiltered normal forces,
geometry identifiers and positions, and execution-contract results. Use the
original **strictly greater than1N** contact threshold as a separate reported
flag. Keep zero/subthreshold rows. Contact sampling is after complete native
controls; earliest integration-substep contact onset remains unknown. Do not add
substep instrumentation or change the controller for this experiment.

Report original nominal point-distance gain, measured fixed-point gain and
measured designated-handle surface-gap change continuously in millimetres for all
seven options. Also report direct drawer-joint motion, cached native handle-center
motion and all success/contact fields with their original semantics. Do not call
cached geometry-center shift identical to direct joint displacement. No fresh
physics forward is inserted to replace native measurement/cache timing.

The primary existential result is whether any option has **zero observed robot
contact rows** and a **strictly positive** endpoint designated-handle surface-gap
gain, without a tuned epsilon. Report zero observed non-handle-contact plus
positive gain and the original1N-threshold counterpart separately. These are
sampled contact-free witnesses, not continuous-time safety certificates. All
outcomes remain in original action order; there is no selected best action.
A valid measured candidate also requires no native execution-contract violation;
report that flag even if the contact/progress conjunction is satisfied.

The offline audit independently checks actual recorded prefix commands/states
against the frozen archive, every new arm's state/control chain and native command
count, source/candidate/point conditions, artifact hashes, and recomputes the
contact/progress conjunctions from raw rows. Preserve all evidence, including
failures. No second seven-arm physical replication is authorized by this protocol.

A useful one-step witness separates lack of any locally progressing option from
failure to select/constrain one. If only hold or retreat avoids contact, that
locates a one-step limitation and motivates a separate detour/horizon/pose/action
question; it does not establish global unreachability. Neither result establishes
sensor observability, a safe deployable gate, controller success at contact,
manipulation success, Laya competence or acquired VLM understanding. There is no
live controller modification or subsequent physical experiment in this protocol.

The archive does not contain full intermediate returned-observation dictionaries.
The exact MV_RIGHT comparison covers every available original command, flattened
state and contact row, plus the complete native result's endpoint robot fields
and evaluator outcome. Newly recorded intermediate returned TCP/gripper vectors
cannot be declared equal to absent archival fields. Equality of the generated
closed-loop commands also constrains the original TCP-feedback timing; no full
hidden controller/observable-cache identity is claimed.

## Append-only pre-execution setup correction

The first preflight at commit `812d99e` failed on `import libero` before the
configured repository loader ran. `coarse-native-counterfactual-preflight-01`
retains run start, failure and termination with all seven arms missing. No world,
reset, control, capture or model call occurred. Move only that import after
`initial_state_inventory`, which uses the original configured LIBERO loader;
freeze this dependency-order correction before preflight02. No physical outcome,
source condition, candidate, measurement or threshold motivates this correction.
The first physical attempt remains `coarse-native-counterfactual-run-01`.
