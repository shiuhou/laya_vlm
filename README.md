# Laya Embodied Runtime

Engineering and research runtime for embodied decisions. Laya selects typed
actions; code owns estimation, validity checks and motor control.
The integrated baseline demonstrates an inspectable visual model-to-actuator loop,
not useful drawer manipulation or a useful reference policy.

The [privileged reference v1](docs/evidence/decision_interface/privileged_reference.md)
now exercises full Jev candidate previews, task-specific effect-contract filtering
and original Jev's two-step witness fallback. Deterministic singleton continuations
are now explicitly separated from genuine Laya decisions. A fresh run achieved
15.173 mm net closure before both one-step contracts and two-step lookahead became
empty; official task success remains unestablished.

## Reading order

1. [Current state](docs/current_state.md): operational truth and stop point.
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
An AtomicBackend owns action layout, coordinates, scaling, gripper polarity and
success predicates; controller scales cannot be copied between environments.

References: [Laya](https://github.com/NandhaKishorM/laya),
[LIBERO-Pro](https://github.com/Zxy-MLlab/LIBERO-PRO),
[Jev-LIBERO](https://github.com/Dimweaker/jev-libero),
[Show-Harness](https://github.com/showlab/Show-Harness).
