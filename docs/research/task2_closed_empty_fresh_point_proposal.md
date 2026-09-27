# Conditional four-image fresh POINT check

The smallest next semantic check would ask the existing LocateAnything model
**“Point to: the wine bottle.”** once on each of four new full RGB images: the
post-event and prelift images in both neck present/away cells. This tests fresh
semantic localization against the possibility that the old fixed image region
describes the hand or background. It does not ask the model whether anything is
held and does not convert a returned point into a holding label.

This is preparation only. It requires an independently admitted physical pair,
completed motion evidence, and a subsequent root decision that this semantic
question is warranted. No model processor preflight, checkpoint loading,
inference or source-image extraction has been performed for this proposal.

## Reuse is possible with a small boundary adaptation

`task2_point_region_control.native_input(processor, rgb, condition)` accepts an
arbitrary native RGB array and the fixed question. It constructs one user
message with one image and one text item, then uses the checkpoint's existing
chat template and vision processor. `call_once` accepts the prepared tensors,
makes one native generation, seals raw output and actual decoded token IDs
before analysis, and enforces its existing 300-second timeout with no retry.

The old `condition_run` and `processor_preflight` are tied to the archived
initial image and two whole/neck descriptions. The old `analyze_return` samples
scene depth and attaches hardcoded initial-frame provenance. They cannot be
used unchanged for this check. The small
[prospective adapter](../../embodied_runtime/experiments/task2_closed_empty_point_adapter.py)
therefore supplies only fixed source selection, RGB-only loading, the unchanged
native processor call, and RGB-only parsing. It has no launcher, worker
construction, CLI or inference call. A later authorized harness can reuse the
existing fresh-process launch pattern and `call_once` without changing the
model, generation function or processor.

Retain the exact checkpoint
`/home/junhongli/models/huggingface/LocateAnything-3B`, content ID
`4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`.
Settings remain BF16, eval mode, one fresh Python/model process per image,
seed 1, the same assigned GPU, `max_new_tokens=256`, `use_cache=true`,
`generation_mode="hybrid"`, `temperature=0.0`, `do_sample=false`,
`verbose=false`, tokenizer maximum length 16384 and EOS ID 151645. Retain the
loaded-config/environment checks and actual processor tensor/token/grid
receipts from the existing runner. No new weights or model are proposed.

Reusable source hashes:

| File | SHA-256 |
| --- | --- |
| `task2_point_region_control.py` | `cded84237e2f8953406806d3432634b33bacdaaecb1a9f26dceb365f2f59e86c` |
| `task2_box_support.py` | `8a8d7d828b4b2f65593975cb0378e5b4e7828c1e27ae432d6ca3bfdae3f179f1` |
| `point_grounding_probe.py` | `bdd39fc30195e28d2a1a151bd78383a568f81f77fca81baa26765b3f81f4a09a` |
| `adapters/locateanything.py` | `5dbc90c5004571cec07486635775040e0bf952df7555b0205d7d367ee67c2704` |

## Exact four-image packet

Use the existing physical sensor seal, motion-source admission and capture
mapping. Select local suffix indices 0 and 16, corresponding to merged source
capture IDs 31 and 47. The fixed order reverses arm order at the second
boundary. Every call starts cold; no earlier image, output or chat history is
reused.

| Call | Source | Capture |
| --- | --- | --- |
| 1 | neck-present | `scene_after`, scene sequence 2, local 0 |
| 2 | neck-away | `scene_after`, scene sequence 2, local 0 |
| 3 | neck-away | `additional_close`, step 30/control 7, auxiliary sequence 16, local 16 |
| 4 | neck-present | `additional_close`, step 30/control 7, auxiliary sequence 16, local 16 |

Decode only `rgb` from each hash-bound NPZ. Preserve all 384 × 384 uint8 pixels;
apply no crop, annotation, resizing outside the unchanged native processor,
ROI highlight, previous-point overlay or image difference. The sole model text
is the question above. Source paths, case names, conditions, event identity,
actions, times, own signals, depth, calibration, mechanical labels and motion
results remain outside model messages. Provenance belongs in the recorder.

All four calls retain their raw return and token audit. Malformed, absent,
multiple, out-of-frame or incomplete/length-limited output is retained as
nonadmission and does not trigger repair or a new prompt. Infrastructure
failure preserves the partial attempt and stops remaining calls without retry.
Admitted output is just the existing native normalized point, continuous image
coordinate and floored integer pixel index; there is no depth sampling or 3D
projection. Seal all sensor-side results before interpretive or privileged
evaluation.

## What the outcome would mean

The away bottle was relocated, not removed from the world. If visible elsewhere
in the image, a useful fresh POINT should localize that bottle there; an away
response is not expected to abstain merely because the closing region is empty.
If the bottle is occluded or outside the view, its current visible identity
remains unresolved. The target-present cell also requires inspection: its
label does not prove that a particular visible surface is bottle material.

Inspect all four actual full RGB images and their returned points together,
retaining nonadmissions. Compare locations with visible bottle, finger and
background evidence; record uncertainty explicitly. Membership in the old
492-pixel region is at most a descriptive comparison, not a correctness label.
Do not add an evaluator-derived image, favorable crop, retry, prompt variant,
new tracker or point-selected motion cohort.

Fresh bottle localization away from the old hand region would support testing
an identity-grounded sensor interface next. Repeated hand/background pointing,
nonadmission or ambiguity would expose a limit of this native semantic query.
Neither outcome verifies persistent material correspondence, attachment,
support clearance, slip resistance or holding.
