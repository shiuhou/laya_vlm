# Verified current state

Reviewed 2026-09-23. This index supersedes historical plans, not raw evidence.
Latest stage: bounded reference-mechanism diagnostics after audit baseline
`0da1596`. Use `git rev-parse HEAD` for the exact final checkout revision.
Experiment status: **reference-quality pilot only; no formal E0/E1 or freeze tag**.

Current report: [reference_mechanism_handoff.md](reference_mechanism_handoff.md).
Previous pilot: [reference_pilot_handoff.md](reference_pilot_handoff.md).
Predeclared pilot and correction: [reference_pilot_protocol.md](reference_pilot_protocol.md).
Conditional next experiment: [research.md](research.md).

## Active and verified

- Stage 1/2 atomic, fusion, visual validity, isolation and durable-record tests
  remain passing. Legacy live runtime behavior is not silently changed.
- Offline CanonicalDecisionState v0.1 and separate CandidateEffectBundle remain;
  primary replay has shared 11-token semantics-only candidates and **no effects**.
- New referent **v0.2**: visible-pixel-weighted foreground top-handle surface
  centroid. Sensor uses its own approximate bbox support/RGB-D. Oracle uses
  independent first-hit visual-mesh rays at calibrated raster centers. No oracle
  membership corrects perception. Raw old AABB and bbox-depth proxies survive.
- Twelve phase-diverse init-0 states plus three pairs each on init 1/2 were
  collected at exactly matched physical boundaries. All 18 raw sensor/oracle
  centroid readouts reproduce; all 18 snapshot restorations/STOP replays have
  zero recorded error. Init-0 full-control replay error remains `1.272e-11`.
- Final Rule/Laya replay: 144 decisions, 72 complete paired comparisons, three
  repeats per input. All 72 Laya calls fit the checkpoint, with stable consumed
  tokens, choice and returned probabilities. No probe choices control collection.
- Three actual benchmark resets (0,1,2), fixed seed 1: each yields approach,
  contact and progress. Only init 0 completes. Init 1/2 finish at 29.879/15.696 mm
  remaining opening; lack of near-completion coverage is preserved.
- 211 tests, ruff and compileall pass. Dependencies, upstream repositories and
  model weights were not changed or downloaded.

## Scientific result and limitations

Latest bounded mechanism evidence: 29 boundaries across init IDs 0/1/2,
435 physical probes, exact restoration throughout. Native primary probes trigger
182/319 reset-envelope flags. Inherited orientation goals causally contribute to
STOP drift (step 144: 56–64 mm becomes 32–35 mm when reanchored), but do not explain
all of it. All 29 native STOP/RELEASE pairs are exact command/endpoint aliases.
No native semantics or uncertainty thresholds were changed.

Separately, 52 no-effect model calls show stable but inadequate instruction
following: both explicit token-selection sentinels fail, all eight nominal
approach fixtures fail, and order/alias changes alter choices. The checkpoint's
11-option temperature (~0.1006) greatly sharpens returned probabilities without
changing argmax. This is evidence of a model/interface competence mismatch as
well as incomplete physical semantics, not merely missing perceptual fields.
Privileged physical diagnostic evidence never enters these model controls.

**The current no-effect oracle-conditioned Laya is not validated as a useful task
reference.** All twelve choices are GRASP/RELEASE; most RELEASE probes equal STOP
because the retained command was already open. One GRASP reopens the drawer by
14.272 mm. Independent offered actions demonstrate useful closure at several
states. Lack of one-step utility does not rule out every preparatory strategy,
but matching this model is not yet evidence of useful decision sufficiency.

- Shared referent is coherent, not accurate perception: final init-0 fused point
  errors are 38–99 mm; late boxes include other handles. It is view/occlusion
  dependent, not rigid object pose. Ray/raster depth residuals and shared camera
  calibration assumptions are explicit.
- Oracle CDS remains a *partial* decision interface, not full controller state.
  The pilot samples low-level collector boundaries, sometimes in loaded/in-flight
  motion. Reset-calibrated execution envelopes flag 91/132 init-0 counterfactual
  probes, including large STOP drift at one state; these are not erased or called
  safety certificates. No hidden gripper actuation was observed.
- Tracking inactive; covariance/semantic scores uncalibrated. Perceptual contact,
  holding, task progress and unsupported visibility remain unknown.
- STOP-only natural availability follows the unobserved-velocity prior and
  uncalibrated covariance. No threshold change. Offline probes bypass natural
  filtering only for paired analysis, never live execution authorization.
- Original mismatched-reference and truncated artifacts remain historical.
  First pilot ID-render/integer-pixel artifacts are also retained as approximate,
  superseded reference evidence, not silently promoted to corrected results.

## Evidence and review gate

Under ignored `runs/reference-pilot/`: `multi-init/`, `init{0,1,2}-raycast-v02/`,
`replay-init0-v02/`, `raw-referent-audit-v02/`. Old `init*-attempt1/`,
`replay-init0/`, and `raw-referent-audit-attempt1/` remain intact.
Older Stage 1/2/interface handoffs remain historical.

Geometric reference comparable: **YES**, under the stated camera/visibility definition.
Reference state usable as a **validated useful-decision reference: NO**.
Multi-init collection viable: **YES**, with incomplete near-completion coverage.
Ready to freeze `exp-e0-v0`: **NO**. Ready to run formal E0: **NO**.

Smallest next test: a tiny, predeclared model/interface capability ladder
(explicit selection → signed relations → nominal geometric choice), alongside
validation of controller-conditioned intervention semantics. Descriptive fidelity
remains possible but is not a validated useful-reference experiment.
Do not silently settle loaded states or waive reset-envelope violations. Do not insert effects
into the no-effect comparison, tune gates, or expand the benchmark without review.
