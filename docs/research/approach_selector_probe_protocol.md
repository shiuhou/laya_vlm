# Sensor-derived approach selector probe v0.1

## Registered question and scope

Does Laya provide useful bounded nominal approach decisions when the existing
deterministic distance selector already has the same sensor-derived geometry?
This is one fixed 12-call offline experiment, not another wording search, a
manipulation success claim, or an oracle-corrected perception condition.

Use six development boundaries from the archived reference-pilot collections:
init0 steps 0, 20, 24, 29; init1 step 0; init2 step 0. These were inspected before
registration and are not held-out samples. They expose target-estimation bias as
well as candidate ranking. Source JSONL SHA-256 values are:

- init0: `d24b0d3d1d73c7618f69bb806168a719301e5806ddf6b68fec2dcc1e3e6a8b58`
- init1: `95dc765928d5af123035a248efc7a89a6d590079d927ee59f8524e0c3d07432a`
- init2: `41d07e9c6ed5db0bc28404ba5856ae71338981935852a12ef2aed180679ac1a5`

## Fixed information and decision boundary

Use only each preserved `perceptual_state`, proprioceptive history and natural
perceptual candidate pool. Reconstruct `VisionCandidateBuilder` from its recorded
configuration and belief snapshot; require every candidate, validity reason,
allowed mask and canonical order to match the archive. Do not restrict the pool
to translations, rerank it or introduce a new contract. GRASP/rotations/STOP remain
present whenever their existing gate allows them. Maintain all original unknowns,
uncertainty, freshness and calibration flags. Historical acceptance of a box does
not establish its correct target identity or complete generation; disclose this
limitation rather than treating these snapshots as validated visual ground truth.

Use the existing `reference_model_diagnostic.APPROACH_INSTRUCTION` exactly:

```
Minimize TCP-to-target Euclidean distance with one nominal 10mm world translation. Leave the gripper unchanged. Choose STOP only if no translation improves distance. This is a geometric command test, not a contact or dynamics prediction.
```

There is no hand-authored contact premise. The full structured perceptual state
and recent proprioceptive outcome remain available. Use `geometric_effects()` to
derive distance and XY-error changes for each allowed translation. Other actions'
effects stay unknown. This is nominal deterministic geometry, not simulator
preview, collision certification, grasp prediction or expected physical motion.

Use one compact effect presentation: column names `distance_change_m` and
`xy_error_change_m` appear once; each candidate maps to the corresponding pair or
null for unknown. Shared source, nonprivileged status and stationary-target /
nominal-10-mm / no-contact-dynamics assumptions appear once. Preserve the complete
raw effect bundle and evidence metadata in records. No numeric precision is lost
beyond the existing six-significant-digit canonical model presentation. Verify
that the existing rule selects the same token using full source precision and the
rounded model-visible delta; do not silently fix any mismatch.

The deterministic comparator is the existing `CanonicalDecisionInput.rule_token()`
on exactly that allowed set. It minimizes nominal distance among translations and
otherwise returns STOP. It is explicitly a policy comparator, not an expert label
or model competence. No selected token or evaluator result enters Laya's input.

## Execution and audit

Freeze six fixtures; call each twice, forward then reverse fixture order, retaining
candidate order. Exactly 12 Laya calls, same typed-decisions checkpoint/configuration,
seed 1 and dtype as the reproduced current-motor reference. No simulator or vision
model is run. First perform a CPU tokenizer-only preflight: exact installed Laya
sequence builder, all candidates retained, no heading/option/state truncation.
GPU inference must match these exact consumed input IDs/markers and frozen code,
protocol/model hashes. Preserve raw logits, outputs, cardinality temperature,
failures and missing calls; do not retry invalid output.

Report each choice alongside the deterministic token, sensor nominal gain, best
available sensor gain and regret where an effect exists. Nontranslation effects
remain unknown; do not assign a fabricated zero effect. Separately identify any
gripper-change choice contrary to the stated objective. Verify repeatability.

Only after a choice exists, evaluate the same nominal displacement against the
archived oracle visible-handle reference. Keep these evaluations in separate
records/reports; they cannot change model input, allowed actions or rule choice.
Report whether sensor bias changes the preferred translation. Neither nominal
oracle geometry nor a low regret predicts loaded-contact controller behavior.

## Consequence for the next physical slice

This experiment does not implement a live policy. Its next empirical question is
whether a fresh-reset, at-most-20-primitive nominal-rule approach produces useful
physical progress relative to a matched active-hold baseline. That physical test
must separate target-estimation failure, action ranking and actual controller
displacement; strict live perception failures remain failures. A Laya physical arm
is warranted only if these offline choices demonstrate useful approach behavior.
The rule/hold slice remains informative even when Laya fails. No full manipulation,
VLM contribution or real-robot capability is established by this probe.
