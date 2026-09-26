# Current project state

Reviewed 2026-09-27 after research iteration029. This is the authoritative current
summary. Historical phase restrictions in older evidence describe those completed
experiments; they do not override the current autonomous research mission.

## Mission and working state

Discover the smallest defensible information interface and division of
responsibility for manipulation under perceptual uncertainty. A VLM planner,
Laya motor decisions, semantic grounding, geometry, temporal belief and candidate
effects are hypotheses whose value must be demonstrated.

Experimental baseline: `share_main` at
`b73b5b43dbef29749677fae06b25e94ca27bad87`. Integration proceeds on
`research/embodied-interface-discovery`; research changes have not been pushed or
merged into `share_main`. No competent hierarchical sensor-driven manipulation
architecture has yet been established.

Read [current beliefs](../CURRENT_BELIEFS.md) for falsifiers/confidence and the
[research log](research/autonomous_research_log.md) for every intervention,
interpretation and next decision. These take precedence over historical plans.

## Preserved privileged baseline

The frozen drawer goal-completion reference achieved official success3/3 using
122 primitives,111 genuine Laya multi-candidate decisions,11 forced singletons
and one lookahead recovery. Opening changed151.659013→−0.392884mm. Predictions
matched execution, and complete970-control trajectories replayed exactly. The
TaskSpec/TaskAdapter extraction preserved inputs, pools, traces and replay, with
three further fresh-process successes. See
[local-objective reference](evidence/decision_interface/local_objective_reference.md).

The architecture includes privileged simulator effects, task-specific admission
contracts and deterministic objective routing before Laya chooses an atomic
candidate. The router is task policy, not a directly reused Jev model-selected
intent. Compact witness presentation preserves every candidate. The canonical
successful run is a privileged **goal-completion** reference, not proof of a
learned intended manipulation skill.

The later canonical native-stage audit reproduces all122 primitives/970 controls
exactly and finds **zero raw designated fingerpad/handle contact rows** in48,500
snapshots around24,250 integrations, including subthreshold rows. Non-designated
contacts occur within288 controls but at only134 endpoints. The net closure is
unchanged; class-conditioned displacement is descriptive, not exact causal
allocation. See [canonical contact audit](evidence/autonomous_research/task1_native_contact_attribution_findings.md).
Historical tags, success labels and original evidence remain unchanged.

Task2 is the derived combined wine-bottle/bottom-drawer task using original
LIBERO init0/seed1: place/release the bottle and close the drawer. The earlier
containment-only diagnostic reached grasp, transport, In, release and substantial
closure but not full closure. Strict placement semantics require oriented object
extent to fit the articulated region before release. The strict fresh gate stops
before22: all27 one-step options and729 two-step pairs have no qualifying witness
at that snapshot. An audited alternative trajectory avoids that snapshot but
later also becomes contract-empty; complete strict feasibility is unresolved.
No Task2 Laya run or success is claimed. See
[interaction-boundary audit](evidence/privileged_reference/interaction_boundary_audit.md).

## Current autonomous research evidence

