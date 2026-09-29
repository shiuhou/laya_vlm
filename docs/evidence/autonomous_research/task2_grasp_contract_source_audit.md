# Task2 source audit: an object observation is not an effector goal

The current sensory approach has no positive open-jaw capture relation. It
minimizes grip-site distance to a cached BOX median-ray point. The successful
scripted prefix used a different relation: align the two-pad midpoint with a
privileged whole-bottle geometry center, subject to jaw-span/aperture and
predicted-push constraints, then establish bilateral pad contact. A more precise
semantic region could help, but would not supply that missing observation-to-
effector relation by itself. This source audit adds no code, goal coordinates,
winning-pose extraction, model/physics/render calls or new geometric outcomes.

Read-only source snapshot: runtime `e91a3a4ca25b1ffe68f4691afbc27aab5cc7a213`,
Jev `11d450455d0307bd806c94a27fc7166efb1c483d`. The bottle JSON SHA-256 is
`469e5760a24b715f912b5397baaf5fcbe8cb4b1f82864775ab05e751ca36c75c`.

## What the scripted grasp actually specified

| Contract element | Exact source semantics |
|---|---|
| Effector reference | Midpoint of the means of left/right fingerpad geometry vertices, not the grip-site origin. The pad axis joins those means. |
| Object reference | World-axis AABB midpoint of vertices from **all bottle contact geometries**; neither a named neck, a visible surface point, nor center of mass. |
| Approach relation | Reduce `norm(target_center − jaw_center)` while the projected whole-object span fits the initial open gap minus 2 mm, the current gap exceeds span plus 2 mm, and predicted object displacement is at most 5 mm. Other declared branches allow opening or span reduction. |
| Grasp admission | One branch permits closing from alignment ≤10 mm, span fit and bounded push; another admits newly established bilateral pad contact with bounded push. Alignment alone is not the measured grasp relation. |
| Result relation | Both designated fingerpads contact the bottle under the existing strict force rule; retained grasp is separately tracked across sampled controls. |

Sources: [bottle measurements](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:1753),
[alignment definition](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:1853),
[generic geometry arithmetic](/home/junhongli/projects/jev-libero/src/jev_libero/measurements.py:372),
[object geometry selection](/home/junhongli/projects/jev-libero/src/jev_libero/measurements.py:228),
[approach contract](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:964),
[grasp contract](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:875),
[thresholds](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:437),
and [bilateral relation](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:239).
These historical thresholds describe the privileged condition; they are not
new sensory admission thresholds.

`TaskSpec` holds objective vocabulary and priority; `TaskAdapter` selects the
first nonempty objective pool. The bottle adapter prioritizes establish-grasp
ahead of approach and changes phase from measured bilateral contact/containment.
Jev filters predicted effects using the declarative contracts and, when enabled,
predicted obstacle contact. This is privileged effect information. The later
local interface experiment copies the archived translation prefix and then
executes GRASP/MV_UP; it does not derive its pregrasp from a semantic neck query.
The fixed archive has 13 approach translations and no commanded pregrasp rotation.
No successful endpoint position or orientation was extracted for this audit.

Sources: [TaskSpec and routing](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/privileged_task.py:14),
[bottle routing](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/privileged_multistage_task.py:16),
[phase update](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/privileged_multistage_task.py:92),
[contract filtering](/home/junhongli/projects/jev-libero/src/jev_libero/policy.py:25),
[archived prefix binding](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/interaction_observability.py:32),
[interface prefix reuse](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/local_grasp_interface.py:210).

## What the sensory interface supplies, and what can be reused

The current [decision constructor](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/task2_box_point_boundary.py:80)
supplies own TCP, joint aperture/command and P; P's definition explicitly denies
surface-centroid, rigid-center and grasp-pose status. The
[derived relation](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/decision_interface.py:99)
is target minus TCP, and the [rule](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/decision_interface.py:340)
chooses the smallest strictly improving nominal 10 mm distance. Neither contains
pad orientation, finite pad overlap, positive capture, object extent or opposing
surface evidence. GRASP itself only [closes the gripper](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/runtime_core.py:469);
it does not convert an observation into a grasp pose.

