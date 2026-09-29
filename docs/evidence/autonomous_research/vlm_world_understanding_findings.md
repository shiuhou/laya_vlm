# Direct image-relation investigation

The pinned Qwen2.5-VL-3B did not provide coherent answers to three coarse visible
relations on this small image set. Simplifying joint answers to independent
single-word questions fixed formatting but did not produce scene discrimination:
all eight horizontal calls returned `aligned`, all eight gap calls `uncertain`,
and all eight orientation calls `uncertain`, including text-only and gray controls.
Useful scene-field coverage was 2/18 and all-three agreement 0/6. This is evidence
about this model/interface/fixture, not proof that the model ignores images or
lacks any internal visual representation.

## Why this experiment was earned

Before any new call, the existing `visual_subgoal_probe.summarize` independently
verified the prior seven-call run's hash chain, completed intent order, actual
forward inputs, image tensor identities, full-vocabulary greedy logits, decoding
and terminal EOS. The run had `generation_complete`: text-only and RGB0–4 answered
`establish_grasp`, RGB5 `uncertain`; primary agreement 1/3 equaled text-only 1/3.
Its raw episode SHA-256 was
`c6b24951478e99f2fff808ad7fa3539edeb644de28467bd92cd11aacfc395365`.
No duplicate subgoal run was started.

That result left several explanations: visual relation reading, binding evidence
to intent/subgoal labels, or the task instruction's prior. The new investigation
asked direct geometric questions without action labels and added mirror, absent
image, gray image and task-prefix controls. The author personally inspected the
original RGB0,2,4 before freezing their labels.

The registered fields were strictly **image** relationships: bottle-center x
relative to the visible drawer interior's horizontal extent; visible gap versus
adjacency at gripper fingertips; and approximately vertical versus clearly
diagonal bottle axis. They do not assert 3D alignment, containment, contact,
stable holding, grasp strength or placement fit.

| Original image | Horizontal | Gap | Orientation |
|---|---|---|---|
| 0 | left | separated | upright |
| 2 | left | adjacent | upright |
| 4 | aligned | separated | diagonal |

Exact horizontal mirrors flip left/right only. All three fields are uncertain
for absent images and uniform gray. These are convenience-selected development
images from lossy resampled primitive-trace video reconstruction, not original
raw sensor/control replay. Synthetic mirrors are dependent image-binding
controls, not physical camera samples.

## Registered twelve-call joint-field probe

[Protocol](../../research/vlm_world_relations_protocol.md) and code were committed
as `35ff3f66f7cae59e5dc4f2350c4208e9e3cd47dc` before preflight and generation.
Exactly twelve independent calls ran: neutral text, neutral gray, six neutral
original/mirror scenes, task-prefixed text, and three task-prefixed originals.
The task condition added only the earlier task sentence. No chain-of-thought was
requested; no invalid output was salvaged or retried.

| Call | Exact decoded output | Registered status |
|---|---|---|
| neutral-text | `left/aligned/uncertain, separated/adjacent/uncertain, upright/uncertain` | invalid |
| neutral-gray | `left/aligned,uncertain,upright` | invalid |
| neutral-original-0 | `aligned/uncertain,adjacent/uncertain,upright/uncertain` | invalid |
| neutral-mirror-0 | `left/aligned,uncertain,upright` | invalid |
| neutral-original-2 | `aligned/uncertain,adjacent/uncertain,upright/uncertain` | invalid |
| neutral-mirror-2 | `aligned/separated/upright` | invalid |
| neutral-original-4 | `aligned/uncertain,adjacent/uncertain,upright/uncertain` | invalid |
| neutral-mirror-4 | `left/uncertain,adjacent/uncertain,upright/uncertain` | invalid |
| task-text | `aligned/separated/upright` | invalid |
| task-original-0 | `aligned,uncertain,upright` | valid |
| task-original-2 | `aligned,uncertain,upright` | valid |
| task-original-4 | `aligned,uncertain,upright` | valid |

Nine of twelve outcomes were invalid; all had EOS without reaching the budget.
Neutral scene agreement was 0/6, with every scene invalid. All three abstention
controls were invalid. The three task-prefixed scene answers were valid but
identical, with 0/3 all-field agreement and field agreement 1/3 horizontal,
0/3 gap, 2/3 orientation. Task text changed format compliance; it did not yield
scene-appropriate joint answers. This does **not** establish detrimental task
interference, because neutral syntax failure makes that comparison inconclusive.

The slash-template copying created a concrete output-composition confound.
Consequently the protocol's one allowed follow-up was earned. The first run
remains a negative result; the follow-up does not replace its scores.

## One frozen single-field follow-up

[Follow-up protocol](../../research/vlm_world_single_relation_protocol.md) and code
were committed as `7ff4963b0b1a92ecc2c96d83624db5671392371c` before its preflight.
Its evaluator mechanically projected the original frozen labels with no new
judgments. All image bytes and geometric definitions were preserved. Each of the
three relations was asked separately with one-word output, removing the joint
format and slash template together. This intervention cannot isolate those two
syntax components from each other.

Exactly 24 independent calls ran: three questions times the same eight image
conditions. Every call returned a valid in-field label with EOS below the cap.
The table lists all outcomes; columns come from independent calls.

| Input | Horizontal answer | Gap answer | Orientation answer |
|---|---|---|---|
| text-only | aligned | uncertain | uncertain |
| uniform gray | aligned | uncertain | uncertain |
| original0 | aligned | uncertain | uncertain |
| mirror0 | aligned | uncertain | uncertain |
| original2 | aligned | uncertain | uncertain |
| mirror2 | aligned | uncertain | uncertain |
| original4 | aligned | uncertain | uncertain |
| mirror4 | aligned | uncertain | uncertain |

