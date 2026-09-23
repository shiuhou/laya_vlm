# Verified current state

Reviewed 2026-09-23. This index supersedes historical plans, not raw evidence.
Previous shared baseline: **`eddbcde04649419d8d5d44e62e433882578328eb`**, including the live
demo at `f806468` and research gate at `3be0fc5`. This integration combines research
commit `84cd781` and demo commits `84abdb8` / `59dae8a`. Research adds the
[fixed-option effect diagnostic](effect_binding_handoff.md) and
[independent-provider comparison](provider_comparison_handoff.md), followed by the
[STOP-clause order diagnostic](clause_order_handoff.md) and the
[Laya goal-placement diagnostic](goal_placement_handoff.md), then the
[selective grip-description diagnostic](selective_grip_handoff.md) and the
[explicit-consequence diagnostic](explicit_consequence_handoff.md); their manifests
record working-source hashes. Demo instrumentation, feedback and subsequent frozen
diagnostics are also integrated. Use `git rev-parse HEAD` for the exact integration
checkout. Historical run identities remain unchanged; merging does not rerun them.
Experiment status: **bounded diagnostics only; no formal E0/E1 or freeze tag**.

## Branches and collaboration

Integration target: **`laya-embodied-runtime` on `share_main`**. Separate worktrees
remain `laya-decision-interface` on `research/decision-interface` and
`laya-mujoco-demo` on `feat/mujoco_demo`. Relevant working changes were committed
on their own tracks before merging research, then demo, with normal merge history.
No remote update, branch rename or new model experiment accompanies integration.

Read [development_tracks.md](development_tracks.md) for track responsibilities,
shared components and integration rules. [research.md](research.md) remains the
single research-direction document; historical handoffs are revision-specific.
The [integration review](integration_checkpoint.md) records merge scope, verification,
architectural history and options for review. It authorizes no next experiment.

## Evidence entry points

Latest research report: [explicit_consequence_handoff.md](explicit_consequence_handoff.md).
Prior selective-grip report: [selective_grip_handoff.md](selective_grip_handoff.md).
Prior goal-placement report: [goal_placement_handoff.md](goal_placement_handoff.md).
Prior clause-order report: [clause_order_handoff.md](clause_order_handoff.md).
Prior provider comparison: [provider_comparison_handoff.md](provider_comparison_handoff.md).
Prior effect-binding diagnostic: [effect_binding_handoff.md](effect_binding_handoff.md).
Prior status/consequence gate: [reference_gate_handoff.md](reference_gate_handoff.md).
Latest engineering-only artifact: [embodied feedback audit](closed_loop_demo.md),
on baseline `84abdb8` plus recorded working-source hashes. Eight Laya choices,
nine sensor captures and seven verified feedback deliveries still produce zero
drawer progress. All 64 controls replay exactly at 73 checked boundaries.
One GPU-memory startup failure was retained before the completed episode.
The [four-action inspector milestone](demo_runbook.md) is preserved.
The [original live visual demo](engineering_demo.md) remains historical evidence.
No task success; no change to the research gate.
Latest engineering diagnostic: [negative-direction option ordering](synthetic_negative_order_probe.md).
The [decision autopsy](decision_autopsy.md), [distance effects](frozen_step0_distance_effects.md),
[local objective](frozen_step0_local_objective.md), [translations-only](frozen_step0_translations_only.md)
and [synthetic direction](synthetic_direction_probe.md) reports retain their bounded,
offline scope. None is a new live policy or a task-completion result.
Prior interface search: [interface_search_handoff.md](interface_search_handoff.md).
Mechanism report: [reference_mechanism_handoff.md](reference_mechanism_handoff.md).
Previous pilot: [reference_pilot_handoff.md](reference_pilot_handoff.md).
Predeclared pilot and correction: [reference_pilot_protocol.md](reference_pilot_protocol.md).
Conditional next experiment: [research.md](research.md).

## Track A — verified engineering demonstration

- **Goal:** sustained task-directed embodied decisions and measurable task progress.
  The real non-oracle RGB-D → LocateAnything → fusion/belief → Laya → executor path
  and a two-step asynchronous smoke predate this branch. This work makes existing
  capability reproducible and auditable; it does not create the first embodied loop.
  Connectivity is an achieved milestone, not the complete engineering objective.
