# Current project state

**Latest: offline human-region geometry diagnostic completed, execution `eb8028e`.**
[Report](p1-human-region-geometry-results.md) and
[evidence](evidence/p1_grounding/human_region_geometry_20261007/README.md).
25/25 frozen VISIBLE wrist frames produce 130 raw geometry candidates under
unchanged gates. NO_TOOL_INTERIOR_CANDIDATE 0/25; every candidate remains UNKNOWN
for execution. Annotation is offline target support only, not perception evidence.
Next priority is semantic identity/support repair followed by new held-out
validation. No further experiment started. P1 acceptance remains unearned;
reference/VERIFY UNKNOWN and temporal/P2/Qwen/Laya blocked. Prior e8cda1e evidence
is frozen and preserved. The earlier dated entries retain their historical scope.


**Latest completed batch: POINT + BOX identity development repair,2026-10-07.**
Frozen execution `b7f5409`; [report](p1-identity-prompt-results.md) and
[complete evidence](evidence/p1_grounding/identity_prompt_20261007/README.md).
50 fixed-query POINT calls,23 typed admissions,7 outside-original-BOX rejections,
16 completed SAM calls,48 native masks evaluated,102 planned slots NOT_EVALUATED.
0 task-valid candidates. Raw candidate count9,149, all outside annotated front.
Same generated8wrist frames: baseline9,226 outside proposals vs new9,149;
median contamination94.218%→96.808%. Admission filtering is recorded separately.
2/9typed wrist POINTs label-correct: init1 blocked by originalBOX; init12native1
reaches a better front plane but NO_TOOL_INTERIOR_CANDIDATE. No fallback/tuning.
Six focused tests pass; unchanged runtime/geometry/model/weights/query/gates.
The set was previously exposed; this is development, not held-out acceptance.
P1/temporal qualification remains unearned, reference/VERIFY UNKNOWN; P2/PUSH/
Qwen/Laya blocked. Stopped for review. No fresh inference or automatic next repair.
The dated checkpoints below preserve their historical status.


**Previous: Formal-50 complete at clean execution `e1ff472`, 2026-10-07.**
[Full report](p1-formal50-results.md),
[checkpoint/evidence](evidence/p1_grounding/formal50_20261007/README.md).
All50 archived BOX inputs →150 native SAM masks → frozen geometry → sealed
blind annotation scoring. No failures/retries/winner. Human wrist25 VISIBLE,
agentview25 UNKNOWN (neither NOT_VISIBLE). Wrist33 masks produce45,252
geometric proposals, all outside the human drawer-front region; correct
tool-supported candidate evidence0/25 visible inits. Raw identity/geometry
taxonomies and offline p50/p95 retained. All10 review sheets inspected.
Nine focused tests before freeze, two independent source/scoring/visual audits.
Init25/26 tuning remains CLOSED. No query/gate/weight/order/controller change.

Next-round proposal B: bounded P1 grounding/identity representation repair,
not yet implemented. Temporal qualification not earned; no new10 sequences,
tracker, reference decoder, PUSH/P2/Qwen/Laya run. Reference/VERIFY UNKNOWN.
**P2 remains blocked pending Formal-50 / temporal P1 gate**; Formal-50 is now
complete. No final scientific Gate A/B/C assigned this round. Stop for review.
Route remains Formal-50 →10 temporal sequences →P1 GateA/B/C →P2a/B0.

The following entries preserve historical checkpoints and their then-current
Gate C conclusions; they do not override the latest bounded evaluation status.

**Previous: mask-support repair at clean `5f97166`, 2026-10-07.**
[Repair/results](p1-mask-support-results.md) preserve `b5ada28` inference and
`26648a3` evidence. Full native-mask depth availability replaces BOX coverage
as segmentation availability; original thresholds and downstream gates remain.
Offline all6 replay gives availability1.0 but all6 ambiguous components and0
candidates. Both old BOX and all six legacy mask results match exactly;
13 tests and independent audit pass. No model/control/tracker calls.
**Init25/26 tuning is CLOSED.** Next is frozen50-frame annotation/observability
evaluation: its input/code/annotation/BOX packet is pinned; repaired scoring is
pending native masks for50 source IDs, whose inference is excluded this round.
No old BOX-only/development substitution; future outside-label points are
semantic identity failures. Then10 temporal sequences → GateA/B/C → P2a/B0.
P1 remains Gate C; reference/VERIFY UNKNOWN, no PUSH/model coupling.

