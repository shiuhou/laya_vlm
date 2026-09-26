# Autonomous embodied-interface research log

## Mission and experimental baseline — 2026-09-26

Find the smallest defensible information interface and division of responsibility
that supports competent closed-loop manipulation under perceptual uncertainty.
VLM semantic planning plus Laya bounded embodied decisions is a hypothesis, not a
required architecture. The user authorizes experiments, implementation, autonomous
iteration, sub-agents, and evidence-driven reframing. Earlier restrictions against
perceptual/hierarchy research describe the prior phase and do not bind this mission.

Baseline repositories (clean at inspection):

- Laya: `b73b5b43dbef29749677fae06b25e94ca27bad87`, `share_main`.
- Jev: `11d450455d0307bd806c94a27fc7166efb1c483d`.
- LIBERO: `8f1084e3132a39270c3a13ebe37270a43ece2a01`.

Work proceeds on `research/embodied-interface-discovery`; historical tags, runs,
and evidence remain intact. No automatic merge/push. Use isolated commits for
infrastructure, experimental conditions, independent evaluation, and results.
Local idle GPUs/open weights are the default; no paid API or rented hardware is
assumed. Maximum two GPU workers, no interference with other users' processes.

### Audit observations

Three independent read-only audits reconstructed decision, perception, and
evaluation paths. Laya is text-only, with a 1,024-token total/256-token heading
limit. The live visual adapter creates a point from a queried bounding box and
depth; the richer offline centroid uses all valid box pixels. There is no general
point-cloud/pose/contact belief interface. The privileged TaskAdapter performs
task-policy filtering and routing; simply hiding oracle effect strings does not
make that path perceptual. Existing RGB-D calibration is synthetic calibrated
sensing, not independently established real-camera calibration.

The same-condition Jev comparison used archived original answers checked against
fresh requests. It establishes a feasible trajectory, not isolated hierarchy
causality. The alphabet-soup archive ends still grasped, so it cannot establish
release/settled placement. Strict Task-2 closeability remains unproven.

### Iteration 001 — predicate recognition versus motor selection

- **Research question:** Can frozen Laya recognize each supplied consequence
  conjunction when it fails to select a matching action among eleven candidates?
- **Why it matters:** A correct VLM subgoal cannot by itself repair a downstream
  inability to use the facts required for motor selection.
- **Hypothesis:** Multi-option selection adds a failure beyond recognizing one
  candidate's goal compatibility.
- **Competing hypotheses:** Conjunction recognition already fails; action wording
  or order dominates; the limitation is specific to the old interface.
- **Intervention/controls:** 704 binary diagnostic calls plus 64 exact explicit
  selection controls; frozen model, source state, effects, goals and canonical
  candidates. See [preregistered protocol](predicate_verification_protocol.md).
- **Metrics:** Per-goal confusion/recall/balanced accuracy; answer-order and repeat
  consistency; matched original-selection errors; token/config/raw-output integrity.
- **Result:** Complete 768-call run, all control/repeat/raw-token checks pass.
  Binary TP96/TN33/FP223/FN0; balanced accuracy 56.45%; opening goal always
  receives `satisfies`. Independent audit agrees.
- **Artifacts:** `runs/autonomous-research/predicate-verification-{preflight,run}-01`;
  [audited findings](../evidence/autonomous_research/initial_findings.md).
- **Interpretation:** Reliable predicate recognition cannot be assumed beneath
  failed multi-option ranking. No controller promotion or manipulation claim.
- **Remaining uncertainty:** Binary versus multi-option presentation is a compound
  task-format intervention; model cardinality calibration differs.
- **Next experiment rule:** Decompose predicate failures if recognition fails;
  test bounded selection if recognition succeeds; confirm relevance on current
  reference boundaries before changing the live decision architecture.

### Parallel audit 001 — sensor support versus depth projection

- **Research question:** What explains archived sensor target errors before any
  high-level planner is introduced?
- **Hypotheses:** Target/background support contamination; depth/calibration error;
  different geometric referents; temporal fusion error.
- **Intervention:** Recompute the existing 18 accepted RGB-D/raycast pairs, with
  oracle support restricted to the evaluator. No new perception inference/rollout.
- **Metrics:** Exact raw reconstruction, support purity, raw versus fused target
  error, valid/missing samples, and explicit covariance calibration status.
- **Result:** All 18 boundaries reconstruct exactly. Support-membership component
  exceeds same-support depth residual in all 18; all covariances uncalibrated.
- **Artifacts:** `runs/autonomous-research/perception-support-audit-01`.
- **Next decision:** Only improve a sensor component after identifying an error
  that can change downstream decisions. Do not add a segmentation model by default.

### Parallel probe 002 — fixed depth separation

- **Question / hypothesis:** Can fixed sensor-only depth grouping repair dominant
  support errors without a new model?
- **Intervention:** [Fixed near-depth split](depth_support_probe_protocol.md), all
  18 development frames; no threshold tuning or oracle support correction.
- **Result:** Median surface-centroid error 79.20 to 9.06 mm, preferred nominal
  direction agreement 10/18 to 12/18, three adverse nominal directions unchanged.
- **Artifacts:** `runs/autonomous-research/depth-support-probe-01`.
- **Interpretation:** Improvement in raw geometry does not establish correct
  semantic target support, a grasp pose or physically useful action selection.
- **Remaining uncertainty / next:** Existing LocateAnything POINT grounding can
  test target identity; no high-level planning model is required for that probe.

### Iteration 002 — registered discriminators after iteration 001

- **Decision recognition:** Four fixed binary conditions on 74 unique payloads
  retaining all 176 source lineages: original full rule, negative-label spacing
  only, absolute-direction clause, STOP-relative clause; two orders/two repeats,
  1,184 calls. Separates answer-form sensitivity from recognition deficits.
- **Current interface:** Reproduce five prospectively selected current-reference
  boundaries unchanged (first two genuine decisions per objective plus first
  lookahead: 0, 1, 9, 10, 87), two repeats, ten calls. All admitted candidates are
  contract-positive, so old positive/negative labels would be uninformative here.
- **Grounding:** Matched 36 BOX/POINT calls on the same 18 full-RGB development
  frames, existing checkpoint/query/settings, no new model or live execution.
- **Status:** All three experiments completed. Exact current-interface controls
  reproduce; clause/spacing changes do not recover discrimination; POINT improves
  early grounding but fails all six late cases. See results below.
- **Why these:** These discriminate known model-interface and semantic-support
  failures before adding a high-level planner around them. They do not protect
  Laya or exclude a different model/responsibility split if the evidence warrants it.

### Iteration 002 — results and belief update

- **Current interface:** 10/10 choices, probabilities and logits reproduce the
  archive. At advance boundaries 9/10, passive `open` has much smaller immediate
  closure than other admitted actions. Thus the issue remains relevant to the
  currently successful architecture, despite eventual goal completion.
- **Predicate decomposition:** all 1,184 calls pass integrity; all spaced-label
  conditions classify constantly within goal (closed negative, open positive).
  Per-goal balanced accuracy 0.5; pooled scores are misleading. Clause coverage
  is insufficient for a general conjunction diagnosis. Stop prompt micro-tuning.
- **Grounding:** 36 matched calls. POINT: 9 hits, 5 misses, 4 mixed-output unknowns;
  all six late frames unsuccessful. Fresh BOX: 1 hit, 7 misses, 10 unknowns under
  strict completeness. All first-box prefixes reproduce historical boxes, exposing
  old acceptance of incomplete generation. No live adapter promoted.
- **Implementation failure:** grounding attempt 01 failed during model metadata
  JSON serialization before any generation. Preserved failure; localized dtype
  serialization fix; clean separate attempt 02. No inference retry hidden.
- **Inspection:** independent raw/token evaluators plus RGB overlays, including
  two clear wrong-handle late points. Distinguish small boundary misses, wrong
  entity, mixed output and truncation.
- **Artifacts:** [iteration 002 findings](../evidence/autonomous_research/iteration_002.md)
  and linked hashed summaries; raw records under `runs/autonomous-research/`.
- **Interpretation:** correct subgoal text alone is not sufficient evidence for
  strong motor ranking; better geometric accuracy alone does not solve semantic
  target identity. A high-level planner is still an untested contribution.
- **Next experiment:** frozen current-motor evidence through the already available
  Qwen provider, ten calls. Separate provider evidence use from absence of task
  decomposition, with provider/wrapper confounds explicit. Parallel read-only
  audit of cached vision capabilities and a decisive target-identity test.

### Iteration 003 — current-provider control

- **Question:** Can the existing Qwen provider use unchanged current motor evidence
  more effectively than Laya, before introducing high-level planning?
- **Hypotheses:** provider-specific limitation; shared evidence/interface problem;
  transport mismatch preventing interpretation.
- **Controls:** same five registered fixtures and native order; frozen existing
  Qwen checkpoint/settings/chat wrapper; complete separate preflight. Code
  `2a42bcf`, clean detached worktree. No simulator execution.
- **Result:** first four outputs valid: `x+10mm`, `z-10mm`, `close`, `close`.
  Fifth output literal `17` at boundary 87 is invalid and stops the run. Ten
  planned, five observed, four valid, one invalid, five unattempted. No retries.
- **Evidence:** all five complete prompts, actual forward IDs, generated IDs,
  full-vocabulary logits and EOS independently verified. No truncation/budget
  problem. Repeatability remains untested because repeats were never reached.
- **Interpretation:** poor immediate-effect choices at 9/10 precede the format
  failure: `close` predicts 1.748/0.05684 mm versus 34.177/31.888 mm for `y-40mm`.
  A simple provider swap did not repair this interface. Action-name priors versus
  numerical comparison and long-table competition remain unresolved.
- **Artifacts:** `runs/autonomous-research/current-motor-provider-control-01/`;
  raw records, report, independent audit/script/interpretation. Preflight has its
  own `current-motor-provider-preflight-01/` directory.
- **Regression:** frozen code suite: 585 passed, 5 skipped. Shared runtime unchanged.
- **Next decision:** prefer an architecture-level discriminator to a prompt sweep:
  existing deterministic nominal-distance selection versus Laya on the same
  sensor-derived coarse-approach inputs. Evaluate sensor ranking separately from
  oracle geometric utility and actual execution.

### Parallel iteration 003 — registered visual target verifier

- **Question:** Does full-RGB reasoning contribute useful target identity before
  attempting high-level planning?
- **Evidence motivating it:** two clear lower-handle POINT errors, three separate
  near-boundary misses, four structurally invalid mixed outputs.
- **Prospective model choice:** one `Qwen/Qwen2.5-VL-3B-Instruct`, revision
  `66285546d2b821cf421d4f5eb2576359d3770cd3`. No generic VLM was cached; download
  only this checkpoint. No paid endpoint, model tournament or runtime integration.
- **Protocol:** 14 structurally valid POINT proposals, full RGB with a fixed hollow
  crosshair at the sensor-produced point, four fixed classification labels, two
  repeats. Four mixed outputs excluded explicitly before inference. No oracle
  masks/depth/contact/phase evidence in the generator. See
  [protocol](visual_target_verification_protocol.md).
