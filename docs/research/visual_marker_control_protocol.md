# Fixed marker-location visual sensitivity control

Registered after the primary VLM run returned target_handle for all28 calls,
including both clearly wrong lower handles. This is a bounded image-sensitivity
control, not a model/prompt search or runtime change.

Freeze source frame indices0,8,11,17 from visual-target-verification-inputs-01.
Root selected them prospectively for this control: early correct target, two
clearly wrong lower handles, and the late target-boundary case. Inspect unmodified
full RGB before generation. At resolution384x384 the fixed control pixel(192,288)
is visibly unobstructed wooden tabletop in all4; evaluator label other_region.
The location is defined algebraically as(floor(W/2),floor(3H/4)), never from an
oracle target/segmentation or model answer.

For each source frame include two input images:
1. Original marked RGB, byte-identical to primary input.
2. Raw full RGB with the same hollow red crosshair relocated to the fixed table
pixel. Construct from RAW image so the original marker is absent. Preserve center
pixel and exactly the same marker construction (offsets2..5,1pixel stroke).

Do not change target instruction, four literal output labels, model/revision,
processor, full-image presentation, generation config, seed, dtype, attention,
controller/runtime (unused), or parsing. SameQwen/Qwen2.5-VL-3B-Instruct pinned
revision66285546d2b821cf421d4f5eb2576359d3770cd3, bf16sdpa, greedy32token budget,
seed1, threads4. Use the existing runner and its consumed image/token/logit audit.
No crops, retries, history, threshold tuning or hidden label information.

Eight inputs in source order0,8,11,17, original then table for each. Two exact
repeats across all8 in that order:16 calls. Keep invalid labels/nonEOS as invalid
outcomes; stop only infrastructure/integrity failure. Complete/missing denominator
must remain16 planned calls. No original-model inference is reused as a new call.

Generator manifest contains source hashes, marker construction and variant, but
only the unchanged instruction and markedRGB enter the model. Evaluator labels
remain separate and frozen before inference: original coarse labels are inherited
from prior independently frozen labels; table variants allother_region.

Primary metrics: tablemarker other_region count/8, original-answer replication
count/8, marker-induced label changes on matched frames/repeats, uncertain/invalid
counts, exactrepeat consistency and logits/image-token provenance. Never call
all-other_region rejection evidence of useful identity recognition without checking
original retention. This is4correlated scenes, not a generalization benchmark.

Interpretation: correcttable rejection with retainedoriginal targets supports
coarse marker use while fine same-cabinet identity remains unresolved. Continued
target_handle everywhere fails this interface sensitivity control; it does not
prove the model globally ignores images. Incorrect/unreliable marker answers do
not justify adding a planner. Stop after this control; no prompt or model tuning.
