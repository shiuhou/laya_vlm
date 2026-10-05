# Observation-only temporal tooling

`embodied_runtime.experiments.p1_temporal_probe` acquires continuous sequences
after one standard fresh reset. It is experiment infrastructure, not a visual
controller or manipulation runtime. The authoritative case definitions remain
in `p1-temporal-sequence-protocol.md`.

The acquisition schema records task/init/seed, exact ordered `pre`, `boundary`,
`post` operations, a control ceiling and the sealed static evidence SHA256.
Allowed operations are existing translation/rotation/hold primitives. Each is
passed unchanged to original `jev_libero.World.execute`. A temporary observer
wraps `env.step`, forwards the exact original command and return object, and
captures same-exposure dual RGB-D plus robot proprioception after every actual
control. The original method is restored even after failure. The existing
official-success early return is preserved; fewer than eight controls is logged
as an acquisition boundary, never relabeled visual completion.

Robot/environment contacts are inspected only by the evaluation harness before
and after each control. The first observed contact stops that case. This is not
a guarantee against contact inside a simulator substep. Contact evidence and
scene-fixture assignments go only to `evaluator.jsonl`; the sensor analyzer
never opens it. No policy, Qwen or Laya is invoked by this module.

Optional evaluator fixtures change a named non-robot slide joint or body during
an existing hold. Joint ramps use that joint's coordinate; free-body translation
is world-frame; fixed-body translation is in its parent frame. Camera ancestry
and robot modifications are rejected. These fixtures test observation under
actual articulated-scene changes, not robotic manipulation competence. They do
not reset or stitch simulator states, warp RGB or create synthetic occluders.

Each case is only `ACQUIRED_UNINSPECTED`, `STOPPED_BOUNDARY` or `RUNTIME_FAILURE`.
None of these proves that the intended view/occlusion occurred. Raw RGB must be
inspected; missing both surfaces, insufficient motion, or a failed occlusion
attempt is **unsupported**, not successful temporal coverage.

The analyzer requires source-bound seeds and an exact recording hash. Seed
artifacts must exist, match their hashes and contain the same camera, frame,
query and ROI. Real model artifacts additionally declare `seed_source=real_model`
and `evaluation_labels_used=false`. Human evaluation labels are prohibited as
seeds. An empty seed list explicitly logs independent face/reference UNSEEDED
states. Multiple semantic candidates cannot be silently reduced to one.

Each camera and each surface has its own tracker. Original capture gaps in both
clocks remain active; replay never retimestamps frames. This is capture-clock
association analysis, not online freshness. Semantic identity stays unverified.
Geometry VALID does not mean the intended drawer face was found. LOST requires
an explicit new source-bound seed. VERIFY is UNKNOWN without independently
supported reference/flush relations and calibration; this module fabricates
neither. It does not use official success.

An optional `capture_observer(receipt, bundle)` callback can launch/poll a real
semantic experiment process during acquisition. It receives only recorded sensor
data. Actual request/response times must be saved by the caller; inference after
acquisition is not a concurrent delayed-reply experiment. No fake latency or
pretend reply qualifies T10.

Commands (outputs must not exist):

```sh
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=2 \
LIBERO_ROOT=/home/junhongli/projects/LIBERO \
JEV_LIBERO_CONFIG_DIR=/tmp/laya-p1-libero \
/home/junhongli/miniforge3/envs/laya-embodied/bin/python \
  -m embodied_runtime.experiments.p1_temporal_probe acquire \
  --config configs/p1_temporal/T01.json \
  --static-evidence runs/p1/corrected-v2-fixed-query-evaluation-20261005/completed.json \
  --output runs/p1/temporal-observation/T01

.venv-p1/bin/python -m embodied_runtime.experiments.p1_temporal_probe inspect \
  --recording runs/p1/temporal-observation/T01/frames \
  --output runs/p1/temporal-observation/T01/inspection

.venv-p1/bin/python -m embodied_runtime.experiments.p1_temporal_probe analyze \
  --recording runs/p1/temporal-observation/T01/frames \
  --seeds runs/p1/temporal-model-seeds/T01/seeds.json \
  --output runs/p1/temporal-observation/T01/analysis
```

The inspector creates dual-view RGB contact sheets and source-clock/pose-change
summaries. It does not classify visibility or certify temporal case coverage.
Unit tests use synthetic fixtures only to verify preservation, bounds and
information separation; they are not part of the ten real cases.
