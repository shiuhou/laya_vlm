# Frozen four-cell POINT-anchor temporal transfer

This prospective feature protocol transfers the existing descriptive LK/depth/
own-TCP estimator once to the completed physical whole/neck × close/open-hold
matrix. All four conditions remain regardless of mechanical outcome. Original
RGB inspection and source admission are already complete; no temporal features
have been computed for this matrix. The physical collector and its review remain
separate from this stored-only extraction.

## Exact source and computation

Raw root: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research`.
Use only `task2-point-anchor-grasp-transfer-run-01`, with matrix journal SHA-256
`39d2a972869d98944bdfb29cce721174cdb9d617ec3696b5139ac5ffd8b139f4`.
The completed sensor admission at
`task2-point-anchor-grasp-rgb-inspection-01/source-admission.json`, SHA-256
`6d283ad5d098ea1e532e82aaf95464df796a01a1cce05e96dd9dae1a9e969681`, binds all
eight sensor manifest/seal hashes, all 186 NPZ hashes, source journals, complete
matrix/replays, initial arrays, source metadata, and exact sensor prefixes.
Revalidate these sensor inputs through the unchanged adapter. The independent
physical audit is bound by SHA-256
`6051e9a498f73e8399b232a2d64b9a0174e8e0ab8d3187cffdb69a4c31a9a018`; hash its bytes
only. Do not decode the mechanical audit or source journals for extraction.

The adapter `task2_point_anchor_retention_adapter.py` is pinned to SHA-256
`59c5c6bcb6198cbc3f7d94bfd09b91aa515a0f82ab14b82e53c2eb55483694f2`. It pins the
unchanged tracker, summary, corrected nearest-center association and prior
transfer helper hashes. The complete source, schema and arithmetic contract is
in [the source plan](task2_point_anchor_retention_source_plan.md). No helper,
threshold, seed, seed order or reference changes are permitted here.

Use all 492 original row-major seeds in `[212,169,224,210)`, including initially
outside-proxy seeds. Run one unchanged chronological tracker call per seed/cell
in order whole-close, whole-open_hold, neck-close, neck-open_hold. Retain 47, 47,
46, 46 captures, respectively: **1,968 tracks and 91,512 rows**. Whole cells each
have 23,124 rows; neck cells each have 22,632. The sole displacement reference is
the preclose merged capture 30 for whole and 29 for neck. Merged capture indices
are zero-based; original stream capture sequences remain one-based.

LK settings remain `winSize=(21,21)`, `maxLevel=3`, `criteria=(3,30,.01)`, `flags=0`,
`minEigThreshold=.0001`. Native forward/backward statuses are the only RGB gates;
residuals have no cutoff. Native failure is permanent, and attempted coordinates,
failure rows, later unknowns and all nulls remain. No smoothing, reseeding,
survivor cohort, repair or retuning. Nearest sampling is `floor(x+0.5)` and
backprojection uses selected pixel index+0.5 with saved K/T, finite inclusive
0.01–5 m depth, unchanged preclose deltas and fixed-denominator summaries.
There is no holding classifier or transferable calibrated co-motion threshold.

## Extraction environment and admission

The extraction environment is distinct from the physical collector environment.
Pin `/home/junhongli/miniforge3/envs/locateanything/bin/python`, Python
`3.10.21 | packaged by conda-forge | (main, Aug 21 2026, 22:42:31) [GCC 14.4.0]`,
OpenCV `4.11.0`, NumPy `1.26.4`, OpenCV's observed **256 threads**, and OpenCV build
information SHA-256 `f3f58b60f58039df358dceb98f617583025ea7b080b4b3b5c84cc15ef13edf09`.
No thread or OpenCV setting is modified. Preflight and execution must match these
values exactly. Run with `PYTHONDONTWRITEBYTECODE=1` from the clean frozen tree.

The wrapper has only `preflight` and `run` modes. Preflight validates stored
sensor sources and the existing synthetic coordinate convention check; it makes
zero archived LK, projection or displacement computations, model, physics or
render calls. It records the clean commit/source identity, protocol hash, runtime,
LK settings, source admission and expected counts.

Actual extraction requires independent review of that exact clean freeze and
source-only preflight. The compact JSON review receipt has `status: "pass"`,
`freeze_commit`, `preflight_sha256`, `protocol_sha256`, and `authorized_batches: 1`.
Additional explanatory fields are permitted. The wrapper checks these exact
bindings and revalidates sources before extracting. Root's existing authorization
permits the reviewer to release this one fixed batch after PASS.

Registered output: `task2-point-anchor-retention-transfer-run-01`. The wrapper
requires that exact new directory and never resumes or overwrites it. Invoke:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/junhongli/miniforge3/envs/locateanything/bin/python -m embodied_runtime.experiments.task2_point_anchor_retention_transfer preflight --output /absolute/new/preflight.json
PYTHONDONTWRITEBYTECODE=1 /home/junhongli/miniforge3/envs/locateanything/bin/python -m embodied_runtime.experiments.task2_point_anchor_retention_transfer run --output /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-point-anchor-retention-transfer-run-01 --preflight /absolute/reviewed/preflight.json --review /absolute/review.json
```

## Complete outputs and failure retention

Write four append-only track JSONL files, flushing/fsyncing after each complete
trajectory. Include every native field, source provenance/time/null, sampled
surface, saved own TCP and preclose delta. Identity and holding remain null.
The complete 186-capture summary uses denominator 492 everywhere and retains
counts, reference-valid counts, missing counts and median/q25/q75 for all four
existing metrics. No second initial reference is added.

Compare the original nine native fields for all 492 seeds over the 31-capture
whole close/open prefix, 30-capture neck close/open prefix, and six-capture
whole-close/neck-close common prefix. Record all **32,964 row comparisons** with
nine individual equality flags plus complete mismatch lists and counts. No
comparison extends beyond the registered common prefix. A mismatch never
changes tracks; finish and seal the complete batch, then record failure.

The sensor seal covers all four track files, full summaries and prefix records,
copied protocol/preflight/review/source receipt, admitted source bindings, and
run configuration/manifest. Journal records link the sensor seal before terminal
status; the final artifacts receipt binds all outputs and the closed journal.
A runtime exception or interrupt retains already written rows, hashes all
retained files, records active cell/completed tracks/written rows with zero retries,
and never produces a complete sensor seal unless the full batch was already
sealed. A hard process kill may leave a partial final line; it is not a completed
row and cannot be interpreted as a completed batch. No automatic retry is allowed.

There are no bottle masks in this source, no membership/departure evaluator,
no new render/FK/model/physics calls, and no holding decision. Reporting and any
external comparison with mechanical evidence follow complete sensor sealing and
independent output review. Reports must retain all conditions, missing values and
the descriptive interpretation; motion cannot establish semantic identity,
contact, support-free retention, task success or anchor superiority.
