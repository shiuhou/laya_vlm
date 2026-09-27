# Smallest fresh-reset retargeting trajectory probe

Proposal only, contingent on independently qualified current-support findings.
No new model call, geometry outcome or physics has been run for this proposal.
The [four fixed decision records](../evidence/autonomous_research/task2_postevent_slow_point_decision_findings.md)
all chose `MV_FWD` under stale support; a physical second decision is the earliest
opportunity to observe whether the resulting trajectories separate.

## Fixed comparison and budget

Use **two fresh benchmark init0/seed1 episodes** on the fixed relocated-bottle
scene, in cached-then-refreshed order. Retain both outcomes. This away fixture
asks about retargeting after relocation; it is declared now, not selected from
the forthcoming support results. The prior present/sham observations remain
available but do not require another pair of physical episodes for this question.

Both episodes regenerate the unchanged 29-action sensor-selected neck approach
from normal reset/settling, using live own observations and the existing original
approach rule/guard. Require the existing complete scientific-prefix verification
and non-executed approach STOP. Apply the same recorded +0.35 m away scene event,
including the existing forward/observation-refresh checks. No saved state or
archived control prefix initializes collection.

After the event, switch only the goal packet:

| Arm | Fixed post-event goal |
| --- | --- |
| cached | admitted historical whole-bottle hybrid POINT |
| refreshed | admitted post-event whole-bottle slow POINT |

Use the **same current-support packet** in both arms, chosen and source-qualified
before physical collection. The proposed primary packet is the current full-BOX
observed support from this exact away frame, using unchanged full-rectangle
projection. If the concurrent support studies do not qualify a common packet,
the physical trial is not released. Do not tune support or choose its definition
according to which arm it lets move. The support remains a partial observation,
not a scene safety certificate.

Require exact live post-event RGB/depth/K/T equality to the admitted stored
source before reusing the semantic goal/support. This permits **zero new model
calls**. Label it archived semantic output reused under exact input equivalence;
it does not measure live inference latency or continual visual model feedback.
Cached-hybrid versus refreshed-slow still changes observation and mode together.

Register at most **two existing approach moves per episode**. At boundary 0,
apply the existing rule/selector to the selected fixed goal and current own
packet. If it moves, execute the unchanged 10 mm primitive, capture its endpoint
and obtain the just-returned own packet. At boundary 1, recompute the same rule
and nominal endpoint guard from that own state; execute at most one more move.
Stop at the two-action budget after preserving the second endpoint. The maximum
post-event collection budget is four primitives / 32 controls / 800 native
integrations across both arms, excluding their separately verified prefixes.

Do **not** force or script a common first `MV_FWD`: current support may change
even the initial choices. Keep the source goal/support fixed during this short
interval and record their ages/unknown exact sample times. This tests one-time
retargeting followed by own-observation feedback, not object tracking. If neither
trajectory separates within the registered budget, retain that bounded negative
result without extending the rollout.

## Existing execution and external stopping

Reuse the experimental `after_approach` callback seam, `AtomicExecutor`,
`observe_controls`, native observer and existing scene-event replay hooks.
The callback needs only the two ordinary decision opportunities; it is not a
new planner or runtime. Preserve OPEN command and original orientation behavior;
no GRASP, RELEASE, lift stage, recovery primitive or target offset is added.

Rule STOP terminates before executing a hold. Keep the existing passive native
new-robot-pair force **>0.05 N** boundary, referenced to the registered initial
baseline: preserve the already-started primitive, then stop before another.
Contact/object measurements remain evaluator-only, apart from this explicit
external abort. Preserve execution-validator/invariant failures and inherited
wall limits, including partial evidence. No retry. A STOP arm receives no
equalizing hold; report its different action count and elapsed simulation time.

Exactly replay each normally completed episode once in its own fresh process,
using recorded controls solely for verification. Reapply the declared scene
event explicitly and compare state/own/native/image evidence. A failure or
replay mismatch stops the remaining batch without repair.

## What would be measured

Preserve both full decision/candidate/veto records, actual action sequences,
own endpoints, controller validation, raw contacts and uncropped RGB evidence.
For both arms, evaluate actual TCP distance to the **same fixed post-event fresh
sensor point**, alongside distance to each arm's own goal. This common evaluation
target stays outside cached-arm selection; independently decreasing two different
objective distances would not by itself demonstrate useful retargeting.

Report the first actual decision/action divergence or its absence, all normal
and adverse terminations, complete counts and exact replay results. Endpoint
distance is to the registered source point, not proven current bottle material;
any visible/object motion belongs in the separate evaluation evidence. A short
trajectory contrast would support this bounded retargeting behavior only. It
would not establish reaching, holding, grasp success, general VLM competence or
collision-free operation.
