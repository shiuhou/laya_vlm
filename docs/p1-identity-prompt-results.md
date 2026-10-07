# Bounded POINT + BOX identity repair results

Completed 2026-10-07 at frozen execution revision
`b7f54092` (full identity in registration). **Task-valid candidates: 0.**
This single bounded batch is a matched **reused-development diagnostic**, not a
new Formal-50 held-out evaluation or P1 acceptance. The Formal-50 images,
annotations and previous results were already exposed before this intervention.

[Prospective protocol](research/p1_identity_prompt_protocol.md),
[evidence index](evidence/p1_grounding/identity_prompt_20261007/README.md),
[all50 frames](evidence/p1_grounding/identity_prompt_20261007/all-frames.csv),
[all150 planned native slots](evidence/p1_grounding/identity_prompt_20261007/all-planned-native-slots.csv),
[machine summary](evidence/p1_grounding/identity_prompt_20261007/summary.json).

## Intervention and preserved conditions

Add a same-frame LocateAnything semantic POINT as one positive SAM prompt,
alongside the **original independently archived BOX**. Nothing else in model,
query, native decoder, mask measurement contract, geometry gates or candidate
ordering was tuned. The original Formal-50 runner and evaluator remain intact.
All50 first exposures (init0–24, agentview+wrist,384×256), sensor/depth/calibration
identities, BOXes and frozen annotations are unchanged.

LocateAnything: same checkpoint content ID
`4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`,
normal native `Point to: {frozen drawer query}.`, max256 tokens/hybrid,
do_sampleFalse/temperature0/cacheTrue. Full RGB and fixed text only.
No new BOX, reference POINT, prefix salvage, retry or budget escalation.
Full terminal-EOS audit precedes typed-v1 parsing; exactly one POINT required.

SAM2.1 hiera-tiny: original source revision
`2b90b9f5ceec907a1c18123530e92e794ad901a4`, checkpoint SHA
`7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`;
all original FP32/deterministic/no-postprocessing settings and the frozen
instance-only dense-grid overlay retained. Positive coordinates are the
reparsed native continuous xy, cast float32, label1. All3 multimasks, logits,
lowres logits, predicted IoUs and canonical ordinals retained.

POINT admission authenticates raw UTF8 bytes, complete source/query and
no-label provenance. It requires continuous half-open POINT-in-BOX, floored
pixel inside the original ceil geometry ROI, and finite/in-range original
pixel depth. No snapping, BOX replacement or component fallback.
Every returned mask runs the unchanged `native-mask-depth/2` geometry, including
masks contradicting the point. Point containment is **separate admission**, not
semantic truth or a prompting gain. No calibrated confidence is claimed.

Both fresh model processes used explicit single RTX4090 allocation
`GPU-85568c28-bb76-35a8-d4ef-16ba2c2b7da3` and exited0, no timeout/retry.
The registration authenticates1,066 source files; all stage seals are verified.
New scoring opened frozen annotations only after POINT+mask+geometry seals.
There were **zero call exceptions**: an incomplete generated reply is recorded
as a completed raw call with failed completion/admission, never prefix-parsed.

## Full denominators and first boundaries

| Measurement | Agentview | Wrist | Total |
|---|---:|---:|---:|
| Source frames / POINT calls |25|25|50|
| Human VISIBLE / UNKNOWN / NOT_VISIBLE |0 /25 /0|25 /0 /0|25 /25 /0|
| Terminal-EOS replies |21|14|35|
| Typed POINT admitted |14|9|23|
| No EOS |4|11|15|
| Wrong POINT cardinality |5|5|10|
| Invalid complete syntax |2|0|2|
| Admitted POINT outside original BOX |6|1|7|
| SAM calls completed |8|8|16|
| Native masks generated and evaluated |24|24|48|
| Planned slots not evaluated |51|51|102|
| Raw geometric proposals |0|9,149|9,149|
| Task-valid drawer-front candidates |0|0|0|

All150 planned slots remain represented. The34 SAM-skipped frames failed
POINT admission or original-BOX compatibility; their downstream geometry is
**NOT_EVALUATED**, not demonstrated absent. All48 returned masks have depth
availability1.0. There is no new depth-availability gate failure.

Physical rejection among returned masks (not annotation-based identity):

| Frozen physical outcome | Agentview24 | Wrist24 | Total48 |
|---|---:|---:|---:|
| INSUFFICIENT_PLANE_SUPPORT |24|0|24|
| AMBIGUOUS_DEPTH_COMPONENTS |0|9|9|
| INSUFFICIENT_CONNECTED_SUPPORT |0|1|1|
| NO_TOOL_INTERIOR_CANDIDATE |0|1|1|
| Raw candidate-producing mask |0|13|13|

The small-mask connected-support rejection is an absolute-support failure,
not missing depth. Rejected stages preserve later NOT_EVALUATED entries.
Wrist annotation-based categories among24 generated masks:11 segmentation
identity failures,3 semantic BOX failures,9 ambiguous-component failures and
1 edge/tool rejection. Agentview semantic accuracy remains UNKNOWN; its labels
must not become negative accuracy examples or proof of camera invisibility.

