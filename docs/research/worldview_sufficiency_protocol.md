# Supplied coherent situation sufficiency v0.1

Registered before inference, 2026-09-27. This is one intervention, not a prompt
selection exercise. No model response is used to choose its wording.

The hypothesis is that a correct local objective and numeric effects remain
disconnected from the situation in Laya's current presentation. A coherent
situation might let the frozen model use those same consequences. This experiment
tests that narrow sufficiency claim, not whether a VLM can acquire a world model.

## Source and correctness boundary

Use the frozen current motor source
`runs/privileged-reference/local-objective-task-adapter-episode-01/episodes.jsonl`,
SHA-256 `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`.
Use the previously selected first two approach and first two advance boundaries,
steps **0, 1, 9, 10**, with **7, 7, 25, 16** candidates. Exclude reposition 87
because its two-step witness horizon is a distinct question; no exclusion uses a
new model answer. These are inspected development states, not held-out examples.

The sensory approach fixtures cannot certify a correct physical worldview:
their visual target identities remain unverified. The present source is instead
an explicitly privileged supplied-situation diagnostic. The oracle state,
objective routing, candidate admission and effects were already present. No new
oracle coordinates, contacts, winning actions or evaluator labels enter either
arm. The prefix is authored from the existing model-visible state and schema.
The phase comes from existing privileged routing; it is not Laya reasoning.

The target is the **moving top-drawer structure**, matching the source geometry
and contact definitions, not a certified designated handle. In the source,
`GeometryGap` compares gripper geometry to `scene.moving`, and `moving_contact`
reports force-thresholded contact with that same set. Contact does not establish
secure grasp. Advance gaps are 0.01/0.00 mm; approach openings are positive.
The constructor verifies the numeric premises directly in model-visible text.

The source-to-packet mapping is fixed:

| Packet statement | Source already visible to Laya / schema basis |
| --- | --- |
| top drawer moving structure | `Task: close top drawer`; `privileged_task.py` serializes `distance_to_moving_geometry_mm` and `moving_contact`; Jev `world.py:features` defines the moving set |
| phase / intent | literal `Current local objective: approach_target` or `advance_target` and the unchanged objective instruction |
| drawer is open | positive model-visible `Current opening` (151.659 mm in both approach states) |
| very near drawer surface | model-visible `gap` of 0.01/0.00 mm in advance states |
| relevant relation | approach objective prefers surface-gap reduction; advance objective prefers closure |
| closure / gap meanings | unchanged table headings `positive closes` / `positive approaches` |
| touching does not certify grasp | source `moving_contact` is a contact flag, with no secure-grasp field |
| rows predict possible outcomes | unchanged `effect_source=oracle_sim`, preview horizon and effects header |

These are schema interpretations and paraphrases, not additional observations.
The packet is constructed only from the existing state string. Hidden oracle
predictions, archived choices and evaluator labels cannot change the payload.

## Fixed matched intervention

Arm B is the exact current motor payload. Arm W prepends exactly one of the
following paragraphs to the original state string, leaving every original byte,
instruction, candidate ID, description, membership, order, effect and history
unchanged. No action sorting, top-k filtering or confidence is introduced.

Approach paragraph:

```
Situation: the target is the top drawer moving structure. Phase: approach. Intent: bring the gripper near that structure so interaction can become possible. The drawer is open; gripper-to-drawer surface separation matters now. Gap reduction measures approach; closure measures drawer motion. Contact means touching, not secure grasp. Rows predict possible next outcomes, not instructions.
```

Advance paragraph:

```
Situation: the target is the top drawer moving structure. Phase: advance. Intent: reduce drawer opening from the present gripper configuration. The gripper is very near the drawer surface; drawer motion matters now. Closure measures drawer motion; gap reduction measures approach. Contact means touching, not secure grasp. Rows predict possible next outcomes, not instructions.
```

The prefixes contain no primitive, direction, chosen outcome, numeric ranking or
unique-action description. They supply target identity, current phase, intent,
the relevant relation, and the interpretation of existing effect fields. They
do not establish the complete physical world or resolve handle validity.

## Execution and measurements

Commit exact code/protocol before the recorded CPU preflight and all model calls.
Use the existing checkpoint with content identity
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`, seed 1,
bfloat16, native cardinality temperature and GPU 0. No new model download.
The tokenizer-only design check gives B/W token counts 372/449, 406/483,
923/996, 652/725, all below the 1,024-token limit. Exact installed sequence
builder audits and consumed forward-hook IDs/option markers are required.

Exactly **16 calls**: chronological boundaries, B then W, followed by the full
reverse fixture traversal. Candidate order never changes. Stop at truncation,
invalid output or token mismatch without a repair or retry. Preserve failures,
missing calls, raw model-facing text/IDs, native responses, logits, probabilities,
model/source/code hashes and environment. Compare B to archived outputs and
both repeats exactly. No simulator execution and no live policy integration.

Recompute source immediate-effect metrics only after each choice. Approach
choices are compared by surface-gap reduction; the existing instruction says
"prefer substantial" and is not treated as a strict argmax correctness label.
Advance choices are compared by closure, with alternatives that offer greater
closure, no less gap reduction/contact, and equal obstacle force/success/horizon.
Report each step and condition, including all unchanged failures. Repeats are
repeatability checks, not extra independent samples. No significance testing.

If W improves both advance states without impairing the two approach states,
that is evidence for a useful supplied-situation interface on this narrow slice;
it earns a prospectively fixed independent-state test, not deployment. If W
retains the weak advance choices, reject the claim that this simple coherent
local situation is sufficient and stop wording refinement. A mixed result is
inconclusive about general sufficiency. No prompt tournament follows.

Added text also changes input length, token positions and semantic emphasis.
The exact B control establishes the intervention's total effect, not which
linguistic mechanism caused it. Failure cannot establish that every coherent
world representation fails; success cannot establish full-world understanding,
interaction-valid manipulation, long-horizon success or VLM necessity.
