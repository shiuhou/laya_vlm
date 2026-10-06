# P1 surface-association repair batch — 2026-10-06

**Implementation completed; fresh semantic/track acceptance is untested.**
The first experiment boundary is available inference compute, not a demonstrated
failure of the association algorithm. No PUSH, Qwen, Laya or P2 ran.

## Implemented interface

- Native BOX is only a search region. Enumerate every recovered depth-plane
  support, disconnected support and residual; retain overlap/ambiguity and
  canonical raster order. Enumeration does not promise exhaustive plane recovery.
- Source-bound native POINT can select only its exact containing pixel. Reject
  mixed/incomplete outputs, foreign sensor sources, missing support and multiple
  matches. No nearest/largest/box-center/annotation substitution.
- Inventory IDs include full source/ROI/config/seed fingerprint; detached
  supports are refit rather than inheriting another patch's validity.
- A unique association remains BOUND_HYPOTHESIS, identity unverified and
  confidence uncalibrated. It is not a full VALID push patch or executable target.
- A support-contained rectangle may initialize the original tracker using
  unchanged depth/context gates. Initialization uses offline capture time,
  not actual live freshness. Unsupported fixedness/VERIFY remain UNKNOWN.

No existing geometry, tracker, executor, scheduler or model provider was rewritten.
Four focused tests passed; Ruff passed. No broad historical suite was rerun.
Implementation commits: `b0c2a53`, `5016337`; artifact-seal/serialization fix:
`7bec920`.

## Fresh probe result

Fresh reset captures succeeded for top_drawer init 25/26, seed 1: four raw
384×256 RGB-D views, software EGL, original ten settling controls, no post-reset
controls. They are development evidence, separate from the frozen 50-view
evaluation. No annotation was read or used to tune queries/geometry.

This session exposes no NVIDIA device. Checkpoint bytes matched the frozen
LocateAnything content ID. The bounded CPU BF16 process completed only 1/8
registered calls before its 900-second ceiling (exit 124). The completed fixed
reference BOX took **816.021 seconds**, with **217 input / 48 output tokens**,
terminal EOS and no length truncation. The next POINT did not complete; its
output/EOS/truncation state is UNKNOWN, not a valid abstention or prediction.
Zero complete pairs means surface binding and real-data tracker initialization
were **not evaluated**. No inference retry or synthetic semantic point was used.

The CPU package emitted the existing tokenizer-regex warning; it was not
silently corrected. CPU BF16/SDPA and software rendering differ from the prior
GPU condition. Do not pool results or infer live latency from this run.

Both agents' [raw-RGB-only review](raw-rgb-review.md) finds strong view limitations:
agentview front nearly edge-on; wrist front narrow/dark/clipped; no clear fixed
front-facing cabinet frame. This is development diagnosis, not new human labels,
and does not negate historical wrist human-mask geometry results.

## Evidence and next boundary

Exact registration, source recording/blobs, raw images, model identity/config,
prompts/input IDs, completed response/output IDs, runtime log and termination
receipt are in [the portable evidence archive](fresh-development-evidence.tar.gz).
[Artifact index](artifact-index.json) records archive and individual SHA256s.
Local source: `runs/p1/surface-dev-20261006-capture02/`.

The running inference used `5016337` and its source hashes; the later runner fix
was not retroactively applied to it. No analysis phase executed. Four disposable
process cache/config directories and the registration-only failed Numba preflight
were cleaned with receipts; canonical/historical evidence remains intact.

Next: complete the preregistered matched BOX/POINT diagnostic when GPU inference
is available, using identifiable device/config/code and these unchanged recorded
inputs. Do not compensate with labels, query tuning, lower geometry gates,
tabletop/side-frame relabeling, controls or model integration. A completed pair
can test surface association; it still cannot establish an observable fixed
reference relation, continuous tracking or P1 task acceptance by itself.
