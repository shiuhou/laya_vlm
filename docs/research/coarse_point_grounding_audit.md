# Post-run single-ray POINT identity audit

This evaluator was specified after the coarse rule run completed. It is an
oracle-only interpretation of existing observations, not another experimental
condition or a policy repair. No inference, RGB modification, pixel correction,
control execution, crop, confidence score, or output salvage is permitted.

Verify the existing record chain and frame hashes. For each recorded capture,
reuse the raw POINT parser and token audit; preserve failed/missing calls as
unknown. Admit only the same single-point/EOS/depth condition. Restore its
recorded flattened simulator state in one fresh render-disabled World and call
forward solely to reconstruct geometry. Require exact restored flattened state
and capture time. No full controller restoration is claimed or needed for
geometric ray evaluation. This is not execution replay.

Reuse the existing designated top-handle visual-mesh binding and pixel-center
ray convention. Cast one MuJoCo first-surface ray through the containing pixel
center using recorded K/camera-to-world, static geometry enabled, body exclusion
-1, and the same 5 m cutoff. Reconstruct geom groups from MjvOption defaults plus
the environment's render_collision_mesh/render_visual_mesh flags, matching
robosuite initialization; record those flags and the relevant source hash. No
new image rendering is required. This reconstruction is explicit because the
original capture did not persist renderer vopt groups.

Record raw first-hit geom ID/name, body, mesh, ray origin/direction/range, world
surface point, optical depth, sampled sensor depth, signed/absolute optical-depth
residual, and exact designated-handle membership. Other named cabinet handle
visual meshes may be separately identified; all other geometry retains its raw
identity. Missing ray hits remain unknown rather than wrong-object claims.

Limitations: shared camera calibration is not independently validated; exact
pixel-center mesh membership differs from antialiased raster boundary coverage;
a correct single visible surface point is not a stable grasp point or proof of
safe approach. Preserve all source evidence; write a new evaluator artifact.
