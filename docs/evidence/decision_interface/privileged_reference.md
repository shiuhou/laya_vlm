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
release/reposition contracts and thresholds remain unchanged. All admitted actions
are offered in Jev vocabulary order; there is no selected intent, top-k,
best-action code or hierarchy. After the original one-step dead end was audited,
v1 was minimally extended to invoke original Jev two-step witnesses only when the
one-step union is empty. Hard-invalid-only remains a possible later ablation.
No CDS or visual default changes.

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
Witness-backed first actions additionally expose the original second action,
two-step net closure/gap, terminal contact/success, peak force and combined
contract membership. The second action is evidence and never executes open-loop.
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

Before collection: 19 focused tests; 403 full pytest tests passed. Ruff, compileall,
diff checks passed. Subsequent offline reporting adds two evidence-integrity tests;
it does not alter the recorded policy or rerun inference.
Reference verification: 21 focused tests, **405 full tests passed**; ruff,
compileall and diff checks passed. The later boundary audit adds seven focused
tests; the suite at that checkpoint was **412 passed**. All 19 recorded contract unions
were independently recomputed from the saved task config/predictions and matched. All 261 local
documentation links resolved before adding the progress-figure link below.
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

The lookahead extension adds six more regression tests. Current verification is
**418 full tests passed**, ruff and compileall passed.

## Original one-step result: genuine approach, no drawer closure

One model episode, on committed implementation
f39e7111dca4906a378d5baa1151968d5eeba01c. The full runtime source was clean.
Local Laya content ID:
9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704.
CUDA/bfloat16, unchanged model/config; no CPU fallback.

- 18 genuine Laya calls/executions; 3–7 offered candidates per call.
- 19 complete 27-action previews; all full-context restoration checks passed.
- 17 actual outcomes fed into subsequent Laya calls; the 18th was admitted at
  the next observation boundary, but no 19th model call was made.
- 144 actual controls; 7.2 seconds simulated execution; approximately 71.5 seconds
  total wall time including startup and evidence writes, not a latency benchmark.
- Surface gap: **93.484405 -> 2.732324 mm**.
- Drawer opening: **151.659013 -> 151.659013 mm**; actual closure **0 mm**.
- Actual target contact remained false; official task success remained false.
- Every executed primitive matched its predicted simulator endpoint with maximum
  error **0**; closure, surface-gap change, contacts, force and duration also matched.
- Input size 287–405 tokens. All 18 heading/option/state audits and actual consumed
  token checks passed. No invalid choices, singleton executions or fallbacks.
- Six nominal tracking flags remain (steps 12–17, maximum translation error
  4.311 mm). These are disclosed deviations from the old reset reference envelope,
  not hidden or confused with preview/execution mismatches.

The unchanged contracts admitted only approach_target actions throughout this
episode. Consequently, gap reduction does not by itself establish Laya's ability
to distinguish approach from closure: code had already imposed an approach-effect
condition on every offered action. No closing/contact decision competence was
demonstrated.

Action sequence, in execution order:

```text
x+3mm × 10
x+10mm × 2
x+40mm × 1
rotate_x+10deg × 5
```

### Exactly what Laya saw

The fixed instruction is above. At decision 0 the state was:

```text
Task: close top drawer. effect_source=oracle_sim; privileged=true. Preview up to 8 controls/0.4s. XYZ world mm; rotations world degrees; nominal commands, predicted dynamics; grip retained except open/close.
Current opening=151.659mm gap=93.48mm target_contact=0 obstacle_contact=0 grip=open finger_gap=76.45mm.
Last actual: none.
Effects: action|closure_mm (positive closes)|gap_reduction_mm (positive approaches)|target_contact|obstacle_peak_N|success|controls
x+3mm|0.000|2.42|0|0.0|0|8
x+10mm|0.000|7.89|0|0.0|0|8
x+40mm|0.000|29.11|0|0.0|0|8
z-40mm|0.000|13.11|0|0.0|0|8
z-10mm|0.000|4.83|0|0.0|0|8
rotate_x+10deg|0.000|4.13|0|0.0|0|8
rotate_z+10deg|0.000|6.75|0|0.0|0|8
```

Options use these native IDs and empty criterion descriptions, so the above
effects appear once. The table order is the consumed option order; JSON object
keys in the recorder are sorted and must not be mistaken for presentation order.
Every subsequent exact input, all logits/responses and ordered candidates are in
the linked evidence, not inferred from action names.

### First concrete failure: boundary 18, before model invocation

At simulation time 7.7 s, all 27 actions were rejected by the existing effect
contracts. None was rejected by the collision-aware obstacle checks; all had
zero predicted obstacle peak force and obstacle-free endpoints.

For collision-aware top_drawer, approach requires at least **2 mm** gap reduction
and closure >= **-0.01 mm**; establishing contact also requires closure >= -0.01 mm.
At this boundary:

