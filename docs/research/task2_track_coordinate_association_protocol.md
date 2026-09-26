# Same sealed tracks: pixel-center-index association check

This parent-authorized condition changes only the discrete depth/mask sampling
association for the 45,264 sealed rows from `task2-box-temporal-run-01`. The
historical floor outputs remain unchanged. No LK, reinitialization, model,
physics, new capture, renderer, smoothing, depth interpolation or parameter
search is permitted. This retrospective measurement-contract check follows the
observed first boundary; it is not a held-out improvement claim.

## Coordinate premise and prospective admission

The existing LK helper initializes integer array indices as image points and
returns subpixel coordinates in that same image coordinate system. The installed
OpenCV 4.11.0 `getRectSubPix` documentation defines
`patch(x,y)=src(x+center.x-(cols-1)/2, y+center.y-(rows-1)/2)` and interpolation
at noninteger source coordinates. A 1 × 1 patch at integer `(2,2)` therefore
returns array element `[2,2]`. Preserve that documentation in the preflight;
it is also documented in OpenCV's image-transform reference under getRectSubPix.

Before archived reassociation, a tiny synthetic 5 × 5 float image must verify
that equality with actual OpenCV. Analytic cases require symmetric ±epsilon
around an integer to choose that integer, crossing ±0.5 to choose the neighbor,
and exact half ties to choose the higher index. Negative/outside coordinates
remain subject to the ordinary bounds check. Stop if these premise checks
fail; do not inspect labels to choose another convention. No archived image
or trajectory is used in these tests and no LK is called.

The fixed alternative is componentwise `floor(x+0.5)`. Historical floor is
`floor(x)` and remains the sealed baseline. Both use the original inclusive
0.01–5 m validity and backproject the selected array pixel center with the
separate existing `(index+0.5)` raster convention. Do not add 0.5 to the LK
coordinates themselves or sample interpolated depth. The check concerns which
array element is associated to a center-index track, not a camera calibration
or rendering correction. It does not prove general RGB/depth ownership.

## Fixed rows, comparison and boundaries

Pin source journal SHA-256
`0e7bd76d3f6b11244729bc767ec1b1f9a2625aa6069e494adf9743ea5900cf05`,
sensor seal `bae9793115ededab12b6b5bca242af9cdb0c2ed8c1e8d62219af3bbce65cc30b`,
and original per-arm track/summary hashes in the adapter. Reuse sensor source
admission and immutable helper SHA-256
`655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50`.
No old/new mask, contact, target pose or previous membership row enters the
sensor computation. Source preflight checks schemas/hashes only and never
computes alternative archived association, displacement or membership.

Copy every original native coordinate, forward/backward status/error/residual,
seed identity and capture/TCP timing field exactly. Native failure stays failed;
depth unknowns keep explicit reasons and strict JSON nulls. At run time verify
historical floor sampling reproduces each sealed original surface row exactly.
Then apply only the fixed alternative association and the unchanged projection,
initial/preclose deltas, fixed 492 denominators and count/median/IQR summaries.
Both arm files retain all 492 × 46 rows. Preclose-relative values remain absent
before capture 13; cohorts use each convention's valid surface at that fixed
reference with missing later rows retained, never selected from labels.

Record per-capture counts of changed sample pixels and changed depth values
by exact old/new equality, denominator 492. Retain every original/new row for
inspection; compare the same existing motion summaries, not a fitted error or
holding classifier. Initial, final and first historical departure are fixed
report checkpoints; complete per-capture sensor/membership curves remain.

Seal all alternative sensor rows, summaries and paired-change counts before
invoking the unchanged proxy-only evaluator. It samples the archived bottle
mask at the new selected index and retains initially outside, observed later
departure and unknown separately. Masks are never used to choose a coordinate
rule or repair tracks. The original all-native-success result remains unchanged.
An association change may alter memberships without repairing correspondence,
and no claim that all later departures are resolved is licensed in advance.

## Execution and completion

Freeze this adapter/protocol/tests, run the synthetic-contract and actual-source
preflight with `/home/junhongli/miniforge3/envs/locateanything/bin/python`, and
obtain independent review naming the exact clean commit before alternative
outcomes. On PASS, run this one condition autonomously under parent authority.
Preserve failures/partial rows without retry or another rounding rule.

Entry point: `python -m embodied_runtime.experiments.task2_track_coordinate_association`
with `preflight --output RECEIPT`, then `run --output RUN --preflight RECEIPT
--review REVIEW`, then separately `evaluate --output RUN`. There are zero
tracker/model/physics/render calls. Report the native center-index premise,
changes to pixel/depth/motion and limited proxy membership, all unknowns and
remaining failures. Identity, surface ownership, generalization, retained load
and transfer to a smaller atomic lift remain untested by this comparison.
