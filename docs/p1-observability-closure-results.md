# P1 observability closure: Gate C

The bounded round is complete. **P1 task acceptance did not pass.** Drawer target
association remains insufficient; continuous drawer/reference tracking and
drawer-relative VERIFY are not established. P2a/P2b, PUSH, Qwen and Laya remain
off. The selected README milestone route is unchanged.

The frozen baseline `d1ed91e` and its reference POINT negative evidence are
preserved. The 256/1024-token no-EOS condition is
`UNSUPPORTED_INCOMPLETE_GENERATION`; no further decoder, token-budget or query
experiments ran. This round made **zero new model calls**.

## Three observability answers

**1. Is a drawer-front surface visible?** The completed immutable human dataset
has 25 VISIBLE wrist frames and 25 UNKNOWN agentview frames; UNKNOWN is not
NOT_VISIBLE. Complete RGB-D inventory finds local plane support intersecting the
annotated region in **21/25 archived BOX searches** and **25/25 full-frame
searches**. This is evaluator-only support existence, not a task-valid tool patch.
The unchanged original pipeline yields a positively annotated tool-interior
candidate in **0/25 init states**, below the required20/25.

**2. Is a fixed cabinet reference observable?** The annotations identify adjacent
cabinet-body regions in 25 agentview frames; all25 have overlapping local plane
supports in the new inventory. However cabinet identity, mechanical attachment,
temporal fixedness and the closed-drawer relation remain unestablished. The
reference query asks for FRONT_FRAME, while the visible annotations describe
ADJACENT_FIXED_BODY. A side/top surface is not automatically a closed reference.
The answer is **REFERENCE_UNKNOWN**, not proven REFERENCE_NOT_OBSERVABLE.
VERIFY remains UNKNOWN.

**3. What fails first?** For the original drawer pipeline, BOX-to-target-surface
association/ROI contamination is the strongest observed bottleneck. Median wrist
BOX contamination relative to the conservative human polygons is **97.4825%**,
despite median annotated coverage1.0. Original geometry is16 VALID,6 AMBIGUOUS,
3 UNKNOWN; **all23,043 candidate projections lack positive polygon support**.
The inspected contact sheet shows table points filling the broad wrist ROI at
init12/24. Outside a conservative polygon alone does not prove every point is
wrong; the raw image inspection supports the table/cavity examples. Depth
component ambiguity and plane/depth rejection also occur. A blanket claim that
the camera contains no relevant surface is unsupported.

See the [offline inspection sheet](evidence/p1_grounding/observability_closure_20261007/offline-evaluation-contact-sheet.png).
Yellow is the sealed model BOX; green is immutable evaluation annotation; red
is the complete original candidate projection. This is an offline evaluator
artifact and was never provided to perception, tracking or policy.

## Generic geometry and immutable evaluation

`reference_candidates.py` enumerates every sensor-supported face and finite
support boundary in canonical inventory order. It records source camera/frame,
RGB/depth/calibration hashes, ROI, support row spans, residuals, overlaps,
four-neighbor measured adjacency and rejection reasons. Adjacency requires the
original0.015m connectivity gate. Boundaries may be ROI/depth/occlusion boundaries;
they are not asserted physical edges. No infinite line, largest/nearest-plane
selection, box-center reference, label seed or oracle target state is introduced.
Identity/fixedness/closed relation remain UNKNOWN; confidence remains uncalibrated
and null. A local plane-valid fit does not satisfy the full patch/tool/safety gates.

The sensor-only generator reused the sealed100 BOX calls and50 recorded views,
retained all original patches and complete hypotheses, and sealed its outputs
before the separate scorer opened the corrected-v2 labels. The original dataset,
rules, statuses, polygons and metadata-correction receipts remain unchanged.
Annotator independence is user-reported, not independently authenticated. This
is a reanalysis of an existing evaluation set, not a new held-out generalization
result. No threshold or query was tuned against it.

Original rejection breakdown:

| Entity / camera | Original result |
|---|---|
| Drawer / wrist |16 VALID;6 ambiguous components;2 degenerate planes;1 insufficient valid depth |
| Drawer / agentview |24 insufficient plane support;1 ambiguous components; labels UNKNOWN |
| Reference / agentview |25 insufficient plane support; labels VISIBLE |
| Reference / wrist |22 ambiguous components;1 insufficient plane support;2 VALID; labels UNKNOWN |

Inventory overlap improves diagnosis, not execution readiness. There are no
runtime admissions based on polygons or generic local fits. The historical
human-mask geometric upper bound remains evaluator-only and was not used here.

## Temporal result

Ten fresh software-rendered cases recorded **600 existing executor controls,
610 dual-view bundles and1,220 camera views**. Each new rendering condition has
one attempt per case; the earlier pre-capture EGL failures remain separately
recorded. Perception never opens the evaluator fixture/contact journals.

| Cases | Actual evidence | Qualification |
|---|---|---|
| T01/T02 | Wrist perspective changes, approximately9.15°/13.31° | AI-agent RGB review; target association not established |
| T07/T08 | Small drawer movement / reversal under isolated observation fixtures | Scene changes visible; no valid tracked drawer chain |
| T09 | Small cabinet-boundary displacement under isolated fixture | No validated fixed-reference identity or lineage |
| T03–T06 | Fresh HOLD recordings | Occlusion event UNSUPPORTED: no bound feature/conservative EEF sweep certificate |
| T10 | Fresh HOLD recording | Occlusion and actual delayed semantic reply UNSUPPORTED |

