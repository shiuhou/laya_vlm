# Minimal sensor-complete closed-empty falsifier

Recommendation: prepare **B, one prospectively fixed neck-anchor present/away
pair**, then stop for review before dynamics. Both cells must regenerate the same
sensor-selected approach from benchmark init 0 / seed 1. At its unexecuted STOP,
apply a logged privileged scene event: sham translation in present, fixed bottle
translation away from the jaws in away. Both then execute unchanged
GRASP / GRASP / MV_UP. This supplies a new observation-specific negative, not
another demonstration that an empty gripper can close. No wrapper, model calls,
qvel microprobe, simulator world, forward call or dynamics were run for this design.

## A versus B

| Design | New collection / verification controls | What it isolates | Main confound / implementation cost |
| --- | --- | --- | --- |
| A: reset, GRASP / GRASP / MV_UP with bottle distant | 24 / 24; two fresh worlds | Same command schedule in an empty grasp region; direct missing qpos/qvel/RGB recording | Compared with existing grasp positives, arm pose, target geometry, elapsed episode time, approach history and image context all change. Existing control replay suffices; a small reset/suffix collector is needed. |
| B: fresh same approach in present and away cells, scene event, same suffix | 512 / 512 at neck; four fresh worlds | Target near the jaws versus away, with identical pre-event policy/sensor history, robot state, commanded suffix and elapsed timing | Requires explicit scene-event collection/replay and matched synchronization. The image change is the intended scene intervention; it is not a visually identical empty-control state. |

Counts exclude World's standard ten open-jaw settling controls per fresh world:
A adds 20, B adds 40. Neck has 29 approach primitives; each B cell therefore has
32 × 8 = 256 recorded controls, of which 24 belong to the suffix. Neck is the
explicitly chosen development fixture with known maintained sampled lift after
added closure. This is not held-out selection or new general success. One pair is
enough to falsify an unconditional holding claim; adding whole now would double
this diagnostic without solving a new confound.

A is cheaper in raw controls but cannot support the matched information claim.
Do not run A as an extra warm-up or collect both designs by default. B is the
smallest of these designs that removes the pose/history alternative explanation.

## Existing archives do not supply this negative

The [source feasibility audit](task2_sensor_handoff_feasibility.md) already checks
the named empty fixture and drawer demo. A broader read-only search under main
`runs/` found named jaw velocity in the following physical source families:

| Source under `runs/autonomous-research/` | Why it does not replace B |
| --- | --- |
| `interaction-observability-paired-01/{sensors.jsonl,endpoints.json,captures.json}` | Closed bottle/lift versus open-jaw hold/lift; first close becomes bilateral. Temporary no-contact samples are not a settled empty endpoint. |
| `local-grasp-interface-run-02/{sensors.json,episodes.jsonl}` | GRASP / MV_UP positive versus OPEN-retaining STOP / MV_UP; no second-close empty arm. |
| `task2-point-anchor-grasp-transfer-run-01/*/sensor-captures.json` | Complete first-GRASP no-contact observations, but those jaws are still moving; open controls retain OPEN. |
| `task2-additional-stationary-grasp-run-01/*/sensor-captures.json` | Both added-closure cells establish bottle contact; no closed-empty cell. |
| `task2-box-point-boundary-run-01`, `task2-endpoint-containment-veto-run-01`, `task2-point-anchor-approach-run-01/{whole,neck}` | Approach only, no GRASP. |
| `task2-pre22-counterfactual-run-01/episodes.jsonl` | Seven translation/STOP branches at an open-jaw boundary, no GRASP. |

The search covered JSON/JSONL for returned/direct jaw qvel and inspected ZIP member
names in all **2,648 NPZ archives** then present under main `runs/` (16 schemas,
zero unreadable archives). None has named jaw qpos/qvel arrays hidden outside the
JSON sensor streams; trajectory files contain flattened simulator states. Derived
reports/tracks repeat existing sources. The independent retention reviewer also
reported no additional confirmed sensor-complete settled closed-empty source.
This is an inventory of the available workspace, not a claim about missing external
archives. No state decoding was used to manufacture observations.

## Concrete B scene event

Use the current `task2_point_anchor_approach` selector, cached admitted neck POINT,
original full-BOX guard, task/assets/init/seed and unchanged executor/controller.
Regenerate both approaches independently; compare their entire scientific prefix
and RGB-D arrays before permitting the event. Archived controls or states are
verification sources only. Preserve the non-executed approach STOP.

