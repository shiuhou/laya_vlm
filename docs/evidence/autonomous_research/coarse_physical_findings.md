# Sensor-driven coarse approach and semantic failure boundary

These results are limited to top_drawer, benchmark init 0, seed 1. The two
20-action arms use revision `a1c76d4764ce19ca25ea68042ceb4aebbafe2df8`;
the separately declared 40-action boundary experiment uses
`b72fcdc494522ea49cb7fd7d9f0b75f2789de49f`.

The decision path is RGB-only LocateAnything POINT, strict EOS/single-point
validation, fresh containing-pixel-center depth projection, the existing
deterministic distance rule, and unchanged AtomicExecutor. There are seven
canonical candidates (six translations and STOP), no Laya motor calls and no
physics-preview selection. Covariance, identity confidence, contact, holding and
velocity remain unknown. This opt-in diagnostic bypasses probabilistic fusion.
Oracle contact monitoring can abort after an atomic action; it cannot select or
correct actions. Therefore this is not an oracle-free safety result.

## Matched fresh physical comparison

| Measurement | Geometric rule | Active hold |
|---|---:|---:|
| Executed primitives / controls | 20 / 160 | 20 / 160 |
| Simulated duration | 8 s | 8 s |
| TCP to designated handle center | 227.258 → 88.945 mm | 227.258 → 227.272 mm |
| Nearest gripper/handle surface gap | 167.131 → 43.345 mm | 167.131 → 166.913 mm |
| Robot contact rows / execution violations | 0 / 0 | 0 / 0 |
| Post-run ray designated-handle membership | 21/21 | 21/21 |
| Full replay maximum state error | 0 | 0 |
| Drawer opening | 151.659 mm unchanged | 151.659 mm unchanged |
| Official task success | false | false |

The matched progress advantage is 138.327 mm. The rule executes 17 FWD and 3 DOWN
actions. A single temporary target-point shift is 3.842 mm. All 21 recommendations
can be reproduced with the original point and recorded proprioception; repeated
grounding is not shown necessary. These are one fresh matched pair, not multiple
initial-state generalization or intended manipulation.

## First semantic failure versus terminal format failure

The next experiment is a fresh reset with a prospective 40-action ceiling. Its
first 20 actions, 160 controls and 21 full model inputs/outputs reproduce the
earlier rule episode exactly. It executes 25 actions / 200 controls before the
existing strict parser stops at boundary 25. No archived-control warm start.

| Boundary (before action) | Capture | POINT | Evaluator identity | Action |
|---|---:|---|---|---|
| 20 | 21 | (158,185), completed | top handle | DOWN |
| 21 | 22 | (84,185), completed | drawer interior/body | RIGHT |
| 22 | 23 | (84,185), completed | drawer interior/body | RIGHT |
| 23 | 24 | (84,192), completed | drawer interior/body | RIGHT |
| 24 | 25 | (84,185), completed | drawer interior/body | RIGHT |
| 25 | 26 | malformed, no EOS | unknown | none |

Boundary 21 is the first observed wrong referent: 74 pixels / 154.331 mm from the
previous point. Independent visual review and separate oracle rays agree. The
target remains visible; its 21-by-21 RGB patch is byte-identical to boundary 20,
including at boundary 25. This rules out complete target occlusion for this
failure, but does not isolate the model's internal cause.

The four RIGHT actions improve true handle-center distance while increasing the
nearest gripper/handle gap from 34.673 to 38.098 mm. Center-distance progress alone
therefore hides the semantic error. Holding the previous point would change the
recorded recommendations to FWD; that offline counterfactual is not a physically
executed continuation or proof it would succeed.

Boundary 25 emits 258 tokens: a point prefix followed by 39 zero-height boxes,
without terminal EOS. Raw output is retained in full; no prefix salvage, retry or
subsequent action. It is not established that the earlier wrong referent caused
this later format failure. All 200 controls replay with zero state error, with
zero contact rows or executor violations. Drawer success remains false.

## Next falsifiers and scope

1. Replay identical RGB frames in fresh model processes and changed call order.
   A reproduced error supports frame-specific grounding failure over accumulated
   conversation/KV history; source code already resets per-call generation state.
2. Test frozen default optical flow against frozen pixels under fixed image
   translation and occlusion controls. Retrospective static-scene continuity is
   insufficient evidence of moving-target tracking, calibrated uncertainty or
   safe recovery. Do not feed oracle identities into either method.

The generic runtime, model configuration, native executor and historical policies
are unchanged. No high-level planner or live tracking recovery is earned yet.

## Evidence

All paths below are under `runs/autonomous-research/` and preserve prior results:

- `coarse-point-rule-01/`, `coarse-point-hold-01/`: raw observations, actual model
  inputs/output tokens, control traces, trajectories and `replay-check.json`.
- `coarse-point-comparison-01.json`: same-condition matched comparison.
- `coarse-point-rule-01/independent-paired-comparison.json` and
  `independent-paired-progress.png`: independent numerical/visual review.
- `coarse-point-rule-grounding-audit-01.json`,
  `coarse-point-hold-grounding-audit-01.json`: evaluator-only pixel ray labels.
- `coarse-point-boundary-01/`: full failed episode, independent audit script,
  first-prefix comparison, visual review, contact sheet and exact replay.
- `coarse-point-boundary-grounding-audit-01.json`: 21 designated-handle hits,
  4 other-geometry hits, 1 unknown malformed observation.
- `coarse-point-temporal-inspection-01/`: RGB comparison, exact CPU inspection
  script and exploratory correspondence results. Not a preregistered tracker test.

Ray labels share the source camera calibration and pixel convention; they are
not an independent calibration validation. Restored-state ray evaluation is
distinct from full executed-control replay, which was also performed.
