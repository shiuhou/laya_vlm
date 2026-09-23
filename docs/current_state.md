# Current project state

Reviewed 2026-09-23. This document supersedes historical plans, not raw evidence.

## Authorized next phase: privileged drawer reference v1

The human has selected a bounded reference before ablations: Jev's full 27-action
vocabulary, one-step World.predict_all(), and the union of existing collision-aware
task-specific effect contracts, followed by a genuine multi-option Laya choice.
These contracts explicitly perform part of candidate-policy filtering; this is
not hard-invalid-only filtering. State and effects are explicitly privileged.
The reference is opt-in; the visual path and CDS remain unchanged.

The [reference record](evidence/decision_interface/privileged_reference.md) specifies
the task, acceptance gate, implementation and results. The target is three
independent successful runs from benchmark init 0 / seed 1 plus control replay.
The first episode on implementation f39e711 made 18 genuine multi-candidate Laya
choices and reduced surface gap from 93.484 to 2.732 mm, but closure stayed 0 mm.
At boundary 18 the effect-contract union was empty: contact-producing actions
predicted opening beyond the -0.01 mm tolerance; non-regressing actions fell below
the 2 mm approach threshold. No fallback executed. All 18 selected previews matched
actual endpoints exactly; 144 controls replayed at 163 boundaries with zero error.
Three-run successful repeatability has not been established; no success repeats
were started. Contracts remain frozen pending review of this concrete failure.
The bounded [dead-end boundary audit](evidence/decision_interface/dead_end_boundary_audit.md)
reconstructed the exact state and all 27 previews. Original Jev's unchanged
one-step `contracts()` and the current reference produced identical predictions,
rejections and empty pools, ruling out a one-step port/integration bug. This is a
**CONTRACT DEAD-END** classification at the frozen one-step boundary. The archived
successful Jev run approached a similar gap in a materially different pose with
closure-positive actions, but that does not prove the frozen state has no useful
physical continuation. Jev's lookahead fallback was explicitly outside this audit.
Final reference verification: 405 pytest tests passed before the boundary audit;
the audit adds seven focused tests and the current full suite is **412 passed**.
Ruff and compileall pass;
raw-derived input/feedback/artifact audits and all 19 recomputed contract unions
passed. The only inference episode used committed implementation f39e711.
No hierarchy, planner, two-step lookahead, hard-invalid-only ablation, non-oracle
replacement or E0 is authorized.

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

The bounded privileged reference above remains the selected track. Before another
model run or reference revision, humans must decide whether and how to represent
the excluded contact transition. Raising the numeric regression tolerance alone
is not supported. The broader judgment boundary and deployable effect sources
remain open. Prompt searches, binary predicate tests, new planners, CDS redesign,
lookahead implementation and E0 remain outside scope.
