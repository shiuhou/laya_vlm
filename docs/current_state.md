# Current project state

Reviewed 2026-09-27. This document supersedes historical plans, not raw evidence.

## Active autonomous research mission

The user has authorized autonomous research into the smallest decision interface
for manipulation under perceptual uncertainty, starting at `b73b5b4`. VLM planning,
Laya, perception, candidate effects and their responsibility split are hypotheses.
The former phase restrictions below remain historical scope, not current prohibitions.
Execution semantics, strict information provenance and historical evidence remain
protected. No new competent visual or interaction-valid policy is established.

Work proceeds on `research/embodied-interface-discovery`. Registered matched
probes now cover predicate recognition, supplied context/action meanings, native
option progress presentation, visual grounding/relations/subgoals, correspondence,
and sensor co-motion. The tested Laya presentations have not repaired the known
weak motor choices; further prefix variants on those states are stopped. The
tested 3B VLM has not shown useful visual phase/relationship differentiation;
one pinned 7B control is underway with the exact prior inputs and labels.

A fresh initial-POINT plus live-proprioception control crosses the repeated
grounder's semantic error, but stops after26 actions on finger-body contact with
the drawer front panel, not the handle. Its208 controls replay exactly. This
shows a physical limitation of point-distance control even with the initial
handle target correctly grounded. The current parallel probes separate
precontact scene visibility, robot-only geometry observability, and whether the
existing action pool contains a useful noncontact continuation. They do not yet
constitute an interaction-valid manipulation policy or a new runtime architecture.

See [current beliefs](../CURRENT_BELIEFS.md) and the
[research log](research/autonomous_research_log.md) for current hypotheses/results.
The following sections describe the preserved baseline.

## Interaction-structured research checkpoint

The current research direction is **Interaction-Structured Decision Interfaces for
Foundation-Model Robotic Manipulation**. The implemented privileged decision
boundary is now understood as four jointly relevant parts: current state, predicted
effects, a local objective and task-declared interaction semantics. The objective is
interaction-valid manipulation without task-specific policy training or a hard-coded
action sequence. It is not human-motion imitation.

Generic Jev measurements now expose exact contact geom/body attribution, boolean
relation traces and object geometry in an articulated frame. Task-specific selectors
and contracts use those measurements to identify designated effectors/affordances,
grasp relations and placement fit. No scheduler, Laya, primitive, executor, CDS,
planner or hierarchy change was introduced.

The frozen top-drawer runs remain reproducible privileged goal-completion references.
Replaying all three 970-control trajectories under the new observer produced the same
152.051897 mm net closure and official success, but found **zero** control endpoints
with designated fingerpad/handle contact and therefore 0 mm of measured
interaction-valid closure. Direct non-designated robot/drawer contact accounted for
46.086120 mm net closure; the remaining 105.965776 mm occurred at endpoints with no
current contact and includes inertia/settling that cannot be causally assigned to a
designated interaction. See
[the valid-interaction record](evidence/privileged_reference/valid_interaction_semantics.md).

The wine-bottle/bottom-drawer TaskSpec now requires full object extent/orientation to
fit the articulated drawer close envelope before release, and preserves that fit while
closing. A fresh deterministic privileged gate established a bilateral grasp and exact
preview/execution agreement, but stopped before decision 22: grasp remained valid,
the object was not inside, placement violation was 177.149474 mm, all one-step pools
were empty and all 729 existing two-step pairs had no witness. No Task-2 Laya call was
made. This is the current first failure boundary; the older continuation that reached
`In`, explicit release and 53.62 mm opening remains diagnostic rather than a canonical
fresh feasibility success.

## Local-objective privileged reference: reproducible success

The same-condition [Jev hierarchy comparison](evidence/decision_interface/jev_hierarchy_same_condition.md)
completed top-drawer closure in 20 decisions and 155 fresh controls. This proves
the fixed physical machinery admits a successful trajectory; it does not isolate
hierarchy from archived Jev motor answers.

The authorized [minimal local-objective reference](evidence/decision_interface/local_objective_reference.md)
adds one deterministic routing boundary before Laya motor selection. It selects
the first nonempty existing contract pool in the fixed order advance, establish,
approach, release, reposition. This router is new task policy; it is not original
Jev's model-selected intent. It retains the complete selected pool in primitive
order and adds no strategy or motion-family filtering.

The boundary-87 capacity failure was repaired without changing the decision
architecture. A lossless compact witness presentation retains all 25 candidates,
their canonical order and the same rounded effects while factoring repeated
metadata. Offline replay used 943 of 1,024 total tokens without clipping. Full raw
predictions and witnesses remain in evidence.

