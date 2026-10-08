# HO23 fixed automatic BOX A/B — final offline evaluation

**The single authorized batch is complete. Neither A nor B produces a candidate
inside the frozen human drawer-front usable regions: 0/23 clean frames in both
arms. The shorter BOX query did not demonstrate a repair.** P1 has not passed;
P2 remains blocked pending perceptual readiness and the temporal P1 gate.
Stop for review; no further experiments or repairs are part of this checkpoint.

Design `33c358c`; capture/generation runner `f71e452`; scorer `a314003`;
generation checkpoint `db08a3e`. All model/geometry outputs were sealed before
annotation scoring. Only the BOX query differs between A and B. Shared POINT,
RGB-D, calibration, model/checkpoint, decoder, SAM, native ordinal ordering,
BOX-to-geometry domain, measurement contract and geometry/tool gates are unchanged.

[Generation archive](evidence/p1_grounding/box_heldout23_20261008/README.md)
remains immutable. [Final scoring evidence](evidence/p1_grounding/box_heldout23_final_20261008/README.md)
adds corrected annotation provenance, all 23 rows, all 12 native masks, overlays,
matched statistics and audit. No model inference or geometry was rerun for scoring.

## Human annotation provenance

All 23 wrist frames are VISIBLE for drawer-front usable support; all 23 fixed
cabinet references are UNKNOWN. These are human evaluations, not runtime inputs.
The supplied export contained contradictory AI-source metadata. In response to
an explicit question about independent drawing from raw RGB without AI drafts or
model outputs, the user confirmed the annotator is a human assistant named AI
and that the metadata was wrong. A separate metadata-only correction preserves
all polygon/status/reason records, dataset bindings, rules and original timestamp.
The original export, initial schema rejection and exact user statement are saved.
Human identity/independence are **user-attested, not independently verified**.
No annotation was redrawn or edited using model results.

The annotator describes conservative visible subsets, not exhaustive object
segmentation. Therefore outside-region counts mean failure against the frozen
usable-region criterion; they do not prove every outside pixel is a different
physical object. BOX IoU is measured against the annotated support bounding
rectangle, not a separately annotated full-object box. No scoring thresholds
were changed to accommodate these qualifications.

## Four layers, with separate denominators

| Measurement | Baseline A | Repair B |
|---|---:|---:|
| BOX attempts | 23 | 23 |
| Complete EOS / typed BOX | 23/23 | 3/23 |
| BOX incomplete/no-EOS | 0/23 | 20/23 |
| BOX fully covers human usable region | 18/23 | 1/23 (1/3 typed) |
| Typed BOX disjoint from human usable region | 5/23 | 2/3 typed |
| BOX localization pass, all frames | 0/23 | 0/23 |
| BOX localization pass, typed frames only | 0/23 | 0/3 |
| SAM generated frames | 4/23 | 0/23 |
| Native masks, all retained | 12 | 0 |
| Raw geometric proposals | 8,467 | 0 |
| Proposals after frozen mask/POINT containment | 7,084 | 0 |
| Admitted proposals inside human usable region | 0/7,084 | 0/0 (unavailable) |
| Frames with any in-region candidate | 0/23 | 0/23 |
| Clean frames | 0/23 | 0/23 |

BOX pass requires coverage >= 0.90 AND support-bbox IoU >= 0.50 for the same
box, as preregistered. A's maximum IoU is 0.2901; B's is 0.2327.
Coverage alone is misleading: A often covers nearly the whole image. All BOX
outputs are graded independently of POINT, including all POINT-failed frames.
Twenty unavailable B boxes are generation failures, not observed mislocalizations.

The shared POINT has 12/23 complete EOS outputs: 4 typed, 8 cardinality failures;
11 more are incomplete/no-EOS. All 4 typed points have valid depth, but **0/4 lie
in the human usable region** (0/23 complete usable-point coverage). A accepts
these 4 prompts; B accepts none. B's completed scenes are init30 (POINT
cardinality), init34 (POINT outside B BOX), init44 (POINT incomplete). All other
B scenes stop at BOX generation. B's SAM/geometry are NOT_EVALUATED upstream;
there is no matched A/B SAM subset (denominator zero).

All 12 A native masks are evaluated. Geometry-only outcomes: 7 candidate-producing,
2 AMBIGUOUS_DEPTH_COMPONENTS, 2 INSUFFICIENT_CONNECTED_SUPPORT, and
1 NO_TOOL_INTERIOR_CANDIDATE. Separate offline identity taxonomy: 9
SEGMENTATION_IDENTITY_FAILURE, 2 AMBIGUOUS_DEPTH_COMPONENTS, 1
EDGE_UNCERTAINTY_TOOL_REJECTED. These taxonomies describe different dimensions;
identity labels must not hide the original geometric first boundary.

Six masks have no overlap with human support; six have partial/full overlap.
Two cover the entire human region but both stop at ambiguous components.
All 7 candidate-producing masks propose only outside the annotated region.
Three masks fail original POINT containment; one of these contributes 1,383
raw proposals, retained in evidence but excluded from the admitted pool.
No predicted-IoU winner, first-VALID selection or annotation-based selection.
All proposals retain usable_status=UNKNOWN; none is executable acceptance.

## All 23 scenes

All rows: human drawer-front VISIBLE; A/B BOX localization fail; zero in-region
or clean candidates. POINT type/depth/identity and missing stages remain separate.
`cardinality` means completed generation with invalid POINT count; `noEOS` means
incomplete generation. Candidate counts below are after frozen containment.

