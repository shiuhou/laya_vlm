# First-contact observability: nearby surface support, uncertain exact contact face

2026-09-27. The recorded pre-action RGB-D contains **nearby cabinet surface support
at the retrospectively queried first-contact edge region**. Finger occlusion
grows in the surrounding pixels. The evidence does not establish the exact
first-touch material point or face normal, complete local free space, or a useful
contact-free next action. An initial visual impression of a hidden contact
surface should therefore remain qualified: nearby support is measurable, while
precise contact interpretation is unresolved.

This is an evaluator-only analysis of the completed `coarse-initial-point-02`
trace. It ran no vision/language model, controller or task primitive. Instantiating
the exact simulator model required its standard reset and ten settling controls;
all physical action APIs were then disabled, and only archived state restoration,
forward kinematics, rendering and geometric queries were used. No evaluator query
or label entered a sensor estimator, candidate gate or policy.

The bounded [procedure](../../research/first_contact_observability_protocol.md)
was registered as `2de5c5c`, with the explicit original-versus-restored render
check added at `dea4f97`, before numerical visibility results. Analytic code and
three geometry-convention tests were frozen at `ff061ca030d098573b3b85c422ed814e0e96147e`
before the sole evaluator run. A separate read-only report exporter at `d450921`
verified raw sensor projections and produced a clearer figure without another
simulator/model call. Original raw images and evaluator artifacts remain intact.

## What is visible in the stored evidence

The primary observation is capture 26, immediately before primitive 25 at
simulator time 10.5 s; capture 25 before primitive 24 is the fixed temporal
reference. The first recorded above-threshold contact occurs after control 0
of primitive 25. Its recorded world point and contacting geometries are oracle
information used only to define the retrospective audit region. Contact force
and designated-handle classification are owned by the separate execution audit;
they are not used to infer visibility here.

The motion-corrected collision-box surface representative projects to
**(147.735686, 166.379530)** in both pre-action images. Its containing pixel is
**(147, 166)**, sampled at pixel center **(147.5, 166.5)**. Recorded optical depth
there is **831.020951 mm**, versus query optical depth **833.794103 mm**.
Backprojection places that raw sensor sample **2.802070 mm** from the oracle
representative. The nearest sample in the fixed 5×5 neighborhood is at
**(147, 165)**, **1.655333 mm** away; enlarging to 11×11 does not improve it.
These are distances to an oracle query, not a sensor-inferred collision warning.

Both the exact continuous query ray and the containing-pixel-center ray intersect
`wooden_cabinet_1_g10`, the visual mesh on `wooden_cabinet_1_cabinet_top`.
They do not first hit robot geometry. The fixed neighborhoods show increasing
robot coverage in the restored evaluator visual geometry:

| Fixed neighborhood | Before action 24: scene / robot rays | Before action 25: scene / robot rays | Nearest recorded point to query |
| --- | --- | --- | --- |
| 1×1 containing pixel | 1 / 0 | 1 / 0 | 2.802070 mm |
| 5×5 | 25 / 0 | 19 / 6 | 1.655333 mm |
| 11×11 | 107 / 14 | 91 / 30 | 1.655333 mm |

All scene rays in those windows hit the cabinet-top visual mesh; robot rays hit
`gripper0_finger1_visual`. Robot identity comes from body ancestry under the
instantiated robot model's `robot0_base`, not an RGB segmentation model. These
counts describe evaluator ray intersections, not exact semantic masks for
anti-aliased raster pixels. The raw RGB crops show the finger approaching the
front/top edge beside the handle; the queried neighboring cabinet region is
still exposed.

Review the [recorded RGB views with clearly labeled oracle overlay](../../../runs/autonomous-research/first-contact-observability-01/recorded-rgb-oracle-query.png)
and [raw depth plus evaluator ray categories](../../../runs/autonomous-research/first-contact-observability-report-01/depth-and-occlusion.png).
The after-control 0 and 7 panels are recorded RGB only. **No post-contact depth
was captured**, so this audit supplies no measured depth trajectory after contact.

## Motion, contact timing and face ambiguity

The recorded contact midpoint is
`(-0.019031453, -0.079670208, 1.122348946)` m. The contacted collision box moves
**0.047614899 mm** in world −Y between the recorded pre-action and first-contact
endpoints. The evaluator converts the midpoint into the post-endpoint box frame,
then carries it through the pre-action box pose. Its nearest box-surface
representative becomes
`(-0.019031453, -0.079622593, 1.122360000)` m before the action. The uncorrected
post-contact coordinate was retained separately as a sensitivity check and was
never labeled unchanged pre-contact truth. Motion correction shifts the midpoint
projection horizontally by approximately **0.02647 pixel**.

That construction is a rigid-correspondence estimate. It cannot recover an
unstored first-touch integration substep or guarantee that a contact-manifold
midpoint is a material surface point. Concrete timing and geometry discrepancies
remain:

- The same-pair contact midpoint recomputed by fresh FK at the recorded final
  state differs from the archived midpoint by **0.023991808 mm**.
- The archived midpoint lies **0.011054470 mm** from the nearest box surface at
  that post-endpoint pose.
- Its distances to the local +Y and +X box faces are **0.011054470** and
  **0.012701937 mm**. Nearest-face selection differs by only **0.001647467 mm**,
  less than the observed recorded-versus-fresh-FK midpoint discrepancy.

