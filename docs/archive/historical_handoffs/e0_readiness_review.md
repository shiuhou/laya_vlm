> Historical record; its plans and checkout paths are not current instructions.
> Current authority: [current_state.md](../../current_state.md).

# E0 adversarial review and diagnostic tooling

2026-09-23. Audit baseline: `fb0823b`. This is a **review/proposal**, not a new
experiment specification or freeze. Historical handoffs and authoritative research
documents are unchanged. No new model calls, simulator trajectories or E0 collection
were run. Implementation changes are read-only evidence inspection, its shared
analysis helper/tests, and suppression of geometric error when both referent
definitions are unknown. CDS/effect revisions below are **not implemented**.

## Research memo: what can E0 presently mean?

The strongest defensible interpretation is **descriptive, interface-conditioned
decision fidelity**: how this frozen model's output distribution changes when a
complete oracle-conditioned input bundle is replaced by a perceptual bundle, under
the same candidates, history and presentation. This is not yet fidelity to an expert
policy, an upper bound on performance, or preservation of useful robotic decisions.

The geometric comparator is now coherent. Referent v0.2 is the pixel-weighted world
centroid of the first-visible foreground top-handle surface in `agentview`, using
shared camera calibration and half-pixel raster centers. Oracle first-hit mesh rays
and sensor-only bbox/RGB-D support estimate that quantity independently. The sensor
is not corrected with oracle membership. It is **not** rigid pose, surface clearance,
grasp center, or a material point whose derivative is necessarily object velocity.
Shared calibration and ray/raster edge differences remain measurement assumptions.

The decision reference is not validated. All twelve init-0 oracle-conditioned Laya
choices were GRASP/RELEASE. The collector's success is not validation: its policy
used different primitives, hierarchy and privileged effects. The local evaluator
is independent of the no-effect model input, but is only a short-horizon, set-valued
diagnostic—not expert truth. Failure to demonstrate one-step utility does not prove
that every preparatory strategy is wrong.

Representative **existing** raw evidence, re-inspected without inference:

| Boundary / phase | Oracle state: remaining mm, target contact | Oracle choice / raw p / normalized margin | Independent evidence | Interpretation |
|---|---|---|---|---|
| 0 / far | 151.659, false | GRASP / .9118 / .8266 | −7.629 mm approach versus STOP; FWD/CCW have local support | Preparation unvalidated, not a demonstrated useful choice |
| 48 / progressing | 113.550, true | RELEASE / .8137 / .6277 | Same commands and endpoint as STOP; RIGHT adds 9.089 mm closure | No incremental task utility established |
| 120 / late pause | 30.751, false | RELEASE / .6048 / .2103 | No offered action resolves the local rubric | Inherently unresolved under this evaluator; not a wrong-action label |
| 140 / loaded contact | 17.516, true | GRASP / .5958 / .1918 | Reopens 14.272 mm; 21.261 mm worse than STOP | Concrete adverse local consequence despite oracle input |
| 144 / near completion | 13.873, false | GRASP / .7824 / .5652 | −.030 mm closure versus STOP; STOP itself moves 56.358 mm | Quasi-static action semantics not established here |

GRASP here means **command finger closure**, not “successfully grasp the handle.”
RELEASE is an executable command in every offered phase, but duplicates STOP when
already open in these probes. Keeping both is legitimate for a frozen vocabulary
study; treating eleven labels as eleven independent physical alternatives is not.
Terminal step 155 is a sentinel, not an ordinary ongoing-task decision.

Supportable claims:

- Paired states share a physical boundary and an explicit geometric estimand;
  missing perceptual contact/progress remain missing.
- The fixed offline candidate/state interface is replayable and token-audited.
- Repeated identical inputs were stable at returned API precision in this pilot.
- Three actual LIBERO resets yield approach/contact/progress states, with unequal
  completion coverage. This is not three random seeds on the same reset.
- Descriptive distribution differences and coherent, explicitly scoped input
  interventions can be measured. They do not automatically have physical meaning.

Unsupported claims:

- Oracle-conditioned Laya or geometric Rule is an expert/useful-policy reference.
- Disagreement is perception error, or agreement demonstrates state use/sufficiency.
- The current oracle CDS contains all action-relevant state at loaded boundaries.
- Nominal pose holding and 10 mm motion have been validated across this sample.
- Uncalibrated covariance/semantic scores are probabilistic correctness guarantees.
- Correlated frames/repeats establish population, task or closed-loop robustness.