**Latest substantive result: 2026-10-07, clean execution `b5ada28`.**
[Completed BOX/SAM2 comparison](p1-segmentation-results.md) preserves all six
native masks on init25/26 development frames, strict determinism and unchanged
queries/source/weights/geometry gates. A dense-grid arange overlay passes exact
native-size raw-byte coordinate/PE checks; no learned buffer or official SAM
source change. A reporting-only duplicate-key error is separately retained,
then disclosed fresh-process continuation completed both masks/geometry stages.
Original and regenerated init25 NPZ bytes match. Zero new LocateAnything calls.
Four broad masks remain depth-ambiguous; two narrow masks22.004/36.783% fail the
unchanged original-BOX depth gate before plane fitting. All candidates0; no mask
winner. This localizes mask-support/ROI-measurement incompatibility and retained
part ambiguity, not absent physical geometry. P1 Gate C remains. A future
mask-support measurement experiment needs a separate condition; no automatic
denominator repair, tracking, reference/VERIFY or P2/model integration occurred.

**Latest continuation: 2026-10-07, clean execution revision `305056a`.**
[Launcher correction evidence](evidence/p1_grounding/box_sam2_continuation_20261007/README.md)
confirms prepared venv identity and byte-identical sealed BOX reuse with zero new
LocateAnything calls. SAM model construction and init25 image encoding completed;
first mask prediction stopped at unsupported strict-deterministic CUDA `cumsum`
in dense positional encoding, before mask decoder execution. Zero returned masks,
zero geometry evaluations; init26 not attempted. No retry or determinism relaxation.
This is operator compatibility evidence, not segmentation-quality evidence.
P1 Gate C, reference/VERIFY UNKNOWN and no control/model integration remain.

**Latest execution receipt: 2026-10-07.** The selected architecture/milestones
remain unchanged. [P1 observability closure](p1-observability-closure-results.md)
finished at `1fedb9c` with Gate C, not continuous drawer/reference tracking.
The [two-sample BOX/SAM2 diagnostic](evidence/p1_grounding/box_sam2_development_20261007/README.md)
ran at clean `1ef973a` on `feat/p1-segmentation-surface`: isolated dependency setup
passed and one new init26 BOX completed; init25 BOX was source-authenticated.
The parent SAM launcher resolved the venv Python symlink to a base interpreter
and failed the pinned Torch guard before any model call. This condition is
STOPPED, with zero masks/geometry evaluations, no retry and no scientific
segmentation conclusion. Reference/VERIFY remain UNKNOWN. Correcting the launch
path would require a separately identified follow-up condition, not overwriting
this failure. The earlier dated records below remain historical evidence.

