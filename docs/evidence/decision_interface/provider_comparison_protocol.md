# Frozen full-effect provider comparison

2026-09-23. Declared before independent-provider inference. Research worktree on
`research/decision-interface`, baseline `eddbcde`, preserving the preceding
uncommitted effect-binding diagnostic. No E0 or runtime/schema/controller changes.

## Provider selected independently of results

Select **Qwen/Qwen2.5-7B-Instruct**, revision
`a09a35458c702b33eeacc393d103063234e8bc28`, as one independent instruction-following
provider. It is publicly available, supported by the installed Transformers 4.57.3,
and fits an available 24 GiB GPU in bfloat16. It uses a different model family,
training and autoregressive inference path from Laya's typed-choice scorer. Local
inventory found Laya, rule/replay baselines and specialized LocateAnything weights;
no general-purpose independent decision checkpoint or configured API credentials.
Download this one pinned checkpoint; do not screen providers on fixture results.
Keep acquisition provenance and failures under `runs/provider-comparison/`.

RuleProvider would test a hand-written policy, not independent learned competence.
LocateAnything's modified grounding decoder is not a reasonable general decision
baseline. The selected Qwen checkpoint is not the project's fine-tuned visual model.

## Frozen source and controlled variables

Read archived fixture records directly from
`runs/effect-binding/factorial-v01/episodes.jsonl`, SHA-256
`3875a25255eeb7880e1168579567758f68d616d39a023cc28c1ddef3e0c5eea5`.
Validate its raw Laya outputs and fixture/payload identities before selecting all
and only `effect_detail=relative` fixtures: **64 fixtures, two repeats, 128 calls**.

Preserve physical boundaries (init 0/1/2 step 48, init 0 step 140, seed 1), source
state identities, exact state string, question, eleven option IDs/descriptions,
order, effect facts and assignments, goals, empty history, utility thresholds and
contract flags. Include both native/anonymous descriptions, true/shift-four effects,
closed/open goals and both option orders. These factors are paired, not pooled away.
The second repeat reverses fixture traversal, as in the Laya experiment.

**Scope correction:** these frozen fixtures are an exploratory sentence projection,
not a full `CanonicalDecisionState` serialization. Preserve that projection and its
source CDS/physical linkage; do not replace it with CDS fields. This comparison can
establish competence on this bounded effect-conditioned interface only. It cannot
establish full CDS v0.1 or no-effect state sufficiency.

## Provider transport and inference

Keep question, options, then state in the same logical order as Laya's sequence.
The Qwen user message is `choice question: <unchanged question>`, followed by one
`<unchanged ID>: <unchanged description>` line per option, followed by the unchanged
state. Use the checkpoint's native chat template. The sole system instruction is
`Return exactly one option ID from the supplied options, with no other text.`
This replaces Laya's structural typed-choice output mechanism, adding no task advice,
examples, new facts, reasoning request or evaluator labels. Record messages, rendered
prompt, complete token IDs, and payload hashes. Model-specific tokenization/chat
framing and generation versus typed scoring are unavoidable provider differences;
conclusions concern provider/checkpoint/adapter pairings, not weights alone.

Use Transformers native Qwen2 causal model, evaluation mode, CUDA/bfloat16, SDPA,
batch size one, greedy decoding (`do_sample=False`), seed 1 set once, maximum 16 new
tokens, and checkpoint EOS/PAD IDs. No constrained decoder, model-output reranking,
fallback, retry after an invalid response, or post-result prompt adjustment. Parse
only a complete option ID after surrounding whitespace removal. Other outputs are
invalid choices and remain in the evidence/denominator.

Audit token fit without truncation and capture actual forward input IDs. Preserve
the unmodified generated sequence/text and full next-token logits in hashed binary
artifacts. These are vocabulary logits, not Laya option probabilities; do not
fabricate option confidence or compare probability magnitudes across providers.
Verify greedy generated IDs against raw-logit argmax. Retain failures, unmatched
intents and incomplete coverage. No source/evaluator metadata enters inference.

## Evaluation and stopping

Use the previous independent numeric local-utility criterion unchanged: >0.25 mm
actual goal-directed opening change AND >0.25 mm improvement beyond STOP, plus the
same sampled obstacle rule. Evaluate true assignments for physical utility. For
shifted assignments, assess consistency with the supplied facts separately from
actual physical outcomes. No reinterpreting false effects as physical truth.

Report useful choices, supplied-fact consistency, paired goal reversal, paired
effect reassignment, option-order behavior, invalid outputs and same-input stability.
For reassignment, correctness of both choices matters; mere change is insufficient.
Do not require identity changes when the supported sets overlap. Retain local
contract flags and distinguish progress from deployment validity.

The native bounded reference passes only if all native true-effect choices are
locally supported and every native shifted-effect choice follows its supplied
facts, across all states/goals/orders/repeats, with stable valid responses. The
anonymous condition is a matched secondary diagnostic, not a replacement task.
A pass supports outcome (1) **only for the frozen local effect-conditioned scope**;
it does not establish an unqualified task expert, safe execution, full CDS sufficiency
or formal E0 readiness. Valid failures support cross-provider persistence on this
presentation (2); technical or material comparison failures support a specifically
evidenced inconclusive result (3). Stop after this comparison and name one next test.
