# Frozen sensor-point / own-gripper proximity diagnostic

This is a read-only development diagnostic using already inspected boundaries
24 and 25, not held-out validation. Freeze this protocol, worker, archive
adapter and analytic tests before computing their proximity results. No new
simulator construction, rendering, dynamics, action execution, controller,
contact classification, action gate or policy is permitted.

## Question and discriminating comparison

Does a raw depth point cloud, combined only with calibrated current own-gripper
geometry, provide useful observed-surface proximity information beyond a TCP
point? Compare all valid depth points with points outside a **partial gripper
silhouette exclusion**. A zero or small raw distance may simply come from the
robot's own visible surface. Residual point identity remains unknown: the
calibration has no arm/wrist visual envelope, and gripper collision proxies can
differ from rendered surfaces. A contaminated or uninformative result is valid.

The measurement is distance from observed points to known gripper convex
proxies, not scene distance or clearance. Missing, occluded and out-of-view
geometry is unknown. No measured distance or descriptive count is an action
admission threshold, collision criterion or free-space certificate.

## Fixed source and firewall

Use `coarse-initial-point-02/episodes.jsonl`, SHA-256
`e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf`.
Exactly two RGB-D captures are registered:

| Development boundary | Frame | SHA-256 |
| --- | --- | --- |
| 24 | `frames/capture-000025.npz` | `3999edda9befca7a7dad6080c66bd03f609e408ce5a7563994b9704422029dab` |
| 25 | `frames/capture-000026.npz` | `907e9f36073adfdd7397fb79a8c205ce7567d7a729cc69d9b512087a42383d05` |

Read own positions from the matching action's control-0 `state_before` using
only the previously registered nine own-qpos indices 1–9. Require exact time
equality with the capture record, but do not pass timestamps to the estimator.
These are **simulator-state-derived own-joint encoder analogues**, not physical
sensor readings. Poison all 31 nonrobot qpos and 27 nonrobot qvel entries with
NaNs and a fixed finite sequence and require identical extracted packets.
Pin the source admission map to SHA-256
`f60adc5b01aa0ccd527459d5711269a66f85b70b8b4cc32105033768251fec51`,
which fixes joint names and both position/velocity indexing used by poisoning.

Reuse sealed `robot-geometry-observability-03/robot-calibration.json`, SHA-256
`11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa`.
It contains static robot bodies/joints, two sites, and five gripper collision
vertex sets. Its installed base transform is assumed known. Recorded camera
intrinsics/extrinsics are likewise **assumed simulator camera calibration**;
physical calibration accuracy and encoder/camera synchronization are untested.
Matching archive times do not establish exact cache synchronization.

The standalone numerical subprocess receives a sanitized directory containing
only `request.json` (robot calibration and two nine-value own-joint packets,
opaque labels `sample0`/`sample1`) and two NPZ files containing `depth_m`,
`intrinsics`, `camera_to_world`. No raw archive path, full simulator state,
target point, object pose/geometry, contact label, force, candidate action,
outcome or evaluator API is passed to it. RGB is read for witness inspection
only after numerical outputs are sealed. The archive adapter's source record
IDs and selection metadata remain outside the numerical subprocess.

## Fixed geometry and data handling

Backproject every finite positive recorded optical depth at pixel center
`(u+0.5,v+0.5)` using `K^-1 [u+0.5,v+0.5,1] * depth`, then recorded
`camera_to_world`. Do not crop a target region, denoise, interpolate missing
depth or tune a range cutoff. Nonfinite/nonpositive samples remain invalid.
Positive background/far-plane samples are not independently validated returns.

Use the frozen pure NumPy robot FK. Each of the five collision vertex sets
defines a solid convex hull. Compute Euclidean point-to-solid-hull distance:
zero for interior points, otherwise minimum exact point-to-triangle distance
over hull facets (face projection or nearest edge). This is a convex proxy,
not a claim about the complete physical collision envelope. Use `1e-12` solely
as the numerical half-space containment tolerance, never as a sensor threshold.

Project each gripper hull into the image and exclude every pixel center inside
the union of projected convex polygons, regardless of observed depth. This
conservative partial exclusion can also remove scene points in front of the
gripper. It is not a pixel identity classifier. A wholly behind-camera proxy
masks nothing; a proxy crossing the camera plane excludes the whole frame;
a wholly off-image projected proxy masks no pixel centers. Record these cases.
An empty valid or residual set produces `nearest = null`, never infinite
clearance.

For each proxy and their union, in each of the two point groups, retain the
minimum distance and exact nearest-pixel witness, nearest solid-proxy point,
interior status, 1st/10th/50th percentiles, and descriptive counts at distances
`1, 2, 5, 10, 20, 50 mm`. Report union contributions by nearest proxy with
deterministic calibration-order tie breaking. These levels are fixed before
results and cannot be selected or tuned into a gate. Point counts depend on
image sampling and are not independent observations or confidence measures.
Retain all per-pixel/per-proxy distance maps and masks.

## Verification, sealing and reporting

Before the first archived comparison, pass analytic tests covering box
face/edge/corner/interior distances, rotated and translated geometry, optical
depth and half-pixel centers, invalid depth, off-image/behind/camera-plane mask
behavior, and all-invalid input returning unknown. Preserve failures; do not
change geometric rules based on these two development results.

Seal sanitized input hashes and all numerical output hashes before opening
RGB witness overlays. Then inspect both complete RGB frames and fixed proxy
projection crops (32-pixel padding, clipped to the frame). Show mask outlines
and each proxy's nearest all-point and residual witnesses on RGB and depth.
Display depth normalization may use crop 2nd/98th percentiles only for plotting;
it must not modify any measurement. Describe apparent self-contamination as a
visual interpretation, not a simulator identity label. Do not read privileged
scene/contact audits to assign witness identity. Save findings separately from
the frozen instrumentation, with all input/output hashes and limitations.
The adapter rejects a dirty producer tree and records the SciPy version used
for convex hull construction. The worker requires exactly both opaque samples,
conventional optical-depth intrinsics and a proper rigid camera rotation.
