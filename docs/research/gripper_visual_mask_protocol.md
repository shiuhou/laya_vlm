# Calibrated gripper visual-mask control

This follow-up is motivated by the sealed partial-collision-mask witnesses at
the visible hand-housing edges. It is a development control on the same two
previously inspected captures, not held-out validation. Change only the mask
source. Reuse the exact sanitized optical-depth/camera/own-joint inputs and all
five per-pixel collision-proxy distance maps from
`sensor-gripper-proximity-01`. Preserve that result unchanged. No margin,
threshold, target region, policy, contact oracle or action filter is introduced.

## Static export freeze

The standard gripper XML declares three group-1 visual meshes: hand and two
fingers. Select only geometries on the registered gripper-root descendant
bodies with `geom_group == 1`, require `contype == conaffinity == 0` and mesh
type, and require exactly three geometries. Record compiled vertex/face counts
and the exported calibration hash before any recorded projection measurement.
Do not export arm links, scene surfaces, current object coordinates, contacts
or rendered labels. Reuse the known robot body/joint calibration and require
its five-collision-proxy export to match the prior sealed calibration exactly.

Use the previously audited static construction boundary: block `mj_step` and
`mj_step2` always, allow only counted constructor `mj_step1` calls whose full
time/qpos/qvel before and after are exactly equal, require constructor time
zero, and block every stepping function immediately after construction. No
rendering, explicit reset, state restore, physics continuation or controls.
Preserve constructor arrays in a separate privileged setup audit that never
enters the estimator. The construction config and simulator model are used
only for static robot-owned export, not recorded-state or scene evaluation.

## Measurement freeze

Use the same pure FK and the exact same projection convention as the prior
diagnostic: convex hull of projected calibrated vertices, pixel centers
`u+0.5,v+0.5`, no expansion. These are conservative convex enclosures of visual
mesh projections, **not exact rendered segmentation**. All-behind-camera
geometry masks nothing; camera-plane crossing excludes all pixels; off-image
projection masks no centers. Record behavior and counts. Replace the collision
mask with the union of the three visual projection masks; do not silently union
the old and new masks. Record newly excluded and newly admitted pixel counts.

The numerical subprocess receives only visual robot calibration, the unchanged
nine-value own-joint packets, the unchanged depth/K/T arrays, and the prior
collision distance/mask arrays. It receives no raw archive or simulator API,
RGB, target point, task geometry, body identity labels, force, contacts or
outcomes. Input and reference map files must be byte-identical to their prior
sealed copies. Recorded camera/base calibration is assumed, and own-joint
values remain simulator-state-derived encoder analogues. Cache/sensor timing
accuracy is not independently validated.

Select residual points from the **unchanged distance maps** using the new
visual mask. Retain the same per-proxy/union minima, pixel witnesses,
1st/10th/50th percentiles, fixed descriptive `1/2/5/10/20/50 mm` counts and
nearest-proxy contributions. Do not recompute the distance field or alter any
threshold. Record whether each old nearest witness is removed by the new mask.
Residual identities remain unknown; removed witnesses are geometrically
excluded by calibration, not given a simulator truth identity. Missing and
occluded surfaces are unknown, not free space.

Seal numerical outputs before RGB inspection. Then reuse fixed full-frame and
32-pixel-padded proxy crops and inspect all five new per-proxy nearest RGB/depth
witnesses in both captures. Interpret appearance separately from exact identity.
The question is whether visual exclusion removes the previously observed
housing-edge minima, and what residual support remains. A larger minimum does
not establish environment clearance, an adequate mask, contact prediction or
safe action admission.

## Pre-measurement calibration manifest

Append the compiled visual mesh counts, calibration hash and unchanged input
hashes after static export and before any recorded visual-mask calculation.

Static export `gripper-visual-calibration-01` from frozen exporter `ea89ca8`
completed before any visual-mask measurement. It selected exactly:

| Visual geometry | Compiled vertices | Compiled faces |
| --- | ---: | ---: |
| `gripper0_hand_visual` | 3,613 | 7,078 |
| `gripper0_finger1_visual` | 318 | 624 |
| `gripper0_finger2_visual` | 318 | 624 |

All three are opaque group-1 noncolliding meshes on the gripper subtree.
Calibration SHA-256:
`c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98`.
The complete prior body/site/collision calibration matched exactly. One
constructor `mj_step1` preserved time/qpos/qvel exactly; time remained zero;
no integration or rendering occurred.

Unchanged input files pinned in the mask-control adapter:

| Prior sealed file | SHA-256 |
| --- | --- |
| Own-joint/original calibration request | `02e9d19a3cdbee61eb4cf34601040a3110ff83a2946f141f674c7ec96e47663e` |
| Sample 0 depth/K/T NPZ | `67b0024f17052f3b8e6f95398d06873605872b295180c697ef504119091dcd8b` |
| Sample 1 depth/K/T NPZ | `98b7631887dafbcdf2e0d11481d03ef23cee1709f9de4c086281ecb957a2bd38` |
| Sample 0 collision-distance/mask NPZ | `23c2244e761473cc6e5de55d1c37f0d787635d14a87f6590b2ee231cbdeed0ac` |
| Sample 1 collision-distance/mask NPZ | `0b9e7e62802a9af9dfb86b2717efa7d9bb22e85e7b078e138b67582dcdf20f77` |

The worker selects witnesses from these existing maps and backprojects their
recorded depths. It does not recalculate point-to-proxy distances. Synthetic
checks require that mask selection preserve the provided distance array and
that complete exclusion produce unknown rather than infinite clearance.
