# Interaction observability sensor probe v1

Frozen before new physical traces, 2026-09-27. This is a mechanical scripted
diagnostic using existing native primitives, not an autonomous policy, original
low-level control replay, Task-2 feasibility gate, or task success attempt.

## Question and fixed comparison

Can a human-initialized, RGB-only bottle correspondence survive closing and
lifting and provide descriptive object/TCP co-motion evidence? The comparator
keeps the jaws open: existing `hold` replaces `close` at archived step 13, and
subsequent translations retain that open command. This is a jaw-command
intervention, not a matched empty-jaw wrench calibration. Native controller,
executor, action durations, task assets, seed 1 and benchmark init 0 remain.

The source is `task2_valid_interaction_gate_failure.jsonl`, SHA256
`6d2b9d347c4fe0576ab7400e4dd0f1995da09ed29f0900fca564ca483d281ce3`.
Execute exactly actions 0–16 in each of two fresh worlds, close condition first.
World's standard initialization includes ten open-jaw settling controls. There
are no previews, model calls, snapshots, restored controller states, recovery
actions, continuation, or retries. Each native primitive normally uses eight
controls; retain actual counts/times and stop on exception, unexpected count,
time nonadvance, or nonfinite sensor values. Failure to grasp is a result and
must not trigger a revised prefix. No full-task success claim is possible.

## Semantic initialization before outcomes

After action 12 in the first world, pause simulation and expose only its raw
agentview RGB. Before action 13, an annotator selects two visible, textured bottle
landmarks and one visible tabletop reference point from that image. Record exact
pixel coordinates, roles, image hash and annotation time. This is human semantic
initialization, not autonomous LocateAnything, calibrated identity, or oracle
truth. No post-close/lift image, trajectory, or evaluator label may inform seed
selection. Save once; no reseeding. The second world must reproduce the seed RGB
and robot sensors exactly through the common prefix; use identical points.

## Sensor and oracle boundary

Record every returned native control: command, before/after simulator time,
returned robot observables, direct robot finger encoders/velocities, raw Panda
`force_ee`/`torque_ee` sensordata in local `ft_frame`, and fresh robot TCP FK on
scratch MjData. Force is aggregate wrist force, not finger tactile contact, and
contains gravity/inertia/other loading. Preserve its frame and timing provenance;
do not subtract unmatched baselines or infer object identity. Joint aperture is
sum(abs(finger qpos)); it differs from privileged geometric pad separation.

Robot observations and MuJoCo derived quantities have sampling/cache semantics.
Record data read time, physics timestep, observable timers and sample status;
do not claim each returned observable sampled at the exact read time. Raw wrench
is read after control and before rendering; its precise sample time is unknown.
RGB-D uses the existing ideal calibrated simulator source, with capture/read
time and state-integrity checks. Record boundary RGB throughout the prefix and
every control during actions 13–16. Data are ideal simulator sensor analogues,
not a validated noisy physical sensor model.

Evaluator-only features, contact names, object geometry and segmentation are
buffered separately during recording because original post-control measurements
cannot be recovered exactly by naive state restoration. They must not affect
control, seed selection, correspondence, or sensor results. Seal/hash sensor
artifacts before writing the evaluator buffer, and seal the sensor-only analysis
before opening evaluator labels. Native World.execute already computes features
internally; this probe does not add oracle-based branching. No contact-list
anonymization is presented as a tactile sensor. Runtime holding stays `None`.

## Frozen analysis

Reuse existing `point_temporal_probe.track_lk` with its unchanged OpenCV 4.11.0
default parameters: 21x21 window, pyramid level 3, count/epsilon 30/.01,
minEigThreshold .0001, forward and backward native status. Track each point from
the shared seed through 32 subsequent controls. Native failure terminates that
point without recovery; native success does not certify identity. Report all
forward/backward residuals and errors, including adverse cases; fit no threshold
or confidence. Depth at the tracked containing pixel center is a descriptive
surface correspondence, not an object pose. Report point/TCP vertical and 3-D
displacements and relative-displacement residuals. Table reference is a visual
stability control, not verified object-support contact or a fitted plane.

Only after sensor results are sealed, inspect evaluator segmentation membership
at tracked pixels, bilateral relation continuity and object motion. Inspect actual
images and trajectories. One successful comparison earns at most observability
in this seeded development condition. Occlusion, wrong identity, co-motion due
to pushing/support, rolling/slip, force calibration, retained load versus intended
object, unseen objects, and real-sensor noise remain unvalidated. The next useful
falsifier is held-versus-slipping/supported co-motion under fixed commands, with
independent human/semantic initialization and no oracle-fed recovery. No generic
runtime retention estimator or thresholds will be integrated from this probe.
