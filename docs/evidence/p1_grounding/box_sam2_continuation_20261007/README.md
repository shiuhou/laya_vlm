# BOX / SAM2 launcher continuation — 2026-10-07

**Launcher repair passed; condition STOPPED at a new deterministic CUDA operator
failure. No returned masks or geometry comparison.** P1 remains Gate C;
reference/VERIFY UNKNOWN. No tracker, PUSH, Qwen or Laya.

Exact execution revision: clean `305056a32beb1e44722bc91623d7d74e4be3201d`,
`feat/p1-segmentation-surface`.
[Continuation protocol](../../../research/p1_box_sam2_launch_continuation.md).
This is an operational continuation of the [frozen launcher failure](../box_sam2_development_20261007/README.md),
not a fresh independent replication or a change to scientific controls.

## What completed

- Repository launcher invokes the absolute prepared Python path without resolving
  its symlink. Import-only preflight confirms executable/prefix, Torch2.5.1+cu121
  and no CUDA initialization/model inference. Native process identity confirms the
  same venv at execution. GPU0 RTX4090 UUID explicitly allocated.
- Before inference, new registration records predecessor registration and BOX seal
  hashes. Raw/audit outputs are reparsed under the unchanged typed contract;
  sensor identity, ordered BOXes and full typed records match. Both BOX stages
  are byte-identical to the predecessor seal. **Zero new LocateAnything calls.**
- Official SAM2.1 tiny model construction and init25 image encoding complete.
  Query, checkpoint/source/config, original RGB-D, BOX denominator, geometry gates,
  all-multimask condition, FP32, no postprocessing/TF32 and strict deterministic
  algorithms remain fixed. No annotations or oracle target information read.

## First new failure

The first `predict()` call reaches `PositionEmbeddingRandom.forward`, whose
float32 ones grid uses CUDA `cumsum(dim=0)`. Torch raises:

```text
cumsum_cuda_kernel does not have a deterministic implementation,
but you set 'torch.use_deterministic_algorithms(True)'.
```

Location: pinned SAM source `sam2/modeling/position_encoding.py:161`, while
evaluating `get_dense_pe()` before mask decoder invocation.

| Operation | Count |
|---|---:|
| Model construction completed | 1 |
| Image encoding completed | 1 |
| Mask prediction attempted | 1 |
| Mask prediction completed | 0 |
| Mask decoder called | 0 |
| Returned native masks/logits / NPZ artifacts | 0 |
| Matched geometry evaluations | 0 |
| Init26 SAM attempts | 0 |

Execution stopped immediately. No retry, disabled deterministic flag,
`warn_only`, CPU fallback, source patch, gate change or second sample followed.
Independent read-only audit confirms counts and the first boundary. A torchvision
non-writable NumPy-input warning is preserved separately; it is not the terminating
failure and no RGB mutation has been demonstrated.

This result establishes **incompatibility of this strict deterministic GPU
condition with the native positional-grid operator**, not SAM incapacity,
association failure or camera unobservability. The four original scientific
hypotheses and mask/BOX gate compatibility remain untested; no masks exist to
visually review. Current source/checkpoint hashes, inherited seal and core
runtime/geometry/tracker/provider bytes remain unchanged and authenticated.

## Evidence and next decision

[Summary](summary.json), [registration](registration.json),
[termination](termination.json), [independent review](independent-review.json),
[invariants](invariant-receipt.json), [portable archive](evidence.tar.gz) and
[artifact/dependency index](artifact-index.json). The archive preserves preflight,
exact commands/process identity, inherited BOX raw inputs/outputs/token audits,
native condition, complete failure traceback and source review. Existing source
and preparation archives are referenced by hashes, without duplicating weights,
environment trees or raw sensor recordings. Archive member bytes validated.

Validation: changed-file Ruff and whitespace checks passed; real preflight and
source-bound BOX reuse passed. Reviewer caught tuple/JSON normalization and the
zero-new-call entry-point guard before the implementation freeze; both were fixed.
No broad historical suite or duplicate semantic/model run was added.

The next bounded step would specify an independently registered deterministic
positional-grid/operator compatibility correction, with numerical equivalence
checked before inference. It must preserve learned weights, BOXes and geometry
gates. Neither that correction nor relaxed determinism is implemented here.
