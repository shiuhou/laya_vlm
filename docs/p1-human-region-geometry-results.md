# Offline human-region geometry upper-bound diagnostic

The single diagnostic completed at execution revision `eb8028e`, preserving
baseline `e8cda1e`. **All 25 VISIBLE wrist frames produce geometry candidates:
130 total, 2–7 per frame, all projecting inside their frozen human regions.**
NO_TOOL_INTERIOR_CANDIDATE occurs in **0/25** frames.

This is an explicitly human-assisted, offline target-support counterfactual on
already exposed development frames. It is not perception performance, independent
held-out validation, P1 acceptance, or evidence of executable manipulation.

[Protocol](research/p1_human_region_geometry_protocol.md) ·
[Evidence and all 25 frame measurements](evidence/p1_grounding/human_region_geometry_20261007/README.md)

## Answers to the three questions

1. **25/25 frames** yield at least one candidate under the frozen human-region
   identity/support condition. This exceeds the prospective 13/25 research-priority
   threshold. That threshold is not a P1 acceptance criterion.
2. **No frame fails a frozen gate.** At the individual grid-point level, edge
   clearance rejects 562 points and visible-support checks reject 228; 130 of
   920 grid points survive. There are zero position-uncertainty rejections.
3. **NO_TOOL_INTERIOR_CANDIDATE is not systematic under this human-support
   condition: 0/25 overall and 0/25 reaching the candidate gate.** The previous
   init12 SAM native1 example rejected, while the same init12 with frozen human
   support produces 7 candidates. This shows the earlier failure depends on the
   supplied support/geometry estimate; it does not justify weakening tool gates.

Next research priority: **semantic identity / target-region support repair,
followed by validation on new held-out frames.** This experiment bypasses BOX and
SAM together, so it does not isolate which identity/segmentation component should
be repaired first. No such repair or further experiment was started.

## Exact condition and boundaries

All original init0–24 wrist images are retained at 384×256, with original RGB-D,
K/T calibration, source timestamps and proprioceptive EEF. Frozen annotations
are authenticated against their original frame bindings and rules. Their region
union is rasterized with the existing evaluator's x+.5/y+.5 pixel convention.
No morphology, relabeling, threshold change or sample selection.

Human support replaces both learned BOX and SAM support. The geometry domain is
the full original image, with depth outside the human mask UNKNOWN. Clipping to
an erroneous model BOX would leave an identity confound in this diagnostic.
Original depth samples inside the human region are unchanged; original sensor
and derived masked-depth hashes are recorded separately. The denominator is
valid in-region depth / human-region pixels, using the frozen mask-support
measurement semantics.

The experiment calls the existing estimate_visible_patch directly; it does not
pretend that human labels satisfy the learned-mask input contract. No runtime
adapter or policy input was changed. The unchanged core owns components,
RANSAC/plane, edge, uncertainty, erosion, 8mm tool radius, 12mm grid and candidate
gates/order. Seed0, original proprioception, no feasibility callback or self mask.
There is no model, query, decoder, threshold, component fallback or ranking change.

All 130 candidates retain usable_status=UNKNOWN and the reasons
FEASIBILITY_NOT_EVALUATED and UNCALIBRATED_UNCERTAINTY. Reachability, swept
clearance, freshness, temporal association and cabinet-relative VERIFY have not
been demonstrated. Human annotation never enters a policy/runtime observation.

## Measurements

| Measurement across 25 frames | Result |
|---|---:|
| Human-region pixels / valid depth samples |1,216–3,102 per frame|
| Human-region depth availability |100% in every frame|
| Ambiguous component rejections |0|
| Plane support ratio |98.734%–100%|
| Reported plane RMS |1.82e-8–3.62e-8 m|
| Position sigma, uncalibrated engineering model |2.638–2.852 mm|
| Frozen erosion requirement |15.276–15.703 mm|
| Eroded support count |194–481 per frame|
| Candidate grid cells |30–48 per frame; 920 total|
| Tool-interior candidates |2–7 per frame; 130 total|
| First frame-level rejection |None for all 25|

The very small plane residuals describe the recorded simulator depth and the
core's final eroded-interior fit. They do not establish real depth-sensor accuracy;
the engineering uncertainty floor remains active and uncalibrated. Small secondary
components are handled by the original dominance-or-abstention rule, without a
new component-selection method.

[all25.csv](evidence/p1_grounding/human_region_geometry_20261007/all25.csv) provides
for every frame: human pixels, valid depth/ratio, component sizes and selected
support, fitted points, plane ratio/RMS, boundary count, sigma, erosion, eroded
support, sampling margin, grid size, candidate rejection counts, candidate count
and first rejection. Raw JSON additionally preserves every reached-stage ledger,
source binding, candidate and continuous projection. Unreached fields would stay
null/NOT_EVALUATED; here every frame reaches the candidate gate.

Candidate counts by init0–24:
`6, 5, 5, 5, 5, 6, 7, 6, 4, 4, 2, 5, 7, 6, 3, 7, 4, 7, 3, 7, 7, 6, 4, 5, 4`.

For the previous init12 boundary, eroded support changes from 11 under SAM native1
to 479 under the human region; candidate count changes from 0 to 7. The erosion
requirements remain comparable (15.463mm vs 15.488mm); no gate was relaxed.
This is a change in supplied support, not a repeated threshold fit.

## Verification, artifacts and stop

Two focused tests passed before execution: an early plane rejection cannot become
an invented tool failure/semantic success, and a valid local plane with no tool
candidate remains a tool rejection. No broad or repeated regression suite.
An independent source audit verified all 1,072 registered hashes, all original
and masked-depth reconstructions, stage seals and candidate UNKNOWN status.
The parent inspected all 25 original RGB/human-mask/candidate overlays across
five review sheets. All candidates lie on the annotated front region in those
sheets. No geometry rerun or model inference was used for review.

Geometry p50/p95: 39.29/54.61ms per frame, one offline pass each, CPU thread
limits1. This is not continuous end-to-end Hz or a latency improvement claim.
The evidence archive contains all 25 masks, raw results, 130 candidates, input
receipts, summaries and review sheets; original RGB-D is reused by pinned hashes.

Observed fact: this human-supported condition is sufficient for the frozen local
geometry gates on these 25 recorded views. Inference: target-part grounding and
support quality are the better next research priority than changing tool thresholds
based on the prior isolated failure. Confidence is high for these frozen results;
generality, annotation uncertainty and learned-perception reliability remain open.
"Upper bound" is this practical support counterfactual, not a mathematical maximum
over every possible sensing or manipulation method.

The diagnostic is complete and stopped. Baseline `e8cda1e` and prior evidence are
unchanged. No new LocateAnything/SAM calls, temporal tracker, reference work,
P2/PUSH, Qwen or Laya. P1 acceptance remains unearned and reference/VERIFY UNKNOWN.
