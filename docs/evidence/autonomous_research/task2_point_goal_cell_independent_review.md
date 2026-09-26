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

## Stored-result review

**PASS** after the single calculation. The independent checker rebuilt one
fixed facet system per proxy at exact P, translated the query points for all
nine poses, and reproduced every one of the 60,300 containment booleans and
per-proxy index lists. Proxy translations agree within 2.23e-16 m. It checks
the request hash, result seal and complete common-witness identities.

All 123 same-point/hand-proxy witnesses are strictly inside at every corner
without relying on the 1e-12 tolerance. Their minimum signed facet margins
over the eight corners range from **0.292925 to 17.087352 mm**. Thus at least
one fixed exclusion set contains the entire stopping cell with substantial
numerical slack under the frozen geometric model. This rules out a route-only
explanation within that model and fixed orientation/jaw state; it does not
prove physical collision, object identity, or impossibility at another pose.

[Complete checker receipt](task2_point_goal_cell_independent_audit.json) and
[stored-only checker](../../../experiments/task2_point_goal_cell_evidence_audit.py)
retain all 123 witness margins. No simulator, model or new target is used.