- **Evaluation:** coarse visible-identity labels frozen before inference and
  reviewed independently; exact rendered-mask membership remains separate.
  Rejection alone is not success: report correct-target retention and coverage.
- **Result:** 28 complete calls; all `target_handle`, 12/12 intended proposals
  retained but 0/2 wrong handles rejected per repeat. Independent full-image,
  actual forward token/image, logits/EOS and checkpoint audits pass. Repeats exact.
- **Environment failure:** preflight 01 in the text-model environment lacked
  Torchvision; preserved before any inference. Existing vision environment passed
  preflight 02 without model/prompt changes or dependency installation.
- **Next:** one image-only marker-location control before any verifier integration.

### Iteration 004 — marker sensitivity and motor family admission

- **Visual hypothesis:** constant target labels could reflect fine handle-identity
  difficulty or a broader marker-binding failure in this interface.
- **Intervention:** four fixed frames, original marker versus marker on clear
  tabletop at algebraic pixel (192,288); no wording/model/settings changes.
  Eight inputs, two repeats, 16 calls, code `14a05fc`.
- **Visual result:** all 16 `target_handle`; tabletop 0/8 correct. Actual changed
  images reach the model and change logits in all matched pairs; original logits
  reproduce the primary run. This fails categorical marker binding, not proof of
  ignoring images. Independent audit passes. Stop marker/prompt tuning here.
- **Motor hypothesis:** Laya might need explicit objective-family admission beyond
  a correct local instruction and supplied geometric effects.
- **Natural-pool result:** six sensory states, ten natural options, twelve calls
  all GRASP despite preserving-gripper/translation instruction. Token/input/gate/
  checkpoint/temperature/raw audits pass, exact repeats. Code `ac4385a`.
- **Family intervention:** remove only GRASP and rotations, retain all six
  translations plus STOP, unchanged remaining text/effects/history. Code `c70b882`,
  twelve calls. Choices BACK,FWD,FWD,FWD,FWD,BACK, exactly repeated.
- **Motor interpretation:** four nominal improvements and two regressions; two
  sensor-optimal choices. Objective-family admission improves compliance but is
  insufficient for reliable direction selection. At two biased sensory states,
  FWD improves oracle nominal distance more than sensor-optimal DOWN. Do not treat
  arithmetic agreement as physical truth or unknown GRASP effects as zero motion.
- **Artifacts:** [audited findings](../evidence/autonomous_research/visual_and_approach_findings.md),
  `visual-marker-control-run-01`, `approach-selector-run-01`, `approach-family-run-01`,
  each under `runs/autonomous-research/` with independent audit scripts/reports.
- **Next decision:** no more model/prompt/menu variants on these fixtures. Test
  whether deterministic fresh-point approach physically outperforms active hold.

### Iteration 005 — declared coarse physical diagnostic

- **Question:** Can an honest fresh visual point plus existing geometric arithmetic
  produce real approach progress, separating perception from model motor ranking?
- **Abstraction audit:** unknown POINT covariance is rejected by current fusion/
  candidate gates. A small projection covariance cannot represent wrong-entity
  uncertainty, and must not be invented to produce motion. Current missing semantic
  evidence is also displayed as confidence zero rather than unknown correctness.
- **Decision:** explicitly opt in to a direct fresh-measurement admission contract,
  bypassing probabilistic fusion while retaining covariance/velocity/semantic
  confidence/contact/holding unknown. This is a bounded experiment, not silent
  relaxation of the old gate or proof of a generic temporal runtime.
- **Protocol:** strict completed POINT, finite containing-pixel depth, full RGB-D,
  seven native actions, existing nominal rule and AtomicExecutor; fresh rule and
  active-hold processes, task/init0/seed1, at most 20 primitives and 900 seconds.
  All-robot oracle contact supervision may abort after an atomic primitive, never
  correct perception or select actions. Compare actual cumulative controls/time,
  reported-point progress and independent handle progress; replay actual controls.
- **Result:** both fresh arms finish 20 actions / 160 controls. The rule reduces
  TCP/handle-center distance 227.258→88.945 mm; hold ends at 227.272 mm. Advantage
  138.327 mm at equal controls/time. No contact or drawer motion. Both full replays
  have zero state error. Post-run ray audits find 21/21 handle points per arm.
- **Alternative explanation:** all rule choices remain unchanged when recomputed
  using only the initial point. This static target/camera slice does not show a
  contribution from repeated visual updates. No learned motor skill claim.
- **Next decision:** separately register one fresh 40-action boundary experiment
  with identical policy/execution and aborts; do not resume archived controls.
  See [protocol](coarse_point_probe_protocol.md).

### Iteration 006 — first semantic failure in fresh extended boundary probe

- **Question:** does the same fresh-point admission remain useful as the robot
  approaches the interaction regime, before any contact or new control policy?
- **Controlled variables:** same task/init0/seed1, model/query, strict parser,
  native executor, unknown fields and oracle external contact supervision. Only
  separately declared action ceiling is 40. Fresh reset; frozen code `b72fcdc`.
- **Result:** exact first-20-action/160-control prefix. After 25 actions, boundary
  25 stops on malformed/no-EOS output (258 tokens). All 200 controls replay at
  zero error, zero contacts. No drawer movement or task success.
- **First divergence:** boundary 21 has a completed valid-format POINT 74 pixels /
  154.331 mm away from the previous handle point. Independent visual and ray
  evaluation locate it on drawer interior. Four RIGHT actions follow; true
  handle-center distance improves but nearest gripper/handle gap worsens.
- **Interpretation:** valid syntax, recent measurement and positive scalar
  progress do not imply correct semantic referent. Complete occlusion is ruled
  out: the target patch remains byte-identical. No evidence that this caused the
  later malformed generation. Physical executor is not the observed failure.
- **Artifacts:** [findings](../evidence/autonomous_research/coarse_physical_findings.md),
  `coarse-point-boundary-01/`, `coarse-point-boundary-grounding-audit-01.json`,
  `coarse-point-temporal-inspection-01/` under `runs/autonomous-research/`.
- **Next experiments:** same RGB in fresh model processes with changed call order;
  fixed RGB temporal correspondence against frozen-pixel translation/occlusion
  controls. These diagnose before any new live policy or recovery is introduced.

### Iteration 007 — frozen-image process control and correspondence falsifiers

- **Hypotheses:** failure may depend on accumulated inference state versus current
  image; apparent tracking success may be stale coordinates versus fresh visual
  correspondence. These are separate questions, with separate interventions.
- **Process intervention:** exact RGB20/21/25, two fresh processes in orders
  [21,20,25] and [25,20,21], six calls total, frozen `ff4a57d`. All native inputs
  match archive, all six outputs and tokens reproduce, including both failures
  cold. Preceding history is unnecessary for either observed failure.
- **Correspondence intervention:** frozen `3411404`, RGB-only default LK versus
  frozen pixels; static, three integer shifts, target/off-target occlusion,
  occlusion+distractor, wrong seed. All 208 rows retained and independently
  reproduced. Maximum shifted visible error 0.001167 px versus 8/8/11.314 px.
  Both target occlusions stop immediately on reverse native-status failure while
  forward status remains successful. No probability/identity or live-policy claim.
- **Instrumentation qualification:** original trace omits attempted reverse
  coordinates. Independent CPU replay stores them separately; `a20c660` adds
  future raw recording plus test without changing propagation. No old overwrite.
- **Interpretation/confidence:** high within these exact fixtures. Image-specific
  regrounding failure and useful RGB correspondence are supported; automatic
  identity recovery, moving-camera transfer and manipulation remain unestablished.
- **Alternative explanations:** LK can track wrong initial referents; surrounding
  context may persist during local occlusion. One-shift sequences are not many
  independent motion tests. No more threshold/prompt/tracker tuning on this scene.
- **Next decision:** cheap direct test of VLM high-level visual proposals versus
  the identical task-text prior, using six visually reviewed archived Task-2
  camera images and one text-only call. Labels frozen before inference; ambiguous
  holding/placement/closing readiness stays uncertain. No execution authority.
- **Artifacts:** [findings](../evidence/autonomous_research/point_failure_controls.md)
  and summary JSON; raw `point-replay-*` and `point-temporal-probe-01` directories.

### Iteration 008 — direct visual subgoal proposal test

- **Question:** does the same VLM provide useful high-level visual information
  beyond task text, independent of earlier marker-verification failure?
- **Intervention:** one task-only and six full-camera image calls, same instruction,
  native model/settings; no history, effects, candidates or simulator variables.
  Frozen code `3d64d7c`, evaluator hash `0daf94ea…243237` before inference.
- **Annotation decision before inference:** only images 0/1/2 (approach, near-grasp,
  suspended bottle needing transport) receive set-valued labels. Later placement/
  drawer images remain descriptive, because provisional subgoal choices do not
  certify hidden fit/safety. No hindsight oracle-phase score.
- **Result:** text-only and RGB0–4 all `establish_grasp`; RGB5 `uncertain`.
  Primary useful agreement 1/3 equals the task-only baseline. Seven valid outputs,
  no truncation; consumed pixels/tokens/forward/logits/EOS verified. 728 tests pass.
- **Interpretation:** no useful phase differentiation demonstrated in this fixed
  interface on the scored development images. Not a claim of image blindness,
  general planning inability or impossibility of a semantic-worldview interface.
- **Alternative causes/next experiments:** independently test visible relationship
  reading versus task-prior interference; Laya use of a correct supplied coherent
  situation versus sparse framing; and realistic retention observability versus
  privileged contact identity. Isolated worktrees/GPU assignments permit direct
  parallel execution without serializing all jobs through root.
- **Artifacts:** [findings](../evidence/autonomous_research/visual_subgoal_findings.md),
  summary JSON and raw `visual-subgoal-*` directories. Original traces unchanged.

### Parallel iteration 009 — can Laya use a supplied coherent situation?

- **Question:** does target/phase/intent/relation context connect existing numeric
  outcomes into useful motor choices when the situation is supplied correctly?
- **Fixed intervention:** one phase-specific 73–77-token prefix to existing
  privileged motor states 0/1/9/10. All original bytes remain the suffix; candidates,
  order, questions, effects, model and settings unchanged. Two reversed repeats,
  16 calls. Registered `d12c4e6`, results `e228389`, integrated `105f7b3`/`89f06a1`.
- **Result:** all choices change. Approach x+40 becomes rotate_x+10 (gap gains
  29.114→4.128 and 15.698→7.282 mm). Advance open becomes close, retaining roughly
  1.75/0.056-mm closure despite admitted 34.177/31.888-mm alternatives. All calls
  valid and exactly repeated; all eight baseline logits match archive. Actual
  consumed sequences fit, including the longest 996/1,024 tokens.
- **Interpretation:** the particular correct supplied packet is insufficient.
  Sensitivity to context is not competent use; immediate-effect comparisons do
  not establish counterfactual full-task or intended-contact outcomes.