**Legacy field caveat:** inherited `by_camera.inference_failures=34` and
`geometry_failures=34` count status!=COMPLETE upstream-skipped SAM rows. They do
not mean34 model/runtime exceptions. Use planned-slot accounting, per-frame
reasons and process receipts for causal interpretation. Frozen JSON is retained;
[provenance notes](evidence/p1_grounding/identity_prompt_20261007/provenance-index.json)
make this naming limitation explicit.

The first chronological raw-call failure boundary is input2 (init1 agentview):
256-token generation without EOS. Independent samples continued without retry,
as registered. On the actionable wrist camera,7/9 typed POINTs are outside the
human front region and2/9 inside;16/25 frames have no admitted POINT. A legal
schema is therefore insufficient grounding evidence.

## Matched contrast and concrete cases

Compare only the **same eight generated wrist frames, all24 native masks**:

| Measurement | Original BOX-only | POINT + BOX raw | After POINT-mask admission |
|---|---:|---:|---:|
| Geometric proposals, all outside front |9,226|9,149|7,617|
| Task-valid candidates |0|0|0|
| Median mask contamination |94.218%|96.808%|95.113%|
| Native mask denominator |24|24|22|

The2 contradictory masks belong to init23: native1 has inadequate connected
support, native2 produces1,532 tabletop proposals. Their raw geometries are
retained; filtering removes1,532 proposals and does not improve target success.
The proposals are correlated grid points, not9,149 independent trials.
Comparing all baseline45,252 proposals against new9,149 would mix prompting
with upstream attrition; the paired subgroup is the appropriate descriptive
comparison. The subgroup is selected by model admission, not independent/random.

Only two wrist POINTs match the human front:

- **init1/input3:** correct POINT at(288,62.976), but original BOX covers another
  region. POINT_OUTSIDE_ORIGINAL_BOX rejects before SAM. No BOX repair performed.
- **init12/input25:** correct POINT at(280.32,45.824), all3 masks contain it.
  Native1 covers81.98% of annotated front with71.33% annotated purity, local
  plane support95.62% and RMS0.332mm. It fails NO_TOOL_INTERIOR_CANDIDATE:
  40 grid cells,29 edge-margin rejects,11 outside-visible-support rejects,
  engineering erosion15.463mm, eroded support11. Uncertainty is uncalibrated.
  Native0/2 remain broad and produce1,452/1,425 tabletop proposals. This is a
  useful single development example of better part segmentation, **not** an
  accepted mask, tool patch or proof of physical impossibility.

Input1/init0 wrist and input5/init2 wrist illustrate wrong POINT/cavity proposals;
input47/init23 illustrates a POINT on an unrelated tabletop object. All50 RGB
and point outcomes,48 masks and proposal overlays were inspected in ten complete
point-review sheets. Two independent reviewers authenticated evidence and
inspected all ten baseline-layout review sheets. Failures were not omitted.

## Offline timing only

| Stage (p50 /p95) | Agentview | Wrist | Total |
|---|---:|---:|---:|
| POINT generation,25 /25 /50 calls |0.549 /3.338s|0.983 /5.308s|0.673 /4.897s|
| SAM encode+decode,8 /8 /16 calls |37.96 /169.98ms|37.19 /51.49ms|37.44 /101.99ms|
| Geometry,24 /24 /48 masks |41.08 /61.08ms|108.68 /8,193.63ms|54.95 /8,047.41ms|

CUDA inference timing is synchronized. These are isolated offline stages,
not continuous end-to-end throughput or freshness. Geometry used
OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1; the earlier baseline has no
authenticated thread-setting receipt. This compute-setting difference is
recorded in the process-context artifact: do not attribute timing changes to
the prompt repair. Geometric algorithm/configuration/gate hashes are unchanged;
no bitwise numerical equivalence claim across CPU thread settings is made.

## Belief update and stop

Observed: this exact POINT+original-BOX condition yields no task-valid candidate,
poor POINT reliability, and no matched aggregate contamination improvement.
Inference: merely adding a positive semantic point is insufficient for this
frozen interface. Point-in-mask does not establish identity of the selected
surface component or its candidates. Confidence high for this batch, limited
for generalization. The2 label-correct POINTs are too few to estimate robust
correct-prompt performance. One shows an independent unchanged tool-support
boundary after better segmentation; the other is blocked by the old BOX.

Do not conclude that cameras lack observable drawer geometry, that all POINT
methods are useless, that a physical push is impossible, or that Qwen/Laya
would fail: none was tested here. No final scientific Gate C is inferred.

Next decision **for review**, not executed: choose one prospective experiment
separating reliable target-part identity from usable tool support, with a new
condition and later independent held-out evidence. Do not resume decoder-budget
research, tune this sample or add planners to compensate for absent geometry.
The selected milestone route is unchanged; P1 acceptance remains unearned and
P2 remains blocked pending the perception/temporal P1 gate. Reference/VERIFY
UNKNOWN. No temporal/tracker, reference decoder, PUSH, P2, Qwen or Laya run.

Changes: source-bound prompt contract, isolated experiment orchestration,
paired postseal evaluator and protocol; generic runtime/executor/controller
unchanged. Six focused synthetic tests pass. Commits747fb7f (contract/runner),
b7f5409 (paired evaluator/frozen execution); evidence checkpoint follows.
