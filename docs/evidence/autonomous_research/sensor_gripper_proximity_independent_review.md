# Independent review of sensor / gripper proximity

The frozen diagnostic respects its input boundary and its stored results pass an
independent arithmetic audit. It computes observed-point proximity under assumed
calibration. It does **not** yet isolate scene clearance, an interaction
affordance, or an information-only cause of action failure.

Before execution, independent source/protocol review checked the sensor-only
worker, privileged archive adapter and synthetic tests. The producer added a
pinned extraction-map hash, clean-code requirement, exact two-sample schema,
SciPy version and conventional camera-matrix checks before freezing commit
`f20476d5e3402584c4ca5d722cdbd568107c1ed1`. These were provenance/schema checks;
no measured result motivated them.

The worker receives only sealed static robot calibration, nine own positions
per sample, depth, camera intrinsics and camera pose. It receives no RGB, contact
label, target point, scene model, action, outcome or full archive state. Both
already inspected development boundaries were selected in advance; this is not
held-out hazard detection. Camera/base accuracy and exact cache synchronization
remain assumptions. The subprocess is a reviewed code/input boundary, not a
filesystem sandbox.

The distance definition is explicit: nearest Euclidean distance to each solid
convex gripper proxy, with interior points assigned zero. The mask excludes the
projected union of these proxies regardless of observed depth. It can remove
scene points and leaves arm/wrist surfaces and visual/collision discrepancies
unresolved. Empty/invalid observations mean unknown, not infinite clearance.

The [independent checker](../../../embodied_runtime/experiments/sensor_gripper_proximity_evidence_audit.py)
verifies all 11 artifact hashes and both input/output seals; exact original
depth/calibration arrays and own-joint extraction; stored distance-map validity,
mask unions, all group counts/quantiles/threshold counts/proxy contributions; and
24 nearest-pixel witnesses, backprojections and point-pair distances. It **does
not recompute FK, hull distances or projected silhouettes**, and does not assign
surface identities. Its [result](sensor_gripper_proximity_independent_audit.json)
passes without simulator or estimator execution.

| Stored measurement | Before action 24 | Before action 25 |
| --- | ---: | ---: |
| Finite positive depth pixels | 147,456 | 147,456 |
| Pixels excluded by partial gripper silhouette | 6,169 | 6,265 |
| Residual points | 141,287 | 141,191 |
| All-point minimum for every proxy | 0 mm | 0 mm |
| Residual union minimum, both to hand proxy | 0.126722 mm | 0.109195 mm |
| Residual finger1-body minimum | 1.738041 mm | 0.162011 mm |
| Residual finger1-pad minimum | 9.379926 mm | 3.023203 mm |

The many zero all-point distances are compatible with the robot's visible
surfaces contaminating a raw proximity calculation. Masking changes the result,
but the remaining minima have **unknown surface identities**. A smaller
finger-proxy distance cannot by itself be called cabinet clearance, imminent
contact, or a validated actionable warning. The numerical input firewall is
stronger than the semantic interpretation currently supported by the output.

Raw directory: `runs/autonomous-research/sensor-gripper-proximity-01` under the
main checkout. `artifacts.json` SHA-256:
`56dcb32aca328d3a2e09af393d310f5abd44af3b62b206034e9f0830af86da49`.
Output-seal SHA-256:
`e3df898cff17974de37727c145e311571f84a3364a29b8b1114fd8e81e0ddb90`.
Numerical outputs were sealed before the producer inspected RGB witness
overlays. This independent note assigns no simulator-derived or visual witness
labels. It supplements the [information-boundary review](information_boundary_review.md)
without changing its motion-contract verdict or launching another experiment.

Reproduce the file/map audit into a new output:

```sh
python -m embodied_runtime.experiments.sensor_gripper_proximity_evidence_audit \
  --raw /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/sensor-gripper-proximity-01 \
  --output /tmp/sensor-gripper-proximity-independent-new.json
```