- **Confound/next:** original bare open/close IDs imply but do not explicitly name
  the commanded gripper. One separately registered actuator-binding intervention
  can distinguish this concrete semantic ambiguity without further worldview
  wording search. Numeric/rotation semantics and every candidate remain intact.
- **Artifacts:** [findings](../evidence/autonomous_research/worldview_sufficiency_findings.md),
  exact-input/output summary, `worldview-sufficiency-{preflight,run}-01`.
  Integrated focused tests: 22 passed. Generic runtime unchanged.

### Parallel iteration 010 — explicit action definitions

- **Question:** do canonical actuator meanings repair choices when bare action IDs
  remain a concrete confound in the situation-prefix experiment?
- **Intervention/controls:** exact supplied definitions before original states
  0/1/9/10; same model, questions, options/order, effects and original state suffix.
  Frozen `3bde95c`, 16 calls with reversed repeats; results `03387f1`.
- **Result:** both approach choices change x+40 to rotate_x+10, reducing predicted
  gap gains. Both advance choices remain open with 1.755743/0.056385-mm closure;
  same pools still contain 34.177342/31.888340-mm alternatives. All calls valid,
  all repeats/baseline logits exact; no truncation up to 1,012 tokens.
- **Interpretation/limits:** this one correct definition packet is insufficient.
  Semantic recognition versus ranking after recognition remains unresolved; text
  length/positions change. This is an offline sufficiency intervention, not new
  physical task evidence or general incapacity.
- **Next:** complete the missing W+A interaction with unchanged existing prefixes
  on the three fitting states; record the fourth's input-budget exclusion before
  inference. No more wording variants or source-state tuning.
- **Artifacts:** [findings](../evidence/autonomous_research/action_semantics_binding_findings.md),
  full payload/output summary, `action-binding-{preflight,run}-01`. Main integration
  `618482a`/`8a6420c` preserves original experimental revisions.

### Parallel iteration 011 — does the VLM read the visible relations?

- **Question:** are failed subgoals caused by reading visible scene relations,
  mapping those relations to goals, or task-prior interference?
- **Interventions:** 12 frozen composite-relation calls on original/mirrored frames
  and no-image/gray/task controls (`35ff3f6`); after composition failure, one fixed
  24-call single-field decomposition (`7ff4963`). No hidden grasp/fit labels.
- **Result:** composite 9/12 invalid, remaining outputs do not give coherent scene
  agreement. Single-field 24/24 valid but all horizontal answers aligned, all gap
  and orientation answers uncertain, with no scene/control differentiation. Useful
  scene agreement 2/18 fields, coherent scenes 0/6. Native generation audits pass.
- **Interpretation:** output syntax is not the sole remaining failure. This 3B
  checkpoint/presentation fails simple relations needed by the proposed worldview.
  General architecture conclusions remain unsupported; small model capacity is a
  live competing cause, and the earlier composite task effect is confounded by syntax.
- **Next:** one pinned native 7B same-family checkpoint, exact 24+7 prior calls,
  unchanged prompts/images/labels/settings and explicit processor identity audit.
  Freeze acquisition/configuration before inference, no model tournament.
- **Artifacts:** [findings](../evidence/autonomous_research/vlm_world_understanding_findings.md),
  `vlm-world-*`/`vlm-world-single-*` runs. Main `ee40c65`/`c71d9c5`/`3da53ac`.

### Parallel iteration 012 — observe retention evidence without oracle identity

- **Question:** can realistic robot channels and seeded RGB-D correspondences
  separate lifted-bottle motion from an open-jaw lift control?
- **Protocol:** `2dd31e0`, same fresh init0/seed1, strict-gate primitive prefix0–16,
  close versus native hold at13, identical lifts14–16. Assistant RGB landmarks
  frozen before close; sensor files sealed before evaluator analysis. The source
  actions are privileged and scripted. No sensor-driven policy is claimed.
- **Result:** each arm 136 controls. Body vertical motion 109.810/0 mm, TCP
  114.133/114.320 mm; body on-bottle support 33/33 in both. Cap support fails at
  open-arm14:5 with native flow success and 0.0011765-pixel residual. Table LK fails
  immediately. Wrench norms overlap; no calibrated load/holding classifier.
- **Audit/regression:** both new traces replay all272 controls exactly. Root directly
  inspected trajectory-contact-sheet, first-cap-failure and sensor curves. Images
  agree with close-arm lifted bottle/open-arm stationary bottle; the cap's earliest
  mask exit precedes its later large depth jump. This does not certify whole-patch
  identity loss or infer support solely from apparent co-motion.
- **Corrections:** annotation schema incorrectly says human; append-only erratum
  identifies Codex assistant. Exact annotator model/session remains unverified.
  Independent raw contact audit finds bilateral physical finger contacts during
  the transient loss of bilateral pad relation, not measured dropping.
- **Interpretation/next:** useful descriptive co-motion, unresolved semantic/depth
  support and support separation. Independently audit seals and relations, then
  an explicitly exploratory fixed table-plane probe on these sealed frames. A
  same-closed-command slipping/support comparator still needs mechanical grounds.
- **Artifacts:** [findings](../evidence/autonomous_research/interaction_observability_findings.md),
  paired sensor/evaluator files and new-control replay. Original `c4e4ebe`/`d23ed4d`,
  main integration `33594dd`/`1c01160`/`a4b4d45`. Production runtime unchanged.

Integrated regression at `a4b4d45`: **771 passed** in the existing text environment;
log `runs/autonomous-research/regression-a4b4d45.log`. All newly integrated code
is under experiments/tests with protocols/evidence; no production controller,
executor, candidate gate or task adapter changed in this integration.

### Parallel iteration 013 — independent contact audit and depth support reference

- **Question:** do source/provenance/contact ambiguities weaken the paired sensor
  result, and does failed low-texture LK eliminate an available support reference?
- **Audit:** 30 independent checks pass; 188 sensor hashes, frozen source identities,
  common prefixes and saved replay results verify. Independent LK and 134 admitted
  backprojections reproduce exactly. This audits existing replay rather than
  inventing a second physical replay. Exact annotator-model identity is unrecorded.
- **Intervention:** post-outcome exploratory fixed31×31 table patch on66 sealed
  RGB-D frames; no new physics, reseeding, robust trimming, thresholds or oracle
  inputs. Freeze `f98b10f`, findings `64e3449`, main `b2f91f4`/`8573780`.
- **Result:** patch/calibration bit-identical across frames, TLS RMS0.001284mm;
  table LK min-eigenvalue0.0000492905 is below native0.0001. A depth plane is
  measurable even though the table correspondence failed. Body height18.237→128.046
  versus18.237→18.237mm, not object-bottom clearance or general support separation.
- **Correction:** bilateral physical finger contact persists through the pad-relation
  flicker; there is no mechanically earned slipping negative control in this trace.
- **Next:** reassign agent to the missing fresh-reset initial-point-only physical
  control of coarse approach. Do not invent a slipping condition from pad flicker.
- **Artifacts:** [audit](../evidence/autonomous_research/retention_independent_audit.md),
  portable summary, `retention-audit-01` and `retention-audit-support-plane-01`.

### Parallel iteration 014 — exact joint W+A sufficiency

- **Question:** can correct supplied situation and canonical action meanings help
  only when combined, despite their individual failures?
- **Intervention:** exact W then exact A then original state, fixed0/1/10, six calls
  with reverse repeat. Unchanged options/order/effects/model/settings; verified
  archived B/W/A controls. Freeze `a3d7db4`, evidence `5bd5e59`.
- **Prospective exclusion:** step9 raw1,085 tokens exceeds limit1,024; no call or
  compression. Included raw totals538/572/814. All six calls complete, exact repeats.
- **Result:** choices equal W: rotate_x+10 at0/1 and close at10. Gap gains4.128/7.282mm
  versus baseline29.114/15.698; advance closure0.056837mm versus admitted31.888340mm.
  No complementarity rescue on this one advance state; no claim of general failure.
- **Independent root audit:** manual tokenizer composition without experiment report
  imports exactly matches all six native hook inputs/markers; raw W/A composition,
  original source/questions/order, argmax, repeated responses and effects verify.
  `joint-interface-independent-audit-01/audit.py` SHA
  `dad8aedc006f6fc83a630b43b5b2a496d3de0dc26277162a37afbb913f734675`.
- **Next:** one native-option progress-field duplication test with unchanged full
  baseline state. Code inspection shows full-row relocation clips16/25-candidate
  option fields under the256-token head cap, although total input may appear short.
  The planned test isolates a presentation package, not pure binding; no more
  situation/action-prefix variants or full physical task execution are earned.
- **Artifacts:** [findings](../evidence/autonomous_research/joint_interface_sufficiency_findings.md),
  full exact payload/response summary and `joint-interface-{preflight,run}-01`.
  Main integration `19c11f6`/`f0976f7`.

### Parallel iteration 015 — native option progress-value sufficiency

- **Question:** does directly associating an option with its already supplied
  progress value help when contextual prefixes fail?
- **Fixed intervention:** criterion becomes `gap_reduction_mm=<printed value>`
  for approach or `closure_mm=<printed value>` for advance; original full state,
  questions otherwise, action identities/order, predictions and settings stay fixed.
  Six calls on0/1/10 plus reversed traversal. Proposal `4976a61`, freeze `37f9425`.
- **Prospective capacity check:** totals442/476/781 fit. Step9 excluded: full1,134
  tokens, native option clipping despite1,022 effective total. No call, top-k,
  merged candidate, moved number, changed configuration or truncated treatment.
- **Result:** rotate_z+10, rotate_x+10, open. Gap gains6.752232/7.282016 versus
  baseline29.114186/15.697692; advance remains0.056385 versus31.888340mm available.
  All six valid calls repeat probabilities/logits exactly, no runtime failure.
- **Independent audit:** manually reconstructed full tokens/markers match six
  native forwards; original state/source preserved, every criterion exactly copies
  the original displayed column string. Script SHA
  `4d39b13aa0487d5c0a691a1b2bb79464ebb0d19520955737f773688e4828a726`, raw run SHA
  `4593d0567b6ad450505a8c0f969f7f9500850ccccc71dbc851c954f6361ef650`.
- **Interpretation/limits:** this duplication/placement package is insufficient.
  It does not uniquely test binding or prove ranking failure after understanding;
  only one advance state fits. No model-selected action was physically executed.
- **Next decision:** close this local wording/criterion line. Reassign agent to
  sensor visibility at the initial-point physical run's first nonhandle contact.
  Do not build the proposed hierarchy around an unvalidated motor selector.
- **Artifacts:** [findings](../evidence/autonomous_research/native_option_progress_sufficiency_findings.md),
  complete summary, `native-option-progress-{preflight,run,independent-audit}-01`.
  Main integration `40714a5`/`5298e25`/`48bd62c`; seven focused tests pass.

### Parallel iteration 016 — one initial visual point reaches the next physical boundary

- **Question:** does a simpler fixed initial sensor target with live proprioception
  pass the first semantic failure of repeated grounding, and what then fails first?
