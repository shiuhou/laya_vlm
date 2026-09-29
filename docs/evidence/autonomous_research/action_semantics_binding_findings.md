# Supplied action definitions: bounded sufficiency result

2026-09-27. Explicit action-to-effector definitions **did not improve either
weak advance decision and reduced predicted approach gain in both controls**.
Both advance states still selected `open`, now explicitly defined as opening
the gripper fingers while commanding pose retention. The definitions affected
logits and changed both approach choices, but selection behavior does not certify
that Laya recognized or applied the supplied meanings.

The [protocol](../../research/action_semantics_binding_protocol.md), implementation
and tests were frozen as commit `3bde95c` before recorded CPU preflight and every
model call. This was one fixed wording on four existing states, baseline versus
definition prefix, with two opposite traversal repeats: **16 calls total**.
No situation prefix was stacked, and no further model calls, wording changes,
simulator execution or live controller integration followed this result.

## Native decisions and consequences

All 16 calls were valid. All eight condition pairs repeated their choice,
probabilities and raw logits exactly. All eight fresh baseline calls exactly
reproduced archived choices, probabilities and logits. There were no missing
calls, retries, invalid outputs, truncations or infrastructure failures.

| Step / objective | Baseline | Action definitions | Baseline → treatment gain (mm) | Same-pool reference |
| --- | --- | --- | --- | --- |
| 0 / approach | `x+40mm` | `rotate_x+10deg` | gap 29.114186 → 4.128456 | maximum gap reduction 29.114186 |
| 1 / approach | `x+40mm` | `rotate_x+10deg` | gap 15.697692 → 7.282016 | maximum gap reduction 23.007465 |
| 9 / advance | `open` | `open` | closure 1.755743 → 1.755743 | `y-40mm` closure 34.177342 |
| 10 / advance | `open` | `open` | closure 0.056385 → 0.056385 | `y-40mm` closure 31.888340 |

Both advance states retain alternatives with greater predicted closure, no
smaller gap reduction or terminal contact, and equal obstacle force, success
flag and control horizon. At step 9 these include `x+40mm`, `y-40mm`, `y-3mm`,
and `z-3mm`; at step 10 they include `y-40mm`, `y-10mm`, `y-3mm`, and `z-3mm`.
The approach instruction says "substantial" progress, so the reduced gains are
reported numerically rather than converted into a new strict-argmax correctness
label. None of these frozen predictions is a new executed outcome.

At step 9, treatment raw logits for `open`, `close`, and `y-40mm` are 1.375,
1.1640625, and 0.07373046875; baseline values are 2.09375, 1.8671875, and
0.26953125. At step 10 they are 1.375, 1.03125, and 0.3671875, versus 1.953125,
1.71875, and 0.08251953125. Native rounded probabilities for treatment `open`
are 0.8787 and 0.9644. These use the unchanged 11+ option temperature
0.10058280825614929 and are scorer outputs, not calibrated semantic confidence.

## What was supplied and preserved

The exact single paragraph was:

```
Primitive commands: x/y/z IDs move the gripper by the signed millimeters along that world axis, retaining orientation and finger command. rotate_axis IDs rotate the gripper by the signed world-axis degrees, retaining position and finger command. open/close command the gripper fingers open/closed while holding position and orientation. hold retains pose and finger command. These are commanded motions; achieved dynamics are the listed predictions.
```

These definitions abbreviate actual Jev `ACTIONS` and `World.execute`, whose
source locations, hashes and archive comparison are in the protocol. The
executor changes the positional target for translation, emits a signed rotation
command, sets open/close finger commands to −1/+1, and retains the finger command
for other primitives. Holding pose describes the command, not guaranteed achieved
pose under controller/contact dynamics. The unchanged effect table supplies
predicted consequences, including possible drawer motion during finger commands
or hold. The prefix asserts neither grasp nor achieved task progress.

Every original state byte remains the exact suffix. Questions and their empty
criterion descriptions, candidate IDs/order, effect numbers, objective, history
and provenance are unchanged. No winner, direction recommendation, ranking,
filter, additional observation or new physical premise was supplied. A poisoning
test verifies that hidden predictions and evaluator labels cannot affect the
definition paragraph or model payload.

Both arms remain privileged supplied-condition diagnostics: source state,
objective routing, candidate admission and effects already use oracle information.
The schema knowledge is also supplied by a researcher; it is not a learned visual
world model. Geometry concerns the moving drawer structure rather than a verified
designated handle, and no secure-grasp fact or interaction-valid manipulation is
established.

## Complete input and provenance audit

| Step | Options | Baseline / treatment total tokens | Treatment state tokens / budget | Heading + option tokens / limit |
| --- | --- | --- | --- | --- |
| 0 | 7 | 372 / 461 | 394 / 957 | 63 / 256 |
| 1 | 7 | 406 / 495 | 428 / 957 | 63 / 256 |
| 9 | 25 | 923 / 1012 | 852 / 864 | 156 / 256 |
| 10 | 16 | 652 / 741 | 628 / 911 | 109 / 256 |

All eight complete sequences fit the 1,024-token limit. Raw heading, option and
state tokens were independently concatenated with special tokens and matched
the installed sequence builder. Every actual forward-hook input and option
marker matched preflight, including the 1,012-token state. A separate direct
raw-log audit verified all 16 actual inputs and exact prefix/suffix preservation.
The tracked [evidence JSON](action_semantics_binding_summary.json) includes the
exact model-facing texts, raw and consumed component IDs, native responses,
logits, comparisons, and recorded model/code/environment identities.

Raw root: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.

- `action-binding-preflight-01/episodes.jsonl`:
  `bf335e439dbb56786e22a2fc802c3cca8a9ba406055a60e253a182ecaf49f449`
- `action-binding-run-01/episodes.jsonl`:
  `a6c42bf8ef985b4b9185b5a4fcc258b624b31d0d0a68f957d5638042e4449d2b`
- Frozen source `episodes.jsonl`:
  `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`
- Registered protocol:
  `ddb1366e48fd1f3ad90c30c4cd2e1dd4d3f88ddc11ef3bb5caae6480adcbad3a`
- Experiment module:
  `ea59261a23214f32421551e5b31a777d0cdd2a0bb2d08c7493c32cf79e86f3a6`
- Frozen model content:
  `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`

Inference used seed 1, bfloat16, offline local weights and GPU 0 (RTX 4090).
The archived source used `CUDA_VISIBLE_DEVICES=1`; fresh baseline logits still
reproduced exactly. Tests: **31 passed, 1 skipped** across binding, worldview
preservation and current motor replication tests; the skip is an existing optional
test. `git diff --check` passed.

Recompute the core report with:

```
python -m embodied_runtime.experiments.action_semantics_binding --summarize /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/action-binding-run-01
```

The tracked summary additionally copies recorded identities/native response
objects and reports the independent raw audit; these are read from the same
append-only logs without further model calls.

## Causal limits

These complete canonical definitions alone are insufficient to repair these
frozen choices. The experiment does **not** distinguish failure to recognize
definitions from failure to rank consequences after correct recognition. Added
text changes token positions, length and emphasis, so it measures the total
prefix intervention rather than a specific linguistic mechanism. In particular,
the result does not prove that a lexical confusion caused or explains away the
earlier situation-prefix result, and the joint intervention was not tested.

Four inspected states and deterministic repeats cannot establish generalization,
full-world understanding, acquired perception, long-horizon success or VLM
necessity. Neither this result nor the earlier situation-prefix failure warrants
predetermining an architecture or rejecting every coherent world representation.
