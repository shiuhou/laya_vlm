# Task2 BOX support-contamination protocol

Approved scope: one initial fixture, one fixed model call, then sealed support
analysis. Freeze the implementation and obtain independent review before the
call. The initial RGB was inspected during design; this is a development fixture.

## Question and budget

Does one existing LocateAnything BOX ground the intended bottle well enough that
the existing depth crop is a credible starting point for local object geometry?
A plausible semantic box can include table, drawer, and boundary pixels; adding
shape descriptors to those depths would not establish bottle geometry.

Budget: **one fixture, one LocateAnything call on GPU0, at most 256 newly generated
tokens, no retries**. Existing checkpoint and hybrid greedy settings are retained.
An inference timeout after 300 s is a recorded failure. No additional models,
prompts, captures, renders, raycasts, scene construction, physics, replay,
segmentation fallback, jaw-span calculation, or effect fit is included.

## Input and semantic call

Use `runs/autonomous-research/interaction-observability-paired-01/close/0000.npz`,
SHA-256 `3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`.
It contains 384 × 384 RGB/depth, intrinsics, camera transform and capture read
time 0.5 s. Cached geometry sample time is unknown. The corresponding PNG has
SHA-256 `9b446e31066ff438765f01e0bed579346b8ab6c99b79e937cf53a992510419e3`.
Do not count the duplicate open-arm reset image as another case.

The model receives only full RGB and the existing BOX template:
`Locate a single instance that matches the following description: the wine bottle.`
No depth, crop, mask, robot/pregrasp context, target coordinates, or previous
response enters the model. Preserve pixel/token fingerprints, model identity,
settings, raw response, actual generated tokens, EOS status, latency and failure.
Require exactly one complete valid BOX with terminal EOS. Missing, multiple,
malformed or truncated output ends the experiment with no alternate prompt or
assistant annotation. The worker's parsed-box score of 1 is not confidence.

## Point and support-carrying representations

P is the unchanged `LocateAnythingProvider` proxy: integer-converted box, clipped
depth ROI, fixed one-fifth interior crop, valid depth range 0.01–5 m, median
depth, and the original box-center ray. Keep the original pixel convention and
exact point. Empty/invalid crop returns unknown.

G retains the same P and explicitly records every valid interior-crop pixel,
RGB/depth, and backprojected surface point using raster centers at (u+0.5,v+0.5).
Preserve selected support and lower/upper median-ranked depth contributor sets,
including every tie. Retain the existing median/MAD/std/valid fraction and
descriptive min/max depth. This is candidate RGB-D support, not a bottle mask or
object shape. No extra POINT call is made. No labels, color rule, clustering,
depth splitting or outcome changes the crop or the point.

The sensor producer receives only RGB-D/calibration and the model BOX. Seal the
model output, P, G and all contributing pixels before loading evaluator labels.
The successful preclose context supplies no target, offset, transform, support
selection, or scoring target in this experiment. No PCA, grasp-pose generator,
dimensions or action decision is added.

## Limited evaluator and actual RGB inspection

After sealing, read only the existing initial bottle-label mask at
`evaluator-only/close-0000-bottle-mask.npy`, SHA-256
`2a474be6d469dc2df45edfb03c97b23a1adf021f9a48551994a619f501a0b747`.
It is an **ID-rendered membership proxy**. MSAA, raster boundaries, mixed
coverage, and render/depth staging can separate that label from the surface
supplying the depth. No new rendering/scene pipeline repairs this uncertainty.

Report crop overlap with the proxy, coverage of its visible pixels, center-pixel
proxy membership, and proxy agreement of both median contributor sets, retaining
all ties. These are rendered-mask agreement fractions, never exact depth
ownership, semantic purity or calibrated confidence. Also retain actual depth at
the box-center sample and its difference from P's median depth; do not fit a
contamination threshold.

Stratify the existing mask with fixed one-pixel 8-neighbor erosion/dilation into
proxy interior, boundary band and exterior, and report selected-pixel counts.
This is evaluator-proxy stratification, not corrected segmentation or proof of
interior depth ownership. It never changes the sensor support.

Make one diagnostic figure showing original RGB with box/crop outlines, raw
crop depth, and a clearly labeled evaluator-proxy overlay. Inspect unmodified
RGB and overlay separately. Record visible table/drawer/background in the crop
and ambiguous boundary/occlusion regions. Assistant visual inspection is
descriptive evidence, not a hidden pixel annotation or correction.

Possible outcomes: plausible bottle BOX with mixed candidate support; wrong or
missing BOX; or candidate support compatible with available visual and limited
proxy evidence. Preserve unknown resolved-depth ownership in every case. Even
agreement earns only bounded support for a later geometry test, not rigid object
extent, orientation, jaw fit, holding, approach qualification or generalization.

## Completion

Freeze code/protocol/tests and input hashes; independent review checks the input
boundary before inference. Synthetic tests cover crop/provider parity, median
ties, projection convention, parser completeness and evaluator strata. Retain
the one attempt's generation, seals, all selected pixels, proxy comparisons,
inspected figure and explicit unknowns. Post-result extraction changes, new
segmentation, alternate prompts or pregrasp/effect fitting are excluded.
