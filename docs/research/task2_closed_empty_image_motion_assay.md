# Fixed image-region motion after the closed-empty scene event

Freeze the smallest comparison that addresses the remaining alternative: **can
the empty gripper produce local image motion resembling the prior close-cell
signal when no bottle is in the closing region?** Use the physically matched
neck present/away pair described in
[the source design](task2_closed_empty_falsifier_design.md), freshly initialize
the same 492 raw pixel locations after each event, and track only the 25-frame
causal suffix. This is a fixed image-region assay. It is not a target tracker,
reidentification method or holding estimator.

This document freezes the feature design only. No future source, LK result,
feature, simulator call or model call was produced for it. The source producer
owns scene placement, event/cache/replay behavior and the independently
qualified mechanical negative. Collection and offline extraction remain
separate actions; an unproduced source cannot yet supply an admission hash.

## Why this is the cheapest defensible comparison

The prior assay used points descended from an initial bottle BOX. Carrying those
trajectories across a privileged relocation would entangle the tested suffix
with an exogenous correspondence jump. Selecting surviving tracks would change
the population. Instead, initialize the same numerical pixels independently in
both post-event images. No new grounding, texture detector, tracker setting,
mask, depth operation or identity classifier is needed.

The fixed pixel region is prior semantic support, not evidence of current
ownership. In the away cell it may contain background, robot or occluded pixels;
those are the contents whose local motion is being measured. Equal seed IDs
across cells denote equal image coordinates, not equal physical material points.
The comparison asks about the local signal under target presence versus absence,
while holding robot approach, commands and timing fixed as far as the source
records establish. It cannot make the post-event scenes visually identical.

## Fixed inputs, population and timing

Only the one prospective neck present/away pair is included. The source must
bind its clean code/protocol, closed journals, replay results and complete sensor
seal. The admitted observation stream must contain the same camera's native
384 × 384 uint8 RGB, saved camera intrinsics and camera-to-world matrix, and
saved own-TCP position with its actual own-packet provenance. Do not construct
FK, a model or a world to obtain a missing measurement.

The ordered seed grid is exactly:

```python
seeds = [[x, y] for y in range(169, 210) for x in range(212, 224)]
```

These are 492 native integer-center pixel-index locations, initialized in each
cell's **post-event image**. They are not transported from any old track and are
not adjusted after seeing the new images. All 492 begin as `seeded`, including
low-texture locations. Seeded status alone says nothing about correspondence.

The sole displacement reference is suffix capture 0, after the one declared
event synchronization/refresh and before the first GRASP control. Capture 1–24
is the existing auxiliary RGB stream after each of the 24 controls of
GRASP / GRASP / MV_UP, in order. No interpolation or through-event LK is used.
The separately recorded before/after event RGB remains source-setup evidence.

| Suffix capture | Boundary | Primary reporting role |
| --- | --- | --- |
| 0 | Post-event / preclose | Sole A/B displacement reference |
| 8 | End of first GRASP | Closing response |
| 16 | End of second GRASP / prelift | Same-exposure closed-jaw observation |
| 24 | End of MV_UP | Response after the fixed lift |

The 25-frame schedule retains the original per-control cadence through the
suffix. Record actual read times; never infer exact image sample times from
the expected control period. A forced event refresh does not prove timestamp
synchrony. Bind every RGB/K/T archive to its source stream, sequence, hash and
own packet. Missing/duplicate/misordered source captures are source-admission
failures, not permission to substitute another frame or extend a cell.

The agreed producer mapping selects `source_capture_stream="scene"` with
`source_capture_seq=2`, `phase="scene_after"`, `scene_boundary="after"`,
`after_step=29`, `control=null` as capture 0. Its own
source is `episodes.jsonl` / `scene_boundary` / boundary `after` / step 29:
the exact forced-refresh observation return assigned to `world.obs`. The
`after_step` field here identifies the intervention at the unexecuted suffix
step 29; it must not be mistaken for a completed GRASP. Captures 1–24 select
all auxiliary source sequences 1–24, with phases `close_or_hold`,
`additional_close` and `lift`, retaining `own_observations`,
`own_tcp_world_m` and their recorded source bindings. The `scene_before`
record is never a tracker input. Actual sealed records must match this mapping;
the producer's announced schema alone is not source admission.

