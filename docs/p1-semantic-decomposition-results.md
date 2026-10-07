# Bounded wrist25 semantic decomposition

The diagnostic completed at execution revision `f60cc1d977976e316075cdc58ace7d9be55d6ddd`,
with baseline `f5cc1ce` preserved. **Prioritize target-part BOX/search-support
localization as the single next semantic repair.** Do not change geometry/tool
gates. No repair or new held-out experiment was executed this round.

This is an offline, human-assisted diagnostic on 25 already exposed development
frames. It is not autonomous perception performance, independent validation,
P1 acceptance, or executable manipulation. Human BOX/POINT were derived from the
frozen annotation only; they never entered runtime/policy evidence.

[Prospective protocol](research/p1_semantic_decomposition_protocol.md) ·
[Evidence, all25 table and raw archive](evidence/p1_grounding/semantic_decomposition_20261007/README.md)

## Four conditions

A candidate frame has at least one geometry candidate projecting inside the
frozen human drawer-front polygon. For SAM conditions the table requires the
native mask to contain its positive point. No mask/candidate winner is selected.
Counts across native masks include overlapping proposals; they are not unique
physical points or a ranking of system performance.

| Condition | SAM completed | Native masks | Candidate frames /25 | Inside candidates | Outside candidates, raw → point-admitted |
|---|---:|---:|---:|---:|---:|
| C1 Human region → geometry (reused) | — | 25 human supports | **25** |130|0|
| C2 Human BOX + human POINT → SAM → geometry |25|75|**25**|344|0 → 0|
| C3 Original model BOX + human POINT → SAM → geometry |21|63|**10**|69|44,737 → 43,188|
| C4 Original model BOX + model POINT (reused) |8|24|**0**|0|9,149 → 7,617|

C3 preserves four `POINT_OUTSIDE_ORIGINAL_BOX` failures: init1/2/5/9. They are
prompt-compatibility failures, not SAM runtime exceptions or missing geometry
capability. All 46 new admitted SAM calls completed once, returning all three
native ordinals. All 138 masks were evaluated, including one C3 mask that
contradicts its positive point. There were no inference retries or mask winners.
All candidate usability remains UNKNOWN: FEASIBILITY_NOT_EVALUATED and
UNCALIBRATED_UNCERTAINTY. Cabinet-relative VERIFY remains UNKNOWN.

## What the comparison establishes

The preregistered priority heuristic uses signed candidate-frame gaps:
C1−C2 = **0**, C2−C3 = **15**, C3−C4 = **10**. The largest gap selects BOX grounding.
There are no reverse frame-existence changes in these contrasts. Counts are not
monotonic: for example init14 has 6 C2 versus 11 C3 inside proposals; candidate
quantity is not the selection criterion.

C2 versus C3 has 21 jointly completed frames: **21 versus 10** candidate frames.
The other four C3 losses occur before SAM because its original BOX excludes the
human point. In the **seven** jointly completed C3/C4 frames (init0/6/12/18/19/20/23),
the result is only **1 versus 0**, with the gain at init20. C4 init2 completed on
its wrong target; C3's human point is outside that BOX, so init2 is excluded from
the jointly completed comparison. The all25 POINT contrast must not be presented
as ten matched segmentation gains: most gains involve formerly unavailable
model POINTs/admissions.

The original BOX fully covers the human region on 21/25 frames, but coverage
alone is insufficient: many BOXes include cabinet/table alternatives. A correct
positive point does not remove this contamination or reliably identify the
intended component. Median whole-native-mask human-region purity is 77.65% in C2
and 9.13% in C3. These are diagnostic overlaps, not acceptance thresholds.

**C2 changes both the SAM BOX prompt and the geometry search ROI.** Visual review
shows C2 masks, especially native0, can extend beyond the human front; tight BOX
bounds restrict which depth samples reach geometry. Thus this experiment does
not isolate a SAM-prompt effect from a geometry-domain effect and does not show
that SAM alone now identifies the part correctly. It supports repairing the
source of a target-part-specific search region. Human BOX alone with the original
model POINT was not tested; success of an autonomous BOX-only repair is unknown.

C1 versus C2 also changes support/search/proposal domains and uses one versus
three supports per frame. Its equal 25/25 frame coverage shows no residual
frame-level loss under the paired human prompts; it does not prove perfect SAM
segmentation. Eight C2 native masks still fail gates.

## Native-mask first boundaries

| First boundary | C2 /75 | C3 /63 |
|---|---:|---:|
| Geometry candidates (including wrong target) |67|40|
| AMBIGUOUS_DEPTH_COMPONENTS |0|17|
| INSUFFICIENT_PLANE_SUPPORT |0|5|
| ERODED_PLANE_DEGENERATE |7|1|
| NO_TOOL_INTERIOR_CANDIDATE |1|0|

