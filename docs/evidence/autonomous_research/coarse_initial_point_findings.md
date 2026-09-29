# Initial visual point crosses the semantic failure and reaches non-handle contact

2026-09-27. One initial LocateAnything POINT plus live robot proprioception
passes the previous fresh-grounding failure at boundary 21. The unchanged
geometry rule then reaches a different boundary: the robot's finger body contacts
the top drawer's non-handle front panel at action 25. The existing external
contact monitor stops the episode after that atomic action. This establishes
a useful simpler coarse-approach baseline, and a concrete limit of this point
distance rule for designated-handle interaction in this configuration.

## Frozen condition and setup provenance

The [protocol](../../research/coarse_initial_point_control_protocol.md) was
frozen at `f8b1bf1`; its append-only setup correction was frozen at `30f49f4`
before the first physical trial. `coarse-initial-point-01` failed during
robosuite import because EGL GPU4 was absent from the CUDA device list. Its five
records contain no world, reset, capture, model call or control. Preserve that
setup failure. `coarse-initial-point-02` is the **first physical attempt**.

The physical run starts at top_drawer benchmark init 0 / seed 1, with standard
reset settling. It uses GPU4 for model and rendering after GPU1 acquired another
user's process. The historical fresh-query run used GPU2. Initial model input
tensors/tokens and output tokens reproduce exactly despite this assignment
change. No physical or perception outcome prompted a retry.

The sole behavioral change is the grounding schedule. One completed initial
POINT uses the same checkpoint, query, processor, hybrid greedy generation,
strict EOS/single-point admission and depth projection. Subsequent decisions
copy its world XYZ and read live returned robot proprioception. All boundary
RGB-D and native trajectory RGB remain recorded, but later images/depth do not
update the target. Seven candidates, nominal 10 mm effects, tie-break, native
controller/executor, 40-action budget, 900-second limit and **1 N** external
all-robot contact abort remain unchanged. There is no tracker, Laya decision,
recovery, grasp/rotation action or physics-preview selection.

This condition explicitly admits a stale point under an unverified stationary
target assumption. The canonical admission policy is
`initial-point-live-proprioception-v1`; geometry and semantic age both increase
from the initial capture. They reach **8.4 s** at the first differing action and
**10.0 s** at the contact-producing action. Source capture/time remain separate
from current decision/proprioception read time. Current visibility, semantic
validity, velocity, covariance, confidence, contact and holding stay unknown.

The raw `decision_boundary.admitted` object is the copied **initial admission**
record, including its historical `fresh_single_POINT_EOS...` string. That string
describes the initial measurement, not a fresh measurement at each boundary.
Canonical `quality.geometry_valid=True` means that the initial finite projection
is admitted under this experiment's stationarity assumption; its basis explicitly
says current validity is unverified. It is not evidence that current geometry
has been validated. The runner's legacy `version` also remains the shared fresh
runner identifier; the distinct experiment profile and canonical admission-policy
identifier specify actual behavior. Default uncertainty/freshness gates were not
validated or changed.

## Comparison identifies the first causal divergence

The initial observed point is `(0.003321376, −0.060191420, 1.096185701) m`, from
pixel `(158,185)`. Its image, calibrated depth, model input/output, initial
simulator state and point equal the historical fresh-query condition exactly.
The archived evaluator ray for that identical state/image/pixel hits the top
handle's visual geometry `wooden_cabinet_1_g17`. This transfers an existing
evaluator label after exact input equality; no ray/geometry enters the selector.

The first **21 primitives / 168 controls** reproduce the old physical actions,
commands and states exactly. All **22 RGB-D captures through boundary 21** also
match exactly. One earlier fresh-point variation at boundary 12 changes recorded
point-distance metrics; it does not change the selected action or actual control.

At boundary 21 the physical state and every robot-proprioception field are equal.
The new run selects **FWD** from the initial point. The fresh-query run selects
**RIGHT** from its new erroneous point
`(−0.037971943, −0.205322755, 1.063785567) m`. Literal independent recomputation
of the same distance rule recovers both actions. This first difference is due
to the target input, not a changed controller, hook side effect or unequal state.
No archived control or state was used to force the match.

## First physical boundary

The new run executes **26 primitives / 208 controls**, advancing simulation
0.5→10.9 s, and makes exactly **one** model call. At action 25, `MV_RIGHT`, the
first sampled contact is control 0, at **10.55 s**:

