# Native option progress-value duplication: bounded sufficiency result

2026-09-27. Copying each action's existing printed progress value into its native
choice description **did not repair the tested decisions**. It reduced predicted
approach gains relative to baseline on both approach states and retained `open`
on the one eligible advance state. This rejects the sufficiency of this exact
local duplication on this inspected slice; it does not isolate semantic binding
as the cause of the failures.

The sole [proposal](../../research/native_option_progress_binding_proposal.md)
was reviewed after one CPU token-budget check. The exact
[protocol](../../research/native_option_progress_sufficiency_protocol.md), code
and tests were frozen at `37f94253fe381e3b4b1ee81d2f9ab5f23445730e` before
recorded preflight and every inference call. There were exactly **six calls**,
steps 0, 1, 10 and the reverse traversal, without a wording sweep. All were valid;
choices, probabilities and raw logits repeated exactly. There were no invalid,
missing or truncated inference calls, retries, infrastructure failures, new
control calls, simulator execution or live policy changes.

## Outcomes against exact archived controls

B is the original input, W the coherent-situation prefix, A the action definitions,
W+A their previously tested composition, and P the new progress-value duplication.
B/W/A identities and exact original-baseline/repeat replication were checked
before P inference. W+A is reported as prior context from its completed raw run.

| Step / objective | B | W | A | W+A | P | Predicted gain B → P (mm) |
| --- | --- | --- | --- | --- | --- | --- |
| 0 / approach | `x+40mm` | `rotate_x+10deg` | `rotate_x+10deg` | `rotate_x+10deg` | `rotate_z+10deg` | gap 29.114186 → 6.752232 |
| 1 / approach | `x+40mm` | `rotate_x+10deg` | `rotate_x+10deg` | `rotate_x+10deg` | `rotate_x+10deg` | gap 15.697692 → 7.282016 |
| 10 / advance | `open` | `close` | `open` | `close` | `open` | closure 0.056385 → 0.056385 |

Same-pool maximum approach gap reductions are 29.114186 and 23.007465 mm.
The instruction prefers "substantial" reduction, so these are reduced gains,
not newly invented strict-argmax correctness labels. At step 10 the selected
`open` predicts closure 0.056385217 mm, gap reduction −0.059129881 mm and no
terminal target contact. `y-40mm` predicts closure 31.888340463 mm, gap reduction
0 mm and terminal contact. Both have 0 N obstacle force, no success and eight
controls. `y-10mm`, `y-3mm` and `z-3mm` also offer greater closure, no less gap
reduction/contact and equal remaining comparison fields.

The step 10 logits moved, including an increase for `y-40mm`, without repairing
the native choice:

| Arm | `open` raw logit | `close` raw logit | `y-40mm` raw logit | Native `open` probability |
| --- | --- | --- | --- | --- |
| B | 1.953125 | 1.718750 | 0.082519531 | 0.9113 |
| P | 1.6171875 | 1.3046875 | 0.7890625 | 0.9567 |

P assigns `y-40mm` probability 0.0003 under the unchanged native 11+ option
temperature 0.10058280825614929. Its step 0/1 choices have native probabilities
0.1988/0.1924 under the unchanged 6–10 option temperature 1.0000158548355103.
These rounded scorer distributions are not calibrated semantic confidence.
The [evidence JSON](native_option_progress_sufficiency_summary.json) retains
all distributions, raw logits, native response objects and full comparisons.

## Exact supplied intervention and model-facing evidence

P leaves the original B state entirely unchanged and adds no W/A prefix. Each
formerly empty native criterion contains exactly one existing field and the
verbatim printed number for that same admitted action. For example, actual
consumed option text includes:

```
[MASK] x+40mm: gap_reduction_mm=29.11
[MASK] open: closure_mm=0.056
[MASK] close: closure_mm=0.057
[MASK] y-40mm: closure_mm=31.888
```

The native renderer supplies the action ID and colon. The constructor reads
phase only from the existing visible state, choosing `gap_reduction_mm` for
approach and `closure_mm` for advance. It copies strings directly from each
original effect row, preserving precision and signed zero. No hidden prediction,
evaluator objective, ranking or expected answer enters construction. A poisoning
test checks independence from those hidden fields.

All actions receive the same scalar-copy operation; no winner, ordering,
recommendation or candidate subset is supplied. Candidate IDs, membership,
order/mapping, question type and instructions are unchanged. The complete
original effect table, all remaining effect fields, history and provenance
remain in the exact original state. High-precision source effects used in the
post-choice comparisons were not substituted into the printed model input.

