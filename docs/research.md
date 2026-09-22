# Research direction and the next experiment

This runtime studies how asynchronous sensor observations can be converted into
decision-sufficient state and candidate-effect evidence for typed embodied decisions.
It does not aim to reconstruct the entire simulator or prove a particular model
intelligent. The oracle-conditioned model is a reference to validate, not ground truth.

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

## Current evidence and limitations

The canonical interface and small paired replay work. A recorded Jev collector
trajectory genuinely covers approach, contact and drawer closure. Its successful
collection policy used simulator preview, different primitives and hierarchy; that
does not validate the current no-effect Laya reference policy.

The visual query/depth proxy and simulator collision-AABB center are different
position definitions. Their numerical discrepancy is currently marked incomparable,
not labeled localization error. Current visibility, contact, holding and task progress
are unknown unless their evidence source actually supports them. Tracking is inactive;
visual covariance and semantic scores are uncalibrated.

An initial replay exposed Laya input truncation. The replacement compact presentation
is token-audited, rejects clipping, and records actual consumed tokens. Earlier
truncated replay artifacts are retained but cannot support full-interface claims.
See [the interface handoff](decision_interface_handoff.md) for measurements.

## Proposed E0, conditional on review — not frozen or run

First pass a **reference-quality pilot**, approximately 12 phase-diverse states from
the verified collection trajectory. Agree on one target-position referent and on
independently evaluated reasonable action sets. Simulator preview may label actions
offline but must not filter the probe set or enter the no-effect decision input.
Check whether oracle-conditioned decisions respond usefully to progress/contact and
whether good decisions are identifiable without effects. If not, either study
descriptive oracle-conditioned fidelity with a narrower claim, or separately approve
a fixed-effect reference condition. Do not silently convert a State Gap study into
State Gap plus Effect Gap.

The smallest proposed formal E0 after this pilot:

- Task: `KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet`, LIBERO `libero_90`.
- Initial-state IDs 0–4, seed 1, with benchmark-state and trajectory hashes. Only
  init 0 collection is verified today; collectors for the other four must first
  be validated independently of the compared model outputs.
- Twelve predeclared boundaries per trajectory: two each for far, approach,
  near-contact, contact, closure progress, near-completion. Define phase rules and
  minimum temporal spacing using evaluator telemetry before selection; preserve
  missing phases and failures instead of replacing trajectories until successful.
- Approximately 60 physical boundaries, each with fresh and 0.4-s-old archived
  sensor history: at most 120 paired records. The age is simulation time, chosen
  from one existing atomic action duration, not from observed method rankings.
  Capture/history replay must supply observations throughout the collection, not
  just at the five sparse smoke boundaries. No artificial occlusion condition yet.
- One fixed 11-token semantics-only probe set, same order, same question, same last
  robot outcome, empty effect bundle on both branches. These are offline choices,
  not execution authorization. Record natural candidate availability separately.
- One local Laya content revision/API/config/presentation for both branches, Rule as
  a deterministic reference. Three alternating-order repeats on every branch; seed
  once per run rather than resetting before each call. Log actual device and tokens.

Primary metrics: top-1 agreement; top-2-set agreement with ties explicit; Jensen–
Shannon divergence in nats using normalized returned probabilities; oracle margin
`p1-p2`; decision latency; same-input variability. Preserve raw rounded probabilities.
Condition results on phase, actual age, missingness and natural candidate availability.
Use position/relation error only for genuinely comparable referents. Candidate-set
agreement is unknown when an oracle natural set has not been collected.

First sensitivity families: target position **and coherently recomputed relations**;
remaining-opening missingness; contact missingness; age/validity; covariance. Literal
single-field counterfactuals can intentionally leave inconsistent relations, but must
be labeled accordingly. Model-facing numeric precision and inclusion/exclusion of
provenance are themselves frozen interface choices, not invisible implementation details.

Report per-initial-state/trajectory results. Frames and repeat calls are correlated,
not independent sample size. Five trajectories are a small first benchmark with
limited uncertainty estimates; do not interpret non-significance as equivalence.
Freeze code, model bytes, task assets, initial states, collection/phase selection,
reference-point definition, candidate vocabulary, question, history, numeric
presentation, temporal config, delay delivery and metrics before formal collection.

No E0 freeze or formal collection is authorized by this document. Current readiness
and next human gate are maintained in [current_state.md](current_state.md).
