# Local grasp transfer to the existing visual atomic interface

Prospective mechanical diagnostic, not autonomous grasping or Task2 completion.
The strongest existing positive witness is the paired bottle close/first40mm lift.
Does the same pregrasp boundary permit GRASP then one10mm MV_UP using the unchanged
visual AtomicExecutor and its unchanged reset-calibrated validator?

## Registered arms and boundaries

Exactly two fresh worlds, close arm then open_hold arm; Task2 bottle/bottom drawer,
init0/seed1, native controller, standard ten settling controls. Regenerate the
original native actions0–12 from the archived strict Task2 gate (no control warm
start, qpos restoration, model, preview, candidate search or recovery). Require
all104 commands, returned robot observations, after-control flattened states and
all14 boundary RGB/depth/K/T arrays to match the prior paired-observability arm.
At13 use unchanged AtomicExecutor GRASP in close and STOP in open_hold. At14 use
one MV_UP, nominal10mm with retained jaw command. Both use eight native controls.
Step13 must match the old close/hold command/state/observation sequence exactly.
Step14 is a new physical intervention; no equality to the40mm lift is expected.

Stop the whole run immediately on source/prefix/state/image mismatch, runtime
error, nonfinite value, unexpected control/integrator count, unexpected robot
contact outside the designated bottle interaction, or unchanged execution
validator failure. Do not continue the other arm after a failure. Save the first
failure and missing comparisons; do not retry, change thresholds, substitute
another movement, extend the lift or run complete placement/closure.

The original prefix is deliberately scripted and privileged-selected. Neither
successful transfer nor sensor recording establishes sensory approach, a model
policy, general grasping or generality. There are no Laya or LocateAnything calls.
Target identity is supplied by the archived experimental condition.

## Measurements and safeguards

Use the original RobotSensors reader and capture schedule, including its scratch
FK and evaluator segmentation renders. Neither updates live physics. Preserve
raw RGB-D and direct/returned proprioceptive histories; wrist sample times and
holding remain unknown. At13/14 passively wrap native mj_step to record BEFORE/
AFTER raw contacts, six force components, direct state and wrist buffers. No
added forward or integration on live data. Verify integration fingerprints around
reads and count25 native integrations per control, Euler2ms. Labels use Task2's
existing strict>0.05N rule, not Task1's1N. Both stages stay separate; no exact
causal or continuous-contact claim is made.

The policy consumes only fixed registered actions. Sensor artifacts are sealed
before separate evaluator labels are written. Evaluator records include bottle
center/bottom, contact pairs, bilateral fingerpad relation, drawer state and
success. Any external-contact abort is explicitly oracle-assisted diagnostic
safety, never a deployable sensor gate. Native contact abort is applied after the
current atomic action; it cannot prevent contact. Treat any above-threshold
robot/scene pair except designated gripper/bottle as unexpected; robot self
contacts also abort. Existing paired baseline contact evidence is retained.

Report actual TCP/bottle displacement, raw contacts and bilateral relation at all
sample stages, grip commands, validator flags, and visual before/after frames.
Report bottle movement and relation continuity descriptively without inventing a
new learned holding threshold. A positive local witness requires both unchanged
atomic validations pass, close-arm bottle rises with bilateral pad contact during
the lift, and open-arm counterpart does not establish that relation. No criterion
is fitted to the results. Final official combined-task success is recorded but is
not an objective of this slice.

## Reproducibility and review

Freeze code/protocol/tests and exact source artifact hashes before dynamics;
independent review must pass. Run on GPU4 with EGL and offline model flags (no
model is used). Preserve environment/package/source identity and full new control
trace. If both arms finish, replay those recorded new controls once from fresh
resets and require every flattened state exact. Replay is verification, not a new
policy attempt. After a failure, stop this condition and interpret it; any next
experiment needs a separate stated question. No production runtime file changes.
