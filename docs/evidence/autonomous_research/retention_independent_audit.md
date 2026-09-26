# Independent retention-evidence audit

2026-09-27. The paired interaction diagnostic passes all **30 independent
offline checks**. Its strongest result remains visible bottle-body co-motion
in the close arm and a stationary body point in the open arm. This audit adds
two useful qualifications: the recorded pad-relation flicker retains contact on
both physical fingers, and the failed tabletop optical-flow point still has a
stable, directly measurable depth-plane neighborhood. Neither result establishes
a general retention decision. Runtime `holding` remains `None`.

## Integrity and provenance

The independent auditor imports neither the collector nor its tracking/report
functions. It verifies all **188 sealed sensor artifacts**, 71 collection-source
and 73 replay-source hashes against their frozen Git objects, the archived
primitive source, all image-array/hash/read-time relationships, the seed chain,
all 104 shared-prefix sensor records and 14 RGB hashes, and both existing report
artifact manifests. Independent OpenCV LK calls reproduce the published point
coordinates, native statuses and forward/backward residuals exactly. Direct
RGB-D backprojection reproduces all 134 admitted surface-point estimates exactly.
The archived empty-close source hash and records 26 and 54 also match.

All 272 recorded replay entries reference the expected control and simulator
time and report zero error against the original 51-value states. This audits
the completed replay and its frozen code; it does not execute a second replay.
The replay saved per-step maximum errors rather than full actual replay-state
arrays. No new simulator world or physical trace was created by this audit.

The seed-freeze time precedes the first close-control sensor read. Source review
shows the physical sequence pauses for annotation, seals sensor artifacts before
writing buffered evaluator labels, and separates sensor analysis from evaluator
reporting. Current file timestamps corroborate that order. Hashes and local
timestamps do not independently prove the absence of out-of-band reads.
`seed-frozen.json` lies outside the 188-file sensor seal; its contents currently
match the sealed `seed.json` exactly. The audit records its own hash.

The append-only erratum correctly attributes seed selection to the **Codex
assistant**, rather than a human. The run does **not record an exact model
identifier, conversation/session identifier or image tool-call record**. The
specific annotator model therefore cannot be independently verified from these
artifacts. That provenance gap must stay visible; model identity is not inferred
from the current auditing assistant.

Wrench and returned-observation sample timestamps remain explicitly unknown.
The largest returned-versus-direct finger encoder difference is **0.191965 mm**.
The recorded RGB-D time is a render/read time, not proof of the exact sample time
of cached derived geometry. Visual evaluator masks identify visible rendered
geometry and do not establish physical support completeness.

## What the first failures mean

The auditor personally inspected the raw RGB trajectory and the first-error
RGB/segmentation crops. In the open arm, cap capture 27 (step 14, control 5)
crosses the visible bottle-mask boundary at the sampled containing pixel while
native LK still succeeds with a **0.001176511 px** round-trip residual. The
previous sampled pixel remains on the bottle. The later large depth jump at
step 15, control 0 is a symptom after that first sampled-support failure.
The boundary image does not establish that every pixel in LK's patch has lost
the bottle, or identify the replacement sampled geometry.

The close-arm body rises **109.810 mm**, the open-arm body remains at **0 mm**,
and the body stays within visible bottle geometry for all 33 frames per arm.
These findings and the raw lift images support the limited co-motion claim.

At close-arm step 16, controls 0–3, the named bilateral **fingerpad** relation
is false. The saved contact rows nevertheless include the bottle touching
`gripper0_finger1_pad_collision` and `gripper0_finger2_collision` throughout.
The second finger's non-pad normal force is **12.246–13.099 N**. The bottle
center rises from **1059.321 to 1081.894 mm** over those four samples. All contact
rows use the task's **0.05 N** reporting filter. This interval is evidence of
designated pad-relation failure while physical contact persists on both fingers;
it is not evidence that both fingers released the bottle or that it dropped.
Changing the task's interaction criterion is a separate design decision.

## Frozen exploratory table-plane probe

The [protocol](../../research/retention_support_plane_probe_protocol.md) and
implementation were committed at `f98b10f` before numerical plane fitting.
The analyst had already seen the outcomes and evaluator labels. The analysis
is explicitly **post-outcome exploration** on the existing 66 correlated frames.
Its fixed 31×31 patch surrounds the original table seed `(171,290)`; the radius
was selected for this follow-up. No new seeds, threshold fitting, outlier removal,
point recovery, oracle input or new physics were used.

All 961 patch depths are valid in every frame. RGB, depth and calibration remain
bit-identical to the seed across both arms. A total least-squares plane fit has
**0.001284 mm RMS** and **0.002919 mm maximum** residual in every frame. Its
world normal is approximately `(0.0006013, 0.000000152, 0.999999819)` and signed
offset is `−0.900613879 m`. These tiny residuals describe internal planarity of
an unchanged ideal simulator depth patch; they do not establish physical sensor
accuracy or independent calibration accuracy.

Using OpenCV's minimum-eigenvalue reporting flag on the first transition, the
original table point has minimum eigenvalue **0.0000492905**, below the frozen
`0.0001` threshold, and forward status 0. The cap and body values are 0.292259
and 0.491232 with forward status 1. This explains why the original native tracker
rejects the table point despite its stable RGB-D neighborhood. The original
failed track remains unknown; the plane is a separate, explicitly initialized
geometric observation.

| Surface landmark distance to the fitted seed plane | Before close | After third lift |
|---|---:|---:|
| Close-arm bottle-body track | 18.237 mm | 128.046 mm |
| Open-arm bottle-body track | 18.237 mm | 18.237 mm |
| Open-arm cap track, including its known failure | 153.923 mm | −0.048 mm |

The erroneous cap output is preserved. A stable table reference does not repair
the identity failure. An interior body-point height is not bottle-bottom
clearance, and a visible table patch does not exclude support by another object.
Consequently automated object/support separation and retention remain unvalidated.

## Next physical decision

The evidence now earns using a separately initialized depth plane as a candidate
support-reference channel in a future fixed-camera diagnostic. It does not yet
earn a same-closed-command slipping or supported-object physical condition:
the audited pad flicker is not such a negative case. Before collecting that
comparison, mechanically establish how the fixed native primitive sequence will
produce supported/slipping motion while matching the jaw command, and freeze
identity and support measurements before its outcomes. A missed grasp after an
arbitrary lateral offset would add an empty-close comparator but would not test
support-induced co-motion. No mass, friction, seed or native controller change
is justified by this audit.

Raw evidence in the main workspace:

- `runs/autonomous-research/retention-audit-01/audit-complete.json` and its
  independent script; initial 27-check audit remains preserved separately.
- `runs/autonomous-research/retention-audit-support-plane-01/`: frozen protocol,
  script, freeze record, sensor results/seal, artifact hashes and visible patch
  overlays. The sensor-only script never reads evaluator files.
- [Portable audit/probe summary](retention_independent_audit_summary.json).

Validation: both standalone audit executions passed (27, then 30 checks after
adding portable anchors and the archived width fixture); the single frozen
plane-probe execution completed across all 66 frames. Python compilation and
repository whitespace checks passed. No production runtime files changed.
