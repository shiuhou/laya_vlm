# Fixed-query Qwen2.5-VL-7B capability control

The larger checkpoint improved useful single-relation labels from 2/18 to 9/18,
but coherent all-field scenes remained 0/6 and primary subgoal agreement fell
from 1/3 to 0/3. Most correct relation labels are explained by constant answers.
This control does not establish a capability rescue for visual proposals or
coherent scene reasoning under the fixed interface.

## Frozen comparison

The [protocol](../../research/vlm_capability_control_protocol.md), registration
implementation and tests were frozen in `ce698e6` before the registered run.
Exactly the original 24 single-relation calls and seven subgoal calls ran once.
The original images, prompts, label sets, order, greedy 32-token cap, BF16/SDPA,
cache, seed1 and four CPU threads were retained. No training, prompt tuning,
runtime integration, extra checkpoint, model retry or physical execution occurred.
The original 3B scores and failures remain intact.

One pinned checkpoint was acquired:
`Qwen/Qwen2.5-VL-7B-Instruct`, revision
`cc594898137f460bfe9f0759e9844b3ce807cfb5`, content ID
`c4c1156e0c3419c0103b28bae5df90fb4b4c0d348172fa55cff23898ec6e51a1`.
All 14 files (16,595,961,188 bytes) matched pinned provider metadata; the five
weight shards total 16,584,414,560 bytes. Git blob IDs or provider SHA-256 ETags
were verified as appropriate, and all local weight SHA-256s were rechecked.
Acquisition network failures and range resumptions remain logged. They preceded
registration and were not model-query retries.

## Every relation answer

Each cell below is one independent query. Mirrors are dependent image controls.

| Input | Horizontal | Gap | Orientation |
|---|---|---|---|
| text-only | uncertain | separated | uncertain |
| uniform gray | uncertain | separated | uncertain |
| original0 | left | separated | diagonal |
| mirror0 | left | separated | upright |
| original2 | left | separated | diagonal |
| mirror2 | left | separated | diagonal |
| original4 | left | separated | diagonal |
| mirror4 | left | separated | diagonal |

| Registered measurement | 3B | 7B |
|---|---:|---:|
| Useful scene fields | 2/18 | 9/18 |
| Horizontal scene answers correct | 2/6 | 2/6 |
| Gap scene answers correct | 0/6 | 4/6 |
| Orientation scene answers correct | 0/6 | 3/6 |
| Coherent scenes (all three independently asked fields) | 0/6 | 0/6 |
| Correct absent/gray abstention | 4/6 | 4/6 |
| Invalid relation outputs | 0/24 | 0/24 |

7B mirror consistency is horizontal 0/3, gap 3/3, orientation 2/3; both-sides
correct is 0/3, 2/3, 1/3 respectively. All six scene horizontal answers are `left`.
Every gap answer is `separated`, including text-only and gray. Five of six scene
orientation answers are `diagonal`; the sole `upright` is mirror0. Constant labels
explain the horizontal and gap scores, and much of the orientation score. Mirror
consistency by itself does not demonstrate correct binding or visual sensitivity.

## Every subgoal answer

| Input | Exact 7B answer | Registered acceptable primary labels |
|---|---|---|
| task-only | approach_drawer | one answer scored against the three primary sets |
| RGB0 | establish_grasp | approach_object |
| RGB1 | approach_drawer | approach_object, establish_grasp |
| RGB2 | establish_grasp | transport_object |
| RGB3 | establish_grasp | descriptive only |
| RGB4 | establish_grasp | descriptive only |
| RGB5 | approach_drawer | descriptive only |

Both 7B RGB primary agreement/usefulness and its task-only comparison score are
0/3. The 3B values were 1/3 and 1/3. The task-only score reuses one response across
three label sets; it is not three independent calls. RGB3–5 have no correctness
or safety gold. All seven outputs are valid, with no uncertainty answer. These
observations do not establish readiness for grasping, transport or placement.

## Native paired audit and resources

