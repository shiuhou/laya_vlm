# Fixed image-motion representation comparison

**Root approved implementation and one frozen extraction after reviewing the
preparation at `6a56c12`. No new features have yet been extracted.** The preparation
consisted of an inventory of existing source/reports and this fixed full-population proposal.
The hypothesis was formed after seeing the completed 3D curves and four
exploratory extreme-track contexts; this is a development comparison, not a
preregistered independent validation of a general holding detector.

## Inventory: related work exists, but this comparison is absent

The search covered experiment source and Markdown research/evidence reports in
this worktree and the canonical root, followed by inspection of the relevant
numeric and reporting functions. No existing report was found that summarizes
this complete four-cell population's native RGB displacement together with
relative projected own-TCP image motion.

| Existing work | What it measures | Why it does not already answer this question |
| --- | --- | --- |
| `point_temporal_probe.py`, [protocol](point_temporal_probe_protocol.md), autonomous research log iteration 007 | RGB-only LK versus frozen pixels under static/transformed/occluded imagery; 208 rows, reference-coordinate errors in pixels | Synthetic correspondence falsifiers with one seed per condition; no full 492-seed physical matrix or projected-TCP comparison |
| `interaction_observability.py` / `_report.py`, [findings](../evidence/autonomous_research/interaction_observability_findings.md) | Three assistant-selected landmarks, native RGB coordinates/residuals, RGB-D world displacement and own-TCP world residual | Different initialization/source/horizon; image overlays and forward/backward residual are not image displacement relative to projected TCP |
| `task2_box_temporal_probe.py` / `_report.py` | Full 492-seed paired source, 45,264 rows; initial/preclose 3D point and point-minus-TCP z/norm summaries | `reference_delta` operates on depth-derived world points and saved world TCP; its four `METRICS` are in metres |
| `task2_track_coordinate_association.py`, [findings](../evidence/autonomous_research/task2_track_association_findings.md) | Same saved native tracks under floor versus nearest-center depth association | Tests the discrete depth association; it preserves native XY but does not summarize RGB motion relative to projected TCP |
| `task2_short_lift_transfer.py` / `_report.py` | 29,520 rows from the previous paired 10 mm lift, preclose world-point/TCP deltas and overlays | Different source and still the same four 3D metrics |
| `task2_point_anchor_retention_adapter.py` / `_report.py`, [current findings](../evidence/autonomous_research/task2_point_anchor_retention_findings.md) | Current 91,512 rows, four 3D metrics, complete min/max/IQR, all-position overlays | The overlays display saved XY; they do not compute population image displacements or projected-TCP residuals |
| `task2_point_anchor_extreme_track_diagnostic.py`, [diagnostic](../evidence/autonomous_research/task2_point_anchor_extreme_track_findings.md) | Four deterministic final-3D-extreme seeds, exact XY/pixel/depth changes and consecutive stored-world jumps | Post-outcome selected case explanations; no full-population 2D summaries or TCP projection |

The generic `association.py` query tracker uses IoU/world-distance gates for
boxes and is unrelated to this saved LK population. Own-wrist history work
projects sensor records into a schema, not TCP coordinates into the camera.
Neither should be introduced as a new tracker for this comparison.

## Minimal proposed condition

Reuse the complete sealed four-cell extraction, in original condition order,
all 492 row-major seeds, all 47/47/46/46 frames and all **91,512 rows**. Keep
preclose capture 30 for whole and 29 for neck as the only reference. All 17
preclose-through-postlift capture summaries per cell remain; earlier rows have
null reference metrics. No new tracker, seed, model, physical episode, render,
mask, depth filter, interpolation, segmentation, semantic classifier or threshold.

Pin the current sensor seal
`39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60`, journal
`d58bd52625e01a89299cce9581c1d9684ee0467c6a0aaffbd043976147558f4c`, source admission
`6d283ad5d098ea1e532e82aaf95464df796a01a1cce05e96dd9dae1a9e969681`, and independent
stored-output audit
`e188710d477c16ce0bd09d61004293015fe15633c12995abdd9252e9dba21b86`.
The four exact track hashes are already listed in the
[extreme-diagnostic source freeze](task2_point_anchor_extreme_track_diagnostic_protocol.md).
The actual implementation freeze must bind them directly and remain separate
from the original extraction. No result from the extra-GRASP physical condition
is added to this source.

**A. RGB-coordinate displacement.** For each admitted saved native floating
coordinate `p_i=(u_i,v_i)`, use `Δp_i=p_i−p_preclose`. Retain both vector components
and summarize image-down displacement `Δv` and Euclidean pixel norm `||Δp||`.
This computation uses RGB-derived native coordinates only, with no rounded
sample pixel, sampled depth, world point or sensor-3D displacement input.

**B. RGB plus projected own-TCP motion.** Project the explicitly saved own TCP
with that frame's saved K and camera-to-world transform. Let `q_i` be this TCP's
floating image index coordinate; compute `Δq_i=q_i−q_preclose`, then
`r_i=Δp_i−Δq_i`. Retain both vectors and summarize `r_v` and `||r||`, in pixels.
This branch adds calibrated 3D own-robot state, so it is **not RGB-only**. It
still reads no measured scene depth and never infers a target 3D point.

