# Task2 point, TCP, and pad evidence review

The proposed fresh approach is a valid **experimental test of the fixed point cue and existing translation rule**, subject to its frozen initial-frame identity gate and external native-contact abort. A reduction in TCP-to-P distance would show that this controller can approach its reported coordinate in this fixture. It would not establish that the coordinate is a grasp center, that the bottle lies between the pads, or that the intervening motion is collision-free. No policy, trajectory, successful-prepose fit, or action correction is constructed here.

## What P supplies

The sealed Task2 result defines P from the **original integer BOX-center ray and crop-median depth**. The center pixel depth is 7.359087467 mm nearer than that median. Thus P is not even the direct depth measurement at the center pixel. G preserves all 492 valid crop samples; 414 have archived rendered-mask membership, and 54 fall outside its fixed one-pixel dilation. The reviewed sensor output intentionally does not use those evaluator labels to clean G. Neither representation certifies an observed bottle surface, object center, surface normal, opposing contact, or width.

For a nominal point approach, the minimum runtime quantities are the sealed world coordinate P, live TCP position in the same world frame, and the existing action mapping. A byte/dtype/shape match of fresh RGB/depth/K/T to the source supports reuse of this initial cue at that initial observation. It does not establish continued object stationarity, refresh the cue, or independently validate synthetic calibration. The immutable point's age and unverified stationarity remain explicit as time advances.

To interpret where the pads lie relative to a **separately qualified** surface sample, the minimum additional own-robot information is current TCP orientation, both signed finger joints, their common frame/time conventions, and the static TCP-to-pad transforms below. This permits the relation `p_TCP = R_world_TCP.T @ (p_world - t_world_TCP)` to be stated. It supplies no target surface identity, object extent, hidden-side geometry, contact, or swept-volume clearance. No such relation is numerically evaluated for a trajectory in this review.

## Static relationship, without a successful pose

The installed `panda_gripper.xml` has SHA-256 `d9d68123909d6910488310d0fae4e358ed4ac831c6d0957f3e30893a5412baac`. Its `eef/grip_site` sits at gripper-local z=97 mm (lines 20–21); both finger roots sit at z=52.4 mm with +90° local Z rotation (lines 28 and 38). Signed finger slides run on local +Y, with q1 in [0,40] mm and q2 in [−40,0] mm (lines 30 and 40). Tip translations and pad positions are explicit at lines 33–35 and 43–45. The two pad boxes have local half-sizes (8,4,8) mm; the fixed rotation makes their TCP-frame half-sizes (4,8,8) mm.

The already sealed compiled own-robot calibration `runs/autonomous-research/robot-geometry-observability-03/robot-calibration.json`, SHA-256 `11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa`, contains the same body/joint/site/pad parameters. Static attribute inspection passes for both pads; no robot state, simulator, FK, or projection is evaluated. In ideal TCP axes, with q1 and q2 measured in metres:

| Quantity | Static expression (m) |
| --- | --- |
| Pad 1 center | `(-q1 - 0.0035, 0, -0.0036)` |
| Pad 2 center | `(-q2 + 0.0035, 0, -0.0036)` |
| Facing surface of pad 1 along TCP X | `-q1 + 0.0005` |
| Facing surface of pad 2 along TCP X | `-q2 - 0.0005` |
| Geometric facing-pad gap | `q1 - q2 - 0.001` |
| Midpoint between facing surfaces | `(-(q1+q2)/2, 0, -0.0036)` |
| Either pad's TCP Y interval | `[−0.008, +0.008]` |
| Either pad's TCP Z interval | `[−0.0116, +0.0044]` |

The z offset is simply `0.0524 + 0.056 - 0.015 - 0.097 = -0.0036`. The 3.5 mm lateral offsets come from `8.5 - 5` mm. For symmetric joints, the gap midpoint lies on TCP X=Y=0 but 3.6 mm behind the TCP along its Z axis. The near-zero-joint formula can yield box overlap; it is a model-geometric expression, not a physical aperture guarantee. Existing `proprioception()` reports `abs(q1)+abs(q2)` as width, which exceeds this facing-pad gap by 1 mm in the normal signed joint range. The code explicitly labels that width as joint opening rather than pad geometry (`embodied_runtime/adapters/libero.py:62`).

Placing TCP at P would therefore place P at one coordinate within this own-gripper layout. It would not place the bottle's unknown cross-section, center, or opposing surfaces there. Even a correctly identified near-side surface point does not specify how far the object extends into the jaw gap or which pad should contact it. Choosing an offset from successful bottle poses would introduce information absent from P and this calibration; no such offset is derived here.

## Position and orientation are not the same observable frame

`LiberoWorldBackend.tcp_pos()` copies `robot0_eef_pos` (`embodied_runtime/adapters/libero.py:50`). Robosuite binds `eef_site_id` to `grip_site` (`robots/single_arm.py:215`) and emits `eef_pos` from that site's position (`:306`). Its `eef_quat` instead comes from the robot end-effector **body** quaternion (`:310`), with XYZW component order. The installed Panda robot's end-effector body is `right_hand`; the gripper is attached with fixed −90° local Z rotation (`panda_gripper.xml:14`), while `eef/grip_site` has identity orientation inside that gripper. Treating the observed position and quaternion as one unadjusted rigid pose would therefore misorient the pad geometry. Use the known body-to-site transform when interpreting these observables, or a consistent own-joint/static-chain pose. This is a frame-accounting requirement, not a new runtime policy.

## What the unchanged experiment can test

The current canonical rule minimizes the next nominal 10 mm TCP-to-point distance and uses its existing tuple tie-break; it selects STOP when no listed translation strictly improves that distance (`embodied_runtime/decision_interface.py:340`). Its effects explicitly assume a stationary target and omit contact/dynamics (`:206`). The admitted action family is six world translations plus STOP (`embodied_runtime/experiments/coarse_point_probe.py:65`). It cannot command jaw alignment or closure. STOP executes a native hold (`embodied_runtime/runtime_core.py:483`); it is not synonymous with zero additional integration.

The fresh test can falsify the sufficiency of this point cue and translation-only rule through native contact, tracking failure, exhaustion, or failure to improve the intended physical relation despite lower point distance. A completed nominal approach supports only the measured approach result. It leaves bilateral grasp semantics, jaw-fit margin, target surface ownership, occluded geometry, and holding unknown. The external contact abort is evaluator-based stop instrumentation and cannot be presented as a sensor-only contact detector, advance clearance proof, or substep-free motion guarantee. Its exact threshold, sampling stage and stop granularity must stay in the prospective protocol.

Local source inspected: `/home/junhongli/miniforge3/envs/locateanything/lib/python3.10/site-packages/robosuite/models/assets/grippers/panda_gripper.xml`, the corresponding `robots/single_arm.py` and `models/robots/manipulators/manipulator_model.py`, and the sealed calibration above. The review uses source and static scalar arithmetic only; no scene output, successful pre-grasp pose, or fitted target geometry enters the derivation.
