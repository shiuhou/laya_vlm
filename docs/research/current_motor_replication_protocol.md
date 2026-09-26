# Current motor-interface replication v0.1

## Question and fixed design

Do the historical eleven-option decision findings apply to the currently frozen
local-objective motor interface? This experiment first reproduces unchanged
inputs. It introduces no binary judgments, new wording, candidate changes,
simulator execution, or policy changes.

Source: `runs/privileged-reference/local-objective-task-adapter-episode-01`.
The source `episodes.jsonl` SHA-256 is
`9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`.
Select the first two genuine model boundaries for every observed objective and
the first genuine lookahead boundary, deduplicate, and keep chronological order.
This yields boundaries **0, 1, 9, 10, 87**, with **7, 7, 25, 16, 25** candidates.
There are only two approach and advance examples and one reposition example;
this is a bounded relevance check, not a success-rate benchmark.

Restore criteria insertion order from each saved `option_order`: the recorder
sorts JSON keys, whereas the model consumes the original order. Preserve the
exact saved state, question, candidate labels and criteria text. Require complete
token/marker agreement with the source encoding audit before any inference.
Fingerprint the local checkpoint and verify its configuration and dtype against
the source. Record the source repository/config/artifact lineage and current
GPU/environment; GPU ordinal differences are reported rather than concealed.

Perform **10 calls**, two per boundary: chronological fixture order on repeat 0,
reverse fixture order on repeat 1. Do not reverse candidates. Seed remains 1.
Run a separate no-inference preflight; inference must use its unchanged code,
protocol, fixtures, model and environment. Stop on truncation, invalid output or
consumed-token discrepancy. No inference is run by source/design inspection.

## Competing interpretations

- Historical failures may not apply to the current local-objective interface.
- A supplied local objective and oracle effects may still leave poor immediate
  motor ranking, independently of a high-level planner.
- Any changed answer may instead be an input-order, checkpoint, numerical or
  environment reproducibility failure; first establish unchanged-call identity.

The archive has already been inspected. Boundaries 9 and 10 select `open` although
`y-40mm` predicts larger closure at the same obstacle force, success and horizon.
This is a registered replication, not a blind discovery or held-out experiment.

## Evaluation and inference limits

Recover results directly from raw responses and captured forward logits, never
from cached analysis. Check native option counts, probabilities, logits, choice,
actual input IDs and option markers. Compare both fresh repeats and the archive.
Report exact choice/probability/logit equality separately. If an archived hook is
absent, report logits as unavailable rather than inferring them from rounded
probabilities. All five selected records currently contain archived hook logits.

For each boundary report the full canonical pool and raw immediate effects,
selected effects, source executed outcome and its preview comparison. For
`approach_target`, report surface-gap reduction and its pool maximum; the prompt
says "prefer substantial" and does not impose a strict argmax, so selecting
another substantial improvement is not scored incorrect. For `advance_target`,
report closure and alternatives with greater closure, no smaller gap reduction
or terminal contact, and equal obstacle force, success and control count. This
is an immediate-effect comparison, not proof of long-term optimality, causal
contact validity, or task failure. For `reposition`, retain all witness data and
separate first-action effects from hypothetical two-step net effects. The stored
second action was not an executed commitment, and no witness score is a gold
label for motor choice.

The successful source remains a privileged goal-completion reference. These
calls cannot establish visual competence, interaction-valid manipulation, VLM
necessity, or multi-task generality. A stable poor immediate ranking would earn
a matched current-interface intervention; it would not by itself earn a new
planner or replacement controller.

## Reproduction

Use `python -m embodied_runtime.experiments.current_motor_replication` with
`--preflight RUN_DIRECTORY`, then `--output RUN_DIRECTORY
--preflight-source PREFLIGHT_DIRECTORY`. `--inspect-source` performs source/schema
checks only; `--summarize RUN_DIRECTORY` recomputes the independent raw report.
All outputs are new append-only runs; source evidence is never overwritten.
