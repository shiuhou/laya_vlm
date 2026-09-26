# First-contact RGB-D observability audit v0.1

Registered before computing visibility/projection/backprojection results,
2026-09-27. This is an evaluator-only analytic audit of an already completed
physical trace, not a new sensor estimator or manipulation experiment. It asks
whether the available RGB-D before the first contact exposed the nearby contacted
surface, how robot/scene occlusion affects that evidence, and what the admitted
single target point omits.

## Frozen evidence and boundary

Use only main-workspace
`runs/autonomous-research/coarse-initial-point-02/episodes.jsonl`, SHA-256
`e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf`, and its
hash-referenced artifacts. The recorded first sampled contact over 1 N occurs
at primitive 25 / control 0, between `gripper0_finger1_collision` and
`wooden_cabinet_1_g11`. This location/pair is an **oracle evaluation query**;
it must never enter a target estimator, candidate gate, collision filter,
controller or model prompt. The parallel execution/provenance audit owns
contact semantics, replay and success interpretation; this audit owns visibility.

Primary sensor evidence is the RGB-D immediately before primitive 25,
`frames/capture-000026.npz`, with the matching paused before/after full state.
Inspect the preceding boundary 24 capture as one fixed temporal reference,
and the raw after-control RGB at primitive 25 / controls 0 and 7. There is no
recorded post-contact depth. Do not synthesize a post-contact sensor measurement
or present a re-render as an original observation.

## Bounded analytic procedure

1. Verify record chains, artifact hashes, ordered boundary/control identities,
   and equality of paused capture state and first control's starting state.
   Preserve a manifest of exact source, code/protocol, package/repository and
   calibration identities. Inspect the three relevant raw RGB views and the
   available depth image without a model call or automatic semantic labeling.
2. Load the exact task/model for **offline evaluator geometry only**. Reconstruct
   stored pre-action and first-contact endpoint qpos/qvel/time using the recorded
   flattened states and forward kinematics; do not execute archived or proposed
   controls, simulate a physical retry, change the native controller, or query an
   action preview. Default environment creation/reset/settling, if required to
   instantiate the model, is evaluator bootstrap and must be disclosed. Require
   restored flattened state equality and matching task/environment identities.
3. Verify camera conventions from the capture code and installed calibration
   code. Stored RGB/depth are vertically corrected; the calibration maps camera
   +Z optical depth and pixel coordinates into world space. Project with the
   inverse recorded camera-to-world matrix, then backproject the containing
   pixel **center** `(floor(u)+0.5, floor(v)+0.5)`. Record continuous coordinates,
   containing pixel, optical depth, ray range, residuals and round-trip errors.
   Check restored camera calibration against the stored calibration. Shared
   calibration agreement is internal consistency, not external calibration proof.
4. The sampled contact world position is after a control and the drawer moves
   during it. Never call its unchanged world coordinate the pre-contact point.
   Record contacted geom transforms at stored pre/post endpoints. Compute the
   contact coordinate in the post-endpoint geom frame and carry that local
   coordinate into the pre-action geom frame. Also find its nearest point on the
   known contacted collision box surface, then carry that surface representative
   back. This is an **oracle rigid-correspondence estimate**, not an observation
   of the exact first-touch material point. Retain the uncorrected projection as
   a disclosed motion sensitivity comparison, not as pre-contact truth.
5. Explicitly assess limitations of the correspondence: a MuJoCo contact point
   may be a contact-manifold midpoint, collision and visual surfaces differ, and
   archived post-control contact/derived geometry may not be perfectly aligned
   with final integration qpos. The first sampled contact is not the first
   integration-substep contact. Record the midpoint's residual to the box surface
   and object endpoint motion. Do not infer unstored substep geometry or assert an
   exact physical pre-contact location when the records cannot establish it.
6. At the primary carried-back box-surface representative, compare recorded
   pre-action optical depth with query depth; independently backproject the raw
   sensor pixel and report 3-D separation. Inspect fixed pixel neighborhoods of
   radius **0, 2, 5** around its containing pixel, preserving all samples rather
   than selecting a favorable point or fitting a threshold. Report continuous
   sensor-depth/geometry residuals and nearest sampled-support distances. Repeat
   the same transported geometric query on the single preceding boundary 24
   capture, using its own stored state/calibration and labeling it secondary.
7. Use MuJoCo visual-geometry rays in the restored evaluator state to identify
   what lies on the exact continuous query ray and the fixed neighborhood's pixel
   rays. Match actual render collision/visual group flags, document ray settings,
   retain geom/body/mesh identity and label each hit robot or scene from explicit
   model provenance. Compare ray optical depths with recorded depth, accounting
   for pixel-center/edge rasterization and collision-vs-visual geometry mismatch.
   This is oracle visibility evaluation, **not sensor segmentation**. No ray label
   or hidden mesh identity may be fed into a runtime decision. Do not remove robot
   geometry or change the scene to manufacture visible support.
8. Produce raw RGB/depth crops or overlays that distinguish the raw admitted
   target point from all oracle query overlays. Inspect before and recorded
   after-contact RGB for robot/scene occlusion. A nearer robot ray hit supports
   self-occlusion at that query; a nearer scene hit has a different interpretation.
   Visible neighboring points can coexist with an occluded/ambiguous exact contact
   representative. Preserve disagreements instead of forcing a binary label.

All geometry-derived query coordinates, membership and motion corrections are
privileged evaluator data. Sensor support measurements are clearly separated
from those evaluator queries. No new segmentation model, checkpoint download,
Laya/LocateAnything inference, collision filter, candidate mask, policy change,
controller change, physical retry, or collision-avoidance success claim follows.
GPU 5 is available only if evaluator model/mesh inspection requires it.

## Report and stopping rule

Report raw measurements and images with source hashes and all uncertainty,
including absent post-contact depth and possible contact/state timing offset.
Distinguish: (a) visible depth support near the retrospectively queried surface,
(b) exact point visibility, (c) full shape/free-space coverage, and (d) semantic
interaction/affordance guarantees. None implies the next automatically. A single
point can supply target location while omitting local surface normal/extent,
robot occupied volume and clearance, time-varying occlusion, or the identity of
contacting surfaces; assess which omissions the evidence actually demonstrates.

If stored state/model evidence cannot locate the pre-contact surface exactly,
report the query as a correspondence estimate or unknown, with sensitivity
measurements; do not reconstruct missing state invisibly. Stop after this bounded
analysis. The result may earn a separately registered geometry measurement or
experiment, not a collision filter or autonomous manipulation claim.
