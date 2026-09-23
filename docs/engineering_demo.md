# A live visual Laya connectivity demonstration

2026-09-23, after baseline `3be0fc5`. Engineering communication artifact only.
One live trajectory; no policy search, task-success tuning, E0 or E1.

For current commands, the offline HTML inspector and a fresh verified successor run,
see [demo_runbook.md](demo_runbook.md). The historical result below is preserved.

## Watch and inspect

- [12-second annotated MP4](../runs/engineering-demo/top-drawer-init0-seed1-v01/demo.mp4)
- [Animated GIF](../runs/engineering-demo/top-drawer-init0-seed1-v01/demo.gif)
- [Trajectory contact sheet](../runs/engineering-demo/top-drawer-init0-seed1-v01/contact-sheet.png)
- [Generated trajectory report](../runs/engineering-demo/top-drawer-init0-seed1-v01/demo.md)
- [Full model inputs, outputs and execution evidence](../runs/engineering-demo/top-drawer-init0-seed1-v01/demo-evidence.json)
- [Raw hash-chained records](../runs/engineering-demo/top-drawer-init0-seed1-v01/episodes.jsonl)
- [Control replay verification](../runs/engineering-demo/top-drawer-init0-seed1-v01/replay-check.json)

These are local, ignored run artifacts, not committed media. The commands below
reproduce the data path in the existing environment. The video uses actual frames
captured after each control, not reconstructed or generated robot motion. Motion
plays at 0.5x; inference pauses are shortened. The side panel explicitly shows
action-end telemetry even during the preceding decision pause. A green box on
decision frames is the detector's selected support, not an oracle annotation.

## What actually ran

```text
LIBERO top_drawer, init_state_id=0, seed=1
  -> calibrated agentview RGB-D, simulation paused
  -> local LocateAnything + depth (existing first-box estimator)
  -> ObservationEvent -> MultiRateFusion -> BeliefSnapshot
  -> existing visual hard-validity candidate gates
  -> compact CanonicalDecisionState v0.1 + permitted nominal action semantics
  -> real local LayaProvider (audited tokens; no effects/history)
  -> unchanged Runtime identity/expiry/membership validation
  -> unchanged AtomicExecutor and native Jev/robosuite controller
  -> MuJoCo execution, frames, actual gripper/TCP telemetry
```

The simplest verified configuration was the existing reset, not a new task.
Task binding: `libero_90/KITCHEN_SCENE10_close_the_top_drawer_of_the_cabinet`.
The fixed query is `the metal handle on the top drawer of the small freestanding
wooden cabinet in the foreground`.

The opt-in `engineering_demo` bridge reuses existing CDS fields and compact
serialization. It offers **exactly** the live gate's permitted tokens, in the shared
nominal vocabulary's order. It does not rank actions or insert recommended choices.
Natural soft direction/progress metadata remains in the audit but is not supplied
as candidate effects. Model history is empty. Its explicitly demo-specific question
requests a task action and warns that validity is not collision approval; it does
not call this live decision an offline probe. Neither the legacy runner nor the
research pairing interface was changed.

Each decision waits for a new RGB-D result at the same physical boundary. This is
a disclosed synchronous demonstration schedule, not a relaxed uncertainty gate or
a measurement of asynchronous robustness. All four geometry ages are 0 s; original
validity thresholds, heuristic covariance and tracking-inactive status remain.

## What Laya decided

| Step | Laya choice = executed token | Returned P(choice) | Actual finger gap, mm | Actual TCP displacement XYZ, mm |
|---|---|---:|---|---|
| 0 | GRASP | .2886 | 76.45 -> 20.81 | +.035, +.118, +.028 |
| 1 | RELEASE | .1879 | 20.81 -> 57.43 | +.019, +.106, +.015 |
| 2 | GRASP | .3220 | 57.43 -> 20.57 | +.017, +.081, +.013 |
| 3 | RELEASE | .1974 | 20.57 -> 57.43 | +.015, +.057, +.012 |

Every boundary had **ten permitted choices**, including all translations, both
rotations and STOP. The gripper gate alternates GRASP/RELEASE availability as the
retained command changes; it does not force Laya to pick either. All four responses
are genuine `source=laya`, with no singleton choices or validation fallbacks.
We cannot infer an internal rationale from these choices.

