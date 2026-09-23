> Historical record; its plans and checkout paths are not current instructions.
> Current authority: [current_state.md](../../current_state.md).

# Vision model selection

Historical model/design notes. For verified active behavior, see
[current_state.md](../../current_state.md): real query tracking is inactive, covariance
is heuristic and uncalibrated, and formal experiment readiness is not established.
Current evaluation targets [oracle-to-belief decision equivalence](../../research.md),
not full simulator reconstruction. A query-box/depth point is not automatically
the same reference point as simulator target geometry; the paired exporter marks
this distinction explicitly. Temporal validity remains part of decision sufficiency.

The newer [reference-quality pilot](../../evidence/decision_interface/reference_pilot_protocol.md) uses a separate,
explicit foreground-handle query and a box-support visible-surface centroid. It
preserves the old bbox/interior-median-depth point as raw evidence. Oracle geometry
is used only to evaluate membership/position, never to correct the sensor box or
fill perceptual contact/progress. This diagnostic estimator is not an automatic
replacement for the historical live RGB-D path below. Its covariance is the old
box-projection heuristic, explicitly uncalibrated for this centroid estimator.

## Decision

The first visual-semantic prototype uses NVIDIA LocateAnything-3B as an asynchronous
localization provider, paired with RGB-D depth and a deterministic tracker. Model weights
are intentionally not included in this repository.

Official sources:

- Research page: https://research.nvidia.com/labs/lpr/locate-anything/
- Model: https://huggingface.co/nvidia/LocateAnything-3B
- Code reference: https://github.com/NVlabs/Eagle/tree/main/Embodied
- Dataset: https://huggingface.co/datasets/NVEagle/LocateAnything-Data
- Paper: https://arxiv.org/abs/2605.27365

The official research page describes LocateAnything as a 3B vision-language grounding
model. Its native input is an image and a natural-language query. Its output is visual
localization: boxes or points. Parallel Box Decoding predicts geometric units in one
parallel step; Hybrid Mode uses the fast parallel mode and falls back to autoregressive
decoding for format or spatial ambiguity. The reported throughput is 12.7 boxes per
second on a single H100 in the benchmark configuration.

Those numbers are not an end-to-end robot rate. They exclude camera capture, depth
projection, tracking, serialization, GPU contention and task predicate evaluation. The
runtime must measure p50/p95 latency on the target RTX 4090 server.

## What LocateAnything provides

For each query such as `the red mug` or `the plate`, the provider can return:

```json
{
  "query": "the red mug",
  "boxes_xyxy": [[120, 80, 245, 260]],
  "points_xy": [[182, 170]],
  "score": 0.91,
  "source": "locateanything-3b",
  "frame_id": "agentview",
  "capture_sim_time": 4.2
}
```

The exact response parser belongs in an adapter and must be tested against the released
checkpoint/API. The model should be queried for a small set of task-relevant entities,
not asked to describe the whole scene.

## What it does not provide

LocateAnything does not by itself provide:

- metric depth or a 3D pose;
- temporal object identity tracking;
- gripper contact or holding state;
- collision-free action feasibility;
- task success or goal predicates;
- a reliable affordance such as “safe to grasp now”;
- the next Show-Harness atomic action.

Therefore LocateAnything plus depth is not the whole perception system. It is a 2D
localization measurement source.

## RGB-D integration

The perception pipeline is:

```text
RGB frame + query
  → LocateAnything boxes/points
  → depth at robust interior samples
  → camera intrinsics/extrinsics
  → 3D observation in world/base frame
  → track association
  → semantic belief with age/confidence
  → candidate/action feasibility
```

Depth must not be sampled from one center pixel. Use the median of valid interior depth
samples, reject missing/outlier depth, and record the valid-sample ratio. The adapter
must carry `frame_id`, capture timestamp and calibration version. If the transform to
world/base is unavailable at the capture time, mark the measurement stale instead of
using the current transform silently.

The output written to BeliefStore should look like:

```json
{
  "track_id": "mug_1",
  "category_belief": {"red_mug": 0.86, "blue_mug": 0.05, "unknown": 0.09},
  "position_m": [0.12, -0.08, 0.31],
  "position_covariance": [[0.002, 0, 0], [0, 0.002, 0], [0, 0, 0.004]],
  "visible": true,
  "age_s": 0.08,
  "source": "locateanything+depth",
  "valid_until_sim": 4.65
}
```

## Scheduling

Initial engineering budgets, to be measured rather than assumed:

- RGB-D capture and structured state: every environment step or 10–20 Hz;
- LocateAnything: 0.5–2 Hz or on target ambiguity, scene change, target loss and action failure;
- Laya: every atomic-action boundary, using the latest valid BeliefSnapshot;
- Show-Harness executor: environment control frequency.

LocateAnything must run in a single worker with a latest-frame queue. It must never block
the executor or Laya. Each result is accepted only if its capture sequence, TTL and track
association are valid. Repeated queries for the same frame/source are deduplicated.

## Is this sufficient for the first experiment?

Yes, for a bounded first experiment whose semantic question is object localization:

- identify the referenced object under color/category/position perturbations;
- fuse its 2D localization with depth;
- choose among legal atomic actions with Laya;
- verify success using the environment predicate and physical feedback.

No, for a claim of general visual task understanding. Language/task perturbations still
need explicit instruction parsing and goal-predicate handling. Graspability and spatial
relations need deterministic geometry/contact checks or a separate calibrated semantic
provider. LocateAnything should not be asked to replace those checks.

## Evaluation matrix

Keep the same Show-Harness executor, candidate contracts and Laya provider in every row:

1. oracle object state + rule decision;
2. oracle object state + Laya;
3. LocateAnything + depth + rule decision;
4. LocateAnything + depth + Laya;
5. structured-only baseline without visual semantic localization.

Report object localization precision/recall, 3D position error, track switches, semantic
Brier/ECE, stale/late drops, Laya decision age, candidate vetoes and task success. Do not
report a simulator-oracle result as visual performance.