| Measurement | Horizontal | Gap | Orientation |
|---|---:|---:|---:|
| Correct scene answers | 2/6 | 0/6 | 0/6 |
| Scene uncertain answers | 0/6 | 6/6 | 6/6 |
| Correct abstention controls | 0/2 | 2/2 | 2/2 |
| Invalid answers | 0/8 | 0/8 | 0/8 |

Useful accepted scene-field coverage is **2/18**: only the aligned original4 and
its mirror. All-three agreement by joining the independent questions is **0/6**.
All nine mirror field-pairs are algebraically consistent, but only the horizontal
original4/mirror4 pair is correct on both sides. Constant `aligned` or `uncertain`
answers make consistency vacuous; it must not be reported as robust binding.

## Native audit, resource use and artifacts

Both runs have clean committed source identities, exact frozen-preflight equality,
complete terminal records, no instrumentation/infrastructure failures, and a
second audit from the persisted native tokens/logits/forward traces. No actual
image was passed for text-only conditions. Gray conditions passed actual pixel
tensors. Every image used native processing from 600x600 to 588x588 with 441
image tokens. Processor floats and consumed BF16 tensors were separately hashed.
There was no input truncation or output-budget failure.

Both runs used the same local Qwen2.5-VL-3B-Instruct revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, checkpoint content ID
`11fccd61f55d2716ae7f8d4e28790b58b63d4126ade6994cef640a3cf337aa33`,
BF16/eval/SDPA, greedy 32-token cap, cache enabled, seed1, four CPU threads,
offline loading, and physical GPU2 (RTX4090, visible as cuda:0). No new model,
training, API call, or physical execution occurred.

Joint-field generation totaled 6.098 seconds, 144 generated tokens and peak
allocated memory 7.226 GiB. The follow-up totaled 4.233 seconds, 64 tokens and
7.213 GiB. These times exclude loading/preflight/artifact audit and are not an
end-to-end runtime benchmark. Image interventions affected first-step logits:
original/mirror maximum absolute differences were 0.875–1.4375 in the first run
and 0.390625–0.9375 across follow-up field/pairs. Constant labels are therefore
not evidence of absent image consumption or completely image-invariant logits.

All raw artifacts are under
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`:

| Evidence | Joint-field | Single-field |
|---|---|---|
| Frozen input directory | `vlm-world-inputs-01` | `vlm-world-single-inputs-01` |
| Frozen labels | `vlm-world-labels-01/labels.json` | `vlm-world-single-labels-01/labels.json` |
| Preflight | `vlm-world-preflight-01` | `vlm-world-single-preflight-01` |
| Generation and derived audit | `vlm-world-run-01` | `vlm-world-single-run-01` |

Each generation directory contains `episodes.jsonl`, native `logits/*.npz`,
`summary.json`, and `audit_metrics.json`, in addition to run configuration and
manifest. Summaries can be regenerated using the corresponding experiment module's
`summarize --output <run-dir> --evaluation <labels-file>` command.

| Identity | Joint-field SHA-256 | Single-field SHA-256 |
|---|---|---|
| Protocol | `4e953022a0a6ebe887e42a98439cc217bc551abb9126ac2d5f16bf83dbd4827c` | `d2c24a4cbe12a5aee7893ccad082f525032a457c8ba49577a6ed2c98e718e251` |
| Input manifest | `9835e5fdddd15b6dd85f8ccb8464106d8a73640233fe4587f548e7b1b607dbde` | `c270d30866bf278f02acfb7ccfaef78d8336753c8f66ee8c17285c15a8315d99` |
| Evaluator | `763531c915563eb030da1af4649deb9d26b1fdac1f70c6b4549c74ae3ddb1e2f` | `441cc0baccefbab5ab105cd701aa73ad3f8632a3173dc3bce3e469c4b91dbe80` |
| Episodes | `127ee191b3734f22a193fc90591f6f9045bc16fe1d709ec3fe4cf6e18565ecad` | `1692a09b52ba8284d70e14a33cb176f77d4066d949b420b21a515817cda2923f` |

The relevant test command ran 48 passing tests and one skipped legacy relative
input-fixture check: `tests/test_vlm_world_single_relation.py`,
`tests/test_vlm_world_relations.py`, and `tests/test_visual_subgoal_probe.py`.
Checks include true no-image presentation, transformations despite rehashed
tampering, strict field vocabularies, native audit preservation, no invalid-output
salvage, dependent mirror scoring, and abstention/usefulness separation.

## Belief update and stopping decision

**Observed:** this interface produces format-compliant but scene-insensitive
single-relation labels after the joint-format failure is removed. High-level
action-label binding and the original task sentence therefore cannot, by
themselves, explain all failures: the direct neutral questions also fail to give
useful relation information. Remaining causes include this model's capability,
question/referent binding, synthetic-render appearance, conservative abstention,
and the chosen input/interface distribution. These experiments do not uniquely
separate those causes.

**Not established:** coherent image-derived world understanding, object relation
tracking, state estimation, high-level planning, or downstream motor competence.
No task-specific VLM representation or planner integration is earned. Correct
answers on two dependent aligned cases are explained by the constant answer and
do not show image contribution.

Stop this prompt/fixture line after its one registered follow-up. If the research
program next needs to separate model capability from architecture, one stronger
pinned local VLM on a prospectively frozen capability control could be justified
before building around the present model. That is a proposed resource decision,
not an experiment executed here or a claim that scaling will succeed. A model
tournament or repeated prompt reformulation is not warranted by these results.
