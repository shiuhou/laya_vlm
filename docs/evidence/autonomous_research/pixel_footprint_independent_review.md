# Prospective independent pixel-footprint review

**PASS** for producer freeze `9b725ed` before the two-frame offline comparison. The geometry module, strict input worker, coordinator and protocol were reviewed; 24 footprint/robot-FK tests independently pass. This approves the registered representation diagnostic, not a mask, pixel-ownership estimate or motion gate.

The GL-to-flipped-array mapping uses `(x+sx, y+1−sy)` in top-left pixel-edge coordinates. It uses the capture viewport, not framebuffer allocation, with the edge-coordinate principal point `(W/2,H/2)`. Unnormalized rays have optical z=1; perspective-correct reciprocal-depth interpolation returns the nearest positive own-triangle intersection. Two-sided candidate geometry, direct floating-point edges, rejected camera-plane crossings and unmodeled GPU culling/clipping/raster rules are explicit. A reviewed fix makes tied meshes preserve edge flags and expose ambiguous geometry identity while retaining a documented first-input index.

The worker accepts only static own-robot visual calibration, nine own-joint values, native resolved depth/K/T and frozen raster samples. It receives neither scene geometry/identity, cached poses, segmentation, contact/force, old masks/distances nor actions. Source hashes and schema checks precede serialization. The worker is a separate process whose output seals before the cached-pose/zero-image evaluator runs. The coordinator checks that the sealed output remains unchanged afterward. This is a code and serialization boundary, not an enforced filesystem sandbox.

Observed depth retains its dtype and bytes, including invalid values. Zero, partial and full modeled coverage remain potential gripper contributions; all leave observed ownership and unmodeled/occluded space unknown. Separate cached-pose comparisons cannot correct or replace the own-qpos output. No rendered depth is assigned to an MSAA sample and no resolve rule is inferred.

Tests cover coordinate flip and nonsquare calibration, optical-depth rays, perspective interpolation, nearest surfaces, pose transforms, mixed coverage, exact-edge/degenerate behavior, cross-mesh ties in both orders, invalid samples, camera-plane rejection, unknown space, bit-preservation, schema rejection and existing robot-only FK checks. The fixed old/new witness set is not expanded or tuned based on results.

| Reviewed file | SHA-256 |
| --- | --- |
| `embodied_runtime/pixel_footprint.py` | `5559a4ee170e50f45295252b3db2b08553b3ba0a2b886e8bbe6cdbc50b15da8c` |
| `embodied_runtime/experiments/pixel_footprint_measurement.py` | `0aa84b4fc649bce578d7eacb51302210aee4497b381a2c3c4a82504a40ec2a56` |
| `embodied_runtime/experiments/pixel_footprint_comparison.py` | `bbe3261d713988d5d2468e230761a88e661bfa0721f1376fdfb04d6e171bccc6` |
| `docs/research/pixel_sample_footprint_protocol.md` | `a7637b3edb8d72716fb21d343c69054b42c860b6e4a34920c9ed3c8c40a9eb3b` |
| `tests/test_pixel_footprint.py` | `7b8be26a2148fc923881dce5bdddcbd0f91d679e6affa007e2abd84a1cf79799` |

Any resulting comparison can describe potential sample support in these already-inspected development frames. It cannot establish actual per-sample scene ownership, physical camera calibration, object geometry, contact, clearance, hidden space or generalization to new poses.
