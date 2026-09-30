# P0 acceptance — 2026-09-30

**P0 A–E contract/scheduling gate: PASS.** This is synthetic engineering evidence,
not a Laya/Qwen result or a physical drawer task result. No neural model, GPU
inference, MuJoCo or LIBERO episode was started.

Implementation branch: `feat/p0-runtime-contracts`. Baseline:
`ea853019d3343ef4cb8eff8a2fdb43a91e760642`. Canonical probe revision:
`e8aebb41fa67a34770f320a819490c862e3f8eef`, with a **clean worktree** at launch.
The documentation/evidence commit following that revision does not change code.

## What is implemented

| Package | Delivered behavior | Main files |
|---|---|---|
| A | Immutable protocol/receipts; frame/request registration; generation/clock/source checks; idempotence; strict config; dependency lock | `contracts.py`, `router.py`, `sensor_api.py`, `configs/p0_runtime.json`, `requirements/` |
| B | Explicit time advancement, pure published reads, existing fixed-lag/OOSM fusion, delayed categorical binding and lineage | `state_store.py`; small categorical guard in `runtime_core.py` |
| C | Canonical base27-v1 in robot_base, all candidates retained, hard-only admission, exact request/hash binding, bounded contracts | `control/action_catalog.py`, `local_candidates.py`, `action_contracts.py` |
| D | Robot-only measurement whitelist, strict policy projection, null uncalibrated confidence, separate evaluator | `sensor_api.py`, `policy_observation.py`, `evaluation.py`; minimal LocateAnything/vision changes |
| E | Owned bounded worker processes, reliable control events, single active contract, cancellation/reset, dual deadlines, measured feedback | `workers.py`, `control/scheduler.py`, `control/servo.py` |

Paths in the table are relative to `embodied_runtime/` unless otherwise stated.
The required proprioception type was committed with A because FrameBundle
validation depends on it; this is a dependency ordering adjustment within D's
planned interface, not an extra architecture layer.

The legacy executor and fusion algorithms were not rewritten. New runtime code
has no task-name branch and does not call the legacy privileged Runtime.step.
The synthetic selector deliberately picks a configured action; it is explicitly
named `synthetic-fixed-selector-v1`, never reported as Laya choice quality.

## Verification

- **279 tests passed** in the isolated, hash-pinned Python 3.10.21 P0 environment.
  This covers the new packages and relevant runtime/fusion/temporal/atomic/
  candidate/vision/worker/decision-interface regressions.
- Ruff passed on new and changed Python modules/tests. `pip check` passed.
- A clean editable install exposed ambiguous setuptools discovery; explicit
  package discovery fixes installation without upgrading the old model stack.
- Independent adversarial tests cover duplicate cancellation, invalid IPC output,
  tighter configured caps, wrong rotation direction/axis, false gripper-completion
  claims and legitimate target replacement.
- A further test advances the clock during validation: dispatch rechecks the
  wall deadline before sending a command, rather than trusting tick-entry time.

The complete suite command and captured output are in
[the evidence directory](evidence/p0/20260930/). Existing historical image-report
tools still need their original Pillow/OpenCV environment; they were not added
to the model-free P0 lock.

## Canonical synthetic trace

The probe recorded **711 events**, **6 candidate sets and 6 model inputs**, each
retaining all **27** candidates in canonical order. The independent raw-trace
audit recomputed **0 expired dispatches, 0 post-cancel dispatches and 0 overlong
segments**. These counts refer to fixture command dispatches, not physical robot
motion after a motor command.

| Case | Outcome inspected in raw trace |
|---|---|
| 2s delay, prospectively configured 3s proposal TTL | Old snapshot revalidated against fresh geometry; two 50ms ticks produce one 5mm segment; nominal 40mm action reports PARTIAL with 35mm remaining; no automatic continuation |
| 2s delay, default 1.2s TTL | PROPOSAL_EXPIRED; zero commands |
| Cancel active contract | One tick occurred before cancellation; remaining motion aborted; duplicate cancel has no additional effect |
| Wall deadline only expires | Aborted after the first tick while sim time was still inside its deadline |
| Sim deadline only expires | Aborted after the first tick while wall time was still inside its deadline |
| Real-wall fake process sleeps 2s | 30 owner-loop updates while inference was pending; reply accepted under a separately preconfigured 10s TTL; one control tick then CONTRACT_EXPIRED; worker shut down and reaped |

