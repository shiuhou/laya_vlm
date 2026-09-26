# Exact situation + action definitions: bounded interaction result

2026-09-27. The exact combination of the previously tested situation prefix W
and action definitions A **did not repair the tested decisions**. W+A selected
the same actions as W alone: reduced predicted approach gain at both approach
states, and a weak finger-closing action at the one eligible advance state.
Separate negative results had left a concrete complementarity question; this
six-call check supplies no evidence of the hoped-for behavioral repair.

The [protocol](../../research/joint_interface_sufficiency_protocol.md), code and
tests were committed as `a3d7db4dd6e129358484c0c09fecae155ee7d621` before the
recorded CPU preflight and every model call. No new wording was authored:
**exact W, then exact A, then the exact baseline state**. All six calls were
valid; choice, probabilities and raw logits repeated exactly under reverse
traversal. There were no missing calls, retries, invalid outputs, infrastructure
failures or truncated inference inputs. No simulator or live controller ran.

## Matched outcomes

B is the original baseline, W the supplied coherent situation, A the supplied
primitive definitions, and W+A their fixed composition. The B/W/A columns are
archived controls whose exact fixtures, model/settings and repeatability were
revalidated before inference. No fresh control calls were needed or made.

| Step / objective | B | W | A | W+A | Predicted gain B → W+A (mm) | Same-pool reference |
| --- | --- | --- | --- | --- | --- | --- |
| 0 / approach | `x+40mm` | `rotate_x+10deg` | `rotate_x+10deg` | `rotate_x+10deg` | gap 29.114186 → 4.128456 | maximum gap 29.114186 |
| 1 / approach | `x+40mm` | `rotate_x+10deg` | `rotate_x+10deg` | `rotate_x+10deg` | gap 15.697692 → 7.282016 | maximum gap 23.007465 |
| 10 / advance | `open` | `close` | `open` | `close` | closure 0.056385 → 0.056837 | `y-40mm` closure 31.888340 |

The approach instruction requests "substantial" predicted surface-gap reduction,
so these are reduced gains, not new strict-argmax correctness labels. At step 10,
`y-40mm`, `y-10mm`, `y-3mm` and `z-3mm` each have greater predicted closure,
no less gap reduction/contact, and equal obstacle force, success and horizon.
For example, `close` gives closure 0.056836543 mm, gap reduction −0.059394271 mm
and no terminal target contact; `y-40mm` gives 31.888340463 mm, 0 mm and contact.
Both have 0 N obstacle force, no success and eight controls. The tiny increase
from B's `open` to W+A's `close` does not repair this decision comparison.

At the eligible advance state, native raw logits are:

| Arm | `open` | `close` | `y-40mm` | Native chosen probability |
| --- | --- | --- | --- | --- |
| B | 1.953125 | 1.718750 | 0.082519531 | `open`: 0.9113 |
| W | 1.109375 | 2.937500 | −0.217773438 | `close`: 1.0000 |
| A | 1.375000 | 1.031250 | 0.367187500 | `open`: 0.9644 |
| W+A | 0.832031250 | 2.703125 | −0.339843750 | `close`: 1.0000 |

W+A changes scores relative to each component even though its choices match W.
The unchanged native 11+ option temperature is 0.10058280825614929; its rounded
probabilities are scorer outputs, not calibrated semantic or physical certainty.
The two approach W+A choices have native probabilities 0.1997 and 0.2014 under
the native 6–10 option temperature 1.0000158548355103. The full distributions
and logits remain in the [evidence JSON](joint_interface_sufficiency_summary.json).

## Complete inputs and prospective budget exclusion

The CPU preflight measured the exact combined presentations before inference:

| Step | Options | Full tokens | State tokens / budget | Inference |
| --- | --- | --- | --- | --- |
| 0 | 7 | 538 | 471 / 957 | two calls |
| 1 | 7 | 572 | 505 / 957 | two calls |
| 9 | 25 | 1,085 | 925 / 864 | excluded before inference |
| 10 | 16 | 814 | 701 / 911 | two calls |

