# Supplied coherent situation: bounded sufficiency result

2026-09-27. The fixed coherent situation prefix **did not repair the two weak
advance decisions and reduced the approach gains in both approach states**.
All four choices changed, so the extra situation text affected the scorer.
That sensitivity does not establish correct situation or action understanding.

The [registered protocol](../../research/worldview_sufficiency_protocol.md) and
implementation were committed as `d12c4e6` before the CPU preflight and all
inference. This was one wording, 4 existing states × 2 conditions × 2 repeats,
with no prompt selection, simulator execution, new model or live integration.
No further wording or action-mapping experiment followed this negative result.

## Results

All 16 calls were valid. Every condition exactly repeated its native choice,
probability distribution and raw logits in reverse traversal. All eight fresh
baseline calls exactly matched the archived choices, probabilities and logits.
There were no missing calls, invalid responses, truncations or retries.

| Step / phase | Baseline choice | Situation choice | Baseline → situation immediate gain (mm) | Same-pool comparison |
| --- | --- | --- | --- | --- |
| 0 / approach | `x+40mm` | `rotate_x+10deg` | gap 29.114186 → 4.128456 | maximum gap reduction 29.114186 |
| 1 / approach | `x+40mm` | `rotate_x+10deg` | gap 15.697692 → 7.282016 | maximum gap reduction 23.007465 |
| 9 / advance | `open` | `close` | closure 1.755743 → 1.748296 | `y-40mm` closure 34.177342 |
| 10 / advance | `open` | `close` | closure 0.056385 → 0.056837 | `y-40mm` closure 31.888340 |

Both advance treatments retain alternatives with greater predicted closure, no
smaller gap reduction or terminal contact, and equal obstacle force, success
flag and control horizon. The 0.000451-mm closure increase at step 10 does not
resolve that comparison. Both approach treatments still predict positive gap
reduction; the instruction asks for substantial progress, so these are reduced
gains rather than newly invented binary incorrectness labels.

At step 9, the treatment's raw logits for `open`, `close`, and `y-40mm` are
1.0546875, 3.125, and −0.44140625; baseline logits are 2.09375, 1.8671875, and
0.26953125. At step 10 they are 1.109375, 2.9375, and −0.2177734375, versus
1.953125, 1.71875, and 0.08251953125. The native 11+ option temperature is
0.10058280825614929. Its rounded response gives `close` probability 1.0 in both
treatments. This is a scorer output, not calibrated certainty about the world.

## What was supplied and held fixed

The prefix supplied target identity, the existing local phase and intent, the
relevant relation, and field meanings. It described the **moving top-drawer
structure**, not a designated handle, and explicitly separated touching from
secure grasp. Its phase and numerical premises come from the existing visible
state; the source-to-packet mapping is in the protocol. The intervention is an
honest researcher-supplied interpretation of already privileged evidence, not
an acquired visual world model or a newly nonprivileged decision interface.

Every original state byte remained the exact suffix of the treatment, including
all numeric effects, history and provenance. Questions, empty criterion texts,
action membership and order were identical. No direction, winner, action rank,
top-k filtering, fabricated confidence or new oracle observation was added.
The constructor receives only the existing model-visible state to build the
prefix; a poisoning test verifies hidden predictions/labels cannot affect it.

| Step | Options | Baseline / treatment tokens | Treatment state tokens / budget |
| --- | --- | --- | --- |
| 0 | 7 | 372 / 449 | 382 / 957 |
| 1 | 7 | 406 / 483 | 416 / 957 |
| 9 | 25 | 923 / 996 | 836 / 864 |
| 10 | 16 | 652 / 725 | 612 / 911 |

All sequences fit the 1,024-token maximum and 256-token heading limit with
complete headings, options and state. Every actual forward-hook input ID and
option marker matches the CPU preflight, including the longest 996-token
sequence. A separate direct raw-log audit checked all 16 consumed inputs,
exact prefix/suffix preservation, unchanged questions/order and both repeats.
The tracked [evidence JSON](worldview_sufficiency_summary.json) contains all
eight exact state/question strings, candidate orders, decoded consumed inputs,
token IDs/markers, and all 16 native responses and raw logits.

## Remaining interpretation limits

The original action semantics are only partly explicit. Each state says
`XYZ world mm; rotations world degrees; nominal commands, predicted dynamics;
grip retained except open/close.` Translation and rotation IDs carry their axis,
sign, magnitude and units; all question criterion descriptions are empty.
`open` and `close` are bare IDs, not explicitly rendered as "open gripper" and
"close gripper". The heading implies their grip role but does not give a full
action-to-physical-effect dictionary; `hold` likewise has no prose definition.
These same deficiencies occur in both arms. The source implementation maps
open/close to gripper commands, but those implementation statements are not
model-facing input. A lexical confusion between closing a drawer and closing
the gripper therefore remains a plausible cause of the advance switch.

The result rejects sufficiency of this particular correct local situation
packet on these inspected states. It does not establish that all coherent
representations are unusable, that a VLM could acquire the same information,
or that Laya correctly understood the supplied action semantics. Extra text
also changes token positions and semantic emphasis; this test measures the
total intervention, not a specific linguistic mechanism. Four fixtures and
deterministic repeats do not establish generalization. The existing source
already has privileged objective routing, admission and effects. Its broad
contact geometry and historic zero valid handle-closure finding prevent any
claim about designated handle manipulation or causal full-task success.

## Reproduction and identities

Raw evidence root: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.

- `worldview-sufficiency-preflight-01/episodes.jsonl`:
  `ca473d33818a5ad21bbd4dfda4c375a564de5b4b691bce9c9e0aafc7749818f5`
- `worldview-sufficiency-run-01/episodes.jsonl`:
  `d1e2950d4e6bcb933d6a97228cc93f88eb15409d370eceedee0ed0767fac969b`
- Source current-motor `episodes.jsonl`:
  `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`
- Registered protocol: `1c0f60a0d537c74d8e33e98d5c55a2f578ff462aad9240ad9242bcded6699fe7`
- Experiment source: `f75536a539b61a70a2c06e20d54ed097e0c88965d8de73e7371f64fde2299901`
- Frozen model content: `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`

Inference used seed 1, bfloat16, offline cached weights, GPU 0 (RTX 4090).
The source used `CUDA_VISIBLE_DEVICES=1`; despite that environment difference,
all baseline logits exactly reproduced. Tests: **21 passed, 1 skipped** across
the new provenance/preservation tests and current motor replication tests; the
skip is an existing optional test. `git diff --check` passed.

Recompute the full raw report with
`python -m embodied_runtime.experiments.worldview_sufficiency --summarize
/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/worldview-sufficiency-run-01`.
