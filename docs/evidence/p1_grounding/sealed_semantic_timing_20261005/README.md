# Sealed semantic ROI timing — 2026-10-05

This measures the complete geometry workload from the sealed corrected-v2 fixed-query LocateAnything outputs. It makes **no semantic model calls**, consumes no annotation contents, issues no post-reset controls, changes no thresholds or scheduling, and confers no execution authority. All ordered boxes and abstentions are retained. Here every source call returned one box: four boxes per dual-camera bundle.

## Conditions and results

| Condition | Workload | Complete persisted bundle rate | Whole geometry p95 | Single ROI p95 |
| --- | --- | ---: | ---: | ---: |
| Offline, committed | 25 original reset bundles, 100 boxes | 0.1723 Hz | 13,970.397 ms | 7,865.753 ms |
| Fresh static init 0, frozen semantic workload cache | 29 fresh dual-camera bundles, 116 boxes, 10.234 s | 2.8338 Hz | 374.412 ms | 107.513 ms |

These rates concern **different workload distributions**, not an optimization comparison. The offline set includes large wrist-view regions that generate many geometric candidates; the selected init-0 workload returns only UNKNOWN/AMBIGUOUS geometry. Across the offline set, wrist drawer-face ROI p50 is 7,554.686 ms, versus 87.676 ms for agent-view drawer-face ROIs. The geometry algorithm and configuration are identical in both conditions.

Offline processing reproduces every original sealed geometry witness exactly, including original frame IDs and capture clocks. Its wall freshness is deliberately unevaluated. Geometry statuses: 53 UNKNOWN, 29 AMBIGUOUS, 18 VALID. Geometric VALID does not establish semantic identity or action eligibility.

The live test requires every freshly captured RGB image, depth array, K, camera transform and calibration identity to match the selected historical source exactly before reusing its frozen boxes. All checks passed. This is a cached **workload** test, not live semantic grounding or a temporal tracker.

Live timing:

- Requested rate: 10 Hz; all 29 scheduled deadlines missed.
- Capture-to-complete-geometry-result p95: 379.731 ms; capture p95: 6.583 ms. The cold first capture was 150.753 ms; no warmup is silently removed.
- Publication means diagnostic serial result availability, **not** P0 state-store installation or servo delivery.
- Payload persistence p95: 6.320 ms; completion-sidecar overhead p95: 1.290 ms. The latter includes receipt hashing/construction plus sidecar fsync.
- Publication-gap p95: 370.722 ms.
- Source wall ages at publication: 0.324–0.576 s; source simulator ages: 0 s because the static world is not stepped.
- 0/116 ROIs satisfy the existing 0.3 s free-space or 0.2 s contact freshness bound. No semantic freshness or policy eligibility is inferred.
- Statuses: 58 UNKNOWN, 58 AMBIGUOUS, no VALID outputs.

Observed failure to meet the serial complete-bundle deadline is established under this shared-host condition. This is not an isolated hardware ceiling, architectural impossibility claim, or evidence that changing thresholds is warranted. LocateAnything inference latency is excluded throughout.

## Provenance and preserved attempts

Implementation: `446a42ecd4f35757917c323c87bdd61a2294423b` (`p1_semantic_roi_timing.py` and seven passing tests). The canonical offline run identifies that commit. The live run identifies `8860d6c730edd9e3a195e6d776b06b6e08f2f6c3`, which adds separate temporal diagnostic tooling; timing and frozen geometry source/configuration hashes are unchanged.

Source: `runs/p1/corrected-v2-fixed-query-evaluation-20261005`. Registration, ordered requests/predictions, prediction seal, source recordings, RGB hashes and geometry hashes are checked before processing. The code does not read human annotation contents.

Preserved outputs:

1. `runs/p1/sealed-semantic-roi-offline-timing-20261005`: exploratory precommit run, clearly excluded as the canonical measurement. Its manifest, summary and persistence receipts remain; duplicate bulk `cycles.jsonl` was retired after exact comparison of all 25 ordered bundles / 100 boxes against the committed canonical run. Exploratory per-cycle timing detail is no longer retained.
2. `runs/p1/sealed-semantic-roi-offline-timing-committed-20261005`: committed offline measurement.
3. `runs/p1/sealed-semantic-roi-live-static-timing-20261005`: failed startup, missing `LIBERO_ROOT`; no simulator creation, sensor processing or execution.
4. `runs/p1/sealed-semantic-roi-live-static-timing-env-fixed-20261005`: fresh static run after supplying the documented environment variable. No source/configuration relaxation.

The canonical offline and live runs preserve `manifest.json`, all per-box results in `cycles.jsonl`, payload-completion receipts, completion-overhead intervals and `summary.json`; the live run also records original new RGB-D frames. This directory's `summary.json` contains source paths, exact revisions, summaries, per-camera/entity timing breakdowns, and SHA-256 digests. Every completion receipt was checked against its serialized cycle hash: 25 exploratory, 25 canonical offline and 29 live records.

`cleanup-ledger.json` records the exploratory retention change, deleted file digest, retained compact file digests, receipt hashes and exact geometry-equivalence checks. The comparison excludes only per-box timing fields; original source clocks, ordered boxes, complete geometry candidates/effects and provenance must match. Deleting the duplicate exploratory raw cycles reclaimed **32,453,199 bytes (30.950 MiB)**; the compact ledger is 9,328 bytes. No canonical offline/live raw evidence or small startup-failure record was removed.

## Reproduction

Use the existing `laya-embodied` Python environment and a **new** output directory; never overwrite a preserved attempt.

```sh
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m embodied_runtime.experiments.p1_semantic_roi_timing \
  --sealed-run runs/p1/corrected-v2-fixed-query-evaluation-20261005 \
  --output NEW_OFFLINE_DIRECTORY --mode offline

MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=1 LIBERO_ROOT=/home/junhongli/projects/LIBERO \
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m embodied_runtime.experiments.p1_semantic_roi_timing \
  --sealed-run runs/p1/corrected-v2-fixed-query-evaluation-20261005 \
  --output NEW_LIVE_DIRECTORY --mode live-static --init-index 0 --live-duration-s 10
```

The ten-second limit prevents starting a new cycle after its deadline; an already-started cycle completes and actual elapsed time is reported. Standard reset settling controls remain explicit infrastructure, not experiment actions.
