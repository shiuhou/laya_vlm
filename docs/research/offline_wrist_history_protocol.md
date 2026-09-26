# Frozen offline wrist-history comparison

Freeze before inspecting wrench/contact associations. No new physics, model,
calibration, mass model, threshold fit, classifier or deployment. Use only the
completed canonical Task1 native observation archive, episodes SHA-256
`e8e253cefe4c694c6091e1bf944a8f269cfc47c7ed08c053419d97e1a73615d4` at
`runs/autonomous-research/task1-native-contact-run-01` under the canonical runtime
worktree. All970 controls and24,250 native calls remain in original order.

## Question and fixed sensor features

Does within-control wrist history discriminate gripper/scene interaction better
than endpoint-only sampling of the same native sensor values on this trace,
especially where endpoint contact sampling misses transient interaction?

For each50 ms control, take the first native BEFORE buffer as the fixed baseline
F0/T0, and all25 AFTER buffers as the observation sequence. Endpoint is its last
member. Retain force and torque independently, without combining or rescaling:

- endpoint_force_change_N = Euclidean norm(F25 - F0);
- temporal_force_change_N = max_i Euclidean norm(Fi - F0), i=1..25;
- endpoint_torque_change_Nm = Euclidean norm(T25 - T0);
- temporal_torque_change_Nm = max_i Euclidean norm(Ti - T0), i=1..25.

Use exactly the recorded local-site axes and native stage values. The sensor site
rotates with the gripper; do not insert world rotation, gravity subtraction,
dynamics compensation, baseline fitting, smoothing, clipping or a sample-rate
change. Actual sensor sample time remains unknown; buffer read time, Euler2 ms
native interval and BEFORE/AFTER stage are retained. These are simulation sensor
analogues, not calibrated hardware force or holding estimates. The temporal
metric includes the endpoint and therefore cannot be smaller; that algebraic
property alone is not improved contact discrimination.

Project an explicit sensor-only file from the frozen raw records first: primitive/
control indices, native times, wrist buffers and sensor metadata only. Seal it by
hash before generating features. The feature function accepts only this sensor
file, never native contacts, drawer motion, generalized forces or evaluation gold.
Seal all970 feature rows before the contact evaluator writes its labels.

## Separate fixed contact evaluator and cohorts

Use only AFTER contact buffers for primary gold, matching the observation sequence
stage. Native force rule stays strictly greater than1 N. The declared gripper
collision group is the gripper-side/downstream-contact proxy; the declared arm
group is upstream. Report these as measured contact groups, not a calibrated
wrist load-transfer model. Robot self-contact is any pair with both robot sides.

For each control, record whether any AFTER sample contains gripper/external-scene,
arm/external-scene or robot-self contact. External scene excludes all robot geoms;
retain whether the scene side is the drawer separately. Partition all970 controls
into `gripper_only`, `arm_only`, `gripper_and_arm`, `no_robot_scene_above_1N`, and
`self_contact_present` (self has precedence). Labels count physical contact
membership, without input from wrench magnitudes. Raw subthreshold contact counts
remain descriptive; absence of >1 N contact is not literal contact freedom.

Primary comparison: `gripper_only` positives versus
`no_robot_scene_above_1N` negatives, both without self-contact by construction.
Report arm-only, mixed and self cohorts separately instead of blending upstream
loads with the gripper target. If either primary cohort is empty, report the
comparison undefined, without changing cohorts.

For endpoint-missed gripper interaction, use the prospectively defined subset of
`gripper_only` controls with at least one earlier AFTER gripper contact but none
in the last AFTER sample. Preserve every such control with primitive/control and
native interval indices, four feature values, and ranks relative to primary
negative controls. Do not select examples after viewing which feature looks best.

## Fixed descriptive evaluation

For force and torque separately, report endpoint and temporal empirical AUROC
(positive-vs-negative pairwise ordering, half credit for ties) and their difference.
Also report group min/5th/median/95th/max values, overlap counts relative to the
negative cohort's observed range, and counts. No threshold choice, classifier,
significance test, confidence calibration, train/test claim or optimized metric.
Compare all positive controls and the fixed endpoint-missed subset separately to
the same negative cohort. Persist all970 features and labels, including excluded
cohorts. The force comparison is primary; torque is a separate secondary channel.

Controls, primitives and repeated contacts come from one trajectory and are not
independent test cases. Acceleration, gravity, changing local axes, controller
transients, preceding contact and wrist-stage cache timing can change these
features without current gripper contact. Association or a higher AUROC does not
isolate contact force, infer holding, establish generalization or authorize a live
gate. Describe overlap and any disagreement with the hypothesized benefit plainly.

Commit protocol/code/tests before extraction/features/evaluation. Send this minimal
protocol to the parent and joint_interface for review before wrench/label analysis.
Tests cover same-baseline feature arithmetic, ties/rank direction, strict contact
thresholds, upstream/self separation and no gold keys in sensor/feature schemas.
An offline audit rehashes source/projection/features/labels, reconstructs scores
and checks the complete970-control lineage. No simulation object is constructed.
