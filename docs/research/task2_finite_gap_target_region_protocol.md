# Eight-corner finite-gap target-region certificate test

One bounded offline calculation of the complete P-in-finite-gap target translation region, with terminal orientation and signed jaws fixed. The prior one-step scalar-objective test formally changed STOP to LEFT by1.958849µm; its criterion remains unchanged and no dynamics follow. This calculation asks a separate compatibility question. A negative common-witness result remains inconclusive; there is no automatic solver, planner or additional pose test.

## Frozen sources and sensor boundary

Reuse the exact terminal decision28 packet from `task2-endpoint-containment-veto-run-01` through the already reviewed `task2_finite_gap_control.prepare()` source/schema reader. It verifies journal SHA256 `17f504c75f9898ec515f474588dac730503c5bd4bef85c3782310b09212de36b`, manifest SHA256 `5b46de6585fa9940ec8c32cd3a3a61ba704177398d50d7dd4821a135200924ad`, exact decision identity, the original P, all1,340 full-BOX points, normalized five-proxy own calibration, returned site position/body quaternion/signed jaws, numerical versions and immutable helpers. It computes no new region or one-step outcomes.

Pin the completed finite-gap request/result/seal, including result SHA256 `dc569f9a564c59faa3686254f6fa726ad304fdcdce37b753a10108e05e821a13`, and its helper source SHA256 `0302f9d1fc4152ba69ee5d6d88122b432f8b1aea1c5b7902e4263e5e40306648`. Require exact equality to the already frozen terminal request. Pass only P, full observed support, own packet/calibration and the sealed static finite-gap/mount/pad-vertex reference to a separate worker. The prior selected move, score, contact labels, point-goal-cell witnesses, target identity and successful-pose data are not worker inputs.

P, full support, orientation and signed jaws remain unchanged. Exact own sample time is unknown. No segmentation, support pruning, margin, tracking, target shift, new semantic feature, model call, renderer or world construction.

## Registered eight corners

Derive the same finite closed gap G from exact pad-box faces and finite Y/Z overlap using unchanged `finite_gap`. Reuse pure calibrated FK and the mounted own placement helper; require bit-exact reproduction of the prior finite-gap bounds, pad vertices and mount. Do not recompute any one-step candidate score or rank. Empty gap stops with preserved failure, not alternative geometry. A nonempty degenerate gap retains all eight indexed corners and records the distinct coordinate count.

With fixed grip-site-to-world R, P lies in `t+RG` exactly for translations `t∈T=P−RG`. G's eight corners are `u_s=(1−s)⊙lower+s⊙upper`, with s in lexicographic `(0,1)^3` order. Register exactly eight TCP corners `t_s=P−R u_s`. T is the exact zero finite-gap-distance region, not the full no-strict-improvement set of the discrete10mm rule. No center, winning pose, goal-point replacement or additional placement is selected.

For each registered t_s, translate all five separate current own proxy solids rigidly from the same returned TCP position. Keep orientation/jaws fixed and gaps between separate proxies. Apply unchanged `proxy_distance` containment to every full-BOX observed point. Retain the existing1e−12 halfspace numerical tolerance, with zero added physical margin; no sweep or adaptive refinement. Verify that the reconstructed corner relation reproduces the gap corner within that numerical tolerance without altering either region.

Persist all eight TCP/gap corners, endpoint-choice indices, every translated proxy vertex set, per-point/per-proxy containment and the complete8×1,340×5 boolean tensor. All five proxy names and all1,340 point indices remain available; no proxy is preselected using contact knowledge.

## Certificate and limitations

Intersect **all eight rows** separately for every point/proxy pair. A same q/j witness at every t_s places every T corner in the convex set `q−RC_j`, proving the whole T is excluded under this frozen observed-point guard. Report every common witness. The earlier nine-placement helper skips a center row; it is not used for this eight-row calculation. Synthetic tests must catch omitting either the first or last corner.

Positive unions at every corner with different points/proxies are insufficient. If no same-pair witness exists, report `no_common_witness_certificate` and remain inconclusive about region exclusion, feasible poses and routing. Never choose an unexcluded corner as a winning pose or launch a follow-up search. Even a positive certificate concerns only the frozen cloud/proxies and terminal orientation/jaws, not actual collision, full target extent, grasp fit, all orientations or task impossibility. The approach veto still applies identically to all five solids, including pads; this is not a grasp-contact contract.

Independent result review must compare the full tensor/lists and use one fixed facet system per proxy with shifted query points to assess any positive witness's signed corner-facet slack. Robust whole-region wording waits for that review. No physical safety margin or new pass/fail threshold is fitted afterward.

## Review and execution

Freeze this protocol, compact source and synthetic tests. Test region equivalence under rotated/asymmetric signed-jaw geometry, empty/degenerate regions, eight-row indexing, same-pair convexity and positive-union counterexamples. Run source-only preflight with `python -m embodied_runtime.experiments.task2_finite_gap_target_region preflight --output RECEIPT.json`; it checks existing seals and schemas without constructing new corners or evaluating any region outcome.

Obtain independent prospective PASS naming the exact clean commit before the single `run --output RUN --preflight RECEIPT.json --review REVIEW`. The controller invokes a sanitized pure worker once, seals its result and preserves any partial failure with no retry. Report all eight results and conditional certificate/inconclusive outcome; stop there, with no model or physical run.