The point is therefore near a box edge where this method cannot reliably assign
an exact contacted face or normal. The primary query uses the prospectively
specified nearest-surface construction, with this ambiguity retained. It is not
a certificate that the robot contacted that precise visible surface sample.

Collision and visual geometry also differ. The collision query concerns box
`wooden_cabinet_1_g11`, while the visual rays hit mesh `wooden_cabinet_1_g10`.
The continuous ray's visual intersection has optical depth **834.907153 mm**,
about **1.113051 mm** behind the box-surface representative. The pixel-center
ray instead intersects at **831.908497 mm**. Its residual to recorded depth is
**−0.887545 mm**. Continuous projection, pixel-center sampling, collision/visual
geometry and contact-state timing are distinct discrepancies; none was absorbed
into an invented confidence or a tuned visibility threshold.

## Fresh geometry was checked against the actual recorded renders

Restored flattened simulator states match their archived values exactly. Camera
intrinsics and the corrected camera-to-world transform agree within 1e−12.
The source adapter's vertical RGB/depth correction and robosuite's
`diag(1,−1,−1)` camera-axis correction are retained. Depth is camera +Z optical
depth, not Euclidean ray range; all backprojections use containing pixel centers.

Fresh-FK renders are **not globally identical** to the archived images. The
check was performed before interpreting ray labels:

| Render comparison | Before action 24 | Before action 25 |
| --- | --- | --- |
| Different RGB pixels / 147,456 | 400 | 482 |
| Mean absolute RGB channel difference | 0.011070 | 0.008705 |
| Mean absolute depth difference | 0.014055 mm | 0.004015 mm |
| Maximum absolute depth difference anywhere | 1,357.548594 mm | 1.657367 mm |
| Maximum absolute depth difference in 5×5 | 0 mm | 0.034571 mm |
| Maximum absolute depth difference in 11×11 | 0.003517 mm | 0.034571 mm |

The large isolated global depth difference before action 24 is retained rather
than hidden by the mean; global equivalence is not claimed. At both the query's
containing pixel and the nearest-support pixel, **recorded and restored RGB and
depth match exactly** for both observations. That supports the local comparison
without treating fresh FK as identical to the original cached derived geometry
everywhere. This audit does not assign each global difference uniquely to cached
geometry, rasterization or GPU differences.

Ray-versus-recorded-depth discrepancies are larger at some neighborhood edges:
up to **35.117814 mm** in the primary 5×5 and **98.948763 mm** in its 11×11.
This is another reason not to interpret evaluator ray counts as exact per-pixel
semantic ground truth. The raw measurements preserve every registered pixel,
including disagreements. No favorable-pixel search, new neighborhood size,
visibility threshold or label correction was run after seeing these values.

## What the single point leaves out

The original admitted point projects to (158.5, 185.5) and is **39.526110 mm**
from the retrospectively carried contact-region query. Its scalar world location
does not encode the neighboring panel's extent or normal, the gripper's occupied
shape, clearance between those surfaces, or which visible surfaces will become
occluded as the robot moves. Later RGB-D captures existed for audit but were not
consumed by the initial-point controller. The present evidence shows that some
nearby depth support was available; it does not establish that a full surface,
free-space or interaction-affordance representation could be recovered reliably.

Visibility alone also does not establish that the existing action family contains
a useful contact-free continuation, or that a controller would select one. That
is a separate candidate-coverage question. No collision filter, hidden oracle
gate, new segmentation model, policy modification or manipulation-success claim
is justified by this audit. An independently checked sensor-relative geometry
measurement may be warranted only with those remaining uncertainties explicit.

## Raw evidence and reproducibility

Raw evaluator root:
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/first-contact-observability-01`.

- Source episode SHA-256:
  `e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf`.
- Evaluator episode SHA-256:
  `ab277877b7eed50bf900bbf202f981af359e8ab18df90929003b4b7c576a8589`.
- Raw recorded-depth pointcloud artifact:
  `recorded-depth-pointclouds.npz`, SHA-256
  `ddf62e98d6cfe8e61e3092327aed3928515e7d1a5d894cadc1c117f2e0707c23`.
- Restored evaluator renders, source artifact/calibration identities, individual
  rays, all neighborhood backprojections, contact poses and failures/termination
  checks are retained in the append-only log and hash manifest.

The [portable summary](first_contact_observability_summary.json) includes all
raw-derived measurements, recorded identities, artifact hashes and limitations.
The read-only report independently reconstructs **294 pixel samples**, including
fixed-window overlap, from original depth/calibration without importing the
analytic experiment helpers. Maximum 3-D reconstruction difference is
**4.44e−16 m**; query projections, distances and category-count arithmetic also
match. This checks projection arithmetic, not independent ray intersections.
All three focused projection/rigid-correspondence/box-surface tests pass, and
`git diff --check` passes. There were no failures in the evaluator record chain.

To rebuild the summary and review figure without loading a simulator or model,
use a fresh figure directory:

```
python -m embodied_runtime.experiments.first_contact_observability_report --raw /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/first-contact-observability-01 --figures /tmp/first-contact-review-new --summary /tmp/first-contact-summary.json
```

This closes the registered visibility audit. Exact contact face/material identity,
full scene support and useful action coverage remain separate questions; no
further physical experiment was performed by this audit.
