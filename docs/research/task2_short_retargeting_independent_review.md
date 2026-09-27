# Material limits of the two-action retargeting probe

Reviewed the proposal at retention commit `bf56741680aeb185d87ac46c4e62311871a3439e`,
document SHA-256 `2b6ce326a930d31640803b536c42d70518c41680c6f9400e3b315974a2b8411b`.
The current BOX source passed independent stored-output review in `fe2a236`;
both returns are single complete 12-token EOS boxes on the same actual RGB and
visual tensors as the current slow POINTs. Current-depth results are recorded
in `4ae646f`. No additional model or physical work was performed for this review.

The design is adequate for a bounded causal intervention on the selected goal
packet, followed by actual controller execution. It already discloses the mode
change, reuse of archived semantic outputs, fixed support, short horizon and
common evaluation point. Those are limits on interpretation, not reasons to
expand this experiment.

The following implementation and reporting details materially affect that claim:

1. **The common support representation is part of the experiment.** With the
   same current away POINT and own state, stale BOX support selects FWD, raw
   current depth selects STOP, and the existing partial-silhouette depth subset
   selects DOWN. Its FWD veto is the single apparent housing-edge pixel
   `[269,158]`, not an established environmental obstacle. Consequently the
   proposed current target BOX must remain the prospectively selected common
   packet; do not substitute a depth representation, combine masks, or choose
   among them according to which lets a desired arm move. A narrow target BOX
   is partial observed target support and does not become full-scene geometry
   merely because its pixels are current.

2. **The original contact boundary is not automatically inherited by the
   callback.** `task2_box_point_boundary.collect` constructs its
   `PassiveContactRecorder` locally, but `after_approach` receives only backend,
   executor, camera, recorder, groups and approach termination. The old
   grasp-transfer suffix uses a plain recorder and a different
   `unexpected_robot_contact` check. The new callback must explicitly preserve
   the registered initial above-0.05-N robot-pair baseline and after-completed-
   primitive stop semantics. Rebaselining at the relocated boundary or copying
   the scripted suffix's check would silently change the external stopping
   condition. Record normal contact stops as outcomes; distinguish them from
   infrastructure failure/replay mismatch.

3. **Bind the physical common start to the saved own packet as well as RGB-D.**
   The existing complete prefix verifier compares all scientific records and
   source frames; it is substantially stronger than merely replaying action
   names. Keep it, the declared scene-event checks, and exact postevent
   RGB/depth/K/T admission. Also assert the three geometry inputs and the fourth
   returned own field match the registered postevent packet before the first
   decision. Use the just-forced returned observation after the event and the
   just-returned endpoint observation after each action. This is a direct source
   binding check, not another state-estimation procedure.

4. **Physical improvement of the selected metric is a limited consequence.**
   Both policies optimize nominal distance to their selected goal. Evaluating
   both against the fixed refreshed point is the correct shared comparison,
   but that point is also the refreshed arm's objective. A two-action distance
   advantage therefore tests whether the controller physically realizes this
   retargeting advantage, not independent evidence that the goal is a complete
   bottle model, that inference freshness alone caused it, or that the task
   improved. Report commanded versus realized displacement and both original
   goals with the common-point error. Keep the common point outside cached-arm
   selection. After the first move, the semantic goal and support remain fixed
   source-time observations; own-observation feedback is the only update.

The stale-support finding does not require a scripted common first FWD. Retain
the proposal's explicit rule to let current support determine both initial
choices and preserve any divergence at boundary zero. A second opportunity can
test continuation or early stopping; it need not be described as the earliest
possible divergence after support has changed. The registered two-action cap
and absence of retries, target repair, equalizing holds or rollout extension
should remain unchanged.

The current BOX support comparison subsequently completed at retention commit
`65a30c1`. Its result SHA-256 is
`27de4407329ce72ebc520a81f2e56bf63b0cd9834aa5618c437866d781c19440`.
The away box contains 2,250 valid depth points and no point is contained in any
of the seven nominal endpoint unions. Applying that empty exclusion set to the
two original away canonical inputs independently reproduced **cached DOWN versus
refreshed FWD at boundary zero**, without geometry recomputation or action
execution. Present current support has 1,220 points, including 40 already inside
current own proxies; its refreshed choice is STOP. The away fixture was already
selected in the proposal before these support outcomes and is not reselected.

The producer's stated callback design explicitly addresses the implementation
issues above: preserve the original initial contact baseline and last prefix
native record, assert exact live RGB-D/K/T plus all returned own fields/read time,
and replay the scene event even when the first decision is STOP without
executing a hold. Source-code review must verify these commitments. Root has
authorized the exact away pair, at most two moves each and one exact replay
each, conditional on that code/preflight review; this document is scientific
review rather than the prospective execution PASS.