**Recommendation:** retain **A, descriptive decision fidelity**, as the only
currently defensible *conditional* E0 claim, subject to explicit human approval.
If useful decision sufficiency remains the scientific goal, the next bounded study
should be **C, revised oracle interface study**, evaluated using **B, independent
task-aware validation**. Do not relabel the existing pilot as B or silently turn
the no-effect comparison into a fixed-effect experiment.

Minimal work before a useful-reference freeze is a discriminating diagnostic, not
an arbitrary field expansion: distinguish ambiguous objective/horizon and option
aliases from missing task-relative information and uncharacterized dynamic state.
Predeclare a small neutral-alias/order and state-insensitivity control; characterize
the flagged action regime; then test one justified field family at a time. These
diagnostics are proposed, not run here. Do not tune wording against desired answers.

## Decision State Review

Evidence base: current `decision_interface.py`, actual compact input, and all 18
accepted Stage 4 pairs. No field necessity is established by a constant-field pilot.
“Remove” means omit from a proposed minimal **model projection**, not delete raw
belief, source evidence or replay history.

| Field | Why needed | Evidence | Risk | Keep/change/remove |
|---|---|---|---|---|
| `task.instruction` | Specifies close versus open | Same instruction in all pairs | Constancy does not establish sensitivity | Keep |
| `task.target_identity` | Disambiguates target | Original query selected background cabinetry | Query text is not tracked instance identity | Change name/definition to target query/context |
| `robot.tcp_position_m` | Basis for relations/workspace reasoning | Shared proprioception | Redundant with delta; absolute-coordinate shortcuts | Keep audit; ablate from minimal model view |
| `robot.gripper_width_m` | Actual aperture versus command | Joint-opening proxy varies about 71–80 mm | Not exact pad clearance, contact or holding | Keep with precise measurement definition |
| `robot.gripper_command` | Identifies action intervention/alias | OPEN in all 18 pairs | Command mistaken for achieved state | Keep |
| `target.position_m` | Geometric reference primitive | Comparable centroid; init-0 fused error 38–99 mm | View-dependent, not contact/grasp point | Keep audit; relative geometry may suffice for model |
| `target.position_definition` | Prevents unlike-point comparison | Legacy AABB/bbox points were incomparable | Base projector still uses legacy definition; collector explicitly substitutes new estimator | Keep as fixed referent contract; never merely rename old values |
| `target.velocity_mps` | Might predict delayed geometry | Oracle null throughout; perceptual norm up to .0725 m/s | Segmentation/visibility motion is not rigid-body velocity | Change to referent-estimate velocity; defer from minimal view |
| `target.visible_now` | Could signal current occlusion | Both branches null throughout | Historical detection does not imply present visibility | Remove from minimal view; unsupported in audit |
| `relations.tcp_target_delta_m` | Avoids model XYZ subtraction | Deterministic target minus TCP, world axes | Centroid is not an interaction point | Keep, explicit frame |
| `relations.distance_m` | Convenient approach summary | Oracle range about 46–237 mm | Redundant; not surface gap/clearance | Keep provisionally; test redundancy |
| `relations.xy_error_m` | Intended alignment summary | Only world XY norm is computed | Vertical-approach assumption inappropriate for horizontal drawer motion | Replace only with justified task-axis alignment, or remove |
| `relations.height_error_m` | Vertical offset | Exactly delta Z | Duplicate information framed as task error | Remove from minimal view |
| `interaction.target_contact` | Distinguishes approach/interaction | Oracle varies across phases; perceptual null | Any moving-geometry contact is not productive finger contact | Keep scoped predicate; do not upgrade to grasp/contact mode |
| `interaction.holding` | Relevant to transport | Both branches null throughout | Closing a drawer need not involve holding | Remove from minimal top-drawer view pending evidence |
| `progress.remaining_open_mm` | Task-goal error | Oracle varies through closure; perceptual null | Negative terminal value; not nonnegative remaining distance | Keep as explicitly signed joint-goal error |
| `quality.geometry_age_s` | Freshness affects usefulness | Zero in both branches for all 18 | Latest update age is not age of every posterior contribution | Keep with exact capture-age definition |
| `quality.geometry_valid` | Availability/control support | True in both branches for all 18 | Oracle tests existence; perception tests age/covariance/TTL | Change: separate availability and policy-specific control validity |
| `quality.position_covariance_m2` | Potential directional uncertainty | Heuristic bbox covariance reused for centroid | Uncalibrated; misses wrong-instance/model errors; oracle null | Keep audit; expose as separately tested uncertainty family |
| `quality.covariance_calibrated` | Prevents false precision claims | Perceptual false throughout; oracle null | Strong branch cue; unknown versus not-applicable conflation | Move to audit/config unless intentionally tested |
| `quality.semantic_age_s` | Identity evidence freshness | Perceptual zero, oracle null | Redundant in current single-stream sample | Keep audit, omit minimal view for now |
| `quality.semantic_valid` | Evidence TTL/support | Perceptual true, oracle null | Does not mean correct localization/identity | Rename evidence-unexpired or omit minimal view |
| `quality.semantic_confidence` | Potential identity ambiguity cue | Raw scores .909–.970 | Uncalibrated score, not probability of correct target | Keep raw score for analysis; omit confidence claim |
| `quality.temporal_consistency_ok` | Admission/history consistency | Perceptual true, oracle null | Not physical or identity consistency | Keep audit; intentional temporal intervention only |

