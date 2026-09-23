> Historical record; its plans and checkout paths are not current instructions.
> Current authority: [current_state.md](../../current_state.md).

# Stage 2 handoff — experimental interface

Work on 2026-09-22; final review 2026-09-23 (Asia/Shanghai).
Scope completed: P0-C, P0-D, bounded infrastructure smoke and E1
readiness assessment. No formal E1/E2/E3 run or freeze tag was created.

## Repository and environments

Starting revision: `ff7441866bf0b038abe0991fba0beb2f36e978f9`.
Implementation commits:

- `37c5daa`: visual candidate validity, matched inputs, durable records and tests.
- `8e9dc0f`: LIBERO namespace-package provenance fix discovered in real startup.
- `fa90144`: explicit singleton Laya choice, avoiding the installed model's topk(2).

The worktree was clean after these commits. The handoff/index/README update is a
documentation-only successor. No weights, credentials or run directories committed;
no push, downloads or dependency upgrades. `docs/mix.md` was ignored.

Actually used:

```text
Unit/lint interpreter: /home/junhongli/miniforge3/envs/laya-embodied/bin/python
Real models/simulator: /home/junhongli/miniforge3/envs/locateanything/bin/python
Both: Python 3.10.21, numpy 1.26.4, pytest 9.1.1, ruff 0.15.22
Real runtime: MuJoCo 3.5.0, robosuite 1.4.1, torch 2.2.0 (CUDA 12.1),
              transformers 4.57.3, laya 0.3.4, RTX 4090
Jev-LIBERO: 3bdad985b225aeccc39fbe5863c6eea2e81c515a (clean)
LIBERO: 8f1084e3132a39270c3a13ebe37270a43ece2a01 (clean)
Experiment/schema: stage2-smoke-v1 / stage2-evidence-v1
```

## Findings and decisions

Before: eleven nearly unconditional visual candidates, token-priority Rule,
partial Laya state, and action rows buffered until normal completion. A provider
or environment exception could erase the entire episode record.

After: missing/invalid geometry or covariance and missing proprioception veto
pose-dependent actions. GRASP additionally requires semantic/time consistency and
known open gripper state; RELEASE requires a closed command or known holding.
STOP remains an active pose/gripper hold. Optional workspace bounds veto predicted
10 mm endpoint violations; bounds are **unset** for smoke. Moving away, low geometric
progress and imperfect alignment are not hard vetoes. There is no collision or
grasp-affordance guarantee. Ten choices remain available in the fresh real fixture.

Rule now uses the supplied distance-reduction evidence, a versioned greedy approach
baseline, rather than always prioritizing GRASP. This is a disclosed policy change,
not a temporal-management result. It is not a validated drawer-closing controller.
The real task instruction is `close the top drawer of the cabinet`.

Both providers receive the same BeliefSnapshot type and candidate objects, including
all soft metadata. SHA256 identities distinguish belief, candidate set and combined
snapshot. Runtime supplies a deep copy to prevent provider mutation of the control
snapshot. Laya receives the complete structured state plus feasible choice criteria.
The real matched fixture selected different tokens from **identical** input hashes.
Forced single-candidate choices are labeled `source=laya_single_candidate`, with
model latency 0: they are constraints, not learned-model decisions/confidence.

The visual boundary is enforced by source and continuous-field allowlists. Backend
proprioception reads robot observations/retained command, not `world.features()`.
The runner's simulator telemetry is separately marked offline evaluator data;
only execution/success use it in the visual path. Tests make privileged accesses
raise and verify oracle preview is explicitly privileged and uses retained grip.

Tracking remains inactive (`tracking_active=false`, query is track ID).
Covariance is a small first-order depth/box projection heuristic: depth spread/MAD,
2 mm depth sigma floor, 1 pixel floor, 5% box-size pixel sigma, rotated using capture
calibration. Source and `calibrated=false` are preserved. “Provided” covariance in
fusion means an array was supplied, **not** that its coverage is calibrated.
The box-presence score is also explicitly uncalibrated. No hindsight candidate
recall metric was invented: a defensible reference action is not yet defined.

## Evidence model and recovery

