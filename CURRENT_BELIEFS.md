# Current research beliefs

Updated 2026-09-27 after iterations041–042. This is a short living assessment;
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
| **Observed:** sensor co-motion contains retention information, without establishing a holding estimator. | All492 initial BOX seeds retain a descriptive close/open co-motion contrast in long and actual-executor10mm archives. Short lift: median rise8.585/0.003835mm,3D point–TCP residual2.064/9.502mm; all29,520 rows retained. | Related paired development archives; overlapping windows and mixed initial support. Small-lift transfer changes executor/horizon/scale together, not an amplitude-only ablation. Native LK still succeeds for support departures. Full independent29,520-row/report audit passes. | High for this descriptive contrast; low for general retention inference. Falsifier: fixed measurements fail a separate physical/capture condition. Runtime holding remains unknown. |
| **Observed:** native wrist history carries contact-group information beyond endpoints on one trace. | Fixed force AUROC0.787248→0.987634; missed99 subset0.653918→0.993602, independent raw audit. | Residual overlap32/163 and14/99; dependent single trajectory, moving axes/inertia confounds, no designated contact examples. | High for descriptive ranking; no calibrated detector. Falsifier: frozen features fail on a prospectively different trace/contact regime. |
| **Observed:** existing visual atomic execution supports a local bilateral bottle lift. | Fresh close/open paired slice: +9.279539/+0.001081mm; all4 hard validations pass; closed lift bilateral8/8 endpoints and200/200 each native stage;240-control replay exact. | Scripted privileged pregrasp prefix, no model/sensor-selected approach, one init. Setup01 failed before physics and is retained. | High for this local mechanism. Falsifier: independent audit or prospective sensor-selected approach cannot reproduce the qualified relation. |
| **Observed:** one bottle BOX supplies a plausible point but mixed ROI support. | One12-token/EOS query; center and median contributors match the limited bottle-label proxy;414/492 crop pixels agree. Actual RGB shows tabletop beside the neck. | Depth ownership, grasp center, object width and opposing surfaces remain unknown. One inspected initial fixture; no generalization. | High for recorded support mixture. Falsifier: independent contributor/source audit contradicts the representation. Coarse approach utility is observed; qualified grasp remains unproved. |
| **Observed:** calibrated sample footprints explain potential self contribution omitted by center rays. | All6 registered large-depth-jump centers miss own triangles at center but have1–2/4 sample hits; all99 registered neighborhoods agree between own-qpos and cached-pose coverage. | This is potential coverage, not resolved depth ownership or clearance. Whole-frame pose comparisons still differ at7/2 samples, with discontinuity depth differences up to7.10/16.52mm. | High for frozen geometry. Falsifier: independent geometry or array audit contradicts it. Renderer investigation closes without a live gate. |
| **Observed:** the bottle point-distance rule reaches palm contact before a qualified grasp relation. | Fresh25-action/200-control approach reduces TCP-to-P208.367→50.951mm. First raw palm/bottle row occurs at action22/FWD; first>0.05N at24/DOWN. All25 validators pass; exact replay of controls/native snapshots/26 images. | One inspected init; fixed cached point and oracle-assisted monitoring. No Laya decisions or GRASP. The original scripted pregrasp used translations too, so missing rotations are not established as the cause. | High for first observed boundary. Falsifier: independent trace/contact audit contradicts it. Target-region semantics versus missing surface constraints remain competing explanations. |

## Current discriminating experiments

1. **A surface guard helps approach but exposes an incompatible point goal:**
   the fresh endpoint-veto run completes28 movements/224 controls with zero raw
   robot-contact rows and exact replay. First divergence is22:FWD→LEFT;
   STOP at28 occurs45.730mm from P because remaining moves do not improve P.
   This is not a zero pool, grasp or task success. At frozen terminal orientation
   and jaws, all of the original point rule's ±5mm stopping cell is excluded:
   123 identical point/hand-proxy pairs occur at all eight corners. Independent
   fixed-facet audit reproduces60,300 entries; all witnesses have strict minimum
   facet slack0.293–17.087mm. Conditional on cached partial support/proxies, a
   route-only repair cannot reach that unchanged target cell at this pose.
   No all-orientation or physical impossibility claim. The matched P-to-finite-gap intervention changes STOP→LEFT by only1.959µm
   nominal reduction, driven by small local rotation components. Its registered
   literal gate passes; physical usefulness remains unproved, so no dynamics.
   The complete finite-gap target region is also excluded:124 same point/hand
   witnesses, independently positive0.341–13.999mm facet slack. This is not a
   route-only limitation under the frozen geometry. No new physical policy or
   fitted threshold follows.