Recent history is separate from CDS: one preceding **raw seven-dimensional robosuite
control**, actual TCP displacement, elapsed simulation time and gripper command.
It is not necessarily a completed atomic action. Displacement/time supplies an
average rate, not instantaneous velocity or controller tracking error. Keep the
legitimate actual outcome; document raw control semantics or keep that opaque vector
in audit rather than expecting the model to interpret it as the offered vocabulary.

Full field source/basis/privilege is audit evidence, not physical state. Compact
presentation removes those labels, but not asymmetric **null masks**: oracle has
contact/progress while perception has velocity/covariance/semantic quality. This
is not hidden privilege leakage. It means whole-bundle disagreement mixes missing
information, value errors and quality cues; it cannot isolate position error.

### CanonicalDecisionState v0.2 hypothesis — not implemented

For a **separately characterized quasi-static regime**, test this small projection:

```text
fixed schema/config: world frame, units, common target referent
task: instruction, target query, goal-error definition
robot: retained gripper command, measured aperture
relations: world TCP-to-target delta, distance
task geometry: closing axis [only with explicit legitimate source; else unknown]
interaction: scoped target-contact predicate
progress: signed joint-goal error
quality: geometry capture age, evidence available, defined control-validity status
shared outcome: one actual TCP displacement + duration + documented prior command
audit: raw fields, exact derivations, missingness reason, source/privilege, IDs
```

The closing axis is a **testable addition**, not assumed available perceptually.
Task contact/progress stay unknown where sensors do not support them. Covariance,
semantic scores and redundant coordinates remain accessible as preregistered field
families. Missingness reasons belong in audit unless their model visibility is an
explicit condition. New versioning must distinguish unknown from not applicable.

This proposal does not claim sufficiency at loaded/in-flight collector boundaries.
Orientation, velocity, controller error and loading are plausible missing families,
but the pilot does not establish which matters. Record/diagnose those physical
mechanisms before adding all of them and declaring the result “minimal.”

## CandidateEffectBundle review

Current implementation is a useful provenance container, not a complete prediction
contract. Geometry effects estimate TCP-to-point distance/XY change. Oracle effects
currently contain drawer closure, gripper-to-collision-surface gap reduction,
endpoint contact and sampled obstacle force. **These are different quantities.**
Swapping the existing bundles would change semantics and availability as well as
estimation error. The primary State-Gap replay correctly requires empty effects.

| Consequence | General or task-specific? | Legitimate support now | Limit |
|---|---|---|---|
| Nominal TCP translation/rotation, retained grip | General action semantics, not prediction | Known executor command definition | Command intent is not physical realization |
| Predicted target-point distance/XY change | Target-relative geometry | RGB-D estimate + proprioception + nominal translation | Stationary target, ideal execution; not contact dynamics |
| Nominal endpoint within configured workspace | General configured constraint | Bounds + proprioception + action semantics; simple future estimator | Not swept clearance, IK or collision freedom |
| Drawer closure | Task-specific | Privileged simulator preview only | Perceptual equivalent unavailable today |
| Endpoint contact, sampled obstacle force | Interaction/evaluator metrics | Privileged simulator preview only | Conditional endpoint/sampled result, not probability or safety bound |
| Grasp success, holding probability, swept clearance | Potentially useful, not currently supported | Unknown | Box centroid and gripper closure are insufficient |
| Previous actual TCP/gripper response | Historical current-state evidence | Proprioception | Keep in recent outcome, not future-effect bundle |

