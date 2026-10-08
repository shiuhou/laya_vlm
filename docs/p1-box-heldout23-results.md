# HO23 fixed automatic BOX A/B experiment — generation complete, blind scoring pending

The authorized single batch is complete through frozen geometry: **23 fresh
scenes,69LocateAnything requests,46arm/frame outcome slots**, no retries or
condition changes. New query B produces **no SAM outputs and no geometry
candidates** under the unchanged admission chain. Semantic localization scores
remain **UNKNOWN until the new human annotations arrive**. This is not a
completed blind evaluation or P1 PASS.

[Approved design](p1-autonomous-box-repair-design.md), revision33c358c.
Generation/capture runner freeze: `f71e452`; independent scoring code: `a314003`.
[All23 operational results and sealed evidence](evidence/p1_grounding/box_heldout23_20261008/README.md).

## Observed results, without reading annotation

| Layer | Baseline A | Repair B |
|---|---:|---:|
| BOX request attempts |23|23|
| Complete EOS and typed BOX admission |23/23|3/23|
| BOX no-EOS |0|20|
| BOX localization correctness |UNKNOWN|UNKNOWN|
| SAM generated frames |4/23|0/23|
| Native masks retained/evaluated |12|0|
| Raw geometry proposals |8,467|0|
| Proposals after original mask/POINT containment |7,084|0|
| Candidate identity / human-region membership |UNKNOWN|No proposals; labels still pending|

The shared automatic POINT has12complete-EOS responses:4typed admissions and
8POINT_CARDINALITY failures. Another11have noEOS. All4typed points have valid
sampled depth; whether they hit the front remains unscored. A/B use exactly the
same per-scene POINT output hashes. BOX calls ran independently on **all23**, even
when POINT failed; thus B's20noEOS BOX results cannot be hidden under POINT failure.

B's three admitted BOX scenes fail at later prompt admission: init30 POINT
cardinality, init34 POINT_OUTSIDE_ORIGINAL_BOX (meaning outside B's supplied BOX),
init44 POINT noEOS. B geometry is **NOT_EVALUATED because no SAM masks exist**;
this must not be reported as a failed plane/tool algorithm on23images.

A generates masks only for init34/35/40/49. Of12native masks,7produce candidates,
2reject AMBIGUOUS_DEPTH_COMPONENTS,2reject INSUFFICIENT_CONNECTED_SUPPORT, and
1has a valid local plane but NO_TOOL_INTERIOR_CANDIDATE. All12were evaluated;
one point-contradictory mask's1,383proposals remain in raw evidence and are
excluded only by the already frozen containment contract. No mask winner is
selected. All geometry proposals retain usable_status=UNKNOWN.

The all23 CSV keeps failed/incomplete slots and explicit ANNOTATION_PENDING.
Missing BOX/POINT/mask stages are not silently removed from the denominator.
Semantic-grade cells are blank/null, not fabricated zero localization scores.

## Inference and remaining uncertainty

Observed availability regression: BOX typed admission falls23→3with only the BOX
query string changed. Independent audit found identical full-RGB input tensors
per scene, exact registered queries/decoder conditions and fresh request history.
This supports a negative **completion/typed-availability** result for this exact
query condition. It does not establish that the three completed B BOXes localize
worse, or that A's23boxes identify the correct part. Annotation will answer those
separately.

B cannot meet the preregistered19/23clean-candidate requirement: no candidates
were generated anywhere. This failure already follows without human labels.
The declared semantic and visibility scoring remains unfinished, so no numerical
BOX localization rate, mask target purity, A clean-candidate rate, or P1 decision
is asserted from these operational counts.

Next required work is the blinded annotation scoring of this same sealed batch,
not more inference. If labels confirm a partial BOX localization benefit, report
it separately from the failed end-to-end chain. After final review, assess the
independent geometry-domain proposal as approved; do not assume it repairs the
shared POINT availability bottleneck (4/23typed). No further query/decoder tuning,
model change, BOX-only fallback, new sample or repair was started.

## Provenance and boundaries

Metadata audit examined6,164documents across28archives and loose research records;
no prior observation exposure for init27–49 was found in available local evidence.
Their50×77source-state inventory has no heldout/development or within-heldout
vector collisions. Full inventories containing all50state hashes are not treated
as prior visual observations. New first-capture wrist RGB blobs match none of
1,744historical RGB hashes, and new raw pixel hashes are unique. This cannot prove
absence of deleted/unrecorded/remote exposure; the audit scope is explicit.

Capture: original task, seed1, init27–49,384×256, original agentview+wrist sensor
configuration, constructor settling only, no post-reset robot command. Only wrist
RGB reaches models. GPU2 EGL capture and the existing laya-embodied environment;
LocateAnything and SAM use the separately locked original environments on
GPU UUID `GPU-293fca5f-bdb8-2235-fa2e-18ab6c488b36` in fresh processes.

The model-facing generator manifest contains no annotation inputs. BOX A/B and
POINT raw calls include full token IDs, formatted requests, image tensor hashes,
EOS evidence, outputs and timing. Same sensor/calibration/EEF, original BOX ROI,
native-mask-depth/2, unchanged SAM/geometry/tool gates and candidate ordering.
No oracle target state, mask, official success, human BOX/POINT or human candidate
selection. Calibration confidence remains null; no runtime/controller changes.

Independent read-only audit passes815checks including capture hashes, all69raw
requests, fresh one-user-message templates, per-call past_key_values initialization,
shared POINTs, native logits/masks/ordinals and all12geometry evaluations. No
repeat inference or geometry run was used for the audit.

Offline p50/p95 seconds: BOX A .743/.752; BOX B3.102/4.173;
POINT2.599/4.231; A native geometry3.873/8.237. A SAM encode .042/.141 and prediction
.013/.083. These are not continuous end-to-end Hz. No latency optimization.

Tests:5runner/packet and7scorer synthetic tests passed; Ruff F checks pass.
The scorer test specifically verifies that failed POINTs do not suppress BOX
accuracy measurement. No development images were rerun for tests or tuning.

## Pending human input and resume

Raw-RGB-only packet:
`/home/junhongli/projects/laya/p1_annotations_inbox/heldout23-20261008/index.html`.
Downloadable ZIP is beside it, `heldout23-20261008-blind-annotation.zip`.
All23new images require human annotation. The historical annotations are not
reused; neither AI-draft masks nor predicted boxes appear in the annotation UI.
Exact frozen rules/2 bytes are retained with an explicit new23-frame scope.

After the complete export is supplied, validate and score **without new model calls**:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_box_grounding_heldout_scoring --output runs/p1/box-heldout23-20261008 --packet /home/junhongli/projects/laya/p1_annotations_inbox/heldout23-20261008 --annotations PATH_TO_COMPLETED_EXPORT
```

That command verifies all generation seals before reading labels, computes all
four layers and paired statistics, and writes a new exclusive scoring stage.
Then inspect paired overlays, append the final evidence/report checkpoint and
stop for review. Do not resume generation, mask prediction or geometry.
P2/tracker/temporal/Qwen/Laya/fixed-reference experiments remain unstarted.
