# Frozen POINT + BOX identity development diagnostic

Execution `b7f54092`, baseline `34486e3`; condition
`p1-point-positive-sam-repair/1`.50 POINT calls,16 SAM calls,48 all-native
masks/geometry outputs,102 planned slots NOT_EVALUATED.0 task-valid candidates.
No retries, thresholds/query/weights changes or downstream control/model runs.
This reused exposed50-frame set is development evidence, not P1 acceptance.

[Full result](../../../p1-identity-prompt-results.md),
[prospective protocol](../../../research/p1_identity_prompt_protocol.md).

- [Registration and source hashes](registration.json)
- [Machine scoring summary](summary.json)
- [All50 frame outcomes](all-frames.csv)
- [All150 planned native slots](all-planned-native-slots.csv)
- [Source/stage provenance and field caveats](provenance-index.json)
- [POINT fresh-process receipt](points-process.json)
- [SAM fresh-process receipt](masks-process.json)
- [Geometry compute context/timing caveat](geometry-process-context.json)

Raw outputs remain in `runs/p1/identity-point-sam-20261007/`:
points (raw/native token audits+input receipts), masks (all native NPZ), geometry
(all proposals/metrics/stage ledgers), scoring, all ten review and ten point-review
sheets. The tracked raw-output companion and authenticated archive inventory
are recorded in `archive-index.json`; no failure sample is removed.

Original RGB-D inputs and BOX corpus are reused, not recaptured or repackaged.
Their hashes are pinned in registration. The original Formal-50 full-evidence
companion contains original source recordings:
`runs/p1/formal50-native-masks-20261007-full-evidence.tar.gz`, SHA256
`d5278a798f5ff222e30939741d4d763e917be25248672cb8bba340f4334b0c1a`.
The new companion includes complete new outputs, not duplicated checkpoints,
weights or original sensor recordings. Reproduction needs the original companion,
local pinned checkpoints and dependencies as well as this repository revision.

Reproduce in a **fresh** output directory after checking out the execution commit:

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_identity_prompt prepare --output NEW_RUN
.venv-p1/bin/python -m embodied_runtime.experiments.p1_identity_prompt launch-points --output NEW_RUN --gpu-uuid AVAILABLE_GPU_UUID
.venv-p1/bin/python -m embodied_runtime.experiments.p1_identity_prompt launch-masks --output NEW_RUN --gpu-uuid AVAILABLE_GPU_UUID
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_identity_prompt geometry --output NEW_RUN
.venv-p1/bin/python -m embodied_runtime.experiments.p1_identity_prompt score --output NEW_RUN
.venv-p1/bin/python -m embodied_runtime.experiments.p1_identity_prompt review --output NEW_RUN
```

This is an archival recipe, not a request to repeat inference. The stage guards
require original baseline/source paths and receipts; the registration intentionally
fails if they or frozen source bytes differ. Relocated archives need an explicitly
identified relocation verifier, never edited hash receipts or silent fallbacks.
