# Task2 matched native POINT semantic-region control v1

## Scope and interpretation

Exactly two prospective native POINT calls compare the fixed descriptions
`the wine bottle` and `the neck of the wine bottle`. The questions are exactly:

1. `Point to: the wine bottle.`
2. `Point to: the neck of the wine bottle.`

This is an output-format/semantic-region comparison on one previously inspected
fixture. It tests whether researcher-specified part information is usable by the
existing interface. It does not test independent grasp-region choice, planning,
grasp quality, or physical feasibility. Syntax, EOS, finite depth, and a projected
coordinate are separate measurements; none establishes semantic correctness.
Keep both results regardless of favorability. No point is selected for execution.
The earlier neck BOX result (42 BOX records, 260 tokens, no EOS) remains unchanged
failed evidence; this test does not repair it or retrospectively relax admission.

## Source audit and fixed controls

Use the original full 384×384 RGB in
`interaction-observability-paired-01/close/0000.npz`, SHA256
`3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`.
The same archived depth, K, and camera-to-world T are available only for sensor
projection after native generation. Capture read time is 0.5 s; exact cached RGB
and depth sample times remain unknown. No recapture, crop, hint, teacher
coordinate, scene reconstruction, physical call, or render is authorized.

Local checkpoint `/home/junhongli/models/huggingface/LocateAnything-3B`, content ID
`4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`.
`source_config()` verifies original sealed whole/neck BOX manifests and exact
questions without reading their model responses. Their loaded configurations are
equal. Each POINT worker must match that original configuration, BF16/eval,
tokenizer model_max_length 16384, and EOS token 151645. No new model.

Use the existing processor/template route from `coarse_point_probe.point_call`
and `LocateAnythingWorker`; do not call the worker's BOX-only `.infer()` method.
The checkpoint README's `point()` and template table specify `Point to: {phrase}.`
and native POINT encoding `<box><x><y></box>`. POINT is selected by the question,
not by changing `generation_mode`. Preserve existing `point_grounding_probe.SETTINGS`:
max_new_tokens 256, use_cache true, generation_mode hybrid, temperature 0,
do_sample false, verbose false. Preserve the native default n_future_tokens=6.
No token-limit, EOS, parser, decoder, confidence, or coordinate relaxation.

## Matched processes, accounting, and failure handling

Run whole first and neck second, one fresh Python/model process each, each seeded
with Python/NumPy/Torch seed1, with no warm-up or prior call. The same single
physical GPU must be explicitly assigned to both and recorded at launch; recheck
availability before the reviewed run. Its number is a resource assignment, not
a scientific condition. Any reassignment occurs before either call. Record GPU,
versions, attention implementations, deterministic-algorithm flag and threads;
require identical loaded environments between conditions. No deterministic-mode
or attention-backend changes are introduced. Prior six-call replay controls
reproduced their specific failures across fresh-process orders, but do not prove
universal absence of order effects; fresh processes remove preceding-call history
from this pair. Two calls do not estimate repeatability or population accuracy.

The controller issues the two registered intents in fixed order and invokes one
child per condition. Each child rejects a missing/mismatched intent, repeated
process use, existing output directory, or input/config mismatch. One model call
per child; two total. There are no automatic repeats or fallback prompts.
A malformed, mixed, multiple, missing-EOS, length-limited, or invalid-depth
response is a retained condition result and does not cancel the second condition.
An infrastructure exception, missing token audit, timeout, configuration/input
mismatch, or evidence failure stops the batch; preserve partial evidence and
leave remaining conditions unrun. No automatic retry even if zero calls occurred.
The 300 s timeout applies to each inference call, as in the BOX baseline.

## Native artifacts and unchanged admission

Processor-only preflight constructs AutoProcessor, never AutoModel/worker. Hash
local checkpoint bytes and full RGB; record formatted questions, all input token
IDs, attention masks, grids, and BF16 image tensor identity represented exactly
as float32. Require identical image tensors and grids across the two descriptions.
Freeze and review code/protocol/tests and this preflight before either model call.
At execution, fresh preprocessing must match preflight exactly; preserve full
native pixels, input metadata and RGB per condition.

Observe tokenizer.batch_decode to capture all actual native generated token IDs,
then seal raw return, return type/repr and observed sequences **before** audit,
parsing, admission, or projection. Restore the tokenizer and signal handler even
on failure. Preserve exceptions and any observed sequences. The native hybrid
loop checks length before appending a chunk and can exceed 256; preserve actual
counts verbatim. Never truncate or salvage the first grounding.

Reuse unchanged `parse_grounding`, `generation_audit`, and
`coarse_point_probe.admit_point`: exactly one valid in-frame native POINT,
terminal EOS, actual count strictly below the effective token limit, finite depth
in inclusive [0.01,5] m, finite projected world point. A complete 256-token output
is still length-limited and is rejected. BOX/multiple/mixed/malformed responses
are rejected. The parser retains all groups and has confidence null.

Native POINT normalized raster coordinates become `(u,v)=(x/1000*width,y/1000*height)`;
take `(floor(u),floor(v))` without clamp, read that depth pixel, and project its
center `(floor(u)+0.5,floor(v)+0.5)` through unchanged K/T. This is the original
POINT convention, not integer-center LK nearest-index association. Preserve the
raw point, parsed coordinates, selected pixel, center, depth, world projection,
source hash and calibration identities. Invalid output has no admitted sensor
point. Resolved-depth ownership, semantic confidence and grasp quality stay
unknown, even for admitted geometry. No support-G/BOX crop is invented.

## Sealed evaluator and actual RGB inspection

Generation opens no evaluator mask. Both sensor results and batch termination
must seal before the separate `evaluate` mode opens the original whole-bottle
ID-rendered membership proxy (SHA256
`2a474be6d469dc2df45edfb03c97b23a1adf021f9a48551994a619f501a0b747`).
Record evaluator start and sensor/journal hashes before opening it. For each
admitted point only, report containing-pixel proxy membership and the existing
3×3 interior/boundary/exterior stratum. Nonadmitted rows have null membership.
The proxy has no neck annotation, is not depth ownership, and cannot validate
grasp quality. MSAA depth/label ambiguity, shared synthetic calibration, and
unknown cached sample times remain. No label-based sensor correction occurs.

Save actual uncropped RGB plus the two fixed condition panels in order; display
an admitted point at its selected array pixel, and preserve nonadmission panels
without salvaged markers. Open and inspect the actual RGB artifact after sealing;
attach a separately identified visual receipt describing where each output falls
or stating that the region is visually ambiguous. This visual reading does not
alter admission or create a neck mask. No automatic semantic label is produced.
Report raw tokens/output, parsing/completeness, sensor geometry and evaluator/
visual evidence separately. No favorable-result selection, policy change,
physics, control, grasp execution, or automatic extension follows this pair.

## Required verification

Synthetic tests cover raw preservation before failed validation, decoder and
signal restoration after generation failure, strict completion/length/depth
admission with unchanged pixel-center projection, continuing the second fixed
condition after nonadmission, stopping on infrastructure failure without retry,
and preventing evaluator access before both rows seal. Reuse original parser
and POINT-admission tests. Processor-only preflight verifies actual source and
paired preprocessing; it reports model constructions/calls, physics and renders
all zero. Independent source/preflight review precedes the two-call run.
