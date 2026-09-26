# Task2 cached BOX point: first physical approach boundary

Prospective approach-only diagnostic. Test whether the existing nominal seven-option rule can approach the unchanged BOX-center-ray/crop-median point P from a fresh Task2 reset using live own proprioception. P is a mixed-support sensor proxy, not an observed bottle surface, rigid object center, pad center or qualified grasp pose.

## Frozen source and admission

Use Task2 wine bottle/bottom drawer, seed1/init0, standard ten settling controls and existing native controller. Construct a fresh world; never restore an archived state, replay archived controls, seed the controller from the successful prefix, or query a model. The one cached LocateAnything BOX result comes from `task2-box-support-run-02`, with one original 12-token EOS call. Its original RGB-D source is `interaction-observability-paired-01/close/0000.npz`.

Pin and verify before world construction:

- Original frame SHA256 `3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`.
- BOX model output SHA256 `c0545950996092c7ea05d7e10cf115ff0ed3ec318d1b08ff729300d1ee8bb944`.
- Sensor representation SHA256 `be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead`.
- Completed BOX journal SHA256 `51dd621269c6da151c39e9b1bd9b0cdf15a890eb2e4af28a59caaea065201a3b`.

P remains exactly `[-0.12371558041536501, 0.05615888976955092, 0.9855272687809821] m`. It retains the original provider's ray convention and crop median; no center-depth substitution, ROI cleanup, footprint correction, offset, extent/PCA feature or successful-prepose information enters the rule.

Before any approach action, capture fresh RGB/depth/K/T and require each array's dtype, shape and value bytes to match the original source exactly. On mismatch stop, preserve the run and do not repair/retry. This qualifies reuse of cached perception only at the initial boundary; it does not verify current identity, later target stationarity or physical sensor calibration. Subsequent images are evidence only and never update P. Report age from the newly matched capture time, retain the original archived provenance, and explicitly label zero new model calls.

## Policy and execution

Use the existing shared canonical six world-axis 10mm translations plus STOP, `geometric_effects`, and `CanonicalDecisionInput.rule_token()` with unchanged tie-break and strict nominal improvement. Input fields contain only the fixed sensor point, requested bottle description and live own TCP/jaw observation/retained command. TCP is the existing grip-site observation; no pad-center or orientation correction is introduced. Unsupported identity, surface, contact, holding and clearance fields remain unknown. The fixed-target assumption is explicit and unverified.

Use unchanged `LiberoWorldBackend` and `AtomicExecutor`, including the reset-calibrated execution validator. Keep the original open-jaw command and orientation behavior. Exactly one fresh physical condition, at most 40 attempted approach primitives and 900s wall time including setup. Complete normal actions with eight native controls and 25 Euler2ms integrations per control. Never extend the budget, recover, regrasp, select an oracle action, or run placement/drawer closure.

The inherited backend/executor/World implementation reads privileged features for execution evidence, validation and official-success handling. Those outputs never enter the point/rule input. Do not call the task adapter's privileged phase routing or `prepare_world`. Preserve any inherited early-success shortening as an unexpected control-count termination, rather than silently accepting fewer than eight controls as this condition's normal primitive.

Rule STOP is terminal without executing a hold, GRASP or lift. The earlier local GRASP+10mm lift witness began at a separately qualified scripted pregrasp boundary; nominal distance STOP on this mixed-support TCP cue does not establish the corresponding jaw/object arrangement. A grasp extension is not part of this experiment.

## Passive native contact evidence and termination

Reuse `local_grasp_interface.native_observer` and its nonmutating `contact_snapshot` to preserve every native BEFORE/AFTER raw contact, force vector, qpos/qvel, wrist buffer and integration fingerprint. No added live forward refresh. Existing read-only guards verify integration state and selected pose/sensor caches around capture and endpoint reads. Native derived contact/force buffers can be older than post-step time/qpos; record both stages separately without claiming continuous-time onset.

