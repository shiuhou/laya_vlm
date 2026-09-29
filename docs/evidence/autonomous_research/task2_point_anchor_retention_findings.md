# Fixed four-cell temporal transfer: sensor findings

The one reviewed extraction completed all **1,968 trajectories / 91,512 rows**
from the fixed whole/neck × close/open-hold source. Both close cells have positive
final median sampled-point rise, while both open-hold medians are zero. Large
individual displacement tails remain despite every row passing native tracking
and sampled-depth gates. These descriptive measurements do not identify the
sampled surface or establish holding, contact, support clearance, task success
or anchor superiority.

Freeze `553c2fd4a8cec43c7e9be5ae2cfd74719f5aafaf` used the independently reviewed
source-only preflight and the pinned LocateAnything Python/OpenCV runtime.
There were no retries, repairs, new model/physics/render/FK calls or changed
seeds/helpers. All **32,964 shared-prefix row comparisons × nine native fields**
agree exactly. The independent stored-output audit at root commit `72f0d81`
passed all rows, 186 source frames, saved-depth projection, all 33,456
preclose-or-later reference deltas, summaries and prefixes without rerunning LK.
The maximum independently observed projection difference was
`2.220446049250313e-16` m; reference-delta difference was zero.

## Complete population and final distributions

Every one of the 186 capture summaries has 492 native-admitted tracks and 492
valid sampled depths; native failures and later unknowns are zero. All four
preclose reference surfaces and own-TCP packets are available. Before preclose,
all displacement metrics remain null with 492 missing values. At and after
preclose all 492 metric values are available. Native success and finite depth
do not establish correspondence identity or bottle ownership.

All values below are **mm from preclose**, including the close/hold interval.
Brackets are q25–q75, describing dependent dense samples rather than independent
trials or confidence intervals. Original full-precision values remain in the
[portable summary](task2_point_anchor_retention_summary.json), together with all
186 curves, per-capture minimum/maximum/count/missing values, raw checkpoints,
saved own TCP and reference deltas.

| Cell | Point Δz median [q25, q75] | Point norm median [q25, q75] | Point−TCP Δz median | Point−TCP norm median [q25, q75] | Saved TCP Δz |
| --- | ---: | ---: | ---: | ---: | ---: |
| whole-close | 8.281058 [6.120315, 11.230381] | 9.463666 [6.852048, 12.065508] | −1.539712 | 5.112751 [4.847445, 10.225246] | 9.820770 |
| whole-open_hold | 0 [0, 0] | 0 [0, 0] | −9.876932 | 9.899415 [9.899415, 9.899415] | 9.876932 |
| neck-close | 8.448493 [5.971457, 10.760542] | 11.109596 [7.713824, 11.917203] | −0.905060 | 5.159369 [5.041803, 9.224616] | 9.353553 |
| neck-open_hold | 0 [0, 0] | 0 [0, 0] | −9.406759 | 9.413874 [9.413874, 9.413874] | 9.406759 |

The all-seed final ranges are much wider than the middle half of samples:

| Cell | Point Δz minimum–maximum (mm) | Point norm minimum–maximum (mm) | Point−TCP norm minimum–maximum (mm) |
| --- | ---: | ---: | ---: |
| whole-close | −1.809987–149.419409 | 0.005078–239.114248 | 2.786407–232.656362 |
| whole-open_hold | −121.653033–7.963471 | 0–210.251192 | 2.058448–216.600878 |
| neck-close | −106.877978–149.296469 | 0.421611–241.913868 | 2.888242–236.449346 |
| neck-open_hold | −131.685068–8.003734 | 0–230.096285 | 1.622524–235.451034 |

No tail was discarded. A zero open-hold median or IQR does not mean every point
is stationary. Likewise, the close-cell medians do not make these per-seed
surface changes a rigid bottle motion estimate. Saved RGB correspondence and
nearest-depth association can remain numerically admitted while following a
different surface or depth discontinuity. This study has no masks, semantic
ownership check or holding classifier to resolve that ambiguity.

The [complete curves](task2_point_anchor_retention_curves.png) show all capture
counts and all 17 preclose-to-postlift summaries per cell. Each metric column
shares its vertical scale across the four cells. Dotted lines mark preclose;
dashed lines mark the end of close/hold. The neck-close point-norm median is
already 2.120405 mm after close, with point Δz median 0.006105 mm, whereas
whole-close has zero median point motion at that boundary. Therefore the final
values include different pre-lift changes; they are not isolated lift effects.

## All-position RGB inspection

The [saved-position overlays](task2_point_anchor_retention_positions.png) were
visually inspected at original resolution. Each of eight tiles draws every
saved native current XY from all 492 seeds on its unchanged original RGB array,
at preclose and postlift for each cell. The underlying RGB is neither cropped
nor resampled; only cyan raster points and separate titles are added. All
3,936 displayed seed records are preserved in raw
`report/all-current-seed-positions.json`; all are in-image and native-admitted.
Overlapping marks can occupy the same raster pixel.

The visible point clouds remain concentrated around the narrow dark
bottle-shaped region below the palm. At the final close frames the cloud and
visible dark outline sit higher; the open-hold clouds remain at roughly the
same image height as preclose while the hand rises. No broad migration of the
cloud across the table or palm is apparent in these eight views. The upper
cloud boundary is close to the fingers and obscured neck, and dense markers
hide some surface detail. This qualitative inspection cannot attribute every
seed to the bottle or distinguish small border/surface switches. The large
metric tails remain unresolved, rather than being dismissed because the cloud
looks compact. The earlier [unmarked RGB report](task2_point_anchor_grasp_rgb_findings.md)
retains the original visual context and its contact/holding limits.

## Artifact identity

Raw output is
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-point-anchor-retention-transfer-run-01`.

| Artifact | SHA-256 |
| --- | --- |
| Sensor seal | `39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60` |
| Closed extraction journal | `d58bd52625e01a89299cce9581c1d9684ee0467c6a0aaffbd043976147558f4c` |
| Extraction artifacts | `5a510ca3e4e9d0110b819f690a66c14feb6d051aafbe9d65b5f5e036bc34e5bc` |
| Portable summary / tracked summary | `a71121448b058026ba805ebab60d15474ca19a32ca6f2956fdbb4fc6279083ee` |
| Complete curves / tracked figure | `b4c6a49540df24328223f119567935187cb1751fe758879d5a4c83013d76d39f` |
| All-position RGB sheet / tracked figure | `3b167bd267c6952941eca9dce3b9ba1f4de000d77982d7df53131c92b1951a91` |
| All-position records | `fb6abdbad15c70375bc2995bfc5cf4943a72bfbdc014aedb0925c18429d37124` |
| Report artifacts | `1bfe14ad6ef797ee392f545e4cbfc0a811cd82bbc036aea4c8a4b6dd0882a87e` |

The report reads sealed stored values and eight saved RGB arrays only. It does
not rerun tracking, projection, displacement estimation, physics or rendering.
Independent mechanical evidence remains separate; no condition is selected as
a winner and no sensor threshold is fitted from these outcomes.
