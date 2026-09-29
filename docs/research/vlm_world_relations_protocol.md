# Frozen visible-relation discriminator

Registered before new inference. This is an offline image-reading experiment,
not a planner, motor policy, grasp detector, or evidence of physical competence.

The preceding seven-call subgoal run must first pass the existing native audit,
including its `generation_complete` record. It has now done so: seven valid EOS
answers, original RGB0–4 `establish_grasp`, RGB5 `uncertain`, primary agreement
1/3, equal to the task-only baseline. This protocol tests narrower explanations
without modifying that prompt or retrying its outcomes.

## Images and independent labels

Use only original RGB0,2,4 from `visual-subgoal-inputs-02`, manifest identity
verified by the preceding module. They are 600x600 unannotated camera crops from
lossy primitive-trace video reconstruction, not original sensor/control replay.
Copy each RGB unchanged and create its exact PIL horizontal mirror without
resizing or annotations. Also create a 600x600 RGB image filled with (128,128,128).
Persist image hashes, parent manifest/hash and transformation lineage. These
seven images plus text-only calls are the entire fixed input set.

The investigator inspected originals before registering these visible labels:

| Original | Bottle center vs drawer interior, horizontally | Bottle vs fingertips | Bottle long axis |
|---|---|---|---|
| 0 | left | separated | upright |
| 2 | left | adjacent | upright |
| 4 | aligned | separated | diagonal |

Mirroring exchanges left/right and preserves the other fields. For no image or
uniform gray, all three labels are uncertain. Here `aligned` means the bottle
center lies horizontally within the visible open drawer interior, not 3D
containment; `adjacent` means no clear visible gap at the fingers, not a stable
grasp. Upright includes small perspective tilt. Labels are deliberately limited
to clearly visible geometry. Freeze the evaluator JSON, including these
definitions, input-manifest hash, per-call acceptable values and explanatory
notes, before preflight. Generation receives only its SHA-256, never its content.

## Twelve calls, one fixed question

Exactly these independent fresh-user-message calls, in this order:

1. Neutral text only.
2. Neutral uniform gray.
3. Neutral original0, mirror0, original2, mirror2, original4, mirror4.
4. Task-prefixed text only.
5. Task-prefixed original0, original2, original4.

Neutral text:

> Report only visible image geometry, not an action or hidden physical state.
> Give three labels in this order, separated by commas and with no other text.
> First: where is the bottle's center horizontally relative to the visible open
> drawer interior? left = left of the interior; right = right of it; aligned =
> within its horizontal extent; uncertain = cannot determine.
> Second: is there a clear visible gap between the bottle and the robot's
> gripper fingertips? separated = clear gap; adjacent = visibly next to or
> overlapping the fingertips; uncertain = cannot determine. This does not ask
> whether the robot securely holds the bottle.
> Third: is the bottle's long axis upright or diagonal in the image? upright =
> approximately vertical; diagonal = clearly tilted; uncertain = cannot
> determine. If no image is available or the objects are not visible, use
> uncertain for each unsupported field.
> Format: left/right/aligned/uncertain,separated/adjacent/uncertain,upright/diagonal/uncertain

The task condition adds exactly the earlier task sentence, followed by a newline:

> Task: pick the wine bottle from the tabletop, place it inside the bottom drawer,
> release it, then close the drawer.

Do not request chain-of-thought, explanations, action labels, or inferred contact.
Commas may have surrounding whitespace; each field must exactly match its
registered vocabulary. Malformed/non-EOS output is invalid with no salvage.

## Frozen execution and audit

Same pinned Qwen/Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, local content identity
`11fccd61f55d2716ae7f8d4e28790b58b63d4126ade6994cef640a3cf337aa33`;
BF16/eval/SDPA, greedy max_new_tokens32, cache true, seed1, four CPU threads.
Run on assigned GPU2, local files only. Commit module/tests/protocol before
preflight. No model acquisition, tuning, repeats or hidden truth is authorized
by this protocol. Retain native image preprocessing, actual forward inputs,
all tokens, full vocabulary logits, decode, EOS/budget, versions, provenance,
latency and GPU memory audits, with equality to preflight before any generation.

## Registered analysis and interpretations

Report every raw answer and all invalid/uncertain outcomes. Score each of three
fields and all-three agreement separately. Primary image denominator is six
neutral scene images; retain original/mirror breakdown and pairwise consistency.
Abstention control denominator is three (neutral text, gray, task text). Report
correct informative field coverage as accepted non-uncertain fields /18. Always
uncertain therefore scores zero useful scene coverage. Task-prefix comparison
uses only its three original scenes paired with their neutral originals.
Never combine original/mirror correctness into an independent-sample estimate.

- Coherent correct relations across originals/mirrors, with controls abstaining,
  weakens broad inability to read these scenes. Failed earlier action proposals
  then implicate objective/intent binding or task framing, still not uniquely.
- Correct neutral relations that deteriorate under the task sentence specifically
  support interference from task context in this fixed relation interface.
- Failure of these direct relations, especially unchanged left/right under
  mirrors, demonstrates a more basic visual/query-binding bottleneck under this
  interface. It does not prove absence of visual features or model-wide inability.
- Object-relation errors with preserved orientation show uneven capability;
  aggregate accuracy alone cannot establish coherent world understanding.
- Image-sensitive logits without correct field changes establish input effects
  only, never image understanding.

Convenience selection, synthetic mirrors, coarse image geometry, single decoding
per call, and one model/interface limit every conclusion. No runtime integration
or claims about holding, fit, safety, motor control or generalization follow.
At most one further discriminator may be separately frozen if these outcomes
identify a concrete ambiguity; there will be no prompt search until success.
