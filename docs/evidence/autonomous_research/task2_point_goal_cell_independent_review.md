# Prospective review: fixed-orientation point-goal cell

**PASS** for producer freeze `60ad6d7dd69aa5deb7be0dfe999e26fd417dd75e`,
reviewed by root before any nine-placement outcomes. This admits one offline
calculation, not a physical run or policy change.

Inspected the complete worker/controller, protocol, four synthetic tests and
unchanged `CanonicalDecisionInput.rule_token()`, geometry placement and convex
halfspace helper. Independently ran the four tests: **4 passed in 0.26 s**.
Root real-source preflight passed with no world or geometry outcomes:
`runs/autonomous-research/task2-point-goal-cell-root-preflight-01.json`.

The h/2 cell follows from the strict six-axis squared-distance inequality in
real arithmetic; no fitted physical margin or trajectory coordinate defines it.
The worker receives original P, all 1,340 observed points, own calibration and
terminal returned own orientation/jaws. It replaces only hypothetical TCP
translation. Object state, successful pregrasp coordinates, contact labels,
saved candidate outcomes and masks do not enter the worker.

The certificate requires the same point/proxy pair at every corner. This is
the correct convexity condition; a union of unrelated corner witnesses is
insufficient. Complete containment tensors and vertices remain available for
independent arithmetic and numerical-margin inspection. Exact-P, corner-union
and same-pair conclusions are separated. Tests include false-positive union
and center-only cases. No target search, new target, policy, dynamics or inference
is introduced.

Scope remains the frozen orientation/jaws, stale partial observed support,
calibration and existing numerical containment convention. An exclusion
certificate is not physical collision ground truth or global unreachability.
Numerical boundaries of a real-arithmetic stopping cell are not a guarantee
about every floating-point tie in the runtime. Inspect witness halfspace slack
before describing the certificate as numerically robust.
