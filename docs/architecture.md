# Decision evidence interfaces

```text
ObservationEvent -> BeliefSnapshot -> CanonicalDecisionState
                                      + Candidate Set
                                      + CandidateEffectBundle
                                      + one recent actual outcome
                                    -> DecisionProvider -> validation -> AtomicExecutor
```

The last two steps execute only in the existing Stage 2 live path. The new canonical
path is currently an **offline, diagnostic decision probe**: its outputs cannot
drive the paired-state collector. Stage 2 live validity/execution contracts remain
unchanged. We do not claim the compact interface has passed closed-loop validation.

## Roles

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

Canonical v0.1 accepts the fixed shared atomic offline probe vocabulary only. It
rejects embedded metadata, free-form oracle preview descriptions, risk scores or
alternative candidate semantics. Existing natural live candidates are recorded
separately; a probe's feasibility flag means inclusion in a question, not safe execution.

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

The separate `experiments.interface_search` diagnostic deliberately does not
require the canonical schema. It compares smaller numeric/categorical/sentence
projections, candidate presentations and typed question scopes without changing
the runtime. Future effects remain absent. Its dominant-axis projection and
hand-written applicability criteria are explicitly policy-bearing controls,
not proposed belief fields. The observed/requested articulation classifier is
an offline status judgment; DONE/CONTINUE must not be mapped to physical STOP
or execution without a separately validated controller. See the
[search handoff](interface_search_handoff.md) for evidence and claim boundaries.

LIBERO/MuJoCo provide physical execution and evaluator state. Jev-LIBERO supplies the
World/controller adapter, oracle preview and the existing recorded collection trace.
Show-Harness inspires atomic token names, not an imported controller. LocateAnything
localizes queries; depth supplies metric projection. Laya is one replaceable typed
decision backend. `QueryTrackManager` exists but remains inactive.

Runs use the existing fsynced, hash-chained recorder. Paired replay and its independent
summary CLI preserve missing outputs, validate identities, and recompute metrics from
raw decisions rather than trusting cached diagnostic rows. No statistical conclusion
follows from a smoke comparison.
