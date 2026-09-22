# Laya Embodied Runtime

This is a research runtime for studying how asynchronous sensor observations can
be converted into decision-sufficient state and candidate-effect evidence for
typed embodied decision making. Laya is one replaceable decision backend.

Current verified status and review gate: [docs/current_state.md](docs/current_state.md).
Research question and proposed E0: [docs/research.md](docs/research.md).
Interfaces: [docs/architecture.md](docs/architecture.md).
Latest evidence and commands: [docs/reference_pilot_handoff.md](docs/reference_pilot_handoff.md).
No formal E0/E1 experiment has started.

It separates temporal belief, compact decision state, candidate semantics/effects,
typed decisions, validation and physical execution. Checkpoints are excluded.

## Model-free smoke test

PowerShell:

    py -3.12 -m venv .venv
    .\.venv\Scripts\python -m pip install -e ".[dev]"
    .\.venv\Scripts\python -m pytest -q

The model-free core includes a fake backend, rule provider, semantic TTL handling and out-of-order rejection.

## Laya

Install the optional dependency separately:

    .\.venv\Scripts\python -m pip install -e ".[laya]"

Load the typed-decisions checkpoint separately and pass the loaded agent to LayaProvider. This repository never downloads model weights.

## Vision model

The first visual-semantic prototype is NVIDIA LocateAnything-3B plus RGB-D depth,
belief fusion. Query tracking is implemented but inactive in the real runner.
See docs/vision_model.md for the boundary: LocateAnything
localizes queried regions; depth, tracking, task predicates and execution remain local
code. LocateAnything weights are not included or downloaded by this repository.

## Environment integration

Implement AtomicBackend for a specific MuJoCo or LIBERO environment. The backend owns action layout, coordinate frame, scaling, gripper polarity, observations and success predicate. Do not reuse ManiSkill action scales for LIBERO.

Oracle state is for execution, evaluation and explicitly privileged baselines.
An oracle-conditioned model is not automatically an expert or a policy upper bound.
Its results must not be reported as visual performance.

References:

- Show-Harness: https://github.com/showlab/Show-Harness
- Jev-LIBERO candidate preview architecture: https://github.com/Dimweaker/jev-libero
- Laya: https://github.com/NandhaKishorM/laya
- LIBERO-Pro: https://github.com/Zxy-MLlab/LIBERO-PRO

## Server environment
environment.yml defines the intended Conda environment (Python 3.10). On the target server, use `conda env create -f environment.yml`; if network access is restricted, install the model-free core with the system Python after the repository clone.
