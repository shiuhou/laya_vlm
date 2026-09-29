# Matched BOX versus POINT grounding probe

Registered before GPU execution. The hypothesis is that the existing LocateAnything
checkpoint can identify the intended handle with a semantic point even when its
box includes other handles. No new model, prompt search, simulator, live policy,
or runtime perception change.

Freeze all18 archived full RGB frames and existing query from the accepted
init0/1/2 raycast-v02 collections. Preparation verifies prior source/frame hashes
and extracts RGB-only artifacts. Generation runs in a separate process reading
only these artifacts and a generator-safe manifest. Depth, oracle supports and
ray depths are evaluator-only and consumed in a later process.

For each frame make exactly one BOX and one POINT call, alternating BOX-first and
POINT-first by frame index. Use the same phrase:
`the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground`.
BOX template: `Locate a single instance that matches the following description: {phrase}.`
POINT template: `Point to: {phrase}.`
Keep existing local weights, bfloat16, full-image processor, hybrid generation,
temperature0, do_sample=false, max_new_tokens256, use_cache=true. No crops,
history, retries or tuning. Stop on concrete model/runtime failure; preserve it.

Record input token IDs/count, image grid, settings, raw output, actual generated
token IDs observed through a transparent batch_decode wrapper, frame/source/model
hashes, latency and CUDA peak memory. EOS and token limit are separately audited;
a parseable point does not establish no truncation. Wrapper delegates unchanged
arguments to the original decoder. If observation is unavailable, fail the audit
rather than claim complete generation.

Parse `<box><x><y></box>` points and four-coordinate boxes with integers0..1000.
Distinguish single, multiple, mixed, none, malformed/no-grounding and out-of-frame.
Multiple points are retained and never reduced to a preferred point. For primary
point comparison only a single valid point is evaluable. Boxes preserve historical
first-box baseline semantics but all boxes/counts remain visible. Coordinates are
continuous image-boundary coordinates (x/1000*W,y/1000*H). Sample containing pixel
floor(x),floor(y), no clamping. Out-of-frame and invalid depth are explicit unknowns.
Backproject the containing pixel center with existing half-pixel convention.

Primary evaluator: point on exact visible-target oracle mask, plus distance to
nearest target pixel. Compare fresh first-box center and archived first-box center
on identical RGB states. Preserve all18 and report six hard late boundaries
(init0 steps120/140/144/152/155 and init2 step144) separately. Measure depth-derived
3D point distance to nearest independently raycast visible-target surface; do not
compare point-to-centroid as equivalent accuracy. No action/execution inference.

Empty grounding can be recorded as abstention but has no calibrated confidence.
No score=1 probability is invented. Correct visible-target point is not a grasp
pose, contact relation, object extent or a high-level plan. Same-depth support
extraction remains a later question even if target identity improves. Optional
point-guided region growth is excluded from this probe. Existing depth-group
selection is also deferred to keep this test about semantic point identity.

Fresh BOX versus archived BOX agreement is reported; cross-process equality is
not assumed. These18 already-inspected correlated development states establish
only a diagnostic, not generalization. Keep all failures and no oracle-corrected
sensor output. Stop after the36 calls and evaluation; no policy integration.
