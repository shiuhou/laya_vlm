# Decision evidence interfaces

Implemented architecture of the integrated baseline; see [collaboration rules](development_tracks.md).
This diagram separates concepts; the entry-point table below identifies which
paths currently execute model decisions and which only replay them offline.

```text
ObservationEvent -> BeliefSnapshot -> CanonicalDecisionState
                                      + Candidate Set
                                      + CandidateEffectBundle
                                      + one recent actual outcome
                                    -> DecisionProvider -> validation -> AtomicExecutor
                                    -> physical execution -> fresh ObservationEvent -> ...
```

The primary canonical research path remains an **offline diagnostic decision probe**:
its outputs cannot drive the paired-state collector. An opt-in
[engineering demo](engineering_demo.md) now bridges the same compact fields and
nominal semantics to the existing live validity/validation/execution path. It
preserves natural feasible tokens and supplies no effects. This demonstrates
auditable embodied execution, not task competence or closed-loop research validation.
The non-oracle visual loop and two-step asynchronous smoke predate the demo branch.
The engineering objective is sustained task-directed feedback and measurable task
progress. Laya chooses atomic tokens; deterministic controllers own motor commands.
The [feedback audit](evidence/demo/closed_loop_demo.md) links execution endpoints to new RGB-D,
admitted observations, used fusion evidence and the next audited input. It distinguishes
candidate-gate changes from evidence of model sensitivity; it does not change CDS,
model questions, history, effects, candidate semantics or execution authorization.
The Stage 2 runner and validity/execution contracts remain unchanged.

## Active paths and their boundaries

| Entry point in `embodied_runtime.experiments` | Role | Model/execution boundary |
|---|---|---|
| `privileged_reference` | Explicit oracle drawer reference, preflight, report and replay | Native Jev 27-action preview; union of collision-aware task-effect contracts; original two-step witnesses only after an empty one-step union; genuine multi-option Laya call; execute one chosen first primitive; actual outcome to next input. No hierarchy or visual/CDS changes. |
| `two_step_lookahead_audit` | Frozen-snapshot audit of original Jev reversible witnesses | Replays the exact dead-end state, invokes unchanged original search, enumerates all qualifying pairs, checks full restoration and verifies the reference produces the same witness pool; no model or live policy episode. |
| `engineering_demo` / `demo_report` / `demo_inspector` / `demo_feedback` | Track A live demo, feedback audit and raw-derived media | Fresh synchronous RGB-D; compact CDS; natural permitted token subset; no effects/history; Laya choices pass live validation and execute; next-input audits expose gate changes and task outcomes; optional final sensing executes no further action |
| `collect_pairs` / `replay_equivalence` | Track B source collection and paired decision replay | Source controls are external/recorded, not selected by replay decisions; primary oracle/perceptual comparison shares semantics-only candidates/history and no effects |
| `interface_search` / `reference_gate` / `effect_binding` / `provider_comparison` / `clause_order` / `goal_placement` / `selective_grip` / `explicit_consequence` | Track B bounded capability/missingness diagnostics | Alternate projections and explicitly labeled diagnostic conditions, never a silently deployed replacement policy |
| `run_libero` | Legacy Stage 2 live smoke path | BeliefSnapshot presentation, optional asynchronous visual worker or explicitly oracle preview branch; not the demo's compact audited path |

The shared implementation map is in [development_tracks.md](development_tracks.md).
Track wrappers may differ in schedule, question, history and candidate selection;
shared classes alone do not establish a matched scientific comparison. Simulator
execution/evaluation telemetry is separate from visual decision evidence in both
tracks. Only explicitly privileged diagnostics may supply oracle states/effects.

## Integration checkpoint: candidate processing remains an open question

The 2026-09-23 integration preserves all interfaces above. The legacy nonvisual
runner still constructs `PhysicsPreviewCandidateBuilder`, which calls
`World.predict_all()` and Jev contracts. Its predicted success/contact/approach/force
descriptions are privileged. The visual path uses `VisionCandidateBuilder` instead;
it computes validity and soft geometric metadata, but the compact demo passes only
permitted nominal candidate descriptions, with no effect bundle. The primary
State-Gap replay likewise keeps effects empty.

Thus oracle preview was isolated from those decision paths, not deleted from the
repository. Whether this also left too much geometry/consequence matching to the
model is an open architectural question, not a demonstrated causal explanation.
The review asks what code should compute before model judgment. It does not approve
restoring preview, preselecting a winner or promoting diagnostic anonymization,
candidate ordering or local-objective text to shared defaults.

