# Verified current state

Reviewed 2026-09-23 (Asia/Shanghai). This index supersedes historical plans, not raw
evidence. Current implementation: `9041f9d`, after `16c4fca`; the documentation-only
successor contains this index. Use `git rev-parse HEAD` for the full checkout revision.
Experiment status: **decision-interface smoke**, no formal E0/E1 and no freeze tag.

The current question is which sensor-derived state preserves oracle-conditioned
decisions, and separately which non-privileged candidate effects preserve decisions.
See [research.md](research.md), [architecture.md](architecture.md), and the
[decision-interface handoff](decision_interface_handoff.md).

## Verified active paths

- Stage 2 live runtime remains operational with visual validity, atomic contracts,
  temporal fusion, source isolation, and durable records. Its 74 tests remain passing.
- New **offline** canonical v0.1 projection/replay path: same schema for perceptual
  and explicitly privileged oracle state; unknown fields stay unknown.
- Separate candidate effects: Tier-0 nominal geometric effects and an explicit
  oracle-preview adapter. Primary State Gap replay uses no effects and one shared
  11-token semantics-only probe set, never executed by the collector.
- Same-provider paired replay, fixed question/history/candidates, field replacement,
  input identities, token-budget checks, and independently regenerated metrics.
- Real collection: 155 archived controls replayed with max state error `1.272e-11`,
  covering approach/contact/closure. Six paired states include a 0.4-s stale variant.
- Real compact Rule/Laya replay: 72 decisions, 36 paired comparisons, zero missing
  outputs; three identical-input repeats had identical returned choices/probabilities.
  All Laya prompt components fit, and consumed-token hashes were stable.
- Actual `init_state_id` passes to LIBERO's benchmark reset; inventory contains 50
  distinct initial-state vectors, separate from seeds. Only init 0 trajectory has
  been validated in this stage.

## Important limitations

- The new canonical path is not yet a validated closed-loop policy. Successful Jev
  collection does not establish correctness of current oracle-input Laya choices.
- Oracle collision-AABB center and perceptual query-box/depth point differ in
  definition. Numeric error is marked incomparable until a common referent is fixed.
- An early full-JSON replay silently exceeded Laya's context and clipped candidate
  meanings. That artifact is retained and invalid for complete-interface claims.
  `compact-v0.1` now rejects clipping and records actual tokens. This also narrows
  the old Stage 2 matching claim: matching upstream snapshots does not guarantee
  that every field reached the model. The legacy live full-snapshot presentation
  has not been retroactively converted to the canonical presentation.
- Tracking remains inactive. Covariance/semantic score are heuristic and uncalibrated.
  Current visibility/contact/holding/progress are not inferred from simulator state
  for perception. No collision-free or grasp-affordance claim exists.
- STOP-only Stage 2 behavior is explained primarily by the unobserved velocity prior,
  not an atomic/controller bug. No thresholds or Stage 1 fusion equations changed.
- Offline collection pauses simulation during model inference; it is not an async
  deployment performance experiment. GPU deterministic algorithms remain disabled;
  repeatability is measured at returned API precision, not guaranteed universally.

## Evidence paths and next gate

All local evidence lives under ignored `runs/interface/`:

- `trajectory-audit/`: inventory and all replayed physical states.
- `paired-smoke-attempt1/`: six pairs, RGB-D frames, observation/belief provenance.
- `replay-smoke-attempt1/`: retained **truncated** initial diagnostic.
- `encoding-audit/`: tokenizer-only comparison of old and compact presentations.
- `replay-smoke-compact/`: accepted unclipped diagnostic and regenerated summaries.

Earlier Stage 2 artifacts remain under `runs/stage2/`; historical details remain in
[stage2_handoff.md](stage2_handoff.md). Current verification: 103 tests pass, lint and
compileall pass. No weights, dependencies, upstream repositories or formal experiment
versions changed.

Ready to freeze `exp-e0-v0`: **NO**. Ready for formal E0: **NO**.
Next human review should settle the oracle-reference sanity pilot, target referent,
and multi-initial-state collection plan in [research.md](research.md).
