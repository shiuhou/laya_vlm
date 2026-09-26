# Interaction observability: useful co-motion, unresolved identity and support

2026-09-27. A fixed bottle-body correspondence distinguishes a fresh close/lift
prefix from a fresh open-jaw lift control. The cap correspondence supplies an
adverse case: it leaves the bottle's visible surface despite successful native
forward/backward optical flow. This earns descriptive co-motion evidence in one
seeded development condition, not a holding classifier or manipulation policy.
Runtime `holding=None` and the native controller/executor are unchanged.

## What was run

The frozen [protocol](../../research/interaction_observability_protocol.md) and
collector are commit `2dd31e0`. Each arm starts at the real Task-2 benchmark
init 0 / seed 1, including World's standard ten open-jaw settling controls, and
executes the archived strict-gate primitive prefix 0–16. The only intervention
replaces `close` at step 13 with native `hold` and retains open jaws for the
three lifts. There are no previews, new primitives, control fixes, snapshots,
warmstarts, models, policy decisions, continuation, or full-task gate repetition.
The source primitive selection was privileged. This is a mechanical scripted
sensor diagnostic, not a sensor-selected policy or archived low-level replay.

Both arms completed 17 primitives / 136 controls; each control lasted 0.05 s and
each arm advanced simulator time 0.5→7.3 s. All 104 controls in the common prefix
have exactly equal recorded robot sensors/commands, excluding wall time; all
14 common-prefix RGB images, including reset, have equal hashes.

After step 12 the first world paused. The Codex assistant inspected only that
raw RGB, choosing cap `(223,174)`, bottle body `(216,217)`, and tabletop
`(171,290)` pixels before any close/lift outcome. The same points were applied
to both arms, with no reseeding. **The raw schema incorrectly says human**;
the [provenance erratum](../../research/interaction_observability_annotation_erratum.md)
and append-only run erratum correct this to assistant-provided visual annotation.
There was no human participant or autonomous LocateAnything initialization.

Sensor artifacts were sealed before the separate evaluator buffer was written;
sensor-only analysis was sealed before evaluator labels were opened. OpenCV
4.11.0 LK uses the prior unchanged defaults. No thresholds or probabilities were
fit. The reader exports direct finger encoders/velocities, returned robot
observables, scratch-FK TCP, raw aggregate wrist force/torque, commands and read
times. Raw wrench/observable sample times are explicitly unknown; returned
finger qpos differs from the current encoder by up to 0.192 mm in this trace.
Render read times are not asserted to be exact derived-geometry sample times.

## Observations

All displacements below start at the frozen pre-close image and end after the
third lift. Evaluator measurements never correct a sensor output.

| Measurement | Close/lift | Open-jaw hold/lift |
|---|---:|---:|
| Robot TCP vertical displacement | +114.133 mm | +114.320 mm |
| Body-point RGB-D vertical displacement | +109.810 mm | 0.000 mm |
| Cap-point RGB-D vertical displacement | +112.942 mm | −153.826 mm |
| Evaluator bottle-center vertical displacement | +113.400 mm | −0.00144 mm |
| Body point on visible bottle geometry | 33/33 frames | 33/33 frames |
| Cap point on visible bottle geometry | 33/33 frames | 14/33 frames |
| Native flow success after seed, each bottle point | 32/32 | 32/32 |

The body endpoint has a 4.323 mm vertical residual relative to TCP in the close
arm, versus −114.320 mm in the open arm. Both seeded bottle points therefore
provide useful close-arm motion evidence; the body point correctly remains
stationary in the negative control. Actual RGB trajectories show the lifted
bottle in the close arm and the bottle remaining on the tabletop in the open
arm. That image inspection is separate from automated support estimation.

The first cap depth-support error occurs in the open control at **step 14,
control 5**, capture 27: the sampled pixel is outside the evaluator's visible
bottle geometry mask although forward/backward residual is only **0.0011765 px**.
At the previous control it is still on the bottle. The initial departure is
near the cap boundary, not the later obvious large-depth symptom. At step 15,
control 0, depth jumps from 0.934 to 1.202 m; the resulting surface estimate ends
154 mm below its start. Native flow stays successful throughout. We inspected
the first-error RGB crops and separate segmentation overlays. This establishes
off-bottle sampled depth support; it does not identify the replacement geom or
claim that every patch pixel stopped depicting the bottle. Low flow residual
does not certify the semantic/depth support of its reported point.