Step 9 exceeded the unchanged 1,024-token limit by 61 tokens. Its full raw state
and installed-builder budget audit are preserved as exclusion evidence; the
truncated builder preview was never submitted to the scorer. No compaction,
row filtering, token-limit change, replacement state or extra call followed.
This leaves **one advance state**, so the combined arm has no result at step 9.

The constructor imports the exact previously registered W/A prefixes and checks
the baseline identity. Every baseline state byte remains the suffix. Questions,
objective instruction, empty criterion texts, candidate membership/order/mapping,
effect numbers, history and provenance remain unchanged. The source-to-prefix
mappings are inherited from the prior protocols. A hidden-label poisoning test
checks that evaluator metadata cannot alter the model payload.

Raw heading/option/state IDs were concatenated independently of the installed
sequence builder and matched it in preflight. All six actual forward-hook inputs
and option markers matched those complete presentations. Direct inspection of
all three raw and decoded model-facing inputs confirms that both prefix
paragraphs and every original table row were consumed. Native choice markers
still precede bare action IDs with empty criterion descriptions; numerical
consequences remain in the state table. These observations describe the actual
interface and do not establish which part of it caused the ranking failures.

## Provenance, limits and next question

The archive gate checked raw B/W/A log hashes, exact reconstructed fixture and
payload identities, unchanged W/A module and protocol hashes, and each prior
run's 16 valid calls. Both archived B batches exactly matched source choices,
probabilities and logits; all prior reversed repeats matched exactly. Current
model, settings, dtype, package versions and GPU execution environment matched
both archived runs. This supports reusing those controls, while not turning
these inspected states or deterministic repeats into independent task samples.

The checkpoint content ID was
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.
Execution used seed 1, bfloat16, offline local files and GPU 0 (RTX 4090).
The original source used GPU 1; exact prior baseline replication supplies the
comparability evidence. Code and native execution identities are copied from
append-only logs into the tracked evidence JSON.

Raw root: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.

- `joint-interface-preflight-01/episodes.jsonl`:
  `d9315919854d8a17e757f805e07bfe931e3def82b4c742afda1f6e95df57c796`
- `joint-interface-run-01/episodes.jsonl`:
  `df423600c8a478191a3dfc9fd002c76c502fa1b4fc3128c81cb58b4bb1a1e8b5`
- Frozen source `episodes.jsonl`:
  `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`
- Registered protocol:
  `df3115bf95b04df385277e197570579498ab7c6621c830af7fcaf42577331d80`
- Frozen experiment module:
  `7accc1f0ba61147280c37993ed03a247d39c2de274d85f28030f48a790128c5d`

Tests before freezing: **36 passed, 1 existing optional skip** across the joint,
worldview, action-binding and current-motor suites; `git diff --check` passed.
Recompute the core report without inference with:

```
python -m embodied_runtime.experiments.joint_interface_sufficiency --summarize /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/joint-interface-run-01
```

The tracked summary additionally copies native response objects, call intents
and recorded identities from those same raw logs. W/A/B remain supplied,
privileged conditions; these outcomes neither establish acquired understanding
nor certify physical execution, valid handle interaction or secure grasp.
The composition changes text length, positions and emphasis, so its failure
cannot isolate semantic recognition from attention, binding or ranking.
No inference about all possible world representations, VLM necessity or a
universally minimal interface follows. This closes the registered six-call
interaction check; no further wording or model calls were run.

The highest-information remaining question is whether the scorer can bind each
candidate to its already supplied numerical consequences in its native option
representation, or whether it still fails to rank actions after that binding.
A lossless token-budget feasibility audit is needed before any such controlled
experiment: moving complete rows into criteria may exceed the separate heading
and option limits even when the total sequence fits. This is a proposed
mechanistic distinction, not an established cause or a runtime recommendation.
