# Proposal: Task2 observed-depth support versus nominal gripper sweeps

**Proposal only; no geometry features or new experiment have been computed.** This is a feasible stored-only diagnostic using the existing convex-proxy distance routine, sealed gripper calibration and returned own observations. A prospective implementation/code review and source-compatibility gate would precede feature computation.

The question is whether the retained depth support contains geometric evidence near the observed hand/bottle interaction that the scalar point-distance rule omitted, or whether this depth/own-geometry representation fails to resolve it. This is an exploratory retrospective comparison: the contact, source image and selected boundaries are already known. The full BOX expansion specifically retains observed upper/cap-region pixels omitted by the fixed inner crop; it does not repair the target center or infer a grasp pose.

## Fixed comparison

Use **pre-action 21 and pre-action 22** from `task2-box-point-boundary-run-01`, all seven unchanged nominal candidates, and all five existing calibrated gripper proxies. These are zero-based steps. The measured actions were **21: MV_DOWN, no raw robot pair; 22: MV_FWD, first raw hand/bottle pair**. The later first >0.05 N crossing was step 24 MV_DOWN and is not the first raw boundary. The executed candidate alone has a measured outcome at each snapshot; the other six outcomes remain UNKNOWN. No seven-way classifier validation or counterfactual success claim is possible.

| Axis | Registered values |
| --- | --- |
| Own pose | Pre-21 and pre-22, control 0 `previous_returned_own_observations` |
| Support | Existing initial inner-crop G; all valid initial depths in original full BOX |
| Nominal motion | FWD/BACK/LEFT/RIGHT/UP/DOWN, 10 mm in existing world axes; STOP zero displacement |
| Own proxies | Hand; finger 1 body; finger 1 pad; finger 2 body; finger 2 pad; also their union |
| Measurement | Current solid, nominal endpoint solid and complete nominal translated swept solid |

## Inputs and feature boundary

Pin the collection journal `f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771`, source frame `3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`, sensor representation `be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead`, and robot calibration `11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa` before extraction. Pin exact source record IDs, source/helper hashes and numerical package versions in a later implementation freeze.

The adapter extracts only the paired returned `robot0_eef_pos`, `robot0_eef_quat` and signed `robot0_gripper_qpos` from each selected control-0 packet. Returned position is already the grip-site origin. Correct the returned eef-body orientation using the separately audited fixed body-to-site mount. Reuse `robot_only_geometry.forward` on a calibration subtree rooted at `robot0_right_hand` with an identity root pose, then express its five proxy vertex sets relative to the calibrated grip site and place them using that returned site pose. This requires only the two named finger joints; it does not require arm qpos addresses, an installed robot-base transform, scene-state extraction or a new FK comparison to simulator poses. Keep the three returned fields together; do not substitute direct/native joints or cached site rotation. Exact observation sample times remain unknown.

Before features, check existing calibration/export provenance, Task2 use of the same Panda/gripper construction, repository/package identities and current own-gripper static subtree compatibility where inexpensive. Pin inspected robot-only source bytes. The sealed compiled calibration and matching construction support an explicitly conditional calibrated-proxy diagnostic. Present-time static compatibility and version strings do not prove historical asset-byte identity; report that remaining uncertainty rather than inventing a historical seal or starting a new full-scene export. A demonstrated static mismatch must be resolved before numerical work. Exact Task2 replay remains separate evidence. No new scene construction or task geometry may be used to fill a provenance gap.

Reproduce the saved inner-crop G exactly, using bounds `[212,169,224,210)` from the original integer BOX `[208,156,228,223)`. The full support uses every finite depth in that full half-open BOX satisfying the **same existing 0.01–5 m inclusive validity rule**. Backproject each pixel at `(u+0.5,v+0.5)` with the original K/T and depth. Preserve pixel coordinates, depth and source identity. Both are generic initial resolved-depth point proxies, not bottle segmentation or certified current physical surfaces. Keep tabletop, background and possible own-robot samples. Do not mask, denoise, interpolate, fit PCA, remove points by labels, query a model, alter P, or use the parallel neck-query result.