The real-wall fixture measured **13.69 Hz mean**, with **85.68ms maximum update
gap**. The fixture performs synthetic geometry/logging plus sleep in its driver;
it does **not** demonstrate stable 20Hz scheduling or real visual servo timing.
Its interrupted segment is recorded as ABORTED with the actual measured 2.5mm
fixture displacement, not rewritten as completion. We did not extend the short
contract to hide this result.

Real-wall and virtual-clock conditions are distinct. Each case's actual config
is preserved in the raw trace; the 3s/10s synthetic proposal budgets were set
before requests, never renewed after late results. The default remains 1.2s.

Evidence:

- [Manifest: commit, configuration, dependencies and source hashes](evidence/p0/20260930/manifest.json)
- [Per-case results and measured feedback](evidence/p0/20260930/summary.json)
- [Complete raw event stream, losslessly compressed](evidence/p0/20260930/events.jsonl.gz)
- [Independent trace audit](evidence/p0/20260930/audit.json)
- [Synthetic source-frame records](evidence/p0/20260930/synthetic_frames.json)
- [Artifact and uncompressed-trace checksums](evidence/p0/20260930/checksums.json)

Local uncompressed evidence: `runs/p0/acceptance-20260930-03/`.
Earlier development/acceptance-01/02 traces remain local; they predate dispatch
clock or terminal-feedback logging fixes and are not counted as independent
reproductions. Synthetic frame records are not RGB images or depth measurements.

## Reproduce

Install using [the dependency instructions](../requirements/README.md). The
existing model/simulator environment is an inventory, not the P0 environment.

```sh
.venv-p0/bin/python -m embodied_runtime.experiments.p0_contract_probe --output runs/p0/new-probe
.venv-p0/bin/python -m embodied_runtime.experiments.p0_trace_audit runs/p0/new-probe/events.jsonl
.venv-p0/bin/python -m embodied_runtime.experiments.p0_trace_audit docs/evidence/p0/20260930/events.jsonl.gz
```

Output directories must be new; previous evidence is never overwritten. Wall
timings can vary; virtual-clock invariants and protocol outcomes are deterministic.
The auditor checks the raw stream independently of the summary, and a regression
test verifies it rejects a deliberately corrupted expired dispatch.

## Important semantic limits

- A box is a detection, not probability 1.0. Uncalibrated confidence stays null;
  geometry quality is independent. The old visual GRASP gate no longer gets
  fabricated semantic certainty. Its behavior is intentionally not claimed to
  be unchanged; the historical privileged drawer executor was not modified.
- Measured width is not a grasp/holding or open/closed completion predicate.
  P0 OPEN/CLOSE feedback remains PARTIAL/GRIPPER_COMPLETION_UNKNOWN without a
  calibrated completion evaluator. Raw width and retained command are distinct.
- SensorPort is a narrow Python capability boundary, not a security sandbox
  against hostile reflection. Policy/candidates/validators receive no world
  object. Only the evaluator owns official success, and its stop notification
  does not become stage evidence.
- Geometry/swept-space validity and selector outputs in the probe are explicitly
  synthetic. Real perception, collision checking, model 27-option token audit,
  confidence calibration, visual completion and physical stopping remain
  unverified.

Next implementation boundary is P1 RGB-D geometry and visible cabinet reference,
then P2 actual deterministic visual servo/B0. The chosen Qwen3-VL/Laya split and
B0–B4 evaluation plan remain intact. No pad↔handle precondition was introduced.

## Commits

| Commit | Purpose |
|---|---|
| `2b8b06c` | Design provenance, isolated dependency lock and packaging |
| `bb85954` | A envelopes, router and prerequisite proprioception type |
| `4f2416e` | B immutable state/association |
| `52a224f` | C complete catalog and action contracts |
| `3680023` | D evidence boundary and confidence correction |
| `e08aedf` | E scheduler, servo, workers and synthetic acceptance |
| `e9e2180` | Recheck deadline at dispatch |
| `247f86b` | Independent raw-trace auditor |
| `e8aebb4` | Persist wall-probe terminal feedback before shutdown |