Direct inspection of all three decoded native inputs confirms both the copied
option values and every original table row. Independent raw component
concatenation matched the installed sequence builder. Every actual hook input
and option marker matched the complete preflight. The original state is not
shortened to make room for the native criteria.

A separate root-agent audit without experiment-report imports independently
checked exact original state/source/order/instruction preservation, every copied
criterion against the original printed column string, all six full native token
and marker sequences against actual forward hooks, argmax/repeat equality, and
selected source effects. All checks passed with zero model calls. Raw script and
result are at `native-option-progress-independent-audit-01/` under the raw root;
script SHA-256 is
`4d39b13aa0487d5c0a691a1b2bb79464ebb0d19520955737f773688e4828a726`.
The tracked evidence JSON includes this independent result and artifact identities.

## Prospective exclusion despite an apparently fitting effective length

| Step | Options | Raw heading + option tokens / 256 | Complete total tokens | Effective tokens | Native input complete? |
| --- | --- | --- | --- | --- | --- |
| 0 | 7 | 24 + 109 | 442 | 442 | yes; two calls |
| 1 | 7 | 24 + 109 | 476 | 476 | yes; two calls |
| 9 | 25 | 30 + 337 | 1,134 | 1,022 | no; excluded before inference |
| 10 | 16 | 30 + 208 | 781 | 781 | yes; two calls |

Step 9's effective 1,022-token sequence concealed native **option clipping**.
Its state and heading were retained, but the complete options did not fit the
separate heading-option budget. A total-length-only check would have missed
this defect. Both the sole design artifact and registered preflight preserve
its full proposed input, raw IDs and truncation flags. It received no model call;
no shortening, different wording, candidate omission, budget change or replacement
state followed. The experiment consequently has only one advance state and no
P result for step 9.

## Provenance, interpretation and stopping point

The archived B/W/A gate reused the exact frozen hashes and checks from the joint
probe. It reconstructed fixtures, source/payload identity and native inputs,
verified all prior source-baseline and reverse-repeat matches, and required
unchanged model, settings, dtype, package versions and GPU environment. Inference
used seed 1, bfloat16, offline local files and GPU 0 (RTX 4090), checkpoint content
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.
This justifies reusing the controls but does not create independent task samples.

Raw root: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.

- `native-option-progress-preflight-01/episodes.jsonl`:
  `31b0b44897f0b5d05fbdbad0bb036b63e65824f1de7926db37afebdbf9dcd1e5`
- `native-option-progress-run-01/episodes.jsonl`:
  `4593d0567b6ad450505a8c0f969f7f9500850ccccc71dbc851c954f6361ef650`
- Sole design artifact `option-progress-binding-design-01.json`:
  `272dc7c7cf67136f5fa740884560f3327c8a27dd5518b2c6341ac92c32253dc4`
- Frozen source `episodes.jsonl`:
  `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`
- Registered protocol:
  `49c9d74fd462734fe9777ae7815dc39025e6d1cb8ebbab9bde1c7d82609b052c`
- Frozen experiment module:
  `96952c461b8b192b6cf3533a316094e76c3b8f393787f8acba0c28515a4ccaec`

Tests before freezing: **37 passed, 1 existing optional skip** across native
progress, joint, action-binding and current-motor checks; `git diff --check`
passed. Recompute the core report without inference with:

```
python -m embodied_runtime.experiments.native_option_progress_sufficiency --summarize /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/native-option-progress-run-01
```

The tracked summary additionally copies native responses, call intents and
recorded identities from the same append-only logs. No new calls are needed to
reconstruct the evidence. Effects remain frozen oracle-simulator predictions,
not newly executed trajectories; state, candidate admission and objective routing
remain privileged supplied conditions.

The intervention changed repetition, association, proximity, format, emphasis
and token positions together. Its negative result does **not** show that values
were correctly recognized and bound before ranking failed. Conversely, an
improvement would not have isolated semantic binding. This result says only that
this exact per-option duplication was insufficient here. It establishes neither
acquired physical understanding nor a need for a VLM or an architectural change.

This closes criterion/prefix micro-variants on these inspected states. The next
research slot should address an orthogonal uncertainty: whether a sensory
interface on fresh views/states can identify the task-relevant object or
interaction region and its motion/contact relation with independently checkable
grounding. That should be assessed before another wording or criterion refinement
on this same slice. No further experiment or live policy change followed here.
