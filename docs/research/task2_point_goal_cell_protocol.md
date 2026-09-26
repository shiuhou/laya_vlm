# Task2 fixed-terminal-orientation point-goal cell check

One offline sensor-only calculation after the endpoint-veto trajectory: determine whether the original point-rule stopping region conflicts with the unchanged observed-point guard at the terminal returned orientation and signed jaw positions. This precedes any planner or physical policy change. No dynamics, pose search, perception query, target update or retry is authorized by this protocol.

## Sources and information boundary

Use the sealed endpoint-veto collection journal SHA256 `17f504c75f9898ec515f474588dac730503c5bd4bef85c3782310b09212de36b` and its exact replay result SHA256 `341abd1d43e7a7c114cc764cef8506196b7cc8dc1f664d4fdf2f70b602a42def`. Select the returned own packet at endpoint step27, capture29, immediately before terminal decision28 STOP. Keep the returned eef-body quaternion and paired signed finger positions fixed throughout. Exact sensor sample time is unknown.

Use exactly the prior1,340 full-BOX observed points, original P and normalized five-proxy own calibration subtree. Verify equality to both the guarded run manifest and the original source frame/sensor/calibration artifacts. Reuse `support/subtree/place` and `proxy_distance` without edits, with the audited grip-site/eef-body static mount. Do not substitute a native pose or merge separate proxy solids. Hash unchanged geometry and point-rule helpers. Current static geometry remains conditional on the prior calibration/compatibility evidence; no historical asset-byte or current compiled-mesh equivalence claim is added.

The controller extracts only the fixed observed support, P, own calibration, three-field terminal own packet and nominal step into the worker request. No scene identity, object pose, contact, outcome label, saved guard candidate result or physical branch result enters the computation. The terminal returned TCP position is retained as provenance only; hypothetical placements replace it with the registered positions below. Returned orientation and jaws remain unchanged.

## Nine predetermined placements and stopping-cell derivation

For nominal step h=0.01m, changing TCP by ±h along axis i changes squared TCP→P distance by `h² ∓2h(P_i−TCP_i)`. Some move on that axis strictly improves distance iff `abs(P_i−TCP_i)>h/2`. Therefore the unchanged unguarded six-axis strict-improvement rule has no improving movement exactly in the closed axis-aligned cell `P+[-0.005,0.005]^3 m`. Equality ties stop. The5mm half-width is analytically derived from the existing10mm movement size, not fitted to contact or this trajectory.

Place the same five separate proxies at exactly nine hypothetical TCP positions: index0 at exact P, then indices1–8 at `P+0.005*s` for signs `s` in lexicographic `product((-1,+1),repeat=3)` order. Fixed terminal orientation and signed jaws are applied through the original `place` helper at every position. Evaluate all1,340 observed points against every proxy at each placement with the unchanged existing closed-halfspace containment convention, including its1e-12 numerical tolerance. Add no physical margin, sweep, pixel cleanup, geometry inflation, changed target or extra placement.

Persist the complete9×1,340×5 boolean containment tensor, all nine TCP positions, proxy vertices/mount, per-proxy contained source indices, and the original sanitized request. Do not choose the point or proxy using oracle contact identity; report every pair satisfying the same test over all eight corners.

## Registered interpretation

A certificate requires **one identical observed point and one identical proxy contained at every one of the eight corners**. Compute the intersection over corner masks separately for each point/proxy pair. For fixed observed q and fixed oriented convex proxy C, translations t satisfying `q in C+t` form `q−C`, a convex set. If this one set contains all eight corners, it contains their convex hull and thus the whole point-rule stopping cell, conditional on the declared proxy/helper numeric convention. If at least one same-pair witness exists, the full stopping cell is excluded by this observed-point guard at this fixed orientation/jaw state. This distinguishes goal/guard incompatibility there from a claim that greedy routing alone explains the stall.

Merely finding some containment at every corner is insufficient when points or proxies differ: a union of convex exclusion sets need not be convex. Intersection at exact P alone is also weaker. If no common witness exists, this calculation provides no whole-cell certificate; do not conclude the cell is feasible, routing is the sole issue or a planner would succeed. Save exact-P containment and all-corner union positivity as separate weaker observations.

Even a whole-cell certificate concerns the frozen partial observed cloud and own proxy convention at the terminal orientation/jaw state. It is not a physical collision certificate, complete scene/object model, impossibility over all orientations/jaws/horizons, or evidence about grasp/task success. No robot action or planner is added regardless of the result.

## Freeze and execution

Commit code/protocol/synthetic tests, then run `python -m embodied_runtime.experiments.task2_point_goal_cell --preflight --output RECEIPT.json`. Preflight verifies real sources and exact support/calibration/P equality without computing any nine-placement outcomes or constructing a world. Tests cover the analytic stopping-cell derivation, fixed-pair convexity, and counterexamples where positive corner unions or exact-P-only containment do not certify a cell.

Obtain independent prospective PASS naming the exact clean freeze before the single real-source calculation. Invoke `--output RUN --review REVIEW`; the controller writes the sanitized request and launches a separate pure worker once, then seals its artifacts. Preserve any partial failure with no retry. Report all nine per-point/per-proxy results, every same-pair witness, exact-P versus corner-union versus whole-cell statements separately, source hashes and numerical limits. No physical execution occurs.
