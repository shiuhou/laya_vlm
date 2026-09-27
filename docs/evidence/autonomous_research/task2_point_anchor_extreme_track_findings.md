# Exploratory diagnosis of four fixed extreme trajectories

The four predetermined extreme cases show **switches between near and far
sampled surfaces at local image boundaries**, producing 210–242 mm final
point-displacement norms while native LK and depth validity remain admitted.
The close-cell examples move from background-colored sampled pixels toward a
visible finger; the open-hold examples switch across the dark bottle / light
background boundary. These are not authenticated trajectories of one material
point on the bottle. The original medians, all 492 seeds and all outliers remain
unchanged.

This is **post-outcome exploratory failure analysis**, not a replacement
estimator, classifier or new population. Root requested one maximum-final-norm
seed per cell after observing the full-range tails. The deterministic selection,
lowest-seed tie rule, complete trajectory, exact changes, largest consecutive
stored-point jump and five fixed RGB/depth contexts were committed before
selection at `e363d2517367c570e89fa0a12644f407208ae572`. The
[protocol](../../research/task2_point_anchor_extreme_track_diagnostic_protocol.md)
pins the complete source seal, four track files, journal and independent audit.
Three synthetic selection/change/padding tests passed. No LK, projection,
displacement estimator, mask, evaluator, FK, model, physics or render was run.

## Deterministic selections and observed jumps

All 492 final metrics were available in every cell; each maximum is unique.
Capture IDs below are the merged **zero-based** sensor sequence. A jump is the
Euclidean distance between two consecutive **already stored** world points.

| Cell | Seed / initial pixel | Final point norm (m) | Earliest largest full-trajectory jump | Jump distance (m) | Source phase |
| --- | --- | ---: | --- | ---: | --- |
| whole-close | 3 / [215,169] | 0.23911424759242372 | 38 → 39 | 0.23368953376111948 | End close → lift control 0 |
| whole-open_hold | 11 / [223,169] | 0.21025119213709395 | 28 → 29 | 0.21362132187394908 | Approach |
| neck-close | 3 / [215,169] | 0.24191386788810873 | 37 → 38 | 0.2365187228110031 | End close → lift control 0 |
| neck-open_hold | 17 / [217,170] | 0.2300962850736131 | 40 → 41 | 0.23083096824357757 | Lift control 2 → 3 |

The whole-open-hold trajectory's largest **post-preclose** jump is separately
retained: 39 → 40, `0.2067768735054103` m. Its larger full-trajectory jump occurs
before the preclose reference, so the two events must not be conflated.

| Cell | First sampled-pixel / depth change, full trajectory | First sampled-pixel change after preclose | First depth change after preclose |
| --- | --- | --- | --- |
| whole-close | 23 → 24 | 37 → 38 | 38 → 39 |
| whole-open_hold | 19 → 20 | 39 → 40 | 39 → 40 |
| neck-close | 37 → 38 | 37 → 38 | 37 → 38 |
| neck-open_hold | 38 → 39 | 38 → 39 | 38 → 39 |

The first exact floating native-XY change is 0 → 1 in all four cases, with no
sampled-pixel or depth change at that step. This exact inequality is recorded
without a threshold; it is not a declaration of physical target motion.

## RGB and depth evidence

All four five-context sheets were inspected at original resolution. Their 20
unmarked full-RGB tiles exactly match the original 384×384 arrays. All 20 saved
21×21 depth neighborhoods and their center samples exactly match the bound NPZ
depth arrays. Enlarged local RGB/depth panels use nearest-neighbor display only,
with one labeled depth color range per cell and no normalization applied to the
stored numbers. The orange square marks the saved sampled pixel.

**[Whole-close, seed 3](task2_point_anchor_extreme_track_whole-close.png):**
At preclose and postclose the center is on tan background beside the dark bottle.
After the largest jump, the local RGB center lies on the visible gray finger
region and the depth is much nearer. The sampled index changes `[216,173]` →
`[214,172]`, and depth changes `1.1881775856018066` → `0.9551792144775391` m.
The local foreground/background depth edge moves across the sample. This
supports a change of visible sampled surface, not 233.7 mm bottle translation.

