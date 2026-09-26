# Calibrated sample footprint: representation and fixed offline comparison

Status: prospective specification; the pre24/pre25 comparison has not run.

## Measurement and boundary

Represent each observed native depth pixel as its unchanged resolved optical-depth scalar together with the calibrated sample rays and the potential contribution of known own-gripper triangles at those rays. The scalar is never assigned to a particular sample, averaged across rays, converted to a new center-ray point, or replaced by a predicted robot depth. Observed ownership and unmodeled/occluded space remain unknown for every coverage count.

The reusable geometry module accepts optical-camera K/T, image dimensions, sample offsets, and own-gripper triangle meshes. The sensor worker receives only sealed static own-robot calibration, nine own-joint values, native depth/K/T, and frozen raster sample metadata. It has no scene model, object pose/identity, cached simulator geometry, contact/force input, segmentation, reference distance map, environment, action API or renderer. The archived joint values are simulator-state-derived own-joint encoder analogues, not physical encoder data. The visual calibration contains three gripper meshes; omitted arm/self geometry is not treated as absent.

Inputs to the fixed comparison are sealed, already-inspected development data. This is a representation diagnostic, not held-out validation or a safety/clearance measurement.

## Coordinate and geometric definition

The adapter flips a 384 × 384 capture vertically. The actual capture viewport governs that flip, not the allocated 640 × 480 offscreen buffer. For flipped array pixel index `(x,y)` and OpenGL bottom-left sample offset `(sx,sy)`, the top-left pixel-edge coordinates are `(x+sx, y+1−sy)`. The center location is `(x+.5,y+.5)`. The camera utility uses focal length `.5*H/tan(fovy/2)` and principal point `(W/2,H/2)`, matching this edge convention for the symmetric viewport. Optical camera axes are x right, y down, z forward. The historical adapter's reversed positional height/width arguments have no numerical effect on these square captures; the new interface explicitly takes `(height,width)` and has a nonsquare analytic test.

Native sample order is frozen from the exact rendering reproduction: `(0.375,0.125)`, `(0.875,0.375)`, `(0.125,0.625)`, `(0.625,0.875)`. This metadata is passed as camera-pipeline calibration; no position is fitted to a witness. The center condition uses only `(0.5,0.5)` as a geometric reference, without claiming a calibrated depth-resolve rule for either framebuffer.

For each sample, use `K^-1 [u,v,1]` as an unnormalized optical ray with z=1. Project each calibrated triangle and use perspective-correct barycentric interpolation to compute its positive ray-intersection depth. Keep the nearest own-triangle depth across the three meshes, with its own-geometry index. Test triangle interiors using direct floating-point inequalities without a fitted margin or dilation. Include exact geometric edges and flag them separately; skip zero-area projected triangles and report their count. Reject any modeled vertex at or behind the camera plane because clipping has not been calibrated. Winding is ignored: these are two-sided geometric candidates. GPU culling, subpixel quantization, edge inclusion and near/far clipping are not emulated or asserted equivalent.

Save the native depth array without changing its dtype or bytes, sample rays, per-sample potential coverage/depth, nearest own-geometry index, exact-edge flags, and the number of covered samples per pixel. Exact depth ties across own meshes keep the first input index, explicitly flag geometry ambiguity, and OR edge flags; tied geometry labels must not be read as uniquely assigned. NaN in predicted depth means no intersection with these modeled triangles, not observed free space. Zero/partial/all sample coverage means zero/partial/all *potential gripper contribution*, not scene/mixture/robot ownership. Native resolved depth can reflect scene occlusion or unspecified resolve semantics, so even all-sample support cannot certify actual ownership.

## Fixed inputs and outputs

Before the comparison, freeze the code/protocol commit, analytic tests, input hashes and independent review. Stop on any input hash/schema mismatch; do not modify calibration, sample offsets, pixel selection or numerical rules in response to results.

