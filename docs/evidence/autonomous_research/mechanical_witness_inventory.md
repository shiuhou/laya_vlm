# Existing mechanical witness and action-interface inventory

The strongest existing local positive witness is the **first bottle lift after the established bilateral grasp**, step 14 of `interaction-observability-paired-01`. It is suitable as a narrowly qualified reference for a future interface comparison. It does not validate the current visual action interface, a holding classifier, full destination transport, or Task-2 success.

This review reads source and stored evidence only. The arithmetic in `embodied_runtime/experiments/mechanical_witness_inventory.py` passes and writes `mechanical_witness_inventory.json`. It independently reconstructs the configured bilateral predicate for all 274 evaluator records and computes the endpoint differences below, without simulation, FK, projection, distance queries, or model calls. The earlier [retention audit](retention_independent_audit.md) covers the larger artifact/replay checks; this inventory does not repeat those experiments.

## Smallest existing positive slice

The paired collector is freeze `2dd31e06c9676d841a6a9c5c993519ce647ff0fb`, using jev `11d450455d0307bd806c94a27fc7166efb1c483d`. Both arms started fresh at init 0 / seed 1 and completed 17 primitives / 136 controls. The common prefix contains 104 exactly matched controls. The intervention at step 13 changes native `close` to `hold`, retaining open jaws in the comparator. The source prefix was privileged and scripted; no sensor or model selected it.

The configured `valid_grasp_relation` requires contact from each of `left_fingerpad` and `right_fingerpad` to `wine_bottle_1`, strictly above **0.05 N**. This differs from the drawer's 1 N threshold. Each recorded control endpoint is 0.05 s apart.

| Stored slice | Close arm bilateral samples | Close arm bottle-center rise | Open/hold arm |
| --- | ---: | ---: | --- |
| Step 13, establish grasp | 1/8, final sample only | +0.013504 mm | 0/8; no gripper contacts |
| Step 14, first lift | **8/8**, with bilateral before state | **+37.902849 mm** | 0/8; no gripper contacts; +0.001081 mm center rise |
| Step 15, second lift | 8/8 | +37.839185 mm | 0/8; +0.000235 mm center rise |
| Step 16, third lift | 4/8, last four | +37.644300 mm | 0/8; −0.000023 mm center rise |

For step 14, the bottle bottom rises from 899.879367 to 937.836341 mm. Together with the recorded bilateral relation this establishes local, observed contact-maintained object motion at the sampled endpoints. Contact rows cover gripper contacts, not all external support. It does not establish support-free retention, force closure, or uninterrupted contact between samples. The third lift's pad-relation flicker is not evidence that both physical fingers detached; finger-body contact remained in the archived trace.

The full three-lift sensor record supplies descriptive body-point co-motion (+109.810 mm close versus 0 mm open), but does not make the first-lift witness a sensor-selected policy. Its visual annotation was assistant-provided, corrected by the existing provenance erratum. The tabletop correspondence failed, so automated support separation was not validated. Runtime `holding` remains unknown.

## Interfaces are distinct

| Interface | Vocabulary | Executor and demonstrated scope |
| --- | --- | --- |
| Native jev | 27: world-axis translations ±3/10/40 mm, world-axis rotations ±10° about X/Y/Z, open/close/hold | `World.execute`, normally eight controls; rotation command on first control only; retained jaw command except open/close. Successful bottle slice uses this family, including native 40 mm lifts. |
| Privileged reference wrapper | Same 27 primitives | `JevAtomicExecutor` reports translation/rotation departures as nominal tracking flags; only jaw-command mismatch is a hard execution-contract failure. It explicitly says the reset envelope is not validated for all 27. |
| Shared offline decision vocabulary | 11: six 10 mm translations, Z rotations ±10°, STOP/GRASP/RELEASE | `shared_atomic_candidates()` is an offline probe vocabulary, not execution authorization. |
| Natural visual approach fixture | 10 admitted options: six translations, two Z rotations, STOP and GRASP | Rebuilt by `VisionCandidateBuilder`; RELEASE is vetoed when holding is unknown and the retained command is open. This is an actual feasibility gate, not merely a static count or an automatic alias collapse. |
| Coarse physical approach family | Seven: six 10 mm translations and STOP | Retains open jaws; no rotation or jaw-change choice. Independent seven-arm test found no contract-valid, contact-free positive approach witness; native-stage review also caught transient contacts missed at endpoints. |
| Visual execution boundary | `AtomicExecutor` through `LiberoWorldBackend` | Hard reset-derived limits: translation error 2 mm, pose-hold translation 1.5 mm, retained-orientation change 1°, rotation-action error 2°. These are calibration envelopes, not general safety or task-success certificates. |

