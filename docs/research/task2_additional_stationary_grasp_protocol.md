# One additional stationary GRASP interval after each fixed POINT approach

Status: preparation only. No new dynamics before the independent exact-freeze
review and root release naming the clean freeze and no-world preflight receipt.
Use the literal closed-source `laya-embodied` Python environment with GPU4/EGL4.

## Hypothesis and fixed design

The completed four-cell source shows both final first-GRASP endpoints without raw
robot/bottle contact or bilateral pads. Whole had no contact during GRASP; neck
had brief unilateral pad contact earlier in GRASP, then none at its endpoint.
Bilateral contact developed during the following lift. Atomic command completion
therefore did not establish the contact relation before lifting.

Test exactly one additional existing GRASP primitive in both fixed anchor cells.
Order: `whole-close`, then `neck-close`, each once in a fresh normal seed1/init0
world, each followed by its separate exact recorded-control replay. The additional
interval is prospectively fixed for both anchors; no sensor/evaluator response can
skip it, add another interval, change a token, tune a target or choose a winner.
No additional open-control dynamics are registered.

Reuse the same initial frame gate, admitted cached native POINT, full BOX support,
endpoint geometry, unchanged approach policy, executor, control duration, jaw
semantics and validation/contact thresholds. Approach STOP executes no hold.
Preserve the existing 40-action and 900-second per-collection limits.

## Fresh prefix and exact intervention schedule

1. Regenerate the original approach from policy and live own observations. Verify
   its full scientific prefix against the same closed whole/neck approach source,
   exactly as in the four-cell experiment. No archived commands or restored state
   are used to generate it.
2. Execute the original first GRASP, phase `close_or_hold`, for eight controls.
   Preserve its native snapshots, returned own packets, eight auxiliary RGB-D
   captures, primary endpoint frame and validation result exactly as before.
3. Before any second-GRASP control, verify the completed scientific prefix through
   that first-GRASP endpoint against the matching closed four-cell source. Compare
   every scientific record including approach verification, terminal decision,
   commands, before/after states, own observations, all native snapshots, action
   results, endpoint, and primary plus first-eight auxiliary RGB/depth/K/T arrays,
   IDs, times and metadata. Ignore only run-start provenance/journal wall-clock
   envelopes; image hashes bind each artifact independently. Any difference stops
   both-cell work before the second GRASP. The comparison never returns commands.
4. Execute exactly one additional existing GRASP, phase `additional_close`, for
   eight controls with retained jaw +1. This is the only intervention change.
5. Execute one original nominal 10 mm MV_UP, phase `lift`, for eight controls with
   retained jaw +1. Its target uses the current post-additional-GRASP TCP, exactly
   as the unchanged executor normally does.

Each primitive has 200 native integrations, 25 per control. Total suffix: three
primitives, 24 controls, 600 integrations and 24 auxiliary endpoint images. The
old first-GRASP action/capture IDs remain unchanged. The added interval gets its
own absolute step/native phase. The same separate auxiliary camera/counter and
sensor manifest/seal are reused; no image or label influences the fixed schedule.
All 24 auxiliary images are included in exact verification replay, alongside the
complete native, command/state/own and primary-image checks.

This is an additional closed-jaw interval/primitive exposure. "Stationary" means
the existing GRASP's nominal arm hold; measured translation and rotation drift
remain possible within its original validator tolerances and must be reported.
The intervention does not isolate pure closure latency from added elapsed time,
continued closed-jaw control, arm drift or contact rearrangement.

## Unchanged aborts and complete negative evidence

Reuse `local_grasp_interface.require_pass`, its tolerances, and its exact
`unexpected_contact` predicate with strict >0.05 N threshold and broad existing
gripper/bottle allowance. Preserve the complete action result, native evidence,
endpoint and captures before checking a completed primitive's abort conditions.
Validator, runtime, native/control count, unexpected-contact, prefix or replay
failure stops the batch with remaining actions/cells unrun. No retry. Preserve
approach-qualified collector failure counters and suffix total counts/current
step/phase/token. Normal absent/weak contact or lift is a retained result, not an
execution failure. No contact-dependent early continuation or stopping is added.

## Registered measurements and comparison limits

Prediction if insufficient closed-jaw time was limiting: bilateral designated-pad
contact is present at the final additional-GRASP endpoint BEFORE lift, and at all
200 lift BEFORE samples plus all 200 lift AFTER samples. Use the original strict
pad normal-force >0.05 N predicate; do not fit a new threshold or infer continuous
time behavior from native sampled stages. Also report all eight lift endpoint
bilateral measurements, bottle center/bottom change relative to the added-GRASP
endpoint, and each GRASP's measured arm translation/rotation and own jaw motion.

Alternative: prelift bilateral contact remains absent, or bilateral contact still
fails at some native lift samples; geometry, slip, continued closure or other
contact dynamics remain unresolved. Do not assign a mechanistic diagnosis from
these two cells alone. Report trajectories even when the stated prediction fails.

Compare descriptively with both sealed one-GRASP close sources and their sealed
open-hold controls. The old close/open matched witness remains as previously
registered and reported. The new close-only two-cell experiment does not inherit
that four-validation witness: the old open controls lack the added interval.
No new positive witness or holding classifier is introduced.

Retain and report every raw and >0.05 N contact family separately: pads, fingers,
hand, other robot links and bottle/scene support contacts. Disclose simultaneous
bilateral and non-designated contacts, even raw zero-force rows. Preserve the
separation between designated-pad relation, native maintenance, actuator
validation, contact mechanism, support-free retention and official task success.
Bilateral plus rise alone is not a clean interaction-valid grasp. Bottle rotation
remains unknown unless a previously recorded source-specific mapping supports it.
Privileged labels stay buffered until sensor-only sealing and cannot choose any
command. No production runtime/controller fork or new geometry tensor audit.
