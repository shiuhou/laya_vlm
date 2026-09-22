# Verified current state

Reviewed 2026-09-23 (Asia/Shanghai). This is the current-state index; older handoffs are historical.
Verified runtime implementation: `fa90144` (after `37c5daa`, `8e9dc0f`). The
documentation-only successor contains this index; use `git rev-parse HEAD` for
the checkout's full revision. Experiment version: **stage2-smoke-v1**, not E1.

## Active and verified

- LIBERO RGB-D capture, capture transforms, LocateAnything, query-as-track identity,
  capture-time temporal fusion and validity metadata; robot-only proprioception.
- `vision-candidates-v1`: hard geometry/semantic/gripper/workspace checks, with
  direction and progress kept as soft evidence. No privileged visual preview.
- Rule greedy centroid approach and Laya typed choice on content-addressed complete
  snapshots. Singleton Laya choices bypass inference and are explicitly labeled.
- Stage 1 atomic contracts and temporal regressions remain passing.
- Durable hash-chained JSONL, captured RGB-D/calibration artifacts, model/source
  fingerprints, original decisions, execution intents and measured completions.
- Independent summary recovery, including partial records and unknown outcomes.

## Implemented but inactive

`QueryTrackManager` is not called by the real runner; `tracking_active=false`.
ReplayProvider exists but does not replay whole LIBERO trajectories in this smoke.
Jev physics preview is active only in oracle methods, never in visual candidates.
Workspace bounds are supported and tested but unset in the smoke configuration;
there is no collision-free-motion or grasp-affordance claim.

## Known limits and blockers

- Visual covariance is a depth/box heuristic, **not calibrated**. Box-presence
  score is not a calibrated semantic probability. No credible oracle-preferred
  action label/coverage metric has been defined.
- The active task is **close the top drawer**, not open/pull. No drawer movement
  occurred in the three-action smoke. Greedy centroid approach has not demonstrated
  task-level closing behavior or an informative temporal-disagreement segment.
- At 0.4 s without a fresh observation, position covariance trace exceeded the
  unchanged Stage 1 limit, leaving only STOP. Availability needs mechanism review.
- V0/latest, V1/temporal-without-validity, V2/temporal-validity matched ablations and
  deterministic delivery-delay controls are not implemented/frozen.
- All current runs use LIBERO init index 0. Changing a seed alone does not establish
  independent task initial conditions. Wall-clock async scheduling is recorded,
  not bitwise deterministic; GPU deterministic algorithms are disabled and logged.
- Shutdown drains in-flight inference for up to 30 s; an unresponsive native CUDA
  call can still exceed this bound. Hard-kill recovery preserves completed records
  and marks unacknowledged execution as unknown, not successful.

## Evidence and next gate

See [Stage 2 handoff](stage2_handoff.md) for exact commands, representative records,
changed files and retained failed attempts. Local artifacts are under
`runs/stage2/` (ignored by Git):

- `rule-seed1-attempt3`: clean three-action Rule smoke.
- `laya-seed1-attempt2`: clean three-action Laya smoke.
- `matched-seed1-step0`: actual Rule/Laya on one identical recorded snapshot.
- Failed attempts are retained, not overwritten or removed.

74 tests pass in both installed environments; lint and compileall pass.
P0-C: PASS for this bounded interface. P0-D: PASS for traceability/recovery.
Ready to freeze E1: **NO**. Ready for formal E1: **NO**.

Next action requires human review of the Stage 2 handoff and agreement on a
minimal task-sensitivity/availability check. No E1 tag or formal outcome exists.
