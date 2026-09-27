# Exploratory extreme-track diagnostic freeze

This is explicitly post-outcome exploratory failure analysis prompted by
200+ mm tails in the completed fixed four-cell temporal transfer. It neither
changes that estimator nor establishes a new success/holding classifier. No
result, seed or condition is excluded from the original report.

Source is raw `task2-point-anchor-retention-transfer-run-01`. Pin sensor seal
`39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60`, closed journal
`d58bd52625e01a89299cce9581c1d9684ee0467c6a0aaffbd043976147558f4c`, and independent
stored-output audit `e188710d477c16ce0bd09d61004293015fe15633c12995abdd9252e9dba21b86`.
The four track hashes are:

| Cell | Track JSONL SHA-256 |
| --- | --- |
| whole-close | `f37c9bd9688175980f0037612b6a5523587b4b207e0f8dd35ded54da032b7010` |
| whole-open_hold | `381847c255d67c65fa34675d14d2e4d82afa1c622dc0ab90296b286900dcd4c5` |
| neck-close | `78e5b4d04697e65cca776266040de2543a3f71cce487822ec189efceb948f8c7` |
| neck-open_hold | `604c025e814aeb7b51a657746863a7a3d3d06d7bc25317fb774e392a806db1a0` |

Before reading outcomes for this diagnostic, commit this protocol and its small
implementation/tests. Then record clean code/protocol/source identities in the
new raw `task2-point-anchor-extreme-track-diagnostic-01` directory. Retain any
partial output rather than overwrite/retry it. Root has authorized this fixed
diagnostic; no additional permission gate is added.

For each of the four cells in original order, select the seed with maximum
**stored final `reference_deltas.preclose.point_delta_norm_m`** over all 492
seeds; exact equal values break ties by lowest seed ID. Preserve the count/IDs
of unavailable final metrics and all tied maxima in the receipt. No residual,
motion, depth or identity threshold is introduced. Do not select by mechanical
labels, source masks, visual appeal or a cross-cell winner.

Preserve the selected seed's full 47/46 original rows, including failures/nulls,
native floating XY, sampled integer XY, sampled depth/world point, saved own
TCP, reference deltas and original source linkage. For every adjacent pair,
record exact inequality flags for native XY, sampled XY and saved sampled depth,
plus Euclidean distance between the two already stored world points when both
exist. This distance is a descriptive comparison of frozen outputs; do not
reproject, retrack or infer a replacement correspondence.

Report the first exact native-XY, sampled-XY and depth change over the full
trajectory, and separately after preclose. No nonzero threshold is used. Find
the largest consecutive stored-world-point distance over the full trajectory;
ties choose the earliest destination capture. Also retain the largest such
distance after preclose to distinguish prior approach effects. Unknown pairs
remain null. The selected complete trajectory remains the primary evidence.

Display a fixed five-column context per cell: preclose, postclose/hold, postlift,
the frame immediately before the earliest largest full-trajectory 3D jump, and
that jump frame. Keep duplicate columns when boundaries coincide. In each
column show the **unmarked original 384×384 RGB**, a local 21×21 RGB neighborhood
centered on that row's saved sampled integer pixel, and the corresponding exact
21×21 saved-depth neighborhood. Enlarge neighborhoods by nearest-neighbor only.
Use one shared depth color range per cell equal to the finite minimum/maximum
over its five displayed neighborhoods, label that range, and preserve all exact
depth arrays. This is display normalization, not a validity/classification gate.
Padding outside the original image is black for RGB and unknown for depth.
Missing sample coordinates produce an explicitly unavailable local panel.

Read only each bound original NPZ's RGB/depth arrays for these displays. Do not
read evaluator journals, masks, contacts, object pose or source state; the
independent audit and extraction journal are hash linkage only. No LK, model,
physics, render, FK, backprojection, threshold fitting, reseeding, reclassification
or replacement estimator is allowed. Qualitative interpretation should identify
what image/depth evidence supports motion, a depth/surface switch or apparent LK
drift, and leave ambiguous ownership unresolved.