No effect is universally required by every task. The useful universal part is a
consistent **effect contract**, not a mandatory bag of consequence fields. Tier-0
kinematics must not assign physical STOP displacement/progress zero: the pilot shows
substantial ongoing dynamics under a hold command.

### Minimal research contract for CandidateEffectBundle v0.1

Clarification proposal, not a schema implementation or learned world model:

```text
version, candidate_set_id
input_state_id / physical_context_id                 # audit
reference_sim_time, input_age_s
estimator_id/version, atomic_semantics_id, executor_config_id
effects[token]:
  source: geometry | oracle_sim | unknown            # learned reserved, unused
  privileged, status: supported | unsupported | invalid
  invalid_reasons, assumptions, frame
  horizon: requested_steps, nominal_duration_s,
           actual_steps/duration_s if simulated, termination_rule
  values: only metrics with fixed definitions/units; unsupported = null
  uncertainty: method, calibrated, supported interval or null
```

Candidate feasibility stays in CandidateSet; effects cannot silently rewrite it.
No effects supplied (`none`) differs from an unavailable estimate for a requested
effect. Bind retained gripper command through state/executor semantics. Reject
nonempty `unknown` values and mislabeled privileges; current loose dictionaries
do not fully enforce this. There is no evidence of current primary-path leakage.

Metric conventions: distance/alignment change is **after minus before** (negative
improves distance); closing mm is **before minus after remaining opening** (positive
closes); endpoint contact is a boolean prediction, not contact likelihood. Force
is a sampled maximum, not a continuous-time safety bound. Native primitives can stop
early on success: equal requested steps do not imply equal actual horizons.

### Later Effect-Gap design — separate from State Gap

Hold perceptual state, physical boundary, candidates/order, history, question,
provider/inference and action horizon fixed. Distinguish three estimands:

1. **Common-field estimation gap:** same metrics, referent, units and missingness
   mask; simulator versus geometric values. A small first test can apply ideal
   versus simulator-realized TCP displacement to the **same fixed perceptual target
   point**. This tests execution realization, not moving-target prediction.
2. **Missing-effect information:** hold common fields fixed, add privileged closure/
   contact values versus explicit unknowns. This is information availability, not
   an estimator-accuracy comparison.
3. **Source-label control:** identical values with matched/blinded model-facing
   source labels; raw provenance remains intact. Current compact effects retain
   `source`, `privileged`, assumptions and differing payload shapes.

Compare distribution changes, local utility and contract flags separately. Use
STOP-adjusted consequences only with matched actual horizons, or explicitly study
native-termination consequences. Never use the legacy preview builder to construct
one branch's candidates: its contracts/descriptions already embed privileged effects.

## Hostile E0 review

F = narrow descriptive fidelity; U = preservation of useful robotic decisions.

| Weakness | Why it matters / severity | Minimal fix or control | Blocks E0? |
|---|---|---|---|
| Oracle validity | All 12 reference choices GRASP/RELEASE; demonstrated adverse/local nonincremental outcomes. **Critical for U** | Approve F explicitly, or separately validate revised interface with independent evaluator | U yes; F requires claim approval |
| Candidate probe design | Eleven labels need not be eleven interventions; natural gates bypassed; many loaded probes exceed reset envelopes. **High** | Freeze offline scope; report state-conditioned aliases and natural availability; characterize operating regime | U yes; F conditional |
| Same-question assumption | Identical question is not unambiguous objective, horizon or terminal handling. Literal GRASP/RELEASE labels enter Laya. **High** | Freeze actual rendered wording/order; bounded alias/order/null-state controls before semantic claims | U unresolved; exact-representation F possible |
| Laya stability | Three repeats at rounded API precision do not ensure universal determinism; API can internally fall back CUDA→CPU. **Moderate/high** | Compare per-call actual device/dtype already logged; fail/preserve changes before formal freeze; repeat under frozen implementation | Matching guard needed for formal run; no fallback observed in pilot |
| State comparability | Values and missingness/quality differ together; geometry_valid predicates differ by branch. **High** | Whole-bundle primary estimand; coherent field-family and matched-null controls for attribution | No for F bundle comparison; yes for field-specific claims without controls |
| Target referent | Visible centroid is view-dependent, not pose/contact point; shared calibration, mixed-edge residual. **Moderate/high** | Freeze estimand/camera/raster convention; preserve contamination/absent referents | Geometric comparison usable; decision sufficiency unvalidated |
| Sample independence | Frames, repeats and fresh/stale pairs cluster by trajectory; teacher-forced collector distribution. **High** | Per-init/trajectory results; repeats for stability, not n; no pooled-frame confidence claims | Blocks generalization, not scoped description |
| LIBERO init coverage | IDs 0/1/2 share transferred controls; only 0 completes and has strict near-completion coverage. **Moderate/high** | Preserve failed trajectories/missing strata; freeze actual vectors/control hashes; do not replace failures | Narrow three-reset F viable; broad robustness unsupported |
| Attribution of disagreement | Null patterns, geometry, contact/progress, aliases and latent dynamics interact; agreement can reflect label priors. **Critical** | State-insensitivity control and preregistered coherent replacements; no “perception failure” labels | Mechanistic/useful claims blocked; descriptive differences measurable |

