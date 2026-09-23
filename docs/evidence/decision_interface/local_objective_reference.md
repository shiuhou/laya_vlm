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

Implementation commits are `056034a`, `d3becbb`, and compact-presentation commit
`9372329`. The full suite passed with 434 tests; ruff, compileall and
`git diff --check` passed. Mechanical preflight
reproduced the flat initial state, retained all seven `approach_target` actions,
matched all 27 preview/execution branches and restored the simulator/controller
snapshot. Raw SHA-256:

- mechanical: `0afabe86ea3242543310afa44ca9574e66e8eb6511add80b7d3aa1068b78201e`;
- frozen paired inputs: `eb690a8fe9d4b4ec373d0da151b156d712399df0caddd979a81a42b6c1cc7bfa`;
- frozen paired results: `6211be259e8f8b2130fcf4d2072ad4d60b1c23e4f08d95c35bb642376f09b03f`;
- live episode: `662913b8eb96b6415ae0e72630dd6d6c48449cbfffc76b99d93632eae6b56df4`;
- replay: `8978a8a2c7cdc9f990a52f58c70602a50a7dc018b591799744fda03c53be081b`.

### Frozen flat comparison

At flat boundary 0, the unchanged flat input reproduced `x+3mm`. The same state,
effects, model and seven candidates with `approach_target` added selected
`x+40mm` (probability 0.2101 versus 0.1803 for flat). At flat boundary 1, both
conditions selected `x+3mm`; the objective condition therefore changed the
initial ranking but did not consistently prefer larger approach effects.

The live path selected `x+40mm` at steps 0 and 1. Step 1 was already a different
physical state from flat boundary 1. Its predictions favored `z-40mm` for gap
reduction (23.01 mm) over the selected `x+40mm` (15.70 mm), showing that the
model did not reliably follow the stated local effect criterion.

### Closed-loop result and first failure

The first fresh episode did **not** complete the task. It executed 87 primitives
and 696 controls: 81 genuine Laya choices and six forced singletons. Opening
changed from `151.659012956` to `55.491175169` mm, a net closure of
`96.167837786` mm. Every selected prediction matched execution with zero state
error. Control replay passed all 784 checked boundaries with zero error.

The first failure was boundary 87, before Laya or execution. The one-step union
was empty; unchanged two-step processing produced 25 `reposition` candidates.
The complete witness presentation was 2,004 characters and failed the existing
Laya audit with `truncated=true` (`max_len=1024`, `head_max_len=256`). No option
was removed and no model response or action followed. This is a
**candidate-consumption/interface-capacity failure**, not an objective-routing,
zero-pool, contract-coverage or physical-execution failure. It also does not
establish that the selected objective architecture would eventually succeed.
Since the first run failed, the two reproduction runs were not started.

### Lossless compact witness presentation and fresh episode

The authorized capacity repair changes presentation only. Witness effect rows
use numbered positions bound to the unchanged canonical action-option order;
task/state/feedback/schema and common invariant fields appear once. No action,
effect field or physically distinct candidate is ranked, pruned, merged or
reordered. Full-precision predictions, witnesses, contracts and rejection records
remain unchanged in `reference_preview`; model-visible numeric precision is the
same as before. One-step and flat presentations remain byte-identical.

The offline boundary-87 replay reconstructed the same closed-gripper snapshot and
all 25 `reposition` candidates in their stored order. The compact state used 768
tokens against an 849-token state budget; the complete input used 943 of 1,024
tokens. State, heading and options all reported `truncated=false`; no model
inference or execution occurred. Raw audit hashes:

- offline audit records: `6fece7e2c82c49084d099de599d1aa317cc4bf83459a688d5b99ab5c4e6691d9`;
- compact boundary audit: `da4ce22369d66bbd5f8465c76ecb72856e69e8d261ddcdc5e85d8f9aec478588`.

The fresh episode reproduced the original 87-action prefix exactly. At boundary
87 all 25 candidates reached Laya. The forward-hook record matched the audited
943-token input. Laya selected `open`; only `open` executed. Predicted and actual
effects matched exactly: closure `0.009825927` mm, gap reduction
`-5.589761827` mm, no target contact, no obstacle force and no success. Its stored
`z-10mm` witness predicted two-step net closure `0.515421708` mm, but was not
executed automatically. The next real state produced a singleton `z-10mm`, which
was executed under the existing forced-singleton rule before replanning.

The episode reached the fixed 100-action budget without official success. It made
91 genuine Laya choices, nine forced-singleton continuations and one executed
lookahead recovery. Opening changed from `151.659012956` to `40.171227260` mm,
for `111.487785695` mm net closure. All 100 selected previews matched execution
with zero state/effect error. There was no truncation, zero-pool, invalid decision,
fallback or physical mismatch. The first new failure boundary is therefore the
pre-registered action budget, not candidate capacity. No post-budget candidate
pool was built, so this run does not establish whether continued execution would
succeed or encounter another decision boundary. Under the stop rule, no second or
third fresh process and no replay run were started.

Raw compact-episode hashes:

