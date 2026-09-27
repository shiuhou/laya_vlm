# Prospective review: two matched native POINT descriptions

**PASS** for clean producer `d4045496dc330529eb8f637bd46d556fc9bc0598`,
before either inference. Root inspected the full wrapper, protocol, synthetic
tests and unchanged native POINT/admission/token-audit helpers. Independently
ran all15 new tests: **15 passed in0.17s**.

Root independently reran the actual processor-only preflight using the
LocateAnything environment, local files only. Its complete JSON and SHA256 are
identical to the producer receipt:
`34bac09d5a1170fe88f339c5896147944533b4b94f989d277762d2781a8aa498`.
Root receipt: `runs/autonomous-research/task2-point-region-control-root-preflight-01.json`.
There were no model constructions, calls, simulator or renderer use. The exact
229/232-token questions share identical full-RGB BF16 image tensors and grid.
The differing questions retain the two prior exact descriptions.

The pair uses the original checkpoint/configuration and native256-token hybrid
settings, fresh seeded processes on one recorded GPU, and no preceding calls.
Loaded model configuration, own process input and image bytes are gated against
the preflight; neither depth nor evaluator labels enter the model. Raw native
return and actual decoded token IDs seal before validation. Missing EOS, length
limits, extra/malformed groundings and invalid depth stay nonadmitted without
salvage. A nonadmission does not select away the second registered condition;
infrastructure failure stops with preserved partial evidence and no retry.

Strict original POINT raster association and pixel-center RGB-D projection
remain unchanged. This is not the separate LK coordinate convention. The
evaluator cannot open the archived whole-bottle mask until both sensor outputs
seal; it has no neck truth, depth-ownership or grasp-quality label. Actual full
RGB and both condition panels require post-seal inspection. No result selects
a physical target, policy, action or retry.

Admission covers exactly the registered whole-then-neck pair after checking GPU
availability. It tests use of a researcher-specified part description on one
development image, not independent planning, general grounding accuracy or
grasp competence. Record the review identity beside the run. No production
runtime or prior evidence changes are authorized by this experiment.
