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

## Independent stored-result and report review

**Stored-result, source-admission and derived-report PASS** for `task2-point-region-control-run-01`, scientific freeze `d4045496dc330529eb8f637bd46d556fc9bc0598`, producer report `5ef2673`. The [independent checker](../../../experiments/task2_point_region_evidence_audit.py) and [machine-readable receipt](task2_point_region_control_independent_audit.json) validate all 24 journal records, all 137 frozen source-file identities, the prospective receipt preceding execution, exact processor-preflight identities, both fresh-process configurations, native inputs, raw tokens, sensor seals and portable results. Root's earlier prospective review `e3672e7` and 53 focused passing tests remain the prospective evidence; this audit does not repeat either model call or processor preflight.

| Condition | Generated tokens | Terminal EOS | Normalized point | Containing pixel | Source depth (m) |
| --- | ---: | --- | --- | --- | ---: |
| Whole bottle | 10 | yes | (571, 496) | (219, 190) | 0.9939957857131958 |
| Bottle neck | 13 | yes | (571, 451) | (219, 173) | 0.9737445712089539 |

Both counts are strictly below the unchanged effective limit of 256. Every generated token ID was checked against the pinned static vocabulary and exactly reconstructs the preserved raw response; no tokenizer/model was constructed. Each response contains exactly one native POINT group. The original rule would still reject an EOS-terminated 256-token response. No truncation, prefix salvage, clipping, corrected pixel or alternative depth was used.

Both input RGB arrays match the original full 384×384 RGB byte for byte. Every native input token, attention-mask entry, image-grid value and BF16 pixel value matches the reviewed processor preflight. The saved float32 image tensor is an exact BF16 representation, with matching shape `[784,3,14,14]` and hash across conditions. Input token counts are 229 and 232. The model identity map, original whole/neck BOX configurations, BF16/eval state, tokenizer limit/EOS and loaded environments match exactly; fresh process IDs are 802086 and 802640 on GPU1. The reviewed source seeds each fresh process with 1, retains the native settings/default chunk size and issues exactly one call per child, whole before neck. Recorded weight identities were verified as maps; this audit did not reread model-weight bytes.

Independent scalar evaluation of the stored K/T equations verifies the source depth and projected pixel centers `(219.5,190.5)` and `(219.5,173.5)`, with maximum absolute discrepancy `1.1102230246251565e-16 m`. The stored world points are respectively `[-0.11673469557117522, 0.058971097589474636, 0.9883583307522877]` and `[-0.12337491393454869, 0.05776965007435101, 1.0288145621732854]`. Native POINT uses normalized raster coordinates, then **floor**, then the containing pixel's depth and center `+0.5`; it does not use the separate LK nearest-index convention. Capture read time remains 0.5 s, with exact cached RGB/depth sample times unknown.

Each raw return seal precedes its sensor-result seal. The complete ordered batch journal contains both sensor hashes and zero retry/physics/render counts. The separately reviewed evaluator requires completed batch termination and verifies both sensor results before recording its start and opening the mask. The saved start record binds the completed journal and both exact sensor hashes with `labels_opened=false`; it contains no wall-clock timestamp, so evaluator ordering is supported by those dependencies and reviewed code rather than an independent evaluator-time measurement. The original evaluator's pending visual field remains unchanged.

Both selected pixels independently evaluate as **True / proxy_interior** under the frozen whole-bottle rendered mask and its fixed 3×3 rule. This supplies no neck truth label or resolved-depth ownership. The reviewer separately opened the actual uncropped RGB figure: the whole-bottle marker is visibly on the wider upper body near the shoulder; the neck marker is on the narrow neck below the cap, 17 array rows higher at the same column. This agrees with the later separately sealed producer visual receipt. It is a qualitative Codex inspection, not human adjudication, semantic confidence, grasp quality or a new sensor admission criterion.

The complete portable summary equals its raw sources field for field, inventories every raw artifact, and preserves the original evaluator plus separate visual receipt. The portable figure is byte-identical to the raw figure. The findings preserve the earlier neck BOX failure (260 tokens, no EOS) and limit the positive POINT result to researcher-specified part wording on this one fixture. They claim neither independent region choice nor accuracy/repeatability, depth ownership, physical feasibility or grasp success. No point was executed by this experiment. This receipt closes the source and report audit; further conditions retain their own prospective gates.

| Artifact | SHA-256 |
| --- | --- |
| Batch journal | `57d9ddcd1348303254d32cf844b0a29e75b90c4eef585a8add4c72afd30b508d` |
| Whole sensor result | `87fb2c2b9587ae1cd08f85d4bf331288c20b4b50b65aa6f0132b78294eb3cef5` |
| Neck sensor result | `fd6edea327618a8bb86a52dafe48fe2d857a2e71fa7677bdcadb89d65657fd0d` |
| Portable summary | `215456189695f6f8c62aff93856c973eb34a101107f7f41164e68ac3fc709feb` |
| Actual RGB figure | `89abdd7933dfb996fb0742a804fcf1ca5fe0a70ca15fc3fa6e900f157c653fd4` |
| Producer visual receipt | `7553fa263d7605faf1634db85ba01c21d2c783b1f2da8ffc803e37e37cfbcc84` |