| Recorded contact evidence | Value |
|---|---|
| Robot collision geometry | `gripper0_finger1_collision` |
| Other collision geometry | `wooden_cabinet_1_g11` |
| First sampled normal force | 4.839181 N |
| Next sample above 1 N | Control 2, 2.670219 N |
| Later contact samples | Controls 4, 5, 7: 0.994117, 0.780797, 0.652785 N |
| Designated handle relation at action boundaries | false throughout |
| Native execution-contract violations | 0 |

The saved task config explicitly lists g11–g16 as non-handle drawer geometry and
g18–g20 as the designated handle collision geometry. Source XML and robosuite's
implicit geometry naming map g11 to the `cabinet_top` front-panel collision box.
The robot contact is on a finger body, not the designated fingerpad. No sampled
contact involves a designated handle geom, another robot part or a simultaneous
second pair. Contact rows include all robot geoms and preserve forces below 1 N.
This is a non-handle collision boundary, not a verified handle grasp/contact.

The observer first sees contact after a complete 0.05 s native control. It does
not observe the earliest integration substep. The original abort runs after the
atomic primitive, so controls 1–7 still execute; no action 26 occurs. At the
endpoint the remaining force is below 1 N, but the earlier above-threshold sample
still correctly causes termination. An endpoint-only contact check would miss
that event.

The drawer state is exactly unchanged through action 24 and immediately before
action 25. At the first contact sample it has closed **0.047615 mm**; after the
full primitive it has closed **6.844671 mm**, from 151.659013 to 144.814342 mm
open. The direct state component was identified by unique initial equality and
checked against every recorded before/after opening label. The cached geometric
handle center shifts 6.826182 mm; keep that distinct from direct joint displacement
because their sample semantics differ. This incidental non-handle push is not
task success. Official success stays false.

The fixed-point distance falls 231.187→52.375 mm, while the independently
evaluated TCP-to-handle-center distance falls 227.258→61.533 mm. The nearest
gripper/handle surface gap is still **25.242 mm** at the endpoint. Immediately
before the contact action, the gap is 24.486 mm and fixed-point distance 57.444 mm.
Improving point/center distance does not establish correct contact geometry.

The auditor personally inspected the raw trajectory contact sheet and enlarged
first/last-contact RGB crops. The finger lies at the upper edge of the drawer
front panel above the visible handle; exact contact is partly self-occluded.
Classification relies on recorded contact identifiers and structural mapping,
not RGB alone. The final available RGB-D is boundary 25 before the action.
Post-contact trajectory frames contain RGB only; no post-contact depth was
recorded after the abort.

## Integrity, limits and next question

The offline audit passes 761 explicit checks covering the evidence chain,
frozen code/protocol/checkpoint hashes, CPU reconstruction of the actual initial
processor arguments and generated tokens, source timestamps, immutable target,
all unknown fields, nominal recommendations/effects, actual controls/states,
trajectory hashes and contacts. The auditor does not call the policy's selector
to reconstruct its choices. An initial audit assertion incorrectly expected
all prefix *distance metrics* to match; its failed log is preserved. The corrected
audit compares physical fields exactly and reports the expected boundary-12
metric difference. No collection data or policy changed.

Full actual-control replay from another fresh reset passes **all 208 controls**:
the initial and every before/after flattened state are exactly equal, **417 checks,
maximum error 0**. It validates these recorded controls, not an independent policy
replication. Processor evidence verifies generation arguments, not forward hooks
or full-vocabulary logits.

Camera calibration is identical across all captures; evaluator handle position
and drawer state are unchanged before the contact-producing primitive. This
supports the fixed-target explanation in this one development condition.
It does not establish moving-target operation, temporal perception benefit,
general point-interface sufficiency, oracle-free safety or successful manipulation.
The point remains semantically grounded while the open-jaw geometry hits a
different part of the drawer: correct semantic targeting alone was insufficient
for this unchanged local controller/rule to establish designated handle contact.

The next useful question is whether the pre-action RGB-D and known robot geometry
could expose the impending non-handle contact, including occlusion and swept
volume uncertainty. That warrants an observational check of existing evidence
before any recovery, new controller or live safety gate.

Raw main-workspace evidence is in `runs/autonomous-research/coarse-initial-point-02/`:
`episodes.jsonl`, captures/model input/trajectory artifacts, `replay-check.json`,
`independent-audit.json`, `independent-audit-v2.py`, `contact-geometry-audit.json`,
its script, and the inspected RGB figures. Setup failure `coarse-initial-point-01`
and both audit logs remain preserved. The
[portable summary](coarse_initial_point_summary.json) includes exact source hashes.
