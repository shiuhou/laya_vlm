# Stage 1 handoff — P0-A and P0-B

Date: 2026-09-22 (Asia/Shanghai)

This handoff covers only the repository audit, atomic action correctness, and
temporal belief correctness. P0-C, P0-D, and formal experiments have not started.

## Repository

Baseline before this stage: `75d810784fd0d7accfad91cd8c2f550518885638`.
The implementation commit for this stage is recorded after this document is
added. The pre-existing untracked `docs/mix.md` is intentionally left untouched.

Verified environment:

```text
Python 3.10.21, numpy 1.26.4, pytest 9.1.1, ruff 0.15.22
mujoco 3.5.0, robosuite 1.4.1, torch 2.2.0
transformers 4.57.3, laya 0.3.4
```

## Atomic audit

`AtomicExecutor` maps movement tokens to backend world XYZ, rotations to the
backend rotation primitive, GRASP/RELEASE to explicit gripper operations, STOP
to `hold`, and DONE to a success-predicate check. The executor no longer owns a
gripper command. `LiberoWorldBackend` owns the retained command and passes it to
Jev for each primitive; only GRASP and RELEASE change it.

`World.execute()` sends eight robosuite control actions per primitive unless the
world reports success earlier. The verified MuJoCo timestep is 0.002 s, so the
probes observed 200 low-level steps. NO_ACTION advances zero steps. STOP is an
active eight-step hold of the current pose/orientation and retained gripper
command. The OSC controller composes rotation increments in world frame.

The old async telemetry showed MV_FWD gap changes of 55.63–75.25 mm. Independent
reset probes isolated the cause: the old executor supplied `+1` on movement while
LIBERO's open command is `-1`. The fix makes all movement and rotation probes
preserve the command from both open and closed starting states. Reset settling
changes gap by about 0.89 mm; this informed the current calibration envelopes
(`atomic-top-drawer-v1`), which are task-specific rather than universal limits.

| token | expected | final open-state measurement | result |
|---|---|---|---|
| NO_ACTION | no motion or command | 0 mm, 0 deg, 0 gap, 0 steps | baseline |
| SETTLE | characterize drift | 0.17 mm position norm, 0.110 deg, +0.885 mm, 200 steps | baseline |
| MV_FWD | +X, retained command | `[9.075, 0.115, -0.418]` mm, 0.164 deg, +0.885 mm | PASS |
| MV_BACK | -X, retained command | `[-9.094, 0.119, 0.388]` mm, 0.103 deg, +0.885 mm | PASS |
| MV_LEFT | +Y, retained command | `[0.207, 9.496, 0.117]` mm, 0.150 deg, +0.889 mm | PASS |
| MV_RIGHT | -Y, retained command | `[-0.182, -9.565, -0.030]` mm, 0.141 deg, +0.889 mm | PASS |
| MV_UP | +Z, retained command | `[-0.266, 0.137, 9.270]` mm, 0.148 deg, +0.885 mm | PASS |
| MV_DOWN | -Z, retained command | `[0.218, 0.102, -9.306]` mm, 0.108 deg, +0.885 mm | PASS |
| ROTATE_CW | -10 deg world-Z | 9.010 deg, 0.464 mm Y drift, +0.904 mm | PASS |
| ROTATE_CCW | +10 deg world-Z | 9.035 deg, 0.499 mm Y drift, +0.901 mm | PASS |
| STOP | hold retained command | 0.123 mm position norm, 0.105 deg, +0.885 mm | PASS |
| GRASP | close only | 0.123 mm, 0.105 deg, -55.632 mm | PASS |
| RELEASE | open only | 0.123 mm, 0.105 deg, +0.885 mm | PASS |

The 13-token probe was repeated from open and closed states. Initial simulator
hashes and telemetry were identical across repeats, with zero contract violations.
Raw artifact: `/home/junhongli/runs/stage1-atomic-final-20260922/`.