Four actions produce 32 low-level controls and 32 recorded execution frames,
advancing simulation from .5 to 2.1 s. No failure events or reset-contract flags.
Actual consumed tokens match the input audits: 588–594 tokens, under the unchanged
1024-token model limit, with no heading/option/state clipping. Model latencies
including observation hooks: 30.5–61.1 ms. Vision inference: 2.42–2.68 s per capture.
Whole run: approximately 31.8 s including startup/hashing. Not a latency benchmark.

The drawer remains at **151.659 mm remaining opening** throughout; no target
contact, no task success. This is observable opening/closing of the gripper in
free space, not a successful grasp or drawer operation. We retained the first live
run rather than selecting a more successful or visually appealing trajectory.

## Reproducibility and evidence boundaries

The exact benchmark initial-state vector is fingerprinted in `demo_initial_identity`;
seed and benchmark index are separate. RGB-D arrays, calibration, accepted events,
full natural snapshots, compact inputs, questions, raw model responses/logits,
token audits, validated intents and physical action outcomes are linked by IDs.
Trajectory NPZ files contain controls, pre-control simulator states, endpoint state
and rendered frames. All control and frame artifacts are hashed.

A fresh simulator reset followed by replay of the **recorded low-level controls**
reproduced all 37 checked boundaries (initial + 32 pre-control + four endpoints)
with maximum recorded state error **0**. This establishes local trajectory replay,
not bitwise reproducibility of a second full vision/model run or another machine.

Simulator target/contact/progress telemetry is marked evaluator-only. Laya receives
sensor-derived geometry, robot proprioception, task context, quality and explicit
unknowns. Contact, holding, visibility and drawer progress remain unknown. No
simulator preview, oracle target point or privileged progress enters this path.
Camera calibration is supplied by the simulation sensor adapter.

LocateAnything returned extra boxes; the unchanged provider uses its first box.
No oracle filtering corrects detections. Target location/covariance accuracy is
not validated by this demo. Tracking remains inactive; covariance/semantic scores
and Laya probabilities are not calibrated. STOP/GRASP/RELEASE are active controller
commands, not promises of no physical drift. Reset contract checks are not general
safety certificates. Earlier loaded-state anomalies remain valid evidence.

**Engineering conclusion:** the visual model-to-actuator path is genuinely live
and auditable. **Research conclusion:** none about task competence, decision
sufficiency, causal perception effects or the usefulness of an oracle policy.
Formal E0 remains unfrozen and unjustified by this demonstration.

## Commands and environment

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
V=/home/junhongli/miniforge3/envs/locateanything/bin/python
CUDA_VISIBLE_DEVICES=1 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V \
  -m embodied_runtime.experiments.engineering_demo \
  --output runs/engineering-demo/top-drawer-init0-seed1-v01 --steps 4
MUJOCO_GL=egl $V -m embodied_runtime.experiments.engineering_demo \
  --output runs/engineering-demo/top-drawer-init0-seed1-v01 --replay-check
$V -m embodied_runtime.experiments.engineering_demo \
  --output runs/engineering-demo/top-drawer-init0-seed1-v01 --render-report
$P -m pytest -q tests/test_engineering_demo.py tests/test_candidates.py tests/test_decision_interface.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
git diff --check
```

Use a **fresh output directory** for new collection. The live command and replay
both exited 0. Re-rendering media does not execute simulation or model inference.
Verification: **28 focused tests, 244 full tests passed**; ruff, compileall and
`git diff --check` passed. The full suite completed in 4.77 s.
Media generation uses existing Pillow and system ffmpeg; no dependencies, upstream
repositories, model weights or live policy code were modified/downloaded.

Runtime: Python 3.10.21, MuJoCo 3.5.0, robosuite 1.4.1, NumPy 1.26.4,
torch 2.2.0, transformers 4.57.3, laya 0.3.4, CUDA/bfloat16 on GPU 1.
Model content IDs remain the previous local Laya `9fba4af58ef0...` and
LocateAnything `4b5384cddeda...`; complete IDs/source hashes are in the manifest.
Known upstream tokenizer/Gym/robosuite warnings were not patched or suppressed.

The instrumentation was recorded against baseline `3be0fc5` plus logged working
source hashes, not a frozen experimental release. New files are the opt-in demo
runner/bridge, raw-derived media report and focused tests; existing research
schema, live runner, candidate logic and executor semantics are untouched.
