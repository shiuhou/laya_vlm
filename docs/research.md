# Research direction and the next experiment

This is the authoritative direction for **Track B — Decision Interface Research**.
Track A demonstrates connectivity; its successful execution is not evidence for the
scientific hypotheses below. Track responsibilities and shared foundations are in
[development_tracks.md](development_tracks.md); verified status is in
[current_state.md](current_state.md).

Central question: **What information must the world expose to a robot decision
model for useful decisions?** This runtime studies how sensor observations,
proprioception and history can be converted into decision-sufficient state and
separately identified candidate-effect evidence for typed embodied decisions.
It does not aim to reconstruct the entire simulator or prove a particular model
intelligent. The oracle-conditioned model is a reference to validate, not ground truth.

Engineering first makes World/Sensors → Structured Interface → Typed Model → Robot
work as a controllable, replaceable instrument. The science then asks which world
and action-consequence information that interface must preserve—not how to reproduce
the whole simulator or merely optimize wording.

## Three-stage roadmap and review boundaries

- **Stage 4, current:** reference/interface validation after the common-referent and
  multi-init pilots. The manipulation-reference gate is still NO; diagnostics and
  minimal-interface hypotheses do not themselves authorize a formal experiment.
- **Stage 5, only after approval:** frozen formal E0 and field-family interventions,
  yielding a decision sensitivity map, not just one agreement percentage.
- **Stage 6, later:** closed-loop tests of the sensitive fields found in E0—temporal
  validity, missing-state estimators, then separately controlled effect comparisons.
  Provider comparisons follow under a matched interface, not a simultaneous change
  to perception, candidate logic, effects and model. Each stage requires review.

The immediate comparison is **State Gap**:

```text
D(oracle decision state, C, fixed history, no effects)
vs
D(perceptual decision state, C, fixed history, no effects)
```

Freshness, uncertainty, missingness and field provenance are dimensions of this gap.
Temporal belief and delayed-event replay remain foundations, not a separate claim
of architectural novelty. A later, separate **Effect Gap** comparison holds the
perceptual state fixed and changes oracle-simulator versus non-privileged candidate
effects. Oracle effects are privileged diagnostic evidence, never deployable vision
policy input.

Belief quality should ultimately be evaluated both geometrically and by its effect
on decisions. Agreement with a useless oracle-conditioned policy is not evidence
of useful decision sufficiency; disagreement is not automatically perception error.

## Hypotheses, not schema requirements

| Information or mechanism | Evidence so far | What remains unresolved |
|---|---|---|
| Articulation + requested state | A finite categorical status interface is goal-sensitive; masking articulation reproduces the tested perceptual output | A legitimate sensor articulation estimate is absent; this is not an action-selection reference |
| Explicit UNKNOWN response | Handles the tested missing-state cases that the binary vocabulary mishandles | Generalization to new wording, partial evidence and uncertain/stale observations; no calibrated abstention guarantee |
| Task-relative geometry | Some sentence-form single-axis controls work; mixed-axis and goal-reversal controls fail | What geometry/abstraction a competent manipulation interface requires; an upstream winning-axis computation already performs policy |
| Contact, holding and recent outcomes | Available evidence/provenance can be represented; unsupported perceptual fields remain unknown | Which family improves useful choices, rather than correlating with task phase or making outputs change |
| Age, validity and uncertainty | Temporal contracts and metadata work | Whether these fields improve task-useful decisions; covariance is still heuristic |
| Candidate-specific consequences | Candidate-local facts help synthetic contrasts; the tested physical eleven-action reference still fails | Neither necessity nor general sufficiency of effects has been established |

Changing an output is not automatically improving a decision. Future field tests
need a bounded question with an independent reference, matched model/candidates/
question/history, one information-family intervention at a time, and same-input
controls. Candidate clarification is a separately labeled condition, not a hidden
change during a state comparison. Do not promote CDS v0.1, a proposed v0.2, or a
larger field list as validated decision sufficiency.

## Current evidence and limitations

The [paired status and consequence gate](reference_gate_handoff.md) isolates a
missing-articulation effect using exact field masking: the binary status model
declares DONE on unknown input, while an explicit UNKNOWN option handles these
tested cases. This is not a visual-estimation or manipulation E0 result. A
separate actual-effect reference test fails despite a passing synthetic
two-option consequence-use control. Effect presentation, native action semantics,
option count, and absolute-versus-STOP-relative abstraction remain distinct
scientific issues; supplying oracle consequences is not automatically sufficient.

The preceding [bounded interface search](interface_search_handoff.md) tests
smaller states rather than presuming CDS v0.1 is sufficient. It finds a narrow
goal-sensitive articulation-status judgment, but no robust eleven-action policy.
Perfect nominal scores appear when code precomputes the winning geometric axis;
that transfers policy upstream and is not evidence of decision sufficiency.
The proposed E0 below remains conditional, not superseded by a quiet change of
task or decision vocabulary.

The canonical interface and small paired replay work. A recorded Jev collector
trajectory genuinely covers approach, contact and drawer closure. Its successful
collection policy used simulator preview, different primitives and hierarchy; that
does not validate the current no-effect Laya reference policy.

The old visual query/depth proxy and simulator collision-AABB center remain
incomparable. The reference-quality pilot instead defines the visible-pixel-weighted
surface centroid of the foreground top-drawer handle. A sensor-only box-support
RGB-D estimator and an independent first-hit visual-geometry ray oracle estimate
that same quantity. Box contamination is measured, not corrected by the oracle.
This is a view-dependent point, not rigid object pose or a grasp center. Current
visibility, contact, holding and task progress are unknown unless their evidence
source actually supports them. Tracking is inactive; visual covariance and semantic
scores are uncalibrated.