The source was captured at 0.5 s; the selected read boundaries are approximately 8.4 and 8.8 s later. Static persistence is unverified. Later RGB-D, native contacts/forces, scene poses and execution outcomes do not enter the sanitized numerical process. It receives only the own packets, static gripper subtree, initial depth/K/T, fixed BOX/crop definitions and canonical translation vectors. Use opaque sample names; keep source-selection and evaluator metadata outside the worker. Seal numerical outputs before attaching actual-action contact evidence or inspecting witness RGB.

## Geometry and complete output

Reuse `sensor_gripper_proximity.proxy_distance`: Euclidean distance from a finite depth point to each **solid convex proxy**, zero for contained points. For proxy vertices V and nominal translation d, the swept solid is `conv(V ∪ (V+d))`. For a convex solid under fixed-orientation translation this is the complete nominal sweep, avoiding a sampled-path step size. The five-proxy union means minimum per-proxy distance and logical OR of containment; never take one convex hull over all five proxies, which would fill the gaps between jaws. STOP uses the unchanged current solid. Apply the existing 1e-12 half-space numerical tolerance only; introduce no physical margin or learned contact threshold.

Hold the snapshot's orientation and signed jaw configuration fixed over each nominal sweep. The actual controller has tracking error and small orientation/jaw motion; its integrated path is not this geometric idealization. STOP here is only zero nominal displacement, not an executed hold or evidence that holding would preserve geometry. Swept point containment is a relation between finite observed points and a nominal robot proxy, not a physical collision predicate.

For every snapshot × support × candidate, retain current/endpoint/swept minimum distances, per-proxy and union containment counts, and all per-pixel/per-proxy distances and containment flags. Retain deterministic nearest witnesses: support pixel, its unmodified depth/world point, proxy identity, and closest solid point. Resolve numerical ties by fixed row-major pixel order then calibration proxy order for the primary witness, and retain every exact minimizing pixel/proxy tie in the arrays. Record every contained pixel without selectively choosing a favorable illustration. Display all seven candidates in canonical order; do not rank, filter, change feasibility flags or choose an action.

Full BOX is a strict superset of inner G. Its minimum distance must therefore weakly decrease for **every** candidate regardless of scientific usefulness. Lower full-BOX minima alone are not improved contact prediction. Show full-support witnesses with their source RGB/depth and whether they lie outside the original crop; any descriptive change may come from background/mixed-depth samples. Finite sampling, hidden space, calibration uncertainty and representation mismatch remain unresolved even when no point intersects a sweep.

Every swept solid also contains its current solid, so swept minimum distance cannot exceed current minimum distance. If any current proxy already contains a support point, all seven swept union minima are zero. Report that degeneracy explicitly using the retained current/endpoint/per-proxy outputs; it is not directional contact discrimination.

## Proposed sequence and interpretation

1. After this proposal is accepted, implement the small subtree/support adapter and swept-hull wrapper using the existing pure helpers. Freeze code, exact inputs/candidate order, complete output schema and this protocol before features. No dynamics, rendering or inference is needed.
2. Pass meaningful analytic checks for direct-site subtree placement, signed jaw mapping, translation/rotation covariance, sweep endpoint/interior containment, STOP equivalence, full/inner support inclusion and excluded-field poisoning. Reuse existing triangle/hull-distance tests; check empty support produces UNKNOWN. Independent reviewer examines protocol/code before features.
3. Compute all registered outputs once and seal sanitized inputs/results. Preserve an error without changing the scientific definitions after results. Then make source-pixel witness figures and append a separate evaluator for executed DOWN at 21 and FWD at 22, retaining raw-versus-threshold evidence and unknown counterfactual outcomes.
4. Report whether the observed support places points near/inside the executed nominal sweep, how witnesses change with support extent and candidate direction, and whether this representation can describe the observed boundary. Any result is descriptive development evidence. It cannot certify clearance, infer object ownership, identify a successful lateral approach, establish grasp readiness, or justify a new policy without a separate experiment.

The renderer/masking investigation remains closed. This proposal contains no new mask variant, target offset, safety gate, fitted margin or physical action.
