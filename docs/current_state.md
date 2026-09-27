# Current project state

Reviewed 2026-09-27 after research iteration050. This is the authoritative current
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
| Can the unchanged bottle point guide a grasp approach? | Fresh25-action approach reduces TCP-to-P208.367→50.951mm but reaches palm/bottle contact. First raw row: action22/FWD; first>0.05N:24/DOWN. All25 validators pass;200 controls,10,000 native snapshots and26 frames replay exactly. No GRASP or Laya call; no qualified grasp relation. |

Detailed entry points: [mechanical local witness](evidence/autonomous_research/local_grasp_interface_findings.md),
[wrist history](evidence/autonomous_research/offline_wrist_history_findings.md),
[render sampling](evidence/autonomous_research/render_measurement_diagnosis_findings.md),
[7B control](evidence/autonomous_research/vlm_capability_control_findings.md),
[coarse physical trajectory](evidence/autonomous_research/coarse_initial_point_findings.md).

## Active next questions

1. The fresh endpoint-containment guard completes28 movements without raw
   robot-contact rows, then stops45.730mm from P. Exact224-control/11,200-native-
   snapshot/29-capture replay passes; first22 actions match the old trajectory.
   At the new boundary, only FWD/DOWN are vetoed and all eligible translations
   worsen the original point objective. Full independent result/report audit
   passes. See [guarded approach](evidence/autonomous_research/task2_endpoint_containment_veto_findings.md).
2. The unchanged point goal is incompatible with that guard at frozen terminal
   orientation/jaws:123 identical observed point/hand-proxy pairs occur at every
   corner of the analytically derived ±5mm point-rule stopping cell. Independent
   fixed-facet recomputation verifies all60,300 entries and strict0.293–17.087mm
   witness margins. This is a conditional proxy exclusion, not physical/global
   unreachability. A matched finite-pad-gap
   objective changes STOP→LEFT by only1.959µm nominal reduction. This passes its
   literal gate but earns no physical test. The entire rotated finite-gap target region is also excluded by124 shared
   hand-proxy witnesses, with independently positive0.341–13.999mm facet slack.
   This remains conditional on frozen own pose/proxies/observed support.
3. The privileged grasp contract targeted whole-object geometry center relative
   to pad midpoint. The sensory rule targets TCP distance to an unverified
   median-ray P. Neither better object naming nor adding planning silently fixes
   that relation mismatch. See [source audit](evidence/autonomous_research/task2_grasp_contract_source_audit.md).
4. All492 initial BOX seeds transfer to30-frame actual-executor10mm close/open
   archives. Median rise8.585/0.003835mm and point–TCP residual2.064/9.502mm show
   descriptive co-motion. Native success persists at support departures; no
   holding classifier. Source initialTCP remains unknown. Root inspected actual
   lift frames and failure panels; independent full-row/report closure passes (`0144331`).
   See [transfer](evidence/autonomous_research/task2_short_lift_transfer_findings.md).
5. The earlier neck BOX query remains nonadmitted:42boxes/260tokens, noEOS.
   Two later matched native POINT calls both admit in10/13tokens withEOS.
   Whole versus neck text produces different visibly relevant locations,
   projectedZ difference40.456mm. Same originalRGB/model/settings, freshprocesses,
   no retry; explicit part use is not independent planning or graspquality.
   Full input/result/report audit passes (`77c415d`). Matched18-placement geometry
   now independently reproduces all120,600 containment booleans: whole exactP
   contains129 points and has104 shared hand witnesses across its ±5mm cell;
   neck exactP contains zero, but four lower-Z corners remain positive.
   The predeclared exploratory physical gate passes, not a clearance/grasp gate.
   See [matched cells](evidence/autonomous_research/task2_point_anchor_goal_cells_findings.md).