The only subsequent behavioral change was the authorized executed-primitive budget
from 100 to 200. On clean revision `4e26719`, three separate fresh processes with
the same task/init/seed/model/configuration each reached official LIBERO success at
step 121 after 122 primitives. Each run contained 111 genuine Laya multi-option
decisions, 11 forced singletons and one lookahead recovery. Opening changed from
151.659 to -0.393 mm, for 152.052 mm net closure. The complete physical decision
traces were identical. All selected previews matched real execution exactly; all
three control replays passed 1,093 boundaries with zero error.

This establishes the first reproducible successful **privileged Laya goal-completion**
reference. Oracle effects, task-specific contracts and deterministic objective
routing remain part of the policy boundary. The result does not establish a
deployable visual policy, flat atomic-choice success or which components are
necessary. No ablation, strategy layer, non-oracle work or E0 has begun.

The successful implementation is frozen by annotated tag
`privileged-drawer-reference-v1` at merge commit `5ba99de`; the three original runs
record execution revision `4e26719`. Drawer-specific task identity, contracts,
objective routing, outcome measurement and presentation were subsequently moved
behind `TaskSpec` / `TaskAdapter` at `3ee18b2`, without changing the decision
architecture. Before new execution, all 111 Laya inputs in each frozen run were
reconstructed byte-for-byte, all 122 routing/pool boundaries per run matched, and
the three frozen control traces replayed at 1,093 zero-error boundaries each.
Three further clean-revision fresh processes then reproduced the same 122-action
trace and official success exactly; their three replays also passed 1,093 boundaries
with zero error. The post-refactor canonical local evidence is
`runs/privileged-reference/local-objective-task-adapter-success/canonical-success-evidence.json`
(SHA-256 `b119aa422d81fc4bfb5fbb28230071eb59dd825cdc3d370735d56b74203160ae`).

## Privileged drawer reference v1: existing lookahead evaluated

The bounded reference uses Jev's full 27-action vocabulary, `World.predict_all()`
and existing collision-aware task contracts before a genuine Laya choice. When
the one-step union is empty, it now invokes original Jev's unchanged two-step
witness fallback. Contracts explicitly perform candidate-policy filtering beyond
hard validity. State/effects remain privileged; the visual path and CDS are unchanged.

The [reference record](evidence/decision_interface/privileged_reference.md) retains
the fixed acceptance gate and all attempts. The original one-step episode made 18
genuine decisions, reduced gap from 93.484 to 2.732 mm, produced zero closure and
stopped at an empty contract union. Its 144 controls replayed exactly.
The bounded [dead-end boundary audit](evidence/decision_interface/dead_end_boundary_audit.md)
reconstructed the exact state and all 27 previews. Original Jev's unchanged
one-step `contracts()` and the current reference produced identical predictions,
rejections and empty pools, ruling out a one-step port/integration bug. This is a
**CONTRACT DEAD-END** classification at the frozen one-step boundary. The archived
successful Jev run approached a similar gap in a materially different pose with
closure-positive actions.

The subsequent [two-step audit and run](evidence/decision_interface/two_step_lookahead.md)
show that original Jev already contains the excluded transition capability. On
the exact frozen state it evaluated 729 branches, found 32 qualifying pairs, and
returned 23 first-action witnesses representing 22 physical operations. Multiple
contact-producing first actions temporarily regress closure and recover positive
two-step net closure. Simulator/controller restoration was exact.

The minimal extension triggers this fallback only after an empty one-step pool,
offers all witness-backed first actions, executes only Laya's chosen first action,
then replans from reality. A clean fresh run reproduced the first 18 actions. At
boundary 18, Laya selected `open` from 23 options; real execution matched its
preview but produced zero closure. The next one-step pool contained only `z-3mm`.
The genuine-choice guard stopped before Laya or execution.

The authorized [forced-singleton continuation](evidence/decision_interface/forced_singleton_reference.md)
then inspected original Jev: it calls its model even for singleton intent/strategy/
motor pools and has no forced-continuation attribution. The reference therefore
uses the specified explicit rule: zero invokes existing lookahead, one executes
once without Laya, and a genuine multi-option pool calls Laya. A fresh run made
86 genuine Laya decisions, six forced continuations and two executed lookahead
recoveries. It achieved 15.173 mm net closure over 92 actions, but official success
remained false. At boundary 92, both the one-step union and unchanged two-step
witness set were empty; no Laya call or action followed. Replay passed 829 boundaries
with zero error. Current verification is **436 pytest tests**, ruff and compileall.
Three-run success is not established for that earlier flat condition; it is now
established for the local-objective privileged condition described above.
No hierarchy, planner, new contract, threshold change, hard-invalid-only ablation,
non-oracle replacement or E0 is authorized.

