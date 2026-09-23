# Final STOP-clause order: controlled offline intervention

2026-09-23. Declared before new inference. Research branch `research/decision-interface`,
baseline `eddbcde`, with working-source hashes recorded per run. No E0 or execution.

## Intervention and scope

Use all 64 frozen full-effect fixtures from `runs/effect-binding/factorial-v01/`.
Validate the original Laya archive and the Qwen archive at
`runs/provider-comparison/qwen-v01/` against the hashes in the preceding handoff.
For each fixture replace exactly one suffix of the state string:

Original, open last:
`When a STOP comparison is supplied, also require lower opening than STOP for closed, or higher opening than STOP for open.`

Intervention, closed last:
`When a STOP comparison is supplied, also require higher opening than STOP for open, or lower opening than STOP for closed.`

All preceding state text (including the absolute-change rule and requested goal),
question, options, descriptions, effects, order, source metadata and empty history
are byte-identical. This is an instruction embedded in the state string, not a
physical-state change. Retain parent fixture/payload IDs and derive new IDs. Do not
regenerate physical outcomes or modify either evaluator. The frozen presentation
is a sentence projection, not full CDS v0.1.

## Calls and providers

Use the same Laya typed-decisions and Qwen2.5-7B-Instruct bytes, adapters, CUDA/bfloat16
and settings as the archived runs. Laya eleven-option temperature remains
0.10058280825614929. Qwen uses the unchanged native chat template and output-only
system instruction, SDPA, greedy batch-one generation, seed one, maximum 16 new
tokens and explicit GenerationConfig from the existing adapter. No retries,
constrained generation, fallback, rationale request or output-dependent selection.

Run 64 transformed fixtures twice per provider, reversing traversal on repeat two.
Reuse archived original-order calls for the matched contrasts. Additionally run
two unchanged baseline controls twice per provider: init 0 / step 48, true effects,
closed goal, original option order, one native and one anonymous description.
These check reproducibility across sessions and description styles without repeating
the entire accepted archive. Controls precede interventions on repeat one and follow
them on repeat two. Total **264 new calls**, 132 per provider. This is one alternative
ordering; no prompt search. No further inference after results in this protocol.

Verify model/config identity before inference. Record every fixture and complete
tokenized presentation before calls; audit actual consumed tokens. Preserve failures,
raw outputs, Laya option logits/probabilities and Qwen full vocabulary logits (not an
invented option distribution). Keep all source code hashes, model hashes and prompts.
Control mismatch, incomplete calls, clipping or changed settings prevents an
unqualified causal conclusion; report the concrete discrepancy, without replacing
failed observations.

## Scoring and interpretation

Reuse the existing numeric local predicate: >0.25 mm absolute AND >0.25 mm beyond
STOP goal progress, and no measured obstacle violation. For shifted effects report
supplied-fact consistency separately from actual physical utility. Keep contract
flags. No threshold or gate relaxation.

For each matched pair and repeat report choices, identity change, presented effect
bundle, requested-goal correctness and actual utility. Classify selected direction
as closed (`decreases/lower`), open (`increases/higher`), other, or unknown/invalid.
Direction uses the assigned effect bundle, never the action name; retain the raw
categories so a mixed bundle is not mistaken for closing/opening support.

Report separately by provider, native/anonymous, true/shifted, goal and option order.
Primary directional contrast: open-to-closed switches when the final clause moves
from open to closed, versus reverse switches and unchanged/mixed choices. Anonymous
conditions isolate this from native action wording. Count alignment with the final
clause separately from correctness for the unchanged requested goal. Report goal
pairs with both choices correct, and effect-reassignment tracking, for each ordering.
Repeat and unchanged-control comparisons include raw logits, not choices alone.

Strong, repeatable directional reversal across matched contexts implicates final-rule
order dominance on this presentation, especially if closing correctness rises while
opening correctness falls. A few changes or persistent exceptions support only a
partial explanation; unchanged opening bias weakens this specific recency account.
Do not infer an internal attention mechanism or universal model limitation from
this behavioral intervention. It swaps first and last positions simultaneously,
so it isolates clause order, not recency versus suppression of the first clause.

A useful bounded reference still requires the unchanged prior gate: complete,
stable, valid native choices consistent with supplied facts for every goal,
assignment and option order, and actually useful under true effects. A shifted
directional bias or higher pooled score alone cannot qualify a reference. These
are correlated finite contexts, not independent episodes or population rates.
Privileged effects remain offline; State Gap and Effect Gap stay separate.
Formal E0 remains blocked; no new physical fields or interface/controller redesign.
