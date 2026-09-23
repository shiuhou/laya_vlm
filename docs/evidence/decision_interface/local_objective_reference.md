# Local-objective privileged reference

Date: 2026-09-23. Baseline checkout: `cae7437fd5564fa9cc7a292aab397fe66cb3d4e7`.
Baseline evidence: `runs/privileged-reference/forced-singleton-episode-01/`.

## Preregistered boundary

The authorized change is a deterministic local objective before Laya motor choice.
Original Jev uses model-selected intents; this fixed router is **new task policy**,
not an exact port of Jev intent decisions. It reuses unchanged Jev contracts and
motor-objective semantics. No strategy or translation-only filtering is added.

At each boundary select the first nonempty contract pool in this fixed order:
`advance_target`, `establish_contact`, `approach_target`, `release_contact`,
`reposition`. The first three retain original 0.01 mm progress, -0.01 mm regression,
and 2 mm approach conditions; release uses existing required-contact rules;
reposition requires existing two-step witnesses. All existing collision clauses
remain active. The router sees pool presence, not action utility. It preserves
the complete selected pool in original primitive order, including rotations.
This explicitly performs candidate-policy filtering and remains privileged.

Architecture: real observation/belief -> original one-step previews/contracts ->
original two-step fallback only if the full one-step union is empty -> fixed
objective -> full objective pool -> Laya motor choice or logged forced singleton
-> one primitive through the original executor -> independently measured outcome
-> next observation. No stored second witness is automatically executed.

The flat default and its presentation stay unchanged. Local presentation adds
`Current local objective: <name>.` and narrows the question using the corresponding
Jev motor criterion. Effects, numeric formatting, checkpoint/configuration and
feedback remain fixed. Every model input is audited for clipping and actual
consumed tokens. Objective exclusions are distinct from contract rejections.

## Bounded comparison and acceptance

`objective_reference_check --mode mechanical` checks fresh reset against the flat
initial state, seven initial approach candidates, all 27 preview/executor branches,
and full snapshot restoration without inference. `--mode paired` freezes flat
boundaries 0 and 1, runs flat/local once each (four calls), logs full inputs and
outputs, and never executes any answer. Baseline/model hashes are preserved.

`privileged_reference --condition local_objective` runs fresh init 0 / seed 1,
100-action and 1800-second budgets. It checks baseline model bytes/configuration.
Zero/singleton/multi-option semantics, physical alias guard and witness fallback
are unchanged. First failure stops the phase without tuning or retries. A valid
small-step choice is not a new failure condition. If the first episode succeeds,
perform two further fresh-process episodes; replay every completed execution.
Only official LIBERO success counts; forced continuations never count as model
competence. Do not merge, add strategy, change routing, tune prompts or start E0.

The frozen comparison uses identical states even if the subsequent live paths
diverge. Jev's earlier successful reference used archived model answers with
fresh simulation, not new Jev inference; it does not isolate hierarchy causality.

## Results

Pending the mechanically verified bounded run. Raw artifacts will remain under
`runs/privileged-reference/local-objective-*`; no historical baseline is overwritten.
