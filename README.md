# Laya Embodied Runtime

This is a small runtime for LIBERO and MuJoCo embodied experiments.

It separates environment execution, asynchronous observation fusion, candidate generation, Laya typed Choice, atomic execution and replay. Checkpoints are intentionally excluded.

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

## Environment integration

Implement AtomicBackend for a specific MuJoCo or LIBERO environment. The backend owns action layout, coordinate frame, scaling, gripper polarity, observations and success predicate. Do not reuse ManiSkill action scales for LIBERO.

Oracle state is for execution and policy upper bounds. It must not be reported as visual performance.

References:

- Show-Harness: https://github.com/showlab/Show-Harness
- Jev-LIBERO candidate preview architecture: https://github.com/Dimweaker/jev-libero
- Laya: https://github.com/NandhaKishorM/laya
- LIBERO-Pro: https://github.com/Zxy-MLlab/LIBERO-PRO