- **Intervention:** one completed POINT, then fixed observed world position; all
  later RGB-D recorded but unconsumed for target updates. Same nominal7-option
  rule, controller/executor, init0/seed1,40-action/900s ceiling and1N external
  contact abort. Explicit stale-target admission, unknown current visibility and
  confidence; default probabilistic/freshness gates are not asserted to work.
- **Freeze/setup:** `f8b1bf1`; zero-world EGL device setup failure preserved as01.
  Correction `30f49f4` precedes the first physical attempt02, GPU4 model+render.
  No physical/model outcome-based retry or archived-control warm start.
- **Causal comparison:**21 actions/168 controls and22 RGB-D captures identical.
  At shared boundary21, initial target selectsFWD versus fresh wrong-pointRIGHT;
  independent selector arithmetic recovers both. Earlier point metrics can differ
  while actions/states remain identical, and are not falsely forced equal.
- **First boundary:** action25/control0 finger body contacts nonhandle front-panel
  g11 at4.839181N. No earlier contact; no pad/handle contact or executor violation.
  Abort after native8controls,26primitives/208controls total. Drawer closes6.844671mm,
  with25.242mm gripper/handle gap remaining. Official successfalse.
- **Integrity:**761 offline checks; full208-control replay417 states exact0.
  Initial native model input/output matches archive. Target age reaches10s; camera
  and drawer are static before contact. Agent and root inspect actual trajectory
  frames. Root sheet: `coarse-initial-point-02/root-visual-review/first-contact.png`.
- **Interpretation:** correct initial semantic target and a nominal distance rule
  suffice to cross regrounding failure, but not to establish intended interaction.
  Incidental nonhandle closure also occurs without Laya. No temporal-perception
  benefit, moving-target competence or oracle-free safety claim.
- **Next:** separate evaluator-side precontact visibility analysis from a robot-only
  FK observability/leakage probe. Do not add a controller/filter/recovery before
  establishing which geometric facts the available sensors can supply.
- **Artifacts:** [findings](../evidence/autonomous_research/coarse_initial_point_findings.md),
  portable summary and `coarse-initial-point-02` full evidence. Original `3abb312`,
  main integration `e2e8016`/`5b6db93`/`6c787f3`.

Integrated regression at `6c787f3`: **784 passed**, log
`runs/autonomous-research/regression-initial-point-integration.log`. The initial
target schedule is an explicitly experimental grounding hook; default fresh
behavior and production controller/executor remain unchanged.

Independent red-team review adds a competing explanation: visible geometry and
known robot shape do not guarantee that the fixed-orientation seven-action pool
contains a useful continuation. A separate evaluator-only seven-candidate witness
at the exact precontact state is therefore assigned in parallel. It must preserve
the original primitives/executor, use explicit diagnostic prefix replay, record
every arm and raw contact/effect outcome, and infer neither global impossibility
from a one-step failure nor deployable safety from one successful alternative.

### Parallel iteration 017 — first-contact region visibility

- **Question:** was the impending nonhandle contact wholly hidden from available
  preaction RGB-D, or does a scalar target point discard relevant visible support?
- **Registered audit:** preaction25 primary,24 temporal reference; carried oracle
  contact/box-surface query, exact and pixel-center rays, fixed1×1/5×5/11×11
  windows. Freeze `ff061ca` after protocol `2de5c5c`/`dea4f97`. No model or
  recorded-boundary task action; standard evaluator bootstrap settling is explicit.
- **Result:** query pixel147,166 gives scene visual mesh g10, not a robot first hit;
  best fixed5×5 raw depth sample lies1.655333mm from the retrospective query.
  Scene/robot ray counts change25/0→19/6 in5×5 and107/14→91/30 in11×11. Nearby
  cabinet support is available while local robot occlusion grows.
- **Uncertainty:** first contact moves drawer0.047615mm; cached versus fresh-FK
  midpoint differs0.023992mm. Face-distance difference0.001647mm at the box edge
  is smaller than that timing discrepancy, so exact contacted face/normal is not
  identified. Visual mesh and collision box differ; ray/raster edge residuals can
  reach98.95mm. No per-pixel semantic truth or full free-space certificate.
- **Render check:** global replayed renders differ; query and nearest-support
  pixels match original RGB/depth exactly, with local5×5 depth difference at most
 0.034571mm. Preserve the global discrepancies instead of substituting fresh FK.
- **Independent verification:** raw-only backprojection reproduces294 registered
  samples to4.44e-16m; three geometry tests pass. Root inspected both original
  annotated RGB and depth/occlusion figures. This verifies arithmetic, not a new
  sensor estimator or independently repeated ray labeling.
- **Next:** a separate own-joint-only FK probe and seven-candidate physical witness
  address robot shape availability and actionable continuation. Reassign completed
  visibility agent to independent provenance/confound review of those producers.
- **Artifacts:** [findings](../evidence/autonomous_research/first_contact_observability_findings.md),
  complete summary, `first-contact-observability-01` and its read-only report.
  Main integration `34f5bcb` through `3670f83`. Production runtime unchanged.

### Parallel iteration 018 — calibrated own-body geometry

- **Question:** can relevant robot geometry be supplied without current object or
  contact state? This separates own-body observability from scene perception.
- **Frozen intervention:** robot-only calibration plus nine own-joint values,
  isolated NumPy FK process; four archived states, eight nonrobot poison variants,
  two synthetic own-joint controls. Original freeze `ad9a826`; numerical producer
  `554d2e7`. Static constructor uses one nonintegrating half-step with exact
  time/qpos/qvel preservation; two precomparison setup failures are retained.
- **Results:**21 body poses,2 sites,5 gripper proxy extents match same-qpos model
  kinematics within1.11e-15m spatial and3.66e-15 rotation elements. All poison
  estimates are float64-bit identical. Positive own-joint changes alter geometry.
  Nine synthetic/dependency tests pass; root reruns366 report checks.
- **Interpretation:** own geometry is available conditional on robot calibration.
  This does not validate physical installation calibration, historical cache timing,
  complete robot collision geometry, surrounding scene extent or action safety.
- **Next:** frozen read-only depth/proxy proximity with explicitly partial gripper
  masking. No policy filter, collision threshold, simulator scene geometry input,
  or runtime branch is introduced.
- **Artifacts:** [findings](../evidence/autonomous_research/robot_geometry_observability_findings.md),
  portable summary/figure; `robot-geometry-observability-03`, preserved01/02 setup
  failures, `robot-geometry-root-report-01`. Main integration `3f14603` through
  `eef21f3`; standalone estimator and reporter remain experimental.

### Parallel iteration 019 — exact-input stronger VLM control

- **Question:** does one larger same-family checkpoint repair the observed visual
  relation and semantic subgoal failures under the existing interface?
- **Competing hypotheses:** limited3B capability versus a limitation also present
  for7B under the fixed imagery/questions; no claim to isolate every confound.
- **Frozen intervention:** `Qwen/Qwen2.5-VL-7B-Instruct`, provider revision
  `cc594898137f460bfe9f0759e9844b3ce807cfb5`, source `ce698e6`; unchanged24 relation
  and7 subgoal calls, labels/order/images/prompts, BF16/SDPA/greedy32/seed1.
  Provider weight hashes verified before generation. Download-only transport
  failures/resumptions preserved separately from model inference.
- **Results:**31 valid completed answers, zero cap hits/truncation/retries;
  source messages/tokens/masks/grids and FP32/BF16 image identities all equal3B.
  Relation usefulness9/18 versus2/18, coherent scenes0/6 for both. Horizontal
  always left on scenes including mirrors; gap always separated including absent
  images. Primary subgoal agreement0/3, matching own text-only0/3;3B was1/3.
  Three later subgoal images remain descriptive and unscored.
- **Independent root audit:** no producer scorer imports; reconstructs all31
  native sequence/forward/cache/argmax/EOS checks and same paired inputs from raw
  records/logits. Inspected actual relation images0/4: no image-orientation or
  absent-scene error explains those example failures.
- **Interpretation:**7B gives some image-sensitive answers, but individual score
  gain includes constant-label priors; no coherent worldview/subgoal repair.
  This is not universal VLM incapacity, failure of all hierarchies, or evidence
  that larger capacity generally hurts. No controller/model is deployed.
- **Next decision:** close this checkpoint-control line without a model/prompt
  tournament. Reassign its agent to the independently identified within-control
  physical observability question after completing the seven-action report.
- **Artifacts:** `vlm7b-capability-{relations,subgoals}-run-01`; root independent
  script/summary `vlm7b-root-independent-audit-01`. Raw SHA-256 respectively
  `50603ec41159cca96f3e55549a5203c00641718849e217a3abb4f538712fea89`
  and `a4d29b33d9c4e36213e76bceaa31550b2e93a5e91f965f60d05f9c46371c6b5c`.

### Parallel iteration 020 — every original native option at boundary25

- **Question:** does the original seven-option family contain a useful native
  one-step alternative at the first nonhandle-contact boundary, independently of
  target/perception/model selection? A positive answer would constrain a pure
  action-coverage explanation; a negative answer is only local.
- **Frozen intervention:** seven canonical options, each after exact archived
  200-control prefix from its own reset. Same initial POINT, native10mm/eight
  controls, open gripper, executor and validator. Explicit evaluator-only prefix
  diagnostic, not a fresh autonomous policy. Freeze `812d99e`; preflight import
  failure preserved before worlds/controls, corrected `e13bc36` precedes first
  physical attempt. No actual-outcome retry, selection or threshold changes.
- **Result:** all7 arms/56 new controls complete. No contract-valid option both
  reduces designated-handle surface gap and has zero sampled robot-contact rows.
  DOWN gives8.466454mm gap gain but2.114787mm translation residual (>2mm), and
  drawer motion1.406205mm despite no control-end contacts. RIGHT reproduces the
  archived8 commands/states/contacts/full result exactly and moves drawer6.844671mm
  through sampled nonhandle contact. FWD improves point distance4.143665mm while
  worsening handle gap0.036381mm. No arm has designated-handle contact or success.
- **Independent review:** all2,971 record-chain identities,1,400 prefix and56 arm
  controls,21 artifacts/trajectories, metric/contract arithmetic pass an independent
  stdlib/NumPy checker. Root reran it and inspected the seven endpoint RGB images
  (`coarse-native-counterfactual-run-01/root-visual-review/seven-arm-endpoints.jpg`).
- **Interpretation:** scene visibility and known own shape do not prove a useful
  action exists under this local regime. Contact-end sampling may hide within-step
  interaction. No global reachability, continuous-time safety or model competence
  claim follows; no causal attribution of tracking error yet.
- **Next experiment:** independently reviewed paired RIGHT/DOWN integration-step
  observer, no dynamics modifications, exact original per-control/result guard.
  Concurrent partial-mask RGB-D proximity remains a measurement-only question.
