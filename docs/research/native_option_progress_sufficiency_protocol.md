# Native option progress-value duplication sufficiency v0.1

Registered before inference, 2026-09-27. Exact code/protocol/tests must be committed
before recorded CPU preflight and every model call. This uses the sole earlier
tokenizer-only design check and the reviewed frozen proposal. This follows the completed B/W/A/W+A diagnostics, whose exact
supplied prefixes did not repair weak advance decisions. It changes the location
and repetition of already supplied action-specific task-progress values within
the existing native typed-choice interface. No runtime or model changes are
proposed, and no model calls have been made on these inputs at registration.

## The question and exact proposed intervention

Is placing each existing printed progress value directly in its corresponding
native choice description sufficient to improve the frozen motor decisions?
The hypothesis is about the total effect of local value duplication, not an
isolated proof of semantic binding. Current native `[MASK]` markers precede bare
action IDs with empty criterion descriptions; all numerical outcomes occur later
in a state table. W/A supplied prose while leaving this relationship unchanged.

The sole proposed arm P uses the **original baseline B state verbatim**, without
W or A. Leave question type, instructions, candidates, admission, order, IDs,
mapping, entire state, effect table, history and provenance unchanged. Replace
each empty action criterion with exactly this string, with no trailing period:

```
<field>=<verbatim printed number from that action's existing effect row>
```

Use `gap_reduction_mm` for the visible `approach_target` phase and `closure_mm`
for the visible `advance_target` phase, matching the existing objective's named
progress metric. Determine phase from the original state text, not evaluator
metadata. Extract each number as a string from that same model-visible table;
do not round, recalculate, normalize, rank or inspect hidden predictions.

Concrete source examples:

```
x+40mm: gap_reduction_mm=29.11
open: closure_mm=0.056
close: closure_mm=0.057
y-40mm: closure_mm=31.888
```

Here the native renderer supplies the action ID and colon; the authored criterion
is only `gap_reduction_mm=29.11`, `closure_mm=0.056`, etc. Field names and printed
numbers already occur in the unchanged table. Copy every admitted action's value
by the same rule, retaining signed strings such as `-0.00` when present. No action
wins by construction, no singleton or subset is created, and no goal label,
ranking, confidence, new physical observation or predicted effect is supplied.
The objective-to-field routing remains the already privileged local objective;
this is not Laya deciding which objective matters.

## One design check and fixed budgets

Source is the same archived privileged drawer episode, SHA-256
`9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`.
One fixed grammar was tokenized on original steps 0, 1, 9, 10 using the frozen
local tokenizer and unchanged 1,024 total / 256 heading-option token limits.
No wording alternatives or inference were used to choose this grammar.

| Step | Native heading tokens | Raw option tokens including markers | Largest option tokens | Complete full sequence | Exact native preservation |
| --- | --- | --- | --- | --- | --- |
| 0 | 24 | 109 | 17 | 442 | yes |
| 1 | 24 | 109 | 17 | 476 | yes |
| 9 | 30 | 337 | 16 | 1,134 | no: options clipped |
| 10 | 30 | 208 | 15 | 781 | yes |

Native `build_sequence` clips each option after 48 text tokens and also clips
options if their aggregate budget would leave fewer than 16 heading tokens.
Step 9's effective output is only 1,022 tokens, but its criteria are clipped.
A total-length-only check would miss this failure. Prospectively exclude step 9;
never submit that shortened builder output. Steps 0, 1, 10 preserve every raw
heading, option and state token under direct full-sequence reconstruction.
Do not shorten descriptions, change budget, drop candidates, alter effects,
replace the state or vary wording in response to this exclusion.

The design artifact and exact script are preserved under
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`:

- `option-progress-binding-design-01.json`, SHA-256
  `272dc7c7cf67136f5fa740884560f3327c8a27dd5518b2c6341ac92c32253dc4`.
- `option-progress-binding-design-01.py`; its SHA-256 is recorded inside the JSON.

The artifact contains unchanged raw states, exact proposed questions, copied
printed values, original source/payload identity, all raw/consumed token IDs,
markers, native truncation flags, frozen tokenizer config and code identity.
It records zero inference calls. The root's separate full-row relocation budget
check already showed why complete six-column criteria cannot fit advance states;
this proposal tests only local duplication of the existing task-progress field.

## Registered minimal run and inference boundary

Commit executable construction/audits/tests and this protocol before a fresh
recorded CPU preflight with exact original source and
archived B/W/A identity gates. The old controls have exactly reproduced source
choices, probabilities and raw logits and opposite-order repeats. Require the
same checkpoint, native temperatures, bfloat16, seed 1, GPU 0 and environment;
otherwise stop without substituting a control design or changing settings.

Exactly **six calls** are registered: P on steps **0, 1, 10, 10, 1, 0**.
No fresh B calls are proposed after exact archive identity and native audit
checks. No W/A is stacked into P. Candidate order stays fixed. Require independent
raw/native token reconstruction and all actual hook IDs/markers to match preflight.
Stop on truncation, invalid response, identity mismatch or infrastructure failure;
retain the failure and missing calls without retries. No simulator/live policy
execution follows this proposal. The parent research agent reviewed and authorized this exact proposal before
implementation. Raw preflight and run roots are `native-option-progress-preflight-01`
and `native-option-progress-run-01` under the raw directory above. The runner
requires every payload and native audit to equal the sole CPU design artifact.
The [joint protocol](joint_interface_sufficiency_protocol.md) fixes the archived
control hashes; its read-only archive gate is reused unchanged. Use checkpoint
content ID `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`,
local offline files, no new model download, and independent raw actual-input
audit after calls. No new control calls, parameter changes or simulator execution
are part of this protocol.

## Outcomes and competing explanations

Compare P to archived B on the same source states and report W/A/W+A as context.
Report native choices/distributions/logits and source immediate effects after
choice. Use approach gap reduction without inventing an argmax correctness label;
use advance closure plus matched no-worse-field alternatives. Success requires
improved advance progress without approach loss relative to B. Report matched
stronger alternatives: a tiny open-to-close numerical increase while strong
no-worse-field alternatives remain does not count as repairing the weak choice.
A result confined
to one state remains a result confined to that state. Repeats are repeatability
checks, not more independent observations; no significance testing is warranted.

A positive result would establish narrow sufficiency of this local duplication
for these inspected inputs, potentially earning an independently registered-state
test. It would be compatible with easier candidate-to-value association, greater
numerical salience, proximity to the scored marker, a familiar criterion format,
objective-specific emphasis, or changed token positions. It cannot isolate those
mechanisms or demonstrate correct semantic recognition. Duplicating one metric
also emphasizes it relative to other unchanged fields, so improvement need not
be a pure spatial-binding effect. The full task instruction and all force/contact/
success fields remain present, but attention to them is not guaranteed.

A negative result would reject only this precise local duplication sufficiency.
It would not show that Laya correctly bound the numbers and then failed ranking;
number recognition, field interpretation, association and ranking could still
fail separately. It would not imply that all native criteria are ineffective.
Both outcomes remain supplied, privileged diagnostics with no new execution,
secure-grasp certificate, verified designated-handle interaction, acquired visual
understanding or general minimal-interface claim. No numeric-format sweep,
more elaborate criterion prose or automatic architecture change follows.

After this result, stop micro-variants on these inspected states. The next research
question must address an orthogonal physical or representation uncertainty, not
further criterion or prefix refinement on this same slice. Report the result
and recommendation to the parent before any additional experiment.
