# One initial POINT with live proprioception: physical control v1

Frozen before physical execution, 2026-09-27. The completed fresh-query condition
is `coarse-point-boundary-01`, revision
`b72fcdc494522ea49cb7fd7d9f0b75f2789de49f`, episodes SHA-256
`d9ed0bc2b10b61b047e44ec37a03ea788b4e88e2f8d06edd8171bcd29677f319`.
It first changes semantic referent at boundary 21 and stops on malformed output
at 25. Its first twenty recommendations are also reproducible with the initial
observed point, but that simpler condition has not been physically executed
across the first semantic failure. This run fills that missing control.

## Single physical condition

Create one fresh top_drawer benchmark init 0 / seed 1 world, with standard reset
settling. Execute at most 40 primitives and retain the existing 900-second wall
limit. No archived controls or states initialize or drive the run.

Make exactly one LocateAnything call at the initial RGB-D capture, using the
unchanged checkpoint content ID, query, hybrid greedy settings, input processing,
strict complete-EOS/single-POINT admission and containing-pixel-center depth
projection. Any initial inference/admission failure ends the run without retry.
Copy that initial observed world point unchanged thereafter. Read returned robot
proprioception at each boundary and recompute the existing nominal geometry
effects, seven canonical candidates, lexical tie-break and rule recommendation.
Use the existing native controller, AtomicExecutor and action durations.

This is an explicitly different admission policy,
`initial-point-live-proprioception-v1`. The initial geometry is accepted under a
stationary-target assumption; current validity is unverified. Both target geometry
and semantic age increase from the initial capture's simulator time. Record the
source capture identity/time separately from each new decision and proprioception
read time. Returned robot observables have no newly asserted exact sample time.
Do not refresh target time, infer zero covariance, manufacture confidence, set
current visibility true or fill target velocity/contact/holding. The default
runtime's uncertainty/freshness gates are not validated by this override.

Capture RGB-D at each boundary and preserve native trajectory images for audit,
but do not consume later RGB, depth or model predictions in target estimation.
There is no tracker, semantic correction, action preview, Laya motor call,
grasp/rotation policy, recovery, Task-2 activity or automatic budget extension.
The common runner receives only an optional grounding hook; its default fresh
mode and shared selector/controller/executor functions retain their behavior.

## Existing stops and full provenance

Preserve stop on invalid initial POINT/depth/generation, paused-state change,
execution-contract violation, new robot-contact pair over the existing **1 N**
threshold, rule STOP, runtime failure, wall limit or action budget. Contact abort
remains at completion of the atomic action containing the first sampled contact;
do not alter its native controls or execute a later primitive. Contact rows cover
all robot geoms, including arm/self contacts, and retain zero-force rows. This
external privileged abort is not an oracle-free safety guarantee. Sampling after
native controls does not identify the first integration-substep contact.

Record the full initial model input tensor/token arguments and actual generated
tokens; preserve all captures, fixed-point source records, increasing ages,
canonical evidence/effects, selected actions, actual controls and simulator
states, evaluator-only contact/distance labels, execution contracts and failures.
Record CUDA and EGL device assignments. The first model call must be completed
before any primitive. A GPU change from the historical run is disclosed and
checked via actual initial model input/output equality, never assumed harmless.

## Audit and causal interpretation

Independently compare this fresh reset, initial image/model input/output/point,
every matching-prefix primitive/control/state and image with the archived
fresh-query run. Locate the first differing selected action. At its boundary,
verify equal physical state and proprioception and independently recompute both
rules from their respective fixed-initial and newly grounded points. Any earlier
physical/model discrepancy is reported, not repaired by warmstart or retry.

At the first physical boundary, inspect actual RGB images and raw contact rows,
including simultaneous contacts and designation of the contacted robot/object
parts. Preserve designated-handle relation only where actually evaluated. A
contact followed by executor violation in the same primitive is reported as both.
Full actual-control replay from another fresh reset must compare every newly
recorded control's before/after state, including partial primitives. This replay
uses no perception and does not claim independent policy replication.

The primary outcome is whether the initial-point condition crosses the prior
semantic failure and which boundary ends it. Contact or reaching a small point
distance does not establish useful handle interaction, sustained contact, task
success or general point-interface sufficiency. Fixed target/camera geometry is
a causal limitation. No temporal-perception benefit can be claimed from an arm
that deliberately performs no temporal target sensing. Report target/camera
motion observed post hoc without feeding it into control.
