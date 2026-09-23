# Laya Embodied Runtime

Engineering and research runtime for embodied decision systems. Laya selects typed
robotic decisions; deterministic code owns geometry, validity checks and motor control.
Laya is one replaceable decision backend.

Two tracks share the same foundations:

| Track | Question | Current evidence and boundary |
|---|---|---|
| A — Embodied demonstration | Can observed world changes drive sustained, useful decisions and measurable task progress through an embodied feedback loop? | A real non-oracle loop and asynchronous smoke predate this branch. Current demos make it auditable; useful drawer manipulation is **not** demonstrated. |
| B — Decision-interface research | What information must the interface preserve for useful decisions? | Paired replay and bounded missing-information findings exist. A useful manipulation reference is **not** validated; formal E0 is not frozen. |

Start here:

1. [Current state](docs/current_state.md): verified implementation, actual branches,
   evidence and limitations.
2. [Development tracks](docs/development_tracks.md): collaboration rules, shared
   components and proposed branch responsibilities.
3. [Architecture](docs/architecture.md): active paths and interface boundaries.
4. [Research direction](docs/research.md): hypotheses, findings and the E0 gate.

Run or inspect the [embodied feedback demo](docs/closed_loop_demo.md), read the
[connectivity inspector runbook](docs/demo_runbook.md) and
[historical demo report](docs/engineering_demo.md), or inspect the latest
[research diagnostic handoff](docs/explicit_consequence_handoff.md), and the
[integration review](docs/integration_checkpoint.md). Demo connectivity
does not establish task competence, and oracle-conditioned decisions are not expert
ground truth. No formal E0/E1 experiment has started.

Historical handoffs describe their own revisions, not current instructions.
`docs/mix.md` is personal scratch material, not project documentation. Model weights,
raw runs and demo media are excluded from Git; a fresh clone does not contain them.
Artifact locations and reproduction commands are in the relevant evidence reports.

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