- Latest episode: eight genuine GRASP/RELEASE decisions; fresh observations and
  used fusion evidence reach all seven subsequent Laya decisions. Optional final
  sensing adds no action. All six translations remain available, but none is chosen.
  Every choice change coincides with veto of the previous choice. Updated inputs
  and output alternation therefore do not isolate useful model sensitivity.
  **No task-directed progress; the next engineering milestone remains unmet.**
- Demo-specific live console and offline HTML inspector now expose the full chain,
  including raw-response/proposal and executor/trajectory agreement, forced choices,
  fallbacks, missing outcomes and evaluator-only measurements. Shared runtime,
  interfaces, gates, providers and executor semantics are unchanged. The new run
  has eight verified Laya executions and zero replay error across 73 boundaries.
  Pre-merge demo verification: 266 tests, ruff and compileall passed.
- Real RGB-D → temporal belief → compact CDS → Laya → validation → atomic executor
  → MuJoCo execution. The opt-in demo bridge leaves the legacy runner and research
  pairing interface unchanged.
- Earlier four-action milestone: GRASP/RELEASE/GRASP/RELEASE, each from ten natural feasible tokens;
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
- Integrated verification: **384 tests passed**, ruff and compileall passed.
  Pre-merge research verification was 362 tests. Dependencies and upstream repositories are
  unchanged. One pinned independent Qwen checkpoint was acquired separately;
  existing model weights were not modified.

Verified runtime versions: Python 3.10.21, MuJoCo 3.5.0, robosuite 1.4.1,
NumPy 1.26.4, torch 2.2.0, transformers 4.57.3, laya 0.3.4. Commands and local
model hashes are in the linked evidence reports. Compact canonical probes and the
demo audit model tokens; this does not retroactively validate legacy/truncated inputs.

## Track B — scientific result and limitations

Latest bounded evidence: **128 Laya calls**, replacing only the generic question
on selective goal-last fixtures with the explicit desired conjunction: `opening
decreases, vs STOP lower, and obstacle no` for closing; `increases/higher` for
opening. All 64 repeat pairs and 64 archived controls match raw scores exactly.
Only **2/32 choices** change, with no corrections and one lost success. True utility
falls **5/16 → 4/16**: closing **0/8**, opening **4/8**. Shifted fact correctness
stays **1/8 closing, 8/8 opening**. Appropriate goal reversal stays **1/16**;
both-assignments correctness falls **5/16 → 4/16**; both-orders correctness remains
**5/16**, all opening. Opening consequences still dominate **24/32** choices,
including **12/16 closing requests**. Explicit criteria do not materially help;
the failure also exists in desired-consequence-to-candidate matching under this
presentation. An upstream-only goal-transformation explanation is weakened.
All 32 question changes affect logits/probabilities, so this is not a zero-effect
intervention. Inputs increase 336 → 344 tokens, without clipping; all other model
input fields remain identical. All 32 explicit choices retain contract flags.
No new provider, physical field, effects, controller or live change. Finite matching
gate FAIL; useful reference/E0 remain NO.

Prior bounded evidence: **128 Laya calls**, replacing only native GRASP/RELEASE
description prefixes with `intervention` on the 32 goal-last native fixtures, with
all matched controls and variants repeated twice. All 64 repeat pairs and 64 archived
control comparisons match logits/probabilities exactly. True-effect utility improves
**0/16 → 5/16**, entirely for opening; true closing remains **0/8**. Appropriate goal
reversal improves only **0/16 → 1/16**; effect-reassignment pairs correct under both
assignments improve **0/16 → 5/16**, all opening requests. No boundary/assignment
passes both goals under both option orders. RELEASE selections fall 20/32 → 3/32,
but GRASP rises 8/32 → 23/32: combined grip selection remains 26/32. Opening bundles
dominate 25/32 choices, including 12/16 closing requests. The two descriptions
contribute, but their removal exposes a remaining directional preference rather than
reliable goal binding. Inputs shorten 344 → 336 tokens without clipping; this does
not isolate lexical meaning from length/position. All 32 transformed first-repeat
choices retain contract flags. No new provider, field, effect or live change.
Useful reference/E0 remain NO.

