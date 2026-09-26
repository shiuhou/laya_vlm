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

## Failed schema attempt and static-topology amendment

Attempt 01 stopped before any coverage measurement because the older sealed visual calibration contains compiled vertices and local transforms but no triangle connectivity. The reviewer missed this concrete schema mismatch during the original prospective approval; synthetic geometry/API tests did not exercise the actual admitted calibration schema. The failed process/log/manifest remain evidence and are not relabeled as a completed comparison.

**PASS for the narrowly scoped static export at `9ec85ba`**, before compilation. The reviewed exporter parses the three named visual geoms and two hash-pinned STL assets into a tiny static `MjModel`. It creates no `MjData`, task scene, camera, joint state or renderer and calls no step/forward API. It must match every compiled vertex in order, geom-local position and quaternion exactly against the existing calibration before exporting bounded compiled triangle indices. No remapping search, hull or tolerance is admitted.

The reviewer performed an actual source-XML/calibration schema preflight without compilation: all three named geoms resolve uniquely, reference the two registered assets, and use standalone supported attributes without missing material/default references. Worker/coordinator changes admit a separate topology object while preserving the original FK calibration; real topology names and index bounds must pass before a worker starts. `TOPOLOGY_SHA256=None` deliberately blocks the next comparison until the export is sealed, independently inspected and pinned.

Reviewed exporter SHA-256: `619118cb78fb42c608a8ff27a1be61e034632614c079e146c7713b22acee5613`; amended worker: `453dfac702a0ae2867a4bfc8ebf8d3bf849962875d16141fecef09bb6946f62d`; coordinator: `e5f072d494d60bd88c2de8c8cc8ea8309010052ebcec388a6284f970541a659b`; protocol: `0a74ae8b9a9adea82a4af233ddec54485536a617f628c491a596dd4e2361c176`. Measurement rules and fixed pixels remain unchanged.

The stored static export passes independent artifact/hash/schema inspection: topology SHA-256 `12bedb9ef0604ba826f8e79a9a6e8d9bfabfe123211181a056ba608130c9fcc1`, audit SHA-256 `1cbbfb1f1ee66fb0388f941d79bc80b9d2b83d52a3f9b2d9a4693bec13f7bd79`, face counts 7,078 / 624 / 624, integer indices within the exact parent vertex counts, and all nine reviewed exact gates recorded as passed. The reviewer did not recompile a model; equality of the compiled vertices/local transforms is supported by the reviewed exporter and recorded gates. Freeze `0733ea7` pins that topology digest for the separately numbered comparison. This closes the missing-topology blocker without modifying sample geometry or observed depth.