An initial replay exposed Laya input truncation. The replacement compact presentation
is token-audited, rejects clipping, and records actual consumed tokens. Earlier
truncated replay artifacts are retained but cannot support full-interface claims.
See [the interface handoff](decision_interface_handoff.md) for measurements.

## Prior E0 collection proposal — conditional, not active or frozen

The design below is retained for traceability, not as instructions to start
collection. It requires a defensible reference/claim and renewed protocol review.
The narrow status result and the engineering demo do not silently redefine or
unblock the proposed manipulation comparison.

The **reference-quality pilot** is predeclared in
[reference_pilot_protocol.md](reference_pilot_protocol.md). Its result and raw evidence
are in [reference_pilot_handoff.md](reference_pilot_handoff.md). It does **not** validate
no-effect oracle-conditioned Laya as an expert reference. Preparatory choices are
not proved wrong merely by lacking one-step utility, but high-confidence agreement
with an unvalidated reference cannot establish useful decision sufficiency.

The remaining gate is scientific: approve a **descriptive decision-fidelity**
claim, review the narrow task-progress target, or establish a competent atomic
reference in a separate pilot. The capability ladder now shows why additional
fields alone are not justified: even well-defined mixed geometry and reversed
motion objectives fail. Loaded/in-flight action semantics have independently been
characterized; reset calibration does not establish realized pose-hold/10 mm
motion at every collector boundary. Do not silently settle the simulator, discard
flagged states, or loosen contracts. A fixed-effect condition remains a separate
reviewed option: both branches would receive the *same* effects, clearly marked
privileged. None were supplied in the interface search; they must not quietly
enter the present no-effect comparison.

The prior bounded collection proposal, still subject to that gate:

- Task: `KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet`, LIBERO `libero_90`.
- Actual benchmark initial-state IDs **0,1,2**, seed **1**, with benchmark-state,
  task/assets and archived-control hashes. All three fixed-control trajectories
  are verified; only init 0 completes the task. Do not discard init 1/2 or append
  successful-only replacements. Near-completion is not pooled across these resets.
- Select from boundaries at least eight controls after reset and before first
  success. Five evaluator strata: far (surface gap >=20 mm); approach (5<=gap<20);
  contact (measured target contact); progressing (>0.1 mm closure since prior
  control); late (remaining opening <=25% of that reset's initial opening).
  Select indices `round(q*(n-1))`, q=.25,.75, ties-to-even, in chronological order
  per stratum. Deduplicate physical states across strata; preserve missing strata.
  Overlapping phase names are not claims of monotonic task progression.
- On the audited trajectories this selects **29 physical states**:
  init 0 `[11,17,23,44,56,82,94,131,134,146]`;
  init 1 `[13,24,32,48,61,132,147,153,155]`;
  init 2 `[14,27,35,50,60,82,132,142,147,151]`.
  Twenty show >0.1 mm drawer displacement over the preceding .4 s; the nine
  static-target windows are controls. This is observed mechanism sensitivity,
  not a model-outcome-derived selection rule.
- **Fresh / .4-s-old** conditions at each boundary: 58 paired records total.
  Collect RGB-D at every archived control boundary with simulation paused during
  inference. Replay the identical history through temporal fusion: the stale
  branch receives only captures through `step-8`, while fresh receives through
  `step`; both use current, identical proprioception/history at the same physical
  boundary. Log actual geometry reference age and temporal update identities.
  No artificial occlusion condition yet; do not conflate wall latency with age.
- One fixed 11-token semantics-only probe set, same order, same question, same last
  robot outcome, empty effect bundle on both branches. These are offline choices,
  not execution authorization. Record natural candidate availability separately.
- One local Laya content revision/API/config/presentation for both branches, Rule as
  a deterministic comparison. Three alternating-order repeats on every branch; seed
  once per run rather than resetting before each call. Log actual device and tokens.

Primary metrics: top-1 agreement; top-2-set agreement with ties explicit; Jensen–
Shannon divergence in nats using normalized returned probabilities; oracle margin
`p1-p2`; decision latency; same-input variability. Preserve raw rounded probabilities.
Condition results on phase, actual age, missingness and natural candidate availability.
Use position/relation error only for genuinely comparable referents. Candidate-set
agreement is unknown when an oracle natural set has not been collected.

First sensitivity families on fresh pairs: target position **and coherently
recomputed relations**; remaining-opening missingness; contact missingness;
age/validity/covariance as a coherent quality family (with separate labeled
counterfactuals only later). Literal
single-field counterfactuals can intentionally leave inconsistent relations, but must
be labeled accordingly. Model-facing numeric precision and inclusion/exclusion of
provenance are themselves frozen interface choices, not invisible implementation details.

Report per-initial-state/trajectory results. Frames and repeat calls are correlated,
not independent sample size. Three trajectories support a small descriptive
benchmark, not population generalization or a convincing bootstrap interval over
independent tasks. Show every reset; do not interpret non-significance as equivalence.
Freeze code, model bytes, task assets, initial states, collection/phase selection,
reference-point definition, candidate vocabulary, question, history, numeric
presentation, temporal config, delay delivery and metrics before formal collection.

No E0 freeze or formal collection is authorized by this document. Current readiness
and next human gate are maintained in [current_state.md](current_state.md).