Prior bounded evidence: **256 Laya calls**, moving only the unchanged requested-goal
sentence after all rules, with all 64 original and 64 transformed fixtures repeated
twice in one session. Every original control reproduces its archive; all 128 repeat
comparisons match raw logits/probabilities. Token multisets/counts and option markers
are unchanged. Placement changes 25/64 choices, but native true-effect utility stays
**0/16**. Anonymous true utility improves **9/16 → 11/16**, and appropriate paired
goal/consequence/action reversal improves **2/32 → 6/32**, all anonymous. No context/
assignment passes both goals under both option orders. Anonymous opening selections
fall **30/32 → 22/32**; effect-reassignment pairs with both choices correct stay
**8/32** overall. Native opening requests now select RELEASE **16/16**, including
eight shifted cases with explicitly closing effects. This strengthens a specific
gripper-wording interference hypothesis while broader integration remains unresolved.
61/64 transformed choices retain execution-contract flags. No Qwen inference,
new physical fields or live changes. Useful manipulation reference/E0 remain NO.

Prior bounded evidence: **264 new calls** on the same frozen full-effect fixtures,
changing only the final STOP-rule closed/open clause order on both existing providers.
Clause order changes 23/64 Laya and 2/64 Qwen choices, but anonymous opening-effect
selections remain dominant: **30/32 → 32/32** and **29/32 → 28/32**, respectively,
when closing moves last. Opening → closing switches occur in only 0/64 and 1/64
pairs. Native true-effect utility remains **0/16 Laya, 8/16 Qwen**; anonymous true
closing remains 0/8 for both. All 66 repeat comparisons per provider are exact,
including raw logits; unchanged controls reproduce the archives. A Qwen configuration
serialization-check failure occurred before inference and is preserved separately.
The final STOP-clause dominance hypothesis is weakened; stable order sensitivity
does not explain the broader failure to bind the goal to consequences. No reference
passes and no physical state fields, model settings or live interfaces changed.

Prior bounded evidence: **128 new Qwen2.5-7B-Instruct calls**, paired with the 128
archived Laya full-effect calls on exactly the same 64 logical fixtures. Native
true-effect utility improves from Laya 0/16 to Qwen **8/16**, but Qwen passes only
**3/32** paired goal reversals across all conditions. Anonymous true and reassigned
facts both score open **8/8**, closed **0/8**; 29/32 anonymous choices select
`increases / higher` facts. Reassignment changes 25/32 choices but both choices
follow their supplied facts in only 13/32 pairs. All outputs are valid, unclipped
and exactly stable across repeats, including vocabulary logits. The gate still
fails. Cross-provider failure strengthens investigation of goal/rule presentation;
it does not establish a specific cause or a need for more state. Frozen fixtures
are a sentence projection, not the full CDS serialization. No interface was changed.

Prior bounded evidence: **256 offline calls**, fixed eleven-option factorial on
the same four loaded contexts. With true absolute AND STOP-relative consequences,
native descriptions yield **0/16** locally supported choices; anonymous descriptions
yield **9/16**, comprising open 8/8 and closed 1/8. Anonymous full-effect choices
stay identical under goal reversal in 7/8 matched cases. Moving effect bundles
changes 15/16 anonymous full-effect action identities; across true/shifted bindings,
30/32 choices follow `opening increases / vs STOP higher`, regardless of goal.
This supports presentation-sensitive, inadequate goal-conditioned consequence
selection, rather than complete effect insensitivity or a missing STOP fact alone.
All 128 repeat comparisons are stable; all calls are unclipped. No native local
reference passes. Privileged effects remain confined to this offline diagnostic;
no new CDS or live policy is promoted. See the latest handoff for claim limits.

Prior bounded evidence: **212 offline calls**, all repeated inputs stable and
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

