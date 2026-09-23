# Current project state

Reviewed 2026-09-23. This document supersedes historical plans, not raw evidence.

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
with zero error. Current verification is **421 pytest tests**, ruff and compileall.
Three-run success is not established.
No hierarchy, planner, new contract, threshold change, hard-invalid-only ablation,
non-oracle replacement or E0 is authorized.

## Integrated baseline

Integration baseline: `33c7039e5f1f331fcac705498854c539a2568d42`, including research
tip `84cd781c400e66568e35d8d6ccf45d3b8fb15ad1` and demo tip
`59dae8ac074e601913251637176771d9d1004c09`.
The clean cleanup baseline is 7c27705. Use `git rev-parse HEAD` for this checkout.

The single local worktree is `laya-embodied-runtime`, currently on the focused
`feat/privileged-reference` branch. The reviewed share_main baseline is retained.
The [cleanup audit](archive/maintenance/cleanup_20260923.md) records old track
retirement and verification. The bounded privileged reference is the only new track;
no deployable architecture or ablation has been selected.
[Development tracks](development_tracks.md) defines collaboration responsibilities.

README plus the five documents directly under docs are authoritative.
Experimental records live in evidence; historical handoffs live in archive.
Their proposed next steps are not current work orders.
Use the [research](research.md) and [demo](engineering_demo.md) evidence indexes.

Cleanup verification: 384 tests passed; ruff, compileall, 13 CLI/import checks,
archival evidence audits and 249 local Markdown links/anchors passed.
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

## Architecture-review stop point

**Formal E0 remains blocked. No useful manipulation reference is established.
The deployable decision architecture remains under review.**

State Gap and Effect Gap remain separate. Effects from oracle_sim, deterministic
geometry, learned prediction and unknown/none must not be conflated. Geometry
derived from oracle inputs remains privileged.

The open question is what processing should occur between belief/world state and
Laya so code owns geometry/physics/candidate processing and the model judges
meaningful alternatives. Isolating privileged preview did not prove candidate
effects or preprocessing unnecessary. The legacy oracle path still contains
PhysicsPreviewCandidateBuilder / World.predict_all(); it is not restored to the
normal visual path.

The existing witness mechanism repairs the original empty-pool boundary, and the
explicit singleton rule correctly continues without counting model competence.
The first remaining failure is now a later state where one-step contracts are empty
and the original two-step search also returns no witnesses after 702 evaluated
branches. This is a zero-pool contract/lookahead dead end on the Laya-produced
trajectory. Current evidence does not distinguish an inherent two-step coverage
limit from a regime the original hierarchy would avoid. The broader judgment
boundary and deployable effect sources remain open. Prompt searches, binary
predicate tests, new planners, CDS redesign, new contracts and E0 remain outside scope.