Installed Laya `agent.system_one` can change its device/dtype after a CUDA error.
**Correction to an initial audit suspicion:** `LayaProvider.decide` already records
post-call `actual_device` and `actual_dtype` in the canonical token audit. All 72
accepted pilot Laya calls record `cuda` / `torch.bfloat16`; fallback is not observed.
The gap is that the old summary does not compare those fields and replay does not
fail on a change—not absence of per-call evidence. The new inspector exposes
agreement/variation; a fail-closed formal replay guard remains a proposal.

The STOP-only natural gate is a different issue from physical STOP drift. With
unobserved velocity prior, position trace grows approximately
`.009508 + 3t² + t³`, crossing `.03` at about `.0815 s`. This is a correct expression
of an uncalibrated configuration, not an empirical safety boundary. Offline shared
probes make data collection possible without loosening thresholds. No change is
justified merely to increase action availability. Paused fresh/stale collection
tests observation availability, not natural online inference throughput.

## Documentation update proposal — not applied

The main README/research/architecture identity is already substantially correct.
Keep: “A research runtime for studying decision-sufficient interfaces between the
physical world and typed embodied decision models.” Laya is replaceable; Jev-LIBERO
supplies controller/preview/collector components; Show-Harness inspires token names,
not an imported executor; LocateAnything supplies query localization, not state truth.

| Document | Specific issue | Small proposed update |
|---|---|---|
| README | Blanket out-of-order rejection hides fixed-lag replay; “never downloads” exceeds explicit remote loader behavior; Windows-only first test instructions | Distinguish late replay from invalid/sequence rejection; scope offline claims to audited local paths; add verified Linux test command |
| `research.md` | Useful-interface question and descriptive fallback coexist; stability can be overread as state use | Put F-versus-U claim gate first; name aliases/order/null masks as interface variables; no automatic E0 approval |
| `architecture.md` | Logical question hash differs from actual compact question; quality predicates differ; action operating regime easy to overlook | Show actual model presentation boundary, payload/token identities, conditional action semantics and field comparability limits |
| `current_state.md` | Stage 4 results are accurate but new audit findings/inspection entry point are absent | Add a short linked review/tool note and proposed inference-change guard; retain NO gate and all limitations |
| `vision_model.md` | Historical preamble conflicts with lower present-tense tracker, never-blocking, sufficiency-YES and old evaluation matrix | Mark those sections explicitly historical/inactive; show live async versus paused pilot paths; retain historical measurements |
| `pyproject.toml` description | Still “Multi-rate belief fusion and Laya decisions over Show-Harness atomic actions” | Align package metadata in a separately approved documentation update |
| Handoffs | Old AABB referent, init-0-only and 103-test facts are historical | Do not rewrite; use current-state index to resolve chronology |

One additional diagram is worthwhile; do not add decorative architecture diagrams:

```text
same physical boundary
  ├─ RGB-D history + proprio → belief → perceptual CDS ─┐
  └─ privileged readout + shared proprio → oracle CDS ─┤
                                                     ├─ same C/history, no E → D
  separate full-snapshot counterfactual evaluator ─────┴─ analysis only
                                                      (never model input)
```

