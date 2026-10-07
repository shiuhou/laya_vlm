# P1 BOX versus SAM2: bounded development condition

Baseline: `1fedb9c`, P1 Gate C. This implements the conditional SAM2.1 tiny fallback
in `brain-cerebellum-plan-v2.md` §4. Keep the selected three-layer architecture and
B0–B4 route. No tracker, reference completion, Qwen, Laya, P2 or robot action runs.

## Question and competing hypotheses

Can RGB-only BOX-prompted segmentation isolate useful drawer-front support from
the contaminated depth ROI? The competing explanations are:

1. A learned mask separates the requested surface; original geometry then gains
   target-supported interior candidates.
2. Masks retain cavity/cabinet/table contamination or describe different parts;
   segmentation has not resolved target association.
3. A plausible narrow target mask is rejected by the original BOX-area validity
   gate before plane fitting. The mask/BOX measurement interface is incompatible.
4. Camera/depth/edge support is insufficient even after a plausible target mask.

Mask geometry VALID is not semantic identity, calibrated uncertainty or action
usability. SAM receives **RGB + BOX**, not the referring query; the query is
provenance of the BOX. SAM cannot be assumed to understand which cabinet subpart
the task intended. Multiple plausible masks remain hypotheses; no winner is chosen.

## Fixed samples and intervention

Use the already recorded development wrist RGB-D at init25/26, seed1,
384×256, from `runs/p1/surface-dev-20261006-capture02/`. Both lie outside init0–24
of the sealed evaluation set. They are development samples already visually
inspected, not a fresh held-out benchmark. No new sensing or scene infrastructure.

Init25 reuses its complete-EOS native BOX artifact from
`runs/p1/drawer-pair-gpu-20261007/`. Init26 requires **one** new BOX-only call under
the unchanged LocateAnything checkpoint/query/native generation settings and
typed output contract. No POINT calls, prefix extraction or decoder repair.
Malformed/truncated/abstaining output stops the semantic stage without retry.

Compare exactly the same exposure and original BOX:

- BOX → unchanged `estimate_visible_patch`.
- BOX → each of three native SAM2 masks → outside-mask depth UNKNOWN → the same
  `estimate_visible_patch` with original BOX, denominator, thresholds, seed0 and
  recorded EEF proprioception.

Do not shrink the BOX, reinterpret the depth denominator, fill depth, use simulator
IDs, apply manual labels, intersect a mask with a selected plane, or add morphology.
The estimator's original tool/uncertainty edge checks remain unchanged. Native
pixels outside the BOX are preserved as evidence; the original ROI bounds the
geometric computation, as in the baseline.

## Pinned segmentation condition

Official `facebookresearch/sam2` revision
`2b90b9f5ceec907a1c18123530e92e794ad901a4`, Apache2.0, with SAM2.1 tiny checkpoint
SHA256 `7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69`.
Config `configs/sam2.1/sam2.1_hiera_t.yaml`, SHA256
`f932eac1c6241e910031b2f000a81cd9f8a8d4896e2277ab5ffb721f378b188d`.

Use isolated Python3.10/Torch2.5.1+cu121/torchvision0.20.1+cu121. Preserve existing
Torch2.2 environments. Optional CUDA connected-components extension disabled;
SAM postprocessing disabled, hole/sprinkle area0, native logit threshold0,
`multimask_output=True`, `return_logits=True`, FP32/no autocast/no TF32,
seed1/deterministic algorithms. Record exact dependency/source/config/weight
hashes before inference and an explicit RTX4090 GPU UUID allocation.

Retain decoder tokens1–3 in native order (the public multimask API excludes its
separate single-mask token0). Preserve logits, low-resolution logits, masks,
predicted-IoU scores and all geometry candidates. Scores are uncalibrated model
outputs, not identity/contact confidence. Confidence remains null. No best-score,
largest-mask, nearest-plane or first-VALID-mask selection.

## Metrics, seals and first boundaries

Prepare a source/asset/dependency registration before model calls. Seal all BOX
outputs, then every raw SAM output, before geometry and image review. Record full
frame/RGB/depth/calibration/time/BOX/mask source chains and artifact hashes.
The generation APIs do not accept annotations. The sealed50 evaluation set and
its labels remain unchanged and are not read by this experiment.

Per mask record occupancy inside/outside original BOX, native support, original
and masked depth hashes, effective valid-depth ratio, component ambiguity, plane
rejections and all original tool-interior candidates. Keep geometry status,
semantic association and execution usability separate. Inspect raw RGB and all
mask/point overlays only after sealing. Agent review is development diagnosis,
not independent human annotation. Record encoding, prediction and geometry
timings separately; offline times do not establish live throughput/freshness.

The important preregistered bound is:

`masked valid depth / original BOX pixels ≤ mask occupancy within original BOX`.

With the unchanged valid-depth threshold0.50, any narrower mask must fail before
plane fitting. Report this as mask-support/original-ROI-gate incompatibility;
it does not demonstrate SAM failure or absence of a visible surface.

Complete these two fixed samples without tuning ordinary UNKNOWN/AMBIGUOUS
results. Stop on concrete runtime/source-binding/invalid-output/truncation
failure; no hidden retry. No automatic gate/measurement-contract rewrite, SAM
positive-point prompt, new query, new view or tracker follows. The next decision
is based on which of the four hypotheses the raw evidence supports.
