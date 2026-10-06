# P1 fixed-reference budget-only completion diagnostic — 2026-10-07

**Increasing the native POINT budget from256 to1024 did not produce terminal
EOS.** The one fresh call reached1024 tokens and stopped at completion admission.
No typed POINT parse, support association, independent reference tracker,
drawer/reference temporal relation, VERIFY or PUSH followed.

## Frozen checkpoints and independent condition

Local annotated tags freeze:

- `p1-tracker-infrastructure-ab361eb` → `ab361eb`;
- `p1-tracker-evidence-065ad2b` → `065ad2b`.

The [freeze receipt](../tracker_episode_freeze_20261007.json) pins the preceding
raw/evidence archive hashes. Historical source, failed calls and successful
single-frame drawer tracker evidence were not overwritten. These are local
tags; no remote push was requested or performed in this phase.

[Preregistration](../../../research/p1_reference_completion_budget_protocol.md)
and implementation were committed at clean `bdab332` before launch. The only
generation-kwargs difference is `max_new_tokens:256→1024`. Native hybrid mode,
EOS handling, temperature0, do_sampleFalse, cache, BF16, checkpoint content ID,
reference query/template, typed contract and geometry/tracker gates remain
fixed. Generation audit accepts an explicit condition budget while its frozen
default stays256. No model/decoder source or runtime scheduling changed.

One fresh POINT used the original384×256 init25 agentview RGB; the old completed
BOX was preserved byte-for-byte and not rerun. Exact request JSON, full prompt,
209 input token IDs, processed image/grid and pixel hash equal the sealed
baseline byte-for-byte. Software versions and resolved model config match.
The same physical GPU2 UUID was explicitly allocated:
`GPU-293fca5f-bdb8-2235-fa2e-18ab6c488b36` (logical cuda:0). Sharing/load is
recorded; latency is descriptive rather than a causal comparison.

## Actual output and ordered gate

| Condition | Generated tokens | Terminal EOS | Completion |
| --- | ---: | --- | --- |
| Historical native hybrid, budget256 | 256 | No | Failed |
| New native hybrid, budget1024 | 1024 | No | Failed |

New generation took6.999065s; context limit was16384 with209 input tokens, so the
input fit. Actual generated IDs/count and full5633-character reply are sealed.
Root inspected the complete raw reply: coordinate-bearing box fragments continue
to the ceiling. No structured POINT/BOX cardinality or surface claim is inferred
from an incomplete reply. In particular there is no prefix acceptance, artificial
EOS, rewritten reply, convenient anchor or box-center fallback.

The completion gate stops BEFORE `parse_semantic_reply`; there is no `parsed`
field on the new raw response, no `typed-point.json`, no admitted-pair directory,
and no geometry or tracker invocation. The process exited0 after explicitly
recording `STOPPED_INCOMPLETE_GENERATION`; this is correct diagnostic termination,
not successful reference grounding. There was one fresh call, zero retries and
zero robot actions. The original incomplete eight-call experiment remains
incomplete and is not relabeled.

## Interpretation and boundary

Observed: fourfold output budget alone does not complete this exact reference
query under native hybrid decoding by1024. The raw reply visually exhibits
continued coordinate-bearing fragments. This weakens a short-budget-only
explanation; it does not prove endless generation, identify a decoder defect,
or show that a valid reference is absent from the camera image.

Reference semantic identity, support association, fixedness, temporal relation
and VERIFY observability remain UNKNOWN/unexamined downstream. No query tuning,
annotation seed, geometry relaxation or official-success substitute was used.
A further decoder/termination intervention would be a separately decided and
preregistered condition; no larger budget or alternate decoder ran automatically.

## Verification and lifecycle

Two focused budget/completion tests and Ruff passed; no broad suite ran.
All27 original source files and seven baseline reference files verified unchanged
before/after. Typed contract, semantic queries, geometry configuration/code,
surface association and tracker code remain byte-identical to `ab361eb`.
Complete raw requests/replies, token audit, loading identity/config, launch/GPU
registration, stdout/stderr, exit receipt and hashes are preserved. The
333,263-byte disposable process-specific model-code cache was removed only after
process exit; no canonical evidence or model checkpoint was deleted.

[Summary](summary.json) · [Hash index](artifact-index.json) ·
[Portable evidence](reference-budget1024-evidence.tar.gz).
Local condition: `runs/p1/reference-budget1024-gpu-20261007/`;
launch: `runs/p1/reference-budget1024-launch-20261007/`.
Original source and BOX/failure remain in the existing
[source](../surface_dev_20261006/README.md) and
[reference](../surface_gpu_diagnostic_20261006/README.md) archives.
