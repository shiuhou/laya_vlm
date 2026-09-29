# Independent review of the gripper visual-mask control

The control changes the intended mask source while preserving the original
observations and collision-distance maps. Both earlier hand-edge minima are
excluded, but this does **not** produce a clean scene-distance measurement.
The visual and collision masks are not nested; the replacement admits some
previously excluded points, including a zero-distance pad witness before action
25. No mask expansion, union, threshold change or outcome-driven correction was
made.

Pre-measurement source review confirmed gripper-root descendant ownership:
exactly three noncolliding group-1 visual meshes, with 3,613 hand vertices and
318 vertices per finger. The complete old body/site/collision calibration had
to match before export. The guarded constructor's one `mj_step1` preserved
time/qpos/qvel; no integration/rendering occurred. The numerical worker receives
the three visual meshes, unchanged own joints/depth/camera calibration and the
five unchanged collision-distance maps. It receives no scene/contact/target
labels or RGB. Visual FK produces only projected convex enclosures, which
replace the old mask without altering distance values.

The [independent file audit](../../../embodied_runtime/experiments/gripper_visual_mask_evidence_audit.py)
passes static-export and measurement artifact hashes/seals, identical copied
depth/map files, unchanged own packets/shared calibration, stored visual-mask
unions, replacement counts, all summary statistics and proxy contributions,
old-witness exclusions and 24 nearest-pixel/backprojection checks. It reruns no
FK, projection, distance computation, renderer or simulator. The
[portable result](gripper_visual_mask_independent_audit.json) retains identities
and all checked measurements.

| Replacement-mask result | Before action 24 | Before action 25 |
| --- | ---: | ---: |
| Old collision-mask pixels | 6,169 | 6,265 |
| New visual-mask pixels | 6,191 | 6,268 |
| Newly excluded / newly admitted | 35 / 13 | 13 / 10 |
| Old hand minimum excluded | Yes | Yes |
| New hand minimum | 0.278252 mm | 0.233802 mm |
| New union minimum | 0.278252 mm, hand | 0 mm, finger1 pad |
| New union witness pixel | (237, 102) | (156, 155) |

The later zero is an unchanged stored point-to-solid-collision-proxy distance
at a newly admitted pixel. It is not evidence of scene penetration or measured
contact. Residual surface identities remain unknown. Convex visual projection
enclosures are not rendered segmentation; raster boundaries, visual/collision
mesh differences and unvalidated camera/base/cache synchronization remain.
Removing two visually suspicious witnesses establishes that this calibrated
mask excludes those pixels, not that every remaining pixel is environment.
Likewise, the result does not identify omitted arm links as the cause.

Producer freeze: `9c5e40f`. Visual calibration SHA-256:
`c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98`.
Raw directory: `runs/autonomous-research/gripper-visual-mask-control-01` under
the main checkout. This supplements the prior
[sensor-proximity review](sensor_gripper_proximity_independent_review.md);
neither result validates scene clearance or an action gate.

```sh
python -m embodied_runtime.experiments.gripper_visual_mask_evidence_audit \
  --raw /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/gripper-visual-mask-control-01 \
  --output /tmp/gripper-visual-mask-independent-new.json
```