**[Neck-close, seed 3](task2_point_anchor_extreme_track_neck-close.png):**
The analogous center starts on tan background and enters the gray finger region
at the first lift endpoint. The saved index changes `[215,169]` → `[214,168]`,
and depth changes `1.2016721963882446` → `0.9657567143440247` m. Both close extrema
were originally the same seed index/pixel, but their complete trajectories and
preclose references remain distinct.

**[Whole-open-hold, seed 11](task2_point_anchor_extreme_track_whole-open_hold.png):**
The sample sits at the dark bottle's right image edge. At the full-trajectory
jump, native X changes only `223.48065185546875` → `223.56028747558594`, crossing
the frozen nearest-index boundary at 223.5. The sampled index changes
`[223,173]` → `[224,173]`, and depth jumps `0.9754049777984619` →
`1.1881775856018066` m. Both native forward/backward statuses are 1 before and
after. At preclose capture 30 the sample returns to the near side,
`[223,175]`, depth `0.9789745807647705` m. During lift 39 → 40, X again crosses
223.5 (`223.4838104248047` → `223.5171661376953`), the sampled index changes
`[223,175]` → `[224,174]`, and depth changes `0.9789745807647705` →
`1.1848511695861816` m. This is a repeated near/far edge switch; a large image
tracking displacement is not needed to produce the large 3D tail.

**[Neck-open-hold, seed 17](task2_point_anchor_extreme_track_neck-open_hold.png):**
The marked pixel is near the dark bottle's left edge. Native Y changes
`168.8741912841797` → `168.46139526367188`, crossing the nearest-index boundary
at 168.5; the sample changes `[217,169]` → `[217,168]`. The saved depth changes
`0.9750217199325562` → `1.2050938606262207` m. The local depth neighborhood shows
the near/far boundary at the selected center even though the RGB border is
visually subtle. A gross migration of the track across the image is not needed
to explain this 230.8 mm stored-point jump.

All four selected trajectories stay `native_status_ok` after initialization.
The observations show a surface-switch failure mode that native/depth admission
does not flag. The frozen nearest-center rule is applied as specified; these
examples do not show a projection-arithmetic error. They do not fully separate RGB flow drift, moving
occlusion edges and nearest-pixel association effects at every frame. The
closed examples provide visible foreground finger evidence; the open examples
demonstrate sensitivity to a subpixel boundary crossing. No privileged ownership
label is introduced, and these four selected extremes do not estimate the
frequency of such switches or certify the remaining samples' identity.

## Complete retained evidence

The [portable diagnostic](task2_point_anchor_extreme_track_summary.json) contains
the deterministic selection receipts, all adjacent-pair records, exact first
changes, full/suffix largest jumps and source-linked display contexts. Raw
`task2-point-anchor-extreme-track-diagnostic-01` retains all four complete
47/46-row selected trajectories, all original native/source/own/depth/delta
fields, exact depth-neighborhood NPZs, protocol, clean code identity and a
separate visual-inspection receipt. No original seed is excluded or
reclassified, and no threshold is proposed from these outcomes.

| Artifact | SHA-256 |
| --- | --- |
| Diagnostic / tracked summary | `dda234acfd67cbbbc2b9a701d03de475101768490631f3dcad06ea8686c362c4` |
| Raw diagnostic artifacts | `19937143109dba6b6a98900fd3cbfc4b1f89280dd58e83e2d0d8919c61e16506` |
| Subsequent visual-inspection receipt | `83e8304bf9ba1337a355c551bf9c569bebe9b90d2e32be88ddf7a234be407503` |

The [complete population report](task2_point_anchor_retention_findings.md) remains
the descriptive result. This diagnostic explains why native success, valid
depth and a compact image cloud cannot by themselves establish bottle retention.
