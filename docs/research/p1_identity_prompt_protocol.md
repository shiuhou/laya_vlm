# Bounded POINT + original BOX identity repair

Prospective condition `p1-point-positive-sam-repair/1`, baseline checkpoint
`34486e3`, same original Formal-50 first exposures (init0–24, 25 per camera).
This set and its labels/results have already been inspected. This is a matched
reused-development diagnostic, **not held-out evaluation or P1 acceptance**.

## Question and hypotheses

H1: the broad original BOX under-specifies the drawer part; a correct same-frame
semantic POINT provided to SAM reduces contamination and enables geometrically
usable front proposals. Prediction: on POINT-admitted identical frames, raw
POINT+BOX outputs improve annotated purity and task-valid candidate counts versus
BOX-only, before contradiction filtering.

H2: POINT itself cannot ground this part reliably. Prediction: incomplete/invalid
POINT or incorrect annotated position dominates failures before SAM.

H3: correct POINT is insufficient: segmentation or unchanged geometry fails.
Prediction: correct-point subgroup still has identity/geometry rejection.

These predictions are descriptive development diagnostics. No independent
performance/generalization claim, significance test or threshold fitting.

## Single intervention and locked inputs

Add exactly one positive native continuous semantic POINT to the existing BOX
prompt. All original RGB, BOX, camera/calibration/depth/source identities, frozen
query/checkpoint, SAM source/weights/native settings/deterministic grid overlay,
mask-support contract, geometry thresholds and canonical candidate ordering stay
unchanged. Registration authenticates baseline entry, all source hashes, assets,
new code and this protocol before generation.

LocateAnything uses the existing `Point to: {frozen drawer query}.` native prompt,
256 output tokens, hybrid, temperature0, do_sampleFalse, cacheTrue. RGB and this
fixed text are its only model inputs. 50 calls maximum, canonical order, one
attempt/frame. No reference POINT, decoder fix, query change or budget escalation.
No prefix extraction. Parse the full typed-v1 reply only after terminal EOS audit;
require exactly one requested POINT. Auxiliary BOX remains evidence and cannot
replace the original independent BOX.

Before SAM, bind POINT to the same complete sensor source and query. Require
continuous half-open inclusion in original BOX **and** floor-sampled POINT pixel
inside original ceil geometry ROI. Require valid finite/in-range original depth
at the pixel. No snapping, expanding, closest/largest component or fallback.
Retain failed rows and three planned NOT_EVALUATED mask slots per frame.

SAM keeps FP32/no autocast/noTF32/postprocessingFalse, native multimask/logit
output, seed1 and CuBLAS `:4096:8`. Positive coordinates are native continuous xy
cast to float32, label1. Retain all three original decoder ordinals, masks,
logits, lowres logits, IoUs and process/timing/source receipts. No winner/ranking.

Every returned native mask runs unchanged geometry, even if it contradicts the
POINT. Exact sampled-pixel containment is recorded separately as admission.
Report raw prompting contrast and admission-filtered results separately: filtering
is not a model gain. Point containment does not prove semantic mask/candidate
identity. Unknown semantic identity remains unknown at runtime.

## Failure and sealing

Each stage uses an exclusive new directory, never overwrites previous evidence.
Ordinary independent frame failures are retained while remaining planned frames
continue. RuntimeError (including CUDA/device errors), MemoryError or process failure stops
the batch with receipts, no retry. Ordinary output/schema failures are per-sample. Each
model process has a fixed 1800-second total ceiling; timeout is a failure, no
continuation splice. All POINT, masks and geometry aggregates/conditions are
sealed before new scoring reads frozen labels. Labels never enter generation,
prompt compatibility, component selection, geometry or candidate ordering.

Scoring: per-camera 50-frame/150-planned-slot denominators; EOS/typed POINT,
correct/wrong POINT on VISIBLE frames (UNKNOWN not an accuracy negative), original
BOX compatibility/depth, raw mask contamination/geometry/candidate identity,
contradictions, matched baseline on generated physical frames and all-frame
failures. Report p50/p95 inference and offline geometry, never continuous Hz.
Inspect all-frame contact sheets and preserve all raw failures.

## Stop

After this one batch, scoring, inspection and checkpoint, stop for review.
No automatic additional repair, init25/26 tuning, temporal/tracker experiment,
fixed-reference work, PUSH/P2, Qwen or Laya. P2 remains blocked pending the
perception/temporal P1 gate. A development improvement cannot waive that gate.
