# Current research beliefs

Updated 2026-09-27 after iterations024–027. This is a short living assessment;
[the research log](docs/research/autonomous_research_log.md) preserves iteration
history and evidence identities. Starting baseline: `b73b5b4` on `share_main`.
Current research branch: `research/embodied-interface-discovery`.

**No competent hierarchical sensor-driven manipulation architecture has yet been
established.** The current VLM/Laya division is unvalidated. Tested context and
checkpoint interventions have not earned deploying either model in a larger
hierarchy. This is bounded negative evidence, not universal model incapacity.

## What the evidence currently supports

| Belief / kind | Supporting evidence | Against or unresolved | Confidence and falsifier |
|---|---|---|---|
| **Observed:** privileged goal completion is reproducible; interaction validity is separate. | Frozen drawer:3/3,122 primitives, exact preview/execution and replay. Native replay:0 raw pad/handle rows in48,500 snapshots, exact970-control trace;154 contact-bearing controls missed at endpoints. | No continuous-time or full causal attribution. Strict Task2 ends before22 with no witness among729 pairs. | High for recorded outcomes. Falsifier: independent replay or finer attribution contradicts the bounded measurement. |
| **Observed:** supplied correct context does not suffice for tested Laya motor ranking. | Original choices reproduce exactly; situation, action definitions, joint prefixes and native progress-value criteria fail to repair weak advance ranking. | Development states and presentations are limited; choices are not new physical rollouts. 11-action visual and27-action privileged interfaces differ. | High within fixtures; no general incapacity claim. Falsifier: a prospectively different interface transfers to held-out decisions/behavior. No more prefix micro-variants here. |
| **Observed:** neither tested VLM checkpoint earns the planner role. | 3B/7B: useful relations2/18→9/18, coherent scenes0/6 both; primary subgoals1/3→0/3, each equal to its own task-only control. Exact native inputs/logits/EOS audited. | Most7B gains follow constant labels; lossy development images, dependent mirrors and non-blinded labels. | High for fixed calls; architectural inference weak. Falsifier: image-sensitive useful proposals with matched downstream benefit. No model tournament. |
| **Observed:** one initial semantic point supports coarse approach but not intended contact. | First21 actions/168 controls identical to repeated grounding. Fixed initial POINT passes fresh-grounding error, then finger body hits nonhandle panel at25;26 primitives/208 controls replay exactly. | Target stationary; age reaches10s, current identity/visibility unknown; external oracle abort. Not generic temporal-fusion or manipulation success. | High within this physical control. Falsifier: changed source/prefix or contact evidence. Generality requires held-out conditions. |
| **Observed:** some relevant scene surface and own robot shape are available. | Precontact raw depth has support1.655mm from retrospective collision-region query. Robot-only FK:21 bodies,2 sites,5 gripper proxies, spatial error≤1.11e-15m;8 poison variants identical. | Query uses evaluator truth; calibrated base/camera and model geometry assumed. Extents cover gripper only. This is not a sensor-only hazard detector or real calibration validation. | High for visibility/FK dependency; usefulness unresolved. Falsifier: calibrated sensor-only relative geometry remains uninformative under tested conditions. |
| **Observed:** the original local action regime has no qualified one-step witness at boundary25. | All7 original options executed. DOWN fails2mm motion tolerance with2.114787mm error. Exact finer replay reveals7 nonhandle-contact integration intervals missed by all8 control-end samples. | Detours, other poses/actions/horizons and general reachability are untested. The tracking error's sole cause remains unresolved. | High for measured local result. Falsifier: raw contract/arithmetic audit or exact new evidence contradicts it. Do not relax the contract. |
| **Observed:** sensor co-motion contains retention information, without establishing a holding estimator. | Paired close/lift versus open/lift: body vertical motion109.810 versus0mm while TCP moves114mm;272 controls replay exactly. | Assistant landmark initialization; cap track leaves bottle despite excellent LK residual; table LK fails. Interior-point height is not bottom clearance. | High for paired motion; low for general retention inference. Falsifier: independently initialized temporal estimator fails matched controls. Runtime holding remains unknown. |

| **Observed:** native wrist history carries contact-group information beyond endpoints on one trace. | Fixed force AUROC0.787248→0.987634; missed99 subset0.653918→0.993602, independent raw audit. | Residual overlap32/163 and14/99; dependent single trajectory, moving axes/inertia confounds, no designated contact examples. | High for descriptive ranking; no calibrated detector. Falsifier: frozen features fail on a prospectively different trace/contact regime. |
| **Observed:** existing visual atomic execution supports a local bilateral bottle lift. | Fresh close/open paired slice: +9.279539/+0.001081mm; all4 hard validations pass; closed lift bilateral8/8 endpoints and200/200 each native stage;240-control replay exact. | Scripted privileged pregrasp prefix, no model/sensor-selected approach, one init. Setup01 failed before physics and is retained. | High for this local mechanism. Falsifier: independent audit or prospective sensor-selected approach cannot reproduce the qualified relation. |