Each run has `resolved_config.yaml` (JSON-compatible YAML), `manifest.json`,
`episodes.jsonl`, `summary.csv`, `failures.csv`, and captured frames under `frames/`.
Config is hashed; model bytes, source files and RGB-D files are fingerprinted.
Manifests include commit/dirty state, versions, local model content identities,
upstream repository revisions, actual task binding, and execution settings. Local
model content hashes substitute for unknown upstream checkpoint revision names.

The raw chain is:

```text
vision_capture (RGB/depth/K/T artifact, sequence, capture sim time)
  -> vision_started/completed (wall time, model latency/output, produced event)
  -> observation (event, store admission and fusion diagnostics)
  -> snapshot (full belief/validity/candidates, three content IDs)
  -> decision (original response/probabilities, input IDs, measured latency)
  -> execution_started (validated choice or explicit fallback, execution sim time)
  -> action (atomic contract, before/after pose/grip/contacts, success)
  -> evaluation (separate privileged physical telemetry)
  -> termination / worker cleanup
```

Observation `accepted` is store admission; filter innovation acceptance and used
evidence IDs are separately available in fusion diagnostics/validity. Event receive
wall time is worker event production; observation record wall time is runtime receipt.
Measurement age is simulation-time age, not model wall latency. All completed worker
events are consumed, instead of silently retaining only the last polled result.

Every JSONL row is flushed/fsynced, sequenced and hash-chained. Summaries validate the
chain, snapshot identities, frame hashes and action-to-decision/intent references.
They regenerate only from raw records/artifacts. Exception, timeout, SIGTERM and
normal termination paths preserve prior evidence. A partial last line is reported;
a corrupt complete line is rejected. Intent without completion is
`execution_outcome_unknown`. A run without termination is `run_incomplete`.
Fsync is not a claim of protection from storage failure. Native CUDA hangs can outlast
Python signal handling; hard-kill recovery does not infer whether an action completed.

Three engineering failures were exposed and retained:

| attempt | measured issue | fix / evidence |
|---|---|---|
| rule-seed1-attempt1 | exit 134 after 3 completed actions; worker still alive at two-second join | drain in-flight inference up to 30 s; recovery reports shutdown_incomplete |
| rule-seed1-attempt2 | exit 1 before actions; LIBERO namespace has `__file__=None` | use namespace package path; startup exception preserved |
| laya-seed1-attempt1 | 1 completed action preserved; topk(2) failed on sole feasible STOP | explicit singleton handling without extra fake candidate or dependency patch |

No failed attempt was overwritten. Subsequent attempts are infrastructure validations,
not statistical retries or comparable formal experimental outcomes.

## Important changed files

| path | purpose / behavioral change |
|---|---|
| `embodied_runtime/adapters/physics_preview.py` | state-dependent visual validity, soft evidence, diagnostics, field guard; oracle grip callback |
| `embodied_runtime/runtime_core.py` | candidate metadata, snapshot IDs, full provider inputs, disclosed Rule baseline, explicit singleton Laya behavior |
| `embodied_runtime/runtime.py` | source isolation, durable decision boundary/intent/completion, raw response preservation, execution-time expiry check |
| `embodied_runtime/adapters/libero.py` | robot-only proprioception and retained-command accessor; atomic semantics unchanged |
| `embodied_runtime/vision.py`, `fusion.py`, `__init__.py` | heuristic covariance and explicit uncalibrated provenance; Stage 1 fusion equations unchanged |
| `embodied_runtime/adapters/locateanything.py` | capture/model/queue evidence and in-flight shutdown drain |
| `embodied_runtime/experiments/run_libero.py` | existing single-episode loop integrated with durable records and cleanup/failure handling |
| `embodied_runtime/experiments/records.py`, `summarize.py` | append-only recorder, content identities, independently regenerated tables |
| `embodied_runtime/experiments/matched_fixture.py` | actual Rule/Laya on one logged snapshot, no simulator execution |
| `tests/test_candidates.py`, `test_evidence.py`, `test_worker.py` | validity/interface/isolation, faults/hard exit/recovery, covariance and shutdown contracts |
| `docs/current_state.md`, this handoff, README, vision/history notices | authoritative current-state index and evidence-backed limits |

