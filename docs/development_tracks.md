# Development tracks and collaboration

This is the collaboration map, not an experiment protocol. Read
[current_state.md](current_state.md) for actual branch/implementation status,
[architecture.md](architecture.md) for contracts, and [research.md](research.md)
for the scientific direction. Neither track's success implies the other's.

## Track A — Embodied demonstration

Question: **Can observed world changes drive sustained, useful atomic decisions
and measurable task progress through an embodied feedback loop?**

```text
World / Sensors -> Structured Interface -> Typed Decision Model
                -> Validation -> Atomic Executor -> Physical Execution
                -> Observed Outcome -> Updated State -> Next Decision
```

Laya makes robotic decisions; deterministic code owns geometry, action semantics,
validity checks and low-level control. A real non-oracle RGB-D/LocateAnything/fusion/
Laya/executor path and a two-step asynchronous `vision_laya` smoke were verified
before this branch (see [historical handoff](handoff.md) and [Stage 0 audit](stage0_audit.md)).
This track makes that capability reproducible, observable, replayable and auditable;
it is not creating an embodied loop from zero. Connectivity is a milestone, not
the full engineering objective. Choice alternation is not useful adaptation merely
because candidate gates removed the previous choice.

Scope: sustained task-directed execution, feedback provenance, observable model
choices, execution telemetry, video/trajectory communication and honest failure
diagnosis. Current entry points
are [engineering_demo.py](../embodied_runtime/experiments/engineering_demo.py) and
[demo_report.py](../embodied_runtime/experiments/demo_report.py). The older
[run_libero.py](../embodied_runtime/experiments/run_libero.py) is a separate legacy
smoke path, not the same model presentation/scheduling configuration.
The [demo runbook](demo_runbook.md) documents the current live console, offline
HTML evidence inspector, reproduction commands and verified engineering artifact.
The [feedback successor](closed_loop_demo.md) audits outcome-to-next-input links
and exposes where task progress fails without substituting a scripted policy.

The [verified demo](engineering_demo.md) uses visual belief, fresh synchronous
captures, natural candidate gates and no effects. Four actual Laya choices operate
the gripper, with replayable controls. The drawer does not move. Do not optimize a
presentation by hiding rule-selected actions, fallbacks, oracle inputs, retries or
task failures. A future oracle demo must be explicitly labeled privileged.

## Track B — Decision-interface research

Question: **What must the world-to-model interface preserve for useful decisions?**

Scope: decision-state abstractions, missingness/UNKNOWN, temporal validity,
task-relative information, candidate semantics and separately controlled effects.
CDS v0.1 is an implemented hypothesis, not an established sufficient state.

Current entry points include [collect_pairs.py](../embodied_runtime/experiments/collect_pairs.py),
[replay_equivalence.py](../embodied_runtime/experiments/replay_equivalence.py),
[interface_search.py](../embodied_runtime/experiments/interface_search.py),
[reference_gate.py](../embodied_runtime/experiments/reference_gate.py),
[effect_binding.py](../embodied_runtime/experiments/effect_binding.py) and
[provider_comparison.py](../embodied_runtime/experiments/provider_comparison.py) and
[clause_order.py](../embodied_runtime/experiments/clause_order.py) and
[goal_placement.py](../embodied_runtime/experiments/goal_placement.py) and
[selective_grip.py](../embodied_runtime/experiments/selective_grip.py) and
[explicit_consequence.py](../embodied_runtime/experiments/explicit_consequence.py).
Collectors and simulator probes can execute physical controls, but the research
decision replays do not drive those source trajectories. A successful archived
Jev collector is not evidence that the current Laya policy solved the task.

The [latest bounded findings](explicit_consequence_handoff.md) show that explicitly
stating the desired consequence does not materially help: true utility falls 5/16
to 4/16, true closing stays 0/8, and appropriate goal reversal stays 1/16. The
desired-consequence-to-candidate operation remains unreliable, weakening an
upstream-only explanation. The historical next diagnostic proposes individual bundle
predicate verification to distinguish recognition from competitive selection;
it is now on hold for the integration checkpoint's architecture review.
No new provider or schema is justified. The earlier selective-grip,
cross-provider, clause-order and goal-placement findings retain their bounded scope;
Laya is the primary research system. The prior
status-missingness result remains narrower than a manipulation reference. State Gap and
Effect Gap remain separate; an E0 freeze needs review, not just functioning tools.

## Shared foundations, not two implementations