| Init | Shared POINT | A SAM / admitted proposals | B first execution boundary |
|---|---|---:|---|
| 27 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 28 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 29 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 30 | cardinality | 0 / 0 | POINT_CARDINALITY |
| 31 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 32 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 33 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 34 | typed, outside region | 1 / 15 | POINT_OUTSIDE_ORIGINAL_BOX |
| 35 | typed, outside region | 1 / 2753 | BOX_INCOMPLETE_GENERATION |
| 36 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 37 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 38 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 39 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 40 | typed, outside region | 1 / 2897 | BOX_INCOMPLETE_GENERATION |
| 41 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 42 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 43 | noEOS | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 44 | noEOS | 0 / 0 | INCOMPLETE_GENERATION |
| 45 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 46 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 47 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 48 | cardinality | 0 / 0 | BOX_INCOMPLETE_GENERATION |
| 49 | typed, outside region | 1 / 1419 | BOX_INCOMPLETE_GENERATION |

Native details for the four A SAM scenes, ordinal 0/1/2:

| Init | Geometry outcomes | Raw proposals | Point containment |
|---|---|---|---|
| 34 | ambiguous / candidate / ambiguous | 0 / 15 / 0 | yes / yes / yes |
| 35 | candidate / connected-support reject / candidate | 1398 / 0 / 1355 | yes / no / yes |
| 40 | candidate / no tool interior / candidate | 1459 / 0 / 1438 | yes / yes / yes |
| 49 | candidate / connected-support reject / candidate | 1419 / 0 / 1383 | yes / no / no |

## Actual visual inspection

Reviewed all 23 raw/BOX/POINT paired panels and all 12 native-mask/proposal panels
from sealed data. Init34's POINT and surviving proposals lie on the wider
cabinet/drawer region to the right of the narrow annotated front strip. Init35
and init49 POINTs land on small tabletop objects. Init40's POINT is below the
annotated strip on a dark horizontal structure. Large SAM masks yield grids of
proposals across tabletop areas. The failure is not explained only by a tight
annotation edge. These descriptions are visual observations, not oracle identities.
The actual surface identity of every dark structure remains uncertain.
All no-output scenes remain in the review sheets; no favorable subset is shown.

## Facts, inference, unknowns and next decision

**Observed:** this exact query intervention lowers BOX typed availability from
23 to 3; BOX localization passes and clean frames remain 0 versus 0. All 4 typed
POINTs miss the annotated usable region. B has no SAM output. A geometric proposal
count is large, but none satisfies the evaluation target-support criterion.
Paired clean-frame and BOX-pass gains/losses are both 0/0 over 23. The descriptive
paired p=1 is not evidence of equivalence; there are zero common SAM frames.
For 0/23 the Wilson 95% interval is [0, 0.1431]; no population impossibility claim.

**Inference:** the proposed wording-only BOX repair is not earned. The current
blocker includes automatic target-part identity AND typed POINT availability;
geometry production on another surface is not drawer-front perception success.
The human VISIBLE labels do not support an all-frames-NOT_VISIBLE explanation,
but do not establish continuous observability or fixed-reference availability.

**Unknown:** performance with another automatic grounding interface, transfer to
other views, causal SAM quality under correct automatic prompts, continuous
tracking, reference-relative VERIFY and closed-loop control. Frozen development
human-prompt upper bounds cannot be reported as automatic held-out performance.

**Next recommendation (design/review only):** assess the proposed independent
geometry search-domain interface against the now-explicit POINT bottleneck,
before implementing it. With POINT admission unchanged, 19/23 scenes cannot even
reach SAM; changing only the later geometry domain cannot meet 19/23 readiness.
On the other 4 scenes there is no target-correct POINT evidence. Thus pure domain
decoupling is not supported as a sufficient next repair. A next experiment needs
a preregistered automatic target-part grounding/interface intervention that
addresses this upstream boundary; choose one variable and a fresh evaluation
set after review, without assuming a replacement model will help. Do not silently
remove POINT admission or retune this exposed batch. No such repair is implemented.

## Reproducibility, timing and checks

Fresh states init27–49, seed1, original task and wrist sensor, 384x256. Constructor
settling only; no post-reset robot action. 69 first-attempt model requests and
46 arm/frame slots retained. Exposure audit: 6,164 documents / 28 archives;
new frames distinct from 1,744 historical RGB hashes. Scope is available local
evidence, not proof about deleted or remote data. Model-facing inputs contain
no labels, oracle segmentation, target state or official success. Calibration
confidence is null. Generation archive: 549 members, 39,737,547 bytes,
SHA256 `c7671a0fd745dc687ce742c410f7cb54e96ad980fd65474e9eb42082ddc7d2e2`.

Offline p50/p95 seconds: BOX A 0.743/0.752, BOX B 3.102/4.173, POINT
2.599/4.231; A SAM encode 0.042/0.141, predict 0.013/0.083; native geometry
3.873/8.237. These are not continuous end-to-end Hz. No throughput experiment.

Generation independent audit: 815 checks passed. Final scoring independent audit: 340 checks passed, including independently
recomputed BOX metrics and all candidate projections/memberships. The companion
archive has 64 members, 5,620,481 bytes; every member hash was verified. Targeted annotation/scorer
regression: 10 tests passed; review-script Ruff F checks passed. No runtime,
model, SAM, geometry or threshold source was changed. The frozen scorer's summary
retains its generic "pending held-out scoring / temporal" status string; its
annotation_status=SCORED and this report establish scoring is complete. We do not
rewrite sealed outputs to change that text.

**Stopped for review.** No tracker, temporal sequence, P2/PUSH, Qwen, Laya,
fixed-reference decoder work, further inference or tuning was started.