| Candidate | Predicted gap reduction mm | Predicted closure mm | Endpoint target contact | Why excluded |
|---|---:|---:|---|---|
| rotate_x+10deg | 2.732324 | -2.215683 | true | Drawer-opening regression exceeds tolerance |
| z-3mm | 2.732324 | -0.108773 | true | Drawer-opening regression exceeds tolerance |
| z-10mm | 2.732324 | -0.265756 | true | Drawer-opening regression exceeds tolerance |
| z-40mm | 2.732324 | -2.670249 | true | Drawer-opening regression exceeds tolerance |
| y+40mm | 2.528604 | -7.235189 | false | Drawer-opening regression exceeds tolerance |
| y-40mm | 1.676634 | 0 | false | Below the 2 mm approach threshold |
| hold / open | 1.225532 | 0 | false | Below the 2 mm approach threshold |

No remaining action predicted positive closure or success. There was no current
contact to release and two-step reposition witnesses were disabled by v1.
The distinct-choice guard therefore stopped **before** another model call or
physical action. The error text mentions needing two distinct operations, but
the actual terminal menu was empty, not a singleton.

Earlier choices led to this state, but the evidence does not establish which
alternative would complete the task, that a temporary opening would recover it,
or that Laya's internal ranking mechanism is the sole cause. The directly
demonstrated bottleneck is loss of admissible continuation under the frozen
one-step effect contracts along this Laya-selected trajectory.

### Bounded dead-end audit

The [complete boundary audit](dead_end_boundary_audit.md) replayed the exact
frozen state, recomputed all 27 previews and exposed every relevant contract
clause. Original Jev commit `3bdad98` and the current reference produced identical
predictions, rejection strings and empty one-step pools. Original
`ValidatedPolicy.choose()` stopped before its policy API. The boundary is therefore
classified **CONTRACT DEAD-END**, ruling out an incorrect one-step contract port.

The archived successful Jev path reached a comparable 2.397 mm gap in a pose
67.185 mm and 47.370 degrees away, where `y-40mm` predicted and produced
30.946 mm closure. Its following `z-40mm` contact transition also predicted and
produced 7.163 mm closure. It did not temporarily reopen the drawer. This shows
that the successful trajectory avoided the same contract state; it does not prove
the failed state lacks a useful physical continuation. The audit did not invoke
Jev's optional two-step witness fallback and does not authorize adding it to v1.

### Original one-step replay and repeatability

The failed trajectory's 144 recorded controls replayed from the original reset
with **0 error at all 163 checked boundaries**. This reproduces the physical
trajectory; it is not a second independent Laya episode. Episodes 02/03 were not
run because v1 requires diagnosing the first failure before success repeats.
**Three-run reproducible task success is not established.**

### Local artifacts and integrity

All paths below are ignored local artifacts, not available in a fresh clone:

- [Per-decision candidates, actions, progress and terminal rejections](../../../runs/privileged-reference/episode-01/reference-report.md)
- [Full model inputs, all predictions and outcome evidence](../../../runs/privileged-reference/episode-01/reference-evidence.json)
- [Raw hash-chained episode](../../../runs/privileged-reference/episode-01/episodes.jsonl)
- [Control replay](../../../runs/privileged-reference/episode-01/replay-check.json)
- [Actual approach and drawer-opening trace](../../../runs/privileged-reference/episode-01/progress.png)
- [Mechanical preflight](../../../runs/privileged-reference/preflight-v01/episodes.jsonl)

Episode raw SHA-256:
5dda05b5c4aadff4c2fa9e8274730dcbe5f502726c3320dcf2f6d4240cf736a7.
Preflight raw SHA-256:
6b9714b41387f86fae40ea851d00c52110eaa1f00d171521f0b2eb785a8e03ad.
Trajectory NPZ files preserve rendered frames, controls and physical states.
Offline summaries also verify hashes, consumed tokens, candidate coverage,
raw endpoint comparisons and actual-outcome links.

### Original one-step stop point

The one-step reference was implemented, exercised and mechanically verified, but
failed its task-success milestone. Contracts remained unchanged. This stop point
led to the bounded dead-end audit and then the separately authorized evaluation
of original Jev lookahead below.

## Existing Jev lookahead result

The complete [two-step witness audit and closed-loop record](two_step_lookahead.md)
shows that the original mechanism repairs the exact empty one-step pool. It finds
32 qualifying pairs and returns 23 witness-backed first tokens, representing 22
physical operations. Several contact-producing first actions temporarily open the
drawer but have positive two-step net closure. The reference implementation
matches original Jev's pool and witness payloads exactly.

On clean commit `3fe6b0d`, a fresh run reproduced the first 18 one-step choices.
At boundary 18, all 23 witness-backed first actions reached Laya without tokenizer
truncation. Laya selected `open`; only that primitive executed, reducing gap from
2.732324 to 1.506793 mm with zero closure and no contact. At the next real state,
one-step contracts admitted only `z-3mm`, predicting `+0.060077 mm` closure and
new contact. The genuine-choice guard stopped before another Laya call or action.

The run made 19 genuine decisions and executions, used 152 controls, and retained
exact prediction/execution agreement. Replay passed 172 state boundaries with
zero error. Official success remained false and no successful repeat runs began.
The first remaining failure is the singleton one-step continuation after Laya's
passive witness-backed transition. No threshold, prompt instruction, hierarchy,
planner, new contract, visual path, CDS, ablation or E0 change followed.
