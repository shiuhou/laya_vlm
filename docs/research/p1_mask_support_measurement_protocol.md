# Prospective mask-support measurement repair — 2026-10-07

Frozen SAM inference revision: `b5ada28becf7b84c57d4ea5c5dc41e78a1f42182`.
Frozen original diagnostic/evidence: `26648a3`, tagged separately before edits.
Reanalysis source: `runs/p1/box-sam2-grid-complete-20261007`, all six native
masks/logits and the exact init25/26 recorded sources. No new model inference.

## Only intervention: measurement domain

Segmentation condition `native-mask-depth/2`:

`depth availability = valid_depth_inside_complete_native_mask / native_mask_pixels`

Valid depth uses original finite/min/max rules. Native mask pixels outside the
original BOX are retained in this availability domain. Geometry continues fitting
only the original BOX with outside-mask depth UNKNOWN. Report full-mask and
within-BOX counts/availability separately. Empty mask has unknown availability
and yields UNKNOWN; no fabricated denominator.

`coverage = mask_pixels_inside_original_BOX / original_BOX_pixels`

Coverage is a separate diagnostic, never a depth-availability gate. Keep the
original0.50 availability threshold and every original absolute support,
component ambiguity/connectivity, plane support/RMS/spread, edge, uncertainty,
tool and semantic-association/execution gate. No BOX shrink, mask crop, fill,
morphology, IoU winner, merged mask, candidate reordering or first-VALID exit.
Candidate usability/semantic identity remain independent of local geometry VALID.

Default nonsegmented geometry keeps the historical BOX denominator and identical
results. Explicit `original-box-depth/1` reproduces old segmented measurements.
Old source guards remain unchanged; the new replay uses a separate exact-source-
hash registration. Original baseline source is still executable under its tag.
Preregistration checks original config bytes and AST identity from component
assembly through plane/edge/uncertainty/tool/candidate-order code, then seals the
new source/condition before replay.

## Run and inspect

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_mask_support_reanalysis prepare \
  --output runs/p1/mask-support-reanalysis-20261007
.venv-p1/bin/python -m embodied_runtime.experiments.p1_mask_support_reanalysis reanalyze \
  --output runs/p1/mask-support-reanalysis-20261007
```

Verify sealed raw artifact hashes and source identities; preserve all native
ordinals0/1/2 for both samples. Before new results, require exact JSON-equivalent
defaultBOX results2/2 and legacy segmented results6/6 against sealed evidence.
Then complete the repaired evaluation for every mask, seal before visual review,
and report the first actual downstream boundary and every point in canonical
order. These development images have no independent human annotations;
candidate identity must stay UNKNOWN, not be inferred from geometry or scores.

Necessary validation: three additional availability/empty/absolute-support cases
plus existing source-binding cases (13 focused tests), byte/result regressions,
AST/source seals and changed-file lint. No broad duplicate suite/model calls.

## Close development tuning and enter formal P1 evaluation

After this single repair, stop all threshold/segmentation tuning on init25/26.
Both possible outcomes transition to frozen50frame evaluation: no usable points
means evaluate observability/failure breakdown; any geometry point is only
development evidence and must be evaluated against the independent human regions.
An outside-region point is a semantic/segmentation identity failure, not task-
valid geometry success. UNKNOWN/NOT_VISIBLE labels remain explicit; no ground
truth is supplied to generation, selection, tracking or policy.

Pin the existing50-frame packet, recorded sources,100 fixed-query BOX records,
unchanged annotation/rules/seal and this repaired pipeline before future mask
generation/scoring. No new LocateAnything/SAM calls are allowed in this round.
If50-frame mask artifacts are unavailable, report that exact prerequisite as
pending rather than claiming repaired-pipeline evaluation from old BOX-only data
or from the two development images. This is an explicit evaluation handoff,
not more development tweaking.

Next route: frozen50frame evaluation → ten real temporal sequences → P1 GateA/B/C
→ P2a/B0. Continuous tracking/reference/VERIFY remain unearned until those gates;
no tracker/PUSH/Qwen/Laya or architecture change in this repair.
