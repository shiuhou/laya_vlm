# Synthetic negative-direction ordering diagnostic

2026-09-23, `feat/mujoco_demo`, baseline `84abdb8` plus existing demo
instrumentation. User-authorized follow-up to the
[minimal synthetic direction probe](synthetic_direction_probe.md).
Exactly three new calls, for -X, -Y and -Z, compared with their saved synthetic
baselines. No baseline rerun, positive-direction call, execution, simulator or E0.

**Reordering alone corrects two of the three previous top-1 failures.**
-X changes from FWD to BACK; -Z changes from UP to DOWN. -Y changes from LEFT to
BACK and remains wrong. This establishes a substantial ordering contribution;
the previous failures cannot be attributed solely to inability to interpret
negative directions. Ordering is not a complete explanation of the residual
failure or evidence of reliable geometric grounding.

## Exact intervention

The original order was:

```text
MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN
```

Only the complete candidate entries are permuted, by indices `[1,0,3,2,5,4]`:

```text
MV_BACK, MV_FWD, MV_RIGHT, MV_LEFT, MV_DOWN, MV_UP
```

Each entry retains its exact identity and description. The new ordered menu is:

| Candidate | Unchanged description |
|---|---|
| MV_BACK | Move the hand 10 mm in the -X direction. |
| MV_FWD | Move the hand 10 mm in the +X direction. |
| MV_RIGHT | Move the hand 10 mm in the -Y direction. |
| MV_LEFT | Move the hand 10 mm in the +Y direction. |
| MV_DOWN | Move the hand 10 mm in the -Z direction. |
| MV_UP | Move the hand 10 mm in the +Z direction. |

The state strings are copied exactly from the preceding synthetic run:

```text
The target is 100 mm in the -X direction from the hand.
The target is 100 mm in the -Y direction from the hand.
The target is 100 mm in the -Z direction from the hand.
```

The question key is `action`, type `choice`, with unchanged instructions:

```text
Which single movement moves the hand closer to the target?
```

There is no additional state, history, effect annotation, task context or answer
hint. These remain synthetic directional sentences, not archived embodied task
states or new sensor measurements. Correct-answer labels stay in the audit only.

The checkpoint, configuration, tokenizer, relevant runtime sources and installed
Laya sources match the preceding run by hash. Both runs use seed 1,
CUDA/bfloat16 on GPU 6 and temperature `1.0000158548355103`. Every input remains
129 tokens with a 14-token state. Token audits establish that the new sequence is
exactly the original heading, the permuted complete option-token blocks, and the
original separator/state suffix. No heading, state or option is clipped.

## Complete probability distributions

Probabilities are API percentages; bold marks top-1. Columns below use the old
display order to simplify comparison; the new calls use the order stated above.
These probabilities are selection scores, not calibrated physical-success rates.

| Target / order | MV_FWD | MV_BACK | MV_LEFT | MV_RIGHT | MV_UP | MV_DOWN |
|---|---:|---:|---:|---:|---:|---:|
| -X / original | **30.94%** | 14.73% | 14.93% | 6.97% | 20.37% | 12.06% |
| -X / reordered | 18.63% | **40.06%** | 9.75% | 8.42% | 9.10% | 14.04% |
| -Y / original | 22.04% | 12.90% | **23.46%** | 10.67% | 19.53% | 11.40% |
| -Y / reordered | 13.21% | **30.41%** | 16.99% | 13.32% | 12.52% | 13.56% |
| -Z / original | 17.62% | 9.54% | 13.12% | 6.65% | **40.32%** | 12.76% |
| -Z / reordered | 11.81% | 25.70% | 10.34% | 7.96% | 17.25% | **26.93%** |

Full changes, reordered minus original, in percentage points:

| Target | MV_FWD | MV_BACK | MV_LEFT | MV_RIGHT | MV_UP | MV_DOWN |
|---|---:|---:|---:|---:|---:|---:|
| -X | -12.31 | +25.33 | -5.18 | +1.45 | -11.27 | +1.98 |
| -Y | -8.83 | +17.51 | -6.47 | +2.65 | -7.01 | +2.16 |
| -Z | -5.81 | +16.16 | -2.78 | +1.31 | -23.07 | +14.17 |

## What changes within each opposing pair?

The pair-conditional share is `P(correct negative action) / (P(negative) + P(positive))`.
It uses unrounded probabilities reconstructed from the raw logits, so unrelated
options' normalization does not determine this comparison.

| Target | Correct action | P(correct), old → new | Pair-conditional share, old → new | Share change, pp | Correct minus opposite margin, old → new, pp |
|---|---|---:|---:|---:|---:|
| -X | MV_BACK | 14.73% → 40.06% | 32.253% → 68.257% | +36.004 | -16.21 → +21.43 |
| -Y | MV_RIGHT | 10.67% → 13.32% | 31.258% → 43.942% | +12.684 | -12.79 → -3.67 |
| -Z | MV_DOWN | 12.76% → 26.93% | 24.042% → 60.952% | +36.910 | -27.56 → +9.68 |

