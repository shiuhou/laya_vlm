# Formal-50 frozen perception evaluation

Prospective condition `p1-formal50-native-masks/1`, starting checkpoint `25f1e4a`.
The frozen entry is
`docs/evidence/p1_grounding/mask_support_reanalysis_20261007/formal50-evaluation-entry.json`.
Its ordered 50 frames are 25 agentview and 25 wrist views, each 384×256,
from init0–24. Init25/26 development tuning is closed.

## Generation boundary

Only original recorded RGB, existing drawer BOX records, locked SAM2.1 tiny,
recorded metric depth/K/T and whitelisted EEF proprioception are used.
No annotation JSON is parsed before both native-mask and geometry stage seals.
Registration includes frozen annotation identities, not annotation values.
Existing reference BOX records remain provenance, not SAM inputs this round.
Zero LocateAnything calls. Frozen RGB/query/BOX/model/decoder/geometry settings
and lexicographic candidate ordering are never tuned against this set.

Invoke each stage once. Native FP32 SAM settings, deterministic grid overlay,
checkpoint/source/dependency identities match the frozen development condition.
All native ordinal0/1/2 masks, logits, low-resolution logits and predicted IoUs
are retained. Predicted IoU is uncalibrated and never selects a winner.
Image encoding happens once per input; every admitted BOX is decoded once.
Any failed encoding/prediction is retained without retry. Independent remaining
inputs continue if the process can do so; catastrophic process failure stops.
Exclusive output paths prevent replacement of the first attempt.

Full native-mask availability is valid finite/in-range depth inside mask divided
by all mask pixels. Mask/BOX coverage is a separate diagnostic. Fitting still
uses the original BOX with depth outside mask UNKNOWN. No component, plane,
mask or point selection using labels; no largest/nearest fallback. Existing
dominance-or-abstention component policy is unchanged. All stage metrics and
first rejection reasons are retained. A rejected stage leaves downstream stages
NOT_EVALUATED, not evidence of downstream impossibility.

## Blind scoring

After verifying generation seals, independently verify the frozen annotation
hash/rules/image bindings before reading it. Preserve human VISIBLE, UNKNOWN,
NOT_VISIBLE separately. UNKNOWN is neither a visible positive nor a negative.
BOX coverage/contamination are continuous diagnostics; intersecting a label
does not imply complete grounding. Report zero-overlap, partial, full coverage
and their VISIBLE denominators, without inventing a tuned coverage gate.
Mask overlap/purity are continuous, evaluator-only measures; no selected mask.

Keep geometry-stage taxonomy and label identity evidence separate. Zero mask
overlap with a VISIBLE region is an identity failure. Every candidate projected
outside a VISIBLE region is SEGMENTATION_IDENTITY_FAILURE even if geometric
gates passed. Inside-region candidates are task-valid geometric evidence only;
UNKNOWN action usability/calibration/reachability remains UNKNOWN. Geometric
VALID with zero tool-interior candidates is not a valid drawer-front candidate.
Any-mask frame coverage is an evaluator statistic, not runtime mask selection.

Report all masks, ordinal distributions, first-boundary taxonomy, camera totals,
candidate counts/positions relative to annotation, and failures. Encoding,
decoding, encoding+decoding and per-mask geometry p50/p95 are isolated offline
workload timings, explicitly not continuous end-to-end Hz. Model startup,
record replay, serialization and evaluation are outside these timing windows.

## Stop and next decision

Stop after scoring, all-frame evidence inspection, report and checkpoint.
No temporal capture/tracker experiment, reference POINT repair, PUSH/P2,
Qwen or Laya. Status: **P2 remains blocked pending Formal-50 / temporal P1 gate**.
Compare formal evidence with the already frozen static gate (correct identity
and tool-interior evidence in at least20/25 inits, wrong admissions0), but do not
declare a final P1 Gate A/B/C without temporal qualification. The distribution
determines the next proposal: temporal evaluation, one justified interface
repair, or sensing/viewpoint reconsideration. No next experiment this round.
