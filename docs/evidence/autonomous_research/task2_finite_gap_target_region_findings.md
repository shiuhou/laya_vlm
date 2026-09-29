# Task2 finite-gap target region conflicts with the fixed-orientation guard

**The entire finite-gap target translation region is excluded by the observed-point guard at the frozen terminal orientation and jaw positions.** There are **124 identical observed-point/hand-proxy pairs contained at all eight registered corners**. Independent verification using one fixed facet system per proxy reproduced all **53,600 containment entries** and found every shared witness strictly inside without the numerical tolerance. Their minimum signed corner-facet slacks range from **0.341268 to 13.998971 mm**. These are geometric slacks for the frozen cloud and convex proxies, not physical safety margins or uncertainty bounds.

| Original unmarked source RGB | All 124 common source pixels in magenta |
| --- | --- |
| ![Original source RGB, unchanged pixels](task2_finite_gap_target_region_source_rgb.png) | ![Same original source with every common source pixel marked](task2_finite_gap_target_region_common_pixels.png) |

Both images use the original cached RGB-D frame. The left PNG reproduces every RGB value exactly; the right changes exactly the 124 common source pixels. All 1,340 full-BOX points retain their original pixel/depth/world coordinates, with no segmentation, mask cleanup or support filtering. P remains the original BOX-center ray at the inner-crop median depth; it is not a measured object center or grasp pose.

## Exact region and fixed corner order

The finite closed gap in grip-site coordinates is `G=[lower,upper]`, derived from the calibrated pad inner faces and their finite Y/Z overlap. Its bounds reproduce the prior sealed finite-gap calculation exactly:

```text
lower = [-0.039498278210574105, -0.007999999999999997, -0.0116] m
upper = [ 0.039498593501164685,  0.007999999999999997,  0.004399999999999987] m
```

With the unchanged point P and fixed site-to-world rotation R, P lies in the translated gap exactly when `t ∈ T = P − R G`. The registered eight translations are `t_s = P − R u_s`, where `u_s=(1−s)·lower+s·upper` and s runs through lexicographic lower/upper choices in site XYZ. Thus the row labels below describe **gap-corner endpoint choices**, not sorted world TCP coordinates. The complete gap corners, world TCP coordinates, R and signed jaws are retained at full precision in the summary.

| Index | Site XYZ choices | Point union | Hand | Finger1 | Pad1 | Finger2 | Pad2 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 000 | 254 | 175 | 79 | 30 | 0 | 0 |
| 1 | 001 | 158 | 125 | 33 | 17 | 0 | 0 |
| 2 | 010 | 204 | 175 | 31 | 0 | 0 | 0 |
| 3 | 011 | 157 | 125 | 32 | 12 | 0 | 0 |
| 4 | 100 | 308 | 174 | 0 | 0 | 152 | 28 |
| 5 | 101 | 229 | 124 | 0 | 0 | 116 | 29 |
| 6 | 110 | 202 | 175 | 0 | 0 | 51 | 0 |
| 7 | 111 | 176 | 125 | 0 | 0 | 72 | 0 |

These are contained observed-point counts, not physical contacts. A point can be contained by overlapping proxies, so the union need not equal the column sum. Individual corners include finger/pad containment, but **all 124 shared pairs use `gripper0_hand_collision`**. No finger or pad supplies a shared eight-corner witness. All five separate proxies and all point indices were evaluated and retained.

For each fixed observed point q and oriented convex proxy C, translations t containing q form the convex set `q−C`. A same-point/same-proxy pair contained at every T corner therefore persists throughout their convex hull, the whole T. Each of the 124 shared pairs supplies this certificate. Merely having positive unions at every corner, with changing point/proxy witnesses, would be insufficient.

The independent audit evaluates each shared pair's signed facet slack at all eight corners using one original facet system and shifted queries. Taking the minimum across those corners and facets gives strictly positive values for every pair, ranging from **0.0003412682429797531 to 0.013998970790134 m**. All 124 individual minima and identities are included in the summary. No new physical margin or pass threshold was fitted. The maximum inverse target-relation residual is **5.637851296924623e−17 m**.

## Meaning and verification

This is the **exact zero finite-gap-distance target region**, not the complete STOP set of the discrete 10 mm rule. It differs from the earlier world-axis P±5 mm point-goal cell: the finite gap has asymmetric site-Z bounds and its translation region is reflected and rotated. The regions need not be nested, so 124 common witnesses here versus 123 in the earlier calculation is not a monotonicity comparison.

At these frozen orientation/jaw settings, changing the translation route alone cannot admit P into this finite gap under this observed-point guard. This does not establish actual collision, full scene clearance, object fit, grasp readiness, global task impossibility, or results at other orientations/jaw positions. The partial unsegmented cloud and calibrated convex proxies remain assumptions, and the own sample time is unknown. The earlier one-step STOP→LEFT strict-rule PASS of 1.958848724274709e−6 m remains unchanged; no physical follow-up was run.

The producer freeze was `22fa806d0221c0aa2f663841ffd80f3ba69d2ff2`; all 14 focused tests passed. Independent prospective PASS was `fbc7dda`, followed by exactly one sealed real-source calculation, with no retry, model call, simulator construction, renderer, robot action, pose selection or adaptive refinement. Independent stored-result PASS `f797467` matched the entire tensor, every per-point list, corner/translated vertices and seals, and supplied the strictly positive fixed-facet slack needed for the bounded whole-region statement.

- [Full-precision summary, all eight results, all 124 witnesses and embedded independent audit](task2_finite_gap_target_region_summary.json).
- [Complete 8×1,340×5 containment tensor and registered placements](task2_finite_gap_target_region_containment.npz).
- [Independent review](task2_finite_gap_target_region_independent_review.md) and [numerical audit](task2_finite_gap_target_region_independent_audit.json).
- [Frozen protocol](../../research/task2_finite_gap_target_region_protocol.md) and [stored-only reporter](../../../embodied_runtime/experiments/task2_finite_gap_target_region_report.py).
- Raw request, all proxy vertices, tensor and feature seal: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-finite-gap-target-region-run-01`.

| Artifact | SHA-256 |
| --- | --- |
| Feature seal | `df260ad8e38988d3c1e6c9159f3f88956023f1f36dcc27237d4d11eab3b05a47` |
| Raw result | `5b9ae028178c5903347f8347908e4982359117a11aa55f42b831beef37cf8d70` |
| Complete containment tensor | `82b6029cbf00eb5ce84c220067f0f6a23fdaa7e80573815750fc507ec89c35a3` |
| Independent numerical audit | `8ac21081d5e1df3848c2bead2960943c3d7e84d9c3f620eaa3a61db00c19a9ad` |