- episode records: `079e01ba1f71b31fbc972a2dede7e7f0c2d9b7537ea39b98313a1147dc52f2ba`;
- derived evidence: `3e69f63ee1d342eaeb7c6744cc81c61b075e46cadf14577bf01b6964aabaafd7`;
- manifest: `f6d7502d4197dcf7d609a58c5f08c3f92ceb0f47a2dc1c8b88698cbc9422ba43`.

Continuation after the repaired boundary:

```text
087 reposition      25 lookahead Laya   open               0.009826 55.481349  8.036585 false false
088 advance_target   1 one_step  forced z-10mm             0.505596 54.975753  5.529505 false false
089 advance_target   7 one_step  Laya   rotate_z-10deg     2.106161 52.869592 15.744538 false false
090 advance_target   1 one_step  forced rotate_x+10deg     2.570606 50.298986 26.309501 false false
091 advance_target  22 one_step  Laya   close              0.200340 50.098645 26.331676 false false
092 advance_target   8 one_step  Laya   rotate_z+10deg     5.438790 44.659855 27.422114 false false
093 advance_target  24 one_step  Laya   close              2.231118 42.428736 28.174671 false false
094 advance_target  27 one_step  Laya   close              0.112106 42.316631 27.997772 false false
095 advance_target  14 one_step  Laya   x+3mm              0.034926 42.281705 27.381745 false false
096 advance_target  27 one_step  Laya   close              0.116397 42.165308 27.464329 false false
097 advance_target  13 one_step  Laya   rotate_y+10deg     0.922258 41.243050 32.646015 false false
098 advance_target   3 one_step  Laya   rotate_z-10deg     0.435816 40.807234 39.159171 false false
099 advance_target   1 one_step  forced z-40mm             0.636007 40.171227 38.348289 false false
```

### Original capacity-failed episode trace

Columns are step, objective, candidate count, choice source, primitive, actual
closure, remaining opening, surface gap, target contact and official success.

