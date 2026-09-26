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