**Current implementation checkpoint: 2026-10-06.** The selected architecture is
Qwen3-VL brain → Laya local selection → continuous RGB-D geometry / deterministic
servo, evaluated later with B0–B4. [P0 is accepted](p0-acceptance.md).
[P1 capture/geometry/tracking and replay are implemented](p1-rgbd-checkpoint.md),
but drawer-front grounding and cabinet-relative VERIFY remain unestablished;
P1 task acceptance and P2 control are pending. Current branch:
`feat/p1-grounding-observability`. Infrastructure checkpoint `92865a8` is preserved.
The [completed grounding closure](p1-grounding-results.md) includes the corrected
human-label provenance, 100 sealed fixed-query calls over 50 views, ten exploratory
temporal acquisitions, and timing evidence. Grounding/reference identity was not
established; none of the temporal acquisitions qualifies as target-valid tracking.
The current bounded [surface-association development probe](research/p1_surface_dev_protocol.md)
uses fresh init 25/26 at 384×256, exact native BOX/POINT queries, retained depth
surface supports and the unchanged tracker gate. This is development diagnosis,
not reuse of evaluation labels or acceptance of P1. No PUSH, P2, Qwen or Laya
integration is authorized in this batch.
The [2026-10-06 repair-batch receipt](evidence/p1_grounding/surface_dev_20261006/README.md)
records fresh capture success and a CPU inference ceiling: only one BOX completed
in 816 seconds; no complete POINT/pair exists, so association and tracker
initialization on real development frames remain untested. The tools and four
focused correctness tests are complete; P1 task acceptance remains pending.
The [earlier GPU preflight](evidence/p1_grounding/surface_gpu_preflight_20261006/README.md)
was blocked by the session's device sandbox. GPU access is now restored. The
[frozen-input GPU diagnostic](evidence/p1_grounding/surface_gpu_diagnostic_20261006/README.md)
ran at `1af81e4` on UUID-allocated GPU 2 and stopped after its first reference
POINT produced mixed output at the 256-token ceiling without EOS. Only two of
eight calls ran; no valid pair, drawer-front surface acceptance, geometry analysis
or tracker test exists. Original recorded evidence/queries/gates remain unchanged.
Independent fixed cabinet reference observability remains the gate after
successful association, not PUSH. P1 acceptance remains pending.

The [2026-10-07 separately registered drawer-front pair](evidence/p1_grounding/drawer_pair_20261007/README.md)
ran the first previously unstarted init25 wrist pair at `f077df8`. Both calls
ended with EOS, but POINT mixed one point and one box and failed strict semantic
admission. No point was bound or tracker initialized. The initial offline
analyzer unnecessarily enumerated five supports; `34b799c` fixes admission order
and rejects the same sealed output before geometry. Both records are preserved;
the earlier original eight-call batch remains incomplete. No model/query/gate
change or further inference followed. Surface association, reference/VERIFY and
P1 acceptance remain unestablished.

The [2026-10-07 typed semantic-output contract repair](evidence/p1_grounding/semantic_contract_20261007/README.md)
reuses the exact `f2af8d8` sealed drawer pair with no new inference. Under the
separately preregistered typed condition, one POINT is admitted and its auxiliary
BOX retained without becoming an ROI. The unchanged independent BOX search
binds one valid vertical support; two-agent RGB review supports the visible
drawer-front interpretation (development evidence, not verified identity).
The first separate tracker initialization at `3e5bd6a` raises `WRONG_EPISODE`:
existing harness episode differs from the recorded frame. No tracker result,
retry or reference stage follows. Source/query/model/geometry/tracker gates stay
unchanged. Fixed reference/VERIFY and P1 task acceptance remain UNKNOWN/pending.

The [2026-10-07 episode-ID harness repair](evidence/p1_grounding/tracker_episode_repair_20261007/README.md)
uses the immutable recorded episode in a separately registered tracker replay at
`ab361eb`. The same reviewed drawer-front support now initializes as TRACKED
(depth support1.0, spread20.439mm against unchanged30mm gate). This is single-frame
offline initialization only. Afterward, independent sealed reference admission
still rejects the historical256-token no-EOS POINT; no reference geometry or
tracker follows. Reference/VERIFY stay UNKNOWN, P1 task acceptance pending.
No new model calls, query/gate changes, temporal updates or actions occurred.

The [2026-10-07 independent reference budget diagnostic](evidence/p1_grounding/reference_budget1024_20261007/README.md)
freezes `ab361eb` infrastructure and `065ad2b` evidence with local annotated tags.
One fresh POINT at clean `bdab332` changes only max_new_tokens256→1024, preserving
sealed reference RGB/query/input, checkpoint, old BOX, native hybrid/EOS and all
contract/geometry/tracker gates. It again reaches the token ceiling without EOS.
Completion fails before any typed POINT parse or downstream association/track.
No retry, temporal relation or action follows. Reference/VERIFY remain UNKNOWN;
fourfold budget alone is insufficient for this condition, not proof of impossibility.

The following is the preserved **2026-09-27 historical research checkpoint**.
Its paused status and architecture-search authority do not describe the resumed
selected implementation work above.

