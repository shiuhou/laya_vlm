# Formal-50 frozen perception evaluation

Completed 2026-10-07 at clean execution revision
`e1ff472936cfb906ea6d3bfaf08adfd8200c0805`, baseline `25f1e4a`.
**Task-valid drawer-front candidates: 0.** All50 inputs and150 native masks were
evaluated; no inference failure, retry or selected mask. This is a completed
frozen failure distribution, not P1 acceptance or a final scientific Gate C.

**P2 remains blocked pending Formal-50 / temporal P1 gate.** Formal-50 itself is
now complete; its result does not earn temporal qualification. No temporal,
tracker, reference diagnostic, PUSH, P2, Qwen or Laya experiment followed.

[Protocol](research/p1_formal50_protocol.md),
[evidence/index](evidence/p1_grounding/formal50_20261007/README.md),
[all150 masks CSV](evidence/p1_grounding/formal50_20261007/all-native-masks.csv),
[machine summary](evidence/p1_grounding/formal50_20261007/summary.json),
[stage diagnostics](evidence/p1_grounding/formal50_20261007/stage-diagnostics.json).

## Frozen inputs and execution

The original Formal-50 manifest selects first recorded exposures for init0–24:
25agentview +25robot0_eye_in_hand, all384×256. No recapture/resize/reordering.
The existing100 BOX records cover two queries per frame; only the50 archived
drawer_front_pushable BOX responses feed this experiment. Both query strings,
response order/raw text/token/EOS audits and preregistration are pinned.
There are **zero new LocateAnything calls**.

SAM2.1 hiera-tiny uses official source
`2b90b9f5ceec907a1c18123530e92e794ad901a4` and checkpoint SHA256
`7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`.
Frozen settings: FP32, no autocast/TF32/postprocessing, threshold0,
hole/sprinkle0, native multimask/logit output, seed1, strict determinism,
CuBLAS `:4096:8`, and the previously frozen instance-only dense-grid overlay.
The raw-byte64×64 coordinate/PE equivalence check passes before images;
original native CUDA-cumsum equivalence remains unrun because unsupported.
No new equivalence claim or SAM source/weight modification.

Fresh process: prepared `.venv-p1-sam2`, Torch2.5.1+cu121, GPU UUID
`GPU-dfe7bb45-8b97-0077-34a1-7012d2454d3b`, RTX4090. One RGB encoding and one
BOX prediction per frame. Every NPZ retains masks0/1/2, full-resolution logits,
low-resolution logits and predicted IoUs; associated source-bound JSON receipts
retain source/calibration IDs and hashes.
Predicted IoU is uncalibrated, never used to choose a mask.

The `native-mask-depth/2` contract is unchanged: valid finite/in-range depth
inside complete native mask / native-mask pixels. BOX coverage is diagnostic;
fitting remains inside original BOX, outside-mask depth UNKNOWN. Geometry
config/thresholds and component/plane/boundary/uncertainty/tool gates are exactly
the frozen repaired pipeline. Existing dominant-component-or-abstention logic
is preserved; no largest/nearest fallback or label-based component selection.
Candidate grid order is unchanged; all points retained without ranking.

Agentview calibration identity:
`camera-calibration:8feedb9b84b50bc50f3a1646e99ae9607665a81be7371f1097068cdbd34a8b8c`.
Wrist calibration identity:
`camera-calibration:bbff21c5a0587b86ed37d932035e7021ad9eeeaa77054bdd4e70c5d35527938b`.
Each camera's25 frames share its recorded calibration identity. RGB/depth/K/T
and EEF proprioception remain source-bound; no simulator object pose, contact,
segmentation ID, future preview or official success enters generation.

Native masks sealed, then all geometry sealed, then annotation hash/binding
verified and labels parsed by the separate scorer. Corrected-v2 annotation SHA
`cd5fd0bf589e7f7b11d6c9fd118040868397e2d31492feaf76bdf64f77d3d700` remains
unchanged. Human independence is user-reported, not independently authenticated.
No annotations became inference inputs, masks, candidate selectors or gates.
All source/pipeline/config/dependency hashes are in the registration.

## Visibility, BOX coverage and candidate identity

| Measurement | Agentview | Wrist | Total |
|---|---:|---:|---:|
| Frames |25|25|50|
| Human VISIBLE |0|25|25|
| Human UNKNOWN |25|0|25|
| Human NOT_VISIBLE |0|0|0|
| Structurally admitted BOX |25|25|50|
| Fully covers VISIBLE region |N/A, no VISIBLE labels|21/25 (84%)|21/25 VISIBLE|
| Partial coverage / zero coverage |N/A|0 /4|0 /4 VISIBLE|
| Native masks |75|75|150|
| Candidate-producing masks |0|33|33|
| Geometric point proposals |0|45,252|45,252|
| Inside / outside / unknown projection vs VISIBLE label |0 /0 /0|0 /45,252 /0|0 /45,252 /0|
| Task-valid candidate frames |0/25, identity unscored|0/25 VISIBLE|0/50|

