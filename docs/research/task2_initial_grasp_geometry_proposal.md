# Proposed Task2 initial observed-surface geometry test

Status: design proposal only. No model call, dynamics, segmentation, descriptor
computation, or approach command has been run for this proposal.

## One question and one fixture

Does one RGB-grounded initial bottle observation provide useful **observed
surface extent relative to the jaws**, beyond the existing single 3-D point?
Test this before attempting a sensor-selected approach. The prior scripted
close/lift witness supplies a successful local context, but it does not validate
getting from the initial view to that context.

Use exactly the close arm's reset capture from
`runs/autonomous-research/interaction-observability-paired-01`:

- `close/0000.npz`, SHA-256
  `3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`;
- `close/0000.png`, SHA-256
  `9b446e31066ff438765f01e0bed579346b8ab6c99b79e937cf53a992510419e3`;
- `endpoints.json`, only `arm=close, after_step=-1`, for the own TCP pose and
  direct finger encoders. The frame contains 384 × 384 RGB/depth, intrinsics,
  camera transform, and capture read time 0.5 s. Actual cached geometry sample
  time is unknown.

No additional frames, image crops selected after a result, approaches, model
variants, or retries enter the test. Both paired initial images are duplicates;
count this as one fixture, not two independent cases.

## Shared grounding and competing representations

The cheapest use of the existing interface is **one LocateAnything BOX call** on
the full initial RGB with the fixed task-language query `the wine bottle`. Use
the existing checkpoint, hybrid greedy generation, and native token/EOS audit.
Require one complete valid box; report missing/multiple/malformed/non-EOS output
without falling back to an assistant annotation or another prompt. Do not treat
the worker's hardcoded score of 1 for a parsed box as semantic confidence.

The production adapter returns a box-center ray at the median depth of its
fixed interior crop. Keep that exact point unchanged as representation P. In
representation G, retain P and append the backprojected valid pixels from the
**same interior crop**, with the existing depth validity range 0.01–5 m and the
declared raster-center convention. No foreground split, learned mask, clustering,
PCA-driven point selection, background subtraction, or outcome-guided cleanup.
The crop contains candidate support, not verified object segmentation.

This comparison holds model call, prompt, RGB, box, point, depth support, and
camera calibration fixed. A separate POINT query would confound representation
with changed grounding, so it is not part of this test. An all-pixel surface
centroid may be reported as a descriptor but must not silently replace P.

G reports observed min/max projections onto the calibrated current jaw-closing
axis, gripper approach axis, and remaining transverse axis, plus the point's
offset from those intervals. It also retains the selected pixel indices and
their 3-D points so the apparent span can be traced to individual pixels. These
axis-aligned projected extents already encode orientation relative to the robot;
PCA, shape completion, fitted bottle dimensions, and a grasp-pose generator are
unnecessary for this first discriminator.

Use only known robot-local TCP-to-pad calibration and the initial own sensors
for jaw axes and open-pad gap. The prior robot-only calibration can supply
static gripper geometry if its local chain identity matches; do not transplant a
Task1 world/base transform to Task2. Admission must verify this before running
the test, without estimating the transform from the successful grasp. Joint
encoder aperture and inner-pad geometric gap remain separate quantities.

## Discriminator and evaluator separation

The single static discriminator is whether the observed support's span is
smaller or larger than the current open-pad gap along each of two fixed robot
axes: the current jaw-closing axis and current approach axis. These two axes are
chosen from robot calibration, before any target output. They pose an orientation
ambiguity that a single point cannot resolve. They are geometric queries, not
new executable orientation actions or proposed approach poses.

P leaves both extent comparisons unknown. G provides two measured spans and
their signed difference from the open-pad gap. The evaluator independently
computes the same quantities from the archived initial bottle mask and depth,
then reports the span errors and whether each measured comparison agrees with
the visible target support. It also reports crop purity, visible target recall,
whether the box-center sample belongs to the bottle, and P's error against the
same visible-target surface reference. No oracle pixels correct G, and the
evaluator never feeds a reference point or offset into P.

This is deliberately a test of **observed-support containment in a jaw-sized
interval**, not a full grasp-fit predicate. A whole-bottle span can differ from
the local section contacted by the pads. Support spanning more than the aperture
refutes enclosure of that complete observed support in that interval, but does
not prove that every local grasp is impossible. A smaller visible span does not
certify opposite surfaces, pad clearance, hidden thickness, force closure,
retention, or a collision-free approach. Numerical equality is retained; no
data-fit tolerance or confidence threshold is introduced.

The archived successful preclose capture `close/0013.npz`, SHA-256
`61cf6082800128f8806a825b84f64b1f455da68924508b6e7100dc93fe91a9cf`, after step 12,
is evaluator-only corroboration. It may show the actually used jaw/body relation
and the discrepancy between initial P and one known successful preclose jaw
midpoint. It cannot select the box, support, axis, target, offset, or scale, and
must not become a fitted goal pose. Report any object motion between the initial
and preclose states separately; do not align the initial prediction using oracle
motion. Agreement with one successful context does not imply uniqueness, and
disagreement alone does not prove an alternative pose infeasible.

## Failure modes and decision value

The initial RGB visibly contains a bottle next to an open drawer. Occlusion,
box contamination by the drawer/table, cap-versus-body selection, black-surface
depth, pixel-boundary conventions, and asynchronous render/proprio caches can
corrupt a geometric descriptor. The archived mask comes from ID rendering and
shares synthetic camera/depth calibration; it is a membership evaluator with
raster-edge limitations, not independent metrology. View-weighted surface
centroids and spans are not rigid-body centers or complete dimensions.

If identity/support is poor or G gives the wrong span comparison, stop with that
specific failure; do not try a segmentation variant in this run. If both identity
and the two-axis measurements agree with the evaluator, the result earns a local
sensor geometry representation with measured limits. It still does not qualify
an approach, a manipulation policy, or generalization. That is the useful next
decision: whether the cheapest current box/depth interface contains enough
geometry to justify a separately frozen local approach experiment.

Before any future execution: freeze code/protocol/input hashes, test numerical
projection and robot-frame conventions synthetically, review the input schemas,
seal the RGB-only model output and sensor geometry before opening masks or
preclose context, and retain every outcome. Estimated cost is one existing-model
query and offline array arithmetic; zero physics, new captures, new planners, or
reference trajectory replay.
