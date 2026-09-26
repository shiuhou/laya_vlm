# Independent fixed neck-BOX review

**Prospective PASS for clean `aee8f298b6e24f8385227497b0bd969020e4fd48` before the single inference.** The scientific wrapper/test freeze is `4d88bdee65cd0e0d68c79f64e4639f1cf0b1e924`; the later commit only pins the existing correct interpreter, records the zero-inference setup failure, and provides reproduction commands. No scientific code, query, setting or extraction rule changed in that amendment.

The minimal wrapper checks the exact successful `task2_box_support.py` hash and temporarily binds only QUERY, QUESTION and PROTOCOL, restoring all three in `finally`. The exact new question is `Locate a single instance that matches the following description: the neck of the wine bottle.` It is a researcher-specified semantic-part condition, not an autonomous choice of affordance or a generated manipulation plan. One unchanged full RGB, the pinned LocateAnything checkpoint, GPU0/BF16, existing hybrid greedy settings, 256-token cap, 300 s inference timeout, and no inference retry remain fixed. No depth, label, previous response, successful grasp pose or robot geometry enters the model.

The raw-generation-before-parser seal, EOS/token audit, single-BOX admission, integer conversion, fixed one-fifth interior depth support, median-center-ray P, complete RGB/depth G with explicit pixel-center convention, median contributor ties, and separate post-seal archived-mask analysis reuse the unchanged implementation. Empty/rejected results remain failures or unknowns; no wording sweep, alternate point, support cleaning, offset, model fallback, new scene, rendering, FK, physics or subsequent action is authorized.

The fixed visual rubric distinguishes a box focused on the visible narrow upper region, the whole bottle, a clearly different region, and ambiguous evidence. It is qualitative inspection after sealing, not a neck segmentation or calibrated correctness measure. The archived bottle mask can measure bottle-proxy membership only; it cannot establish neck correctness, resolved-depth ownership, jaw fit or grasp readiness. All original raster/cached-time/shared-calibration limitations remain. A changed P is a descriptive result and cannot be selected as better from this comparison alone.

The reviewer independently ran the existing nine support tests and the new failure-restoration/geometry-invariance test: **10 passed**. The producer's actual exact-question processor preflight 02 is sealed at SHA-256 `96560dcbd2da06c2918206edd614e754642cc23deb1628196228719d153c7d36`. Its clean `4d88bde` code identity and unchanged core hash match the reviewed source. It records 240 input IDs, input/attention tensors of shape 1×240, float32 pixels 784×3×14×14, and native NumPy int64 grid 1×2 `[[28,28]]`, with zero model constructions and zero calls. The subsequent protocol-only amendment does not affect those processor inputs; no duplicate processor or model call was performed by the reviewer.

Preflight 01 used the `laya-embodied` interpreter and failed AutoProcessor dependency imports before model construction/inference or result JSON creation. Its explicitly transcribed command-failure receipt, SHA-256 `801acd729f6063def94c01f4ebde3c27fe1117ce8a930eddea5b9d64324aa5cd`, remains preserved. Switching to the already installed `/home/junhongli/miniforge3/envs/locateanything/bin/python` without dependency installation or code change was independently reviewed as an infrastructure-only correction under the parent's standing setup authorization. This did not spend or increase the one-call scientific budget.

| Reviewed file | SHA-256 |
| --- | --- |
| Reused `embodied_runtime/experiments/task2_box_support.py` | `9986c4f79578dd4e2691726f21df7ba0706ac8b9876a255ca078eed2f9bb43a6` |
| `embodied_runtime/experiments/task2_neck_box_support.py` | `ecf975b9e824232f5f90fe2193651e35c0f500be43e4f0bd746912b413af2276` |
| `docs/research/task2_neck_box_support_protocol.md` | `77ad9fabbcce512ddac045b3ab4fa1a9896f88908ff53f043c597226c956f43c` |
| `tests/test_task2_neck_box_support.py` | `bc72389747369967ea132b8fcd4ecc1024ed2d54762ddfbbe0dfcbda2df0b181` |

The original object-level call remains a separate completed condition. This approval covers exactly the one additional fixed neck-region inference and its registered stored-result analysis. Generalization, model planning, physical utility, and whether metric geometry can be omitted remain untested.

## Pre-inference GPU1 resource amendment

**Prospective PASS for clean `f1cae7c9160e31d2439683a7818c339b6f854dca`.** This supersedes the GPU0 allocation above. The parent authorized physical GPU1, another RTX 4090, because GPU0 has an unrelated Isaac-GR00T process; that process remains untouched. The sole reused-core change adds `generate(output, *, expected_gpu='0')` and checks the actual `CUDA_VISIBLE_DEVICES` against the explicit parameter. The neck wrapper explicitly requests `'1'`; the historical default remains `'0'`. The actual environment is recorded without spoofing. The wrapper's explicit four-mode CLI dispatch preserves the existing generate, evaluate, audit and processor-preflight behavior, including restoration of the fixed query context in `finally`.

