# Task2 single semantic-part BOX condition

This prospectively fixed probe changes exactly the requested region in the
existing BOX template: `the neck of the wine bottle`. The question is whether
explicitly requesting a manipulation-relevant region changes the semantic
grounding beyond the sealed object-level baseline. This is a researcher-specified
semantic target, not a VLM-generated plan, verified surface or certified grasp
point. A neck-localized box could motivate further work but cannot establish
that richer metric geometry is unnecessary.

## Fixed input, call and budget

Use only the same full 384 × 384 RGB from
`interaction-observability-paired-01/close/0000.npz`, SHA-256
`3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`.
The image is already inspected development data. Depth, calibration, evaluator
labels, old responses and successful grasp poses do not enter the model. No
successful old grasp coordinates inform this query, point or evaluation.

Exact question:
`Locate a single instance that matches the following description: the neck of the wine bottle.`

Use the existing LocateAnything-3B checkpoint at
`/home/junhongli/models/huggingface/LocateAnything-3B`, content ID
`4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`.
Keep GPU0, BF16, the existing native hybrid greedy SETTINGS and 256 generated
token cap. Budget is exactly one new model query, with 300 s inference timeout,
no inference retries, alternate wording, extra models, offsets, new capture,
render, physics, replay, FK or scene construction. A setup failure before
inference is preserved; any proposed infrastructure-only continuation requires
independent review and a separately numbered attempt. A post-call failure,
timeout, missing/multiple/malformed BOX, missing terminal EOS or truncated
generation ends the condition without another call.

## Reuse and preflight

The minimal `task2_neck_box_support` wrapper temporarily binds only QUERY,
QUESTION and PROTOCOL in the unchanged `task2_box_support` implementation.
Settings, raw schema, worker, token audit, parser, depth extraction, projection,
seals and proxy analysis are reused without edits. The baseline source and
sealed `task2-box-support-run-02` output remain unchanged.
The wrapper checks the reused core source SHA-256 before each mode:
`9986c4f79578dd4e2691726f21df7ba0706ac8b9876a255ca078eed2f9bb43a6`.

Before inference, run the existing actual processor-only preflight on this exact
fixed question and RGB with local files only. It constructs no model and performs
no inference. Require input_ids, attention_mask, pixel_values and image_grid_hws;
record native types/shapes/dtypes, exact input token IDs and serialized NumPy or
tensor grid. Run the existing nine support tests and the wrapper's synthetic
geometry-invariance/failure-restoration test. Freeze clean code, protocol and
tests, then obtain independent prospective review of this diff and actual schema
receipt before the single call. No output-dependent edit is allowed.

## Unchanged point, support and seals

Preserve RGB/token/processed-pixel fingerprints, model identity/settings, raw
return, actual decoded token sequences, EOS and latency. Seal raw generation
before parsing. Admit exactly one complete valid BOX and retain the continuous
box and provider integer conversion. Preserve the unchanged one-fifth interior
depth crop, valid range 0.01–5 m, median and original box-center ray point P.
Retain all candidate RGB-D support G with pixel centers (u+0.5,v+0.5), exact lower
and upper median contributor sets including ties, depth MAD/std/min/max, center
sample and its median difference. Empty valid crop remains unknown. No support
cleanup, segmentation, point correction or derived grasp offset is permitted.

Seal model and sensor outputs before opening evaluator labels, inspecting the
new BOX overlay or comparing to the baseline. The existing model's score of 1
is not semantic confidence. P is a box-center/median-depth proxy, not guaranteed
to be a measured neck surface or a suitable grasp position.

## Registered descriptive comparison and limits

After sealing, inspect the unmodified RGB and fixed box/crop overlay separately
from the evaluator overlay. Describe the requested region as visibly neck-localized,
full-bottle, wrong region or ambiguous. The fixed qualitative rubric is: a box
focused on the visible narrow upper bottle region is neck-localized; one spanning
the narrow upper region and main wide body is full-bottle; a clearly different
visible region is wrong; unclear/occluded boundaries or conflicting evidence are
ambiguous. Do not create a hidden neck pixel label,
fit a threshold or select another point. Retain visible table/background and
boundary ambiguity in the crop. Image inspection is descriptive, not a new
model call or annotation used to modify output.

Use only the archived bottle ID-rendered membership proxy, SHA-256
`2a474be6d469dc2df45edfb03c97b23a1adf021f9a48551994a619f501a0b747`.
Reuse fixed crop overlap, visible-bottle coverage, center and median-contributor
membership, and one-pixel 8-neighbor interior/boundary/exterior strata. The mask
tests bottle membership only; it cannot certify the neck, depth ownership or
grasp readiness. MSAA, raster boundaries, shared calibration and unknown cache
times remain limitations. Fractions are agreement counts, not calibrated purity
or confidence; resolved depth ownership stays null.

Compare the sealed object-level baseline and this single condition by raw
response/EOS, box/crop, valid support count, median depth, P, descriptive RGB
region, and the same limited bottle-proxy counts. Report the P displacement as
descriptive only, without choosing the better point. Baseline journal SHA-256:
`51dd621269c6da151c39e9b1bd9b0cdf15a890eb2e4af28a59caaea065201a3b`;
baseline sensor SHA-256:
`be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead`.
One inspected fixture cannot establish generalization, grasp success, policy
quality, or that semantic-region wording resolves the metric geometry problem.
No subsequent physical action is authorized by this probe.