- **Artifacts:** [seven-option findings](../evidence/autonomous_research/coarse_native_counterfactual_findings.md),
  [independent review](../evidence/autonomous_research/information_boundary_review.md),
  `coarse-native-counterfactual-run-01`; SHA
  `23a5e0ea9a59317ad843141a4ec0017958d0c180fdbc7c2aed90cf41697943fa`.
  Main integrations `54ee10b`, `e1dc0a8`, `6ac3d18`, `0755742`, `d5ed5ab`.

Integrated regression after geometry/VLM/counterfactual integration: **805 passed**
in30.65s; log `runs/autonomous-research/regression-geometry-vlm-counterfactual-integration.log`.
Tested code at `0755742`; subsequent `d5ed5ab` is only a report-path correction.
The root raw audit and integrated independent boundary checker also pass.
Production `runtime_core.py` and `adapters/libero.py` remain byte-identical to the
experimental starting commit `b73b5b4`.

### Parallel iteration 021 — sensor-only observed-point proximity

- **Question:** can sealed raw depth and known own geometry support a useful
  proximity measurement, or does the robot's own appearance dominate it?
- **Frozen comparison:** all finite-positive depth versus outside the projected
  five collision-proxy silhouettes, at two registered development boundaries24/25.
  Same calibrated camera/robot and own-joint packets; no target, scene geometry,
  contact, force, candidate or outcome input to the standalone numerical worker.
  RGB is opened for interpretation only after numerical outputs are sealed.
  Producer `f20476d`; first run01 completes without a revised measurement.
- **Results:** every all-point proxy minimum is0. Masks exclude6,169/6,265 pixels;
  residual union minima0.126722/0.109195mm remain on apparent housing edges.
  Finger1/pad1 nearest pixels are visually mixed/ambiguous, so their declining
  distance cannot be called environmental clearance or an imminent-contact label.
  Root inspected both full RGB/depth overlays and fixed17×17 witness patches.
- **Independent evidence:** 15 analytic/FK tests and333 reporting checks pass.
  Separate checker verifies11 artifacts/seals, raw sensor arrays/own packets,
  all stored-map summaries and24 witness backprojections/distances without FK,
  hull or mask recomputation. Root reruns that checker and15 focused tests.
- **Interpretation:** a sensor-only numerical measurement is available, but its
  minimum lacks the surface identity needed for a scene-proximity claim. The
  visible housing extends beyond the collision silhouette; exact cause may also
  include raster/cache/calibration effects. Omitted arm links are not established
  as the dominant nearest witnesses. No safe gate or policy is earned.
- **Next experiment:** known gripper visual silhouettes versus existing collision
  silhouettes, exact same depth/qpos and stored distance maps; no margin tuning,
  extra arm export, dynamic rendering or action selection. Independently review
  static robot ownership and projection before measurement.
- **Artifacts:** [findings](../evidence/autonomous_research/sensor_gripper_proximity_findings.md),
  summary/overlays/witnesses and independent review; `sensor-gripper-proximity-01`.
  Input/output artifact manifest SHA
  `56dcb32aca328d3a2e09af393d310f5abd44af3b62b206034e9f0830af86da49`.
  Main integration `ce7e550`, `bc2cb3b`, `51f0893`.

### Parallel iteration 022 — contact aliasing at native integration boundaries

- **Question:** did coarse contact sampling miss interaction during DOWN's drawer
  movement, or is another source needed to explain the apparent contact-free arm?
- **Frozen paired diagnostic:** RIGHT then DOWN, each fresh reset plus exact200
  archived prefix controls. Pass-through wrappers observe native Euler2ms calls
  before/after without added forward, integration, cache update or controller
  changes. Same original8 controls/action and2mm motion tolerance. Freeze `ef5a4e0`,
  independent pre-execution review; preflight01/run01 complete without retries.
- **Results:** commands, all400 prefix/16 native control states, returned fields,
  endpoint contacts and both full executor results exactly reproduce the reference.
  RIGHT has contacts in112/200 native integrations, peak6.912957N; DOWN7/200,
  peak14.913734N, all finger-body/nonhandle front-panel contacts. DOWN's8 original
  control-end samples remain empty. First contact and first direct drawer motion
  occur in the same native interval,10.590–10.592s for DOWN; prior drawer velocity0.
  All applied generalized/Cartesian forces are0. Drawer movement and failed
  translation residual remain unchanged.
- **Interpretation:** contact aliasing is demonstrated. The14 DOWN before/after
  contact rows bracket7 native calls; forces change during the solve, and these
  are not14 independent impacts or literal duplicate rows. Cached geometry may
  lag qpos. This is contact-associated motion, not isolated sole-cause evidence
  for the controller's tracking residual or continuous-time impulse attribution.
- **Independent verification:** 2,451 record hashes,400 native integrations/800
  snapshots, all source/reference chains, membership/force/address/chronology
  arithmetic and6 RGB-D/trajectory artifacts pass. Root reruns independent checker
  and views actual contact/drawer chronology plot; native execution is unchanged.
- **Regression correction:** integration initially fails one test because it asks
  the expanded main checkout to equal an older frozen whole scientific source.
  The experiment guard correctly refuses that. Main-only test change `0c4cdc2`
  verifies the guard with a synthetic source mutation and separately checks local
  archive identity; all8 focused tests then pass. Frozen producer/guard unchanged;
  this is not a physical experiment failure or outcome retry.
- **Next:** one canonical122-primitive/970-control Task1 observational replay with
  native-substep attribution, exact all archived boundaries and official success.
  Retain historical control-end evidence. Passive wrist sensor buffers may be
  recorded separately before protocol freeze, without entering oracle classes.
- **Artifacts:** [findings](../evidence/autonomous_research/native_substep_observability_findings.md),
  timing figure, compact summary, independent review and
  `native-substep-observability-run-01`. Raw SHA
  `7fce36f5df64da7009d3ddb71b98f01d2383065c13d3b88069af39aed997337a`.
  Main source/report/audit integration `35df10c`, `c10e555`, `cbaed8d`, `b144436`.

### Parallel iteration 023 — known gripper visual geometry replaces the mask

- **Question:** do residual housing-edge minima arise because collision proxy
  silhouettes omit the gripper's known visible geometry?
- **Frozen intervention:** only replace the five collision-mask silhouettes with
  projected convex enclosures of three static gripper-owned visual meshes. Same
  pixel-center convention, no expansion, same two depth/K/T/own-joint packets,
  and all five stored collision-distance arrays byte-identical. Static export
  `ea89ca8` preserves the original full robot chain/collision calibration; one
  nonintegrating constructor half-step, no rendering or dynamics. Measurement
  freeze `9c5e40f`, independent pre-execution review, first run01.
- **Result:** masks add/remove35/13 pixels at24 and13/10 at25. Both old hand
  witnesses disappear, but new hand minima0.278252/0.233802mm remain at apparent
  housing/cable-side edges. At25, a newly admitted pad-edge point has distance0.
  All eight previous finger/pad nearest witnesses remain eligible. Root views
  actual fixed RGB witness patches; these are interpretation, not geom-ID truth.
- **Interpretation:** calibrated visual replacement alone does not establish
  environmental proximity. The masks are not nested; excluding one problematic
  point does not monotonically improve the whole measurement. Pixel footprint,
  render groups, geometry/cache/calibration differences remain competing causes.
  No margin, mask union, policy gate or outcome-driven repair is introduced.
- **Verification:**17 focused tests and334 post-seal report checks pass. Static
  visual calibration SHA `c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98`;
  hand3,613 vertices/7,078 faces, each finger318/624, all opaque. Identity/seals,
  fixed-map selection and previous baseline summaries preserved.
- **Next:** read-only rendering/source diagnosis before any third mask experiment.
  Distinguish actual pixel sampling from ideal center rays and rendered geometry
  inclusion; missing historical settings must remain unknown.
- **Artifacts:** [findings](../evidence/autonomous_research/gripper_visual_mask_findings.md),
  complete summary and RGB/depth/witness figures; `gripper-visual-calibration-01`
  and `gripper-visual-mask-control-01`. Main integration `96c91b9`, `c61c038`,
  `936526a`. Original collision-mask evidence remains unchanged.

Integrated regression at `936526a`: **821 passed** in30.45s; log
`runs/autonomous-research/regression-proximity-native-integration.log`.
Later independent visual-mask checker/report `68bed76` adds no producer change;
root reruns it into `gripper-visual-mask-root-audit-01.json`. It verifies24
witnesses and stored selection arithmetic, without rerunning geometry or physics.

### Parallel iteration 024 — canonical success lacks designated native-stage contact

- **Question:** did historical control-end sampling miss the intended pad/handle
  interaction during the successful drawer trajectory?
- **Frozen experiment:** ONE canonical Task1 source, fresh init0/seed1 reset,
  original970 control arrays, no policy/model/preview or extra control. Producer
  `f6efbcb`, reviewed before run01; raw SHA
  `e8e253cefe4c694c6091e1bf944a8f269cfc47c7ed08c053419d97e1a73615d4`.
  Native observer adds no forward, physics call or cache refresh. Existing wrist
  buffers are recorded separately, without entering contact classes.
- **Observed:** all available control/primitive states and official success match
  exactly.122 primitives,24,250 integrations,48,500 snapshots. Zero raw designated
  pad/handle rows at either stage, including subthreshold/unforced contacts.
  Non-designated contact appears within288 controls versus134 endpoints, adding154
  contact-bearing controls. Net closure remains152.05189674218448mm.
- **Partition:** stages agree on3035 non-designated intervals/55.953266mm net and
  21209 neither-relation intervals/96.074782mm;6 disagreements contribute0.023849mm.
  Historical endpoint134/46.086120mm and836/105.965776mm are reproduced. These
  partitions describe association, not exact causal allocation; neither can
  contain inertia, subthreshold or other contacts. Snapshot stages are not
  independent impacts or continuous-time contact durations.
- **Evidence:** independent raw-only streaming audit passes100,158 records,
  source/command/state identities, sensor metadata, native chronology and all
  partition sums. Root inspects the actual attribution figure and source/report.
  Findings `task1_native_contact_attribution_findings.md`, independent review
  `task1_substep_independent_review.md`. Main integrations `6a9354d`, `a7b10c0`,
  `6e5850a`; historical tags/evidence unchanged.
- **Belief update:** native-stage observation strengthens the interpretation of
  Task1 as goal completion without measured designated interaction. It does not
  establish that the machinery cannot perform intended manipulation.
- **Next:** preregistered OFFLINE wrist endpoint-versus-history comparison using
  sealed sensor inputs and separate gripper/upstream-arm evaluator labels.
  Concurrent bounded renderer diagnosis and existing grasp/action-family inventory
  should identify a defensible next local physical skill experiment. No additional
  hierarchy, wording tournament, threshold change or live safety claim follows.

### Parallel iteration 025 — depth sampling versus cached robot geometry

- **Question:** why do apparent own-gripper pixels remain outside a calibrated
  center-ray silhouette? Competing causes include cache/FK disagreement and actual
  raster sampling rather than ideal pixel-center measurement.