2. **Semantic region is usable in one supported format:** one fixed description,
   `the neck of the wine bottle`, yields42 BOX records/260 actual tokens/no EOS
   under the unchanged native256-token cap. No point/support was extracted; no
   prefix salvage or retry. The later matched native POINT pair admits both exact descriptions in10/13
   tokens withEOS. Actual RGB shows whole-body/shoulder versus narrow-neck
   points; both are bottle-proxy interior, with40.456mm projectedZ difference.
   This supports use of explicit part text on this fixture, not independent
   region choice or grasp quality. Full native-input/result/report audit passes (`77c415d`).
   Next compares BOTH anchors with the same18-pose original point-goal-cell
   geometry before any physical trial; no point is selected by outcome.
3. **Coordinate consistency transfers; holding remains unknown:** justified
   nearest-center association removes the epsilon-only switch. The unchanged
   method on30-frame10mm actual-executor pairs keeps all492 seeds and all29,520
   rows;13,776 shared-prefix native rows match exactly. Initial own TCP remains
   null; motion references preclose13 only. Median motion/residual contrasts
   survive, but low LK residual still coexists with boundary sample departures.
   Root inspected all16 lift RGB frames, curves and both departure panels.
   This is descriptive transfer, not a calibrated holding/identity estimator;
   full independent29,520-row/report audit passes (`0144331`).
4. **Frame accounting is qualified locally:**240 saved observations support the
   fixed body-to-site rotation; model packets currently omit orientation. The
   checked transform shows final P remains outside the finite pad Y/Z span, with
   nearest-pad distance34.300mm. It does not explain full palm/object geometry or
   supply a replacement grasp target. Exact observation times remain unknown.

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
- Integrated endpoint/short-lift/goal-cell/finite-gap regression:935 tests pass
  in32.32s at `fe5de7f`; the subsequent region test has its own focused review.
  Production `runtime_core.py`, `adapters/libero.py` and `decision_interface.py`
  remain byte-identical to the baseline.

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
- [Task2 BOX and depth support](docs/evidence/autonomous_research/task2_box_support_findings.md)
- [Calibrated sample footprint](docs/evidence/autonomous_research/pixel_sample_footprint_findings.md)
- [Point versus TCP/pad relationship](docs/evidence/autonomous_research/task2_point_tcp_pad_evidence_review.md)
- [Stored proprioceptive frame audit](docs/evidence/autonomous_research/proprio_frame_consistency_findings.md)
- [Fresh Task2 approach audit](docs/evidence/autonomous_research/task2_box_point_boundary_independent_review.md)
- [Point and jaw interpretation](docs/evidence/autonomous_research/task2_point_jaw_interpretation.md)
- [Single neck-query nonadmission](docs/evidence/autonomous_research/task2_neck_box_support_findings.md)
- [Observed-depth support and nominal gripper sweeps](docs/evidence/autonomous_research/task2_observed_surface_sweep_findings.md)
- [All initial-BOX temporal tracks](docs/evidence/autonomous_research/task2_box_temporal_findings.md)
- [Seven qualified Task2 physical counterfactuals](docs/evidence/autonomous_research/task2_pre22_counterfactual_findings.md)
- [Same-track coordinate association](docs/evidence/autonomous_research/task2_track_association_findings.md)
- [Fresh guarded approach and replay](docs/evidence/autonomous_research/task2_endpoint_containment_veto_findings.md)
- [Short-lift transfer](docs/evidence/autonomous_research/task2_short_lift_transfer_findings.md)
- [Point-goal cell and numerical certificate](docs/evidence/autonomous_research/task2_point_goal_cell_findings.md)
- [Finite-gap local objective intervention](docs/evidence/autonomous_research/task2_finite_gap_control_findings.md)
- [Full finite-gap target-region exclusion](docs/evidence/autonomous_research/task2_finite_gap_target_region_findings.md)
- [Two matched native POINT descriptions](docs/evidence/autonomous_research/task2_point_region_control_findings.md)
- [Observation versus effector goal](docs/evidence/autonomous_research/task2_grasp_contract_source_audit.md)
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