| Shared component | Location | Contract to preserve across tracks |
|---|---|---|
| Observation and temporal belief | [runtime_core.py](../embodied_runtime/runtime_core.py), [fusion.py](../embodied_runtime/fusion.py) | Capture-time provenance, fixed-lag replay, age/validity and honest uncertainty |
| State/effect interfaces | [decision_interface.py](../embodied_runtime/decision_interface.py) | Current state distinct from prospective effects; unknown and privileged values explicit |
| Candidate validity | [physics_preview.py](../embodied_runtime/adapters/physics_preview.py) | Visual gates distinct from privileged simulator previews; hard rejection distinct from soft evidence |
| Providers, validation and execution | [runtime.py](../embodied_runtime/runtime.py), [runtime_core.py](../embodied_runtime/runtime_core.py), [libero.py](../embodied_runtime/adapters/libero.py) | No silent policy substitution; validated identities; backend-owned control semantics |
| Sensors and model input | [adapters/](../embodied_runtime/adapters/), [vision.py](../embodied_runtime/vision.py) | No oracle back-fill into visual inputs; token audits for compact research/demo paths |
| Provenance and tests | [records.py](../embodied_runtime/experiments/records.py), [tests/](../tests/) | Durable raw evidence, failure preservation, artifact identities and regression checks |

Shared code does not imply matched experiments: demo natural candidates, offline
eleven-token probes, question text, history, target referent and sensing schedule
can differ. Record those choices; do not pool the resulting measurements.

## Recommended branch strategy — human-controlled

| Branch | Intended responsibility | Integration rule |
|---|---|---|
| `share_main` | Shared, reviewed baseline containing both tracks and common foundations | Integrate coherent changes with tests, evidence links and current-state updates |
| `research/decision-interface` | Track B diagnostics, hypotheses and protocols | Keep experimental configurations/results identifiable; no automatic promotion to live policy |
| `feat/mujoco_demo` | Track A demos, visualization and reproducibility | Keep demo-specific adapters opt-in; no silent change to research comparisons |

The three branches now have separate worktrees: `laya-embodied-runtime` on
`share_main`, `laya-decision-interface` on `research/decision-interface`, and
`laya-mujoco-demo` on `feat/mujoco_demo`. The 2026-09-23 checkpoint integrates
research `84cd781` and demo `84abdb8` / `59dae8a` into `share_main`; see
[current_state.md](current_state.md). Track worktrees retain their track commits.
No remote/default-branch change accompanies this integration. The shared baseline
is not an `exp-e0-v0` experimental freeze. Further experiments, including the
proposed binary predicate diagnostic, are on hold for architecture review.

Prefer small reviewed merges back to `share_main`, then bring shared changes into
both tracks. Shared-module fixes belong in focused changes, not duplicate forks
inside each track. Before changing a schema, executor, gate, model presentation or
record format, coordinate across tracks and state which artifacts/tests are affected.
No branch reset, force-push, default-branch change or automatic experiment follows
from this recommendation. Separate worktrees help parallel humans/agents avoid
editing the same checkout; agree file ownership when a worktree is shared.

## Working agreement and evidence handoff

1. Start with `git status --short`, `git branch --show-current`, and
   `git rev-parse HEAD`; read the current-state index and the relevant evidence
   report. Preserve unrelated edits. State the track and whether work is diagnostic,
   implementation or an approved experiment.
2. Keep simulator diagnostics outside visual model inputs. Preserve unknown fields,
   failed attempts, actual candidate sets, forced/fallback choices and token audits.
   Do not relax thresholds or move policy into a projection to make results cleaner.
3. Record task, actual LIBERO `init_state_id`, seed, model/source/config identities
   and physical boundary. Seed alone is not an independent benchmark reset. Keep
   State Gap comparisons matched in model, question, candidates, history and effects.
4. Use fresh run directories. Handoff code revision/working-source hashes, commands,
   environment, raw artifact locations, failures and claim boundaries. `runs/`, media
   and model weights are local/ignored: a clone is not an evidence bundle. Collaborators
   need the relevant manifests, raw records and referenced hashed artifacts, or must
   report that evidence is unavailable. Preserve hashes when transferring artifacts.
5. Run focused tests for changed contracts and the existing full pytest/ruff workflow
   before integration; use a bounded real smoke when a live path changes. Documentation
   edits need link/path and consistency checks, not new model/benchmark collection.
6. Update the operational index when verified behavior changes. Keep historical
   handoffs/protocols intact; add a dated successor/correction and link it from the
   index. A proposed schema or experiment is not an implemented or verified result.

## Documentation authority

- [README](../README.md): identity and onboarding.
- [current_state.md](current_state.md): operational truth and current review gate.
- This file: track responsibilities and collaboration/branch recommendations.
- [architecture.md](architecture.md): implemented interfaces and active data paths.
- [research.md](research.md): one research-direction document; hypotheses are not facts.
- [engineering_demo.md](engineering_demo.md) and dated handoffs/protocols: revision-
  specific evidence and commands. `handoff.md`, Stage 0/1/2/interface/pilot reports,
  the E0 readiness review, and older vision/async design notes retain historical scope.

When prose disagrees with code/tests/raw records, inspect the evidence and document
the discrepancy; do not silently rewrite the old result. `docs/mix.md` is personal
scratch and is outside this authority map.
