# GPU continuation admission — 2026-10-06

**Blocked before inference: this session exposes zero usable CUDA devices.**
Unmasked PyTorch reports CUDA unavailable/device count 0; NVIDIA-SMI cannot
communicate with the driver. Only `/dev/nvidia-caps` exists, with no usable
device node. This does not establish that the physical host lacks GPUs.

All 27 original recorded files and four sensor-view fingerprints were verified
unchanged. Queries, geometry gates and the CPU acquisition registration remain
untouched. There were no new GPU model calls, CPU retries, captures, association
results or tracker tests. No annotation was read, and no P2 behavior ran.

The runner now supports a fresh, explicitly UUID-allocated GPU execution
directory separate from source evidence, plus association-only analysis by
default. Existing CPU request tokens/pixel hashes are checked for exact equality
before generating GPU outputs. Tracker initialization is an explicit later
stage. Geometry and tracker implementations are unchanged. Ruff passed and
the unavailable-GPU negative path stopped before output creation/weight loading;
no broad test suite was rerun. A placeholder UUID in that negative-path check
is not an experimental GPU identity.

See the [continuation protocol](../../../research/p1_surface_gpu_continuation.md)
and [preflight receipt](receipt.json). Surface association is **NOT EVALUATED**,
tracker is **NOT EVALUATED**, fixed reference/VERIFY remain **UNKNOWN**.
The next actionable condition is availability of an identifiable GPU execution
environment. After association succeeds, proceed to independent fixed cabinet
reference observability, never directly to PUSH.