Candidate fixed event: translate `wine_bottle_1_joint0` **+0.35 m along world X**
in away and +0.0 m in present. Retain target Z, orientation and all velocities;
do not zero velocity, remove collision geometry, hide the mesh, change mass,
retarget the task, or relocate the robot. The bottle remains elsewhere in the
scene; "away" means absent from the grasp region, not absent from the world.
Do not use robosuite `clear_objects`, which teleports an object to (10,10,10) and
changes orientation, creating an unnecessary falling/out-of-scene condition.

This is feasible at source level: LIBERO `WineBottle` uses a free joint, and the
archived `task2-pre22-counterfactual-run-01/current-model.xml` names
`wine_bottle_1_joint0` as `type="free"` (XML SHA-256
`3d4b4f0ded735a29b947b8b14f393e8c25c056ffda41d4b5edf28d7706541f03`).
The task's kitchen tabletop is 1.0 × 1.2 m with top Z = 0.90 m. A
[stored-only placement calculation](../evidence/autonomous_research/task2_closed_empty_static_bounds.json)
uses pure XML/STL transforms and the recorded neck preclose native qpos at source
seq 12216, time 12.1 s. The XML-derived named joint types and qpos addresses
hash-match the archived compiled model arrays. It covers all 16 robot, 40 bowl,
21 bottle, 36 cabinet and 9 rack collision geometries. Because reset writes fixture
positions into the compiled model, it bounds cabinet/rack world X across the full
BDDL placement ranges instead of treating their unset XML root positions as truth.

The translated bottle collision envelope is X [0.198487, 0.241079] m,
Y [0.038607, 0.082846] m, wholly inside the tabletop. Conservative world-X
separation from the remaining collision geometry is:

| Geometry group | Separation lower bound |
| --- | ---: |
| All robot links, mount and gripper | 268.910 mm |
| Bowl | 133.227 mm |
| Cabinet across its BDDL placement range | 57.257 mm |
| Rack across its BDDL placement range | 154.107 mm |

X-disjoint bounds suffice for static separation regardless of unknown fixture
Y/Z. Target Z/orientation and its table penetration/support geometry are preserved
by pure horizontal translation over the same flat tabletop. The
[calculation source](../evidence/autonomous_research/task2_closed_empty_static_bounds_source.py)
imports no simulator and constructs no model/world. Its setup assumptions and
source identities remain subject to independent review and live identity gates;
this is **not** dynamic stability, camera-visibility or suffix swept-clearance
certification. At the authorized event, verify the named joint and model, fixture
placement contract, full translated footprint and static non-table separation.
A failed check stops the attempt. Do not search or adjust the offset after seeing
outcomes. Geometry checks and scene editing are privileged experimental setup,
never sensor evidence or online policy.

Apply exactly one explicitly recorded `sim.forward()` and one forced observation
refresh in **both** cells after the write. Assign only the returned observations
to `world.obs`; retain the normal own-field allowlist. LIBERO's
`env_wrapper.py:136–145` and robosuite `base.py:315–341` already support observation
refresh after direct state edits, but the convenience `set_init_state` path also
restores full state and invokes task post-processing: do not use it here.

Forward/refresh is part of the scene intervention, not a read-only sensor hook.
It can change derived geometry, contacts, accelerations, solver buffers and
observable timers. Log those effects, including the sham's effects; preserve
simulation time, non-target generalized positions, all velocities/actuation,
retained command and controller state. The explicit write must change only target
translation; any synchronization-induced changes must be separately attributable
to the declared calls. Do not reset controller state or load a solver snapshot.
This is why an old positive trace cannot substitute for the fresh sham cell.

Journal the intent before mutation and completion afterward: intervention ID,
`privileged_scene_intervention=true`, target/joint name and resolved address,
fixed delta, before/after state and integration fingerprint, model identity,
controller/RNG/observation-cache identities, actual forward/refresh calls, time,
own observation provenance and boundary image hash. Store pose/contact/geometry
details in the mixed audit journal or evaluator lane. Strip condition, event name,
target pose, geom IDs, contacts, solver state and absolute action/time identifiers
from any later model-facing packet. Treat the jump as an exogenous discontinuity,
not ordinary tracked object dynamics. A separately fixed through-event transfer
of all original LK seeds may be preserved as a diagnostic, including every failure;
do not choose a suffix cohort by which seeds survive. Holding judgments use the
fixed causal post-event window in both cells and cannot borrow correspondence
identity across the relocation without evidence.

