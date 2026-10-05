# Temporal observation attempts — P1 NOT PASS

Ten physical acquisitions produced 344 existing control commands and 354
dual-camera bundles. All controls/returns use the existing executor; scene
perturbations belong to an explicit evaluator fixture, not a robot policy.
Robot/environment contacts were checked before/after each existing control,
with none observed; substep absence is not certified.

| Cases | Inspected observation | Qualification limit |
| --- | --- | --- |
| T01 | Modest wrist perspective change, approximately 10° | No supported face/reference track pair. |
| T02 | Larger wrist perspective change, approximately 28° | No supported face/reference track pair. |
| T03–T06 | Real translations/reversals | Intended EEF occlusions did not occur; cropping is not occlusion. |
| T07 | Drawer movement relative to cabinet is visible | Evaluator fixture; no valid semantic track. |
| T08 | Drawer movement reversal is visible | Evaluator fixture; no valid semantic track. |
| T09 | Cabinet/reference translation is visible | Semantic identity continuity is not verified. |
| T10 | Perspective change and real concurrent LocateAnything inference | Selected RGB shows no intended EEF occlusion; actual late replies recorded, no online tracker installed. |

The temporal investigator viewed both camera contact sheets for T01–T09; the
parent also viewed selected T03/T06/T07 sheets and the stored
[T10 raw contact sheet](T10-raw-contact-sheet.jpg). T10 selected source sequences
are 1, 19, 38 and 57 in both cameras. All original frames are retained locally;
the selected sheets do not replace the complete recording.

**Zero target-valid qualifying sequences.** Forty initial semantic hypotheses
are LOST with `SEED_DEPTH_OR_CONTEXT_INVALID`; the remaining 1,376 updates report
`RESEED_REQUIRED`. All 708 VERIFY results are UNKNOWN. No successful initial
track exists, so these data do not isolate temporal association under valid
initialization. No hidden reseed or invented calibrated covariance was used.
The first-case diagnostic independently finds off-image template context and
0.138–0.299 m depth spread, exceeding the unchanged 0.03 m limit.

## Explicit acquisition confound

The configs use 384×384, chosen from sensor/world defaults instead of matching
the sealed static 384×256. This was an implementation oversight caught during
integration. It was recorded in the configs before acquisition and receives
its own calibration identity, but is **not a matched temporal extension** of the
50-view condition. Different model boxes cannot be attributed causally to time
or motion across these resolutions. The original static result remains intact.
No silent relabeling or automatic full rerun was performed.

## T10 asynchronous evidence

The source-bound requests use the original fixed queries/settings and only RGB.
Inference actually overlaps acquisition, with no injected delay. Responses arrive
1.40–2.85 s after source capture and exceed the recorded original 1.2 s diagnostic
proposal deadlines. Offline capture-time replay is separate; it does not turn
these stale replies into live accepted observations or demonstrate online
binding rejection.

The first T10 launch failed before simulator construction because CUDA mask 0
and EGL device 3 were incompatible. Its directory and failure remain preserved.
The separately named `T10-env-fixed` launch uses CUDA/EGL 0 and identical physical
recipe. It supplies the first physical T10 acquisition, without a hidden episode
retry or any policy/gate change.

## Artifacts

- `raw-summary.json`: all acquisition/replay summaries and recording/artifact hashes.
- `first-seed-diagnostic.json`: unchanged-gate depth/context failure inspection.
- Local complete recordings: `runs/p1/temporal-observation-20261005/T01…T09/`,
  `runs/p1/temporal-observation-20261005/T10-env-fixed/`.
- Initial offline RGB-only semantic hypotheses: `runs/p1/temporal-initial-semantics-20261005/`.
- Actual T10 requests/responses: `runs/p1/temporal-semantic-async-T10-env-fixed-20261005/`.
- Every inspected T01–T09 case retains `inspection/{agentview,robot0_eye_in_hand}.png`
  and complete `analysis/perception.jsonl`.

Tooling/config commits: `4125b55`, `c39c08b`; semantic worker and source-binding
commits: `8860d6c`, `3741c87`, `531c92c`. Manifests preserve actual run revisions
and source hashes. Only focused tooling checks were run; no full historical test
suite, Qwen/Laya integration, PUSH or further physical attempts followed.
