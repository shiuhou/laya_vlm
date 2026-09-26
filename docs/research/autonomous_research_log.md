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
- **Result:** Pending. No new inference at registration.
- **Artifacts:** Planned `runs/autonomous-research/predicate-verification-*`.
- **Interpretation:** Pending; no controller promotion or manipulation claim.
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
- **Result:** Pending.
- **Artifacts:** Planned `runs/autonomous-research/perception-support-audit-01`.
- **Next decision:** Only improve a sensor component after identifying an error
  that can change downstream decisions. Do not add a segmentation model by default.

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
