# Observation age and support ownership are separate uncertainties

The [current-BOX comparison](../evidence/autonomous_research/task2_postevent_box_support_findings.md)
supports this distinction in two bounded observations. Present support changes
from 1,340 old points with only DOWN vetoed to 1,220 current points with
FWD/LEFT/RIGHT/DOWN vetoed and STOP selected. Forty current returns already lie
inside the saved hand proxy, at the upper BOX/gripper-to-neck image boundary.
After relocation, 2,250 current points remove the old 36-point DOWN witness;
the fresh goal still selects FWD.

This is consistent with refresh adding robot-contaminated returns in the present
scene while removing a stale target-relative obstruction after relocation.
Ownership remains unknown: mixed edge depth or calibration/proxy mismatch can
also explain present containment. Away zero witnesses covers a changed ROI,
not the complete scene. Both semantic extent and depth changed together.

A temporal belief should therefore retain source time, target association and
surface ownership as separate uncertainties. Newer observation does not prove
better ownership; age alone does not invalidate a stationary object surface.
The evidence supports that distinction, not calibrated ownership probabilities
or a validated update rule. Exact source sample times remain unknown.

## Conditional future discriminator

**The rendering/source-ownership branch remains closed.** Current ownership can
remain unknown for the bounded retargeting pair. Revisit attribution only if
actual behavior or an architecture decision requires it. This note authorizes
no experiment, model, geometry, mask repair or implementation.

If attribution later becomes necessary, the smallest useful rendered diagnostic
would freeze all old/current ROI samples and use normal, own-gripper-hidden and
target-hidden RGB-D at each matched reference/current snapshot. With qualified
normal baselines this requires two additional views per epoch, without physics.
Camera, depth convention, other render settings and state remain fixed; normal
input equivalence and existing read-only/determinism checks must hold.

These hiding operations would be privileged **evaluator interventions**, using
only the identity of the disabled rendered geometry. No target pose coordinates,
mask or cleaned cloud would reach the selector. Own-hidden depth sensitivity
with target-hidden invariance would support own visual contribution; the converse
would support target contribution. Mixed/antialiased boundaries, both-sensitive
samples and failed render checks stay ambiguous. A normal/own-hidden pair alone
cannot establish whether old points belong to the target, so the target-hidden
control is necessary for the stated contrast.

A conservative positive witness for old target support would require target
attribution at both epochs and an exactly repeated normal pixel/depth sample
under identical camera calibration. Changed or occluded samples remain unknown;
failure of exact agreement does not prove invalidity. No fitted depth tolerance,
mask margin, nearest-neighbor threshold or favorable point selection is needed.
Report all ROI and saved-veto samples by attribution/persistence, including every
unknown. Preserve the predeclared present and away populations. Do not evaluate
a filtered cloud or revised policy within that attribution-only diagnostic.
