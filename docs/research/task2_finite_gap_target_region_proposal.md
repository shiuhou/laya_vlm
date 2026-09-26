# Conditional proposal: full finite-gap target translation region

**Analytical preparation only; no corner coordinates, containment outcomes, pose search or new ranking has been calculated.** Execution remains a separate root decision after the other lane's exact-terminal one-step finite-gap result. This proposal does not authorize physics or a new perception call.

## Region from the existing calibration

Keep original P, all1,340 full-BOX points and the endpoint-veto terminal returned orientation/signed jaws fixed. Let R be the correctly mounted grip-site-to-world rotation, and t the hypothetical TCP translation. Reuse the two exact finite pad boxes and their current signed-slide placement. In site axes, the closed finite facing-gap prism is

`G=[a_x,b_x]×[a_y,b_y]×[a_z,b_z]`.

Extract X bounds from the left pad's facing inner face and the right pad's facing inner face; intersect the pads' Y ranges and Z ranges. For the already audited static calibration this is symbolically

`a=(-q1+0.0005, −0.008, −0.0116) m`,
`b=(-q2−0.0005, +0.008, +0.0044) m`.

Use signed q1/q2, not summed absolute encoder aperture. Prefer the existing `finite_gap` helper's calibrated vertices and verify these formulas, rather than substituting a task-specific offset. “Open gap” refers to open jaws; preserve the existing closed boundary convention. Empty overlap is an empty target-region admission result with no replacement geometry. Degenerate nonempty overlap is a lower-dimensional convex region; eight registered corner indices may then have duplicate coordinates.

The complete TCP translation region putting P in this gap is exactly

`T={t:P∈t+RG}=P−RG`.

It is a reflected, rotated rectangular parallelepiped, not generally world-axis aligned. Its eight corners follow directly from the eight endpoint choices of G:

`u_s=(1−s)⊙a+s⊙b;  t_s=P−R u_s,  s∈{0,1}³`.

No center placement or preferred translation is selected. P remains unchanged; this is the zero-distance region of the already proposed finite-gap relation. Indeed `distance(P,t+RG)=distance(t,T)` by the Euclidean norm. The zero-distance region is distinct from the full no-strict-improvement set of a discrete10mm world-axis rule, which can also stop outside T.

## Same common-witness argument

Let C_j be one fixed separate convex own proxy in site axes, and q one fixed observed point. Translations excluded by this pair form the convex set

`E_(q,j)={t:q∈t+RC_j}=q−RC_j`.

If the **same q and same j** contain q at every registered t_s, then all eight vertices of T lie in E_(q,j); convexity proves `T⊆E_(q,j)`. Thus the entire finite-gap target region is excluded under this frozen guard. Equivalently, in site axes it is sufficient to establish `Rᵀ(q−P)+G⊆C_j` by checking G's eight corners.

All-corner positive unions with different points/proxies do not establish this claim. The full excluded set is a union of convex pair sets, not necessarily convex. The common-pair test is sufficient, not necessary: **no common witness means no region-exclusion certificate**, not that the region is feasible, that a route exists or that some pose is a qualified grasp. Preserve all results without choosing or presenting a winning pose.

## Narrow source reuse and prospective safeguards

- Reuse the same terminal own packet, unchanged P/full support/normalized calibration source seals, mounted `geometry.place`, and `proxy_distance` convention. Reuse the other lane's finite pad-box derivation after its source is admitted. No one-step candidate-distance calculation is repeated here.
- Register exactly eight corners in lexicographic endpoint-choice order. Persist the full8×1,340×5 point/proxy containment tensor, all derived pad bounds and translations, and every same-pair witness. No interior sampling, adaptive refinement, sweep, margin, support pruning or additional orientation/jaw state.
- The prior `task2_point_goal_cell.common_corner_witnesses` assumes nine rows (center plus eight corners) and ignores row0. Do **not** apply it directly to this eight-row tensor. A future small adapter must explicitly intersect all eight registered corner rows, preserving all five separate proxies.
- A positive result needs independent fixed-facet recomputation and signed facet-slack verification, as in the point-cell audit. One fixed facet system per proxy with shifted query points avoids treating separately rounded translated hulls as the proof. Record numerical tolerance and margins; do not silently add a physical safety margin.
- Before any real-source calculation, freeze a compact protocol/adapter and synthetic tests for `P∈t+RG ⇔ t∈T`, rotated/asymmetric signed-jaw corners, degenerate/empty regions, eight-row indexing and the positive-union/no-common-witness counterexample. Obtain independent prospective review. Stop after the single registered calculation, whether certified or inconclusive.

Any resulting certificate is limited to frozen observed support, calibrated convex proxies, terminal orientation/jaws and the finite-gap point relation. It does not verify target identity/extent, actual contact, path clearance, grasping, all orientations or global task impossibility. This proposal introduces no policy, target offset or new semantic feature.
