# Iteration 002: downstream decisions and visual target identity

These are development diagnostics. No robot controls were executed and no new
architecture or manipulation competence is claimed. Historical execution code,
TaskAdapters, model settings and evidence are unchanged.

## Current motor evidence is reproduced, not repaired

The five boundaries selected before inference were 0, 1, 9, 10 and 87: first two
genuine choices per objective plus first lookahead. Two repeats give ten calls.
All choices, probabilities and logits match the canonical successful archive
exactly. Complete token consumption and output membership pass.

| Boundary | Objective | Pool | Laya choice | Supplied progress of choice | Illustrative available alternative |
|---|---|---:|---|---|---|
| 0 | approach_target | 7 | x+40mm | gap reduction 29.11 mm | selected action has maximum gap reduction |
| 1 | approach_target | 7 | x+40mm | gap reduction 15.70 mm | z−40mm: 23.01 mm |
| 9 | advance_target | 25 | open | closure 1.755743 mm | y−40mm: approximately 34.177 mm |
| 10 | advance_target | 16 | open | closure 0.056385 mm | y−40mm: approximately 31.888 mm |
| 87 | reposition | 25 | open | witness net closure 0.515422 mm | rotate_y−10: approximately 28.510 mm |

The approach instruction asks for substantial improvement, not a strict maximum.
Witness effects at boundary 87 are hypothetical subsequent actions, not executed
commands or guaranteed future outcomes. At boundaries 9/10 the compared immediate
alternatives do not have worse contact/obstacle/success/horizon fields. Nevertheless,
immediate superiority does not establish a better full trajectory. All admitted
candidates are already contract-positive; binary admissibility on this pool would
be uninformative. The source trajectory is not designated interaction-valid.

## Predicate decomposition fails to establish effect discrimination

Seventy-four unique inputs preserve all 176 source lineages. Four conditions,
two answer orders and two repeats produce 1,184 calls. All 592 repeat pairs and
704 original-response comparisons match exactly. Independent token, raw-logit and
checkpoint binary-temperature audits pass.

| Condition | Closed balanced accuracy | Open balanced accuracy |
|---|---:|---:|
| Original full rule / underscored label | 65.18% | 50.00% |
| Full rule / spaced label | 50.00% | 50.00% |
| Opening clause only / spaced label | 50.00% | 50.00% |
| STOP-relative clause only / spaced label | 50.00% | 50.00% |

In every spaced-label condition, the model answers negative for every closed-goal
input and positive for every open-goal input. Different pooled balanced accuracies
reflect label prevalence across goals, not successful clause reasoning. The corpus
also has incomplete Boolean coverage: closed full truth equals STOP-relative truth,
and open full truth equals opening-clause truth. It cannot identify general
conjunction ability. Further prompt micro-tuning on this corpus is not the next
experiment.

## POINT helps early views but does not resolve late target identity

Same full RGB, query phrase, LocateAnything checkpoint and generation settings;
only the supported BOX versus POINT template changes. All 36 calls are preserved.
An independent CPU audit re-decodes every actual generated token sequence and
checks target membership against evaluator-only masks.

| Output | Target hit | Miss | Unknown | EOS complete |
|---|---:|---:|---:|---:|
| POINT | 9 | 5 | 4 | 18/18 |
| Fresh BOX center | 1 | 7 | 10 | 8/18 |
| Historical first-box center | 1 | 17 | 0 | not historically audited |

All fresh first-box prefixes equal the archives. Nine BOX generations repeat to
260 tokens under the nominal 256-token hybrid generation cap; one is malformed
without EOS. Prefix extraction concealed this incompleteness. Do not conflate
strict output coverage with semantic membership or salvage mixed outputs after
seeing their labels.

All six registered late frames fail strict POINT evaluation: three mixed outputs,
three misses. Root and independent auditor inspected the RGB overlays. Two points
clearly select a lower handle, 22.10 and 30.53 pixels from the designated top-handle
mask. The third is a 1.26-pixel boundary miss. Three other misses across the whole
set are near boundaries, not all distinct-object confusions. POINT estimates are
not grasp poses, shapes, collision certificates or calibrated uncertainties.

Attempt 01 failed before model generation because model metadata contained a
non-JSON torch dtype. The preserved attempt was followed by a localized metadata
serialization fix and separately recorded attempt 02. No model, prompt, parser or
runtime behavior changed to obtain attempt 02.

## Artifacts and next decision

Raw evidence is local, not included in a clone:

- `runs/autonomous-research/current-motor-replication-01/`
- `runs/autonomous-research/predicate-decomposition-run-01/`
- `runs/autonomous-research/point-grounding-probe-01/` (pre-inference failure)
- `runs/autonomous-research/point-grounding-probe-02/`

The tracked `iteration_002_summary.json` preserves report hashes and independent
audit summaries. Grounding run 02 used clean revision `6436678`; predicate and
motor experiments used the separate frozen verification worktree. Their manifests
retain exact source, code and environment identities.

Next: apply the existing local Qwen text provider to the five unchanged current
motor fixtures. If it uses the evidence better, the provider/interface boundary
deserves reconsideration before adding planning. If not, distinguish output-format
failure and underspecified ranking from missing physical information. Independently
assess whether an already available vision model can contribute target identity
on difficult frozen RGB views; no VLM runtime or new perception model is earned yet.
