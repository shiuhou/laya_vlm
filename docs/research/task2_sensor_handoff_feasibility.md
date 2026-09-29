# Sensor handoff proposal: source feasibility decision

Do not implement the original three-packet model comparison. The named empty-close
archive has no returned jaw qpos/qvel or RGB-D. It cannot test whether a sensor-only
decision distinguishes settled empty jaws from an object relation. Keep its
pad-gap/contact result as an evaluator-only counterexample to width implying
holding. No model, physics, features, thresholds, or runtime changes were made
for this audit.

The [source inventory](../evidence/autonomous_research/task2_sensor_handoff_source_inventory.json)
records exact paths, manifest/seal/journal hashes, capture IDs, raw own fields,
artifact hashes and journal record IDs for all 20 fixed boundaries below. Each
selected image hash and RGB-D schema was checked; all 20 own packets equal the
named journal observation exactly. The inventory is provenance, not a proposed
model packet. Raw artifacts remain local under `runs/` in the main repository.

## What exists at the boundaries

`O` means `runs/autonomous-research/task2-point-anchor-grasp-transfer-run-01/`;
`A` means `runs/autonomous-research/task2-additional-stationary-grasp-run-01/`.
Entries are merged zero-based `capture_id` and simulation read time in seconds
(rounded here; full precision in the inventory).

| Source / cell | Preclose | First close / open-hold end | Added close end | Lift end |
| --- | --- | --- | --- | --- |
| O / whole-close | 30 / 12.5 | 38 / 12.9 | absent | 46 / 13.3 |
| O / whole-open_hold | 30 / 12.5 | 38 / 12.9 | absent | 46 / 13.3 |
| O / neck-close | 29 / 12.1 | 37 / 12.5 | absent | 45 / 12.9 |
| O / neck-open_hold | 29 / 12.1 | 37 / 12.5 | absent | 45 / 12.9 |
| A / whole-close | 30 / 12.5 | 38 / 12.9 | 46 / 13.3 | 54 / 13.7 |
| A / neck-close | 29 / 12.1 | 37 / 12.5 | 45 / 12.9 | 53 / 13.3 |

Every listed modern boundary has named `robot0_eef_pos`, `robot0_eef_quat`,
`robot0_gripper_qpos` and `robot0_gripper_qvel` in `sensor-captures.json`, plus
384×384 RGB, depth, intrinsics and camera-to-world transform in its NPZ. Preclose
is the last primary approach endpoint: `frames/capture-000031.npz` for whole,
`000030` for neck, with journal `endpoint.data.own_observations`. Suffix boundaries
use `auxiliary/capture-000008.npz` after first close/hold, `000016` after the next
primitive, and `000024` after A's lift. Their own source is
`control_completed.data.returned_own_observations`, control 7; these are the
just-returned observations, not the stale `world.obs` inside the callback.

`capture_sim_time`, `capture_read_sim_time_s`, and `tcp_read_sim_time_s` are
present. `cached_geometry_sample_time_s` and `exact_observation_sample_time_s`
are explicitly null. Read-time equality is not proof of identical sensor sample
times. Execution completion, retained command and validator status are available
in journals, but contacts, success and evaluator geometry must be stripped from
any selected execution record. The separate `evaluator-only/labels.json` is never
an own-state or image field.

The named empty-close journal is
`runs/privileged-reference/task2-preflight-dev-01/episodes.jsonl`, SHA-256
`0bf519b66ace3eede5169a7cc9e4c727bf5c14872157073de87e71ebf8de042a`.
Records 26 (`reset/close`) and 54 (`closed_gripper/close`) have eight commands,
execution TCP/orientation/retained command, primitive times 0.5→0.9 and 0.9→1.3 s,
validator status, and privileged pad gap/contact. They have **no named returned
jaw qpos/qvel, RGB-D, separate sensor read time or exact sensor sample time**.
The directory contains only journal, manifest and resolved configuration.
`actual_joint_qpos_m`, `qpos_m` and `drawer_qpos_m` are drawer coordinates, not
jaw encoders. The 51-value `predicted.sim_state_after` is simulator state; decoding
it would not restore a missing recorded sensor packet and is excluded.

`privileged_reference.py:471–525` creates each fixture with rendering off and
restores its snapshot before every action; `closed_gripper` first executes one
unrecorded setup close. Records 26/54 therefore do not form a contiguous captured
two-close observation history. `privileged_multistage_task.py:200–209` identifies
the drawer coordinate explicitly. The existing
[counterexample report](../evidence/autonomous_research/interaction_observability_findings.md)
already distinguishes geometric gap from a joint encoder baseline.

A separate drawer demo, `runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/`,
has RGB-D records 6/22 and proprio records 11/27 before/after its empty GRASP
(journal SHA-256 `bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`).
It records named joint positions, width, TCP and retained command, but no named
qvel. `trajectory/action-000.npz` holds commands, flattened states and RGB frames,
not returned own packets. Its different task, scene and observation contract make
it an unmatched illustration. It cannot silently replace the named control.

