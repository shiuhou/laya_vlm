# P1 semantic-output typed contract repair — preregistration

Registered before new-condition reanalysis of the sealed `f2af8d8` evidence.
This is an interface intervention, not completion/reclassification of the old
strict-single-point experiment. Historical raw outputs and results stay intact.

## Fixed conditions and scope

Reanalyze only the complete two-call init25 wrist drawer-front pair in
`runs/p1/drawer-pair-gpu-20261007/`, using the original
`runs/p1/surface-dev-20261006-capture02/` RGB-D/calibration. No new inference,
query/checkpoint/decoder change, human annotation, simulator truth, geometry or
tracker gate change, robot action, Qwen/Laya integration or PUSH.
Legacy parsing remains available unchanged; explicitly select `typed-v1` for
this new condition. Record clean revision, protocol hash, raw-response hashes,
source identity and original inference seal. Use a new analysis directory.

## Typed schema and fixed admission rules

A reply contains an optional single leading `<ref>...</ref>` description,
followed by ordered `<box>...</box>` atoms and terminal `<|im_end|>`.
Whitespace between atoms is allowed; unrecognized/trailing text, nested or
unbalanced tags, malformed atoms and nonterminal/missing EOS reject the entire
reply. Generation audit must independently demonstrate terminal EOS, correct
recorded token count and no over-budget generation. A textual EOS alone never
licenses an incomplete reply.

Atoms are typed by arity: POINT has two integer coordinates; BOX has four;
`none` is an explicit NONE atom. Integers use the checkpoint's [0,1000] native
scale. Conversion is x/1000*width, y/1000*height without snapping or clamping.
POINT must lie within the image's half-open pixel domain. BOX must have positive
width/height and lie within the image's closed edge domain. NONE is admissible
syntax but is not a usable grounding; NONE mixed with coordinates is rejected.
All atoms retain raw text/span, type, native coordinates, converted coordinates
and original order. Confidence remains uncalibrated/unknown.

POINT request: exactly one valid POINT is required. Valid BOX atoms in the SAME
complete reply are typed auxiliary evidence and retained, not additional points,
ROIs, constraints, target confidence or fallback. No requirement that an auxiliary
box contain the point is invented. Zero or multiple POINTs reject admission,
even identical duplicates. Any malformed auxiliary atom rejects the entire reply.

BOX request: one or more valid BOX atoms required; use every BOX in original
order, without ranking, merging or choosing the largest. Any POINT atoms remain
auxiliary evidence and cannot seed association. Multiple ROIs can create existing
cross-ROI ambiguity; this is preserved.

The separate registered BOX call alone defines search ROIs; the separate POINT
call alone defines the unique anchor. Source/image/query identity must match.
The repair does not reinterpret semantic identity: a unique geometric support
is only BOUND_HYPOTHESIS, not verified drawer-front identity, fixedness or safety.

## Stage order and stopping rules

1. Freeze schema/rules; implement focused boundary tests, preserving legacy tests.
2. Seal clean implementation and new-condition manifest before reanalysis.
3. Parse both full replies and enforce typed admission BEFORE any geometry.
4. Run unchanged surface inventory/association on independently supplied BOX ROI.
5. Inspect actual RGB/support/anchor evidence. If no unique valid requested
   surface, stop; no tracker and no downstream reference experiment.
6. Only after both geometry and requested-surface review pass, separately record
   offline tracker initialization with unchanged gates. Initialization is not a
   temporal tracking or live freshness claim. Stop if tracker fails.
7. If those gates pass, inspect independent fixed cabinet reference observability.
   The old incomplete reference POINT remains rejected, regardless of typed atoms;
   absent independent valid reference, VERIFY stays UNKNOWN. No new model call is
   automatically permitted by this sealed-output analysis.

## Interpretation

Competing predictions: (A) typed admission exposes a correct uniquely supported
front-surface anchor; (B) format repair exposes wrong/no/ambiguous surface, locating
the next failure at grounding/geometry; (C) source or completion integrity fails.
Compare legacy and typed results on identical raw bytes. Do not call format
admission itself improved perception or completed P1 acceptance. Do not tune
rules after observing the new-condition surface outcome.
