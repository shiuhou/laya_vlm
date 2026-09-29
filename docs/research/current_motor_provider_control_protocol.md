# Current motor provider control v0.1

## Question and intervention

Can the already available Qwen2.5-7B-Instruct provider use the same current motor
state, local objective and numerical effects that produce poor immediate ranking
in Laya? This is a bounded provider control, not a VLM/planner implementation,
model tournament, prompt search or closed-loop competence comparison.

Use the five unchanged fixtures from `current_motor_replication`: source boundaries
0, 1, 9, 10 and 87 of `local-objective-task-adapter-episode-01`, selected by the
previously registered first-two-per-objective/first-lookahead rule. Candidate counts
are 7, 7, 25, 16 and 25. Source JSONL SHA-256 is
`9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`.
The completed fresh Laya replication JSONL SHA-256 is
`afe0c64acf7b82d7a0a3c99ed50bd09b02db67cbccbd6fa3466ae71e53fb0804`.

Competing hypotheses:

- The current logical presentation is sufficient for at least one existing
  provider; Laya's ranking limitation is not explained solely by absent subgoals.
- The same presentation is difficult for both providers, or is underspecified.
- A provider/output-format mismatch prevents an interpretable comparison.

## Fixed provider, payload and execution

Reuse `provider_comparison.FrozenTransformersProvider`, its unchanged SYSTEM
instruction, chat wrapper, greedy generation, bfloat16/SDPA execution and
`max_new_tokens=16`. The SYSTEM is:
`Return exactly one option ID from the supplied options, with no other text.`
Checkpoint: `/home/junhongli/models/huggingface/Qwen2.5-7B-Instruct`, content ID
`e2b474b2efa21f2dbfc6e6c31de53a54f20eea68942e02d34164526078dc4cf5`.
Verify configuration against the existing `runs/provider-comparison/qwen-v01`
archive, JSONL SHA-256
`baf1512634f6a60f74f852ebc3988690555f4af897845dbc930cb81091796dff`.

Preserve exact source state, question, native option IDs, descriptions, order,
candidate membership and numerical effects. The only transport difference is the
already existing provider-specific chat template and generation interface. Do not
alias, rank, reorder, prune or rewrite options. The provider gets only state and
questions; evaluator records, full simulator truth and stored chosen actions stay
outside model input. Record both common logical payload identity and exact
provider-facing messages, rendered prompt, input IDs and token count.

Run a separate preflight with no generation, checking every full input fits, that
chat-template tokenization agrees by both existing code paths, and every native
option ID can fit with EOS within 16 output tokens. Freeze code, protocol, model,
generation settings, fixtures and preflight environment. Run exactly ten calls:
five chronological fixtures, then the same fixtures in reverse order. Candidate
order stays fixed. Seed 1 and four CPU threads match the previous Qwen provider.
GPU ordinal may differ from the old archive and must be recorded.

Preserve every generated token, observed forward input, full-vocabulary logit
artifact and hash. Require greedy argmax, complete consumed prompt, an EOS-terminated
answer, and exact membership of the stripped text in the native option set. An
invalid or non-EOS result is a recorded failure and ends this run immediately;
there is no extraction, fallback, retry or change to the generation budget.

## Evaluation and bounds on conclusions

Recover answers independently from raw generation and logits. Report all ten
planned calls, missing/invalid calls, repeat equality, and immediate effects of
Qwen's chosen action alongside both archived and freshly reproduced Laya choices.
Do not compare Qwen token probabilities with Laya option probabilities.

For boundaries 9/10, compare closure, gap, target contact, obstacle force, success
and horizon under the supplied `advance_target` criterion. For 0/1, report the
chosen surface-gap reduction and pool maximum; “prefer substantial” is not a strict
argmax correctness label. For 87, report first-step effects separately from all
stored hypothetical witness effects. A second-step witness is not a future command
and is not executed. No simulator or live runtime is constructed in this experiment.

The source achieves official goal completion through invalid/ambiguous designated
contacts; larger predicted closure does not establish interaction-valid action.
If Qwen picks stronger immediate effects, that supports readability by this
provider-plus-adapter and motivates a targeted next intervention. It cannot isolate
architecture from training, size or wrapper, establish task-optimal trajectories,
prove a need for VLM planning, or establish visual/real-robot generalization. If
both fail, distinguish format failure from ranking before changing architecture.
