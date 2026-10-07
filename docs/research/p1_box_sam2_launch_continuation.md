# P1 BOX / SAM2 launcher correction — 2026-10-07

Predecessor `5e04055` froze the first attempt: BOX stage passed, SAM process
invoked a resolved base Python path and stopped before model construction.
This is a separately registered operational continuation, not an independent
replication. The original failure remains unchanged.

Change only invocation: preserve the absolute prepared venv Python path without
resolving its symlink. Run an import-only process preflight recording executable,
prefix/base-prefix, Torch version and lack of CUDA initialization, then register
a fresh root before inference. The SAM stage repeats the executable/prefix/version
checks and records process identity before model construction. GPU0 UUID and
deterministic workspace remain explicit.

Authenticate the predecessor registration and sealed BOX files. Require matching
sensor sources, RGB/depth/K/T, original queries, settings, checkpoint/config/source
hashes, full raw/audit typed parsing, sample order and ordered BOX coordinates.
Reuse the exact sealed BOX stage byte-for-byte: zero new LocateAnything calls,
no regenerated BOX, no POINT. Register inheritance rather than claiming fresh
semantic inference. The source frames are still development-only init25/26.

All scientific controls and stopping rules in
[the original protocol](p1_box_sam2_protocol.md) remain fixed: all native masks,
original BOX/denominator/geometry gates, RGB-only SAM input, no labels or mask
winner, no tracker/PUSH/Qwen/Laya. Stop the new condition on the first concrete
failure. Ordinary UNKNOWN/AMBIGUOUS results are retained for both samples.

Commands, from repository root:

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_sam2_launcher preflight \
  --assets runs/p1/sam2-preparation-pip25-20261007/assets.json \
  --output runs/p1/sam2-launch-preflight-20261007.json \
  --gpu-uuid GPU-dfe7bb45-8b97-0077-34a1-7012d2454d3b
.venv-p1/bin/python -m embodied_runtime.experiments.p1_segmentation_probe prepare \
  --assets runs/p1/sam2-preparation-pip25-20261007/assets.json \
  --output runs/p1/box-sam2-continuation-20261007 \
  --reuse-boxes-from runs/p1/box-sam2-development-20261007
.venv-p1/bin/python -m embodied_runtime.experiments.p1_segmentation_probe reuse-boxes \
  --output runs/p1/box-sam2-continuation-20261007
.venv-p1/bin/python -m embodied_runtime.experiments.p1_sam2_launcher masks \
  --assets runs/p1/sam2-preparation-pip25-20261007/assets.json \
  --output runs/p1/box-sam2-continuation-20261007 \
  --gpu-uuid GPU-dfe7bb45-8b97-0077-34a1-7012d2454d3b
.venv-p1/bin/python -m embodied_runtime.experiments.p1_segmentation_probe geometry \
  --output runs/p1/box-sam2-continuation-20261007
```

Each command depends on prior success; do not execute later stages after failure.
Receipt checks, real reuse/native-stage integration and changed-file lint are the
necessary validation. Do not repeat broad historical tests or model calls.