BOX failures on wrist: init1/2/5/9. **84% coverage is not clean grounding:**
median wrist BOX contamination97.4825% (target purity2.5175%);15 BOXes occupy
83.83–99.6% of the image. A very large search region can cover the right part
while providing poor part specificity to a BOX-only segmenter.

Wrist native masks:50/75 have zero overlap with the annotated front;14 have
partial coverage;11 cover the full annotated pixel region. Median mask purity0;
p95 purity34.22%. Nonzero overlap is not identity confirmation. Of25 masks
with any target overlap,16 stop at ambiguity,2 at plane support,7 produce
geometric points **entirely outside** that region. Zero masks yield a target point.

All45,252 points come from33 masks in16 wrist frames. They are correlated grid
proposals across native hypotheses, not independent trials or unique physical
locations. Point-to-annotated-boundary distance in original pixel coordinates:
minimum11.16px, median126.90px, p95247.92px. Thus these are substantial target
association errors, not numerical polygon-boundary rounding. No candidate is
declared executable: uncertainty is uncalibrated and feasibility UNKNOWN.

## Complete native-mask failure distributions

First physical boundary below is independent of human target identity. It sums
to all150 masks, including UNKNOWN-label views.

| Geometry outcome | Agentview /75 | Wrist /75 | Total /150 |
|---|---:|---:|---:|
| INSUFFICIENT_DEPTH |0|1|1|
| AMBIGUOUS_DEPTH_COMPONENTS |7 (9.33%)|27 (36%)|34 (22.67%)|
| GEOMETRY_REJECTED |68|11|79|
| EDGE_UNCERTAINTY_TOOL_REJECTED |0|3|3|
| GEOMETRIC_CANDIDATE, identity unverified |0|33|33|
| Inference / geometry runtime failure |0 /0|0 /0|0 /0|

Raw reasons: agentview68 INSUFFICIENT_PLANE_SUPPORT +7 ambiguity. Wrist27
ambiguity +9 PLANE_DEGENERATE +2 INSUFFICIENT_PLANE_SUPPORT +1
INSUFFICIENT_VALID_DEPTH +3 NO_TOOL_INTERIOR_CANDIDATE;33 have geometric points.
Availability is exactly1.0 for all75 agentview masks and64/75 wrist masks;
all150 median1.0, wrist minimum0.4731. Only one availability gate rejects.
Therefore sensor-depth availability is not the dominant failure here.

The exclusive evaluator taxonomy below uses UNKNOWN/NOT_VISIBLE first, then
BOX miss, zero mask overlap or outside candidate identity, then geometry.
This preserves the physical ledger above instead of erasing its rejection.

| Offline evaluator category | Agentview /75 | Wrist /75 | Total /150 |
|---|---:|---:|---:|
| UNKNOWN |75|0|75|
| NOT_VISIBLE |0|0|0|
| SEMANTIC_BOX_FAILURE |unscored|12|12|
| SEGMENTATION_IDENTITY_FAILURE |unscored|45|45|
| INSUFFICIENT_DEPTH |unscored|0|0|
| AMBIGUOUS_DEPTH_COMPONENTS |unscored|16|16|
| GEOMETRY_REJECTED |unscored|2|2|
| EDGE_UNCERTAINTY_TOOL_REJECTED |unscored|0|0|
| VALID_DRAWER_FRONT_CANDIDATE |0|0|0|
| Inference / geometry runtime failure |0 /0|0 /0|0 /0|

For wrist at frame level, categories may coexist across masks: BOX miss4/25,
segmentation identity failure15/25, ambiguity6/25, plane rejection2/25,
task-valid0/25. Frame counts are nonexclusive; no best mask is selected.

| Camera / native ordinal | Ambiguous components | Plane/local rejection | Insufficient depth | No tool point | Geometric point-producing |
|---|---:|---:|---:|---:|---:|
| Agentview0 |1|24|0|0|0|
| Agentview1 |5|20|0|0|0|
| Agentview2 |1|24|0|0|0|
| Wrist0 |8|1|0|0|16|
| Wrist1 |13|8|0|3|1|
| Wrist2 |6|2|1|0|16|

Wrist evaluator ordinal0: BOX4 /identity15 /ambiguity6; ordinal1:
BOX4 /identity15 /ambiguity4 /plane2; ordinal2: BOX4 /identity15 /ambiguity6.
Each ordinal has25 rows. Every agentview ordinal has25 identity-UNKNOWN rows.

## Reached stages, not downstream impossibility