## Recorder and replay work required

Existing pieces can be reused without changing production behavior:

- `task2_box_point_boundary.collect:205` accepts `after_approach`; its
  `observe_controls:151` already saves previous and just-returned named own
  packets, commands and before/after states.
- `task2_point_anchor_grasp_transfer.verify_prefix:79` verifies the freshly
  regenerated approach. Its suffix/native observers and unchanged validator
  support the three existing actions. Do not call the additional-GRASP module's
  historical first-GRASP equality check after a scene edit; equality is required
  only before the intervention and against each new cell's own replay afterward.
- `local_grasp_interface.read_only_measurement:77` guards ordinary render/read
  operations; `native_observer:116` preserves BEFORE/AFTER contact records.
  Scene mutation must occur outside those read-only guards.

The gap is explicit: `task2_box_point_boundary.replay:357` walks recorded actions
and controls only, assumes one primary image per action plus reset, and has no
scene-event dispatcher. `AuxiliaryReplay` runs only after controls. Leaving this
unchanged would either fail on the first edited state/image or omit the cause.
The smallest addition is an optional `before_suffix` callback to the existing
experimental `Intervention`, invoked after prefix verification, and an optional
`before_action` callback in the existing experimental replay, invoked before the
first suffix control/state check. The new experiment supplies a tightly bounded
scene-event handler to these hooks; existing callers retain their default path.
Use a separate one-image scene-boundary capture stream so the replay's primary
one-image-per-action accounting stays intact. The handler verifies event
preconditions, applies the same named translation and synchronization, and checks
its complete before/after record and image, then normal control replay continues.
Never restore the recorded after-state to make the comparison pass. Require
exactly one expected event, no duplicate, unconsumed or unknown mutations, and
normal exact state/own/image/native checks. Do not construct a standalone runtime.
Keep new code under experiments; retain production/runtime/controller hashes.

Minimal new sensor coverage is **four suffix RGB-D boundaries per cell**:
post-event/preclose, after close 1, after close 2/prelift, and after lift. The
pre-event image already exists in the approach prefix. Keep all 24 suffix control
own packets and all existing native evaluator records; per-control RGB is not
needed for this first falsifier. The current seal drops primary suffix images in
favor of auxiliary captures, so a small experiment-local seal must retain these
four boundaries and bind each to its actual own packet. Seal sensor files before
writing separate labels. Preserve read times and explicit unknown exact sample
times; a forced refresh does not silently establish new timestamp guarantees.

Before dynamics, test event dispatch/order with fakes, reject wrong joint/state,
missing/duplicate events and undeclared changes, and verify the sensor export
allowlist. Then freeze protocol/code, perform a no-world source preflight, and
review the exact two-cell matrix. No extra live calibration, hidden settling
controls, suffix extension, retry or outcome-selected boundary is included.

## What this could falsify

Prelift is the fixed endpoint after the second GRASP. Evaluator labels should
separately report designated pad contacts, other robot/target contacts, target
support and later lift behavior. A present cell that loses its expected relation
is a retained adverse result, not a reason to choose another anchor. An away cell
with unintended contact invalidates the intended empty comparison and stops it.
Neither a privileged relation label nor a scene-event flag enters a sensor packet.

Do not assume two closes settle the empty jaws. Record qvel throughout the fixed
schedule. If they remain moving at prelift, the result is a same-exposure
closed-empty observation, but **not** a settled-empty counterexample at that
boundary. A later quiet endpoint cannot be backdated or used to justify extending
only the empty arm. No velocity threshold is fitted to this pair.

The cheapest future assay keeps prelift claims separate from observed lift
retention. A holding claim in the away cell despite the matched negative evidence
falsifies the proposed estimator/interface. Abstaining in both cells establishes
no positive competence. Distinguishing the two from their causal sensor windows
would support only a provisional relation-estimation role; it must not be credited
for reading condition names, the relocation event, action count or time. Unresolved
occlusion remains unknown, and the observed jump is not ordinary object dynamics.
Even success on this pair would not establish force closure, retention against
slip/support, or general handoff control. It would determine whether a further
sensor-relation interface test is warranted; it would not justify a qvel-only
model microprobe or a fixed two-GRASP policy.
