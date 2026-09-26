# Robot-only geometry from own joint positions: offline probe v1

Frozen before archived-state numerical comparisons, 2026-09-27. The question is
whether known robot calibration/geometry and its own scalar joint encoders can
supply link, TCP, finger and pad poses/extents absent from the coarse point/TCP
interface. This is an information-dependency and kinematic correctness probe,
not a controller, collision filter, contact classifier or safety validation.

## Fixed inputs and sensor semantics

Use only `coarse-initial-point-02/episodes.jsonl`, SHA-256
`e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf`.
Select exactly four states without search:

1. Initial `environment.sim_state`.
2. Action 25, control 0, `state_before`.
3. Action 25, control 0, `state_after` (first recorded contact sample).
4. Action 25, control 7, `state_after` (endpoint).

The historical run stores full simulator time/qpos/qvel, not an independent
stream of joint encoder measurements. A separate archive adapter will extract
only seven arm and two finger joint positions using static named-joint indexing
metadata. Call them **simulator-state-derived own-joint encoder analogues**.
Do not call the full state a robot sensor or claim real sensor accuracy. Pose
estimation does not require velocities; no object qpos/qvel, contact, target,
camera or scene surface is admitted to the estimator.

## Static robot calibration and standalone estimator

Construct the standard top_drawer model only to recover its static robot model
and to provide a separate evaluator. Do not use `World`, reset, `set_init_state`,
native controls or replay. Block `mj_step`, `mj_step1` and `mj_step2`; require the
constructor's simulator time to remain zero. The library may initialize qpos and
forward caches during model construction. Record that setup explicitly; if it
requires dynamic stepping, stop and report it rather than disguise it.

Export a standalone robot-only JSON containing the fixed robot root transform,
its descendant body/joint chain, TCP and force-frame sites, and all collision
geoms in its gripper subtree. Require exactly the registered nine own scalar
joints, with hinge/slide type, body-local anchor/axis and `qpos0` reference.
Reject any root with a non-world parent or any unsupported joint. The fixed root
position/orientation in the world frame is **assumed known base calibration**;
its real-world calibration accuracy is unvalidated. Do not export scene/object
bodies, geometry, joint coordinates or task contact selectors to the estimator.

Use compiled static mesh vertices for mesh collision shapes and all eight box
corners for pad boxes. Unsupported geometry stops the probe. These are known
robot collision proxies, not sensed surfaces or validated complete physical
envelopes. Report both rigid transforms and transformed vertex-set AABBs; AABBs
are axis-aligned extents, not collision-free space.

The estimator is a separate process receiving only the standalone robot JSON
and own-joint dictionaries over stdin. Pure NumPy code computes parent-first FK,
handling nonzero fixed-base transforms, body quaternions, hinge anchor/axis,
scalar `qpos-qpos0`, and signed slides. It has no simulator, environment, task,
archive path, object-state or evaluator API. Its algorithm must have no robot
or task-name branch. Missing, extra or nonfinite own-joint inputs are rejected.
Keep caller metadata, archive source identity and times outside the pure FK.

## Frozen comparisons and leakage controls

Seal standalone estimates before evaluator transforms are computed. For each
of the four archived states, create fresh evaluator MjData, set the recorded
qpos/qvel/time and run **`mj_kinematics` only**. Compare every exported robot body,
site and gripper collider's position/rotation, transformed vertices and AABB.
The fixed tolerance is `1e-10 m` for positions/vertices/extents and `1e-10` for
rotation-matrix elements; do not tune it after results. This compares independent
FK calculations on the same qpos. It does not recover original cached post-control
contact-time transforms or validate robot model/calibration accuracy.

For each archived state, poison all non-robot qpos/qvel before archive extraction
with (a) NaNs and (b) the fixed finite sequence `1234.5 + 0.25*i` over excluded
indices. Keep time and own joint values unchanged. Do not run MuJoCo on poisoned
states. Require the extracted own-joint dictionaries and standalone FK outputs
to remain exactly equal to their unpoisoned counterparts. The estimator receives
the sanitized dictionaries only. A guarded-index unit test must also raise if
the extractor even attempts to read a forbidden full-state coordinate.

As positive dependency controls at the pre-action-25 input, independently add
0.01 rad to the first calibrated hinge, and 0.001 m to the first calibrated
finger slide. These are synthetic encoder variations without dynamics. Require
each to change some selected gripper vertex by more than `1e-8 m`, so a constant
output cannot pass the poisoning test. Do not use these variations for action
selection, physical feasibility, safety or task claims.

Synthetic unit tests cover a rotated/translated base, nonzero hinge anchor and
reference position, signed slide reference, site offsets and known box extents.
Compare recomputed TCP to archived returned TCP at initial, pre-action-25 and
endpoint only as descriptive sampling evidence, not as a pass/fail correction;
those observable sample times were not recorded. No target geometry is read.

## Interpretation

A pass earns a robot-only own-body pose/extent source under accurate static
calibration and joint sensing. It does not earn scene obstacle observability,
swept-volume correctness, safe action admission, force/contact inference,
retention, collision avoidance or a manipulation policy. It may motivate richer
own-body fields than a TCP point and scalar jaw width, but no runtime interface,
controller, gate or policy is changed in this probe. Publish all raw source
indices, calibration hashes, sanitized process inputs, sealed outputs, evaluator
results, poisoning results and failures.
