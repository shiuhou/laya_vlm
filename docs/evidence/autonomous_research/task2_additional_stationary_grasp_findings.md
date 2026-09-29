# Additional closed-jaw interval: relation established before lift

Both fixed cells completed once and passed all six original atomic validations,
full recorded-control/native/primary-image replays and all 48 auxiliary-image
checks. Each fresh approach and first GRASP matched its sealed original cell
before the additional interval. No threshold, target, posture or action sequence
was tuned. Both registered predictions were satisfied.

| Anchor | Original one-GRASP lift endpoints; native BEFORE | After added interval, prelift bilateral | New lift endpoints; native BEFORE | Center lift (mm) | Bottom lift (mm) |
| --- | ---: | ---: | ---: | ---: | ---: |
| whole-close | 7/8; 172/200 | true | 8/8; 200/200 | 9.402737 | 9.387343 |
| neck-close | 8/8; 183/200 | true | 8/8; 200/200 | 9.362801 | 9.373160 |

Native AFTER counts equal BEFORE counts in every table entry. New rise is measured
from the final additional-GRASP endpoint. The original open-hold controls had zero
rise and zero bilateral endpoints, but lack the added interval; this close-only
experiment does not inherit the previous matched close/open witness.

At both first-GRASP endpoints, bilateral contact was absent and both jaws were
still moving at about 0.099 m/s per joint. First bilateral evidence in the added
interval appeared at whole control 1/native index 28 (BEFORE time 12.956 s) and
neck control 0/native index 17 (12.534 s). These are first recorded cache samples,
not exact continuous contact-onset times. The added interval had 172/200 whole
and 183/200 neck bilateral samples at each native stage; its final endpoint was
bilateral in both. The following lift had 200/200 at each stage and 8/8 endpoints.

| Anchor | Added interval arm translation norm (mm) | Arm rotation (deg) | Bottle center change [x,y,z] (mm) | Final signed joint separation (mm) |
| --- | ---: | ---: | ---: | ---: |
| whole-close | 0.203580 | 0.057893 | [+0.410415, -4.015751, +0.392665] | 12.096102 |
| neck-close | 0.070986 | 0.005976 | [-0.157376, -4.351412, +0.298618] | 14.958580 |

The separation is arithmetic qpos difference, not physical pad gap. At the end
of the added interval, joint velocities were approximately 3–4×10⁻⁵ m/s each;
this is measured proprioception, not a holding classifier. The summary retains
all 48 qpos/qvel/TCP packets, every close1/close2/lift endpoint, full arm deltas and
rotation changes, bottle center/bottom changes and raw/strong contact families.
Before-first-GRASP bottle labels were not separately sampled: its reported bottle
change uses control 0 to control 7, explicitly not a full primitive-start delta.
Added-interval and lift changes use their preceding primitive endpoints exactly.
Bottle rotation remains unknown without a recorded source-specific mapping.

Establishment was not clean. Whole's added interval included 12 raw non-pad finger
samples overlapping bilateral pads at each native stage; one per stage exceeded
0.05 N, with maximum 0.385890355 N. Neck had 10 raw zero-force finger overlaps per
stage. Table contacts persisted for 34 whole and 27 neck raw samples per stage
(32 and 27 above threshold). The subsequent lift had no raw non-pad robot/bottle
or bottle/table contact at any saved native sample. These observations do not
establish a clean continuous grasp or support-free retention. Raw families and
support histories remain in the summary; complete native force vectors remain
in the linked sealed journals.

The added action supplied eight more controls / 0.4 s of retained closure, with
measured arm drift and bottle rearrangement. It supports the distinction between
command completion and a subsequently established contact relation. It does not
isolate pure latency. After a retained CLOSED command, executed STOP-hold and
GRASP use the same nominal arm/jaw control under this executor; GRASP is not a
unique token winner. Approach STOP's non-execution remains a separate convention.
No fixed-two-GRASP policy is inferred.

The [whole RGB sheet](task2_additional_stationary_grasp_whole-close_rgb.png) and
[neck RGB sheet](task2_additional_stationary_grasp_neck-close_rgb.png) each contain 18 original frames:
before first GRASP, after first GRASP, every added-GRASP endpoint and every lift
endpoint. All 36 native-resolution RGB panels match sealed source arrays exactly.
The [source ledger](task2_additional_stationary_grasp_rgb_sources.json) binds each panel and the
[full measured summary](task2_additional_stationary_grasp_summary.json) preserves data and comparisons.
No new rendering, masks, model calls or physics were used for this report.

Physics ran from clean producer `945c96d81916f7952d9b40565c52b00085363544` using `laya-embodied`; main integration
`d29a805` and report commits were not the physics producer. Independent audit
`13a6741bbf430be8c47a99217fe32acbe7f9d7cb5ad3e671ebd689eb24e95ad3` binds both cells. Matrix journal
`40261179ca643c48cf81d76daa7521cb8e9ba61023859813e97661573605e8fa` completed normally. The subprocess, driver and
outer tool session returned 0; no retries occurred. The earlier four-cell
launcher's 143/0 discrepancy remains in that earlier report and is not present here.
