# One canonical Task1 native-contact observational replay

Frozen prospectively before any replay dynamics. This asks whether the historical
control-end measurement of zero designated fingerpad/handle closure missed
designated contacts inside native controls. It observes one archived successful
trace and does not rerun its policy, model, previews, selector or recovery.

## Exactly one source and replay

Canonical source:
`runs/privileged-reference/local-objective-task-adapter-episode-01`, under
`/home/junhongli/projects/laya-embodied-runtime`.
Its source identities are episodes SHA-256
`9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`,
manifest `a19ddc51c95e094be6d4dbac3fbb1271902de30ede8f630d432c8e40f9ec4b2a`,
reference-evidence `063ad9585ca4bd5c9c5e7dbedff39efe522d51261a5a5e2e8246a94653cba008`.
Freeze all122 trajectory NPZ hashes and commands/state arrays before dynamics.
Primitive indices0–120 have8 controls each; primitive121 has2, totaling970.
Preserve that final shortened primitive and official success, with no added hold.

Use the established `interaction_boundary_audit.audit_task1` reset/replay path:
fresh `TOP_DRAWER_ADAPTER` init0/seed1, standard10 settling controls, render=False,
then directly replay the original command arrays and native `world.obs` assignment.
No model/policy, action-token regeneration, physics preview, snapshot restore,
controller/primitive/validator/tolerance changes, or second/third trajectory.
GPU6 environment is CUDA_VISIBLE_DEVICES=6, MUJOCO_GL=egl,
MUJOCO_EGL_DEVICE_ID=6. This does not change the established render-free replay.

Require exact initial state and exact archived flattened state before AND after
every control: the following archived before-state supplies the intermediate
after-state, and each primitive's stored final state supplies its last after-state.
Also require exact primitive boundary qpos and official-success values from the
archive. Stop before another control on any mismatch or infrastructure failure,
retain partial evidence/missing controls, and do not retry. The old audit merely
accumulated state error; this replay hard-fails at the first discrepancy.
Complete evidence requires122 primitives,970 controls,24,250 actual native
integrations,48,500 before/after snapshots and reproduced official success.

The original policy predates the designated-interaction measurement additions.
Record both source manifest and current measurement TaskSpec/hash/repository state
explicitly. Use the same current top_drawer measurement definitions used by the
historical semantic audit; do not demand an unrelated old all-source-code identity
or claim this is the original policy's admission contract. No historical score,
evidence byte or task-validity tag is overwritten. Full original observation and
controller caches are absent; exact archived state replay is measured trace
equality, not proof of all hidden cache identity.
Specifically, compare the historical Jev d67cb50 TaskSpec (SHA-256
`fb5cd2c73b27ff6ab244667a215dc0a16528eb9a52e25f72e846910dd2d14497`) with the
current11d4504 file (`006395162b0ccafb5a8a632d56d6fdedf26590c788fb5ac095766c54f09dfe50`):
all original measurements and designated/bilateral/non-designated expressions
must be equal. Later effector/axis/evaluation additions are recorded as such.

## Read-only native observation and sensor buffers

Reuse unchanged paired-observer `native_substep_observability.observe_integrators`
and its snapshot implementation, whose exact-reproduction tests and two-arm run
already passed. Bound observer contexts/buffers to one primitive (at most200
integrations), stream sealed records, and clear them between primitives. Record
before/after actual `mj_step` (expected25 per control), any actual split calls,
and native forward counts without adding a step or forward. Expected Euler2 ms
path, contact/cache stages and direct qpos/DoF addresses remain explicit.
Snapshot fingerprints must show no native integration-state mutation.

Preserve all raw contact rows (including nonrobot, zero and subthreshold forces),
six contact-frame force components, native cached geometry and generalized/applied
forces. Retain exact geom IDs/names and frozen membership of all robot, moving
drawer, left/right designated fingerpads and designated handle geoms g18–g20.

Compose a new observer wrapper to additionally read existing `force_ee` and
`torque_ee` wrist sensor buffers, obtained from the gripper's important_sensors.
Freeze sensor names, IDs, addresses, dimensions, types, site/object IDs, local site
frames and units (N/Nm), plus cached site pose. Record native sensordata slices
without copying/forwarding scratch physics, recalculating sensors, calibration,
filtering or an estimator. Their buffer sample times remain unknown; read time and
before/after native stage are explicit. These simulated hardware-sensor analogues
are separate measurements and never enter oracle contact attribution classes.
Do not edit the frozen paired hook source to add them.

## Prospective attribution classes

The native force rule is strictly greater than1 N, retained unchanged. A designated
contact is either designated Panda fingerpad against g18/g19/g20. The historical
non-designated boolean is exactly the TaskSpec rule: arm/drawer contact OR gripper
contact with explicit g11–g16 OR (gripper/handle contact AND no pad/handle contact).
In particular, simultaneous pad and finger-body handle contact alone does not
trigger that historical boolean. Preserve this rule in the primary tables.
Also report the broader pairwise complement (every robot/drawer pair outside
pad/handle), explicitly separate from historical semantic validity, and additional
robot/other-scene contacts. All raw rows remain available.
Robot self-contact is counted separately from robot/other-scene contact, which
requires exactly one robot side.

Classify each BEFORE and AFTER snapshot independently into exactly one of:
`designated_only`, `historical_non_designated_only`, `simultaneous`,
`neither_historical_relation`. The last class is not a claim of literal contact
absence: broader pairwise and subthreshold contacts remain separately counted.
Bilateral pad presence is descriptive, not
required for the historical either-pad relation. Below-threshold and unforced
raw contacts are distinguished from literal absence in the retained measurements.

For each actual integration interval, compute direct drawer-joint change in mm.
Produce separate before-class and after-class sums of positive/negative/net change,
each covering the entire trace once. A third interval table uses the common
class only if both stages agree; otherwise it uses `ambiguous_stage_difference`.
Simultaneous contacts stay separate. Do not pool stages as independent events,
count the same interval twice in one table, or assign exact causal responsibility
to contact classes. No-contact intervals can carry inertial/constraint dynamics.

Retain ordinary control-end readings and regenerate their positive/negative/net
drawer-change table as a comparability check against the earlier semantic audit.
Report newly observed designated/non-designated samples, threshold flags,
first/last sampled intervals and per-primitive/per-control timing. Snapshot-stage
contacts still do not establish continuous first touch, grasp quality, successful
intended interaction or an interaction-valid acquired skill.

## Freeze, review, audit and stop

Commit protocol/source/tests before preflight. Send source identity and protocol
to the parent, and receive joint_interface independent review before dynamics.
Synthetic tests must cover strict thresholds, simultaneous and stage-disagreement
classes, wrist-buffer indexing/read-only checks, bounded observer restoration,
streaming integrity checks and no-follow-on-control after a mismatch.
Offline audit uses bounded streaming hash-chain verification, source/trajectory
hashes, exact control/primitive lineage, native call/snapshot counts and chain,
sensor metadata/value dimensions, unchanged code/protocol, direct-joint arithmetic
and all partition totals. Preserve all failures. No follow-up dynamics is included.
