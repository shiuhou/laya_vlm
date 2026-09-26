# Initial BOX temporal cue: source check and small proposed condition

**Proposal only; no tracking or outcome features computed.** Can the sealed
initial model BOX supply an uncorrected track population through the existing
approach, close/hold and lift sequence, without the former assistant-selected
landmarks? This tests descriptive correspondence/surface co-motion on one known
paired development trace. It is not an identity, holding or support classifier.

## Coverage established without tracking

`interaction-observability-paired-01` has 46 RGB-D captures per arm (`close`,
`open_hold`), IDs 0–45, from 0.5 to 7.3 s. All 92 NPZ files are present, match
their capture hashes and have the existing 384 × 384 RGB/depth plus 3 × 3
intrinsics and 4 × 4 camera transform schema. The initial frame and the 13
approach endpoints span 0.5–5.7 s in 0.4 s increments; no within-primitive RGB
exists for these approach steps. Close/hold and three lifts supply 32 subsequent
captures at 0.05 s. All 92 archived bottle-mask filenames exist; their contents
were not opened for this source check. Cached geometry/sample times remain
unknown. Coverage permits a complete sampled path, not continuous visibility.

| Source receipt | SHA-256 |
|---|---|
| `captures.json` | `e632b67471cf4b3b7bb924201a884d43339e677140a64522b4ef63f349fb2650` |
| `sensors.jsonl` | `59a38821e165393d607be1b3ec9100f093fcc52718282173fe8b28c556174bbe` |
| `endpoints.json` | `c28136d9e0e67b359491a3d270b0566e49a7f5939287363a18cdd8192ab7abe5` |
| `sensor-seal.json` | `77752c151c979e234607942a46674f25f3e6664eb66844e4411cff1def076013` |
| Initial close RGB-D | `3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969` |
| Sealed BOX sensor representation | `be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead` |

## One proposed sensor condition

Initialize exactly the existing 492 row-major `support_G.pixel_xy` coordinates
from `task2-box-support-run-02/sensor-representation.json`, once at capture 0
in each arm. These are all valid inner-crop pixels `[212,169,224,210)`, not a
bottle mask. Validate the paired initial sensor frames and common-prefix RGB
identity before admission. Do not use the old seed file, selected landmarks,
neck-query output, evaluator labels, target coordinates or successful grasp
poses to initialize or modify this population.

Reuse `point_temporal_probe.track_lk` unchanged, separately for each seed and
arm, over all 46 chronological RGB frames. OpenCV 4.11.0: window 21 × 21,
maxLevel 3, criteria count/epsilon 30/0.01, flags 0, minEigThreshold 0.0001.
Native forward and backward status plus finite coordinates determine survival;
no residual threshold is added. Native failure ends that seed permanently.
Preserve attempted coordinates/status/error/residual and every later unknown
row. No reseeding, batch substitution, ROI correction, feature selection,
smoothing, label cleanup, alternate setting or threshold fit is included.

Use the existing interaction analysis's depth admission and projection exactly:
only seeded/native-status-ok coordinates, floor to a containing pixel, bounds
check, finite depth in inclusive [0.01,5] m, then backproject that pixel center
at `(x+0.5,y+0.5)`. LK seeds use integer pixel indices; the projection half-pixel
is not added to the LK seeds. A depth failure leaves surface position unknown
but does not terminate an otherwise surviving RGB track. Depth resumption does
not restore a failed RGB track or certify its surface identity.

Match each capture to the already saved `tcp_fk_world_m` from the corresponding
control; capture 0 uses the initial endpoint packet. This reuses the original
own-TCP measurement without executing FK or mixing in target state. Keep read
times and unknown exact sampling times explicit. No force, contact labels,
controller state or object pose enters tracking or displacement computation.

Retain all 492 × 46 rows per arm, including failures. For every capture report
native-surviving and valid-surface counts with denominator 492. Retain per-seed
world displacement and TCP displacement from capture 0, their vertical
components and 3-D residual vector/norm. Also re-reference these same surviving
trajectories to fixed preclose capture 13 for the close/hold/lift comparison;
this is arithmetic, not reseeding. The capture-13 valid cohort and all later
missing rows remain explicit. Fixed descriptive summaries are count, median,
25th and 75th percentiles of vertical point displacement, point displacement
norm, vertical point-minus-TCP displacement and its 3-D norm. Empty subsets
return null. Do not replace missing rows with zero or infer a holding label.

## Falsifiers, evaluation and limits

The cheapest falsifier is prefix survival: inspect the first 0.4 s transition
and all 13 approach transitions before interpreting any lift co-motion. If no
seed survives to capture 13, the initialization chain fails before grasp.
Partial attrition remains a result, with no chosen survivor or minimum-count
success cutoff. Even a surviving population may track table/background or
switch surfaces; motion summaries alone do not qualify it.

Seal all sensor tracks and summaries before opening archived rendered bottle
membership masks. Then report per-capture proxy membership among admitted
sample pixels, unknown counts, and each seed's first observed proxy departure
while native tracking remains successful. These labels never change tracks,
summaries or admission. No new masks, segmentation, object-pose evaluator or
contact classification is needed. Rendered membership is not exact depth
ownership, full-patch identity, semantic confidence or neck correctness.

The former open-arm cap failure at step 14/control 5 remains separate adverse
evidence: native flow succeeded with 0.0011765 px forward/backward residual
while its sampled pixel left the bottle proxy. A dense median cannot erase it.
This changes initialization time, seed count/population and tracking horizon
relative to the three old assistant seeds; it is not an isolated initializer
ablation. Neighboring pixels have overlapping LK windows and highly dependent
motion/depth errors. The common prefix and two interventions are one paired
trajectory, not 984 independent trials; no statistical confidence or calibrated
success rate follows. Sparse approach cadence, later occlusion, unknown depth
ownership and survivor bias remain explicit.

Implementation must remain in this worktree, freeze a small offline adapter and
tests, validate actual capture/seed schemas without running LK, and obtain
review before tracking. This proposal authorizes no implementation or outcome
computation by itself. No model, physics, renderer, replay or runtime change is
needed. No alternate condition follows automatically from failure.
