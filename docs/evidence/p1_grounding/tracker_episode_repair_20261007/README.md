# P1 tracker episode repair and reference gate — 2026-10-07

**The separately registered drawer-front tracker initialization is TRACKED.**
The independent fixed cabinet reference remains UNKNOWN because its earlier
sealed POINT did not terminate with EOS. VERIFY/P1 task acceptance remain pending;
no new inference, action, PUSH, Qwen or Laya integration occurred.

## Implementation and controls

At clean `ab361eb`, the only behavioral code change is:

```python
tracker = VisualTracker(view["episode_id"])
```

The offline harness previously manufactured `surface-dev/{stem}`, causing
WRONG_EPISODE against the immutable recorded `p1-surface-dev/init25`. Captured
fields and the tracker identity guard remain unchanged. The previous failure is
preserved in the [typed-contract checkpoint](../semantic_contract_20261007/README.md).
The [new preregistration](../../../research/p1_tracker_episode_repair.md) fixes
one attempt on the same sealed pair and prior pinned RGB/support review, using
unchanged query/checkpoint/typed contract, BOX ROI, POINT, inventory seed and
geometry/tracker gates. A fresh output directory records command, revision,
source hashes, stdout/stderr and process exit. There is no recovery or retry.

## Actual result and image inspection

The retained independent BOX ROI again yields five measured supports. The POINT
again binds surface-0; its inventory is byte-identical to the reviewed prior
inventory. A support-contained rectangle is `[251.5,33,263.5,92]` pixels; its
original 1.2× template context has pixel edges `[250,27,265,98]`. Every context
pixel remains within that measured support. Actual raw RGB/seed inspection
shows the rectangle on the narrow outward drawer panel, away from the cavity.
See [seed and context on original RGB](tracker-seed-rgb.png).

The existing tracker returns:

| Field | Recorded result |
| --- | --- |
| status | TRACKED |
| episode | p1-surface-dev/init25 |
| depth support ratio | 1.0 |
| depth spread | 20.439 mm |
| unchanged maximum spread | 30 mm |
| reason codes | empty |
| age | 0, original offline capture clock |

This is **one-frame offline initialization**, not continuous temporal tracking,
live freshness, independent semantic identity, generalization or a safe push
patch. `semantic_identity_verified=false`, calibrated confidence unknown and
`for_execution=false` remain explicit. No temporal updates or new captures ran.

## Independent reference gate

Only after initialization passed did we register and inspect the separate
fixed-reference evidence from `surface-dev-gpu-20261006`. Existing sealed raw
requests/replies were hash-checked, matched to their original agentview image
and exact registered question, then parsed whole under the same typed contract.
BOX is admitted. POINT has **256 generated tokens, no terminal EOS** and fails
whole-reply admission with missing-EOS/inconsistent-completion errors. No point
prefix is accepted or used, and no reference geometry or tracker starts.

Root inspected the original agentview and existing BOX diagnostic: the broad
BOX covers cabinet top/side rather than an established fixed front-frame surface.
This does **not** prove that a fixed reference is absent from the camera image.
The demonstrated blocker is semantic-output completion; camera observability,
fixedness and a closed-state relation remain UNKNOWN. The historical failure
is neither overwritten nor relabeled as a new model failure. No model retry,
query change, token-limit change, annotation seed or official-success shortcut
was used.

Stop at `REFERENCE_POINT_INCOMPLETE_GENERATION`. The next research boundary is
independent fixed-reference grounding and observable reference relation, not
PUSH. Further model/decoder/query conditions were not run here.

## Evidence and validation

Actual sealed-input initialization passed; targeted Ruff and diff checks passed.
No new synthetic tests or broad suite were necessary for the one-line correction.
All 27 original source files, six drawer inference files and pinned prior review
verified unchanged before/after; existing reference inference hashes also match.
No historical failure, unique observation or canonical artifact was deleted.

[Summary](summary.json) · [Hash index](artifact-index.json) ·
[Portable evidence](tracker-episode-evidence.tar.gz).
Local raw condition: `runs/p1/tracker-episode-repair-20261007/`.
The unchanged full RGB-D source and previous drawer/reference model calls remain
in the linked [source](../surface_dev_20261006/README.md),
[drawer pair](../drawer_pair_20261007/README.md) and
[reference](../surface_gpu_diagnostic_20261006/README.md) archives.