The generic runtime constant additionally includes terminal DONE; its separate basic `CandidateBuilder` also has a dynamic menu. A static vocabulary count must not be reported as the menu offered by every experiment.

The bottle collector calls native `World.execute` directly and checks eight-control completion. It does **not** run the visual `AtomicExecutor` validator. Every archived control in both bottle arms has zero commanded rotation components, preserving the initial orientation command; no alternate grasp orientation is validated. Nominal 40 mm lift evidence cannot be silently converted into evidence for a 10 mm lift or a stricter executor envelope.

Source anchors: `jev-libero/src/jev_libero/actions.py` and `world.py:World.execute`; `embodied_runtime/experiments/interaction_observability.py`; `experiments/privileged_reference.py:JevAtomicExecutor`; `decision_interface.py:shared_atomic_candidates`; `adapters/physics_preview.py:VisionCandidateBuilder`; `adapters/libero.py:execution_evidence`; and `experiments/approach_family_control.py:NATURAL_ORDER`.

## What can be checked for step 13 without replay

The visual validator uses returned `robot0_eef_pos` for translation, but native cached `data.site_xmat[eef_site_id]` for rotation. The paired archive retains the former, returned quaternions, and separate scratch-FK matrices. It does not retain the exact native cached site matrices.

| Step-13 measure | Close | Open/hold | Status |
| --- | ---: | ---: | --- |
| Exact validator TCP displacement norm | 0.220081 mm | 0.310048 mm | Both below 1.5 mm hold limit |
| Archived jaw commands | Closed throughout | Open throughout | Expected commands matched |
| Returned-quaternion relative rotation | 0.029370° | 0.022966° | Descriptive; different cache from validator |
| Archived scratch-FK relative rotation | 0.028118° | 0.021757° | Descriptive; different cache from validator |
| Exact validator cached-matrix rotation | Unknown | Unknown | Full historical contract cannot be certified |

No new FK was computed for this table: the arithmetic only compares archived matrices/quaternions. Values from another cache must not fill the unknown exact rotation field merely because they are small.

The pre-step-13 boundary has archived flattened simulator state, robot observations, low-level commands, RGB-D and evaluator baseline. It has no complete historical controller/observation-cache checkpoint. A fresh-prefix comparison can gate equality against the archive; restoring only qpos would not reproduce the full native context.

## Recommended bounded comparison

The smallest useful next mechanical check is transfer at this established pre-grasp boundary to the **unchanged visual executor**, with its original validation active, followed by a single 10 mm lift only if the preceding operation passes. The existing paired close/hold structure supplies a local comparator. This tests whether the demonstrated native grasp transfers to the actual action interface before expanding perception or model decisions. The parent is registering this separately; this inventory prescribes no approach recipe and runs no new dynamics.

Both endpoint grasp admission and the strict per-control relation should remain visible. In the bottle TaskSpec, `p.valid_grasp_maintained` means before AND after; `p.valid_grasp_continuous` and strict interaction evaluation use the complete sampled trace. The first lift satisfies both observed meanings. Neither should be relabeled continuous-time contact.

Task 1's official successful canonical replay has no observed designated contacts at recorded native stages. Task 2's later strict gate stops before decision 22 with no one-step pool and no valid two-step witness among 729 pairs; it does not achieve placement fit or combined success. The early bottle slice is therefore local positive mechanics, not a successful full manipulation reference or a general feasibility proof.

## Stored identity

| File under `runs/autonomous-research/interaction-observability-paired-01` | SHA-256 |
| --- | --- |
| `manifest.json` | `b68dfcbf65048555069bb1c27639915ec2fda9c520822600f81549547031b02f` |
| `evaluator-only/labels.json` | `493c7b1ff32943217351d73b631c385199dfaab4d3ed8427a52de32c768945c5` |
| `endpoints.json` | `c28136d9e0e67b359491a3d270b0566e49a7f5939287363a18cdd8192ab7abe5` |
| `sensors.jsonl` | `59a38821e165393d607be1b3ec9100f093fcc52718282173fe8b28c556174bbe` |