The complete per-cell sensor manifest has 56 rows: 30 original reset/approach
captures, distinct before/after scene archives, then 24 auxiliary captures.
The suffix selects merged capture IDs 31–55 and reports endpoints 31/39/47/55
as local indices 0/8/16/24. Both source conditions retain `anchor="neck"` and
`arm="close"`; their exact condition/directory names are `neck-present` and
`neck-away`. The seal additionally binds `own-controls.json`; the motion
loader hashes that file without decoding it. The capture's
`render_preserves_state_and_caches=true` describes the individually guarded
capture after synchronization, never the preceding scene event.

The expected complete output is **984 trajectories / 24,600 rows**, with 492
rows at every capture in each cell. There are 23,616 potential forward steps
and at most 47,232 forward/backward LK calls; native failure may reduce actual
calls but never output rows. A missing or invalid own TCP affects B only and
must not delete an otherwise admitted RGB frame or A result.

## Frozen motion definitions

Use the existing single-seed RGB `track_lk` function unchanged, OpenCV 4.11.0,
and its native forward/backward status rules. Settings remain window 21 × 21,
maximum pyramid level 3, criteria `(3, 30, .01)`, flags 0 and minimum eigenvalue
threshold `.0001`. Preserve all nine native fields. Native failure is absorbing:
retain the attempted coordinates/status/error fields when defined and all
subsequent `unknown_after_native_failure` rows. Do not add an error threshold,
recovery, reseeding after capture 0, feature detector or cross-cell intersection.

Reuse the current image-motion arithmetic with reference index 0:

- **A:** `p[i] - p[0]`, where `p` is the native admitted RGB pixel coordinate.
- **B:** A minus `project(saved_tcp[i], K[i], T[i]) -
  project(saved_tcp[0], K[0], T[0])`.

B uses saved proprioception and calibration. Projection retains the established
edge-to-index subtraction of 0.5 and finite off-image projections. Neither
branch reads measured scene depth. A receives only native RGB records; B adds
saved own TCP and K/T. Source condition/event labels, privileged poses,
contacts, evaluator fields and any old 3D results do not enter feature functions.

Store the two vectors and projected TCP vector, plus the same four scalars:
`rgb_delta_v_px`, `rgb_delta_norm_px`, `rgb_minus_tcp_delta_v_px`, and
`rgb_minus_tcp_delta_norm_px`. Positive v means image-down. Invalid native
current/reference points make A and B null; unavailable current/reference TCP
projection makes only B null. A capture-0 zero is an initialized reference, not
measured evidence of attachment. Keep `identity_verified` and `holding` null.

Existing source identities to retain at implementation freeze:

| Source | SHA-256 |
| --- | --- |
| `point_temporal_probe.py` (`track_lk`) | `86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36` |
| `task2_point_anchor_image_motion.py` (pure motion helpers) | `3f3822e3609ccb3a1647d53e1d5b8143f04deb8c07b759d9d14919576672e19b` |
| `pixel_footprint.py` (pure camera transform) | `5559a4ee170e50f45295252b3db2b08553b3ba0a2b886e8bbe6cdbc50b15da8c` |

Reuse the pinned Python 3.10.21 / NumPy 1.26.4 runtime. The source-specific
adapter must eventually bind the actual new sensor filenames, schedule and
sealed hashes; this design does not invent them or authorize adapting the
population after outcomes. No old-source extraction is rerun for this proposal.

## Concrete offline wrapper and later source binding

The [extraction wrapper](../../embodied_runtime/experiments/task2_closed_empty_image_motion.py)
reuses those helpers. Its [synthetic tests](../../tests/test_task2_closed_empty_image_motion.py)
exercise the 56-to-25 selection, event/own binding, dropped/reordered/duplicate
captures, archive hash changes, RGB/K/T-only decoding, failure/null retention,
all 492 denominators and rejection before source access for an unreviewed binding.
No future source or feature is needed for these tests.

