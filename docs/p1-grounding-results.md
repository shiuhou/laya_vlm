# P1 grounding / observability closure — measured results

Current continuation: [P1 observability closure results](p1-observability-closure-results.md)
give **Gate C**. The historical fixed-query evaluation below remains unchanged.
No further reference POINT decoder experiments are planned; target tracking and
cabinet-relative VERIFY are still unestablished.

**P1 task acceptance has not passed.** The frozen fixed-query experiment is
complete: 50 recorded views, 100 LocateAnything calls, no truncation, no robot
actions. The first demonstrated drawer failure is semantic surface association:
the ROI can include the intended front while its fitted plane and candidates
belong to the cavity or tabletop. Qwen, Laya, PUSH and full P2 remain off.

## What is actually observable?

| Question | Evidence | Conclusion |
| --- | --- | --- |
| Visible drawer-front potential push patch? | Human labels mark 25 wrist views VISIBLE; the unchanged human-mask diagnostic produces VALID geometry in all 25, with 130 candidate projections inside those polygons. Agentview drawer labels are UNKNOWN. | There is visible geometric support in wrist images. This does not establish calibrated uncertainty, reachability, contact safety or executable push acceptance. |
| Fixed cabinet reference? | 25 agentview labels identify adjacent cabinet top/side surfaces; wrist reference labels are UNKNOWN. In a separate post-registration diagnostic, all 50 individual reference polygons yield VALID local geometry. | Adjacent cabinet surfaces are visually identifiable and measurable. Physical fixedness and a closed-drawer relation are not established from static RGB. No visible FRONT_FRAME annotation or validated coplanarity relation supports VERIFY. |
| Primary failure source? | Zero of 23,043 semantic drawer candidate projections overlap the conservative visible-front annotations. Inspected RGB includes cavity points, tabletop points and a robot/image-bar localization. Correct-region mask diagnostics retain 130/130 points inside. | Semantic ROI/surface association is the first concrete drawer boundary. Camera limitations and multi-surface reference ambiguity are additional boundaries, not reasons to relax gates. |

No individual image has both entities labeled VISIBLE. The two camera views are
sequential captures of the same unstepped simulator state; within each view RGB
and depth share a render. Camera wall timestamps remain distinct (approximately
100 ms apart in the first recorded bundle). Known simulator camera/robot
calibration alone does not establish semantic correspondence or a valid
closed-reference relation.
Separate face/reference tracks and the observational VERIFY helper remain
available; unsupported reference, relation or uncertainty keeps VERIFY UNKNOWN.

## Fixed-query experiment

The original v2 registration predates the original label export. User correction
of erroneous provenance is preserved separately; normalization changes only
serialization, not regions, reasons, statuses, reference types or export time.
Human identity and non-exposure are **project-user-reported**, not independently
authenticated. The v3 validator is unchanged; these are not fresh v3 labels.

The evaluator ran at clean commit
`ea4dd51494d19d351def97488d01e1e194d045a9`, on explicit CUDA GPU 0, with original
queries, checkpoint, generation settings and `92865a8` geometry hashes. The
corrected-label seal is recorded at `6ffb97b`. Inputs contain RGB and fixed query
only; labels are evaluation-only and never seed tracking or select a robot target.

- All 100 responses contain a single box and terminate with EOS.
- Input tokens: 208–217; generated tokens: 39–48; no truncation or hidden retry.
- Drawer wrist geometry: 16 VALID, 6 AMBIGUOUS, 3 UNKNOWN; all 23,043 generated
  projections lie outside the visible annotations.
- Visible drawer mean polygon IoU: 0.044985; median annotated-pixel coverage 1.0,
  median box contamination relative to those polygons 97.4825%.
- Reference agentview geometry: 25 UNKNOWN. The human two-polygon union produces
  25 AMBIGUOUS outputs; separately evaluating both top/side polygons produces
  50 VALID local surfaces. Both results are retained.
- LocateAnything inference p50/p95: 0.446/0.560 seconds, excluding geometry and
  model initialization; these are offline latencies, not live semantic freshness.