The pinned source artifact-manifest SHA256 values are `4e0109bdf477cb579086b2a0fbe0f1cfea69fa7ccca89f1bfa47b93c478bdff5` for `gripper-visual-mask-control-01` and `e8852ee0a9162cd46acc3ea78ecfff6d7b6eccc10d3510ca62447cfaf570050c` for `render-measurement-diagnosis-01`. Verify every listed artifact plus the rendering output seal before input admission. The coordinator records input hashes and launches the restricted worker in a separate process, seals its outputs, then performs the cached-pose/zero-image evaluator comparison. It rejects an uncommitted working tree and never retries a failure under changed settings.

Read only these existing sealed sources under `runs/autonomous-research`:

- `gripper-visual-calibration-01/gripper-visual-calibration.json`, SHA256 `c86706370d8442f85365d1e1d7e962ffb0f2346c235d968146694ed6e3fb4c98`.
- Sanitized native `depth_m`, `intrinsics`, `camera_to_world` and nine-joint packets from `gripper-visual-mask-control-01/estimator-input`. Admit neither its old masks/distance arrays nor its distance-proxy names to the worker. Verify against the source manifest and calibration.
- Frozen raster metadata and native/zero captures from `render-measurement-diagnosis-01`, whose output seal/artifact manifest must pass. The worker receives only the native arrays and allowed sample positions. Zero captures and cached-pose values stay in the separate evaluator after worker output is sealed.

Evaluate both complete 384 × 384 native frames, using own-qpos FK and the same three visual triangle meshes. Save four-sample and center-only geometric predictions. Report full-image counts of 0/1/2/3/4 native covered samples and all center-versus-sample coverage combinations, with no pixel removal, new mask, distance recomputation, residual minimum, tolerance threshold, or action decision. Report all eleven already-registered centers and all 99 fixed 3 × 3 neighborhood entries from the render diagnosis, without best-neighbor selection or adding centers based on this result. Retain full arrays so any aggregate can be audited.

After sealing those sensor-side outputs, a separate read-only evaluator may compare the saved native versus zero resolved scalar changes against the fixed coverage categories. Report their distributions and every registered witness; do not choose a depth-change threshold or claim these comparisons identify actual ownership. A large native-to-zero difference at a mixed-potential sample footprint is compatible with subpixel ownership effects, but it is not a proof of the GPU resolve mechanism.

The same separate evaluator may transform the static visual vertices using the already-sealed cached gripper poses, compute geometric sample coverage numerically, and report cached-versus-own-qpos coverage disagreements and common-hit predicted depth differences. Cached poses must never enter the sensor worker or replace its own-qpos predictions. No simulator import, state mutation, forward refresh, rendering, dynamics or continuation is permitted anywhere in this offline comparison.

## Verification and interpretation

Analytic tests precede all sealed-frame measurement and independently check GL vertical flip, nonsquare viewport/principal point, optical rather than unit-ray depth, mixed coverage, sloped-plane perspective depth, nearest surfaces, pose transform, exact-edge/degenerate behavior, malformed sample metadata and camera-plane rejection. Tests also require bit-preservation of resolved native depth, including invalid scalar values, with ownership/space remaining unknown.

A successful offline result establishes that the sensor-side representation can carry the known raster sample footprint and potential own-gripper contributions without conflating an unspecified resolved scalar with a center-ray point. It can reveal whether the registered pixels have mixed geometric sample coverage and whether cached-versus-own-qpos poses change those same coverage decisions. It cannot establish actual per-sample scene ownership, physical sensor calibration, target identity, full-body clearance, contact, hidden free space, or a safe motion. Small cached-versus-FK vertex error does not excuse any observed coverage disagreement.

Any future claim that predicted samples match actual GPU ownership needs independently known geometry and prospectively fixed new poses/edge cases, including culling/clipping/edge semantics and resolve calibration. No uncertainty margin may be fitted to these two development frames. No automatic mask, sensor pipeline, estimator, policy or action gate integration is authorized by this protocol.
