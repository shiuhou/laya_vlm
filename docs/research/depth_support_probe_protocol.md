# Fixed depth support separation probe

Registered before running the probe. Development diagnostic only; no live policy,
model call, simulator execution, production perception change, or success claim.

Hypothesis: the dominant bbox membership error measured in the archived support
audit can be reduced by separating a nearer depth layer without a new vision model.
This is an aggressive two-layer foreground hypothesis, not an uncertainty-aware
production selector. A single depth view need not contain two separable layers,
and the nearer layer need not be the requested target.

Use all 18 accepted historical RGB-D/raycast paired states from
`runs/reference-pilot/init{0,1,2}-raycast-v02`, unchanged. These are development
states already inspected by the prior audit, not held-out data. Reuse its source
integrity checks and retain every boundary, missing result and disagreement.

For each original bbox, retain finite depths in [0.01,5] m. Sort ascending.
Set minimum group size to max(3, ceil(0.05*n)). Consider only adjacent splits
leaving at least that many pixels on each side. Choose the largest adjacent depth
gap; ties choose the lowest split index. Return the nearer group as foreground,
retain the farther group, both pixel counts, gap, valid count, split rank, and
support pixel identities in evidence. If no split satisfies group sizes, return
unknown. No minimum-gap threshold or oracle-dependent correction is permitted.
Zero-gap ties are retained and explicitly flagged as ambiguous: stable raster
order breaks equal-depth pixel ties, without a claim that this identifies a
physical surface. Backproject each support with the existing half-pixel camera
convention. No tuning after results.

Compare full-bbox and foreground centroids against the same visible-target-surface
oracle referent. Oracle mask and ray depths are evaluator-only. Record purity,
visible-target recall, 3D surface-centroid error, and support changes for every
frame/init. The target remains a view-dependent surface centroid, not a grasp
point or full object pose. Shared camera calibration limits calibration claims.
Do not include the median-depth proxy in an accuracy ranking with this estimand.

Use matched sensor proprioceptive TCP to construct a separate algebraic diagnostic:
six nominal 10 mm world-axis translations plus hold, in fixed order
x+, x-, y+, y-, z+, z-, hold. Define preferred sets by maximum reduction in target
Euclidean distance (absolute tie tolerance 1e-12 m). Report all tied choices,
intersection with oracle-preferred set, true geometric reduction range of selected
set, and regret range against the oracle maximum. No scripted tie winner. No
rotation, collision, dynamics, controller realization or execution is inferred;
these directions are not expert manipulation labels. This tests whether target
estimation errors can change a simple local directional decision.

Report all18 and per-init results, unchanged versus improved/worsened cases,
unknown/ambiguous counts, source hashes, and representative RGB/support overlays
and scatter plots. Inspect both successes and failures. If separation fails, state
which assumption failed and stop; do not retune or add another method in this probe.

Acceptance is diagnostic completeness and honest support-boundary accounting,
not a target success rate. Any apparent improvement must be validated later on
independent task/view states before runtime integration.
