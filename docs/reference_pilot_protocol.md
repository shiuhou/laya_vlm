# Reference-quality pilot protocol (not a formal E0 freeze)

Declared before new reference-pilot model choices, 2026-09-23. Starting code:
`0141a70`. No formal E0 dataset, tag, policy evaluation, or parameter tuning.

## Questions and bounded sampling

1. Do the two position fields estimate a common, explicitly defined target?
2. Does the no-effect oracle-conditioned model have useful local task behavior?
3. Does recorded-control transfer cover phases across actual benchmark resets?

Use archived `jev-libero/examples/records/top_drawer_seed1` controls, seed 1.
Primary initial state 0, boundaries **0,20,24,29,33,48,80,120,140,144,152,155**.
These are chosen from existing telemetry for far/approach/near-contact/contact/
progress/near-completion coverage. Boundary 155 is a **terminal sentinel**, not
an ongoing-task accuracy example. Twelve states are correlated, not independent n.
Additional initial-state IDs **1,2** receive the same 155 controls, without asserting
archive identity. Preserve every outcome, missing phase and failure. A few paused
RGB-D pairs may verify pairing there; no large collection grid.

## Common target estimand

Use the **visible-pixel-weighted world-space surface centroid of the top drawer's
metal handle**, from the fixed agentview camera. This is explicitly view/occlusion
dependent, not a rigid object center, grasp center, collision AABB, or complete
drawer pose. An invisible handle has unknown oracle visible-surface centroid.

Perception estimates handle membership using the first box from one fixed query:
`the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground`.
Its box-support RGB-D centroid is a deliberately approximate surface estimate;
background/occluder contamination and wrong-instance selection are measurement
errors, not oracle-corrected inputs. No learned segmenter or ground-truth box is
supplied to perception. Independent oracle first-hit visual-mesh camera rays
define the ideal visible handle support and its centroid. Save both masks/supports,
membership overlap and old AABB / box-center-with-median-depth representations.
Do not conflate a shared estimand with a proven accurate or calibrated estimator.
If visibility or identity makes the comparison undefined, report missingness.

## Primary model interface

Same model/checkpoint/API, compact-v0.1 presentation with clipping rejection,
question, shared 11 semantics-only atomic probes, one previous proprioceptive
outcome, and **empty effects** on both branches. Simulation pauses during vision.
Use three identical-input repeats with RNG seeded once; alternate branch order.
Rule is a deterministic comparison, not the expert label. No chosen probe executes
in the collector. Keep legacy mismatched/truncated artifacts untouched.

## Independent evaluator, before reading new model choices

Execute each of the **offered 11** tokens through AtomicExecutor in independent
full Jev snapshots. Restore backend grip as well as MuJoCo/controller state.
Record physical endpoints, commands, contract residuals, contacts/forces and
official success. Repeat STOP to check restoration; verify ongoing init-0 replay
against the archive within the existing 1e-8 tolerance. Evaluator records never
enter candidate metadata, current state, history or the no-effect Laya prompt.

Report raw closure, closure minus STOP, surface approach minus STOP, contact,
obstacle pairs and forces. STOP can make progress through residual dynamics.
Native actions stop early upon success: report unequal durations and do not call
their differences equal-horizon causal effects. Reset-calibrated atomic residuals
in contact are diagnostics, not automatic task-failure/safety labels.

Predeclared local utility: no new sampled obstacle pairs and no obstacle endpoint;
then completion, otherwise incremental closure >=0.25 mm, otherwise nonregressing
incremental contact or >=2 mm approach without >0.25 mm closure loss. These are
existing task conventions, not fitted/calibrated safety thresholds. A set-valued
near-best reference uses closure ties within 0.25 mm and approach ties within 2 mm.
Report useful local support separately from membership in that near-best set.
Commanding GRASP/RELEASE alone is not useful-task evidence. No observed one-step
utility means **unresolved preparation**, not proof that a long-horizon action is
wrong. Terminal preservation is labeled separately.

No threshold changes based on model results. Do not turn this pilot into an
accuracy score. If no-effect oracle choices lack demonstrated utility, recommend
a descriptive fidelity claim or a separately reviewed interface/effect condition;
do not silently redefine the primary State-Gap comparison.

## Recorded implementation correction (before any formal freeze)

The first pilot collection used ID-color segmentation/render depth and integer
pixel indices (`...centroid_v0.1`). Raw inspection found isolated false handle-ID
pixels elsewhere in the scene. A geometric first-hit ray oracle removes those
ID-color artifacts without using model choices or changing utility thresholds.
Camera audit also established the raster convention: with K principal point at
`(W/2,H/2)`, flipped raster pixel centers are `(u+.5,v+.5)`, not `(u,v)`.

The corrected **referent v0.2** uses that convention for both sensor centroid and
oracle rays. The original live bbox-center/median-depth path is unchanged; its
continuous box-center coordinates must not receive an automatic half-pixel shift.
Original `init*-attempt1` and `replay-init0` artifacts remain available but are
not the final common-referent evidence. One explicitly labeled recollection/replay
checks the correction on the same states, query, candidates, question, history,
model bytes and rubric. It is not a success-conditioned retry or a new seed search.
Ray-vs-raster depth residuals remain recorded, not hidden by mask correction.