Two existing pieces are reusable without importing a privileged goal:

1. [Own-pad relation arithmetic](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/task2_point_jaw_geometry.py:19)
   already maps a supplied point into the correctly mounted site frame and
   reports a finite open-gap prism: facing X planes from signed jaw joints,
   Y within ±8 mm and Z within [−11.6,+4.4] mm. Its midpoint is offset from the
   site by robot calibration, not a fitted task offset. This measures only
   point membership in static own-pad geometry; it cannot establish bottle fit.
2. [Separate hand/finger/pad geometry placement](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/task2_observed_surface_sweep.py:88)
   uses only own observations and static calibration. The
   [endpoint guard](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/task2_endpoint_containment_veto.py:57)
   reports observed-support containment in each solid, but then retains the
   original P-distance ranking. Absence of sampled containment is not positive
   capture, clearance, or a qualified terminal relation.

`InteractionSpec` is not a separate implemented class in the inspected runtime
or Jev source. The reusable contract is the existing task-level
[`interaction_relations` / `interaction_evaluation` declaration](/home/junhongli/projects/laya-embodied-runtime/embodied_runtime/experiments/tasks/wine_bottle_bottom_drawer.json:2052):
result, required relation and forbidden relation, consumed by a
[generic evaluator](/home/junhongli/projects/jev-libero/src/jev_libero/interaction.py:43).
The bottle grasp declaration's forbidden expression is currently constant false;
it must not be described as an existing no-palm-contact qualification. Contact
labels and full bottle geometry remain evaluator/oracle inputs, not deployable
sensor values. The evaluator casts expressions to booleans; unknown sensory
capture must stay explicit rather than being silently passed through as false.

The minimum representation change to investigate is therefore a **separate
observed-support–to–open-jaw relation**, with signed finite-pad margins and
per-solid obstruction evidence, alongside the original P and its provenance.
Do not overwrite `target.position_m` with a task offset or relabel P as a desired
TCP pose. A qualified effector goal remains unknown until that relation can be
supported; no planner or new action ranking is implied by adding a measurement.

## Competing explanations and the cheapest discriminating measurement

**Semantic/support hypothesis:** the admitted whole-object BOX and mixed depth
support do not isolate useful grasp support. The single neck query was
nonadmitted, so it supplies no cleaner region comparison. This leaves region
uncertainty open. The scripted task did not require a neck region, so its success
is not evidence that a neck prompt is the missing fix.

**Effector-relation hypothesis:** even a correctly identified visible surface
point can be a poor grip-site destination. Surface, whole-object center, pad
midpoint and grip site are distinct. A one-sided observed surface does not
supply object thickness, opposing contact or a free insertion corridor. Better
identity alone cannot establish those quantities.

Consume the geometry lane's already frozen **exact-P plus eight half-step-cell
corner** outputs before any policy change. Do not choose a winning corner or
search new poses. At precisely those same declared hypothetical poses, the
cheapest complementary measurement is the existing finite-pad relation for P
and **all retained full-BOX support**, alongside the already separate
hand/finger/pad containment rows. Preserve per-point signed margins, counts and
pixel IDs; no new crop, clustering, threshold, collision render, model call,
simulation or grasp trial is needed. This is a proposal, not an executed test.

The discriminator is limited but useful: sampled support lying in a hand solid
while outside the finite pad region would show that the current point target
and observed geometry conflict under that nominal pose assumption, without
requiring a new semantic query. P lying in the gap by itself proves little;
the rest of the observed support may conflict, belong to another surface, or
omit an occluded side. If the declared poses show no sampled conflict, both
semantic uncertainty and missing unobserved geometry remain. Corners do not
certify the cell interior, and endpoint tests do not certify a path.

Seal that sensor-only table before any optional evaluator attachment. The
producer may read RGB-D, fixed BOX support, own pose/joints and static robot
geometry only. Existing mask membership can then characterize which retained
pixels conflict, with ownership still unknown. Full object geometry, contacts,
privileged target center and successful pregrasp remain excluded from target
construction. This separates the immediate geometric contradiction question
from the still-open semantic-region question without fabricating a grasp goal.
