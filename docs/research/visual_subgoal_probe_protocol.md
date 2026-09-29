# RGB versus task-only provisional local objectives

This is a small offline high-level proposal probe, not physical execution,
interaction-state verification, a complete planner, or a new runtime layer.
Test whether the already frozen Qwen2.5-VL-3B can use visible scene differences to
propose useful next local objectives beyond an identical task-text-only prior.

## Registered input preparation

Use only the frozen Task2 permissive diagnostic video with SHA-256
`22abc6df7615bcf058ca5ae1de0bdf7d0b39d862c0654d3c02bc3027a508dda5`.
Sequentially decode zero-based frames **7,55,135,183,239,319** from frame0 with
OpenCV/FFmpeg. Extract only the left600x600 camera viewport from the960x600 source;
exclude the right HUD entirely. Save unannotated RGB PNGs without resizing.
Persist decoder version, source hash, frame indices, crop and image hashes in
separate extraction evidence. The model sees no frame number, phase, HUD, prior
image, action history, simulator state, candidate, trace label or evaluator label.

These images are **lossy resampled primitive-trace reconstruction**, not original
control replay, raw sensor observations, or a fresh closed-loop episode. This
limits the conclusion to image-conditioned provisional objective proposals.

Root must inspect the six extracted RGBs and freeze evaluator scope and set-valued
visual labels in a separate file before inference. Only images0,1,2 (frames7,55,135)
receive primary labels: respectively approach_object; approach_object or
establish_grasp; transport_object. Images3,4,5 are exploratory/descriptive with
no gold objective and no safety/correctness score. A provisional close-related
proposal does not certify hidden placement fit, so hidden simulator truth must not
be used to reject it as a wrong proposal. Generator never reads the evaluator file.
Record its preregistered hash separately.

## Seven calls and model

Exactly one identical-task-text-only call followed by six unique RGB calls in the
registered frame order: **7 total**, one pass, no repetitions or prompt search.
Each call is a fresh user message, without previous answers or conversation.
Use Qwen/Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, local content identity
`11fccd61f55d2716ae7f8d4e28790b58b63d4126ade6994cef640a3cf337aa33`, native
BF16/eval/SDPA, greedy max_new_tokens32, use_cache=true, seed1 and four CPU threads,
as in the existing visual target verification probe. The image item is the only
model-message difference between the task-only and RGB conditions.

Fixed text:

> Task: pick the wine bottle from the tabletop, place it inside the bottom drawer,
> release it, then close the drawer. Choose the best provisional next local
> objective using the available observation. This proposal does not authorize
> execution; physical preconditions require independent verification. Do not
> assume hidden grasp strength or placement fit. If the observation cannot support
> a useful choice, return uncertain. Return exactly one allowed label:
> approach_object, establish_grasp, transport_object, place_object, release_object,
> approach_drawer, establish_drawer_contact, advance_drawer, uncertain.

Persist prompt/messages, exact token IDs, attention mask, image patch grid,
processor/native BF16 tensor identity, actual forward input IDs/tensor identities,
all generated token IDs, full vocabulary logits, raw decoding, EOS/budget audit,
versions, latency and GPU peak. Require preflight equality before inference.
Fail on input truncation, integrity or infrastructure error. Malformed label or
non-EOS output is recorded as an invalid outcome without salvage or retry.

## Analysis

Report each result, invalid and uncertain counts, and decisions changed relative
to the task-only answer. Score primary images0,1,2 only: set-valued annotation
agreement and useful accepted non-uncertain proposal coverage, both denominator3.
Compare the sole task-only answer against these same three label sets. Report
images3,4,5 descriptively without correctness/safety/fit scoring; never produce an
all-six headline accuracy. **All-uncertain does not pass usefulness**. A changed
answer alone is not improvement. No proposal authorizes release or drawer motion.

This convenience sample of six development images cannot demonstrate full-task
planning, safe replanning, holding inference, placement fit, manipulation success,
generalization or model superiority. No runtime integration follows automatically.
