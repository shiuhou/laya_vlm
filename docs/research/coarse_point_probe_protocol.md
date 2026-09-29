# Fresh POINT coarse approach diagnostic v1

Prospective scope: top_drawer, benchmark init 0, seed 1; one rule run and one
hold run, separate fresh processes, maximum 20 primitives and 900 wall seconds
per run. This is deterministic coarse approach to a reported visual referent,
not manipulation, model motor competence, or a collision-safe robot policy.
No Laya/VLM motor call, preview, archived controls, recovery, or parameter search.

Each boundary captures fresh full RGB-D and calibrated camera matrices. A single
initialized LocateAnything worker receives RGB only and the frozen POINT query
from point_grounding_probe. Keep native greedy hybrid settings and raw generated
tokens. Before World construction or model loading, require the archived checkpoint
content ID `4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`.
Admit only exactly one in-frame point with terminal EOS, no reached
generation limit, and finite containing-pixel depth in [0.01, 5] m. Backproject
the containing pixel center, not an invented bounding box. No retry or mixed
output salvage. Record simulator state before capture and after inference and
require exact equality of flattened simulator time/qpos/qvel only. This check
does not cover controller or solver caches; independent actual-control replay
tests whether observational reads/rendering changed later execution. All
probability, covariance, velocity, contact, holding,
semantic validity and temporal consistency fields remain unknown. Geometry-valid
means this explicit fresh-point admission policy only, not calibrated confidence
or verified identity.

Seven candidates in existing canonical order: six native 10 mm world-axis
translations and STOP (active pose hold). Use unchanged canonical rule_token:
minimize nominal distance to stationary reported point, retaining existing lexical
token tie-break; STOP if no strict nominal improvement. Hold condition executes
STOP but computes/logs the same rule recommendation. Both conditions perform the
same sensing/admission path, including a final fresh observation when no earlier
failure prevents it. No fabricated semantic score/covariance; no fusion.

Use unchanged AtomicExecutor / RecordingBackend. An observational wrapper of the
existing env.step records every robot collision-geom contact after each native
control. Geoms come from Measurements group=robot (all arm + gripper). Keep all
contact rows, including zero-force contacts and robot self-contact; external
supervision stops at the completed atomic boundary on any newly seen robot
contact pair above the task's existing force threshold. Existing initial pairs
are logged and excluded only from the new-pair abort, never hidden. This is an
oracle experimental abort, not perceptual safety or action ranking. Restore the
observer in finally. Record independent designated handle distance, valid handle
contact, drawer opening, official success and raw contacts as evaluator-only.

Stop at first admission/state/executor/runtime failure, new contact, rule STOP
(rule arm only), budget, or wall limit. No manipulation success target. Capture
full control replay artifacts; exact replay tolerance remains 1e-8. Persist
partial controls if a runtime exception occurs during a primitive.

Report distance to the fixed pre-action sensor point before/after each action,
distance to the next freshly reported point separately, proprioceptive TCP delta,
and independent TCP-to-designated-handle-center and gripper-to-handle surface
distance. Changing referents must not masquerade as physical progress. Compare
rule/hold at common executed-action counts and, primarily, intersect their
cumulative actual-control counts at atomic endpoints. Verify logged control
counts against execution evidence; record cumulative simulated elapsed time and
its agreement at every matched endpoint. Do not assume every primitive took
eight controls. Report independent handle-distance contrasts at those common
control counts, declare unequal-horizon censoring, and retain each condition's
own endpoint. Never extend the budget automatically.

Comparison requires identical recorded source commit/hashes, task configuration,
benchmark initial-state identity/binding, environment repository identities,
model content ID, initial simulator state and resolved settings except condition
and output path. Reject mismatches before interpreting the contrast.
