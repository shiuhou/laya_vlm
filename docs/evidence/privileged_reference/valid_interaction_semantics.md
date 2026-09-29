# Result and valid-interaction semantics

Status: **generic measurements implemented; Task-2 deterministic feasibility
gate did not pass; Task-2 Laya was not run**.

This record separates physical goal change from goal change produced through a
task-valid interaction. Development started from Laya commit `72780c1` on
`feat/privileged-multistage-reference` and Jev commit `6d55eff` on
`feat/multitarget-task-support`.

## Generic effect fields

The Jev measurement layer now accepts exact named geometry selectors and the
generic robot groups `arm` and `robot`. A `contact_relation` measurement emits
one record per matching contact with:

- `left_geom`, `left_body`;
- `right_geom`, `right_body`;
- `normal_force_N`.

A `geometry_in_frame` measurement transforms all selected object geometry into
an articulated target site's frame and emits:

- body position and rotation matrix;
- object bounds and extent;
- close-envelope bounds;
- lower and upper margins;
- per-axis violation, minimum margin and total violation;
- `fits`.

TaskSpecs may declare boolean `interaction_relations`. Every primitive effect
then retains the complete per-control boolean values plus `ever`, strict
`maintained`, `fraction`, and `final` reductions. Two-step witness effects retain
the concatenated trace across both primitives. These fields are produced by the
existing `World.execute`, `predict_all`, and witness paths; no runner or
scheduling branch was added.

## Task-specific contracts

For `top_drawer`, the designated target region is handle geometry
`wooden_cabinet_1_g18..g20`, and the designated effectors are the two Panda
fingerpads. The TaskSpec distinguishes any fingerpad/handle contact, bilateral
fingerpad/handle grasp, arm/drawer contact, gripper/non-handle contact, and
non-fingerpad handle contact. `establish_contact` now establishes the designated
relation. `advance_target` requires designated handle contact at every recorded
control and at the final state before closure is admitted as contract-valid
progress.

For `wine_bottle_bottom_drawer`, a valid grasp requires both fingerpads to
contact `wine_bottle_1`. The bottle's full collision geometry is measured in the
`white_cabinet_1_bottom_region` frame. `placement_fit` is true only when the full
extent, in its current orientation, lies inside that site's close envelope.

- `place_object` preserves a bilateral grasp and must reduce close-envelope
  violation by the existing progress threshold or reach `placement_fit`.
- `object_released` requires LIBERO `In`, `placement_fit`, and no fingerpad
  contact. `release_object` requires fit both before and after explicit release.
- drawer approach, contact, and advance contracts require containment, release,
  and `placement_fit` before and after the primitive, with fit maintained across
  every recorded control.
- reposition witnesses may not drop an existing valid grasp.

The trace also preserves strict within-primitive grasp continuity. Transport and
placement use the bilateral relation at decision boundaries because contact can
flicker inside an otherwise retained physical grasp; that distinction remains
explicit rather than being hidden in `held`.

## Frozen Task-1 attribution audit

The three successful frozen Task-1 runs were replayed from init 0 / seed 1 using
their recorded low-level controls. All three produced the same physical trace:
970 controls, opening `151.659013 -> -0.392884 mm`, and net closure
`152.051897 mm`. Contact was sampled after every recorded control.

| Endpoint attribution | Controls | Positive closure | Negative closure | Net closure |
|---|---:|---:|---:|---:|
| Designated fingerpad/handle interaction | 0 | 0.000000 mm | 0.000000 mm | 0.000000 mm |
| Non-designated robot/drawer contact | 134 | 49.314652 mm | -3.228532 mm | 46.086120 mm |
| No current robot/drawer contact | 836 | 108.445044 mm | -2.479268 mm | 105.965776 mm |

The two largest concurrent non-designated pairs were link 7 against drawer body
geometry `g11` (`32.924683 mm` positive, `30.286907 mm` net) and the gripper hand
against `g11` (`14.334403 mm` positive, `13.743647 mm` net). Link 7 also contacted
handle geometry `g18`, but link 7 is not the designated fingerpad.

Therefore the frozen success contains **0 mm of measured interaction-valid
closure** under the new definition. The 105.97 mm assigned to endpoints with no
current contact includes inertia and settling following earlier pushes. Because
no designated relation was observed at any control endpoint, it cannot be
credited as designated interaction. This endpoint audit does not claim to resolve
contacts that begin and end entirely inside a MuJoCo substep.

The machine-readable audit is
[`task1_contact_attribution.json`](task1_contact_attribution.json), SHA-256
`cfe594484ad96e8977e3757f6e8cafc4ec9e754dceb1caa6240ce806cd129af5`.

## Fresh Task-2 deterministic gate

The gate used the combined wine-bottle/bottom-drawer BDDL, init 0, seed 1, the
same 27 primitives, one-step previews, existing two-step witnesses and official
`env.check_success()`. It used a deterministic, task-effect-based scorer over the
complete selected contract pool. It made no model calls and is not evidence of
Laya competence.

The fresh run established a bilateral grasp with explicit `close` at step 13 and
kept the valid grasp through step 21. It executed transport primitives with exact
preview/execution state agreement (`max error = 0`). It did not reach containment
or `placement_fit`.

At the first failure boundary, before decision 22:

- phase/objective regime: `transport_place_release` / transport;
- valid grasp: true; object inside: false; released: false;
- drawer opening: `157.019662 mm`;
- object clearance: `20.241202 mm`; drawer-goal XY error: `168.429284 mm`;
- `placement_fit=false`; violation: `177.149474 mm`;
- all one-step contract pools were empty;
- the existing two-step mechanism evaluated all `27 x 27 = 729` pairs and found
  no valid witness.

The acceptance phases therefore stand as follows:

| Phase | Result |
|---|---|
| Grasp | Passed: bilateral designated fingerpad relation established |
| Transport | Partial mechanics only; destination transport did not complete |
| Placement fit | Not reached |
| Explicit release | Not reached |
| Drawer close | Not reached |
| Official combined success | False |

This is a zero-pool transport boundary under the new contracts. It is not a
measurement failure, simulator mismatch, object loss, Laya failure, or proof that
the task is mechanically impossible. Per the bounded gate instruction, execution
stopped at this first new failure and no Task-2 Laya episode was started.

The complete 22-step trace, final state and all 27 rejection records are in
[`task2_valid_interaction_gate_failure.jsonl`](task2_valid_interaction_gate_failure.jsonl),
SHA-256 `6d2b9d347c4fe0576ab7400e4dd0f1995da09ed29f0900fca564ca483d281ce3`.

## Runtime boundary

The Laya runtime still owns belief, preview/effects, candidate presentation,
provider calls, execution, replay and scheduling. The generic Jev world only
gained measurements and relation traces. Entity selection, target regions,
relation meaning, placement envelope, objective routing, contracts and success
semantics remain in TaskSpec/TaskAdapter configuration. No task-specific runtime,
planner, new decision layer, primitive, lookahead rule or executor branch was
introduced.