Both persisted native audits pass: unchanged scorers, complete query intent/order,
raw hash chains, actual forward input traces, full native vocabulary logits,
greedy token choices, decoding and EOS; frozen preflight and registration; pinned
checkpoint files and loaded model/config/processor/generation settings. All 31
queries completed with terminal EOS, zero invalids, zero cap hits and zero
generation failures. Gold content is read only by the evaluator, never the model
generator.

For every matched 3B/7B call, actual messages, rendered prompts, input IDs,
attention masks, RGB bytes, FP32 processor pixels, consumed BF16 pixels, grids,
processed image sizes and image-token counts match. All token-count deltas are
zero. Actual images process to 588×588, grid `[1,42,42]`, 441 image tokens.
Text-only calls pass no image. The software versions match both baselines.
The native 7B vocabulary size is 152064 versus 151936 for 3B; auditing uses the
actual checkpoint vocabulary instead of assuming equality.

The checkpoint fits natively on physical GPU2 (RTX4090). Relation generation sums
to 4.593968 seconds, subgoals to 1.684657 seconds; overall peak allocated memory
is 16,025.224 MiB and reserved memory 16,332 MiB. These timings exclude acquisition,
model loading, preflight and audits, and are not an end-to-end runtime benchmark.
Relevant tests passed 51 cases with one optional actual-source case initially
skipped; that case subsequently passed from the canonical source cwd (52 distinct
checked cases). No frozen Python source changed while writing these findings.
An independent root audit, using raw files without producer scorer imports or
model calls, also passes all 31 paired input/native greedy/EOS checks and
reconstructs both scores. Its script and report are retained at
`vlm7b-root-independent-audit-01/{audit.py,summary.json}` under the raw root.

## Interpretation and evidence

The paired presentation checks rule out a changed prompt, image preprocessing,
token budget or malformed native inference as the explanation for this contrast.
The gain is uneven label-level performance on this fixture, without coherent
scene or useful subgoal improvement. Negative evidence now includes both pinned
checkpoints under the fixed interface and imagery. It does not identify a sole
cause among capability, referent/question binding or image/interface distribution.
It does not refute the proposed division between visual proposals and independent
physical verification, or establish planner, manipulation or generalization claims.

These remain convenience images reconstructed from lossy primitive-trace video,
with previously frozen non-blinded visual annotations and dependent synthetic
mirrors. No pooling of relation and subgoal scores is appropriate. No additional
checkpoint, prompt sweep or query retry is earned by this registered control.

Raw root:
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.
The acquisition and registration directories are
`vlm7b-capability-acquisition-01` and `vlm7b-capability-registration-01`.
Each probe has `vlm7b-capability-{relations,subgoals}-preflight-01` and `-run-01`;
run directories retain complete episodes, full native logits and audited summaries.
The execution driver records registration, both preflights, both generations and
both audits. The compact [summary](vlm_capability_control_summary.json) preserves
all 31 response strings, paired checks and per-probe outcomes.

| Identity | SHA-256 |
|---|---|
| Verified acquisition | `91d286757069b13148e4cb1f008cdb6623997a79a2ee708cdc110be100a67f4f` |
| Registration | `909fd2ebc9051e7a75ace59b106a06de906e13ceec69b5e59fdd022ea8258297` |
| Protocol | `ddb1265bc40cee1a3d152d1f2688ca3fd2943309461167e488f5e9e0874d3c51` |
| Relation episodes | `50603ec41159cca96f3e55549a5203c00641718849e217a3abb4f538712fea89` |
| Relation audited summary | `77ffc63f6a0b7d25424acab510a536eebb67b2a3d743a3968d163f3cdb7e79ec` |
| Subgoal episodes | `a4d29b33d9c4e36213e76bceaa31550b2e93a5e91f965f60d05f9c46371c6b5c` |
| Subgoal audited summary | `761f73765399b41264b0c72461746d7910d8c4bb94f97d671416d021af566a89` |