C2 candidate-producing native ordinals 0/1/2 occur in 25/17/25 frames.
C3 inside-candidate-producing ordinals 0/1/2 occur in 0/10/0 frames. This is a
retrospective distribution, **not permission to choose native1 in a future
pipeline**. All other masks, including wrong-target candidates, remain evidence.
Early rejections retain later stages as NOT_EVALUATED; no threshold was relaxed.

## Image and first-divergence review

All five summary sheets and all 25 frame rows were visually reviewed, showing
both conditions and every returned ordinal. Full-resolution individual sheets
are retained. Magenta is native SAM support, yellow the offline human polygon,
green inside candidates and red outside candidates. Original/prompt panels show
BOX in red and positive point in cyan.

- init1/2/5/9: first divergence is BOX compatibility, before SAM. Human point is
  retained unchanged; no snapping, clamping or BOX fallback.
- init0: C2 produces 18 inside candidates across three masks; C3's broader
  cabinet support is rejected as AMBIGUOUS_DEPTH_COMPONENTS for every ordinal.
- init7: C3 native1 yields seven inside candidates, while native0/2 yield
  1,593/1,553 outside candidates. Point containment admits all three. A useful
  mask existing in a pool does not make the pool task-safe.
- init12: C2 native0/2 each yield seven inside candidates; native1 is rejected
  ERODED_PLANE_DEGENERATE. C3 native1 also degenerates (38 eroded support samples),
  while native0/2 yield 1,449/1,424 outside candidates. The old C4 native1 failed
  NO_TOOL_INTERIOR_CANDIDATE. Correct prompts do not force every native mask to
  succeed, and failures are not removed.
- init20: the only gain in the jointly completed C3/C4 subset; C3 native1 yields
  eight inside candidates, but native0/2 still yield 1,540/1,485 outside proposals.

## Frozen implementation and provenance

New experiment-only modules: `p1_semantic_decomposition.py` and
`p1_decomposition_report.py`. No runtime, geometry, SAM, query, candidate-ordering
or threshold module changed. The human BOX is a minimal half-open bounding
rectangle; positive point is the maximal exact Euclidean distance-to-complement
pixel of the false-padded human mask, row-major tie break, continuous pixel centre.
Depth only enters subsequent prompt admissibility and unchanged geometry.

Pure `estimate_visible_patch` receives original sensor depth with pixels outside
each native mask NaN, that condition's BOX ROI, original calibration/EEF/timestamps,
seed0, and full-native-mask depth denominator. It does not misuse the learned-only
wrapper by claiming human labels were absent. External SAM source/weights/config
and 1,424 registered source files are authenticated. The fixed FP32 deterministic
SAM2.1 tiny condition uses the same grid compatibility overlay; all original
logits, low-resolution logits, uncalibrated IoUs and ordinals are saved.

GPU: RTX4090 UUID `GPU-85568c28-bb76-35a8-d4ef-16ba2c2b7da3`, torch2.5.1+cu121,
existing prepared SAM venv. Other workloads shared the GPU, so timing is this
batch's observed latency, not an isolated hardware benchmark.

| Offline latency, ms p50 / p95 | C2 | C3 |
|---|---:|---:|
| SAM image encoding |29.16 /35.66|30.08 /39.93|
| SAM native prediction |11.50 /13.63|11.56 /12.16|
| Encoding + prediction |40.87 /47.14|41.49 /51.79|
| Geometry per native mask |40.09 /58.91|79.98 /8,401.96|

C3's large mask/candidate domains produce a long geometry latency tail. These
measurements exclude full continuous acquisition/tracking/scheduling and are
**not continuous end-to-end Hz**. No efficiency optimization was attempted.

## Decision and stop

Observed fact: paired human BOX+POINT recovers candidate existence in 25/25
frames; retaining original BOX with human POINT recovers only 10/25 and retains
extensive wrong-target proposals. Inference: **target-part BOX/search-support
localization** is the best supported single next repair priority. Confidence is
high for this frozen development contrast, limited for transfer or BOX-only
causality. Competing explanation: domain restriction contributes more than SAM
prompting; this experiment deliberately cannot separate them.

Future validation must use new held-out frames, keep geometry/tool gates frozen,
and preserve failures and all native outputs. Human prompts must not enter that
runtime/perception condition. No new repair, held-out collection, tracker,
temporal sequence, P2/PUSH, Qwen or Laya was started. P2 remains blocked pending
independent spatial validation / temporal P1 gate.

Two targeted tests passed (exact padded-distance/tie/coordinate convention and
BOX incompatibility without clamping). Independent read-only audit checked
source/config hashes, seals, all 138 native masks, and recomputed candidate
projection/counts. No model or geometry rerun was needed. C1/C4 archives remain
unchanged. Execution tag: `p1-semantic-decomposition-execution-f60cc1d`.
