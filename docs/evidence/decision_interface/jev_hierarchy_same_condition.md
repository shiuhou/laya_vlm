# Original Jev hierarchy on the flat-Laya task condition

Date: 2026-09-23

This is the controlled architecture comparison requested after the flat-Laya
Privileged Drawer Reference v1 ended at a zero-pool boundary. It runs the
original Jev hierarchy from a fresh simulator reset. It does not load archived
controls, warm-start a trajectory, run Laya, alter contracts, or add lookahead.

## Provenance and method

- comparison repository commit: `1d2476ee3c3d176280dc3ef49d69be049a781ef1`
- original Jev repository commit: `3bdad985b225aeccc39fbe5863c6eea2e81c515a`
- LIBERO repository commit: `8f1084e3132a39270c3a13ebe37270a43ece2a01`
- raw output: `runs/privileged-reference/jev-hierarchy-same-condition-03/`
- archived original answers: `jev-libero/examples/records/top_drawer_seed1/api.jsonl.gz`
- archived-answer SHA-256: `fba0512743b44d2598e859e14756b1be00f50fb4e67cb3e85095d258adcd40e0`

No provider credential was available locally. The fresh original hierarchy
therefore rebuilt every intent, strategy, and motor request online and returned
an archived original Jev answer only after the request passed the comparison
gate. All 30 returned choices were members of the freshly computed option set.
Twenty-nine requests matched exactly. Call 16 differed only in the displayed
`x+10mm` surface-gap reduction, `-1.97` versus archived `-1.96` mm; the raw
geometry difference was about 0.00123 mm and crossed a two-decimal rounding
boundary. This equivalence is recorded explicitly in
`request-numeric-equivalences.jsonl`.

The current task file explicitly declares the legacy default joint-position
measurement that the archived schema omitted. The normalized task semantics,
27 primitives, contracts, collision handling, controller, horizon 8,
lookahead 2, task, init 0, seed 1, assets, and LIBERO success predicate match.
The fresh initial state equals the flat-Laya initial state exactly. Against the
archive, one EEF coordinate differs by `3.20e-14` mm. This is recorded as
numeric equality rather than byte equality.

## Result

The fresh Jev run reached the official LIBERO success predicate after 20
physical decisions and 155 controls. Drawer opening changed from
`151.659012956` to `-1.157187794` mm. All selected preview endpoints had zero
simulator-state error against execution. The fresh action sequence equals the
archived successful action sequence; full action/control drift was at most
`3.27e-12`, state drift at most `5.62e-12`, and final-state drift at most
`1.63e-12`.

The task config does not request per-control `record_features`. The table's
opening, gap, and contact endpoint fields therefore come from the selected
preview endpoint, backed at each boundary by zero prediction/execution state
error. Actual closure and official success come from the fresh execution trace.