Candidate effects retain distinct sources: `oracle_sim`, deterministic `geometry`,
`learned`, and `unknown` (or an empty bundle when none is supplied). Geometry derived
from oracle inputs is still privileged. Supporting a source label does not establish
a validated learned predictor. See [integration_checkpoint.md](archive/historical_handoffs/integration_checkpoint.md)
for history, claim boundaries and alternatives to review; no redesign is implemented.

## Roles

The human-authorized [privileged reference v1](evidence/decision_interface/privileged_reference.md)
uses the existing BeliefStore with an audited compact oracle presentation,
not CanonicalDecisionInput. Runtime's optional executor argument defaults to the
original AtomicExecutor; this reference injects a Jev-native AtomicExecutor
adapter. The preview builder's explicit action mapping opts into the 27 primitives
without legacy STOP/DONE additions. Candidate metadata declares oracle_sim,
privileged=true and task_specific_effect_contract_union. Contracts implement
part of candidate-policy filtering, not only hard validity; this attribution is
part of the reference definition. If that union is empty, the opt-in reference
uses original Jev two-step witnesses as `reposition` evidence. Each witness proves
a second primitive can satisfy an existing combined contract; it does not authorize
that second primitive. Laya chooses among witness-backed first actions, only one
first primitive executes, and the next decision uses the real endpoint. All
defaults outside this opt-in path remain. If the complete admitted pool has one
token, the reference executes that token once as `forced_singleton`, records no
model probabilities and does not call or credit Laya. A pool with two or more
physically distinct actions reaches Laya. Zero candidates after lookahead fail
closed. Every execution is followed by a real observation and fresh candidate build.
For a local-objective witness pool, the model-facing serializer binds numbered
effect rows to the unchanged canonical question-option order and factors common
metadata once. It does not rank, prune, merge or reorder candidates. The raw
`reference_preview` record retains every full-precision prediction and witness;
the compact view retains the previous rounded model-visible fields. One-step and
flat presentations remain unchanged. Token audit still fails closed before inference,
and the recording hook verifies the model consumed exactly the audited token IDs.
With a 200-primitive execution ceiling, this implemented path reached official
success in three fresh runs at primitive 122; the ceiling changes termination only,
not any decision or execution contract.

`BeliefSnapshot` remains generic temporal estimation: position/velocity/covariance,
semantic evidence, capture/reference times, age, validity, consistency and provenance.
It is not a task-specific universal world state. `project_belief` accepts only this
snapshot plus target query, has no simulator/backend argument, and applies the visual
field guard.

`CanonicalDecisionState` is a deterministic projection. `project_oracle` produces a
separate diagnostic state, preserving matched robot/task fields and marking oracle
facts explicitly. Oracle evaluation never back-fills the perceptual state.

## CanonicalDecisionState v0.1

The serialized shape is:

```text
version: canonical-decision-state-v0.1
meta: branch, belief_id, revision, asof_sim_time, oracle_source when applicable
fields:
  <field.name>: {value, source, basis, privileged}
```

`source` is one of unknown, sensor, proprioception, task, derived, oracle_sim.
Unknown requires `value=null`. Derived relations/effects retain oracle privilege when
their inputs are privileged. Audit metadata is excluded from model features.

| Field family | Available perceptual/proprioceptive values | Oracle branch |
|---|---|---|
| task | instruction and query identity | identical supplied context |
| robot | world TCP XYZ; joint-opening width; retained OPEN/CLOSED command | identical robot information |
| target | fused world position/velocity with explicit measurement referent | same referent in the new pilot; legacy AABB remains distinct; velocity unknown |
| relations | target minus TCP XYZ, norm, XY norm, signed Z error | same formulas on oracle target |
| interaction | contact unknown; holding unknown unless legitimately observed | measured simulator target-contact boolean; shared legitimate holding |
| progress | remaining opening unknown | simulator remaining_open_mm |
| quality | geometry age/validity/covariance; calibrated flag; semantic age/validity/score; consistency | instantaneous geometry reading/age; sensor covariance and semantic confidence unknown |

Current visibility is unknown on both branches: a historical detection does not
establish current visibility. TCP orientation/velocity and target-progress histories
are deliberately not included in v0.1. Source IDs in the paired record link the compact
state to full belief/event/camera records and separate simulator evaluation records.

