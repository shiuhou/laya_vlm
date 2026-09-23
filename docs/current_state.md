# Verified current state

Reviewed 2026-09-23. This index supersedes historical plans, not raw evidence.
Implementation/evidence baseline: **`f8064688f84b0c7dffbcf6b8dc89fb64d1c59779`**
(live visual demo), including research diagnostics at `3be0fc5`. The documentation
alignment on top changes no implementation or experimental conclusion. Use
`git rev-parse HEAD` for the exact checkout/documentation commit.
Experiment status: **bounded diagnostics only; no formal E0/E1 or freeze tag**.

## Branches and collaboration

Current branch: **`share_main`**. At this review, local `master` also points to
`f806468`; `origin/master` and `origin/share_main` are present as local remote-tracking
refs, with `origin/HEAD -> origin/master`. No fetch or server/default-branch change
was performed. `research/decision-interface` and `feat/mujoco_demo` are recommended
future branches, absent from the inspected refs. No branches were created, renamed
or deleted by this documentation alignment.

Read [development_tracks.md](development_tracks.md) for track responsibilities,
shared components and integration rules. [research.md](research.md) remains the
single research-direction document; historical handoffs are revision-specific.

## Evidence entry points

Latest research report: [reference_gate_handoff.md](reference_gate_handoff.md).
Latest engineering-only artifact: [live visual demo](engineering_demo.md), after
baseline `3be0fc5`. Four actual Laya choices drove GRASP/RELEASE commands; all 32
recorded controls replay exactly. No task success; no change to the research gate.
Prior interface search: [interface_search_handoff.md](interface_search_handoff.md).
Mechanism report: [reference_mechanism_handoff.md](reference_mechanism_handoff.md).
Previous pilot: [reference_pilot_handoff.md](reference_pilot_handoff.md).
Predeclared pilot and correction: [reference_pilot_protocol.md](reference_pilot_protocol.md).
Conditional next experiment: [research.md](research.md).

## Track A — verified engineering demonstration

- Real RGB-D → temporal belief → compact CDS → Laya → validation → atomic executor
  → MuJoCo execution. The opt-in demo bridge leaves the legacy runner and research
  pairing interface unchanged.
- Four choices, GRASP/RELEASE/GRASP/RELEASE, each from ten natural feasible tokens;
  no forced singleton, fallback, clipping or contract violation. Actual gripper
  movement, 32 controls and video are recorded. Control replay matches 37 boundaries
  exactly; it is not a second independent model-driven rollout.
- **No drawer movement or task success.** Sensing is synchronous with simulation
  paused; this is not asynchronous robustness evidence. Visual model inputs contain
  no oracle target/contact/progress or candidate effects.

## Shared foundations and Track B tooling

- Stage 1/2 atomic, fusion, visual validity, isolation and durable-record tests
  remain passing. Legacy live runtime behavior is not silently changed.
- Offline CanonicalDecisionState v0.1 and separate CandidateEffectBundle remain;
  primary replay has shared 11-token semantics-only candidates and **no effects**.
- Research-pilot referent **v0.2**: visible-pixel-weighted foreground top-handle surface
  centroid. Sensor uses its own approximate bbox support/RGB-D. Oracle uses
  independent first-hit visual-mesh rays at calibrated raster centers. No oracle
  membership corrects perception. Raw old AABB and bbox-depth proxies survive.
  The live demo still uses the existing query-box/interior-median-depth estimator;
  it must not be described as running the pilot's common-referent estimator.
- Twelve phase-diverse init-0 states plus three pairs each on init 1/2 were
  collected at exactly matched physical boundaries. All 18 raw sensor/oracle
  centroid readouts reproduce; all 18 snapshot restorations/STOP replays have
  zero recorded error. Init-0 full-control replay error remains `1.272e-11`.
- Final Rule/Laya replay: 144 decisions, 72 complete paired comparisons, three
  repeats per input. All 72 Laya calls fit the checkpoint, with stable consumed
  tokens, choice and returned probabilities. No probe choices control collection.