This shows the causal/evaluator boundary missing from a single linear pipeline.
Keep the existing linear diagram for concept definitions and distinguish the live
Stage 2 executor path from offline canonical probes, which do not control collection.

## Implemented diagnostic: one CLI, not five tools

Research value: the batch summary already computes disagreement and repeatability.
A single per-pair inspector closes the practical gap between those numbers and the
evidence: which values, unknowns, sources, options and actual outputs produced them?
It surfaces ambiguity and integrity problems without changing the experimental input.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
$P -m embodied_runtime.experiments.inspect_decision_pair \
  runs/reference-pilot/replay-init0-v02 --list

$P -m embodied_runtime.experiments.inspect_decision_pair \
  runs/reference-pilot/replay-init0-v02 --init-state-id 0 --step 140 \
  --collection runs/reference-pilot/init0-raycast-v02

$P -m embodied_runtime.experiments.inspect_decision_pair \
  runs/reference-pilot/replay-init0-v02 --pair-id 25980f57a461 \
  --show-input --format json
```

Accepts a run directory or raw JSONL. `--variant` disambiguates fresh/stale records.
Ambiguous selections fail rather than guess. Output is stdout only. No model or
simulator is loaded, no unknown is filled, and no source artifact/summary is written.

- Full raw field values, source/basis/privilege, missingness, comparable numeric
  differences; mismatched position definitions suppress misleading numeric error.
- Exact shared candidate semantics, natural feasible sets/veto/soft metadata kept
  separate; unobserved oracle natural set remains unknown.
- Raw choices/probabilities, confidence and latency; normalized JS/margin/top-2
  diagnostics; repeated-input and consumed-token evidence. Returned precision stays
  explicit. No invented probabilities or decisions for interrupted runs.
- Hash-chain, pair, candidate, question, payload and token identity checks reused
  from existing analysis. Mismatched presentations are exposed; contradictory
  clipping audits fail; incomplete audits cannot become full-input-valid evidence.
- `--show-input` reconstructs only observed branch/presentation combinations whose
  payload hashes were checked. It does not pretend a missing call happened.
- Recorded device/dtype and model content ID are visible. Payload validity is not
  proof of matched hardware, reference utility, or correctness.
- Optional collection join requires the identical pair. Evaluator source features
  are cross-checked when available; rubric is recomputed from raw previews.
  Incomplete probes, contract flags and unknown/nonzero restoration errors remain
  visible. Exact command/endpoint alias groups are **boundary-specific**, not a
  vocabulary rewrite. Evaluator evidence never enters displayed model payloads.

The batch writer now uses a pure `analyze_equivalence` helper, preserving existing
CSV/JSON behavior. The inspector is not a simulator-state restore verifier or an
image/ray re-audit; use the existing dedicated tools for those checks.

### Verification

Using Python 3.10.21 / NumPy 1.26.4 / pytest 9.1.1 / ruff 0.15.22, without loading
MuJoCo or inference models:

```sh
$P -m pytest -q tests/test_inspect_decision_pair.py tests/test_equivalence_summary.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Focused tests: **37 passed**. Full tests: **173 passed**. Lint and compileall: PASS.
Tests cover read-only behavior, selection ambiguity, missing/incomplete evidence,
corruption, candidate identity, provenance/unknowns, clipping, presentation mismatch,
device changes, evaluator joins and separation from model inputs.

Existing-artifact smoke: all 12 final pairs listed; steps 0/48/140/144 inspected,
including separate evaluators. STOP/RELEASE command+endpoint equivalence is visible;
step 140 preserves adverse closure despite top-1 agreement. Legacy replay remains
unusable for full-input Laya claims when token audit is absent; legacy referents
remain incomparable. Hashes of 15 raw/summary files were unchanged by inspection.

## Review gate

Geometric reference comparable: **YES**, under the stated referent.
Validated useful-decision reference: **NO**.
Multi-init collection viable: **YES**, unequal phase coverage explicitly retained.
Ready to freeze `exp-e0-v0`: **NO**. Ready for formal E0: **NO**.

Smallest next decision: approve the narrow descriptive claim, or authorize the
bounded reference-interface/operating-regime diagnostic described above. The existing
conditional 29-boundary/58-pair proposal remains conditional; this review does not
authorize collection, change schemas, add effects, tune thresholds or create a tag.