## Comparisons and confounds

O close/open share an exact approach prefix within each anchor and equal elapsed
close-or-hold/lift exposure; this is a valid command intervention with recorded
sensors. The open arm is not a closed-empty specificity control. A and O close
share exact approach and first-GRASP scientific records/images; A's first close
does not add an independent state. After that shared boundary, A maintains closure
while O lifts. Their equal-time endpoints compare different actions; comparing
their final lifts adds an extra 0.4 s of closure as well as an extra primitive.
Within A, first versus added close is a temporal progression, not a matched
empty-versus-object pair. Both anchors are development cases, not independent
generalization evidence.

Condition, phase (`additional_close`), absolute step/control, file/capture ID,
absolute time, cumulative duration and prior-action count expose first versus
second close. Keep provenance outside a blinded input; use anonymous local IDs
and equal-length causal windows with only necessary relative timing. Do not let
history length reveal the answer. A completion-only input can be identical across
the relevant completed primitives; repeated copies do not create new evidence.
Later lift images cannot support a prelift judgment. The parallel 2D/3D tracking
audit also leaves point ownership unresolved: finite depth and track admission
cannot turn depth-boundary jumps into object motion.

Under retained CLOSED, executed STOP (`hold`, grip +1) and GRASP (`close`, +1)
use the same nominal TCP target, rotation, jaw command, eight-control bound and
success break in Jev `src/jev_libero/world.py:241`. They belong to one stationary
closure-maintenance effect class. Approach STOP terminates without execution and
is different. Neither a new physical STOP arm nor scoring GRASP uniquely correct
would isolate the proposed information question.

## Smallest next choice and architectural consequence

**Recommended now: stop at the source audit.** The existing
[own-state report](../evidence/autonomous_research/task2_grasp_proprio_findings.md)
establishes recorded residual jaw motion after first GRASP and documents that
canonical Laya input omits qvel. Raw qvel after the added interval is much smaller;
that observation does not certify holding. Missing projection and inability to
use supplied facts are different hypotheses.

If a model diagnostic is still desired, restrict it to **own-motion evidence**:
two pairs, A whole captures 38/46 and A neck 37/45. Give both pair members the same
completion/validator/retained-CLOSED information. Compare that packet against the
same packet plus only the two raw jaw velocity values per member. Ask which member
has greater reported jaw motion, or whether the supplied fields do not determine
it, and whether these fields establish object holding. Counterbalance anonymous
row order; this is 2 anchors × 2 information conditions × 2 orders = 8 outputs,
with no images, qpos width heuristic, action ordinal, absolute time, future data,
threshold or motor choice. This is a proposed diagnostic, not a frozen executable
protocol or authorization to run it.

Only unknown without qvel, correct ordering with qvel in both row orders, and
continued holding-unknown would support a narrow provisional role in summarizing
own observations. A constant answer, order dependence or holding claim would
reject even that role for this interface; stop without prompt variants. Success
would **not** transfer grasp-handoff or motor responsibility to Laya: numerical
ordering is deterministic, and this test has no matched holding negative. If that
narrow responsibility is not useful, skip the model diagnostic entirely.

To test holding specificity, a **sensor-complete closed-empty condition is still
needed**: comparable task/sensor contract, same retained-closure exposure and
boundary schedule, named returned qpos/qvel, RGB-D, explicit read/sample-time
provenance, and separate evaluator labels. New recording would fill a sensor
coverage gap; empty closure's mechanics are already demonstrated. No such physics
is proposed for immediate execution. Before recording, define the exact claim
(prelift relation support versus observed retention during lift), comparison and
decision that a result could change. A future matched positive result would need
to distinguish object-supported from closed-empty evidence at equal exposure,
abstain under unresolved visibility, and survive removal of count/time cues before
even provisional relation-estimation responsibility is warranted.

This limit also follows the prior negative probes: [predicate verification](../evidence/autonomous_research/initial_findings.md)
used 768 calls and achieved 56.45% pooled balanced accuracy; [decomposition](../evidence/autonomous_research/iteration_002.md)
used 1,184 calls and its spaced-label single-clause conditions stayed at 50%.
[Coherent supplied state](../evidence/autonomous_research/worldview_sufficiency_findings.md),
[combined state and action semantics](../evidence/autonomous_research/joint_interface_sufficiency_findings.md),
and [native printed progress](../evidence/autonomous_research/native_option_progress_sufficiency_findings.md)
did not repair choices. [Sensor-only approach/marker probes](../evidence/autonomous_research/visual_and_approach_findings.md)
also failed elementary distinctions. Another large nested-packet or wording sweep
would repeat unresolved capability assumptions rather than justify handoff control.
