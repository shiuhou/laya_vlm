# Independent review of the corrected-v2 fixed-query evaluation

The first demonstrated bottleneck is **semantic association of a visible surface with the requested drawer subpart**. Geometrically valid planes and many generated points do not establish that the plane belongs to that subpart. No runtime action, model call, or simulator step was performed by this review.

The sealed experiment remains unchanged at `runs/p1/corrected-v2-fixed-query-evaluation-20261005`. The reviewer independently recomputed the complete prediction seal, reprojected every stored candidate from robot-base coordinates using its recorded camera calibration, and compared the resulting points with the annotation polygons. Counts agree with the original evaluator. All 100 responses are single boxes, terminate with EOS, and remain below the output limit.

## Results reproduced

| Condition / camera | Geometry results | Candidate projections |
|---|---|---|
| Model drawer ROI, wrist | 16 VALID, 6 AMBIGUOUS, 3 UNKNOWN | 23,043 total; **0 inside** annotated drawer-front regions |
| Human-mask drawer diagnostic, wrist | 25 VALID | 130 total; **130 inside** annotated regions |
| Model drawer ROI, agentview | 24 UNKNOWN, 1 AMBIGUOUS | 0; drawer labels are UNKNOWN in all 25 views |
| Model reference ROI, agentview | 25 UNKNOWN | 0 |
| Human-mask reference union, agentview | 25 AMBIGUOUS | 0 |
| Model reference ROI, wrist | 22 AMBIGUOUS, 1 UNKNOWN, 2 VALID | 3,032; reference labels are UNKNOWN, so these points are not scored as correct or incorrect |

Drawer visible-label mean IoU is **0.0449852**. Median coverage of the conservative visible polygon is 1.0, while median fraction of model-box pixels outside that polygon is **0.9748254**. Large boxes can cover the intended patch while overwhelmingly including other surfaces. Reference mean IoU is **0.5553500**, with the interpretation caveats below.

The evaluator's 1.0 visibility accuracy has little discriminative value here: all known labels are VISIBLE, all model responses contain a box, and UNKNOWN labels are excluded. This dataset does not test a NOT_VISIBLE negative class or establish reliable model abstention.

## Earliest concrete boundaries and inspected RGB

The contact sheet contains raw RGB, annotation/model-box overlays, all semantic-ROI geometry points, and human-mask geometry points. Orange denotes annotation polygons, magenta model boxes, and cyan projected points. Every point is displayed; the visualization does not select a preferred candidate.

- `call-000`, init 0 agentview drawer: the model rectangle includes the open cavity/assembly. Geometry stops with insufficient plane support. Its human drawer label is UNKNOWN, so the annotation cannot establish a semantic false positive here.
- **`call-002`, init 0 wrist drawer: first drawer example with a VISIBLE label.** The model box `[243.84, 0, 383.232, 110.336]` includes the cavity and surrounding assembly, rather than isolating the narrow outward-facing patch. IoU is 0.08437. Geometry correctly abstains because two depth components have comparable size. The unchanged human-mask diagnostic yields a VALID patch and six interior candidate projections. This isolates an input-region association problem before motor selection; it does not prove a perception implementation can recover the human region automatically.
- `call-006`, init 1 wrist drawer: the box selects the bottom robot/image bar, visibly disconnected from the drawer. Geometry returns UNKNOWN. This is an unambiguous visual localization error in the inspected evidence.
- **`call-010`, init 2 wrist drawer: first VALID model-derived drawer patch.** All 36 points project onto the cavity/interior region, not the annotated front. The nearest is more than 30 pixels from the annotation boundary. VALID here describes geometric fit, not task identity.
- `call-014`, init 3 wrist drawer: the near-full-frame box yields 1,538 points across the tabletop. They all lie outside the annotated front. `call-098`, init 24, repeats this behavior with 1,614 points.

These are direct image observations, not diagnoses inferred only from IoU. Nevertheless, annotations are conservative subsets: **outside a polygon does not by itself prove an invalid semantic surface**. The selected raw RGB provides the stronger evidence for cavity/table/robot-bar substitution.

## Separate post-registration reference diagnostic

The original reference upper bound combines two disjoint human polygons: cabinet top and cabinet side. Treating their union as a single unambiguous local patch produces AMBIGUOUS in all 25 views.

After the original condition was sealed, the review reran the same frozen geometry **on each supplied reference polygon separately**. This is explicitly an evaluator-only, human-conditioned, post-registration diagnostic; it is not part of the original experiment or a deployable selector.

- **50 / 50 individual polygons yield VALID geometry.**
- Their 6,850 candidate projections all lie inside the respective polygon.
- In init 0 the top-plane normal is approximately `[0.0040, 0.0000, 1.0000]`, while the side-plane normal is `[1.0000, -0.0018, -0.0035]`: these are different surfaces, not a single failed plane.

Thus the union failures **do not support the conclusion that usable local cabinet geometry is unavailable**. They expose a mismatch between a multi-surface semantic region and a single-patch geometric representation. No winning polygon was chosen, no threshold changed, and no resulting point became an executable action.

## Limits on interpretation

1. The frozen reference query asks for the fixed **front-facing frame** immediately around the drawer. All 50 visible reference polygons instead have type `ADJACENT_FIXED_BODY`, covering top/side surfaces. This query/label granularity mismatch limits conclusions from reference IoU and outside-polygon counts. Neither query nor labels were tuned after observing results.
2. No frame has both entities marked VISIBLE: drawer labels are visible only in wrist images; reference labels only in agentview images. Cross-view or temporal relation validity remains untested.
3. All 25 agentview reference polygon sets are identical. Different benchmark inits do not constitute 25 independently posed cabinets or diverse viewpoints.
4. Human-label independence is **project-user-reported**, with the original contradictory metadata and its correction preserved. The software and this reviewer did not independently authenticate the annotator or their exposure history.
5. Even the human-mask and per-polygon VALID results do not establish reachability, collision safety, task interaction validity, static-reference identity, or successful manipulation.

The evidence supports improving and testing semantic surface association before attempting P2 manipulation. It does not support modifying Laya, planning depth, action vocabulary, controller semantics, or geometry thresholds in response to these results.

## Artifacts and reproduction

- `independent-review.py`: model-free audit, reprojection, original mask comparison, separate per-polygon diagnostic, and contact-sheet generation.
- `independent-review.json`: source/seal hashes, all 100 call-level measurements and summary.
- `independent-contact-sheet.jpg`: seven selected boundaries, actually inspected by the reviewer.
- `independent-reference-polygon-diagnostic.json.gz` (lossless compressed archive): all 50 post-registration per-polygon results, explicit evaluator provenance, unchanged geometry hashes.

From repository root: `.venv-p1/bin/python docs/evidence/p1_grounding/corrected_v2_evaluation_20261005/independent-review.py`. Outputs use exclusive creation; existing evidence is not overwritten. For a fresh rerun, copy the script to a new sibling review directory under `docs/evidence/p1_grounding/` before invoking it.
