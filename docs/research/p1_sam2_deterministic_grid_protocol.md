# P1 SAM2 deterministic-grid compatibility and matched diagnostic

Follow-up to `3aa6aea`/execution `305056a`. User authorized the compatibility
repair and completion of the two-sample diagnostic, without stopping at setup
milestones. Prior failures remain sealed; use a fresh exclusive run root.

## Exact intervention

Keep official SAM source/config/checkpoint and scientific settings unchanged.
For the loaded instance only, override
`sam_prompt_encoder.pe_layer.forward` to replace float32 cumulative sums of
ones with `arange(1, h+1)` / `arange(1, w+1)`; preserve subtraction0.5, division
and native `_pe_encoding`. No learned weights, `forward_with_coords`, threshold,
postprocessing, query or BOX change. Strict deterministic algorithms remain on;
no `warn_only`, disabled flag, or repeated prediction after failure.

Before either image, require native64×64 and record bitwise equivalence:

1. Original CPU dense forward versus repaired CPU forward, same copied state.
2. Original CPU cumulative coordinate grid transferred to GPU versus repaired
   GPU arange grid.
3. Those two grids encoded by the same GPU `_pe_encoding` and learned buffer.
4. Gaussian buffer bytes unchanged; overlay source hash preregistered.

Integers1..64 are exact float32 values. This verifies the grid/PE at the actual
shape/state; it is not a claim of end-to-end original-versus-repaired GPU mask
equivalence, since the strict original CUDA path is unsupported. No original
nondeterministic GPU reference run is permitted. A byte-identical writable RGB
copy avoids torchvision's readonly-input warning; this changes no sensor pixels.

## Execution and interpretation

Fresh registration with `--deterministic-grid --reuse-boxes-from
runs/p1/box-sam2-continuation-20261007`; reused BOX stage must pass existing
whole-output parse/source/seal checks. Zero new LocateAnything calls. Init25/26
development wrist images, all three native multimasks retained in original order.
Seal raw logits/lowres/scores/masks before geometry or visual inspection.

Keep original BOX denominator, outside-mask depth UNKNOWN and geometry gates.
Measure mask occupancy, depth ratio, geometry status/reasons, every target-point
candidate, and component/plane metrics only where actually computed. Do not
complete skipped stages to make a rejection look like absent physical geometry.
Measure encoding/prediction and offline geometry time separately, not realtime Hz.

Inspect both raw RGBs and all six mask/candidate overlays after sealing;
independent agent review is development diagnosis, not human evaluation labels.
Ordinary UNKNOWN/AMBIGUOUS results are completed for both samples without tuning.
Freeze/report the matched diagnostic and substantive association/gate conclusion,
not just environment completion. No automatic denominator repair, mask winner,
query/point/view tuning, tracker, reference completion, PUSH, Qwen or Laya.

Minimal validation: actual native-grid numerical gate, source-bound inherited
BOX integration, stage seals and changed-file lint. No broad duplicate tests.
Concrete new data/numerical/runtime failure remains a recorded boundary; small
successful setup milestones do not end the work.
