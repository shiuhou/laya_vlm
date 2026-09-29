# Frozen RGB POINT replay and order probe v1

## Question and code evidence

Does the wrong POINT at boundary21 persist when its identical RGB is the first
call in a fresh model process, or does preceding inference history change the
result? Also test whether the terminal malformed boundary25 output recurs cold.
Boundary20 supplies an intact neighboring-image control.

The frozen LocateAnything `generate()` sets `past_key_values=None`, clones the
new input, extracts the new image features, and initializes hybrid decoding mode
and sampling history locally on every call. No intentional cross-call conversation
or KV cache is supplied. Lazy internal caches and numerical/order effects remain
possible; source inspection does not replace this empirical check.

## Fixed source and six calls

Use `coarse-point-boundary-01`, raw JSONL SHA-256
`d9ed0bc2b10b61b047e44ec37a03ea788b4e88e2f8d06edd8171bcd29677f319`.
Extract only RGB from captures21,22,26: physical boundaries20,21,25. Preserve and
hash their exact uint8 arrays and the original model-native image tensors/token
inputs. Depth, calibration, robot/world state and oracle labels are excluded from
the prepared generator manifest. Archived outputs live in a separate evaluator
reference that generation never opens.

Exactly two fresh Python/model processes, one pass each:

- `target_first`: boundaries **21,20,25**.
- `terminal_first`: boundaries **25,20,21**.

Three calls per process, six total. The first-wrong frame21 and terminal malformed
frame25 each occur cold in one arm and after different preceding inputs in the
other; normal frame20 stays second. No warm-up, extra repeat, random permutation,
or alternative wording. Fresh-process code enforces one arm per Python process.

Use the existing `coarse_point_probe.point_call` path and identical POINT query,
checkpoint content ID `4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`,
precision, tokenizer, image preprocessing, greedy hybrid settings and seed1.
The worker receives only a fresh RGB frame and an audit-only call sequence ID;
there is no chat history, depth or oracle input. The call sequence ID changes only
artifact naming and logs. Never feed archived native tensors instead of RGB:
they are equality checks on fresh preprocessing, not alternate model inputs.

## Integrity and malformed outcomes

Before generation, require the actual formatted question, token IDs/count,
attention mask, image grid and image tensor values to equal the corresponding
archived model-native input exactly. Fail on any infrastructure/provenance/input
mismatch. Persist the new native tensor artifact, complete generated token IDs,
raw decoded response, parsing status, EOS/length-limit audit and timing.

A malformed or length-limited response is an intended measured outcome in this
offline test. Preserve it verbatim and proceed to the next registered image;
do not salvage its first point, retry it, or execute any action. Missing raw tokens,
an exception or corrupted evidence is an infrastructure failure and stops the arm.
No simulator or execution layer is constructed.

## Interpretation

Compare both arms to each other and to the recorded online source, separately
for raw output, generated token IDs, parsed grounding, and completion. If wrong
frame21 reproduces cold, the original twenty preceding calls are not necessary
for that failure. If malformed frame25 reproduces cold, its original history is
not necessary either. This does not prove all possible order/history effects
absent or establish semantic correctness of a changed output.

Any mismatch earns inspection of exact input/model/environment evidence before
attribution to hidden state. Do not add repeats automatically; a further diagnostic
requires a separately registered decision. This experiment changes no policy,
admission, prompt, model settings, controller or runtime architecture.