- **Frozen intervention:** producer `5b17822`, after source/protocol `cdd03ae` and
  independent review. Fresh exact original prefix through pre25 only, both native
  RGB/depth/K/T arrays byte-identical and402 recorded state gates pass. At each
  saved boundary, block further physics and compare native4-sample rendering to
  zero-MSAA rendering of the same complete cached data. Invariant render settings,
  poses and integration fingerprints are guarded. Separate own-qpos FK comparison
  cannot alter the rendered scene. No mask, margin or controller changes.
- **Observed:** actual4-sample positions are(.375,.125),(.875,.375),(.125,.625),
  (.625,.875). Sampling alone changes registered witness depth by up to734.777mm;
  pre25 newly admitted pad-zero witness changes by418.181mm. Own-FK versus cached
  projected vertex discrepancies are at most0.00457/0.00488px at24/25, with world
  discrepancies10.93/34.75µm. Root inspected the actual fixed witness panel.
- **Interpretation:** pixel-center ownership is not a justified assumption for
  these resolved edge depths. Small cache differences remain measured, but the
  controlled sampling intervention demonstrates a large separate effect. Exact
  GL depth resolve ownership, real-sensor calibration and scene clearance are not
  established. No mask union/dilation or calibrated safety claim is earned.
- **Verification:**14 tests,239 post-seal reporting checks and independent saved-
  array audit PASS. The auditor verifies recorded402 gates; it does not rerun
  dynamics. Post-seal ignored EGL cleanup exceptions are retained/disclosed, with
  process exit0 and completed seals. Raw `render-measurement-diagnosis-01` and log;
  report `render_measurement_diagnosis_findings.md`, reviewer
  `render_diagnosis_independent_review.md`. Main integrations `59fe990`,`4fe2f33`,
  `6a142e5`,`53710d6`.
- **Next:** minimal calibrated pixel-sample/own-triangle measurement with explicit
  ambiguous ownership, analytic tests first; no resolved-point invention or live
  gate. In parallel, the mechanical inventory earns a local grasp→10mm lift
  transfer test using the unchanged actual visual executor. Setup attempt01
  stopped before world construction on missing LIBERO bootstrap; its log is kept,
  native setup is fixed separately, and no physical outcome was observed.

Maintenance closeout:26 inactive checkouts removed,320.1MiB reclaimed; all exact
HEADs pinned, raw evidence/failures/branches retained. See `workspace_lifecycle.md`.
Integrated regression before renderer additions at `fb7af48`:830 tests passed
in31.84s; log `regression-canonical-attribution-integration.log`.

### Parallel iteration 026 — fixed wrist temporal features add information

- **Question:** can recorded within-control wrist history recover interaction
  information missed by endpoint-only sampling, without oracle inputs to features?
- **Freeze:** `adc7eb4`, independent review before analysis, single existing Task1
  native archive. Seal sensor-only projection then970 fixed feature rows before
  evaluator labels. Force primary, torque secondary. Same first-BEFORE baseline;
  compare norm(final-AFTER minus baseline) with max of25 AFTER differences. No
  calibration, feature fitting, threshold, model, physics or live estimator.
- **Observed:**163 gripper-only positives,641 no-robot-scene>1N negatives;164 arm
  and2 mixed controls separate. Primary force AUROC0.787248→0.987634. In the fixed99
  endpoint-missed gripper controls,0.653918→0.993602. Temporal overlap remains32/163
  positives and14/99 missed positives within the negative observed range. Torque
  improves less cleanly:0.765455→0.932822, with117/163 temporal overlap.
- **Interpretation:** retaining within-control sensor history is informative on
  this trajectory. Temporal score≥endpoint is algebraic; AUROC/overlap, not that
  inequality, support the comparison. Dependent controls, gravity/acceleration,
  rotating axes and cache timing confound causal interpretation. No designated
  pad/handle examples exist in this archive, so no designated-interaction or
  holding detector is validated. There is no deployed threshold.
- **Verification:** frozen6 tests and independent reconstruction of all970 inputs,
  features/cohorts and24,250 gold samples pass. Root inspects empirical distributions.
  Raw `offline-wrist-history-run-01`, journal SHA
  `055ecd9561e4306598f95d178ed785e9c7e2fa561f3279d42358abc09dbf810d`.
  Findings `offline_wrist_history_findings.md`; main `6ffa74a`,`88906f5`,`9facbe6`,
  `d87003f`. No post-result feature variant follows.
- **Next decision:** retain temporal measurement as a candidate evidence channel;
  reassign lane to the distinct target-support gap needed for sensory approach.

### Parallel iteration 027 — local skill passes the actual visual executor

- **Question:** does the existing native40mm bottle-lift witness transfer to the
  actual visual10mm action interface and its unchanged hard validator?
- **Registered comparison:** two fresh Task2 init0/seed1 worlds, original scripted
  native prefix0–12, then GRASP versus open STOP, then one MV_UP each. No model,
  preview, new action, state restore, candidate policy or threshold change. Frozen
  `20d2b1a`/`ef58bf9`, independent review; attempt01 fails before any world on LIBERO
  package bootstrap. Preserve log; native initialization fix `9b85ad5`, reviewed,
  zero-world preflight02, then separately named run02. No physical retry.
- **Observed:** all4 hard contracts pass. Close bottle rise9.279538663mm versus
  open0.001080886mm; TCP rise9.423957/9.484801mm. Closed lift bilateral at8/8 control
  endpoints and200/200 BEFORE plus200/200 AFTER native stages; open0. No unexpected
  robot contact. Actual lift translation errors0.600963/0.542131mm, both under the
  unchanged2mm limit; original hold/rotation tolerances preserved. Official full
  task success false in both arms, as expected for the registered local slice.
- **Verification:**22 focused tests;224 archived comparable controls and28 prefix
  RGB/depth/K/T frames exact. All240 new controls replay exactly at every stored
  state under the same clean source/settings. Independent raw-only audit passes
  2149records, all command/state/contact/validator reductions and replay states.
  Root inspects actual six-frame before/after images. Raw
  `local-grasp-interface-run-02` SHA
  `9347eab2f1b48fe3799ccfbc3164f60406b6451bd194819ef66632df7d6464bb`.
- **Belief update:** the actual visual atomic interface has a qualified local
  contact-maintained lift. The pregrasp approach remains scripted/privileged;
  grasp generality, support-free retention, model decisions and complete Task2
  success remain unproved. Snapshot continuity is not continuous-time proof.
- **Next:** one fixed initial RGB BOX/depth support-contamination experiment,
  with the same center/median-depth point and crop; output sealed before limited
  rendered-mask proxy evaluation. No successful-pose offset fitting or oracle
  foreground cleanup. This targets the missing sensor-derived approach evidence.
- **Integration:** source/report `512d032`,`195c974`,`298300e`,`d7e6844`; prospective
  reviews `636bab3`,`f9687d3`; independent audit `8fc5efb`. Regression at `8fc5efb`:
  **847 passed** in31.97s, log `regression-contact-render-wrist-grasp-integration.log`.
  Generic runtime, Libero adapter and decision interface remain byte-identical to
  `b73b5b4`. Local producer checkout retired immediately after integration;27 total
  inactive checkouts removed,338.7MiB reclaimed, four active checkouts remain.

### Parallel iteration 028 — calibrated sample footprints preserve ambiguity

- **Question:** can an own-geometry representation explain the registered depth
  returns without equating a resolved scalar with pixel-center ownership?
- **Hypotheses:** partial native sample coverage can be missed by the center ray;
  alternatively, cached versus own-qpos geometry explains the selected anomalies.
- **Frozen experiment:** `0733ea7`, native four sample rays plus center, unchanged
  scalar depth, calibrated own-gripper triangles and own joints. No physics or
  rendering. Seal sensor output before separate cached-pose comparison. Attempt01
  fails before output because the old calibration lacks triangle connectivity;
  preserve it. Static own-STL export passes9 exact vertex/pose gates and supplies
  topology; no scene, MjData, joint state or fitted hull. Attempt02 is separate.
- **Observed:** all6 prior large-jump center rays miss modeled gripper while1–2/4
  native samples hit. Four smaller-change witnesses have0/4 support and remain
  unexplained. Own-qpos/cache coverage agrees at all11 centers/99 neighbors. Whole-
  frame disagreement remains7/2 samples; common-hit depth differences reach
  7.10/16.52mm at discontinuities despite subpixel pose agreement.
- **Interpretation:** potential self contribution is measurable; resolved depth
  ownership and environmental clearance remain unknown. Small projected vertex
  differences are not uniform depth bounds. No mask, margin, pixel rejection or
  candidate gate follows. This geometry diagnosis is closed.
- **Verification/artifacts:**25 focused tests,232 report checks, independent17-
  artifact stored-array audit PASS; root reruns checker and inspects witness panel.
  Raw `pixel-sample-footprint-02`, previous failure and topology export retained.
  Main source/report `2b1e8b2`,`602474c`,`fa75625`,`eac39df`; independent result
  `dd5fb11`. See `pixel_sample_footprint_findings.md` and root receipt
  `runs/autonomous-research/pixel-footprint-root-audit-01.json`.
- **Next:** reuse producer worktree for the distinct fresh Task2 point approach;
  no additional automatic renderer/masking variants.

### Parallel iteration 029 — bottle point plausibility versus ROI geometry

- **Question:** does existing semantic grounding supply target-specific bottle
  geometry suitable for moving beyond the scripted local-grasp witness?
- **Competing hypotheses:** a plausible BOX may support a useful coarse point;
  treating its whole interior depth crop as bottle-only geometry may already fail.
- **Frozen experiment:** `ba7ab2e`, one full-RGB LocateAnything query `the wine
  bottle`, same3B checkpoint/settings,256-token cap. Fixed inspected initial Task2
  image; unchanged integer BOX-center ray/crop-median point and every crop sample.
  Seal before archived rendered-mask proxy evaluation. No dynamics, new query,
  oracle cleanup or successful-pose offset. Attempt01 has zero inference: NumPy
  processor metadata fails tensor-only serialization. Separate fixed attempt02
  follows actual-input processor preflight. Both attempts remain recorded.
- **Observed:** one12-token/EOS output gives normalized box[542,408,596,582].492
  valid crop samples;414 agree with the limited bottle-label proxy,373 are proxy-
  interior,65 boundary,54 exterior. Center and both median contributors agree with
  the proxy; point P approximately[-.123715580,.056158890,.985527269]m. Center depth
  differs from median by−7.359mm. Root inspects actual RGB/depth: tabletop is visible
  beside the narrow neck inside the fixed crop.
- **Interpretation:** plausible semantic point, mixed depth support. Exact depth
  ownership, grasp center, jaw span, hidden surface and approach utility remain
  unknown. The representation cannot promote all ROI points to bottle geometry.
  No downstream correction is fitted from this result.
- **Verification/artifacts:**9 tests and independent9-record/all492-pixel audit
  PASS; root reruns checker. Raw `task2-box-support-run-02`, prior setup failure and
  processor preflight preserved. Main final source `22901b1`, report `fd53609`,
  independent audit `27bad9a`; root receipt `task2-box-root-audit-01.json`.
