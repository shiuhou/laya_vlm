# Interaction-boundary audit

Status: **Task-1 interaction attribution complete; Task-2 strict feasibility
gate remains failed; no Task-2 Laya run was made**.

This audit is observational. It adds no candidate, contract, threshold, scorer,
planner, lookahead rule, primitive, executor branch, prompt, or runtime schedule.
It replays frozen controls or archived deterministic choices and evaluates the
resulting physical evidence.

## Representation and code boundary

The generic Jev layer now accepts an optional `interaction_evaluation`
declaration with three required expressions (`result`, `required`, and
`forbidden`) and an optional motion declaration naming effector position,
affordance position, and articulated-joint axis features. The evaluator emits:

- `interaction_valid` when result progress, the required relation, absence of a
  forbidden relation, and compatible joint-axis motion are all observed;
- `interaction_invalid` for an observed forbidden interaction without the
  required relation, or for motion opposed to the affordance motion;
- `interaction_ambiguous` when progress exists but causal evidence is mixed,
  intermittent, inertial, or incomplete;
- `no_goal_progress` when the declared result expression is false.

Every classification retains the evaluated booleans and raw motion evidence:
effector and affordance displacement, joint-axis projections, orthogonal
motion, relative slip, and directional support. No numeric motion threshold was
introduced. The only new generic measurement is the normalized world-frame
`joint_axis`.

Task-specific declarations bind those generic fields. `top_drawer` binds the
two fingerpad center, handle center, drawer axis, required fingerpad/handle
relation, and non-designated robot contact. The wine-bottle TaskSpec declares
observational evaluations for grasp, transport, placement, release, and drawer
advance using the already integrated bilateral-grasp and placement-fit fields.
The generic runtime does not inspect task names and was not changed.

This representation describes acceptable physical evidence. It does not name
an action, rank candidates, prescribe an axis command, or select a primitive.
It therefore does **not** encode a manipulation policy.

## Frozen Task-1 audit

All three canonical successful runs replayed exactly from their stored 970
low-level controls. Each replay retained official success, reproduced
`151.659013 -> -0.392884 mm` opening, and had maximum simulator-state error
`0.0`. Their action-level classifications were byte-equivalent in physical
totals:

| Classification | Actions | Net closure |
|---|---:|---:|
| Interaction valid | 0 | 0.000000 mm |
| Interaction invalid | 67 | 109.951365 mm |
| Interaction ambiguous | 41 | 42.088519 mm |
| No goal progress | 14 | 0.012012 mm |

Of the invalid total, 25 actions / `55.866364 mm` contained an observed
non-designated contact without designated fingerpad/handle contact. Another 42
actions / `54.085001 mm` had effector axis motion opposed to the drawer-handle
motion. The ambiguous total contains progress with no sampled required or
forbidden contact and is not assigned a causal link.

Concrete examples from run 01:

- step 70, `y-40mm`: `9.121075 mm` closure; non-designated contact occurred at
  one of eight control endpoints, designated contact never occurred, and axis
  motion was compatible. Classification: invalid.
- step 108, `rotate_z+10deg`: `6.430529 mm` closure; intermittent
  non-designated contact and opposed effector/handle axis motion.
  Classification: invalid.
- step 34, `rotate_x-10deg`: `7.297644 mm` closure; no relevant contact was
  sampled and motion alone cannot establish causation. Classification:
  ambiguous.
- step 87, `open`: `0.009826 mm` closure, below the existing `0.01 mm`
  progress threshold. Classification: no goal progress.

The result confirms the earlier endpoint audit with a stricter action-level
statement: the frozen goal-completion trajectory contains **0 mm measured
interaction-valid closure**. It remains a valid privileged goal-completion
reference and is not evidence of designated handle manipulation.

The complete controls, raw contacts, relations, motion metrics, classifications,
and source hashes are in
[`task1_interaction_classification.json`](task1_interaction_classification.json),
SHA-256 `131323900b522dc0e257ce651cadcb797c37279b2fad5c494bf34adc4a139446`.

## Task-2 placement geometry

`placement_fit` uses all selected wine-bottle collision geometry transformed
into the articulated `white_cabinet_1_bottom_region` site frame. It requires the
full oriented bounds to lie inside the site's bounds. At the frozen boundary:

- drawer-frame close envelope: `[-29.93, -75.61, -102.24]` to
  `[29.93, 75.61, 102.24] mm`;