**Paused by the user on 2026-09-27.** Historical local checkpoint tag:
`research-checkpoint-20260927-paused`. No active research processes or automatic
retries. See [checkpoint receipt](evidence/autonomous_research/pause_checkpoint_20260927.json).

Reviewed 2026-09-27 after research iteration057. This is the authoritative current
summary for that historical checkpoint. Historical phase restrictions in older evidence describe those completed
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

The subsequent matched neck present/away source is now observationally qualified:
both fresh32-action/256-control collections complete; present lifts9.402435mm,
away0mm with zero raw robot/bottle contacts. Both exact replays are available,
but the original matrix remains interrupted/incomplete143: a separate second
away verification passed, with zero recollection and the original files unchanged.
Forced refresh changes own-observation sampling phase equally in both cells;
old-source returned packets cannot substitute for the new sham. Empty prelift
jaws still move; no settled-empty label. See
[source and timing](evidence/autonomous_research/task2_closed_empty_scene_findings.md).

The fixed post-event image assay retains24,600rows. Present/away final median
motion4.198224/0.058783px, but available counts492/365 differ, and admitted away
positions drift onto robot/background with extremes178.866px. Root inspected
all8fullRGB endpoints and complete curves; full numerical audit passes. No
holding/identity threshold follows. See
[motion evidence](evidence/autonomous_research/task2_closed_empty_image_motion_findings.md).

Four cold native POINT calls then admit both present images and reject both away
images as malformed mixed POINT/BOX outputs. All reachEOS below the cap; exact
inputs/configs/process isolation pass audit. Root's fullRGB inspection places
the two admitted points on the visible bottle body. The hybrid-based downstream
eight-decision comparison remains held. The subsequent two-call native slow
decoder control admits both post-event POINTs in10tokens/EOS, with identical
archived native inputs and only generation mode changed. Present stays[218,193];
away newly admits[228,328]. Root inspected both fullRGBs and found the points
on visible bottle bodies. Independent stored-output audit passes; no inference
retry or old-prefix salvage. This is a two-image decoder-sensitivity result,
not general localization/holding competence or an established MTP bug. A separate
four-record offline comparison now asks whether cached-hybrid versus fresh-slow
goals change existing geometric decisions, with original stale support explicit.
All four offline guarded choices remain FWD; fresh away changes the unguarded
preference DOWN→FWD, while the stale guard already vetoes DOWN for both goals.
There is no immediate guarded-token divergence or physical outcome. Both current
semanticBOX and current raw/partially self-excluded depth are being compared as
alternative support representations. The depth-only diagnostic now completes:
raw support vetoes every translation in both scenes; existing partial silhouette
leaves housing-edge witnesses that change choices to present STOP/away DOWN.
Root inspected actual RGB overlays. Unknown ownership and partial visibility
prevent treating either cloud as a verified environmental guard. Two currentBOX
calls now both admit12tokens/EOS. Holding current goals fixed, present1220points
include40current-handproxy witnesses and change choice FWD→STOP; away2250points
have no endpoint containment, retain FWD and remove old DOWNveto. Root inspected
all41present witnesspixels at the upperBOX/gripper-neck boundary. Neither BOX
is certified segmentation or scene clearance. The preregistered away pair now
has first-choice cachedDOWN versus refreshedFWD under common current support.
Two fresh resets with at most2moves each and exact replay are authorized only
after frozen implementation/mechanical review. Implementation and review
completed, but launch01 exited1 at the preflight-matching gate before any worker
or world construction. No actions occurred. Failure evidence is retained; no
repair/retry occurred before user pause. No physical result exists. See
[four-call evidence](evidence/autonomous_research/task2_closed_empty_fresh_point_findings.md).

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

Latest integrated regression at `97ffa19`: **1173 tests pass** in51.68s, including
the scene-event/replay hooks, slow POINT control and offline paired adapters.
Log: `runs/autonomous-research/regression-slow-point-integration-01.log`,
SHA256 `2d50f04df21ffe94991e01ec36c0d9ab057991b045c600bc4d09d84856d134e7`.
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