A later reviewed JSON binding must contain exactly this information (SHA values
and paths below are placeholders, not an admission):

```json
{
  "schema": "task2-closed-empty-image-motion-binding-v1",
  "source_admitted": true,
  "source_root": "/absolute/path/to/complete/physical/matrix",
  "matrix_journal_sha256": "<closed matrix journal SHA-256>",
  "source_admission": {"path": "/absolute/path/to/source-admission.json", "sha256": "<SHA-256>"},
  "source_review": {"path": "/absolute/path/to/independent-source-review.json", "sha256": "<SHA-256>"},
  "cells": {
    "present": {"directory": "neck-present", "condition": "neck-present", "sha256": {
      "sensor-captures.json": "<SHA-256>", "sensor-seal.json": "<SHA-256>"}},
    "away": {"directory": "neck-away", "condition": "neck-away", "sha256": {
      "sensor-captures.json": "<SHA-256>", "sensor-seal.json": "<SHA-256>"}}
  }
}
```

`preflight --binding BINDING --output RECEIPT` checks the clean frozen code,
pinned runtime, helper identities and bound sensor source; it decodes RGB/K/T
without calling LK or projecting TCP. After this source admission, the existing
independent one-batch review record binds `status="pass"`, the exact
`freeze_commit`, `protocol_sha256`, `binding_sha256`, `preflight_sha256` and
`authorized_batches=1`. This is the concrete receipt needed by
`run --binding BINDING --preflight RECEIPT --review REVIEW --output OUTPUT`.
The source-specific hashes remain external to the already frozen feature code.

The sole registered output is
`runs/autonomous-research/task2-closed-empty-image-motion-run-01` in the main
worktree. Existing output prevents rerun/resume. The wrapper retains failures,
partial rows and the closed journal on an interrupted attempt; a complete seal
requires both cells and all 24,600 rows. Source admission/review and mixed
journals are hash linkages only and are never decoded for feature selection.
No collection, preflight on a future source, extraction or model handoff is
released merely by committing this wrapper.

## Report and decision limits

Report all 25 captures for both cells, and the four endpoints above. Every
summary keeps denominator 492, native admitted/failed/unknown counts, A/B
available counts, and metric count/missing count, minimum, q25, median, q75 and
maximum. Quantiles use the existing linear method on available values; display
missingness beside them. Do not suppress a cell or compare only common survivors.
Dense neighboring seeds are dependent observations, not 492 trials.

Show complete native RGB frames with the fixed seed region and all defined
tracked positions at the four endpoints. Keep raw/native failure status distinct
from admitted coordinates. Draw full-population motion curves with the same
scales and denominator annotations. No extreme-seed search, favorable crop or
threshold/classifier fit is needed for this question.

Seal the sensor-only tracks/features before joining the source's separate
mechanical qualification. That qualification must establish what the away
condition actually did and report contacts, support and later target behavior
for present without assuming it was retained. If empty jaws remain moving at
prelift, report a same-exposure empty observation; do not rename it settled or
extend only that cell. This lane neither constructs mechanical labels nor uses
them to filter pixels.

The specific confound under test is **robot-local image motion being mistaken
for retained-target motion**. LK's 21 × 21 patch and pyramid support can include
finger edges, background and occlusion boundaries outside the seed's pixel or
the narrow ROI. Empty-cell co-motion would show that the local signal can occur
without a bottle in the closing region, within this source's tested conditions.
Differing motion would establish only a local descriptive difference. It would
not identify which visible surface was tracked or validate a holding estimator.
Failures or broad distributions are results, not a reason to add a tracker.

All displacements remain relative to post-event capture 0, so final values
include both closes and lift. The curve and named boundaries expose that
history; no independent lift-only reference or fitted endpoint is introduced.
Projection residual is not a calibrated rigid-attachment/slip error, and motion
along the camera ray may remain weak in RGB. No general depth-unnecessary,
grasp-quality or force-closure conclusion follows from this one matched pair.
