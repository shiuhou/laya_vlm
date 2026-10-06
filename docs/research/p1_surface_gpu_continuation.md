# Frozen-input GPU continuation and ordered gates

Authorized by the user on 2026-10-06. The original CPU registration, inputs,
recordings, queries, model content ID, generation settings and geometry gates
remain unchanged. Device is the sole inference execution override. This
supplement does not redefine the 50-view evaluation or use its annotations.

Source: `runs/p1/surface-dev-20261006-capture02/`. Run all eight BOX/POINT calls
in their registered order in a fresh GPU process and separate output directory;
never splice the completed CPU BOX into a GPU pair. Every existing recorded
model-input request must match exactly, including input IDs and processor pixel
hash. All four paired inputs remain the same recorded frames; no fresh reset,
camera movement, new label, semantic query or geometry setting is introduced.

The runner accepts only one explicitly UUID-masked GPU as logical `cuda:0`.
It records allocation, device properties, source hashes, checkpoint bytes,
versions, source-code hashes, BF16 dtype and unchanged eight CPU threads.
The GPU admission check runs before creating outputs or loading weights. If no
GPU is exposed, stop; do not silently fall back to CPU. Keep the existing
900-second process ceiling. Save the invocation/runtime log outside source
evidence. Do not correct package warnings or change generation settings here.

Example with the **actual** allocated GPU UUID substituted in the environment:

```sh
CUDA_VISIBLE_DEVICES='GPU-REPLACE-WITH-ACTUAL-UUID' \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
HF_MODULES_CACHE=/tmp/laya-surface-gpu-hf \
OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 \
timeout 900 /home/junhongli/miniforge3/envs/locateanything/bin/python \
  -m embodied_runtime.experiments.p1_surface_dev infer \
  --output runs/p1/surface-dev-20261006-capture02 \
  --device cuda:0 --inference-dir runs/p1/surface-dev-gpu-20261006
```

After all eight outputs are sealed, run association only:

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_surface_dev analyze \
  --output runs/p1/surface-dev-20261006-capture02 \
  --inference-dir runs/p1/surface-dev-gpu-20261006 \
  --analysis-dir runs/p1/surface-dev-gpu-association-20261006
```

This phase cannot initialize a tracker. First inspect exact POINT-to-support
bindings, all competing supports/residuals and raw RGB/overlays. Report both
geometric association and whether the selected visible subpart is consistent
with the frozen semantic query. A unique BOUND_HYPOTHESIS alone does not prove
target identity or fixedness. Wrong, absent or ambiguous supports stop the gate;
they must not be replaced by a label, nearest plane or different target.

Only after that review establishes the requested surface association may the
same analysis be invoked with `--test-tracker`, writing to a different fresh
`--analysis-dir`. This explicit second stage reuses the same fixed surfaces and
tracker settings. It tests offline initialization, not continuous tracking,
live freshness or manipulation. No test outcome retroactively changes phase 1.

Even if association and tracker initialization succeed, the next independent
gate is **fixed cabinet reference observability**: measurable visible reference,
separate identity/track lineage and an observation-supported drawer-relative
relation. Missing evidence leaves reference/VERIFY UNKNOWN. No automatic PUSH,
official-success substitution, P2, Qwen or Laya integration follows.