- **Next experiment:** fresh Task2 init0/seed1 approach using exact sealed P, only
  after byte/dtype/shape match of initial RGB/depth/K/T. Live TCP/jaw observations,
  original seven10mm translations/STOP and geometric rule,40 actions/900s, no model
  call or archived controls. Native contacts are passively recorded through each
  complete atomic primitive, followed by stop before another action. Distinguish
  designated pad/bottle boundary from forbidden contacts; no automatic GRASP.
  Independent review and one exact replay planned. Concurrent offline frame audit
  checks the observed site-position/body-quaternion distinction without dynamics.
- **Integration regression:**872 tests pass in31.68s at `b924819`; log
  `regression-box-footprint-integration.log`. Production runtime, adapter and
  decision interface remain byte-identical to baseline. Completed source/reports
  are integrated and the four existing worktrees are reused.

### Parallel iteration 030 — frame accounting without a runtime correction

- **Question:** does the observed site-position/body-quaternion distinction
  actually corrupt current decisions, or only matter for future jaw geometry?
- **Frozen experiment:** `a083645`, static calibration composition and saved240
  local-grasp sensor rows,30 cached endpoints,4 actual executor interventions.
  No dynamics, rendering, new FK, model call, target fitting or action selection.
  Current proprioception/model/effect packets are separately exercised with a
  guarded robot-only observation map and poisoned quaternion.
- **Observed:** unadjusted body versus site rotation≈90°; fixed Rz(−90°) leaves
  median0.003643°/max0.045301° against saved scratch matrices. Saved wrist/TCP
  rotations are identical240/240. Cached endpoint corrected max0.010974°; recorded
  sample times differ or are unknown. All4 original validator rotations reproduce.
  Absolute mount error cancels in same-frame world-relative rotation. A hypothetical
  unadjusted pad projection would shift centers26.03–61.51mm, but actual current
  model/proprio packets omit quaternion and are poison-invariant240/240.
- **Interpretation:** known own-frame structure matters when exposing pad geometry;
  no current mixed-pose failure was found in the inspected path. Omission does not
  prove orientation unnecessary for grasp. Shared synthetic calibration and unknown
  sample timing preclude a real-robot or exact same-time pose validation claim.
- **Verification/artifacts:**4 focused tests pass; root checks9 source hashes and
  all240 corrected angles with an alternate quaternion/angle formula and confirms
  wrist matrix equality. Raw `proprio-frame-consistency-01`; root receipt
  `proprio-frame-root-audit-01.json`. Main source/report `bf98178`,`216863c`; report
  `proprio_frame_consistency_findings.md`. No production change.
- **Next:** use own observations/fixed P only to interpret the first fresh approach
  boundary in jaw coordinates. This cannot supply unseen bottle extent, fit a
  target offset or authorize grasp. Independent trace audit proceeds separately.

### Parallel iteration 031 — fresh bottle point approach reaches palm contact

- **Question:** can the unchanged sensor-derived BOX point guide the existing
  seven-option nominal-distance rule toward a qualified local grasp context?
- **Freeze/control:** `9de837c`, after source `aee75a9`, actual-input no-world
  preflights and independent `cbf132a`. One fresh Task2 init0/seed1 world; initial
  RGB/depth/K/T shape/dtype/bytes match the original source. Explicit reuse of one
  cached inference; no new model calls, historical controls or state restore.
  Fixed P, live own observations, unchanged10mm rule/tie-break/executor/validator;
  open jaws,40-action/900s cap. Passive native contact recording through a complete
  primitive, then stop before another action at a new pair>0.05N. No GRASP/lift.
- **Observed:**25 complete actions/200 controls/5,000 integrations. TCP-to-P drops
  208.367227535→50.951274876mm. All25 execution validations pass; maximum translation
  residual1.27866mm, rotation0.22724°. First threshold crossing is action24/DOWN,
  control0, native BEFORE index3 at10.106s: hand collision mesh75 versus bottle
  geom134,0.081747743N. The previous AFTER has the same recorded time, so this is
  a cached-stage observation, not precise continuous contact onset. No further
  primitive follows; jaws remain open, holding unknown, official success false.
- **Independent correction:** raw hand/bottle rows already begin during action22/
  FWD, control7, BEFORE index186 at9.672s,0.017555969N. Action23 is LEFT, action24
  DOWN. Across these actions249 raw rows per stage; no raw pad, arm, other-scene or
  self rows. Action24 has40 above-threshold rows per stage, peak0.185976166N BEFORE.
  The last raw row is below threshold again. Preserve the difference between first
  raw observation and first threshold crossing; do not change the historical gate.
- **Actual inspection:** root views six RGB stages and raw journal. Initial image
  impression suggested a finger near the cap; raw names identify the palm, and
  that attribution overrides the image impression. The fixed point at threshold
  and terminal packets lies outside finite pad Y/Z spans despite≈79mm facing gap;
  final nearest-pad distance34.300mm. Body-to-site transform is the separately
  checked one; exact native contact pose and bottle extent remain unknown.
- **Competing explanation check:** source-only original successful local-grasp
  preclose prefix consists of13 translations, not rotations. Missing pitch/roll
  alone is therefore not established. That privileged route, step sizes and
  information differ; no successful target coordinates or offset are fitted.
- **Verification:**200-control fresh raw-command replay passes every saved state,
  all10,000 native snapshots and26 complete RGB/depth/K/T captures. Producer
  compares full snapshots/images; reviewer independently checks exported states/
  fingerprints and source code, without reexported replay contact/image arrays.
  Independent raw audit `409e8c2` PASS; root reruns it. Raw run journal SHA
  `f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771`, replay result SHA
  `5c3a02fb731d3d8c120ec6f89327762b942d36ab62716a48552ebfc348faa5f9`.
  Raw directories `task2-box-point-boundary-run-01` and `-replay-01` preserve both.
  Integrated approach/frame suite886 tests passes at `0fb3a44`;3 additional jaw
  tests pass. Production runtime/adapter/decision interface remain unchanged.
- **Belief update:** nominal point progress does not establish a valid approach
  relation. This is a deterministic-policy boundary, not a Laya decision failure,
  executor failure, grasp attempt or proof of global geometric impossibility.
- **Next, parallel:** (A) exploratory retrospective observed-surface measurement
  at pre21/pre22: original inner crop versus full BOX, all five calibrated gripper
  proxies and seven nominal candidate sweeps, no thresholds/gates/labels as input.
  Only executed actions have measured contact outcomes. (B) exactly one fixed
  semantic-region query `the neck of the wine bottle` under the same initial RGB,
  model and BOX/depth extraction, no retries or offsets. This researcher-specified
  region tests semantic target selection, not autonomous planning. Seal outputs
  before evaluation; choose a new physical intervention only after these results.
- **Closeout:** producer findings/figure/table integrated as `1e29772`; independent
  audit as `5ca7bc7`; jaw interpretation as `a81024d`–`583b583`. Root inspected the
  canonical figure, retained all original frames, then removed reconstructible
  caches and the redundant temporary root panel (3.05MiB); receipt in workspace
  lifecycle. Four active worktrees continue to be reused.

### Parallel iteration 032 — one explicit neck description does not yield a point

- **Question:** can explicitly requesting a manipulation-relevant part repair
  object-level grounding, without richer geometry or a new model?
- **Frozen intervention:** one exact `the neck of the wine bottle` description,
  existing BOX template, same original full RGB, checkpoint/BF16/native settings,
  configured256-token cap and unchanged extraction if admitted. This is a
  researcher-specified semantic condition, not an autonomous planner proposal.
  Freeze `f1cae7c`; preserve previous object-level result. Zero-call processor01
  fails on wrong existing interpreter; separately numbered02 uses the pinned
  LocateAnything environment. GPU0 becomes occupied by an unrelated workload;
  explicit resource-only amendment uses identical-type GPU1, default core GPU0
  unchanged. CPU preflight03 repeats240 IDs/schema exactly under final identity.
- **Observed:** one call returns260 actual tokens,42 BOX records and no terminal
  EOS; strict admission rejects it. No neck P/G, proxy evaluator, visual region
  classification or physical action exists. No prefix is salvaged, no box chosen,
  no alternate wording/mode/model/retry. Native unchanged generator checks its
  length before appending a multi-token chunk, explaining possible cap overshoot;
  raw260 tokens remain intact. GPU equivalence was not separately tested.
- **Verification:**11 focused tests; independent audit reconstructs all260 tokens
  from pinned vocabulary bytes, checks8 chained records, original RGB/processed
  pixel identity, actual240 input IDs,42 raw BOX records and no downstream output.
  Reviewer `a1f0964`, main `d1246a4`; final report `474cd39`. Journal SHA
  `e099159c3f9e017c2e6afc7022edad9ec1988f91cbcf6aad11d688024161bbcf` at
  `task2-neck-box-support-run-01`; root reads complete raw response/audit schema.
- **Belief update:** this exact single semantic-part condition is insufficient
  for admissible grounding. One development fixture cannot prove general neck
  incapacity or geometric sufficiency. Close this line without prompt variants.
- **Next:** continue the independent frozen observed-surface sweep. Reassign the
  freed agent to proposal/source feasibility for initial model-BOX dense seeding
  of unchanged LK on the existing close/open traces, avoiding assistant landmarks.
  All92 source frames exist, with0.4s approach then0.05s close/lift cadence. No
  tracker features yet; semantics remain unverified and sample dependence explicit.

### Parallel iteration 033 — one omitted surface sample explains a contact boundary

- **Question:** does object-center/cropped support omit observed geometry relevant
  to the first raw palm contact, or is the existing geometry uninformative?
- **Competing predictions:** whole BOX support may expose an intersecting hand
  sample at pre22/FWD; alternatively it may remain positive or indiscriminately
  intersect every candidate. Neither prediction establishes alternative safety.
- **Frozen intervention:** producer `cb394fd`, same initial depth/calibration,
  returned own packets before actions21/22,492 inner versus1340 full BOX samples,
  all five separate convex gripper proxies and seven canonical nominal moves.
  No dynamics, learned query, semantic cleanup, thresholds or action selection.
- **Observed:** pre21 executed DOWN full/inner swept minima7.557/25.198mm,
  no containment. Pre22 executed FWD full minimum0mm, one contained hand point;
  inner minimum16.081mm. No current overlap; all other six pre22 full sweeps
  remain positive. Historical evaluator has zero raw rows at21 and26 stage rows
  at22, solely palm/bottle. Unexecuted candidate outcomes remain unknown.
- **Inspection/interpretation:** root inspected source RGB, crop, every distinct
  primary witness and canonical seven-way table. Pixel(221,158) lies in the
  visible upper/cap region outside the inner crop, but exact depth ownership is
  unverified. All14 full-support sweep minima use this one pixel/hand, and the
  decisive point also lies inside the endpoint. Reduced minima for a superset
  are tautological; the specific boundary agreement is useful bounded evidence.
  No sweep advantage, dense shape recovery or calibrated clearance is established.