| Physical stage | Agentview reached /rejected /not evaluated | Wrist reached /rejected /not evaluated | Total reached /rejected /not evaluated |
|---|---|---|---|
| Native-mask depth availability |75 /0 /0|75 /1 /0|150 /1 /0|
| Depth components |75 /7 /0|74 /27 /1|149 /34 /1|
| Plane/local geometry |68 /68 /7|47 /11 /28|115 /79 /35|
| Visible boundary/interior refit |0 /0 /75|36 /0 /39|36 /0 /114|
| Uncertainty gate |0 /0 /75|36 /0 /39|36 /0 /114|
| Grid generation |0 /0 /75|36 /0 /39|36 /0 /114|
| Tool-interior candidate gate |0 /0 /75|36 /3 /39|36 /3 /114|

Rejection denominators are **reached** counts, not always150. For example,
plane rejects79/115 reached; component ambiguity34/149 reached.114 masks
never reach boundary/uncertainty/grid/tool evaluation. This does not establish
that their later stages would fail, or that their camera has no physical surface.

## Measured offline latency

| Timed workload, p50 /p95 ms | Agentview | Wrist | Total |
|---|---:|---:|---:|
| SAM RGB encoding,25/25/50 frames |28.48 /33.71|28.49 /35.25|28.49 /35.18|
| SAM BOX decoding,25/25/50 BOXes |11.64 /13.50|11.66 /12.17|11.65 /12.39|
| Encoding + decoding |39.99 /45.78|40.24 /47.20|40.19 /47.17|
| Frozen geometry per mask,75/75/150 masks |77.93 /119.35|83.78 /8,372.56|78.26 /8,325.01|

CUDA synchronized around inference timing; geometry uses perf_counter.
Model load +overlay startup0.924s is separate. Broad wrong-surface masks
can produce large candidate grids and dominate geometry tail latency.
**These are offline submodule workload timings, not continuous end-to-end Hz.**
No capture/queue/freshness/temporal-tracking throughput claim follows. Source
replay, model startup, persistence, blind scoring and visualization are outside
these windows; external geometry-launch wall duration was not recorded.
The unchanged local geometry venv is recorded after completion (Python3.10.21,
NumPy1.26.4); this is not an independent launch-process environment receipt.

## Inspection, interpretation and next proposal

Parent and two independent code/evidence reviewers inspected all10 contact
sheets: all50 original RGB images and150 mask overlays, including failures.
Pink is native mask, yellow is frozen evaluation-only human region, cyan is
geometric candidate; the first column remains original RGB. Agentview masks
generally cover broad cabinet/body/cavity parts; the outward front is near
edge-on. Wrist candidate overlays predominantly lie on tabletop; init2 points
are on another drawer/cabinet surface. This agrees with independent reprojection.

Observed: wrist has a human-recognizable front in25/25 static views, but the
BOX→SAM→geometry interface yields no target-supported tool point. Inference:
grounding specificity / segmentation-part identity contamination is the
strongest supported bottleneck, with component ambiguity and plane support
also material. High confidence for these frozen measurements; limited confidence
for new viewpoints/tasks. A geometry-valid plane cannot validate target identity.

Wrist is the better **development sensing source in this recorded condition**
because it has25 VISIBLE labels versus agentview0 VISIBLE. Neither is qualified
as a control sensing source. Agentview UNKNOWN does not prove NOT_VISIBLE or
global camera unobservability. Static resets are not perspective/occlusion trials.
The human regions identify potentially contactable pixels, not guaranteed tool
clearance, reachability or cabinet/reference fixedness.

Correct identity +tool-interior evidence0/25 inits falls short of the frozen
static minimum20/25 even under evaluator-only any-mask existence. There is
**insufficient evidence to launch temporal tracking qualification**. The supported
next proposal is **B: one scoped, prospective P1 grounding/identity representation
repair**, based on this full distribution. This is a next-round proposal, not
a repair performed here. Do not lower component/geometry gates, pick largest
planes, select by labels or retry segmentation on these evaluation frames.
It is not evidence for final sensing Gate C, and temporal/reference/VERIFY
remain unearned/UNKNOWN. Fixed-reference POINT decoder work remains closed.

Only experiment/evaluator/report code was added. Frozen perception geometry,
models, queries, masks, controller/runtime and candidate ordering were not changed.
Nine focused synthetic tests passed before the clean runner freeze. Source,
stage, ordinal/shape/raw-byte and annotation-binding audits passed independently.
Raw failures and evidence remain immutable. Stop here for review.
Archive creation completed on its first attempt. A packaging verifier initially
compared absolute preparation-receipt names against tarfile's leading-slash-
stripped names; the corrected verifier authenticated the existing archives
without recreating either archive or rerunning inference/geometry. The
[packaging note](evidence/p1_grounding/formal50_20261007/packaging-note.json)
preserves this reporting failure separately from the zero inference failures.
