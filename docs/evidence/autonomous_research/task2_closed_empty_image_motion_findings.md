# Post-event fixed-region motion: median contrast with failures and off-target tracks

The away cell does not reproduce the present cell's median image motion in
this matched pair. Final A displacement-norm medians are **4.19822365283334 px
present** and **0.05878343476007969 px away**. However, the away cell has only
365 available trajectories out of 492 by the final capture, and its retained
native-success outliers reach 178.86600529610445 px. The actual overlays show
coordinates scattered onto the robot and background while the relocated bottle
remains visibly elsewhere. A fixed region's native tracking status and motion
cannot establish that it represents the bottle.

The one authorized extraction at clean freeze
`9891aa5ced02cf7b9924f582c221faeb8f400fa8` completed **984 trajectories /
24,600 rows**, with zero retries. It used the same 492 numerical seed locations
freshly initialized in each post-event RGB image, all 25 suffix captures, the
unchanged LK function/settings and the frozen A/B definitions. No through-event
tracking, reseeding, mask, measured scene depth, favorable cohort or threshold
was added. The [protocol](../../research/task2_closed_empty_image_motion_assay.md)
and [prepared report](../../research/task2_closed_empty_image_motion_report_preparation.md)
define the comparison.

The [independent numerical audit](task2_closed_empty_image_motion_independent_audit.json)
passed all 984 trajectories, 24,600 rows, 50 summaries and 50 saved-own-TCP
projection checks without rerunning LK. A and B each have 21,725 available
values across the complete two-cell output. Present remains 492/492 throughout;
away has 94 native failures on the first control and 127 failures cumulatively
by the final capture. Every failure and subsequent unknown row remains stored.

## Fixed endpoints and complete population

All displacement values use local capture 0, **post-event/preclose**, as the
sole reference. Final displacement therefore includes both closes and the lift.
A uses native RGB coordinates; B subtracts projected saved own-TCP displacement
and therefore adds proprioception and calibration. Positive v means image-down.
All 492 capture-0 entries are initialized zero references, not attachment evidence.

| Cell / endpoint | Available A and B / 492 | Missing | A norm median (px) | B norm median (px) |
| --- | ---: | ---: | ---: | ---: |
| present / close 1, capture 8 | 492 | 0 | 0.549632215237538 | 0.641811372773174 |
| away / close 1, capture 8 | 370 | 122 | 0.0373306842068945 | 0.11184414416338445 |
| present / close 2, capture 16 | 492 | 0 | 2.168239835614667 | 2.2947791367812105 |
| away / close 2, capture 16 | 368 | 124 | 0.04670857403388656 | 0.11863097194545416 |
| present / postlift, capture 24 | 492 | 0 | 4.19822365283334 | 2.420117861871131 |
| away / postlift, capture 24 | 365 | 127 | 0.05878343476007969 | 3.7282189656252247 |

Final available-value distributions retain the full range:

| Cell / metric | Median | q25–q75 | Minimum–maximum |
| --- | ---: | --- | --- |
| present / A norm | 4.19822365283334 | 3.304782046419546–4.5464352448867436 | 0.3444956318020969–8.397962201275503 |
| away / A norm | 0.05878343476007969 | 0.010365705455327487–5.375674566787182 | 0.00011003269273266568–178.86600529610445 |
| present / B norm | 2.420117861871131 | 2.1255311079868386–2.619941794422486 | 1.4081154887486769–4.742477622830279 |
| away / B norm | 3.7282189656252247 | 3.7032597501169273–4.344993133558821 | 1.030273910903196–175.2844473083217 |

Final median A image-down displacement is `-3.609222412109375` px present and
`0.004425048828125` px away. Median B image-down residual is
`0.06887846220374172` px present and `3.6937120320254166` px away. The away
residual distribution is broad: its q25 image-down residual is
`0.14599779862697915` px, while its norm minimum is `1.030273910903196` px.
No value or subgroup is selected as a holding threshold or identity label.