## Current discriminating experiments

1. **Task2 target-specific depth support:** one fixed LocateAnything BOX query on
   the inspected initial bottle RGB. Keep the production center/median-depth point
   and the same crop's complete candidate support. Seal before rendered-mask proxy
   evaluation. No oracle cleanup, fitted grasp offset, extra query or dynamics.
   This asks whether semantic localization yields usable object support at all.
2. **Pixel footprint:** native4-sample versus zero-MSAA rendering at identical
   cached geometry changes edge depths by up to735mm; own-FK/cache projection
   difference is below0.005px. A frozen offline own-triangle/sample-ray measurement
   now tests potential self contribution. Resolved depth stays separate; omitted
   geometry, scene occlusion and depth-resolve ownership remain unknown. No gate.
3. **Physical qualification:** the actual visual executor's local GRASP +10mm lift
   now passes from a scripted pregrasp boundary, with exact240-control paired replay.
   The next useful physical comparison requires a sensor-derived approach target;
   this success does not supply an oracle target or an action recipe to that policy.

These address different uncertainties: visibility, identifiable relative geometry,
measured interaction and available action behavior must not be conflated.

## Closed lines and preserved limitations

- Binary predicate tests768+1184 calls did not establish reliable recognition.
  Goal/answer wording biases remain; no further local predicate prompt sweep.
- Grounder POINT improves completeness over BOX but retains identity failures.
  Wrong boundary21 and malformed boundary25 outputs reproduce cold across orders;
  prior inference history is not necessary. Syntax/freshness is not identity.
- LK passes synthetic image translations and fails masked-target reverse status;
  this is not general semantic tracking. Low residual alone cannot certify identity.
- Native Laya audits must check both1024 total and256 heading/options limits.
  A1022-token consumed input can still have silently clipped options.
- No new Task2 Laya run, strict placement/closure success, non-oracle manipulation,
  real-robot calibration, learned world model or cross-task generality is claimed.
- Integrated contact/render/wrist/local-grasp regression:847 tests pass. Production
  `runtime_core.py` and `adapters/libero.py` remain unchanged from the baseline.

## Evidence entry points

- [Current-interface/action investigations](docs/evidence/autonomous_research/native_option_progress_sufficiency_findings.md)
- [7B exact-query control](docs/evidence/autonomous_research/vlm_capability_control_findings.md)
- [Initial-point physical trajectory](docs/evidence/autonomous_research/coarse_initial_point_findings.md)
- [Visibility audit](docs/evidence/autonomous_research/first_contact_observability_findings.md)
- [Robot-only geometry](docs/evidence/autonomous_research/robot_geometry_observability_findings.md)
- [Seven physical options](docs/evidence/autonomous_research/coarse_native_counterfactual_findings.md)
- [Native contact sampling](docs/evidence/autonomous_research/native_substep_observability_findings.md)
- [Canonical Task1 native attribution](docs/evidence/autonomous_research/task1_native_contact_attribution_findings.md)
- [Observed-point proximity](docs/evidence/autonomous_research/sensor_gripper_proximity_findings.md)
- [Calibrated visual-mask control](docs/evidence/autonomous_research/gripper_visual_mask_findings.md)
- [Fixed-cache rendering diagnosis](docs/evidence/autonomous_research/render_measurement_diagnosis_findings.md)
- [Qualified mechanical witness inventory](docs/evidence/autonomous_research/mechanical_witness_inventory.md)
- [Wrist history](docs/evidence/autonomous_research/offline_wrist_history_findings.md)
- [Local actual-executor grasp/lift](docs/evidence/autonomous_research/local_grasp_interface_findings.md)
- [Workspace lifecycle](docs/research/workspace_lifecycle.md)
- [Independent information-boundary review](docs/evidence/autonomous_research/information_boundary_review.md)
- [Retention independent audit](docs/evidence/autonomous_research/retention_independent_audit.md)

## Responsibility and evidence rules

Keep simulator oracle, sensor observations, calibrated deterministic geometry,
proprioception, learned estimates and unknown separate. Candidate admission,
objective routing, history, witnesses and termination also carry provenance.
Raw point clouds are perception evidence; current Laya is a text typed-choice
model. A model answer, official success and interaction-valid success differ.

Freeze a discriminating experiment before inference/dynamics; retain failures,
inspect actual frames/inputs/trajectories, and stop at its declared boundary.
Identical-init replay/repeats establish repeatability, not generalization.
Development states remain development data. Build only what the evidence earns.