The tabletop seed fails native flow immediately in both arms and remains
unknown. It was not replaced. Consequently **this probe does not validate an
automated support-separation measurement**. Co-motion alone does not establish
retention against slipping, rolling, external support, or pushing controls.

Evaluator bilateral fingerpad contact is true at close-arm endpoints 13–16,
but true at only 21/32 controls after the seed: it begins at the eighth close
control and flickers false during the first four controls of the third lift.
Both visual bottle points remain on the moving bottle through that interval.
The open arm has zero bilateral controls. Contact-relation continuity, physical
co-motion and task-valid interaction are distinct measurements.

## What the robot-only channels do not establish

The cheapest prior falsifier remains the archived empty-close fixture:
`task2-preflight-dev-01`, records 26 and 54. Eight close controls leave a
**20.813329 mm geometric pad gap**, with no recorded gripper contact; a further
eight close controls reduce it to **1.195033 mm**, still without contact. These
are privileged geometric gaps, not encoder aperture, and contact rows use the
configured force filter. Nonzero width after a finite close does not establish
an object. The portable summary retains exact source hashes and record indices.

In the fresh paired trace, close-arm final encoder aperture is 28.813418 mm and
geometric gap 27.813419 mm; open-arm values are 79.993904 and 78.993894 mm. The
different definitions must not be silently interchanged. These arms have
different jaw commands, so this is not a matched empty-closed aperture baseline.

The raw aggregate wrist-force norm ranges overlap: 4.190–6.012 N in close/lift
and 4.692–5.843 N in open/lift. The XML-backed `force_ee`/`torque_ee` channels
are legitimate wrist sensor analogues in `gripper0_ft_frame`; they carry no
entity ID. Gravity, inertia, gripper configuration, orientation and other
contacts remain in the signal. We did not fit a threshold, subtract an unmatched
baseline, infer intended-object identity, or invent finger tactile channels.
This comparison does not establish that calibrated wrench sensing is useless.

## Integrity and scope

The [integrity replay](../../research/interaction_observability_replay_protocol.md)
was frozen at `c4e4ebe` after recording. Both arms were reset fresh and given
their newly recorded 7-D controls directly, with no rendering or instrumented
sensor reads: **all 272 post-control 51-value simulator states match exactly,
maximum error 0**. This validates the diagnostic's own control replay, not the
historical gate's original controls or policy. Offline report recomputation
reproduces summary, membership, both trajectory figures and the first-failure
figure byte for byte. Eleven focused tests pass. No production/runtime files
changed, and no new Task-2 success evidence was produced.

Raw data are under `runs/autonomous-research/interaction-observability-paired-01`
and `interaction-observability-replay-01` in the main workspace. Review artifacts:

- [Portable summary](interaction_observability_summary.json).
- [RGB trajectory](../../../runs/autonomous-research/interaction-observability-paired-01/evaluation-audit/trajectory-contact-sheet.png).
- [First cap-support failure](../../../runs/autonomous-research/interaction-observability-paired-01/evaluation-audit/first-cap-failure.png).
- [Sensor trajectories](../../../runs/autonomous-research/interaction-observability-paired-01/evaluation-audit/trajectory-sensors.png).

## Minimal next interface and falsifier

An evidence interface would need candidate identity with initialization
provenance, timestamped RGB-D correspondences/support validity, robot TCP and jaw
motion, and an explicit independently observed support-separation field. Keep
identity, correspondence, support and retention unknown separately when absent;
provide raw co-motion residuals without pretending they are probabilities.
Wrist load evidence can be optional, with sensor frame, timing and calibration
provenance. It must never select the intended object by itself. This study does
not justify adding `holding=True` to the runtime.

The highest-information next physical falsifier is a prospectively fixed
**same-closed-command retained-versus-slipping/supported-object comparison**,
with independent visual semantic initialization and an observable support
reference. It tests the live alternatives that the present open-jaw comparator
cannot separate. First establish the condition mechanically, then freeze the
sensor rule; do not tune thresholds or seed selection against these two traces.
Matched empty-closed orientation/dynamics data would be needed separately before
attributing wrist-force differences to retained load.
