# One earned discriminator: independent single-relation questions

Freeze before inference, after `vlm-world-run-01` completed all twelve calls and
passed the native re-audit. That run contains nine invalid strings, chiefly
slash-separated alternatives copied from the three-field template. All outputs
had EOS and none reached the 32-token cap. Its three valid task-prefixed scene
answers were all `aligned,uncertain,upright`; none matched all fields. Therefore
the earlier result cannot separate output composition from direct image reading.
No invalid answer is salvaged or replaced.

This is the one earned follow-up allowed by the parent protocol. Ask each of the
same three relations independently using one word, without a slash template or
the task sentence. Keep image bytes, labels, definitions, checkpoint, BF16/eval/
SDPA, greedy 32-token budget, seed, four threads and native audit unchanged.
Removing joint output and slash syntax is a combined interface intervention;
even improvement cannot distinguish those two components individually.

## Fixed inputs, prompts and twenty-four calls

Reuse the seven images from `vlm-world-inputs-01` exactly, with copied artifacts,
parent-manifest/image identities and protocol hash. No additional image, crop,
marker, task hint, temporal context, hidden state or model is introduced.
Each question starts with:

> Report only visible image geometry, not an action or hidden physical state.

Then use the corresponding unchanged definition (only remove `First/Second/Third`
and capitalize the question beginning):

**Horizontal**

> Where is the bottle's center horizontally relative to the visible open drawer
> interior? left = left of the interior; right = right of it; aligned = within
> its horizontal extent; uncertain = cannot determine.

**Gap**

> Is there a clear visible gap between the bottle and the robot's gripper
> fingertips? separated = clear gap; adjacent = visibly next to or overlapping
> the fingertips; uncertain = cannot determine. This does not ask whether the
> robot securely holds the bottle.

**Orientation**

> Is the bottle's long axis upright or diagonal in the image? upright =
> approximately vertical; diagonal = clearly tilted; uncertain = cannot determine.

Each ends:

> If no image is available or the objects are not visible, answer uncertain.
> Return exactly one word: [the field's comma-separated labels].

The label lists are respectively `left, right, aligned, uncertain`;
`separated, adjacent, uncertain`; and `upright, diagonal, uncertain`.
No explanatory reasoning is requested.

In horizontal, gap, orientation order, run eight independent calls each:
text-only, uniform gray, original0, mirror0, original2, mirror2, original4, mirror4.
Exactly 24 calls total, no repeats or further prompt changes. The generator reads
only its new input manifest/images and the preregistered evaluator hash. Freeze
the new evaluator JSON by mechanically projecting the original registered field
labels to the matching single-relation calls; record the old evaluator hash.
No new human label judgment or post-result change is permitted.

## Audit and analysis

Keep the original complete run intact. Commit protocol/module/tests before
preflight. Require exact frozen-preflight equality and retain native input/image/
forward/token/logit/EOS evidence, including invalid answers without salvage.
No-image inputs must truly lack pixels; gray controls must contain pixel tensors.

Report each field separately on six scene images (dependent mirrored pairs) and
two abstention controls, plus useful accepted non-uncertain answers /18 across
all scene-field calls. Report coherent all-three agreement on the six scene
images by joining the independent calls, with explicit disclosure that these
were three independent questions. All-uncertain has zero useful scene coverage.
For each field report mirror consistency and correctness separately: constant
answers may be mirror-consistent for gap/orientation while wrong on originals.

- Valid, accurate single-field results would locate a substantial interface
  contribution, without proving joint scene representation or planning.
- Valid but image-inappropriate constant answers reveal a direct relation/query
  binding failure in this fixed interface, beyond joint-output syntax alone.
- Successful orientation but failed object-object relations indicates uneven
  visual capability, not coherent world understanding.
- Failed no-image abstention reflects an unsupported-answer tendency, not visual
  recognition. Changes in gray/image logits alone do not establish competence.
- Continued malformed answers leave relation ability unresolved; stop this
  fixture/prompt line rather than reformulating again.

There is no further follow-up here, no model acquisition, training, physical
execution, runtime integration, or inference of 3D contact/holding/containment.
