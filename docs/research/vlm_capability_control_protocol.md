# One stronger same-family capability control

Freeze this protocol, runner changes and tests before preparing or generating any
7B response. This separate control is authorized after the completed 3B relation
and subgoal probes; it does not retrospectively change their no-followup rules.
Those probes constrain the pinned 3B model/interface, not a general division of
responsibility between visual proposals and independent physical verification.

## One intervention, 31 unique queries

Acquire exactly `Qwen/Qwen2.5-VL-7B-Instruct`, provider revision
`cc594898137f460bfe9f0759e9844b3ce807cfb5`, pinned by provider metadata before
weight downloads. Keep immutable provider metadata, per-file ETags, all five
weight SHA-256s, Git blob hashes of small files, acquisition plan and final local
content identity in separate `vlm7b-capability-acquisition-01` evidence. Acquire no
other checkpoint; perform no training, quantization, prompt/threshold search or
paid model calls. Load native BF16/eval/SDPA on assigned GPU2. Record a fit failure
and stop rather than silently changing precision or settings.

Reuse `vlm-world-single-inputs-01` and the exact original evaluator
`vlm-world-single-labels-01/labels.json`: 24 calls in existing order, horizontal,
gap and orientation each queried on no image, gray, original0, mirror0, original2,
mirror2, original4, mirror4. Reuse `visual-subgoal-inputs-02` and the exact original
evaluator `visual-subgoal-labels-01/labels.json`: one task-only and six RGB calls,
7 total. Their original source manifests retain 3B provenance; a separate control
registration identifies the actual 7B inference model without rewriting input or
gold bytes. Both existing strict input loaders, prompt builders, native auditors
and scorers remain in use. Each call has a fresh user message and no history.

Register all 31 call identities, original manifest/evaluator/protocol hashes,
baseline raw/preflight hashes, acquired model identity and clean committed source
identity before preflight. The generator sees only the original safe input
manifest/images, registration metadata and evaluator hash, never evaluator
contents, source frame metadata, HUD, trace, phase, or simulator state.

The only intervention is the checkpoint and its required native model/processor
configuration. Retain the exact task text, field definitions, label vocabulary,
images, crop, order, seed1, four threads, slow processor, no truncation, greedy
`max_new_tokens=32`, `use_cache=true`, and full native logits. Construct generation
settings with the same function as 3B, taking only native BOS/EOS/pad token IDs
from the selected checkpoint. Do not assume processor output tokens are equal:
compare every current presentation with corresponding 3B evidence, reporting
prompt/IDs/masks, image grid, processed dimensions, FP32/BF16 pixel identities,
image-token count and input-token count differences.

Run each condition once: relations24 then subgoals7. Both preflights must complete
before generation. Freeze equality of registration/model/code/config/prompts and
processed inputs from preflight through calls. Keep invalid, uncertain and negative
responses; do not retry or salvage them. Infrastructure failures remain evidence
and do not authorize replacement responses. No further prompt/model experiment
follows from a disappointing answer in this control.

## Native audit and fixed analysis

Persist actual consumed input IDs/masks/pixels/grid, generated IDs, complete
vocabulary logits, raw and cleaned decoding, EOS/budget checks, checkpoint/config/
processor/code/version provenance, latency and CUDA peaks. The post-run control
audit rehashes local checkpoint bytes, regenerates every presentation from source
images and processor, validates the native loaded model configuration, rechecks
preflight and original baseline identities, and runs the existing original
native/logit/EOS scorer against the unchanged gold evaluator.

Compare relation useful accepted non-uncertain scene answers /18, each relation
/6, coherent all-three agreement across independent questions /6, abstention
controls /6, per-field invalid/uncertain counts and all9 mirror pairs. Mirror
consistency is separate from correctness; mirrored images are dependent. Baseline
3B had 2/18 useful scene fields and 0/6 coherent scenes, with constant per-field
outputs aligned/uncertain/uncertain and 4/6 correct abstention controls.

Compare subgoal annotation agreement and useful accepted proposals only for
primary RGB images0,1,2, denominator3; score the single task-only answer on those
same three label sets. Report images3,4,5 descriptively without correctness/safety
labels. Baseline 3B had 1/3 primary agreement/usefulness, equal to its task-only
answer scored on those three sets. That task-only result is one call, not three
independent trials. Report all31 raw strings and invalid/EOS/budget/resource data;
never pool the different probes into a headline accuracy.

A substantial 7B gain shifts this fixed-fixture diagnosis toward limited 3B
capability; relation-only gain indicates an uneven capability boundary. Failure
of both fixed probes supports a limitation shared by these two checkpoints under
this interface and imagery, not a universal model-family or architectural failure.
Useful proposal gains can motivate further separately authorized investigation,
not physical authorization. Neither outcome establishes full planning, contact or
holding inference, placement fit, closed-loop manipulation, safe execution,
generalization, model-family superiority or failure of the proposed division of
responsibility. The convenience images remain lossy primitive-trace video
reconstructions, with primary labels previously judged by non-blinded reviewers.