- bottle bounds: `[-207.079474, -133.012335, -165.234137]` to
  `[-50.171202, -83.648108, -92.703739] mm`;
- per-axis violation: `[177.149474, 57.402335, 62.994137] mm`;
- placement violation: `177.149474 mm`; `placement_fit=false`.

The frame site is attached directly to the bottom-drawer joint body. An
independent recomputation from raw geometry had maximum error `0.0 mm`.
This rules out a transform/frame implementation error at this boundary. The
site is LIBERO's articulated containment region; equivalence between that region
and the complete collision-swept close volume has not yet been established.

## Fresh strict-gate reconstruction

The exact 22 archived deterministic actions were replayed from init 0 / seed 1.
Every recorded opening, goal-XY error, clearance, and fit violation matched with
maximum error `0.0`. The phase trace was:

1. steps 0-12: approach the bottle;
2. step 13: explicit `close`, establishing the bilateral fingerpad grasp;
3. steps 14-21: transport actions
   `z+40, z+40, z+40, z-40, z+40, z-40, z+40, z-10`;
4. boundary 22: zero pool before any further action.

At boundary 22 the bottle was still held, was not inside the drawer, and was
not released. Drawer opening was `157.019662 mm`, goal-XY error was
`168.429284 mm`, and vertical clearance was `20.241202 mm`.

All 27 primitives passed the obstacle collision gate. All 27 then lost the
bilateral grasp within the primitive, so none satisfied strict grasp continuity
and none reached containment or placement fit. The complete two-step audit
evaluated all `27 x 27 = 729` ordered pairs. No pair ended with a valid grasp,
containment, or placement fit, and no pair satisfied any contract. Thus the
exact snapshot is a real one-step and existing-two-step contract dead end; it is
not a preview/execution mismatch.

## Trajectory/scorer comparison

The failed strict gate and the older diagnostic trajectory share actions 0-15.
At step 16 both had the same current motor alternatives:
`z+3mm`, `z+10mm`, `z+40mm`, and `rotate_y-10deg`.

- the failed deterministic gate selected `z+40mm`, raising clearance from
  `-6.238535` to `31.317655 mm`; it then alternated large down/up motions and
  arrived at the frozen dead end;
- the older diagnostic selected `z+10mm`, then rotation and horizontal
  transport, reducing goal-XY error to `109.916305 mm` by step 21.

The older choices were mechanically replayed and checked against the **current
strict contracts**. Actions 0-21 remained current-contract eligible and replayed
with maximum feature error `0.0`. Its archived step-22 release action was no
longer eligible: current placement fit remained false with `157.814264 mm`
violation, and its current one-step pool was empty. This comparison therefore
does not establish Task-2 feasibility under the new semantics. It does establish
that the specific frozen boundary was reached because the deterministic scorer
selected the large lift at a real multi-option boundary.

Classification of the audited frozen failure: **TRAJECTORY / SCORER DEAD-END**.
The exact terminal snapshot is contract-empty, but an alternative sequence that
remains valid under the same current contracts avoids that snapshot. The
alternative later encounters a different one-step empty pool, so the broader
question of whether the current contracts and 27 primitives can reach
`placement_fit` remains unresolved. No contract or scorer was changed here.

The full 27 one-step effects and clause trees, all 729 two-step results, frozen
snapshot hashes, geometry validation, and same-contract comparison replay are in
[`task2_boundary_audit.json`](task2_boundary_audit.json), SHA-256
`edafa37861c8b54e125139daf8cf15c2674be8315587915d099f8f427a442d32`.
The local frozen simulator/controller files are retained under
`runs/privileged-reference/interaction-boundary-audit/` and are intentionally
excluded from source control; their hashes are embedded in the JSON evidence.

## Acceptance and stop point

| Requirement | Result |
|---|---|
| One generic schema supports both tasks | Pass |
| Task-1 valid/invalid/ambiguous audit | Pass |
| Task-1 replay remains exact and successful | Pass, 3/3 |
| Task-2 grasp | Pass |
| Task-2 transport to placement region | Fail at audited trajectory boundary |
| Task-2 `placement_fit` before release | Not reached |
| Task-2 explicit valid release | Not reached |
| Task-2 official and interaction-valid success | False |
| Task-specific runtime fork | None |
| Task-2 Laya execution | Not run |

The first remaining failure is the deterministic feasibility trajectory/scorer
boundary. The evidence does not justify changing the live contracts, primitives,
lookahead, objective routing, or runtime in this checkpoint.
