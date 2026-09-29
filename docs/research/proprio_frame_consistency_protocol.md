# Offline proprioceptive frame consistency audit

Audit fixed stored local-grasp02 evidence and the sealed Task2 BOX point. No
physics, model inference, renderer, FK, target fit, policy, or runtime edit.
Use the independently reviewed static body-to-site relation from `3065e87`;
the purpose is empirical frame accounting and bounded interface dependency.

Use all 240 local-grasp sensor rows and all 30 saved primitive-end site rotation
matrices. The four AtomicExecutor interventions additionally supply before/after
site matrices and native rotation validators. Read the initial robot sensor
packet from the earlier paired archive's close-arm endpoint -1 because the
local-grasp collector did not save a separate initial robot sensor packet.
Its initial RGB-D is byte-identical to the BOX source; preserve that provenance
distinction and never imply identical historical sample caches.

Compose the fixed right_hand→right_gripper→eef→grip_site transform from the
sealed own-robot calibration, rejecting any joint on that static chain.
Returned `robot0_eef_quat` is XYZW for the right_hand body; predicted site rotation
is R_body·R_body_to_site. Compare it and the unadjusted body rotation against the
saved scratch-FK site matrix for every sensor row. Also compare saved wrist-site
and TCP-site rotations. At all 30 action endpoints compare against the saved
native cached site matrix separately. Report min/median/max rotation residuals
and full rowwise results. Saved returned-site versus scratch-site position
differences are descriptive cache/time discrepancies, not a body-origin check.
Actual returned sample times remain unknown; small corrected residual is not an
exact same-time validation. No archived matrix is recomputed with a simulator.

Check four recorded AtomicExecutor orientation deltas and thresholds from saved
site matrices. Compare against relative body-quaternion deltas and show the
constant-mount cancellation algebra. These are different caches, so their small
differences do not authorize replacing the recorded validator or its inputs.
Translation/body-origin verification remains unknown because no independent
world body-position measurement is saved in these sensor packets.

Quantify a clearly hypothetical misuse: applying the unadjusted body matrix to
static TCP-local pad-center offsets at the same saved returned TCP position.
Compare with the properly mounted matrix at each row's direct finger joints.
No result is a fitted target offset or a contact/clearance claim. Express the
unchanged initial BOX point in both axes using only the initial sensor packet;
this illustrates coordinate interpretation, not a new target or grasp pose.

Exercise the existing backend proprioception method on stored robot-only
packets using a guard that rejects quaternion reads and forbids features or
execution. Construct canonical model-facing states/effects from those outputs
and the unchanged BOX point, with no action chosen or model invoked. Compare
with an orientation-poisoned packet: model input/effects must be identical.
Report whether the schema exposes orientation, and whether GRASP effects remain
unknown. Source hashes must match the archived local-grasp core modules.
Inspect recorded GRASP low-level rotation commands separately; do not execute
the interface. These checks apply to this version and inspected call path,
not every external consumer of raw robot observations.

Small synthetic checks cover XYZW/WXYZ conventions, multiplication direction,
constant-frame cancellation and guarded input dependency. Freeze audit/code
before numerical analysis; preserve hashes and unknowns in a standalone report.