```text
000 approach_target  7 Laya   x+40mm             0.000000 151.659013 64.370219 false false
001 approach_target  7 Laya   x+40mm             0.000000 151.659013 48.672527 false false
002 approach_target  3 Laya   rotate_x+10deg     0.000000 151.659013 40.823411 false false
003 approach_target  5 Laya   rotate_x+10deg     0.000000 151.659013 31.731538 false false
004 approach_target  5 Laya   rotate_x+10deg     0.000000 151.659013 25.316015 false false
005 approach_target  6 Laya   rotate_x+10deg     0.000000 151.659013 20.931259 false false
006 approach_target  6 Laya   rotate_x+10deg     0.000000 151.659013  5.796067 false false
007 approach_target  2 Laya   y+40mm             0.000000 151.659013  2.724450 false false
008 advance_target   1 forced rotate_x+10deg     2.094755 149.564258  0.008362 false false
009 advance_target  25 Laya   open               1.755743 147.808514  0.000000 true  false
010 advance_target  16 Laya   open               0.056385 147.752129  0.059130 false false
011 advance_target   9 Laya   rotate_y+10deg     1.274636 146.477493  0.820900 false false
012 advance_target  15 Laya   close              0.663177 145.814316  0.014155 false false
013 advance_target  13 Laya   close              0.057538 145.756778  0.205316 false false
014 advance_target   8 Laya   y-3mm              1.789947 143.966831  0.000000 false false
015 advance_target  23 Laya   close              0.137441 143.829390  0.157472 false false
016 advance_target   8 Laya   y-3mm              1.815767 142.013623  0.000000 false false
017 advance_target  23 Laya   open               0.122132 141.891491  0.132237 false false
018 advance_target   8 Laya   x-40mm             1.007770 140.883722 28.054711 false false
019 approach_target  5 Laya   x+40mm             0.002120 140.881602  2.886378 false false
020 advance_target  12 Laya   open               0.150028 140.731574  0.226255 false false
021 advance_target  25 Laya   close              0.017560 140.714014  0.777741 false false
022 advance_target   8 Laya   rotate_x+10deg     0.149343 140.564671  0.000000 true  false
023 advance_target  18 Laya   x+40mm             1.080623 139.484047  0.106215 false false
024 advance_target  25 Laya   open               2.317899 137.166148  0.022119 false false
025 advance_target   9 Laya   rotate_y+10deg     0.552036 136.614112  0.512223 false false
026 advance_target  16 Laya   open               0.535168 136.078944  0.000405 false false
027 advance_target  10 Laya   rotate_y+10deg     0.481587 135.597358  1.466612 false false
028 advance_target   9 Laya   rotate_y-10deg     0.071358 135.525999  0.107461 false false
029 advance_target   6 Laya   rotate_y+10deg     0.297230 135.228770  2.830019 false false
030 advance_target   6 Laya   z-3mm              0.420156 134.808613  0.000000 true  false
031 advance_target  12 Laya   rotate_y+10deg     0.481586 134.327028  2.864222 false false
032 advance_target   5 Laya   rotate_z-10deg     0.351570 133.975457  1.645494 false false
033 advance_target   1 forced rotate_x+10deg     1.435514 132.539943  0.036315 false false
034 advance_target  13 Laya   rotate_x-10deg     7.297644 125.242299 11.781635 false false
035 advance_target  26 Laya   close              0.015849 125.226450 15.529799 false false
036 advance_target   1 forced z-40mm             1.133295 124.093155  0.000000 true  false
037 advance_target  18 Laya   close              0.474015 123.619140  0.000758 false false
038 advance_target  23 Laya   open               0.175049 123.444090  0.059800 false false
039 advance_target  12 Laya   rotate_x-10deg     4.339857 119.104234 13.787882 false false
040 advance_target   1 forced z-40mm             3.208849 115.895384  1.724657 false false
041 advance_target   8 Laya   z+40mm             0.144185 115.751199 28.425190 false false
042 advance_target   1 forced z-40mm             0.715826 115.035374  3.427830 false false
043 advance_target  16 Laya   open               0.251258 114.784116  3.620087 false false
044 advance_target   5 Laya   rotate_x-10deg     3.868233 110.915883 15.195558 false false
045 advance_target  27 Laya   close              0.017528 110.898355 18.284818 false false
046 advance_target   1 forced z-40mm             0.386204 110.512151  7.613898 false false
047 advance_target   9 Laya   x+40mm             0.726908 109.785243 10.694436 false false
048 advance_target  25 Laya   close              2.608612 107.176632  9.991159 false false
049 advance_target   6 Laya   rotate_x-10deg     0.347420 106.829211 18.248958 false false
050 advance_target   2 Laya   y-40mm             7.941563  98.887648  0.004473 false false
051 advance_target  27 Laya   close              2.026242  96.861406  0.171157 false false
052 advance_target  27 Laya   close              0.011054  96.850352  0.122480 false false
053 advance_target  14 Laya   rotate_x+10deg     2.922596  93.927757  0.000991 false false
054 advance_target  26 Laya   close              2.706057  91.221699  0.000000 true  false
055 advance_target  25 Laya   close              0.271004  90.950695  0.000608 false false
056 advance_target  24 Laya   close              0.041655  90.909040  0.007521 false false
057 advance_target  15 Laya   close              0.017197  90.891843  0.000139 false false
058 advance_target  15 Laya   close              0.027703  90.864140  0.000151 false false
059 advance_target  15 Laya   close              0.022872  90.841268  0.000227 false false
060 advance_target  15 Laya   close              0.018890  90.822378  0.000396 false false
061 advance_target  15 Laya   close              0.014486  90.807892  0.000226 false false
062 advance_target  13 Laya   open               0.010095  90.797797  0.000675 false false
063 advance_target  12 Laya   rotate_z+10deg     0.286468  90.511329  0.040104 false false
064 advance_target  27 Laya   close              3.247594  87.263735  0.015452 false false
065 advance_target  25 Laya   close              0.266061  86.997673  0.450195 false false
066 advance_target   8 Laya   rotate_x+10deg     3.683094  83.314579  1.114423 false false
067 advance_target  17 Laya   close              0.024070  83.290509  1.166573 false false
068 advance_target   7 Laya   rotate_x-10deg     5.156049  78.134460 13.082952 false false
069 advance_target  26 Laya   close              0.012550  78.121909 15.815273 false false
070 advance_target   2 Laya   y-40mm             9.121075  69.000834  0.022256 false false
071 advance_target  26 Laya   close              2.212885  66.787949  0.020329 false false
072 advance_target  24 Laya   close              0.165070  66.622879  0.173337 false false
073 advance_target   9 Laya   x-40mm             3.371501  63.251379  0.994061 false false
074 advance_target  25 Laya   close              0.049328  63.202050  4.368780 false false
075 advance_target   4 Laya   rotate_x+10deg     1.886564  61.315487  0.000000 true  false
076 advance_target  24 Laya   open               1.381866  59.933621  0.000000 true  false
077 advance_target  14 Laya   open               0.121951  59.811670  0.000040 false false
078 advance_target  20 Laya   close              0.051630  59.760040  0.000046 false false
079 advance_target  14 Laya   close              0.027119  59.732921  0.000074 false false
080 advance_target  14 Laya   close              0.018190  59.714731  0.000280 false false
081 advance_target  14 Laya   open               0.012926  59.701805  0.000324 false false
082 advance_target  14 Laya   open               0.010295  59.691510  0.000394 false false
083 advance_target  11 Laya   rotate_y+10deg     0.452583  59.238927  3.830195 false false
084 advance_target   7 Laya   rotate_x+10deg     0.371982  58.866945  0.000000 true  false
085 advance_target  17 Laya   close              0.094769  58.772176  0.000000 true  false
086 advance_target  11 Laya   rotate_z-10deg     3.281001  55.491175  2.446823 false false
```

Raw artifacts remain under `runs/privileged-reference/local-objective-*`; no
historical baseline was overwritten. Without a new architecture decision, do
not add strategy, truncate/top-k the reposition pool, change the prompt or model
limits, alter routing/contracts/thresholds, deepen lookahead, or begin E0.
