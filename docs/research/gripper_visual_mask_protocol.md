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
