# Collaboration and document authority

## Active mission — 2026-09-26

The user authorized the autonomous embodied-interface mission on
`research/embodied-interface-discovery`, based on `share_main` at `b73b5b4`.
Parallel agents have disjoint implementation/evaluation/perception-audit ownership;
the research lead schedules GPU/physical experiments and reviews independent results.
This supersedes earlier restrictions on which research branches/experiments may
begin. Preserve the integration baseline and normal history; do not automatically
merge or publish exploratory results. See the
[research log](research/autonomous_research_log.md).

## One integrated baseline

`laya-embodied-runtime` / `share_main` is the shared reviewed baseline.
Former tracks `research/decision-interface` (tip `84cd781`) and
`feat/mujoco_demo` (tip `59dae8a`) are fully integrated.
The [cleanup audit](archive/maintenance/cleanup_20260923.md) records their
worktree/local-branch disposition. Their history remains reachable.
Remote branches are not removed. The bounded privileged reference was developed on
`feat/privileged-reference`, integrated into `share_main`, and frozen as
`privileged-drawer-reference-v1`. A focused `refactor/task-spec-adapter` branch then
isolated its drawer semantics behind `TaskSpec` / `TaskAdapter`; three fresh runs and
replay established exact behavioral equivalence before integration. The main
working directory then integrated the wine-bottle/bottom-drawer TaskSpec and generic
valid-interaction measurements, including the failed strict Task-2 gate. It has
returned to the single `share_main` baseline. Further candidate-policy or
architecture changes require a new decision; the authorized next branch is an
observational interaction-boundary audit only.

## Responsibilities for future work

| Area | Responsibility |
|---|---|
| Shared runtime | Belief/fusion, validity, decision/effect contracts, provenance, validation, atomic execution, replay |
| Research | Controlled information/effect questions and useful-reference qualification |
| Demo | Reproducible connectivity, telemetry, inspection and measured outcomes |

Class reuse does not make different questions, schedules, histories or candidate
sets scientifically matched. Diagnostic transformations stay opt-in, never silent
defaults. Shared-contract changes need review across research/demo uses and
relevant regression tests.

## Six authoritative documents

| Document | Responsibility |
|---|---|
| [README](../README.md) | Identity, setup and reading order |
| [Current state](current_state.md) | Operational truth and stop point |
| [Architecture](architecture.md) | Implemented contracts/dataflow |
| [Research](research.md) | Questions, hypotheses and evidence boundaries |
| [Engineering demo](engineering_demo.md) | Engineering claims/evidence |
| This document | Collaboration/ownership |

Dated evidence is revision-specific; archived handoffs are historical.
Neither overrides current_state or authorizes old next steps.
Preserve failures, assumptions, protocol/source hashes and negative results.

## Future integration rules

Use focused worktrees only after scope is agreed. Check status before editing;
never overwrite, stash or commit unrelated work. Merge normal history after
verification. Before retirement check unmerged commits and unique untracked or
ignored evidence. Git does not preserve ignored runs.

Keep oracle evaluation outside visual decisions. State Gap and Effect Gap differ.
Candidate validity is not collision approval; agreement is not utility;
connectivity is not task success.
