# Full-RGB target-proposal verification

Registered before inference. Prospectively select exactly one general VLM,
`Qwen/Qwen2.5-VL-3B-Instruct`. Freeze its downloaded revision and local content hash
before any call; no model tournament or prompt search. This probes semantic target
verification, not high-level planning, motor choice, contact truth or skill.

Use the completed LocateAnything POINT probe attempt02. Its18 full-RGB frames are
already-inspected development data. Independently validate the source hash chain,
actual generated-token audit and parsed outputs. Admit exactly14 single in-frame
POINT outputs with terminal EOS. Explicitly exclude the4 mixed point/box outputs;
none is repaired by the VLM. Selection is based only on structural output validity,
not oracle membership or geometric distance.

Preserve each original384x384 uint8 RGB and a marked copy. The model sees ONE full
marked RGB image without cropping. Draw a red crosshair around the saved containing
pixel: offsets2,3,4,5 pixels in each cardinal direction, one-pixel stroke. The
central pixel remains visible; out-of-image arm pixels are omitted. Save both
continuous original point and containing pixel. Never recenter on an oracle target.
No oracle mask, depth, geometry, simulation phase, grasp/contact label, past image,
past answer or detector confidence enters generator artifacts.

Fixed instruction:

> The intended target is the metal handle on the top drawer of the small
> freestanding wooden cabinet in the foreground. The red crosshair marks a proposed
> target location. Classify which visible part the marked location denotes.
> Return exactly one label: target_handle (the intended handle), other_handle
> (a different drawer handle), other_region (another visible region), or uncertain
> (the visible evidence is insufficient). Do not infer contact or task completion.

This is coarse visible identity; a point immediately next to the target boundary
can denote the correct handle without being inside its exact rendered mask.
Do not add pixel-membership tolerance to the separate strict metric.

Run two exact repetitions of every input,28 calls total, repeat1 across all14 then
repeat2 across all14 in frozen source order. Same image bytes, instruction, processor,
checkpoint and greedy generation, max_new_tokens32, do_sample=false, use_cache=true.
No retries, crop, history, prompt variants, temperature search or runtime integration.
Stop on infrastructure failure and preserve complete and missing calls. Invalid
output or length-limit termination is recorded as invalid, without reinterpretation.

Record full prompt/messages and image artifacts; processor input token IDs, attention
mask, image grid and exact pixel tensor bytes hash/dtype/shape; actual model forward
input-ID trace; generated token IDs, raw decoded text, EOS and budget audit; wall
latency, device/dtype/package/model versions and GPU peak. No claim of complete
input or output from parsed text alone. Strict accepted labels are the four literal
strings after outer whitespace stripping. No arbitrary JSON/markdown/prose salvage.

Separate evaluator labels must be frozen before VLM inference. Record coarse
visible identity and label basis independently of VLM answers, retaining uncertainty.
Exact oracle visible-target pixel membership remains a distinct evaluator field.
The generator never reads this label file. Keep the three near-boundary exact-mask
misses distinct from two clearly wrong lower handles. Do not mark every strict
pixel miss as a semantic mistake. If label ambiguity remains, report separately.

Primary analysis: reject wrong-handle proposals while retaining correct-target
proposals, denominator14 each repeat. Report every label, wrong-handle false accepts,
correct-target retention, uncertain/invalid counts, conditional accuracy and coverage,
exact-repeat agreement, and all per-frame cases. Do not collapse abstention into
success. Coarse semantic and strict geometric scores must remain separate. The
four preexcluded mixed cases retain denominator18 accounting but receive no VLM call.

Possible conclusion: useful verification earns a semantic target-binding boundary,
not a planner. Failure means full-RGB reasoning has not yet supplied useful target
identity evidence. Neither outcome establishes collision safety, contact, grasp pose,
object extent, motion competence, or generalization. Stop after this probe.
