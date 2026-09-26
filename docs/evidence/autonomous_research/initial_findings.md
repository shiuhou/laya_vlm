# First autonomous research findings — 2026-09-26

These are offline development diagnostics, not a new manipulation success.
Baseline `b73b5b4`; protocols and research memory are linked from
[the research log](../../research/autonomous_research_log.md).

## Predicate recognition is not yet a reliable escape from action ranking

The preregistered experiment completed all 768 calls from frozen code `dee27ea`:
704 binary judgments and 64 unchanged eleven-option controls. All source controls
reproduced choices, rounded probabilities and raw logits exactly. All repeat pairs
were identical. Input/forward-token checks and the independent numeric/text auditor
passed; no truncation, malformed output, missing call or hidden retry occurred.

First-repeat binary results (answer orders are correlated conditions):

| Requested goal | True positive | True negative | False positive | False negative | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| Closed | 68 | 33 | 75 | 0 | 65.28% |
| Open | 28 | 0 | 148 | 0 | 50.00% |
| Both | 96 | 33 | 223 | 0 | 56.45% |

Laya returned `satisfies` in 319/352 judgments, including every open-goal case.
Ordinary accuracy was 129/352 (36.65%); class imbalance makes balanced accuracy
and specificity important. Eleven of 176 paired answer orders changed the answer.
These are variants of four physical contexts, not 352 independent scenes.

For closed goals, 35/36 candidates with the right absolute direction but wrong
STOP-relative progress were accepted. For open goals, all 124 candidates failing
both direction clauses were accepted. Example: `opening decreases; vs STOP lower;
obstacle no` was judged to satisfy the opening goal. Raw affirmative margins were
not merely numerical ties. All obstacles were false, so obstacle-veto understanding
was not tested.

**Observed:** removing multi-option competition did not establish reliable
predicate verification under this fixed presentation. **Inference:** a high-level
planner cannot be assumed to fix the downstream interface simply by supplying a
desired consequence. **Unresolved:** criterion parsing, task framing, affirmative
bias, and the negative label `does_not_satisfy` remain competing explanations.
This does not prove that every binary interface, or Laya generally, must fail.

Next registered discriminator: separately change only the negative-label spacing,
then test the absolute and STOP-relative clauses with fixed instructions. Deduplicate
identical model inputs while retaining every parent lineage. No live controller
will be constructed from these binary judgments.

## Point-cloud membership matters more than depth residuals in these views

The CPU-only support audit reconstructed all 18 accepted RGB-D/raycast pairs
exactly, including historical median-depth proxy, sensor surface centroid and
independent oracle surface centroid. No missing boundary was removed.

The full-box surface centroid has median error 79.20 mm. An evaluator-only vector
decomposition gives median support-membership component 75.21 mm and same-support
ray/render-depth component 3.37 mm. The support component is larger in 18/18 cases.
It includes contamination and missed coverage; shared calibration prevents an
independent calibration-validity claim. The historical median proxy estimates a
different quantity and is not scored as a competing surface-centroid estimator.

All simulated observation ages are zero despite 1.48–4.75 seconds of wall time
between capture and paired input. This is paused-simulator evidence, not a real-time
robustness result. Every covariance remains explicitly uncalibrated.

## Better centroid accuracy does not automatically produce better decisions

A second preregistered CPU experiment separated the nearer side of the largest
valid depth gap inside each existing box. The fixed rule used only sensor depth;
no oracle masks, threshold tuning, learned segmentation or model inference.

| Measurement, 18 development boundaries | Full box | Near-depth support |
|---|---:|---:|
| Median visible-surface centroid error | 79.20 mm | 9.06 mm |
| Maximum error | 101.42 mm | 91.80 mm |
| Median target pixel purity | 49.43% | 63.24% |
| Nominal preferred-direction agreement | 10/18 | 12/18 |
| Preferred direction reduces true geometric distance | 15/18 | 15/18 |
| Worst nominal directional regret | 8.60 mm | 8.60 mm |

Direction comparisons use six nominal 10 mm translations plus hold, not executed
controls or an expert manipulation policy. All 18 centroid errors improved, yet
three adverse nominal directions remained. RGB/support plots show why: late views
merge the drawer panel and several handles in the same near-depth layer. Nearer
does not mean the requested semantic target. This earns further semantic-grounding
measurement, not production integration or claims about grasp poses.

The existing LocateAnything checkpoint supports point grounding. A matched full-RGB
BOX/POINT diagnostic can test semantic target identity without adding a VLM model.
It must preserve empty, malformed, multiple and out-of-image outputs, and evaluate
points against the visible target surface rather than its centroid.

## Provenance, reproduction and limitations

Tracked summaries contain raw artifact hashes:

- [Predicate verification](predicate_verification_summary.json).
- [Perception support](perception_support_summary.json).
- [Depth support](depth_support_summary.json).

Raw artifacts are local under `runs/autonomous-research/`; they are not included
in a fresh clone. CPU probes recorded source hashes and dirty-worktree status
before their isolated commits; their source files were unchanged on commit.
The GPU experiment used a clean detached `dee27ea` checkout, GPU 0, frozen local
Laya weights, and a separate completed preflight. The archived GPU ordinal was 1;
this difference is recorded and all unchanged controls nevertheless match exactly.

The baseline 441 tests passed. With these experiment/audit modules, 531 tests and
Ruff pass. One sandboxed full-suite attempt failed at robosuite/Numba cache access;
the same suite passed outside the sandbox without a code/configuration change.
No shared runtime, executor, model setting, primitive or frozen task was changed.

Next steps are empirical: clause/answer-form separation, unchanged current-interface
reproduction, and existing-model point grounding. There is no evidence yet that a
new high-level VLM planner is the dominant missing component.
