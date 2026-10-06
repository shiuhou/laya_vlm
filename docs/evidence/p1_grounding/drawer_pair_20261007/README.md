# First unstarted drawer-front pair — 2026-10-07

**Surface association remains UNKNOWN; tracker was not tested.** This separately
registered pair completed both model calls, but POINT's complete response was
mixed rather than a strict single point. Do not confuse completion of these two
calls with completion of the original eight-call experiment.

## Question and controls

The earlier reference POINT failed without EOS and prevented the drawer-front
calls from being reached. The user requested continuation. We registered the
first previously unstarted canonical drawer-front pair, init25 wrist camera,
before executing it. We did not retry the failed reference or resume its batch.

Inference code: clean `f077df8`; GPU UUID
`GPU-293fca5f-bdb8-2235-fa2e-18ab6c488b36`, logical `cuda:0`, BF16.
Original 384×256 RGB-D/calibration, semantic phrase, BOX/POINT templates,
checkpoint bytes, hybrid decoding, max_new_tokens256, temperature0, no sampling,
cache settings and all geometry/tracker gates were unchanged. The only new
experimental scope was one independent BOX/POINT pair. All 27 original evidence
files and the preceding reference failure seal remained unchanged. No source
capture, annotation, simulator target state, controller or robot action was used.

| Call | Input tokens | Generated tokens | EOS | Format | Generation time |
| --- | ---: | ---: | --- | --- | ---: |
| BOX | 208 | 39 | Yes | Single box | 0.752360 s |
| POINT | 200 | 44 | Yes | One point **and** one box; mixed | 0.370823 s |

POINT was not truncated this time. Its full reply contains both
`<box><671><246></box>` and `<box><673><350><1000><997></box>` before EOS.
The existing strict semantic admission rejects the entire mixed response. No
first-point extraction, response rewriting, nearest surface or label is used.
This is a semantic output/interface mismatch before admitted surface binding,
not a demonstrated geometry, tracking or physical execution failure.

## Related evidence and competing explanations

A read-only audit of archived `point-grounding-probe-02` found 18 POINT replies
under identical checkpoint content ID, versions and generation settings:
14 strict single-point+EOS, four mixed point+box+EOS, zero incomplete POINTs.
The old images were 384×384 and the query asked for a metal handle; no old oracle
or annotation evaluation was reused here. This contradicts systematic POINT
format incapability, but does not establish current drawer semantic accuracy.

Native code explicitly recognizes a two-coordinate `point_box`; the pattern
itself is nonterminal and generation may continue until EOS. Hybrid decoding can
also emit four-coordinate boxes. Query/image dependence and decoder behavior
remain competing explanations; reading code is not a causal intervention.
The current drawer observation differs from the failed fixed-reference query
in both semantic target and camera/image, so it does not isolate either factor.

The [raw RGB plus BOX diagnostic](drawer-box-rgb.png) preserves the model search
region. No rejected POINT is displayed as an accepted anchor. Image clipping and
mixed surfaces remain visible, but this is agent development evidence, not new
independent human labels or geometric push acceptance.

## Admission-order implementation deviation and correction

The first association analyzer at `f077df8` still enumerated **five measured ROI
supports** before rejecting the mixed POINT. It accepted zero points, bound zero
surfaces and initialized no tracker, but this violated the registered
admission-before-geometry order. That exploratory inventory and its full raw
supports/residuals are retained and explicitly excluded from gate acceptance.

At `34b799c`, the offline analyzer was corrected to reject non-single POINTs
before any geometry work. It was run on the **same sealed two model responses**;
there was no model retry. The corrected analysis creates zero inventory files,
empty bindings/point coordinates, `geometry_evaluated=false`, reason
`POINT_RESPONSE_NOT_SINGLE_POINT`, and tracker
`NOT_TESTED_SEMANTIC_ADMISSION_FAILED`. The change affects experimental stage
ordering only, not the generic runtime, model, geometry/tracker gates or parser's
admission standard. Ruff passed; no broad tests or additional inference ran.
An independent agent verified both analyses, source/seal integrity and scope.

## Decision

Requested surface association is **not established** because there is no admitted
strict POINT. Tracker is **not tested**; fixed cabinet reference and VERIFY stay
**UNKNOWN**. P1 task acceptance remains pending. Stop this pair at semantic
admission. Do not run init26, retry a failed call, modify prompts/decoder/token
ceilings, relax a gate or redefine mixed replies as accepted under this condition.

The next decision concerns the semantic output/interface boundary, with the
current failure preserved. Geometry thresholds, controls and more hierarchy do
not address the demonstrated failure. Any future accepted surface association
still leads to independent fixed cabinet reference observability, not PUSH.

Full preregistration, raw prompts/token IDs/model/config identity, sealed
responses, original exploratory inventory and corrected admission are in
[the evidence archive](drawer-pair-evidence.tar.gz), with
[SHA256 index](artifact-index.json) and [summary](summary.json).
Local inference: `runs/p1/drawer-pair-gpu-20261007/`.
Only the disposable process-specific model-code cache was removed after exit;
original/canonical evidence remains intact.
