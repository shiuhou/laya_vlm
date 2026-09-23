# Privileged Drawer Reference v1

Current authority: [current_state.md](../../current_state.md).
Base: share_main 7c277053bee6a2f1a29428b36fc70ca75aa9a52f.
Human-approved bounded reference, not E0, ablation or a visual claim.

## Fixed architecture and attribution

Oracle observation -> BeliefStore -> 27 native Jev primitives ->
World.predict_all() -> collision-aware task-specific effect-contract union ->
Laya choice -> Jev AtomicExecutor adapter -> real backend execution ->
independently read actual outcome -> next observation and model input.

**Task-specific effect contracts perform part of candidate-policy filtering.**
They exclude more than hard-invalid actions. Existing approach/contact/closure/
release contracts and thresholds remain unchanged. All admitted actions are
offered in Jev vocabulary order; no selected intent, top-k, best-action code,
hierarchy or two-step witness. Hard-invalid-only is a possible later ablation,
not part of v1. No CDS or visual default changes.

The opt-in builder mapping preserves the old eleven-token default. Runtime accepts
an optional executor; its default is unchanged. The reference executor uses the
same native World.execute() controls as preview, including inherited controller
goals and retained grip. Nominal tracking errors remain recorded separately from
preview/execution mismatches; reset tolerances are not claimed to validate all 27.

## Frozen collection and acceptance

- Task: libero_90/KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet.
- Benchmark initial state 0, seed 1; original reset, no demonstration warm start.
- Three independent processes with the same code/model/config/seed must succeed;
  each must pass recorded-control replay (state tolerance 1e-8).
- Maximum 100 decisions / 1800 wall seconds per episode.
- Only local Laya typed-decisions, CUDA/bfloat16, unchanged checkpoint context.
- Every nonterminal decision requires at least two distinct operations; hold/open
  or hold/close aliases alone are not counted as genuine choice.
- No singleton execution, rule fallback, invalid choice, clipping or hidden retry.
- Actual joint state and official env.check_success() determine success after
  live execution; predicted success never declares completion.
- Stop and diagnose preview/execution mismatch. Preserve unsuccessful attempts;
  do not tune prompts/filtering or add architecture to conceal failure.

State/effects are explicitly effect_source=oracle_sim, privileged=true.
Input contains current opening, surface gap, target/obstacle contact, grip/gap,
one previous actual outcome, and each admitted action's closure, gap reduction,
target contact, obstacle peak force, success and number of controls.
Closure uses three decimal mm, gap two decimal mm, force one decimal N; raw
full-precision values remain recorded. Preview is up to eight controls / 0.4 s,
with early success stopping disclosed. Fixed instruction:

> Choose one action to close the drawer using its predicted effects. Prefer
> completion, closure, then contact or approach; avoid obstacle force.

All actual API payloads, ordered options, encoding audits and consumed tokens are
recorded. Contracts/predictions/rejections remain available for every candidate.
Actual previous outcome record IDs link into subsequent model inputs.

## Why this is more than a prompt change

The visual demo had no model-facing physics effects/history and repeatedly toggled
the gripper without approaching. The old preview builder omitted closing_mm from
its descriptions. The eleven-token subset excluded 3/40 mm primitives used by the
historical Jev success and reduced one archived contact state's five candidates
to a singleton. This reference restores the full native vocabulary, task-effect
filtering and dynamics-conditioned consequences. It does not prove these suffice:
earlier effect-bearing diagnostics already show genuine selection difficulties.
The historical Jev success used a hierarchy, so is not a Laya success reference.

## Verification before model collection

19 focused tests; 403 full pytest tests passed. Ruff, compileall, diff checks pass.
Mechanical evidence: runs/privileged-reference/preflight-v01.
All 27 primitives at reset, closed-gripper and archived loaded step 48 matched
preview against executor (81 probes), with complete context restoration.
Archived controls were used only to construct the mechanical test fixture.
No model calls occurred in this preflight.

## Commands

From repository root, use a fresh output directory per collection attempt:

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
MUJOCO_GL=egl $P -m embodied_runtime.experiments.privileged_reference \
  --mode preflight --output runs/privileged-reference/preflight-v01
CUDA_VISIBLE_DEVICES=1 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.privileged_reference \
  --output runs/privileged-reference/episode-01
MUJOCO_GL=egl $P -m embodied_runtime.experiments.privileged_reference \
  --mode replay --output runs/privileged-reference/episode-01
$P -m embodied_runtime.experiments.privileged_reference \
  --mode summarize --output runs/privileged-reference/episode-01
```

## Results

Pending first model episode. No successful reference or repeatability claim yet.