Historical baseline evidence remains in `laya-embodied-runtime`. Under its ignored
`runs/reference-pilot/`: `multi-init/`, `init{0,1,2}-raycast-v02/`,
`replay-init0-v02/`, `raw-referent-audit-v02/`. Old `init*-attempt1/`,
`replay-init0/`, and `raw-referent-audit-attempt1/` remain intact.
Older Stage 1/2/interface handoffs remain historical.
Prior research artifacts: `runs/reference-gate/{status,consequences,abstention,physical}-v01/`.
Prior engineering artifact: `runs/engineering-demo/top-drawer-init0-seed1-v01/`.
New research evidence remains in **`laya-decision-interface`**, starting with
`runs/effect-binding/factorial-v01/`,
including raw calls, manifests, a raw-derived report and fixture/contrast audit.
Prior: `runs/provider-comparison/qwen-v01/`, with full raw vocabulary logits,
report and audit; sibling `preflight-v01/` and `acquisition-v0{1,2,3}/` preserve
input preflight, pinned model acquisition, interrupted transfers and verification.
Prior: `runs/clause-order/{preflight-v01,laya-v01,qwen-v01,qwen-v02}/`, independent
`audit.json`/script and `matched_pairs.csv`. Full presentations and raw logits are
retained; Qwen v01 is a zero-inference harness failure, v02 the completed run.
New demo evidence remains in **`laya-mujoco-demo`**:
Latest completed engineering artifact: `runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/`.
Preserved startup failure: `runs/engineering-demo/top-drawer-init0-seed1-feedback-v01/`.
Earlier inspector artifact: `runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/`.
Subsequent frozen and synthetic diagnostic directories are linked from their reports.
All are local/ignored, not included in a fresh clone; share their manifests and
referenced artifacts separately. See the collaboration guide's evidence handoff rules.
The following research paths are relative to `laya-decision-interface`:
Prior: `runs/goal-placement/{preflight-v01,laya-v01}/`, independent `audit.py` /
`audit.json` and `matched_pairs.csv`. Full prompts, tokens, raw logits/probabilities,
all unchanged controls and working-source/model identities are retained.
Prior: `runs/selective-grip/{preflight-v01,laya-v01}/`, independent `audit.py` /
`audit.json`, `matched_pairs.csv` and `verification.json`. All original and selective
prompts/outputs, raw scores, source lineage and configuration checks are preserved.
Latest: `runs/explicit-consequence/{preflight-v01,laya-v01}/`, independent `audit.py`
/ `audit.json`, `matched_pairs.csv` and `verification.json`. Full matched prompts,
raw scores, token audits, source lineage and predicate equivalence checks are retained.

Geometric reference comparable: **YES**, under the stated camera/visibility definition.
Bounded known-state status judgment: **YES**, only for the tested finite interface.
Reference state usable as a **validated useful manipulation-decision reference: NO**.
Multi-init collection viable: **YES**, with incomplete near-completion coverage.
Ready to freeze `exp-e0-v0`: **NO**. Ready to run formal E0: **NO**.

## Integration stop point — architecture review before further experiments

Flat multi-candidate atomic ranking is under architectural review. Goal-last
placement and selective GRASP/RELEASE anonymization improved some bounded cases;
neither established useful goal/effect binding. Explicit desired-consequence
predicates failed to repair selection. Candidate ordering substantially affects
ranking: the demo's frozen swap changes GRASP to MV_BACK; a synthetic negative-axis
permutation corrects two of three errors but leaves -Y wrong. These observations
favor investigating decision-interface/candidate consumption over an explanation
based solely on missing raw physical state. They do not identify a unique cause.

Action-semantics/distance annotations did not make atomic choices reliably useful.
The local-objective intervention also added a contact premise and did not rescue
the choice; it is a diagnostic hypothesis, not accepted task decomposition.
Anonymization and reorderings remain offline manipulations, not canonical semantics.

The architectural question is what processing belongs between belief/world state
and Laya so the model performs judgment rather than low-level geometry, physics or
logical candidate matching. The earlier PhysicsPreviewCandidateBuilder /
World.predict_all() combined privileged facts with useful candidate processing.
It still exists in the explicit oracle path; isolation from visual/research inputs
must not be confused with deleting the implementation or proving that processing
unnecessary. Restoring oracle preview is not an approved solution.

Keep oracle_sim, deterministic geometry (`geometry`), learned prediction (`learned`)
and unknown/no effects distinct, with source and privilege propagated from inputs.
State Gap and Effect Gap remain separate. No scientifically defensible useful
manipulation reference has been established; formal E0 remains blocked.

The following historical next-test proposal is **on hold for architecture review**;
it is not authorized by this integration: candidate-by-candidate predicate verification.
Ask whether each unchanged candidate description/effect bundle satisfies the same
explicit desired conjunction, with neutral `satisfies` / `does not satisfy` answer
IDs, both answer orders and repeats. Cover both directions and all existing bundles,
including wrong-direction and mixed/neutral effects. Keep state/rules/model and
numeric predicate fixed. This separates recognizing predicate satisfaction from
selection among eleven competing candidates; it is a separate binary diagnostic,
not a new policy or validation of the original interface. Proposed, not run.
See the latest handoff for scope and interpretation limits.
No additional provider search or schema redesign is justified. The narrower status result still lacks a
sensor articulation estimator and broader UNKNOWN validation, but does not replace
the manipulation task. Full atomic-policy E0 still lacks a competent reference.
Do not silently settle loaded states or waive reset-envelope violations. Do not insert effects
into the no-effect comparison, tune gates, or expand the benchmark without review.