6. The fresh POINT pair now completes under unchanged point rule/BOX guard:
   whole30 actions ends43.052mm from its own goal, guard-limited; neck29 ends
   5.010mm from its own goal, original rule STOP. Separate replays reproduce
   all472 controls/23,600 native snapshots/61captures; zero raw robot contacts.
   First difference is decision5 at identical state/exclusions. Crucially, the
   terminal TCPs differ only9.022mm and both lie within6.130mm of the neck point.
   Root inspected the actualRGB and independently checked finite-gap arithmetic:
   own-P membership false/true is not proof of grasp superiority.
   See [full paired trace](evidence/autonomous_research/task2_point_anchor_approach_findings.md)
   and [RGB/gap interpretation](evidence/autonomous_research/task2_point_anchor_approach_interpretation_findings.md).
7. The fixed fresh2×2 now completes with all four primary/native/auxiliary replays:
   whole CLOSE lifts center8.262mm, neck CLOSE9.013mm; both OPEN controls0mm.
   All1,008 controls/50,400 native snapshots pass. The registered sampled-endpoint
   witness is whole false(7/8 bilateral), neck true(8/8), but native maintenance
   is172/200 and183/200 respectively. Both final GRASP endpoints lack contact;
   bilateral grasp arises during the lift. This is sensor-selected approach plus
   scripted experimental actions, not autonomous manipulation or fullTask2 success.
   Root inspected all40 fixedRGBs. The added stationary-GRASP pair now also
   completes: both final added endpoints have bilateral pads and all200 native
   BEFORE/AFTER lift samples retain them, with9.403/9.363mm center rise. All520
   controls/26,000 snapshots/67primary+48aux captures replay. Whole establishment
   includes one strong finger/bilateral overlap perstage(max0.386N); no raw
   non-pad/table contact occurs at sampled lift stages. Time, arm drift and
   contact rearrangement are not isolated. No fixed two-GRASP policy is deployed.
   Root inspected all36 new originalRGB panels.
   The unchanged temporal extraction retains91,512 rows and exact32,964 native
   prefix comparisons. Close/open median motion contrast transfers, but210–242mm
   displacement tails survive all native/depth gates. Root independently audits
   all rows/arithmetic and inspects curves/overlays. A fixed four-seed source
   diagnostic now shows unflagged depth-boundary switches, including a0.08px
   shift selecting depth212.773mm farther away. Root inspected all20 original
   context/depth panels. This is selected failure analysis, not a failure rate.
   The full-population2D comparison now completes: final median RGB motion
   3.871/4.129px CLOSE versus0.003165/0.002232px OPEN, retaining all91,512 rows
   and overlapping tails. Independent arithmetic, source, report and plot audit
   passes. Neither RGB displacement nor its calibrated own-TCP residual needs
   scene depth for this local contrast; neither establishes target ownership or
   holding. Root inspected both complete plots. Next is the same-approach
   neck present/relocated negative with matched privileged scene synchronization,
   fixed suffix exposure and event-aware replay, currently in preparation.
   See [image-motion findings](evidence/autonomous_research/task2_point_anchor_image_motion_findings.md).
   See [raw mechanical audit](evidence/autonomous_research/task2_point_anchor_grasp_transfer_raw_review.md).

For these new POINT approach/grasp collections, the actual closed manifests use
`/home/junhongli/miniforge3/envs/laya-embodied/bin/python`, GPU4/EGL4. General older
environment notes suggesting locateanything must not override those recorded
dependencies. The root's mistaken environment assumption and its correction are
preserved; admitted grasp freeze `1702cb2` uses preflight02, not alternative03.

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

Latest integrated regression at `1e665a2`: **1131 tests pass** in43.44s, including
the scene-event/replay hooks and new source-bound sensor adapters.
Log: `runs/autonomous-research/regression-closed-empty-event-integration-01.log`,
SHA256 `15b08cb0c1f28cfcd48578ec3ae9093454f69f5fe81b7720f3c13f0f9000acb5`.
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