The reviewer independently inspected the complete `aee8f29..f1cae7c` diff and reran the focused tests: **11 passed**. Raw generation, settings, parsing, depth support, P/G arithmetic, seals and evaluation did not change. The actual no-model processor preflight 03 has SHA-256 `548c206d665f131c5bc9df121850b55f7ab03dde12633d82aa3da688e809cbcc` and clean `f1cae7c` identity. Its source hash, exact question, all 240 input token IDs, field types/shapes/dtypes and serialized grid match preflight 02 exactly; both model construction and call counts are zero. The reviewer compared the stored receipts and hashes without another processor or inference invocation.

| Current reviewed file | SHA-256 |
| --- | --- |
| Reused `embodied_runtime/experiments/task2_box_support.py` | `8a8d7d828b4b2f65593975cb0378e5b4e7828c1e27ae432d6ca3bfdae3f179f1` |
| `embodied_runtime/experiments/task2_neck_box_support.py` | `c194386706b69519f1b68b275fde1e011c60f7248c99b1d9a080968ce18e38c4` |
| `docs/research/task2_neck_box_support_protocol.md` | `1f96645a8e951ff509850cbe9cd1550b7b61857835206d4219e843695319497e` |
| `tests/test_task2_neck_box_support.py` | `0dc2b687c970e4a0c5bc56927559a10e343abc90dfcc8fb486767e33b66e2b62` |

This review permits the same one fixed neck-query inference and registered stored-result analysis under the parent's existing allocation. The inference remains unspent at this prospective review; no retry or expanded scientific budget is implied.

## Sealed one-call result: nonadmission independently verified

**Stored-evidence audit PASS; scientific outcome `grounding_not_admitted`.** The one authorized GPU1 call at clean `f1cae7c` returned 42 BOX records and 260 actual generated tokens, with no EOS anywhere in the returned sequence. The unchanged configured `max_new_tokens` and effective limit were 256. The frozen rule rejects incomplete generation, more than 256 actual tokens, and multiple BOX records. No BOX was admitted; no sensor representation, P, G, bottle-proxy evaluator or qualitative region classification exists. No prefix was selected, truncated, repaired or extracted. The condition closes after this single call with zero retries, physics calls or renders.

The independent checker [task2_neck_box_evidence_audit.py](../../../experiments/task2_neck_box_evidence_audit.py) and [machine-readable receipt](task2_neck_box_independent_audit.json) verify all eight chained records, exact source/code/protocol/model identities, actual GPU1/BF16 allocation, raw-before-parser seals, final manifest reconstruction, exact 240 input tokens and grid against processor03, original RGB bytes, and equality of the processed BF16 image fingerprint to the sealed object-level condition. The complete 260-token sequence independently reconstructs the exact raw response from the pinned vocabulary and added-token metadata, without executing a tokenizer, processor or model. All 42 normalized raw BOX records remain present in the parser output, with none selected. The recorded checkpoint hash map is internally checked; the reviewer did not reread model weights.

Source-only inspection of pinned `modeling_locateanything.py` (SHA-256 `ffe736fb8ded5d597201704ccd85134d18a8e4dea43d309228644737234b7244`) finds the length target at line 331, the pre-append loop condition at line 464, the whole multi-token append at line 497, and untrimmed generated-ID slicing/decoding at lines 516–517. This accounts for how native output can exceed the configured limit. It does not change the configuration, raw record or admission result. The four-token overshoot is disclosed as observed native behavior rather than silently relabeled as 256 generated tokens.

| Audited result artifact | SHA-256 |
| --- | --- |
| Journal | `e099159c3f9e017c2e6afc7022edad9ec1988f91cbcf6aad11d688024161bbcf` |
| Raw generation return | `e19129163c257e9e5cde4e91094809c0e6a3b73d21ef45fe765ee82f946e56fc` |
| Model output | `33ed071dc19ec0990e83689c23a247536f7c4207f0712541964297e9e9dacb05` |

The producer's report and portable summary were also reviewed against these stored artifacts. Their bounded conclusion is supported: this single fixed researcher-specified neck query did not provide an admissible grounding. The object-level baseline remains a separately admitted result, but no neck-vs-object point, support or grasp-readiness comparison can be made. Different physical devices of the same GPU model were used; bitwise device equivalence was not tested. No conclusion about general semantic capability or the necessity or sufficiency of metric geometry follows. No automatic prompt, mode or model variant is authorized by this receipt.
