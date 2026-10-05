# P1 static sensor diagnostic evidence

See [the checkpoint report](../../../p1-rgbd-checkpoint.md) for condition, measured
results, limits and reproduction. **P1 task acceptance is not passed.**

- `manifest.json`: clean canonical revision, configs, source/package/external
  repository identities and reset controls.
- `summary.json`: capture-process results; `replay-summary.json`: fresh-process
  exact result comparison. `replay-manifest.json` binds original capture metadata.
- `geometry.jsonl.gz`: all 200 records, all raw fit metrics/reasons, all candidates
  in their original order, separate diagnostic/tracked outputs and provenance.
- `plane-consistency.json`: all 50 unmerged assumed-table-plane comparisons.
- Both camera contact sheets: all 25 fresh-reset views. Boxes are diagnostic
  seeds, **not independently validated semantic labels**.
- `examples/`: init-0 RGB/depth/plane/candidate panels and complete projection
  metadata. Amber points mean execution status UNKNOWN.
- `sensor-sample-init000.tar.gz`: unmodified init-0 raw `.npy` blobs, R4 envelopes,
  sealed identity sidecar and recording metadata. It is a **subset** of the full
  collection, not a complete standalone 25-init replay condition.
- `raw-artifact-checksums.json`: every file in the canonical local collection.
- `tests.txt`, `lint.txt`, `dependencies.txt`, `test-command.txt`: verification.
- `checksums.json`: every tracked evidence file's SHA256, excluding itself.

For sample-only sensor inspection, extract the archive into a new directory and
use `embodied_runtime.perception.recording.replay_frames(path / "init-000")`.
For full matched replay use the complete original collection or reproduce fresh
capture. No original artifact is overwritten by replay.

Calibration is simulator camera configuration plus known robot base/FK; task
oracle state is excluded. This is not physical-sensor calibration evidence.
There are no model outputs, robot runtime actions, real temporal sequences,
independent human labels or official success measurements in this collection.