## Temporal audit

The filter now commits a posterior to the lag boundary before pruning, then
replays retained events. Admission and innovation gating are separate. A delayed
capture inside the window is accepted by capture time; duplicate, sequence
regression, too-late, zero-quality, episode-mismatch, and future-capture events
are rejected with reasons and counters. Read-only estimates do not change drop
counters. Geometry and semantic evidence retain capture-time provenance;
publishing fusion does not renew semantic TTL.

| case | result |
|---|---|
| in-order observations | accepted and replayed deterministically |
| delayed within lag | same posterior as ordered arrival |
| too-late / duplicate / sequence regression | rejected without state mutation |
| capture-time out-of-order arrival | accepted when unseen and consistent; replay matches ordered result |
| semantic TTL | capture-derived TTL remains fixed; expired distribution is normalized with unknown mass |
| geometry age / event TTL | estimate remains for diagnostics; `geometry_valid` becomes false with explicit reasons |
| lag pruning | short-lag and full-history filters match position, velocity, covariance |
| semantic/geometry mismatch | evidence IDs, capture gap, and consistency reasons are published |
| invalid event | rejected before store or filter mutation |

Decision-time snapshots publish geometry age, capture/reference times, validity,
invalid reasons, covariance and summary, semantic age/validity, evidence IDs,
temporal consistency, provenance, and resolved versioned `TemporalConfig`.
`Runtime.step()` refreshes this metadata before candidate construction and passes
it to RuleProvider and LayaProvider. The visual adapter still lacks measured
position covariance, so its configured fallback is tagged
`measurement_covariance_unverified`.

## Modified files

| path | purpose |
|---|---|
| `embodied_runtime/adapters/libero.py` | retained gripper command, world-frame contract evidence, low-level trace |
| `embodied_runtime/adapters/callback_backend.py` | retained command support for callbacks |
| `embodied_runtime/runtime_core.py` | strict event/store/snapshot/executor contracts |
| `embodied_runtime/runtime.py` | fusion admission and decision-time diagnostics |
| `embodied_runtime/fusion.py` | posterior-preserving fixed lag, admission, TTL, provenance, validity |
| `embodied_runtime/experiments/calibrate_atomic_actions.py` | repeatable raw calibration and regenerated summaries |
| `embodied_runtime/experiments/run_libero.py` | resolved temporal and execution evidence fields |
| `configs/temporal_stage1.json` | versioned Stage 1 temporal defaults |
| `tests/test_atomic.py` | atomic and execution-contract regressions |
| `tests/test_temporal_contracts.py` | deterministic delayed/order/TTL/pruning/validity tests |
| `docs/stage0_audit.md` | pre-modification factual active-path audit |

## Verification

```text
python -m pytest -q                         54 passed in 0.40s
python -m ruff check .                      All checks passed!
python -m compileall -q embodied_runtime tests  passed
python examples/fake_run.py                 five expected FakeBackend moves
python -m embodied_runtime.experiments.calibrate_atomic_actions ...
                                             13 probes, zero contract violations,
                                             200 low-level steps per executed token
```

The calibration emitted the expected robosuite private-macro and LIBERO dataset
path warnings; they did not change the deterministic results. Upstream checkouts
were not modified: Jev-LIBERO `3bdad985b225aeccc39fbe5863c6eea2e81c515a`,
LIBERO `8f1084e3132a39270c3a13ebe37270a43ece2a01`.

## Open risks

Thresholds are calibrated on `top_drawer` and require review before another task.
Visual covariance is still a configured fallback. The real vision path uses the
query as `track_id`; QueryTrackManager remains inactive. Candidate validity and
full experiment instrumentation are intentionally deferred to P0-C/D. No formal
E1 outcome or task-level reliability claim exists.

## Readiness

```text
P0-A: PASS
P0-B: PASS
Ready for P0-C/D: NO
```

Stop here for human review of atomic semantics and temporal belief correctness.