## Verification commands and outputs

Executed from the repository root, with these interpreter paths:

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
V=/home/junhongli/miniforge3/envs/locateanything/bin/python
$P -m pytest -q tests/test_candidates.py tests/test_evidence.py tests/test_worker.py
# 21 passed in 2.54s
$P -m pytest -q tests/test_atomic.py tests/test_temporal_contracts.py
# 42 passed in 0.34s (Stage 1 tests unchanged)
$P -m pytest -q
# 74 passed in 2.74s
$V -m pytest -q
# 74 passed in 2.75s
$P -m ruff check .
# All checks passed!
$P -m compileall -q embodied_runtime tests
# exit 0
git diff --check
# exit 0
```

Independent atomic calibration was not rerun: P0-A was not changed. Its historical
artifact remains `/home/junhongli/runs/stage1-atomic-final-20260922/`; all six actions
in the final online interface smokes had zero execution contract violations.

Exact successful online commands (fixed seed, three actions; asynchronous wall
scheduling is not claimed bitwise deterministic):

```sh
CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V -m embodied_runtime.experiments.run_libero --experiment vision --provider rule --task top_drawer --seed 1 --steps 3 --vision-warmup-s 30 --timeout-s 180 --device cuda --libero-root /home/junhongli/projects/LIBERO --config-dir /home/junhongli/runs/libero-config --output runs/stage2 --run-id rule-seed1-attempt3
# exit 0; 3 actions, zero failure events, zero contract violations
CUDA_VISIBLE_DEVICES=3 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V -m embodied_runtime.experiments.run_libero --experiment vision --provider laya --task top_drawer --seed 1 --steps 3 --vision-warmup-s 30 --timeout-s 180 --device cuda --libero-root /home/junhongli/projects/LIBERO --config-dir /home/junhongli/runs/libero-config --output runs/stage2 --run-id laya-seed1-attempt2
# exit 0; 3 actions, zero failure events, zero contract violations
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V -m embodied_runtime.experiments.matched_fixture runs/stage2/rule-seed1-attempt3/episodes.jsonl --step 0 --output runs/stage2/matched-seed1-step0 --laya-path /home/junhongli/models/huggingface/laya/typed-decisions --device cuda
# exit 0; identical input IDs, two real provider outputs, zero physical actions
$P -m embodied_runtime.experiments.summarize runs/stage2/rule-seed1-attempt3
# {"completed_actions": 3, "failure_events": 0, "terminated": true}
```

Failed commands used the same respective online arguments with run IDs
`rule-seed1-attempt1`, `rule-seed1-attempt2`, `laya-seed1-attempt1`, before their fixes.
Two consecutive `summarize(path)` calls over **all six** artifact directories gave
byte-identical summary/failure CSVs, including the failed attempts. Test coverage
also includes injected model/environment exceptions, subprocess `os._exit(9)`,
unterminated tail recovery and corruption rejection.

Known upstream warnings (not silently patched): old Gym API, missing robosuite private
macros/dataset directory, tokenizer regex warning, slow processor and Transformers
deprecations. No downloads occurred; model loaders used the installed local weights.

## Representative raw evidence

All evidence paths below are relative to `runs/stage2/`; each online directory has
the five required files plus RGB-D artifacts. Full identifiers are in JSONL.

| run / step | belief ID prefix | candidate-set ID prefix | choice | vetoes / 11 | measured TCP delta, mm | outcome |
|---|---|---|---|---|---|---|
| rule-seed1-attempt3 / 0 | 2d95add510ef | 7ec7aed6b33a | MV_BACK | 1 | [-9.094, +0.119, +0.388] | no success; contract passes |
| rule-seed1-attempt3 / 1 | 82b7cf2b2cc9 | 66a795f02cd3 | STOP | 10 | [-0.739, +0.132, -0.556] | no success; contract passes |
| laya-seed1-attempt2 / 0 | cf12c8c1dfcb | 7ec7aed6b33a | MV_FWD | 1 | [+9.075, +0.115, -0.418] | no success; contract passes |
| laya-seed1-attempt2 / 1 | 4f43bcaea45a | 05570123bc5d | STOP (singleton) | 10 | [+0.697, +0.079, +0.520] | no success; contract passes |

At the Rule fixture's first boundary, MV_BACK and MV_FWD are both feasible, with
soft distance reduction +0.008360 m and -0.008381 m respectively. RELEASE is vetoed
with `holding_state_unknown`. Both providers in `matched-seed1-step0` reference:

```text
belief:    2d95add510ef0a118695e15bcae0b57437539abea3b267e39ad2dbdc78b53d18
candidates:7ec7aed6b33a8fc4f9e122d7dd38b800ca9dc48521346f26a919aa4e77936b38
snapshot:  75cb92604b7a113b7f37566c00d0aea26f7beb05ffe51b1c0e8be0dbf121c149
Rule: MV_BACK; Laya: MV_FWD
```

This tests interface matching, not model accuracy. Online snapshots differ because
receive times and subsequent trajectories differ. Rule smoke used `8e9dc0f`; final
Laya smoke used `fa90144` after the singleton-only fix. No causal outcome comparison
is being made across these smoke revisions.

Initial capture was at sim time 0.5 s. Its worker latency was 2551.49 ms (model
2499.56 ms), but decision-time geometry age was **0 s** because simulation did not
advance during warmup. After one action age was 0.4 s, trace increased from
0.009508 to **0.553508 m²** against the unchanged **0.03 m²** limit. At age 0.8 s
trace was 2.441508 m² and TTL also expired. Only STOP remained; the second completed
vision event arrived during cleanup, was archived but not consumed by a decision.

Drawer `qpos_m` stayed exactly `-0.15165901295563317` through every Rule before/after
evaluation. Robot motion alone is not evidence of temporal target disagreement:
the target is estimated in world coordinates and relative geometry uses current
proprioception. Both final runs ended by action budget, not task success.

## Scientific readiness and next human gate

```text
P0-C: PASS — state-dependent validity, meaningful fresh-state choices, matched inputs
P0-D: PASS — traceable actions, durable failures and reproducible derived tables
Ready to freeze exp-e1-v0: NO
Ready to begin formal E1: NO
```

Smallest remaining blockers, to agree on before additional work:

1. Demonstrate a relevant drawer-closing/contact segment with measurable stale-vs-
   current target disagreement, or select a more informative bounded benchmark.
   Do not infer sensitivity from these static-target approach/STOP records.
2. Review covariance/process assumptions and validity availability using a separate
   mechanism fixture, not outcome-driven threshold tuning. Current defaults become
   STOP-only after one action without a fresh measurement; uncertainty coverage is
   uncalibrated. Establish useful recovery after new information arrives.
3. Implement and test matched V0/latest, V1/temporal, V2/temporal+validity switches
   and deterministic delivery controls. Separate identical-measurement replay
   estimation checks from online trajectory comparisons. None is frozen yet.
4. Fix a paired seed **and initial-state-index** plan. Current init index is always
   0; independent seeds alone do not demonstrate independent task configurations.

Conditional E1 recommendation, not a preregistration: retain Rule for V0/V1/V2 and
one natural plus one controlled-delay condition. Select the additional delay from
measured simulation-age sensitivity before comparing outcomes; **do not freeze
+0.5 s now** given the existing 0.4 s availability collapse. Primary evidence should
separate position/consistency error, invalid-geometry action rate/availability,
recovery, and official task success/action budget. Define the target reference point
before computing simulator-vs-box-centroid position error. Use paired results,
predeclared bootstrap intervals and Wilson success intervals once n is justified.

Freeze checklist after those checks: task binding/assets/init indices and seeds;
query and local model hashes; camera/depth/projection settings and score convention;
atomic frames/scales/control steps; candidate rules/workspace/gripper thresholds;
Rule version/tie breaks; lag/process/measurement/initial covariance and validity/TTL
settings; decision lifetime; capture/delivery/queue timing and controlled delay;
warmup and action/wall budgets; official success predicate; target evaluation point;
failure/summary schema; paired metrics/statistics; environment/source revisions.

STOP for human review. No formal experiment configuration is recommended as frozen
until these evidence-backed mechanism blockers are resolved.