The reference query requests FRONT_FRAME whereas all visible reference labels
are ADJACENT_FIXED_BODY. Conservative polygons are subsets; being outside them
means a candidate lacks positive annotation support, not that every outside
pixel is semantically wrong. Actual images substantiate the cavity/tabletop
examples. UNKNOWN labels are excluded from accuracy, and no NOT_VISIBLE negatives
exist here: nominal 100% visibility accuracy is not evidence of reliable abstention.
All 25 reference polygon sets are identical, limiting scene diversity.

The per-polygon reference diagnostic is explicitly **post-registration,
human-mask-plus-sensor, evaluator-only**. It preserves every polygon and candidate,
changes no threshold and chooses no winning surface. It identifies union-induced
geometry ambiguity; it is not a new runtime segmentation policy.

## Continuous geometry timing

The committed geometry-only replay reproduces all 100 sealed box witnesses.
Across 25 original bundles, complete persisted throughput is 0.1723 Hz and
whole-bundle geometry p95 is 13.970 seconds; large wrist boxes dominate cost.
This historical replay does not evaluate wall freshness.

The separate fresh static init-0 workload keeps all four sealed semantic boxes,
requires exact observed RGB/depth/calibration equivalence, and performs no new
semantic inference or robot action. It measures 29 bundles over 10.234 seconds:

- Complete persisted rate: **2.834 Hz**, requested 10 Hz.
- Single ROI p95: **107.513 ms**; complete capture-to-geometry publication p95:
  **379.731 ms**, with persistence measured separately.
- All 29 deadlines missed; **0/116 ROI outputs** met existing 0.3 s free-space or
  0.2 s contact freshness at complete publication.

Publication here means a complete diagnostic result, not runtime installation
or servo delivery. The live init-0 and 25-init replay workloads differ, so their
rates are not an optimization comparison. Shared-host compute and excluded model
inference prevent treating these measurements as an isolated hardware ceiling.
No scheduler, threshold or freshness setting was modified.

## Temporal closure

Ten bounded acquisition recipes were preregistered after the static seal, using
existing free-space atomic controls and separately logged evaluator-only scene
perturbations. They produced **354 dual-view bundles over 344 controls**, with no
robot/environment contact observed at the existing control boundaries. This does
not certify absence of transient substep contact.

All 40 initial surface hypotheses failed with `SEED_DEPTH_OR_CONTEXT_INVALID`;
subsequent updates recorded 1,376 `RESEED_REQUIRED` states. No tracked lineage was
silently recovered. All 708 observational VERIFY outputs were UNKNOWN. These
records establish failure to initialize supported tracks, not tracking behavior
under a valid initial seed. A first-case diagnostic finds all four templates
extend beyond the image and depth spread is 0.138–0.299 m, above the unchanged
0.03 m tracking gate.

The ten acquisition configs explicitly use **384×384**, while the static blind
evaluation uses **384×256**. This is an exploratory framing/calibration condition,
not a matched extension of the original 50 views. No results are pooled across
these conditions and no automatic corrected-resolution rerun was performed.
Raw acquisition does not certify that intended EEF occlusion actually occurred;
unsupported coverage remains explicit. **Zero target-valid qualifying temporal
sequences are established.**

T10 records actual asynchronous fixed-query inference while original observation
controls execute: four replies arrived 1.40–2.85 s after source capture, beyond
their original 1.2 s diagnostic proposal deadlines. No delay was injected. No
online tracker or scheduler was installed, so this is actual arrival/expiry
evidence, not an online semantic-binding rejection demonstration. The original
T10 launch failed before simulator construction due to CUDA/EGL routing; a
separately preserved launch fixes only device routing and supplies the first
physical acquisition. It is not an undisclosed episode retry.

See the [raw temporal summary](evidence/p1_grounding/temporal_observation_20261005/raw-summary.json)
and [first-seed diagnostic](evidence/p1_grounding/temporal_observation_20261005/first-seed-diagnostic.json).
The [temporal coverage report](evidence/p1_grounding/temporal_observation_20261005/README.md)
separates actual perspective/movement from absent occlusion and unsupported tracking.

## Evidence and next boundary

- [Independent review](evidence/p1_grounding/corrected_v2_evaluation_20261005/independent-review.md)
  and [inspected contact sheet](evidence/p1_grounding/corrected_v2_evaluation_20261005/independent-contact-sheet.jpg).
