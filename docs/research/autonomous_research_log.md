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
