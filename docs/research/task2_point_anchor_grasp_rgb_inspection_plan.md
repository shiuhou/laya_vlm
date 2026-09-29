# Fixed original-RGB inspection of the POINT-anchor mechanical matrix

Prepare forty original images, ten per cell, in the registered order
whole-close, whole-open_hold, neck-close, neck-open_hold. No cell, time, crop,
overlay or view is selected from apparent outcome quality.

| Anchor | Preintervention | After eight close/hold controls | All eight lift controls |
| --- | ---: | ---: | --- |
| Whole |30|38|39–46|
| Neck |29|37|38–45|

Indices are the merged zero-based sensor captures. The preintervention image is
the final approach endpoint, before the scripted GRASP or executed open STOP
hold. Postclose/hold is control7; lift images retain all controls0–7.

`task2_point_anchor_grasp_rgb_report.py` reuses the prior short-lift report's
unscaled384px Pillow tiles with separate24px headers. It exports each original
RGB unchanged and verifies exact round-trip pixel equality, plus a fixed two-row,
five-column sheet per cell. Headers identify boundary, capture and read time;
full-precision times and original source metadata stay in JSON. No duplicate NPZ,
mask, colored overlay, crop, resampling, geometry calculation or LK feature is
created. The prior report's mask-dependent entry point is not used.

Canonical report production and sensor-source admission wait for all four cells
to close and the actual source hashes to be reviewed. The expected raw directory
is `runs/autonomous-research/task2-point-anchor-grasp-transfer-run-01`. Preparation
does not assert that it exists or authorize its execution. A failed/incomplete
matrix remains incomplete; no frame or comparison is invented or replaced.

Inspect the four original-RGB sheets and individual originals where needed.
Record visible gripper aperture/placement, visible bottle parts, occlusion,
apparent image motion and visible axis/tilt cues across the fixed sequence.
Distinguish what is visible from what is obscured or ambiguous. Do not convert
apparent co-motion, occlusion or a finger-flanked outline into holding truth,
pad contact, support-free retention, grasp success or anchor superiority.
Root/joint raw-mechanics evidence remains separately attributed. No masks are
available and no new rendering is authorized by this inspection.

The exporter leaves `visual_inspection_completed=False`: successful image export
is not visual review. The later independent inspection receipt must identify the
actual viewed artifacts and hashes, observations and limits after those views.
The source-admission receipt may later support the unchanged LK adapter, but
image reporting itself performs zero tracking or co-motion extraction.
