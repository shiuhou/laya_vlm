# One offline human-region geometry upper-bound diagnostic

Baseline `e8cda1e` and its exposed development evidence stay frozen. No new
LocateAnything POINT, SAM prompt, query, decoder, model inference or threshold
work. One diagnostic, 25 frozen VISIBLE wrist frames, init0–24, original384×256.

Question: if frozen human target-part support replaces uncertain learned identity,
does unchanged observed RGB-D geometry admit any tool-interior candidates?
Competing explanations: identity is the primary actionable blocker; or existing
geometry/tool support/viewpoint remains insufficient even with human support.

Human annotations are deliberately read by this **offline-only counterfactual**.
They cannot enter policy/runtime and cannot count as perception performance.
"Upper bound" means the practical human-region support condition, not a
mathematical maximum over all sensors/methods or perfect annotation certainty.
The set was already exposed; this is development evidence, not held-out acceptance.

Inputs: original Formal-50 sensor records/calibration and frozen annotation/rules.
Use all25 wrist VISIBLE regions without selection. Rasterize with original
polygon_mask at x+.5,y+.5, union all supplied polygons, no dilation/erosion,
shrinking, filling or relabeling. Preserve original depth exactly inside the mask;
outside becomes UNKNOWN. Separate original sensor and derived masked-depth hashes.

Bypass learned BOX/SAM as part of the identity intervention. Fit over the complete
original frame domain with only human-region depth support, never clip to a wrong
archived BOX. This prevents residual BOX identity failure from contaminating the
geometry upper bound. Depth availability uses valid in-region depth / human-region
pixels, the already frozen native-mask-depth/2 denominator semantics.

Directly call unchanged estimate_visible_patch with original K/T/timestamps,
proprioceptive EEF, seed0 and frozen GeometryConfig. No feasibility callback,
robot self mask, new component association, model, controller or action authority.
Keep original dominant-component-or-abstention, absolute support, RANSAC/plane,
spread/residual, edge/uncertainty, 8mm tool radius, erosion formula, 12mm grid,
interior/candidate ordering and all thresholds. No winner or component fallback.
Candidate usability remains UNKNOWN; geometric proposal does not establish safe
execution, reference identity, full physical visibility or VERIFY.

Per frame record support/depth, components, plane support/reported residual,
boundary/uncertainty/erosion/interior metrics, all candidates, reached stage ledger
and first reason code. Unreached fields stay null / NOT_EVALUATED. Core "VALID"
with NO_TOOL_INTERIOR_CANDIDATE is not usable-tool success. Candidate continuous
projection vs original polygons is diagnostic only, never changes candidate gates.

Prospective priority rule, **not P1 acceptance**: at least13/25 frames with one
or more raw geometry candidates prioritizes semantic identity repair with new
held-out validation. Otherwise a majority has no candidates: prioritize
geometry/tool/viewpoint repair and stop prioritizing semantic model experiments.
For NO_TOOL_INTERIOR_CANDIDATE report full25 fraction and fraction among frames
reaching candidate gates;13/25 is global-majority evidence under this condition,
not a claim of physical impossibility. No thresholds are tuned from these outputs.

Fresh exclusive prepare/evaluate stages with code/source/annotation hashes and
sealed raw outputs. CPU OPENBLAS_NUM_THREADS=1, OMP_NUM_THREADS=1; offline timings
only, no continuous Hz or timing improvement claim. One attempt/frame; runtime
error stops with receipt and no retry. Two focused tests check null/reached-stage
accounting and exclusion of semantic-admission claims; no broad test sweep.

After results, raw imagery inspection, report and checkpoint: STOP. No second
upper-bound condition, semantic inference, temporal tracker, P2/PUSH, Qwen/Laya,
reference or decoder work. Selected milestones remain unchanged.
