# Laya Embodied Runtime

Engineering and research runtime for embodied decisions. Laya selects typed
actions; code owns estimation, validity checks and motor control.
The integrated baseline demonstrates an inspectable visual model-to-actuator loop.
That non-oracle demo still does not establish useful drawer manipulation.

The selected implementation direction (2026-09-30) is **Qwen3-VL brain → Laya
local choice → continuous RGB-D geometry and deterministic servo**. Model
contributions remain to be evaluated with B0–B4; this is not an open-ended
architecture search. Start with the [P0 acceptance report](docs/p0-acceptance.md),
[approved implementation plan](docs/p0-implementation-plan.md), and
[wire protocols](docs/protocols-and-inference-example.md).

P0 now supplies model-free message/state/action contracts, sensor boundaries and
cancellable scheduling. Its synthetic tests do not establish visual robot
control, model performance or drawer success. P1/P2 own real perception/control.
The [P1 RGB-D checkpoint](docs/p1-rgbd-checkpoint.md) adds same-exposure sensing,
conservative geometry/tracking and exact 200-record replay. Static diagnostics
have not yet established a drawer-front push patch or cabinet-relative VERIFY;
P1 task acceptance and P2 manipulation remain pending.
The first task is pushing a visible drawer front; a pad/handle grasp is not a
prerequisite. Earlier [beliefs](CURRENT_BELIEFS.md) and the
[research log](docs/research/autonomous_research_log.md) remain historical records.

The earlier privileged research phase studied **Interaction-Structured Decision Interfaces for
Foundation-Model Robotic Manipulation**. The question is what physical structure a
runtime must expose to a frozen decision model so its closed-loop choices satisfy
both task results and task-valid interaction relations. The interface under study is
current state + predicted effects + local objective + interaction semantics. This
phase was explicitly privileged. Its scope restrictions describe those historical
experiments, not the selected implementation direction above.

The [local-objective privileged reference](docs/evidence/decision_interface/local_objective_reference.md)
now exercises full Jev candidate previews, task-specific effect-contract filtering,
an explicit local objective and original Jev's two-step witness fallback.
Deterministic singleton continuations are explicitly separated from genuine Laya
decisions. On top-drawer init 0 / seed 1, three fresh privileged runs each reached
official success after 122 primitives, with exact preview/execution and control
replay. This is a reproducible privileged **goal-completion** reference. A later
contact-attribution replay found zero measured fingerpad/handle interaction, so it is
not evidence of a learned drawer-closing manipulation skill.
The frozen reference is tagged `privileged-drawer-reference-v1`. Its top-drawer
semantics now live behind a `TaskSpec` / `TaskAdapter` boundary; three post-refactor
fresh runs and full control replay reproduce the frozen trace exactly.
The same runtime now hosts a wine-bottle/bottom-drawer TaskSpec plus generic contact
relation and frame-relative placement measurements. Its latest fresh deterministic
gate retained a valid grasp but stopped at a transport zero-pool before placement;
Task-2 Laya has not run. See the
[valid-interaction record](docs/evidence/privileged_reference/valid_interaction_semantics.md).

## Reading order

1. [P0 acceptance](docs/p0-acceptance.md): current implementation, tests and limits.
   [Current-state checkpoint](docs/current_state.md) records the preceding research stop point.
2. [Architecture](docs/architecture.md): implemented interfaces and boundaries.
3. [Research](docs/research.md) or [engineering demo](docs/engineering_demo.md):
   claims and focused evidence indexes.
4. [Development tracks](docs/development_tracks.md): collaboration and authority.
5. Consult evidence for specific results and the
   [historical handoff](docs/archive/historical_handoffs/handoff.md) for provenance.

Historical protocols and reproduction commands are records, not instructions to
start experiments. Raw runs, media and model weights are excluded from Git;
a fresh clone does not contain local evidence artifacts.

## Environment

Python >=3.10 is required. The server uses Miniforge/Python 3.10;
[environment.yml](environment.yml) records the environment:

```sh
conda env create -f environment.yml
conda activate laya-embodied
python -m pip install -e ".[mujoco,libero,dev]"
```

On restricted networks use an accessible package mirror appropriate to your
environment; setup does not require changing global package settings.
For model-free development:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m examples.fake_run
python -m pytest -q
python -m ruff check .
python -m compileall -q embodied_runtime tests
```

Laya is an optional extra (`pip install -e ".[laya]"`); its typed-decisions
checkpoint must be supplied separately. LocateAnything weights and the external
LIBERO/Jev setup are local prerequisites, not downloaded by this repository.

## Boundaries

The visual path uses RGB-D and proprioception. Simulator state is allowed for
execution/evaluation and explicitly privileged references, never silent visual
decision input. Oracle-conditioned decisions are not automatically useful.
The legacy AtomicBackend owns action layout, scaling and success predicates.
The new sensor-only path gives servo only a SensorPort and sends official success
to an independent evaluator. Controller scales cannot be copied between environments.

References: [Laya](https://github.com/NandhaKishorM/laya),
[LIBERO-Pro](https://github.com/Zxy-MLlab/LIBERO-PRO),
[Jev-LIBERO](https://github.com/Dimweaker/jev-libero),
[Show-Harness](https://github.com/showlab/Show-Harness).
