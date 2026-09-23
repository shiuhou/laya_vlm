# Task 2 privileged feasibility gate

Status: **not passed; Task-2 Laya was not run**.

This is a bounded engineering feasibility record, not a successful reference
episode. Development started from Laya commit
`c468d340649d17add4e9c450a096b5bca18af3c4`; the generic Jev measurement support
is commit `6d55eff` on `feat/multitarget-task-support`. Development gate traces
remain under ignored `runs/privileged-reference/task2-*-dev-*` directories. The
one portable boundary retained in Git is
`task2_strict_release_boundary.json`.

## Selected environment

The closest existing environment is LIBERO-90
`KITCHEN_SCENE4_put_the_wine_bottle_in_the_bottom_drawer_of_the_cabinet`, init 0,
seed 1. LIBERO has separate Scene-4 goals for putting the wine bottle in the
bottom drawer and closing that drawer, but no existing task combines them.
The derived BDDL changes only the goal to:

```lisp
(And
  (In wine_bottle_1 white_cabinet_1_bottom_region)
  (Close white_cabinet_1_bottom_region))
```

Loading that BDDL and applying the original put-task init-0 vector produced the
same 51-value simulator state as the original BDDL (`max_abs_error = 0.0`). The
official success remains `env.check_success()`.

The black-bowl alternatives were rejected at selection time because the measured
bowl span along the jaw axis was about 107.20 mm while the available Panda jaw
opening was about 76.45 mm. The wine bottle span was about 44.29 mm.

## Generic support exercised

The gate uses the existing 27 primitives and the existing one-step preview and
two-step witness machinery. The generic Jev world support added for this task is:

- an explicit BDDL override while retaining the benchmark init-state vector;
- adapter-controlled active collision/contact target binding;
- named-joint, LIBERO predicate, site-bound and articulated-subpart measurements.

Task-specific state, objective routing, contracts and success semantics remain in
the wine-bottle/bottom-drawer adapter and JSON TaskSpec. No separate runtime,
planner, strategy layer or new primitive was added.

Mechanical preflight passed at reset and closed-gripper fixtures: 27/27 previewed
primitives exactly matched real execution in each fixture and the preview restored
the controller/simulator context.

## Gate behavior

No TypeSafe/OpenRouter credential was present, so this was not a new live Jev-model
run. A deterministic privileged feasibility scorer selected from the complete
original contract pools using the declared effect for the active objective. It was
used only as a mechanical gate; it is not part of the Laya runtime and is not model
competence evidence.

The gate demonstrated these physical phases:

1. approach and bilateral grasp;
2. lift and transport while preserving the grasp;
3. bottom-drawer contact and official `In` containment;
4. an explicit `open` primitive that removed all bottle/fingerpad contacts;
5. bottom-drawer closure from roughly 158 mm to roughly 54 mm while containment
   and release stayed true.

Preview/execution state error remained zero in the recorded gate traces. The
stronger release definition was necessary: loss of bilateral contact under a
rotation with the jaw still commanded closed was rejected as release.

The run did not satisfy official success. A closure trajectory reached a zero-pool
boundary with the drawer still about 53.62 mm open. This trajectory was a replayed
continuation used to locate the mechanical blocker, so it is not a canonical fresh
feasibility success. An earlier clean strict-release boundary with all 27 effects
and zero two-step witnesses is preserved in
`task2_strict_release_boundary.json`.

The checked-in TaskSpec contains the later placement/release corrections used to
localize this blocker. That exact final working-tree configuration has not been
rerun as a fresh feasibility episode. The continuation to explicit release and
53.62 mm opening is diagnostic evidence only and must not be reported as a
canonical oracle run.

## Blocker

The reused basket placement contracts expose goal-center transport and containment,
but do not expose whether the held object's orientation and vertical extent fit the
**closed** drawer volume. The wine bottle was admitted by the open-drawer `In`
predicate in a pose that later obstructed closure. The existing contract set could
therefore establish containment and release without establishing closeability.

The smallest required extension is task-specific, not a new runtime: measure bottle
extent in the drawer frame and define a physically justified placement-fit/orientation
effect before release. That contract must first pass a fresh same-condition
Jev/oracle feasibility run. It was deliberately not invented in this task after the
gate failure.

Because the gate did not pass, no Task-2 Laya episode, reproduction run, or Task-2
replay claim was made.