| Question | Bounded evidence and limitation |
|---|---|
| Can correct supplied context repair tested Laya motor ranking? | Tested situation/action-definition/native-progress presentations did not repair weak choices on development fixtures. Exact model inputs/logits were audited. Further local prefix variants stopped. This is not universal model incapacity. |
| Does a VLM earn the planner role? | Exact matched3B/7B inputs: coherent relations0/6 for both; scored7B subgoals0/3, equal its task-only control. Useful individual relations improve2/18→9/18, often constant-label gains. No larger hierarchy is earned. |
| Can simple sensed geometry drive approach? | Initial grounded POINT plus proprioception drives useful coarse approach, then nonhandle finger contact at action25;26 actions/208 controls replay exactly. Oracle contact monitoring aborts; this is not a deployable safety result. |
| Does own geometry help explain the boundary? | Robot-only calibrated FK reproduces archived own poses without object-state inputs. Seven native options at the examined boundary contain no qualified contact-free positive one-step witness; this does not prove global unreachability. |
| Are endpoint contact observations sufficient? | No: native sampling reveals contacts missed by all eight endpoints in one arm and154 additional contact-bearing controls in the canonical drawer trace. |
| Does wrist history contain extra evidence? | Fixed offline force AUROC0.787248→0.987634 for gripper-only versus no>1N robot contact; missed99 subset0.653918→0.993602. Residual overlap, single-trajectory dependence and dynamics/cache confounds remain. No calibrated contact/holding gate. |
| Is center-ray depth reliable at gripper edges? | Exact rendering reproduction plus fixed-cache MSAA intervention changes registered depths by up to735mm. FK/cache projected differences remain below0.005px. Resolved depth ownership cannot be assumed to be pixel-center ownership. |
| Does the actual visual executor support a local grasp/lift? | Fresh paired scripted-pregrasp test: GRASP+10mm lift moves bottle9.279539mm versus open0.001081mm, all4 unchanged hard validations pass, bilateral pads8/8 endpoints and200/200 each native stage.240 controls replay exactly. Approach and action choice were scripted, not sensor/model-selected. |
| Does one bottle BOX provide useful geometry? | One full-RGB query produces a plausible point.414/492 fixed crop pixels agree with a limited rendered-mask proxy; visible tabletop contaminates the rest. The cloud is not bottle-only geometry, and the point is not a certified grasp center. |
| Can calibrated sampling explain edge returns? | All6 registered large-depth-jump center rays miss own triangles but have partial native sample support. This explains potential self contribution, not resolved depth ownership, target extent or action clearance. The geometry investigation is closed. |

Detailed entry points: [mechanical local witness](evidence/autonomous_research/local_grasp_interface_findings.md),
[wrist history](evidence/autonomous_research/offline_wrist_history_findings.md),
[render sampling](evidence/autonomous_research/render_measurement_diagnosis_findings.md),
[7B control](evidence/autonomous_research/vlm_capability_control_findings.md),
[coarse physical trajectory](evidence/autonomous_research/coarse_initial_point_findings.md).

## Active next questions

1. Fresh Task2 reset: exact initial RGB/depth/K/T match permits explicitly cached
   BOX-point reuse with live proprioception and the existing seven-option10mm rule.
   No fitted target offset or archived-control initialization. Native contacts are
   passively observed; complete the atomic action, then stop before the next one.
   This is an approach-only diagnostic with oracle-assisted stop monitoring.
2. Audit site-position/body-quaternion frame consistency from archived evidence
   and own calibration before interpreting jaw-relative target geometry.
3. Inspect the resulting first physical boundary before adding grasp routing,
   model hierarchy or full-task complexity. Point convergence alone is not grasp.

## Protected execution and evidence boundaries

Production `runtime_core.py`, `adapters/libero.py` and `decision_interface.py`
remain byte-identical to `b73b5b4`. New experiments and measurements are isolated
from the live runtime. The existing27-action native and10mm visual action families
have different validation semantics; success in one must not silently certify the
other. Oracle previews, geometry, contacts and success predicates retain explicit
provenance, including when used only for evaluation or diagnostic aborts.

Sensor observations, proprioception, calibrated geometry, learned estimates and
oracle state stay separate. Unknown holding, actual sensor sample timestamps,
hidden surfaces and semantic confidence remain unknown. A parsed box's score1
is not calibrated identity confidence. Real sensor calibration, complete visual
manipulation and real-robot transfer are unvalidated.

Latest integrated regression at `b924819`: **872 tests pass** in31.68s, including
contact/render/wrist/local-grasp/BOX/footprint additions. Log:
`runs/autonomous-research/regression-box-footprint-integration.log`.
Experiments additionally have frozen pre-execution reviews and independent raw
checks; repeatability is not generalization.

## Workspace and evidence lifecycle

Raw evidence lives under canonical `runs/` and is generally gitignored; tracked
reports include hashes and source identities. A fresh clone does not contain all
raw evidence. Preserve unique observations, failures and historical tags.

Completed checkout cleanup removes reconstructible caches and idle worktrees
after integration, exact-source preservation and dependency checks.27 inactive
checkouts have been removed; four active environments remain. See
[workspace lifecycle](research/workspace_lifecycle.md) for the inventory,
restoration commands and closeout policy. Earlier detailed state descriptions
remain available in Git history and their linked evidence records.
