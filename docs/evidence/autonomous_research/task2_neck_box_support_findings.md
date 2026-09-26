# Task2 semantic neck query: grounding not admitted

The single fixed query `the neck of the wine bottle` returned repeated BOX
records without terminal EOS. The frozen admission rule rejected it. No neck
point, candidate depth support, visual region classification or bottle-proxy
comparison exists. No prefix or individual box was selected, and no retry,
alternative wording, POINT fallback, offset or physical action followed.

This is a researcher-specified semantic-part query, not a model-generated plan
or certified grasp point. It reaches an output-format/completion boundary on
one already-inspected development image. It does not establish a general
inability to localize necks, nor that metric geometry is necessary or sufficient.

## Fixed contrast and observed output

Both conditions use the same initial full RGB, checkpoint, BF16 processing,
native hybrid greedy settings, 256-token configured limit and existing BOX
template. The exact new question is:
`Locate a single instance that matches the following description: the neck of the wine bottle.`

| Field | Sealed object-level baseline | Single neck condition |
|---|---|---|
| Actual generated tokens | 12 | 260 |
| Terminal EOS | Yes | No |
| Parsed BOX records | 1 | 42 |
| Admission | Single complete BOX | Rejected: multiple boxes and incomplete generation |
| Sensor point/support | Existing P/G retained unchanged | Not produced |

The 42 raw BOX records comprise normalized coordinates `[542,410,596,582]`
once, `[543,0,637,225]` 21 times and `[543,410,596,582]` 20 times. These are raw
token descriptions only; no region was chosen for interpretation or extraction.
The [portable summary](task2_neck_box_support_summary.json) retains the full raw
return and all actual generated token IDs. Audited return latency was 2.990 s.

The native generator exceeded its configured 256-token limit by four tokens.
Source-only inspection shows that its loop checks total length before appending
an entire multi-token chunk, then decodes without truncating that append. The
stored audit preserves the actual 260-token sequence and absent EOS. No decoder
or admission rule was changed after this result.

## Freeze, setup and audit

The [protocol](../../research/task2_neck_box_support_protocol.md) and wrapper were
frozen before inference. Final clean freeze is **`f1cae7c`**; all 11 focused tests
passed in producer and independent review. The sole core API amendment exposes
`expected_gpu='0'` while preserving the historical default. Root-authorized neck
inference explicitly used idle physical GPU1, also an RTX 4090, and honestly
recorded `CUDA_VISIBLE_DEVICES=1`. GPU0 was occupied by an unrelated workload.
This single observed contrast does not test bitwise device equivalence.

Processor preflight 01 used the wrong existing Python environment and stopped
at missing dependencies before any model construction or call; its transcribed
failure receipt remains preserved. Preflights 02 and 03 used the pinned
LocateAnything environment and passed with identical 240 input token IDs and
native Tensor/NumPy schema. Preflight 03 records the final clean freeze.

The run preserves one `call_started`, then sealed generation-return and model
output, then `termination(reason=grounding_not_admitted, model_calls=1,
retries=0, physics_calls=0, renders=0)`. Sensor extraction and evaluator loading
were never reached. The success-only sensor audit correctly refused the absent
sensor artifact. The separate stored-only nonadmission audit passes journal
links/seals, actual tokens, exact preflight question/tokens/grid, unchanged
baseline RGB and processed BF16 pixel fingerprints, and the absence of sensor
and evaluator outputs. It constructs no model and performs no inference.

Independent prospective review is recorded in
`task2_neck_box_support_independent_review.md` in the reviewer worktree.
The sealed object-level baseline journal and sensor hashes remain unchanged.
This semantic-region line closes at the nonadmission boundary.

## Evidence seals

Raw directory:
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-neck-box-support-run-01`.
The complete raw response, tokens, model/source identity and settings remain
there; no artifact has been replaced.

| Artifact | SHA-256 |
|---|---|
| Run journal | `e099159c3f9e017c2e6afc7022edad9ec1988f91cbcf6aad11d688024161bbcf` |
| Raw generation return | `e19129163c257e9e5cde4e91094809c0e6a3b73d21ef45fe765ee82f946e56fc` |
| Audited model output | `33ed071dc19ec0990e83689c23a247536f7c4207f0712541964297e9e9dacb05` |
| Processor preflight 03 | `548c206d665f131c5bc9df121850b55f7ab03dde12633d82aa3da688e809cbcc` |
| Producer stored-only audit | `333b868e156dc3cf7b7fd15a344c5005533820111345fe7050cc0cb619f3f440` |