Use the existing rigid camera transform convention: camera point
`c=Rᵀ(TCP−t)`, homogeneous projection `h=Kc`, edge-coordinate image projection
`h_xy/h_z`, then subtract `(0.5,0.5)` to express the result in native integer-center
index coordinates. The same constant half-pixel offset cancels in `Δq`; state
the convention explicitly anyway. The pure `pixel_footprint.camera_vertices`
helper already implements the rigid world-to-camera arithmetic and checks
rigidity; its module SHA-256 is
`5559a4ee170e50f45295252b3db2b08553b3ba0a2b886e8bbe6cdbc50b15da8c`.
The existing `render_measurement_diagnosis.projected` function uses the same
projection algebra, but importing its evaluator/physical collection module is
unnecessary. A tiny sensor-only projection wrapper can call the pure transform
helper and apply K directly. No FK or object geometry is needed.

Native `seeded`/`native_status_ok` remains the only RGB admission, with finite
current/reference XY required. Failed attempted coordinates remain recorded
but do not become admitted motion. Missing current/reference own TCP or an
undefined/nonfinite projection (including camera z≤0) makes only branch B null;
branch A can remain available. Off-image finite TCP projections are retained,
not clipped or used as a rejection threshold. Preserve original source read
times and unknown sample/cache times. No temporal synchronization is invented.

The new feature function receives an explicit whitelist of native XY/status,
seed/capture identity, saved own TCP/time/provenance and bound K/T. It does not
receive sampled depth, selected-depth pixel, surface-world point, old 3D deltas,
contact/object labels or masks. Read only K/T arrays from the bound source NPZs;
RGB and depth need not be decoded. Preserve all original output files unchanged.

## Fixed outputs and assessment

Write all 91,512 feature rows and complete capture summaries. Each of the four
pixel metrics reports count, missing count, median, q25/q75, minimum and maximum
with denominator 492. Retain all underlying Δp/Δq/r vectors and raw native/source
fields. Report initial, preclose, postclose/hold and postlift checkpoints and
complete four-cell curves with shared scales within each pixel metric. Seal the
new image-motion outputs before joining the existing sealed 3D summaries for a
side-by-side descriptive comparison. No 3D feature is recomputed.

The substantive comparison is whether the close/open pattern remains visible
in native image displacement and relative projected-TCP motion, and how the
full tails behave when sampled scene depth is absent. Keep the four previously
fixed diagnostic seed IDs 3/11/3/17 available as labeled exploratory references
within the full population; they do not define a retained cohort or tune a rule.
Do not add a new max-based selection or depth-based grouping for this proposal.
If depth supplies distinctions that these 2D views fail to show, report that
alternative with the same complete curves. No accuracy/AUC, fitted cutoff,
holding label, anchor ranking or statistical independence claim is proposed.

Pixels and metres cannot be compared as interchangeable error magnitudes.
Image-down displacement is not world-vertical displacement. Points and TCP at
different depths can have different projected motion under a common rigid
translation; an image residual is not a calibrated rigid-attachment error.
Camera-ray motion, perspective, rotation and occlusion remain limitations, and
2D LK can still drift or follow the wrong surface. Smaller image tails would
not establish identity or holding, and these executed close/open conditions
are not validated held/not-held labels.

The implementation includes small synthetic checks for
projection/index convention and offset cancellation, exact reference deltas,
native failure/null preservation, missing TCP affecting only branch B, and
complete row/summary denominators. Freeze code/environment/output contract
before actual new arithmetic. Until the exact implementation freeze passes its
quick whitelist/null review, no TCP projection or native-pixel displacement is
extracted from actual sources.

## Implemented execution contract

`task2_point_anchor_image_motion.py` provides the small stored-only wrapper.
Its input whitelist preserves the nine native fields, seed/capture identity,
source stream/artifact hashes, phase/control metadata, saved own TCP and read-time
provenance. `rgb_delta` receives only the native record. `project_own_tcp`
receives only saved own position plus K/T; their results are combined afterward.
Only K/T arrays are decoded from bound source NPZs. Synthetic tests cover these
boundaries and full 492-denominator summaries, in addition to the arithmetic.

Use `/home/junhongli/miniforge3/envs/locateanything/bin/python`, Python
`3.10.21 | packaged by conda-forge | (main, Aug 21 2026, 22:42:31) [GCC 14.4.0]`,
NumPy `1.26.4`, and `PYTHONDONTWRITEBYTECODE=1`. No OpenCV function is called.
Pin the pure transform module hash above and unchanged summary helper module
`task2_box_temporal_probe.py` SHA-256
`655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50`.

The reviewer supplies one compact JSON receipt with `status: "pass"`, the exact
`freeze_commit`, `protocol_sha256`, and `authorized_batches: 1`. Root has already
authorized execution after this quick code-boundary review; no further human
gate is added. The wrapper requires clean matching code and pinned runtime,
rechecks the existing source hashes, and creates only the new fixed raw output
`task2-point-anchor-image-motion-run-01`. An existing directory prevents rerun.

Four append-only feature JSONL files retain every row, flushing/fsyncing each
completed seed. `image-motion-summary.json` contains all 186 capture summaries;
the complete sensor seal binds rows/summaries, protocol, review and run records
before any later report reads old 3D summaries. Terminal status records all
1,968 tracks / 91,512 rows, and final artifact hashes include the closed journal.
On exception/interrupt, partial files and written-row/completed-track counts are
retained with zero retries and no complete seal. No complete result is inferred
from a partial final line after an external hard kill.