| Step | Intent | Strategy | Union → intent → motor | Motor candidates | Choice | Source | Opening mm | Gap mm | Target | Obstacle | Actual closure mm | Success |
|---:|---|---|---|---|---|---|---:|---:|---|---|---:|---|
| 0 | approach_target | no_target_contact__translation | 7 → 7 → 5 | x+3, x+10, x+40, z-40, z-10 | `x+40mm` | one-step | 151.659013 | 64.370219 | false | false | 0.000000 | false |
| 1 | approach_target | no_target_contact__translation | 7 → 7 → 5 | x+10, x+40, z-40, z-10, z-3 | `z-40mm` | one-step | 151.659013 | 41.362754 | false | false | 0.000000 | false |
| 2 | approach_target | no_target_contact__translation | 4 → 4 → 3 | x+10, x+40, z-40 | `x+40mm` | one-step | 151.659013 | 14.804399 | false | false | 0.000000 | false |
| 3 | approach_target | no_target_contact__translation | 5 → 5 → 4 | y-40, y-10, z-40, z-10 | `z-40mm` | one-step | 151.659013 | 2.397207 | false | false | 0.000000 | false |
| 4 | approach_target | no_target_contact__translation | 8 → 6 → 4 | y-40, y-10, y-3, z-10 | `y-40mm` | one-step | 120.713360 | 0.002155 | false | false | 30.945653 | false |
| 5 | establish_contact | palm__translation | 27 → 4 → 1 | z-40 | `z-40mm` | one-step | 113.549953 | 0.000000 | true | false | 7.163407 | false |
| 6 | advance_target | no_target_contact__translation | 25 → 23 → 10 | x-40, x-10, x-3, x+3, x+10, x+40, y-40, y-10, z+3, z+40 | `y-40mm` | one-step | 78.875394 | 0.000971 | false | false | 34.674559 | false |
| 7 | advance_target | no_target_contact__translation | 25 → 25 → 10 | x-40, x-10, x-3, x+3, x+10, x+40, y-10, z+3, z+10, z+40 | `x+40mm` | one-step | 71.509871 | 0.265832 | false | false | 7.365523 | false |
| 8 | advance_target | no_target_contact__translation | 27 → 27 → 15 | x-40, x-10, x-3, x+3, x+10, y-40, y-10, y-3, y+3, y+10, y+40, z-3, z+3, z+10, z+40 | `y-40mm` | one-step | 40.976169 | 0.005111 | false | false | 30.533702 | false |
| 9 | advance_target | no_target_contact__translation | 23 → 23 → 12 | x-40, x-10, x-3, x+3, x+10, y-3, y+3, y+10, y+40, z+3, z+10, z+40 | `y-3mm` | one-step | 35.466780 | 0.004075 | false | false | 5.509389 | false |
| 10 | advance_target | no_target_contact__translation | 20 → 20 → 12 | x-40, x-10, x-3, x+3, x+10, y-3, y+3, y+10, y+40, z+3, z+10, z+40 | `y-3mm` | one-step | 32.828974 | 0.000065 | false | false | 2.637806 | false |
| 11 | advance_target | no_target_contact__translation | 18 → 18 → 11 | x-40, x-10, x-3, x+3, x+10, y+3, y+10, y+40, z+3, z+10, z+40 | `y+3mm` | one-step | 32.631258 | 2.088188 | false | false | 0.197716 | false |
| 12 | advance_target | no_target_contact__translation | 5 → 5 → 1 | y-3 | `y-3mm` | one-step | 32.432647 | 0.000036 | false | false | 0.198611 | false |
| 13 | advance_target | no_target_contact__translation | 18 → 18 → 11 | x-40, x-10, x-3, x+3, x+10, y+3, y+10, y+40, z+3, z+10, z+40 | `x-10mm` | one-step | 32.016960 | 0.331882 | false | false | 0.415687 | false |
| 14 | advance_target | no_target_contact__translation | 6 → 6 → 2 | x-40, x+40 | `x+40mm` | one-step | 30.751297 | 1.193965 | false | false | 1.265663 | false |
| 15 | advance_target | no_target_contact__translation | 12 → 12 → 6 | x-40, x-10, x-3, z+3, z+10, z+40 | `z+3mm` | one-step | 30.123905 | 0.303685 | false | false | 0.627392 | false |
| 16 | advance_target | no_target_contact__translation | 8 → 8 → 2 | y-10, z-3 | `y-10mm` | one-step | 24.868172 | 0.000000 | false | false | 5.255732 | false |
| 17 | advance_target | no_target_contact__translation | 18 → 18 → 11 | x-40, x-10, x-3, x+40, y-10, y-3, y+3, y+10, z+3, z+10, z+40 | `x+40mm` | one-step | 13.873026 | 0.023268 | false | false | 10.995146 | false |
| 18 | advance_target | no_target_contact__translation | 25 → 25 → 15 | x-40, x-10, x-3, x+3, x+10, x+40, y-3, y+3, y+10, y+40, z-10, z-3, z+3, z+10, z+40 | `z-10mm` | one-step | 10.436152 | 0.035707 | false | false | 3.436874 | false |
| 19 | advance_target | no_target_contact__translation | 26 → 26 → 17 | x-40, x-10, x-3, x+3, x+10, x+40, y-40, y-10, y-3, y+3, y+10, y+40, z-10, z-3, z+3, z+10, z+40 | `y-40mm` | one-step | -1.157188 | 3.258886 | false | false | 11.593340 | true |

## Architecture comparison

At the identical initial state, Jev selected intent `approach_target`, strategy
`no_target_contact__translation`, reduced the seven contract-valid primitives
to five motor candidates, and chose `x+40mm`. Flat Laya saw the same five
translations plus two rotations and chose `x+3mm`. Both `x+40mm` and `x+3mm`
were valid members of Jev's motor pool, so strategy filtering alone does not
explain the first divergence. The first cross-axis divergence followed at
decision 1: Jev chose `z-40mm`, while flat Laya chose another `x+3mm` from its
own new state. The consequence became unambiguous at Jev decision 4, when
`y-40mm` closed 30.946 mm; this single action exceeded flat Laya's total
15.173 mm closure.

Jev never visited the flat-Laya terminal state. The closest Jev endpoint by
pose was still 82.290 mm away with 61.445 degrees rotation difference and had
already reduced opening to 10.436 mm. The closest by opening was Jev step 0,
still 15.173 mm away in drawer opening. The flat-Laya zero-pool geometry was
therefore completely avoided.

This run supports the whole original hierarchy plus its original answers as a
successful reference. It does not isolate hierarchy from model ranking. The
operation most consistent with the early difference is the
`approach_target`-conditioned motor judgment: it ranks substantial surface-gap
reduction inside a translation family, leading to large `x/z` approach moves.
Because both first actions survived the hierarchy filters, the evidence does
not establish candidate-pool reduction alone as the cause.

The smallest justified next architecture change is therefore an explicit
local-objective-conditioned motor boundary for Laya, initially only the
`approach_target` objective with its translation family and gap-reduction
criterion. Existing contracts, previews, lookahead, executor, actions, CDS,
and thresholds should remain fixed. This is a proposed next change, not part of
this comparison, and the full Jev hierarchy has not been ported.

## Raw artifact hashes

- `api.jsonl`: `8fe14128941e055b538b75b011ab2c920cc92cfa3e41c7d6d2ec34ef1e598099`
- `predictions.jsonl`: `b0e0801ee619147bc5d958833b8a16c5f5d3e294033d958771b8d21941f2d8a7`
- `trace.jsonl`: `ea9cbad94b7ace9bfd2e4e20cda0d48410e455d90a2312eda682d4051110df73`
- `sim_trajectory.npz`: `e15a7976295410f94a80deb5c67155d5ea3e1167cff20e31df47100d6e9a86b6`
- `summary.json`: `17e3be0a826e46684d01cf9bfa22031b5276eebcac0335b683014176f50a32d5`
- `architecture-comparison.json`: `9f3f4e1016dc194e8ad74c217abbbb5eb5b14ef77c96cf39830188b624cc30d3`