The reference-quality collector uses referent v0.2: pixel-weighted visible top-handle
surface centroid, with `(u+.5,v+.5)` raster centers. Its sensor-only bbox/RGB-D
estimator enters a fresh isolated fusion stream; its oracle uses independent
first-hit visual-mesh rays. Legacy bbox-median and collision-AABB values are retained,
not renamed. This view-dependent centroid is not a rigid grasp point; its filtered
velocity is point-estimate velocity, not independently measured rigid-body velocity.
Independent full-snapshot atomic previews assess outputs but never enter the
no-effect model input. See the reference pilot handoff for operating-envelope limits.

`state.intervene({...}, label=...)` performs only named field replacements and records
the parent state ID. It does not silently recompute dependent relations. This supports
both coherent family interventions and explicitly inconsistent counterfactuals.

## Candidate semantics and effects

Canonical v0.1 accepts the fixed shared atomic semantics, including a permitted
subset used by the opt-in demo. It rejects embedded metadata, free-form oracle
preview descriptions, risk scores or
alternative candidate semantics. Existing natural live candidates are recorded
separately; a probe's feasibility flag means inclusion in a question, not safe execution.
The demo takes its permitted subset from the existing visual gate and binds the
model response back to the original live snapshot for validation. It does not use
the unrestricted eleven-token research probes as execution authorization.

```text
CandidateEffectBundle:
  version: candidate-effects-v0.1
  candidate_set_id
  effects[token]:
    source: geometry | oracle_sim | learned | unknown
    privileged: boolean
    values: supported candidate-local consequences only
    assumptions / state_id / geometry_valid when applicable
```

Tier-0 translations predict signed **after-minus-before** distance and XY-error
change assuming a stationary target and exact nominal 10 mm motion. This is kinematic
arithmetic, not contact/dynamics or collision prediction. Unsupported rotations,
grasp outcomes, task progress and clearance remain unknown. Geometry effects derived
from oracle geometry remain privileged.

The oracle adapter can explicitly package Jev preview closure, surface-gap reduction,
contact and obstacle-force outputs. No previews were supplied in the primary smoke.
`CanonicalDecisionInput` rejects privileged states/effects unless `diagnostic_only=True`.
The State-Gap replay requires an empty effect bundle. A later Effect-Gap probe can
hold one perceptual state/candidate set fixed and change bundles via the same input
class, but is not part of the current primary replay CLI.

## History, pairing and model presentation

History is at most one previous actual outcome: action/control, proprioceptive TCP
displacement, elapsed simulation time and retained grip. Simulator object/contact/
success telemetry cannot be inserted via this history allowlist. Recorded controls
used by collection are explicitly labeled, not mislabeled as runtime atomic actions.

Experimental identity includes task/binding, benchmark `init_state_id` and state hash,
seed, trajectory hash, control boundary, simulator-state hash, source belief and pair
hash. Projection time equals the physical boundary on both branches; visual capture
may be older, and its age is explicit. Collection checks simulator immobility during
perception and replay agreement against every archived state for the original init.
Transferred controls on other benchmark resets have their own physical identities;
they are not expected to match init 0's archived states.

The model presentation `compact-v0.1` uses values/nulls, quality and effects/history;
full field source/basis/privilege stays in the audit record, not in the model prompt.
Numbers use six significant digits, with raw precision retained. Key order is fixed.
Candidate meanings appear once in compact question criteria. Auditable identities
include both logical payload hashes and actual Laya token IDs/hashes.

Laya's installed API budgets the heading/options and state separately. The adapter
audits its actual tokenizer/sequence builder and fails before inference if any state,
heading or option is clipped. It does not enlarge the checkpoint context or alter
dependencies. Unsupported agents without a tokenizer/config report audit unavailable.
The older `audit-json-v0` presentation is retained only for interpreting old records.

## Dependencies and evidence

Offline diagnostic runners retain their alternate projections, presentation
interventions and source identities. They do not change the shared CDS or live
policy. The [research evidence index](research.md) records each intervention and
its limitations; the protocols remain byte-identical historical specifications.

LIBERO/MuJoCo provide physical execution and evaluator state. Jev-LIBERO supplies the
World/controller adapter, oracle preview and the existing recorded collection trace.
Show-Harness inspires atomic token names, not an imported controller. LocateAnything
localizes queries; depth supplies metric projection. Laya is one replaceable typed
decision backend. `QueryTrackManager` exists but remains inactive.

Runs use the existing fsynced, hash-chained recorder. Paired replay and its independent
summary CLI preserve missing outputs, validate identities, and recompute metrics from
raw decisions rather than trusting cached diagnostic rows. No statistical conclusion
follows from a smoke comparison.