- **Controls/limits:** initial support is8.4/8.8s old, stationarity unverified;
  nominal translations omit control-path variation. Current static asset checks
  pass; historical mesh byte identity remains unproven. Sensor arrays sealed
  before separate evaluation by reviewed source, without independent event timing.
- **Artifacts:** `task2-observed-surface-sweep-run-01`; feature seal
  `2272dd32051a5965b1188360c993bf89e0b1a77d9f569b053351b5e65c8e9601`.
  Producer report `e8e3a0f`, main `aba6e71`; prospective/result/factual reviews
  `c062ed6`,`6cb5825`,`e1c799e`; independent interpretation `49c324b`.
  23 producer/reviewer analytic tests pass. Integrated suite at `7dc4aae`:
  899 passed in32.91s; `regression-surface-sweep-integration.log`. Protected
  production runtime/adapter/decision files remain byte-identical to baseline.
- **Next decision:** execute all seven original candidates individually from
  fresh exact pre22-prefix reproductions, first qualifying archived FWD states,
  controls and native contacts. Record raw and>0.05N contacts and unchanged
  validators; no continuation/filter/recovery or fitted policy. In parallel,
  implement the reviewed-source initial BOX492-seed temporal proposal on the
  existing paired archive, with native tracking failures retained and no
  holding classifier. Three existing agent slots cover producers and review;
  root integrates evidence. Neither next result is presumed successful.

### Parallel iteration 034 — BOX population retains co-motion; depth association switches

- **Question:** does the old retention contrast require assistant-chosen seeds,
  or can the sealed initial model crop initialize useful temporal observations?
- **Competing hypotheses:** sparse approach captures may kill correspondence
  before grasp; surviving tracks may no longer support the target; or the full
  population may retain descriptive close/open co-motion despite contamination.
- **Intervention/control:** freeze `9a34f29`, prospective `ee05831`; all492
  row-major initial inner-crop seeds, unchanged single-seed LK across46 captures
  per arm. Fixed native failure/depth/summary rules; no feature selection or
  labels in sensor computation. Original paired script/observations unchanged.
  One batch; all45,264 rows sealed before archived mask evaluation. No new
  inference, physics, renderer, FK or live holding label.
- **Observed:** all492 survive with admitted depth at every capture in both
  arms. From preclose, median vertical displacement110.376mm versus0.003887mm;
  median3D point-minus-TCP displacement5.036mm versus114.329mm. Initial proxy
  membership414/492; final402 close/399 open.34/32 seeds have an observed
  True→False membership change. No native failure event exists in this batch.
- **First boundary correction:** seed5 at first approach capture, both arms:
  X217→216.999969482px, residual0.000122070px. Historical floor picks pixel216
  rather than217, depth1.201672m rather than0.975022m. Next capture returns to
 217. This establishes unstable sampled-depth/membership association, not large
  LK drift or full-patch identity loss. Faithful historical floor implementation
  does not settle correctness of mapping OpenCV center coordinates to depth.
- **Inspection:** root reads sealed all-population summaries and views six
  checkpoints for both arms, full curves and first-departure raw/proxy panels.
  Bottle rises with closed jaws and remains on table in open arm. The images
  make the one-pixel neck-edge switch visible. Masks never remove samples from
  motion statistics; mixed support and dependent windows remain limitations.
- **Evidence/tests:** raw `task2-box-temporal-run-01`; journal
  `0e7bd76d3f6b11244729bc767ec1b1f9a2625aa6069e494adf9743ea5900cf05`,
  sensor seal `bae9793115ededab12b6b5bca242af9cdb0c2ed8c1e8d62219af3bbce65cc30b`.
  Full-row independent audit `b06377f`, final report audit `38b3602`.
  Producer reports `1f1aa44`,`6b4938d`; integrated report `452725e`.
  Integrated temporal/physical-probe suite at `5d0905d`:911 pass in33.40s.
- **Belief update/next:** assistant landmarks are unnecessary for this one
  population-level contrast. This does not establish target identity, grasp
  load, support, slip or a holding estimator. Freeze same-track historical floor
  versus center-index nearest association after an independent convention check;
  preserve every row and all old outputs, with no retracking or fitted threshold.
  Smaller10mm actual-executor transfer is next only after measurement semantics
  settle and archive coverage is checked. Physical seven-way probe runs in parallel.

### Parallel iteration 035 — physical alternatives preserve point progress without raw contact

- **Question:** does the frozen observed-surface flag distinguish real candidate
  outcomes, and does this boundary contain a contact-free positive alternative?
- **Intervention:** producer `69d6491`, prospective `d809214`. Seven independent
  fresh init0/seed1 resets, openly replaying the original22-action/176-control
  prefix before one complete candidate primitive, canonical order. No source
  state restore, selection, continuation, new model or policy. STOP/hold is an
  explicit executed diagnostic; original policy STOP would execute nothing.
- **Qualification:** all7 prefixes match every command/state/own observation,
  8,800 native stage snapshots and23 captures. First FWD then matches original
  action22's eight controls,400 native samples, full result and actual endpoint
  RGB-D. Current models match within batch; no claim of historical asset bytes.
- **Observed:** only FWD has raw robot contact:13 rows per stage, hand/bottle,
  peak≈0.017556N. No branch exceeds0.05N; every validator passes. Actual P-distance
  reduction in canonical order, mm: FWD+5.381981514, BACK−6.148948752,
  LEFT+4.916035785, RIGHT−5.841106641, UP−5.588838873, DOWN+4.612389597.
  Executed hold drifts+0.043304533mm toward P; do not call that policy progress.
- **Interpretation:** LEFT and DOWN are measured positive contact-free witnesses
  over this0.4s horizon. Full-BOX endpoint and sweep both flag only FWD; inner
  support misses it. This agrees with raw-contact observations, not prediction
  of a force-threshold crossing (all negative), safety elsewhere or grasp
  readiness. No incremental sweep benefit, dense-shape validation or generality.
- **Inspection/report correction:** first draft reporter selected capture23
  (pre-probe) instead of actual endpoint24. Independent review caught this before
  report integration. Stored-only reporter now matches exact execution times,
  with a regression test and preserved reporting-error receipt/old artifacts;
  no physics rerun. Root inspected the corrected eight-panel actual RGB sheet.
- **Artifacts/tests:** `task2-pre22-counterfactual-run-01`,67,188 chained records,
  1,232 prefix+56 probe controls,32,200 integrations/64,400 stage snapshots,
  168 captures. Journal `35f1dee4edfcf4c3d5e059e6db3533d8df9876d0aff7b6adbbdfad7fda2f76d8`.
  17 focused producer/reviewer tests; full stored audit `b6a6659`; final corrected
  report review `eb8cac5`, producer report `ba97d53`, main report `5718c2e`.
- **Next decision:** one fresh40-action/900s approach-only condition adds a
  full-BOX/own-shape nominal endpoint containment veto for the six translations.
  Original point objective, ranking/ties, executor, threshold abort and terminal
  STOP remain; all7 candidates and exclusions retained. No physical margin,
  sweep, new target, recovery or planner. Hypothesis: first divergence at pre22
  replaces FWD with a positive eligible move; actually measure divergence and
  first new boundary, then stop without an automatic patch. Exact replay planned.
  This is a partial-observation guard experiment, not a safety-certified policy.

### Parallel iteration 036 — fix the association convention without repairing tracks

- **Question:** is the earliest depth jump caused by association bookkeeping,
  and does correcting that convention invalidate the observed co-motion cue?
- **Frozen intervention:** `dc1ec6c`, prospective `7d02e6f`; same45,264 sealed
  native rows, statuses/errors/coordinates/times unchanged. Installed OpenCV
  coordinate formula plus a synthetic integer-center test justify `floor(x+0.5)`;
  analytic epsilon/half-crossing/tie/bounds tests precede archived outcomes.
  Same selected-pixel-center backprojection, depth limits,492 denominators and
  fixed summaries. Historical floor rows reproduced exactly and preserved.
  No tracking, model, physics, renderer, interpolation or threshold fit.
- **Observed:** first epsilon switch disappears: capture1 seed5 remains217,169
  at0.975022m, and proxy membership stays414/492 in both arms. Native survival
  and valid-depth counts stay492. Final proxy membership419/402 rather than
  402/399; remaining departure seeds30/25 rather than34/32. At capture1,
  371 pixels and338 depths change per arm; these counts are not accuracy scores.
  Median preclose→final vertical motion110.935/0.003971mm and3D residual
  4.404/114.329mm preserve the broad paired contrast.
- **First remaining boundary/inspection:** both arms, seed124 at capture6:
  nearest pixel216,178, depth1.171730m, residual1.140163px, outside proxy.
  Previous capture sampled216,179 at0.992485m. Root viewed the original RGB
  and proxy panels: gripper enters the neighborhood; marked samples lie near
  the bottle edge. No residual filter was fitted; no whole-patch identity or
  replacement-geometry inference follows. Old assistant-cap trace is separate.
- **Interpretation:** a specific measurement-contract correction is supported
  independently of label improvement. Native LK status still cannot certify
  semantic/depth support. This retrospective matched association is not another
  independent tracking trial or validated holding estimator.
- **Evidence/tests:** `task2-track-association-run-01`, journal
  `b68ddf216f1164273301d58f35caf2a9b53f79d32b6e0c3e152a61ac7d20cbb3`,
  sensor seal `d0bbf1a0671a34c8af96e10fd50321697200d5c07d775eb44b7f83c09862ec22`.
  9 focused tests pass, including root integrated check. All-row audit
  `9d24e28`, report review `315adc6`, producer report `dc8f747` plus attachment
  `4dedc9e`; integrated report `63a2b57`. No correction to raw results needed.
- **Next decision:** transfer frozen LK/nearest sampling to the existing
  successful local-grasp-interface-run-02 with30frames per arm. Source-only
  inventory confirms60 sensor hashes and all14 shared-prefix RGB-D/K/T arrays.
  Initial ownTCP is absent; keep it unknown and report only preclose13-relative
  motion, retaining all29,520 rows. Sensor seal precedes mask evaluation.
  No new physics/inference or classifier. This changes executor/horizon and
  lift scale together, so it tests descriptive transfer, not amplitude-only
  causality. Endpoint-veto fresh physical probe proceeds independently.

## Iteration and stopping rules

Each next experiment gets a question, competing predictions, fixed controls,
prospective condition selection, and independent evaluator before inference.
Inspect the first concrete failure and raw frames/inputs, not only aggregate scores.
Failures and environment-access issues remain recorded. No hidden retry.

Start closed-loop testing with a bounded approach slice, then a mechanically
qualified existing manipulation task. Partial skills remain partial skills.
Separate official success, interaction validity, genuine model choices, forced
singletons, and deterministic-policy contributions. Three fresh-process repeats
plus replay test reproducibility; held-out init/view/uncertainty cases test transfer.

Continue until a clear architecture is supported within stated conditions, the
core hypothesis requires a major reframe, necessary resources are unavailable, or
a genuinely human research decision is required. A negative experiment alone does
not end the mission or authorize arbitrary complexity.