- **-X:** Correct BACK becomes top-1 at 40.06%, ahead of FWD by 21.43 pp.
  Ordering alone is sufficient to remove this observed error in the tested menu.
- **-Y:** Correct RIGHT remains below its opposite LEFT, 13.32% versus 16.99%.
  Ordering explains part of the within-pair deficit: the margin improves by
  9.12 pp, but does not reverse. BACK becomes the overall winner at 30.41%.
  RIGHT's deficit to the best competing action actually grows from 12.79 to
  17.09 pp. A within-pair improvement must not be reported as task correctness.
- **-Z:** Correct DOWN becomes top-1 at 26.93%, ahead of UP by 9.68 pp.
  Ordering alone removes this observed error, but DOWN leads the new runner-up
  BACK by only **1.23 pp**.

## Updated interpretation

For these three particular top-1 errors, ordering is a **major contributor**:
the requested permutation removes two errors while everything else is fixed.
It accounts for most of the observed error count in this small set, not a
quantified fraction of the checkpoint's general grounding failures. For -Y,
the contribution is only partial within the relevant pair and does not fix the
overall decision.

The evidence now supports **strong sensitivity to candidate ordering with a
remaining grounding/ranking failure**, rather than a clean diagnosis of
order-independent signed-direction incapability. The earlier six-case probe's
3/6 result remains valid for its original order; its attribution must include
this newly measured order dependence.

This is not a pure “always choose the first candidate” rule: -Z chooses DOWN in
position 5. Nor is it an “always choose the earlier member of the target-axis
pair” rule: -Y still ranks LEFT above the now-earlier RIGHT. BACK's probability
rises by 17.51 pp on -Y and 16.16 pp on -Z despite being unrelated to those target
axes, consistent with a strong presentation preference. The exact internal
mechanism is not observable from the typed scores.

All three pairs were swapped together. This identifies the effect of that whole
permutation; it does not isolate an absolute-position bias from relative position,
label/position interactions or effects of neighboring options. No positive-target
cases were run under the new order. The two corrected winners therefore do not
establish that the checkpoint now reverses reliably with target sign: the new
order may favor negative candidates even when they are inappropriate. A residual
signed-direction weakness is still possible, but cannot be separated fully from
presentation effects by this diagnostic alone.

No order change is installed in the live demo. This does not justify sorting
candidates using the desired answer, changing CDS, or claiming task competence.
No further inference, simulator operation or formal research experiment followed.

## Artifacts and verification

Local ignored directory: `runs/engineering-demo/synthetic-negative-order-probe-v01/`.

- [Complete old/new distributions and new raw logits/token traces](../runs/engineering-demo/synthetic-negative-order-probe-v01/comparison.json)
- [Original synthetic inputs, responses, traces and provenance](../runs/engineering-demo/synthetic-negative-order-probe-v01/baseline-reference.json)
- Exact reordered inputs: [-X](../runs/engineering-demo/synthetic-negative-order-probe-v01/0-minus-x-input.json), [-Y](../runs/engineering-demo/synthetic-negative-order-probe-v01/1-minus-y-input.json), [-Z](../runs/engineering-demo/synthetic-negative-order-probe-v01/2-minus-z-input.json)
- [Derived metrics and verification results](../runs/engineering-demo/synthetic-negative-order-probe-v01/analysis.json)
- [Chained raw records](../runs/engineering-demo/synthetic-negative-order-probe-v01/episodes.jsonl)
- [Manifest](../runs/engineering-demo/synthetic-negative-order-probe-v01/manifest.json), [configuration](../runs/engineering-demo/synthetic-negative-order-probe-v01/resolved_config.yaml), [exact runner](../runs/engineering-demo/synthetic-negative-order-probe-v01/run_probe.py), [analysis-only verifier](../runs/engineering-demo/synthetic-negative-order-probe-v01/analyze_probe.py)
- [Console log](../runs/engineering-demo/synthetic-negative-order-probe-v01.console.log)

New JSONL SHA-256:
`551d27d72a078877c0c8f8068f4918e816c3533ecc185595db8f194b059f165d`.
Unchanged synthetic baseline JSONL SHA-256:
`d866b11d24b4525de54f59fdc912754f3f039d60a3289dc9ecb64854c8071d13`.

Inference exited 0. All 13 new chained records validate: exactly three new inputs,
outputs and forward traces, zero baseline reruns/retries/warm-ups, zero execution.
Original-order tokenizations were checked without inference. Both old and new
probabilities independently reconstruct from logits. Token-block permutation,
model/configuration/source identities, baseline integrity and unchanged runtime
hashes pass verification. No simulator modules were loaded. Report values, links
and `git diff --check` pass. Generated artifacts remain ignored; existing working
changes are preserved. No live behavior, CDS or shared component changed, and
no commit was made. Runtime tests were not rerun for documentation and ignored
diagnostic artifacts.