- [Sealed-call summary](evidence/p1_grounding/fixed_query_results_20261005/summary.json),
  including raw artifact hashes. Full local input/output/effects:
  `runs/p1/corrected-v2-fixed-query-evaluation-20261005/`.
- [Label normalization ledger](evidence/p1_grounding/corrected_v2_seal_20261005/seal.json)
  and [user correction](evidence/p1_grounding/annotation_metadata_correction_20261005/README.md).
- [Timing report](evidence/p1_grounding/sealed_semantic_timing_20261005/README.md).
- [Prospective temporal protocol](p1-temporal-sequence-protocol.md).

The evidence does not justify model integration or PUSH yet. The next technical
boundary is a source-bound association between the requested semantic subpart
and its measured surface, plus an observable reference relation and measured
freshness. This report does not implement that repair or tune the current
queries/geometry against the evaluation labels.

The subsequent [bounded development repair](evidence/p1_grounding/surface_dev_20261006/README.md)
implements source-bound POINT-to-surface association without changing these
historical results or gates. Fresh init 25/26 capture succeeded, but a CPU-only
900-second inference ceiling left no complete BOX/POINT pair. Real-data surface
association/tracker acceptance therefore remains untested; no PUSH/model
integration follows from the implementation tests.

After GPU access was restored, the [frozen-input GPU continuation](evidence/p1_grounding/surface_gpu_diagnostic_20261006/README.md)
started at clean `1af81e4`. Its first fixed-reference BOX completed; its first
POINT mixed one point with 35 boxes and exhausted 256 output tokens without EOS.
The preregistered stop ended the batch at two calls. No surface association or
tracker analysis ran, and the six remaining calls were not started. This new
boundary is incomplete model generation before geometry, not evidence against
the geometry mechanism or permission to salvage a prefix/change the condition.

The user-requested [one-pair continuation on the previously unstarted drawer-front view](evidence/p1_grounding/drawer_pair_20261007/README.md)
completed both calls with EOS under unchanged inputs/settings. POINT mixed a point
and a box, so strict admission still failed and no tracker was tested. An initial
exploratory analyzer enumerated five ROI supports before rejection; its admission
order was corrected at `34b799c` and reanalyzed without model calls. Both records
remain visible. This isolates a completed-but-mixed output boundary from the prior
reference's truncated output; it does not demonstrate valid surface association.

## Typed semantic-output contract repair — 2026-10-07

A separately preregistered typed-v1 condition reanalyzes the sealed `f2af8d8`
drawer pair. The complete reply has one POINT plus one auxiliary BOX; typed
admission preserves both, uses only the independent BOX call as ROI, and binds
one of five unchanged supports. RGB review supports a drawer-front interpretation
with identity and push safety still unverified. The next tracker initialization
stops at a preexisting experiment-harness `WRONG_EPISODE`, before any tracker
result. No retry, fixed-reference stage or robot action followed. See the
[full evidence and failure boundary](evidence/p1_grounding/semantic_contract_20261007/README.md).

## Episode harness repair and independent reference gate — 2026-10-07

The one-line harness correction uses the recorded episode ID. One separately
registered replay of the same reviewed sealed drawer pair initializes TRACKED
with unchanged support/context/depth gates. This establishes static initialization,
not temporal tracking or push safety. The subsequent independent reference gate
reuses the historical no-EOS POINT and still rejects it under typed-v1; no
reference geometry/track begins, and VERIFY stays UNKNOWN. See
[results and preserved evidence](evidence/p1_grounding/tracker_episode_repair_20261007/README.md).

## Independent fixed-reference completion budget diagnostic — 2026-10-07

After local freezing of the prior tracker/evidence checkpoints, one independent
condition changed only native POINT max_new_tokens256→1024. Same sealed RGB, query,
request bytes, checkpoint, old BOX, typed contract and geometry/tracker gates.
The fresh call still generated1024tokens withoutEOS; it stops before POINT parsing,
association or reference tracker. Thus budget extension alone is insufficient by
1024; reference/VERIFY stayUNKNOWN. No automatic retry or other decoder was run.
See [preregistration, full raw evidence and audit](evidence/p1_grounding/reference_budget1024_20261007/README.md).
