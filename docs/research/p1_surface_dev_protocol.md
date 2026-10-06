# P1 source-bound surface association development probe

Condition fixed before acquisition/inference, 2026-10-06. This is a repair
development diagnostic, not another evaluation of the frozen human label set.

Question: can a native LocateAnything POINT on a fresh image select a measured
surface inside its native BOX search region, and initialize the unchanged
tracker, without largest-plane or nearest-point substitution?

Competing explanations: the previous box mixed front/cavity/rim surfaces; the
semantic point itself targets the wrong surface; a correct point lacks usable
depth/plane support; or tracker depth/context gates reject valid association.

Fixed condition is `configs/p1_surface_dev.json`: top_drawer, seed 1, held-out
development init indices 25/26, one reset capture per init, two cameras,
384×256. World constructor settling is preserved; no additional controls.
Software EGL rendering is recorded and kept separate from historical GPU
capture. Wrist camera queries drawer front; agentview queries fixed front frame.
No evaluation annotation is read. The old exact semantic phrases, checkpoint
content ID and deterministic generation settings are reused. Native BOX then
POINT runs on the identical image: four matched pairs, eight calls, no retry.
Inference device is CPU BF16 with eight Torch threads because this session
cannot access GPUs. One bounded process has a 900-second execution ceiling;
an interrupted process is incomplete, never a valid measurement. CPU latency
is not evidence about GPU/live throughput. Full prompts, actual input/output
IDs, terminal EOS and image/processor/source identities are retained.

Boxes delimit searches only. All extracted planar support hypotheses,
overlap, undersized/unexplained residuals and canonical pixel order survive.
RANSAC enumeration does not guarantee recovery of every physical surface.
Each disconnected support is refit with unchanged plane settings. One strict
complete point may bind only its containing support pixel. No snapping,
largest surface, box center, annotation centroid, object IDs or global-plane
fallback. A support outside every search ROI remains UNKNOWN. Multiple
surface matches, including across boxes, remain AMBIGUOUS.

The association result is at most BOUND_HYPOTHESIS: identity is not verified,
confidence is uncalibrated, and it is not an executable push patch. Tracker
initialization uses a measured support-contained rectangle and the original
tracker depth/context settings. It uses capture-clock replay, so a TRACKED
result is an initialization diagnostic, not continuous temporal tracking or
live freshness acceptance. Fixed reference and VERIFY remain UNKNOWN because
there is no observed fixedness/closed-state relation in this static probe.

Seal all eight model calls before inspecting outputs. Inspect raw RGB plus
point/support overlays. Report association, tracker initialization, wrong
surface and unobservable reference separately. Visual review is agent
development diagnosis, not an independent human success label. Stop this
batch at its first concrete blocker; do not tune a query/threshold or execute
controls afterward. No PUSH, P2, Qwen or Laya process is started.

Only focused surface-association tests and syntax/lint checks are required.
Canonical fresh source evidence is retained; disposable module/cache files
may be cleaned after processes exit. Existing execution/tracking/geometry
implementations and historical evidence remain unchanged.