- Three actual benchmark resets (0,1,2), fixed seed 1, with the external recorded
  collector: each yields approach, contact and progress. Only collector init 0
  completes; this is **not Laya task success**. Init 1/2 finish at 29.879/15.696 mm
  remaining opening; lack of near-completion coverage is preserved.
- 244 tests, ruff and compileall pass. Dependencies, upstream repositories and
  model weights were not changed or downloaded.

Verified runtime versions: Python 3.10.21, MuJoCo 3.5.0, robosuite 1.4.1,
NumPy 1.26.4, torch 2.2.0, transformers 4.57.3, laya 0.3.4. Commands and local
model hashes are in the linked evidence reports. Compact canonical probes and the
demo audit model tokens; this does not retroactively validate legacy/truncated inputs.

## Track B — scientific result and limitations

Latest bounded evidence: **212 offline calls**, all repeated inputs stable and
unclipped. Three archived oracle/perceptual status pairs isolate missing
articulation: correct oracle CONTINUE at open/intermediate states becomes DONE
when that field is unknown. Oracle-field masking exactly reproduces perceptual
payloads and outputs. Adding an explicit UNKNOWN answer in a separate diagnostic
resolves the tested missingness cases without breaking known-state judgments.
This is a finite status-reference result, not perception accuracy or robot control.

Candidate-attached qualitative effects pass an eight-contrast synthetic goal/
assignment/order test; equivalent state-side tables do not. Transfer to four
actual loaded contexts with all eleven actions fails: true effects yield no
incrementally useful choices in original order and only one of eight under
reversed order. Coarse absolute-change categories also omit distinctions needed
by STOP-relative utility. No paired manipulation E0 follows the failed gate.

Latest interface search: **744 bounded offline model calls**, no future effects
or action execution. A spatial sentence + neutral candidate IDs passes simple
single-axis approach tests but fails mixed geometry and goal reversal (archived
oracle nominal labels: 1/18). A precomputed dominant-axis projection scores 25/25,
but already performs the decision in code and has physical local support at only
9/18 archived boundaries. It is an explicitly answer-equivalent control, not a
replacement decision state.

A narrower positive result: `observed articulation category + requested category`
rendered as two short sentences yields correct DONE/CONTINUE judgments on all six
combinations, both option orders, repeated twice. This is goal-sensitive task
progress classification, **not a full-task action reference or a deployed policy**.
Its oracle articulation category is unavailable to current perception. All 372
same-fixture repeat comparisons are stable and unclipped. No new CDS promoted.

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
reference.** In the original twelve-state reference pilot, all choices are
GRASP/RELEASE; most RELEASE probes equal STOP
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
Latest research artifacts: `runs/reference-gate/{status,consequences,abstention,physical}-v01/`.
Latest engineering artifact: `runs/engineering-demo/top-drawer-init0-seed1-v01/`.
All are local/ignored, not included in a fresh clone; share their manifests and
referenced artifacts separately. See the collaboration guide's evidence handoff rules.

Geometric reference comparable: **YES**, under the stated camera/visibility definition.
Bounded known-state status judgment: **YES**, only for the tested finite interface.
Reference state usable as a **validated useful manipulation-decision reference: NO**.
Multi-init collection viable: **YES**, with incomplete near-completion coverage.
Ready to freeze `exp-e0-v0`: **NO**. Ready to run formal E0: **NO**.

Smallest next tests: validate explicit UNKNOWN status outputs and obtain a
legitimate sensor-derived articulation estimate for anything beyond the observed
missingness effect. For manipulation, isolate effect binding from native action
semantics at fixed option count, and expose STOP-relative effects if incremental
utility is the objective. Full atomic-policy E0 still lacks a competent reference;
do not silently rename the narrow status result as that experiment.
Do not silently settle loaded states or waive reset-envelope violations. Do not insert effects
into the no-effect comparison, tune gates, or expand the benchmark without review.
