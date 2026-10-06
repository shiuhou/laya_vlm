# P1 typed semantic-output repair — 2026-10-07

**Typed surface association passes the bounded development gate. Tracker's first
initialization attempt stops at an experiment-harness `WRONG_EPISODE` error.**
No fixed-reference stage, new inference, retry, PUSH, Qwen or Laya followed.
P1 task acceptance is still pending.

## Versioned contract

[Preregistration](../../../research/p1_semantic_output_contract_repair.md)
committed at `c31b622` fixes the rules before new-condition reanalysis.
`dbeacd9` implements `p1-semantic-output/typed-v1`; the legacy parser/default
remain unchanged. Each complete reply retains ordered POINT/BOX/NONE atoms,
full raw text/spans, native coordinates, pixel coordinates, generation audit and
unknown calibrated confidence. Whole-reply syntax, EOS/token integrity,
cardinality and coordinate checks precede geometry. Malformed auxiliary evidence
also rejects admission; no valid-prefix salvage exists.

POINT requires exactly one POINT; its auxiliary BOX atoms survive as evidence
but never become ROIs, constraints or fallbacks. BOX preserves all BOX atoms in
original order; its POINT atoms cannot seed association. Only the separate BOX
call defines search regions. Sources and exact registered requests must match.
Neither typed admission nor geometry establishes verified semantic identity.

`924b987` adds a pinned prior RGB/support review requirement for a separate typed
tracker stage. `3e5bd6a` additionally rejects oversized numeric text before
conversion; native coordinate rules are unchanged. No production runtime,
tracker, geometry/association implementation, query, checkpoint or gate changed.

## Matched sealed-output result

The exact init25 wrist pair sealed in `f2af8d8` was reused. No model call occurred.
All 27 original source files and six sealed inference files verified unchanged
before and after the run. Same RGB-D, calibration, independent BOX ROI and
inventory seed zero; no evaluation annotation or simulator truth was read.

| Boundary | Legacy condition | New typed condition |
| --- | --- | --- |
| Full POINT reply | Complete mixed POINT+BOX, rejected | One POINT admitted; one auxiliary BOX retained |
| ROI | Not analyzed in corrected legacy stage | Separate BOX call only; one ROI |
| Geometry | Not evaluated in corrected legacy stage | Five supports; one matching valid support |
| Association | UNKNOWN | BOUND_HYPOTHESIS, surface-0 |

Anchor: `[257.664, 62.976]`, sampled at `[257, 62]`. Selected support has 2,625
pixels, RMS **0.940 mm**, normal approximately `[0, 1, 0.023]` and unchanged
`plane_valid=true`. Root and an independent reviewer inspected original wrist
RGB, support overlay and same-capture agentview RGB. They interpret the selected
narrow vertical, handle-adjacent outer panel as the requested drawer front;
the larger horizontal support is cavity/interior. This is development visual
inference, not independent human annotation or a certified executable patch.
`semantic_identity_verified=false`, `for_execution=false`, and uncalibrated
confidence remain explicit. Partial image clipping remains visible.

See [actual support/anchor overlay](drawer-front-support.png). The full reply,
auxiliary atom and every retained support/residual are in the archive.

## First new failure: tracker harness identity

A separate tracker registration pinned the reviewed association and unchanged
gates before one attempt at clean `3e5bd6a`. The analysis harness constructed:

```text
tracker episode: surface-dev/init-025-drawer_front_pushable
recorded episode: p1-surface-dev/init25
```

`VisualTracker.initialize → _frame` raises `WRONG_EPISODE` before template
initialization, appearance/depth checks, generation increment or TRACKED/LOST
result emission. The erroneous constructor already existed at `f2af8d8`; the
typed repair merely reached it for the first time. This is an experiment-harness
provenance mismatch, not evidence that tracker geometry or appearance fails.
The partial attempt inventory is byte-identical to the reviewed inventory.
Independent read-only audit confirms the cause and preserved gate/source bytes.
The attempt stops here: **zero retries, no repair-and-rerun, no reference stage**.

The failure observation is explicitly agent-recorded from the command's exit1
and traceback, rather than presented as a worker-emitted terminal report. The
original tracker directory contains only the partial inventory. Both are
preserved. Fixed-reference observability and VERIFY remain UNKNOWN; drawer
association does not supply a cabinet reference or a closed-state relation.

## Verification and next boundary

56 distinct focused tests passed: current schema/review tests33 and existing
parser/association regression tests23. Initial CPU regression had one unrelated
failure because Torch is absent there; that same existing dtype-serialization
test passed in the checkpoint's LocateAnything environment. Ruff passed. No broad
suite or GPU experiment ran. Historical evidence was not overwritten.

The next engineering boundary is to correct the harness episode identity to the
recorded episode, then separately register a tracker initialization replay of
these sealed inputs. Do not retune queries/gates, infer fixedness from this
surface, or skip directly to manipulation. No such fix or rerun is included here.

[Summary](summary.json) · [Hash index](artifact-index.json) ·
[Portable evidence](typed-contract-evidence.tar.gz).
Raw local condition: `runs/p1/semantic-contract-typed-20261007/`.
The unchanged original full RGB-D source remains in the
[previous source archive](../surface_dev_20261006/README.md).
