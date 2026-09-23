# Privileged Drawer Reference v1: dead-end boundary audit

Current authority: [current_state.md](../../current_state.md).
Diagnostic only. No model call, live policy execution, threshold change,
lookahead, hierarchy, ablation or task action was performed.

## Question and method

After 18 genuine Laya decisions, Privileged Drawer Reference v1 reached a
2.732 mm surface gap and its next one-step contract union was empty. This audit
replayed all 144 recorded controls, verified the simulator and controller
identity against the frozen source preview, recomputed all 27
`World.predict_all()` outcomes, and evaluated the unchanged top-drawer clauses
with both original Jev `contracts()` and the current reference builder.

The original Jev source was clean commit
`3bdad985b225aeccc39fbe5863c6eea2e81c515a`. The successful trajectory was
read only for comparison; it was not used as a warm start or policy input.

## Exact first dead-end state

- Simulation time: `7.699999999999374 s`
- Simulator-state SHA-256:
  `ba1d9ee0d186cfb04f94fb4f17f35a580cc350730b065def1f1950fd6d5e66fe`
- Controller context ID:
  `ff643c9c992fe032fa31ea200b2d66aedf09333104ebde08bb8aef00c6a43673`
- Source belief ID:
  `8d20d25686ae4610cce816be6d3da3ca4e4d19c5b71632d82534f46144dd929a`
- Source episode SHA-256:
  `5dda05b5c4aadff4c2fa9e8274730dcbe5f502726c3320dcf2f6d4240cf736a7`
- Drawer opening: `151.65901295563316 mm`
- Surface gap: `2.732324299728142 mm`
- EEF XYZ:
  `[-125.50662649498356, -24.75070633248924, 1170.5729451113293] mm`
- Finger gap: `78.5791991471395 mm`
- Grip command: open, `-1.0`
- Target contact / obstacle contact / success: `false / false / false`

## Complete 27-primitive rejection audit

Every preview used eight controls, a 0.4 s horizon, predicted no success, had
zero obstacle peak force and ended obstacle-free. `A` is advance
(`closure >= 0.01` or success); `E` is establish contact (no current contact /
endpoint contact / `closure >= -0.01`); `P` is approach (no current contact /
gap reduction `>= 2` / no endpoint obstacle / `closure >= -0.01`); `R` is
release required contacts; `W` is an explicit reposition witness. Boolean cells
show every clause in that order followed by the contract result.

| Primitive | Closure mm | Gap reduction mm | Target contact | A clauses | E clauses | P clauses | R | W | Exact rejection reason |
|---|---:|---:|---|---|---|---|---|---|---|
| x-40mm | 0 | -17.6163238379065 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| x-10mm | 0 | 0.690235092220072 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| x-3mm | 0 | 1.08049631021413 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| x+3mm | 0 | 1.36677607540774 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| x+10mm | 0 | 1.22573704099242 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| x+40mm | 0 | -8.97108251499449 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| y-40mm | 0 | 1.67663381189114 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| y-10mm | 0 | 1.23848900964209 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| y-3mm | 0 | 1.24700475782484 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| y+3mm | 0 | 1.14086143508235 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| y+10mm | 0 | 1.00625155695159 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| y+40mm | -7.23518949891985 | 2.52860400355592 | false | F/F -> F | T/F/F -> F | T/T/T/F -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| z-40mm | -2.67024877426136 | 2.73232429972814 | true | F/F -> F | T/T/F -> F | T/T/T/F -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| z-10mm | -0.265755865287542 | 2.73232429972814 | true | F/F -> F | T/T/F -> F | T/T/T/F -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| z-3mm | -0.108773173028126 | 2.73232429972814 | true | F/F -> F | T/T/F -> F | T/T/T/F -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| z+3mm | 0 | -1.65174545330797 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| z+10mm | 0 | -8.45083055656069 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| z+40mm | 0 | -37.8223282281021 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| rotate_x-10deg | 0 | -14.3502475180435 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| rotate_x+10deg | -2.21568293573346 | 2.73232429972814 | true | F/F -> F | T/T/F -> F | T/T/T/F -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| rotate_y-10deg | 0 | 0.730204611394352 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| rotate_y+10deg | -0.101070881460386 | -0.0736329790345076 | false | F/F -> F | T/F/F -> F | T/F/T/F -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| rotate_z-10deg | 0 | -0.510917104646401 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| rotate_z+10deg | 0 | -0.320142499155368 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| open | 0 | 1.22553178972333 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| close | 0 | 1.22596371350539 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |
| hold | 0 | 1.22553178972333 | false | F/F -> F | T/F/T -> F | T/F/T/T -> F | F/F -> F | F -> F | No witnessed goal effect in this horizon; not an executable local goal for this decision. |