The [full curves](task2_closed_empty_image_motion_curves.png) show all 25
captures, denominator 492, native status, A/B availability and missingness,
and all four metric distributions on shared scales. Large away outliers remain
in the gray full-range bands; they compress the central curves visually rather
than being hidden. Quantiles summarize available values with missing counts
alongside them; they are not confidence intervals or 492 independent trials.
The complete full-precision summaries remain in the
[sealed source JSON](/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-closed-empty-image-motion-run-01/sensor-summary.json).

## Actual RGB inspection

Both [present](task2_closed_empty_image_motion_present_rgb.png) and
[away](task2_closed_empty_image_motion_away_rgb.png) sheets were viewed at their
original resolution, including all eight uncropped RGB panels and all eight
position overlays. The separate
[visual receipt](task2_closed_empty_image_motion_visual_inspection.json)
records the inspected files and exact source RGB bindings. The report's original
index retains its generation-time pending-inspection field; this subsequent
receipt records the completed viewing.

In the present panels the bottle is visible below the gripper, and the fixed
seed region overlaps that local bottle/background area. In away, the bottle is
visible much lower in the image, outside the fixed region; the closing gripper
has no bottle beneath it in that region. Away's later admitted point positions
include the robot and other background locations, as well as positions near the
initial region. This is visible evidence that the fixed pixel population does
not supply current semantic ownership. No per-pixel material labels are inferred
from these overlays.

The available medians describe a local present/away difference. The unequal
availability, broad overlapping ranges and off-target coordinates prevent that
description from establishing a reliable target-motion or holding estimator.
The experiment does not track the relocated bottle elsewhere. B also remains
a projected point/TCP residual, not a calibrated rigid-attachment or slip error;
the source's exact observation/sample times remain unknown. Mechanical and
qvel qualification are separate from this sensor-only report.

## Source qualification and identity

The original physical matrix remains **`interrupted_incomplete`**. The source
was instead qualified as **`observational-source-qualified`** using the two
original sealed collections, the original exact present replay, and a separately
authorized second away verification. The binding retains the first interrupted
away intent with unknown executed counts and the separate successful second
attempt. Neither this extraction nor its successful termination retroactively
completes the original matrix. No collection was repeated for this report.

Raw extraction/report output is
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-closed-empty-image-motion-run-01`.

| Artifact | SHA-256 |
| --- | --- |
| Composite source binding | `49dbc6e182a6e516e43142537005234c7559264fd69c9f051a10e1b7b4f4d04f` |
| Source-only preflight | `a2c641097eead7c51a8b992461b593abe10ca4cb8bcc07bc169ed7b8c531f8a8` |
| One-batch independent release | `7cf3c5fe4ad415fad2a786fa0ff81269362a4e5c75db3ca3f7d5b779d25e867a` |
| Extraction sensor seal | `669d99542346b7b7f7f9d76090b16ebf84c9575f0365498a55f91d84496d57ac` |
| Closed extraction journal | `4a864d843fd2ea596044d8667205a7212348d3a00edaaf56a1bd75d75498ba4a` |
| Full stored summary | `549f9872fb99bc48e931d3f1d983ca65f33bd2de2449c792623f99edaf950844` |
| Independent output audit | `b195a27d6818e5e5688116ace4fc805d70c5af976ddd676d5d08172c640adc61` |
| Report artifacts | `7cda70fde851419f535ea5a7b1885b909a3912d97a7fcd1d4c04f08f9cd614bf` |
| Full curves / tracked copy | `2097b364cee6bdc5f39ff46ac107721abd1ed3b63ad53185fce8fd281bd1d88a` |
| Present RGB / tracked copy | `02ef81b513a0280a3f375d497d13bd00714997fc712e1017029d97df82ffb162` |
| Away RGB / tracked copy | `bd67db44287237acb94cb2d45b81bab12af4f6d5f3e26c002f7fdd486505d15f` |
| Visual inspection / tracked copy | `74e51f65cac15776fa9d146b417adbc15e6543845a491a1379739c25fd03c2ac` |