At initial reset, record baseline robot contact pairs using Task2's existing strict normal-force threshold `>0.05N`. During approach, record the first native sample containing an above-threshold robot pair absent from that baseline, including bottle contact and robot self-contact. Preserve the immediately preceding observed sample and all later contacts within the same primitive. Do not raise from `mj_step` for contact or otherwise interrupt a normally started atomic primitive: the observer is passive. Complete that primitive, retain its unchanged execution validation, then stop before another action. This is an evaluator/oracle abort at an action boundary, not a sensor-derived safety controller and not prevention of contact.

Classify first contact in evaluator records as pad/bottle, other-gripper/bottle, gripper/other-scene, arm/scene, or self. These are terminal boundary evidence, not universally invalid interactions. Retain all simultaneous qualifying pairs at the first stage and all later qualifying pairs through the completed primitive, so an initially designated bottle contact cannot hide later self/other-scene contact. All raw contacts are retained; classification does not steer action choice. Record executor violations separately even if the same action also encounters contact. The older observer's `unexpected_robot_contact` field is preserved as raw legacy evaluator output; the new approach stop uses all robot pairs, independent of that field.

Stop on first completed-action contact flag, unchanged execution-validator failure, rule STOP, 40-action cap or wall limit. Read-only invariant failures, nonfinite data, unexpected control/integration counts, source/frame admission failures and runtime errors stop immediately, preserving any partial action. No extra action follows any stop. Save the entire first trajectory and terminal image when normal execution permits; never continue merely to make a cleaner demonstration.

## Freeze, preflight and report

Freeze wrapper/protocol/tests and unchanged runtime/backend/decision/RGB-D/native-observer hashes before dynamics. Run a real-source preflight that loads the actual BOX/point/frame schemas, checks the completed journal, verifies source identities and initializes configured library imports without constructing a world. Independent review must pass before the physical invocation. Use GPU4, EGL4 and no model calls. Keep source fixtures, preflight, native journal, fresh frames, complete new command/state trace and first-contact record.

After one normally terminated collection, replay its newly recorded raw commands once from a fresh Task2 reset with the same clean source/protocol/package/Jev/stepping/GPU identity. Compare every saved control-before/control-after flattened state and own-observation packet and every native BEFORE/AFTER snapshot exactly, including integration fingerprints, and reproduce every saved RGB/depth/K/T capture byte-for-byte. Preserve the first mismatching actual state/snapshot or capture arrays with its expected source key before stopping, so any failure is interpretable without another run. The passive native observer remains installed during replay; this is reproduction, not an observer-removal intervention. No point policy, model inference or archived historical-prefix action is rerun. A source with partial runtime failure is not silently replayed as a completed condition. Stop and retain any replay mismatch without repair or another attempt. Complete replay before report-code edits alter the frozen scientific identity.

Preserve initial, per-control and terminal raw own eef-position, eef-body quaternion and finger-joint observations for later frame interpretation. They do not alter the selector. Eef-body quaternion is not silently paired with the grip-site position as a common pose; any later jaw-frame report must use the separately audited static body-to-site mount. Sensor sample timestamps remain unknown.

Concrete entry points use `python -m embodied_runtime.experiments.task2_box_point_boundary --mode collect --output RUN --review REVIEW` and then `--mode replay --source RUN --output REPLAY`, with the identical GPU4/EGL4 environment. The separate `--preflight --output RECEIPT.json` entry creates no world.

Report initial/final live TCP-to-P distances, every selected token and unchanged validator outcome, action/control/native counts, first observed contact interval/class, all within-action contacts and exact initial image gate. Distances describe approach to P only. If contact-free STOP is reached, it establishes only a nominal point-approach endpoint under this rule; it is not grasp readiness. If contact or validator failure occurs, describe the specific physical boundary without redefining P or tuning the rule afterward. Both source image and physical condition are development evidence. No autonomous grasp/task-completion or environmental-clearance claim follows.