## Original Jev on the identical snapshot

Original Jev one-step `contracts()` returns `{}`. Its rejection string is
identical for all 27 primitives, and the current reference returns the same
predictions, rejection strings and empty pools. Original
`ValidatedPolicy.choose()` raises `NoFeasibleAction` before calling its policy
API on those predictions. This rules out a port/integration discrepancy at the
one-step contract boundary.

The archived successful run enabled the runner's `lookahead=2` mode, although
its audit records zero two-step searches on its successful path. When one-step
pools are empty, that runner would call `two_step_witnesses()` outside
`contracts()` and retry with explicit reposition witnesses. The present bounded
audit did not invoke that fallback, as lookahead was outside the authorized v1
reference and this diagnostic. It therefore does not claim that the full
lookahead-enabled runner has no continuation.

## Archived successful Jev contact transition

The closest successful state by surface gap is also the step immediately before
the first contact-producing action:

| Step | Gap mm | Opening mm | Current contact | Eligible pools | Selected | Predicted / actual closure mm | Endpoint contact | Temporary opening? | Pose difference from dead state |
|---:|---:|---:|---|---|---|---:|---|---|---:|
| 4 | 2.397207118124928 | 151.65901295563316 | false | advance: y-40,y-10,y-3,z-40,rx-10,rx+10,rz-10; establish: z-40,rx+10; approach: y-40,y-10,y-3,z-40,z-10,rx+10 | y-40mm | 30.94565275646352 / 30.94565275646352 | false | false | 67.1853 mm / 47.3696 deg |
| 5 | 0.0021545572901442065 | 120.71336019916964 | false | all 27 advance; establish: y-40,z-40,rx+10,rz+10 | z-40mm | 7.163407067741156 / 7.163407067741156 | true | false | 71.5225 mm / 47.3011 deg |

The successful trajectory did not temporarily open the drawer to establish
contact. It approached with a materially different end-effector pose and had
closure-positive primitives at both boundaries. Surface gap alone is therefore
not a sufficient equivalence descriptor. The successful path avoids the audited
one-step contract state, but this does not prove the frozen state has no
physically useful continuation.

## Classification and next step

**CONTRACT DEAD-END.** Original Jev's unchanged one-step contracts also have no
acceptable primitive on the exact snapshot. This rules out a one-step contract
port bug. The evidence also shows a trajectory contribution, but does not justify
the stronger `TRAJECTORY DEAD-END` label because physical continuation from the
state was not proven impossible.

The smallest justified future change to review is a named contact-transition
contract requiring no current target contact, an obstacle-free endpoint, newly
established target contact, and a verified next primitive from the fully restored
endpoint that recovers the temporary opening and yields positive net closure over
both primitives. That identifies the excluded physical transition without
admitting arbitrary opening. Jev's reversible witness mechanism is a possible
existing mechanism to assess separately. This audit does not authorize or
implement it, and it does not justify increasing the `-0.01 mm` threshold.

## Evidence identity

The authoritative tracked table above was generated by
`embodied_runtime.experiments.dead_end_boundary_audit`. Full-precision contact
pairs, predictions and all clause fields are retained in ignored local artifacts:

- `runs/privileged-reference/dead-end-boundary-audit-v02/episodes.jsonl`
  SHA-256 `fb0a611f2e4b7430699296a80ac8bb95954c0d891b97b165554024c114d27c2a`
- `runs/privileged-reference/dead-end-boundary-audit-v02/dead-end-boundary-audit.json`
  SHA-256 `615d5ffd1abafeb55ad2308cf928841cff7b8a09ac93196fef5f611d8f319c3c`
- `runs/privileged-reference/dead-end-boundary-audit-v02/dead-end-boundary-report.md`
  SHA-256 `abf7bf82125cf83b314bd62901b742ad14ae482ff4105322df5f1e3b91a93d21`

Successful-trajectory source hashes are
`eced2be815f53d6e93a9a30a87a2d143acf5e751cc2c642df044f81bd0830002`
for `trace.jsonl.gz`,
`b45317811b9dd23235da4ca5648c45334e10388016c9a9f092d4b482a568d0bc`
for `predictions.jsonl.gz`, and
`495d8865438cf37a90b29f3eb527346ec20212e7f229cb3387239adc13adb451`
for `task_config.json`.