## Integrated baseline

The earlier research/demo integration is `33c7039`, and the cleanup baseline is
`7c27705`. The privileged reference was integrated at `5ba99de` and frozen by the
tag above. The behavior-preserving task-adapter extraction is also integrated into
`share_main`; use `git rev-parse HEAD` for the current baseline.

The integrated baseline is `laya-embodied-runtime` on `share_main`. The Task-2 adapter
and valid-interaction measurement phase were developed as focused commits and
integrated only after preserving the failed fresh gate. No successful Task-2 tag or
new architecture claim was created.
The [cleanup audit](archive/maintenance/cleanup_20260923.md) records old track
retirement and verification. No focused development track remains active; no
deployable architecture or ablation has been selected.
[Development tracks](development_tracks.md) defines collaboration responsibilities.

README plus the five documents directly under docs are authoritative.
Experimental records live in evidence; historical handoffs live in archive.
Their proposed next steps are not current work orders.
Use the [research](research.md) and [demo](engineering_demo.md) evidence indexes.

Current verification: 441 Laya-runtime tests, 43 non-simulation Jev tests and three
LIBERO measurement simulation tests passed; ruff, compileall, `git diff --check`,
byte-identical input reconstruction, and six replayed runs (three frozen and three
post-refactor). The cleanup baseline separately passed 13 CLI/import checks,
archival evidence audits and 249 local Markdown links/anchors.
Both old worktrees and their fully integrated local track branches were removed;
remote branches and the local master branch remain unchanged.

## Implemented and evidenced

Temporal observation admission, fusion, TTL/validity, provenance, canonical
decision projection, candidate identity, separate effect contracts, token audits,
atomic validation/execution, hash-chained records and replay have regression tests.
The live visual loop includes execution-to-next-input feedback audits.
Query tracking exists but is inactive in the live runner.
Offline paired diagnostic decisions cannot drive the paired collector.
These are infrastructure achievements, not manipulation competence.

Goal-last improved some anonymous choices without useful goal/effect binding.
Selective GRASP/RELEASE anonymization helped opening cases but not closing.
Explicit desired-consequence predicates did not reliably repair selection.
Candidate ordering substantially influences ranking. Evidence increasingly
implicates candidate consumption/the decision interface, without isolating a single
cause or proving physical state irrelevant.

The latest completed demo has eight Laya choices, nine captures, seven verified
feedback deliveries, and 64 controls replayed at 73 checked boundaries.
Drawer closure is zero, target contact false and task success false.
Action semantics and distance annotations did not make frozen atomic choices
reliably useful. Local-objective text also added a contact premise and did not
rescue the choice; decomposition remains a hypothesis.

## Evidence preservation

516 ignored evidence files (398,493,726 bytes) from both old tracks were copied
byte-for-byte into this worktree's runs directory. The transfer manifest is
`runs/maintenance/architecture-reset-20260923/evidence-transfer.json`,
SHA-256 `3e6a6f4510b95def5d9e2ba32a459f477b0674f431dac4a8f5bd1dea020433df`.
Original run identities/source hashes remain unchanged. This is local preservation,
not a remote backup; ignored artifacts are absent from fresh clones.

## Current stop point

**A reproducible privileged goal-completion reference is established. Its interaction
mechanism is invalid under the new designated-handle definition. Task-2 strict
mechanical feasibility is not established. Formal E0 has not begun.**

State Gap and Effect Gap remain separate. Effects from oracle_sim, deterministic
geometry, learned prediction and unknown/none must not be conflated. Geometry
derived from oracle inputs remains privileged.

The open question is what processing should occur between belief/world state and
Laya so code owns geometry/physics/candidate processing and the model judges
meaningful alternatives. Isolating privileged preview did not prove candidate
effects or preprocessing unnecessary. The legacy oracle path still contains
PhysicsPreviewCandidateBuilder / World.predict_all(); it is not restored to the
normal visual path.

The existing witness mechanism repairs the original empty-pool boundary, the
explicit singleton rule continues without counting model competence, and compact
serialization admits the complete 25-option witness pool. With only the authorized
budget extension, this unchanged policy completed the goal reproducibly, but through
non-designated contact. The next bounded work is an observational interaction audit
and an exact reconstruction of the Task-2 transport zero-pool. It must not alter
contracts, scoring, planning or model behavior. Non-oracle replacement, prompt
searches, binary predicate tests, new planners, CDS redesign and E0 remain outside
the current phase.
