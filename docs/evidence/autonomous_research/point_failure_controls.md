# POINT failure controls: fresh inference and temporal correspondence

Two inexpensive controls localize the first semantic failure without changing
the live policy. The observed boundary-21 wrong point and boundary-25 malformed
output both reproduce in a fresh process, while independent RGB correspondence
can retain the visible target through the recorded episode. Neither result
establishes successful manipulation, calibrated uncertainty or reliable identity.

## Identical RGB in two fresh model processes

Frozen revision `ff4a57d`; six calls total, one pass in each fresh process:

| Order | Boundary | Cold first call? | Output | Matches original tokens and raw text? |
|---|---:|---|---|---|
| target_first | 21 | yes | completed point at drawer interior | yes |
| target_first | 20 | no | completed handle point | yes |
| target_first | 25 | no | 258 tokens, malformed, no EOS | yes |
| terminal_first | 25 | yes | 258 tokens, malformed, no EOS | yes |
| terminal_first | 20 | no | completed handle point | yes |
| terminal_first | 21 | no | completed point at drawer interior | yes |

Freshly processed image tensors, formatted text, token IDs, masks and image grids
exactly match their archived input before generation. Same checkpoint, BF16/eval,
query, greedy hybrid decoding and seed. No chat history, warm-up, source answer or
oracle variable is supplied to the model. Invalid generation is retained as an
offline outcome; subsequent registered calls continue without retry or salvage.

The preceding twenty model calls are not necessary for boundary-21 failure; the
preceding physical/inference history is also unnecessary for the malformed
boundary-25 output. This supports an image-specific failure in the fixed grounding
interface over cumulative inference-state contamination. It does not prove
universal statelessness or identify the internal neural cause. We do not tune its
prompt, generation limit or parser to hide the result.

## RGB correspondence against frozen-pixel baseline

Frozen revision `3411404`; OpenCV 4.11.0, one default LK configuration, eight
prospectively specified conditions, all 208 rows retained. The primary seed is
the first admitted sensor point. No depth, oracle geometry or labels enter the
tracker. All transforms and outputs reproduce in an independent CPU audit.

| Condition | LK after seed | Largest visible correspondence error | Frozen-pixel error |
|---|---|---:|---:|
| Original static-target sequence | 25 statuses OK | 0.001161 px | 0 px |
| Full image shift (+8,0) | 25 statuses OK | 0.001167 px | 8 px |
| Full image shift (0,+8) | 25 statuses OK | 0.001167 px | 8 px |
| Full image shift (-8,-8) | 25 statuses OK | 0.001167 px | 11.314 px |
| Target patch occluded | immediate reverse-status failure | unknown | no visibility claim |
| Off-target patch occluded | 25 statuses OK | 0.001344 px | 0 px |
| Target occluded + copied distractor | immediate reverse-status failure | unknown | no visibility claim |
| Wrong initial seed | immediate forward-status failure | no identity label | 62.394 px to primary |

The shift control shows correspondence uses image evidence beyond stale pixel
coordinates. Each shifted sequence contains one jump followed by near-static
frames, not 25 independent motion trials. For the two target occlusions the
**forward** native status remains successful; the reverse status fails. A forward
status alone would not have stopped these cases. A 31-pixel occluder hides the
local patch while pyramidal LK can use wider context. Native statuses and low
residuals are not calibrated visibility or identity probabilities. This wrong
seed happens to fail; textured wrong objects could still track reliably.

Independent review found the original recorder omitted attempted reverse
coordinates, including failed reverse calls. The original evidence is unchanged;
`reviewer_audit.json` records those outputs from a separately identified CPU
replay. Revision `a20c660` adds the missing raw field and a failure-propagation test
for future runs; it changes no propagation rule or prior result.

## Research decision

These controls earn separate semantic proposals and temporal correspondence as
research variables; they do not earn automatic replacement of a detector point
or a live recovery controller. Stopping on the known disagreement would be a
retrospective failure-localization result, not newly demonstrated competence.
Wrong but mutually consistent estimates remain possible.

The next high-information experiment returns to the proposed high-level visual
role: the same frozen VLM, full-camera RGB versus identical task text alone,
proposing local objectives on a small archived Task-2 visual contrast. Marker
verification failure does not logically imply high-level proposal failure. Labels
must describe visible evidence and preserve uncertainty about hidden grasp/fit.
No high-level proposal is execution authorization, and Task-2 strict physical
feasibility remains unresolved.

## Artifacts

Under `runs/autonomous-research/`:

- `point-replay-order-inputs-01/`: image-only extraction/native-input references.
- `point-replay-target-first-01/`, `point-replay-terminal-first-01/`: raw native
  inputs, generated tokens, complete outputs and summaries.
- `point-temporal-probe-01/`: transformed RGB arrays, all rows, contact sheet,
  independent audit script, numerical replay and interpretation.

The checked-in [summary](point_failure_controls_summary.json) preserves source
hashes, revisions, counts and numerical outcomes. Protocols and experiment modules
preserve the exact registered preparation, inference and evaluation conditions.