There were no subsequent acquisition runtime/contact boundaries. **Zero trackers
initialized; all independent drawer/reference camera chains remain UNSEEDED.**
There are zero qualifying continuous-tracking sequences. Absence of LOST,
AMBIGUOUS or wrong-ID continuation in uninitialized chains is not a tracking pass.
Original timestamps/source identities are retained; no archived seed was
transplanted and no hidden reseed or retry repairs missing evidence.

All20 raw contact sheets were inspected by an AI agent; root additionally
reviewed T01/T07/T09. This is not human evaluation. The raw-only review packet
contains160 images and20 complete videos, no model/geometry overlays, and zero
completed human temporal annotations. Thus the95% visible temporal association
criterion is not evaluable and cannot pass. Packet:
`runs/p1/observability-closure-temporal-software7-packet-20261007/index.html`.

## Live throughput and freshness

Three fresh resets requested10Hz for30s at init0/12/24, dual384×256 cameras.
The workload is two archived BOX search windows plus full-frame context per
camera: exhaustive inventory/candidate assembly, publication and persistence.
Archived windows are diagnostic regions, not fresh semantic seeds. There is no
initialized tracker, so **valid-target Hz0** is an availability statement, not
a model-choice or tracker-performance measurement.

| Init | Captured bundles | Published snapshots including drain | Replaced bundles | Publication Hz within30s | Geometry pipeline p50/p95 |
|---|---:|---:|---:|---:|---|
| 0 |114 |2 |112 |0.0333 |26.513 /26.698s |
| 12 |112 |3 |109 |0.0333 |26.841 /26.857s |
| 24 |113 |2 |111 |0 |32.780 /33.456s |

Total339 captures,7 snapshots,332 atomic bundle replacements. All14 published
diagnostic view ages exceed the unchanged0.3s free-space gate. Sim-age stays0 in
this static cost test; wall-age p95 is27.690/55.843/39.447s. Init12/24 complete
drain took88.199/72.510s; pending queue age and persistence are reported separately.
Do not divide a single-ROI cost into an end-to-end Hz claim.

For init0, archived BOX searches individually cost0.194–0.577s; full-frame
agentview inventory plus candidate assembly cost about20s. This exhaustive
diagnostic is computationally unsuitable as a continuous control loop under
the tested condition. It does not measure what a successfully seeded,
target-specific tracker would cost. All seven persisted source-identity records
replayed successfully.

## Operational failures and exact revisions

Initial Mesa-only rendering still chose hardware EGL device0 and failed before
capture. Read-only enumeration identified device7 as `EGL_MESA_device_software`.
A separate preregistered environment condition set `MUJOCO_EGL_DEVICE_ID=7`;
same code/config/query/gates, with original failures preserved. This is software
rendering and is not a latency comparison against the historical GPU condition.

Init0 completed capture and two durable snapshots but failed while serializing
boolean histogram keys. Exact recoverable metrics were derived from preserved
logs; unavailable journal/end metrics remain null. Init0 was not reexecuted.
An isolated worktree changed only those keys to strings; init12/24 then produced
actual canonical summaries. The temporary mirrored test was removed; real
serialization provides the relevant regression evidence.

- `228482f`: freeze receipt and preregistration.
- `0b5afe9`: generic reference candidate enumeration.
- `107e99c`: source-bound temporal tooling/configuration.
- `44944a1`: latest-frame workload measurement.
- `fb2b299`: static generator/scorer and actual experiment checkpoint.
- `eb39068`: isolated reporting-only revision used for init12/24; preserved tag
  `p1-stream-reporting-condition-eb39068`.
- `daf6a26`: integrated production serialization fix; geometry/executor unchanged.

Focused verification:50 geometry/reference/stream/temporal/tracker tests plus2
static-scorer tests passed, changed Python Ruff passed, static generation/scoring
completed, and actual init12/24 summary serialization succeeded. No broad suite
or redundant replay experiments ran.

## Scope decision and next milestone

[Machine-readable gate](evidence/p1_grounding/observability_closure_20261007/scope-gate.json):
**Gate C — P1 perception insufficient.** Static target-tool support fails0/25;
continuous association qualification and target freshness are unavailable.
Reference/VERIFY remains UNKNOWN. Gate B cannot follow merely from one successful
development initialization. The round stops here; no decoder extension, models,
PUSH or automatic fallback occurs.

The next separately defined P1 intervention should address **BOX-to-target-surface
association** using the planned segmentation/sensing alternatives on development
data, preserving the sealed evaluation set and original gates. It must then earn
live target association and temporal qualification. Reference closed-relation
geometry remains a separate gate. The next control milestone remains **P2/B0**,
followed by B1–B4 model-contribution evaluation; the architecture is not reopened.

Evidence, checksums, reconstruction commands and cleanup receipts are indexed in
[this evidence directory](evidence/p1_grounding/observability_closure_20261007/README.md).
Raw RGB-D, human evaluation packets and historical evidence remain preserved
locally; lossless portable archives retain generated hypotheses and review data.
