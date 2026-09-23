> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Stage 4 — reference-quality pilot handoff

2026-09-23. Start: clean `0141a70`. **No formal E0/E1, freeze tag, threshold
loosening, new model, tracking integration or dependency update.**

**Recommendation: do not freeze E0 as a useful-decision-sufficiency benchmark yet.**
The common geometric referent and multi-init collection now work, but the current
no-effect oracle-conditioned Laya has not demonstrated useful local task decisions.
State matching alone cannot fix an unvalidated reference policy/interface.

## Repository and environment

- `3984a07`: bounded collection/evaluator, first referent and tests.
- `87f5163`: corrected first-hit camera-ray oracle and pixel-center convention.
- The commit containing this handoff also hardens raw multi-init summary validation;
  `git rev-parse HEAD` identifies the exact final revision.
- Final accepted collection/replay ran from **clean `87f5163`**. Multi-init audit
  ran during initial development; its manifest preserves dirty status and source
  hashes. No raw records were overwritten.
- Python 3.10.21; NumPy 1.26.4; MuJoCo 3.5.0; robosuite 1.4.1; torch 2.2.0;
  CUDA 12.1; transformers 4.57.3; laya 0.3.4; pytest 9.1.1; ruff 0.15.22.
- Real inference: RTX 4090, Laya bfloat16, deterministic algorithms disabled.
  Repeated-input stability is measured at returned API precision, not guaranteed.
- Jev-LIBERO `3bdad985b225aeccc39fbe5863c6eea2e81c515a` and LIBERO
  `8f1084e3132a39270c3a13ebe37270a43ece2a01` remain clean and unchanged.
- Local content IDs, not asserted upstream revision names:
  LocateAnything `4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`;
  Laya `9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.

## What changed

| File | Purpose |
|---|---|
| `experiments/target_referent.py` | Pure sensor centroid, separate privileged mesh-ray reference, membership diagnostics, raw reconstruction audit |
| `experiments/reference_quality.py` | Independent full-snapshot 11-token counterfactuals, STOP baseline, predeclared local-utility rubric, raw-derived report |
| `experiments/collect_pairs.py` | Bounded reference mode, actual init ID override, preserved raw old quantities, paired new referent; legacy path retained |
| `experiments/audit_initial_states.py` | Fixed-control transfer over three benchmark resets, full physical identities, phase/outcome reconstruction without trusting cached summaries |
| `tests/test_target_referent.py`, `test_reference_quality.py`, `test_initial_state_audit.py` | Geometry/privilege/restore/integrity/regression coverage; existing tests not weakened |
| README/current-state/research/architecture/vision docs | Current evidence, explicit three-stage review roadmap; historical handoffs unchanged |

Paths above are relative to `embodied_runtime/` except tests/docs. No core temporal
equations, deployment candidate thresholds, executor commands or Laya weights changed.

## Common target referent

**Referent v0.2:** the pixel-weighted world-space centroid of the **first visible
surface of the foreground top drawer's metal handle**, viewed from `agentview`.

The oracle binds the visual mesh `wooden_cabinet_top_handle_vis` on body
`wooden_cabinet_1_cabinet_top`, not the full drawer collision AABB. Full-grid
`mj_multiRay` supplies first-hit geometry and metric depth; it never consumes the
sensor box or sensor depth values. The sensor estimates handle membership from its
own first query box and backprojects all valid RGB-D pixels in that support.
Both use K/T and raster pixel centers `(u+.5,v+.5)`. The query is frozen for the pilot:

```text
the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground
```

This establishes one estimand, **not accurate segmentation**. Boxes may include
background/other handles; those errors remain in perception. No oracle support
corrects a measurement, covariance, candidate, history or model input. An invisible
oracle handle would have an unknown centroid. Contact/progress remain oracle-only.

Raw sensor and oracle centroid values reproduce exactly in all **18** accepted
pairs from saved supports, sensor frames and ray depths. All ray masks are single
connected components. Init-0 fused position errors are **38.3–98.9 mm**. Sensor
pixel purity ranges **11.7–52.5%**: early boxes find the right handle, while later
ones include other handles. Recall alone would hide that contamination.

Representative matched points, metres (full precision in raw records):

| Boundary / pair prefix | Oracle surface centroid | Perceptual fused estimate |
|---|---|---|
| 0 / `a99f0c0ae6f3` | `[.001897,-.059326,1.093591]` | `[-.057361,-.070449,1.050280]` |
| 48 / `80a7b0d86ac8` | `[.001965,-.097100,1.093620]` | `[-.056853,-.110252,1.050467]` |
| 152 / `695c2b09ca01` | `[.004516,-.198457,1.093462]` | `[-.025952,-.218286,1.004317]` |

Important limits: pixel weighting is not surface-area weighting; occlusion/view
changes can move this point without rigid-body translation. It is not a grasp
center or full object pose. Calibration is shared, not independently validated
against a real camera. Ray-versus-raster mixed-edge depth residuals remain:
0.04–4.46 mm over init 0, at most 5.54 mm across all 18. They are not corrected away.
Covariance reuses the explicitly labeled box-projection heuristic; it is **not
calibrated for this centroid**. Fresh capture does not imply fused estimate equals
the measurement.

The old AABB and bbox-center/interior-median-depth values remain separate raw
quantities. Their old numerical difference is still incomparable. Prior five
generic-query boxes selected background kitchen cabinetry, a distinct instance
localization failure. The new query/estimator must not retroactively upgrade them.

### Preserved correction history

First pilot `init*-attempt1/` used ID-color rendered segmentation and integer pixel
indices. Independent inspection found small false handle-ID components elsewhere
in the image. A full first-hit ray readout removed that ambiguity. Camera geometry
also required half-pixel raster centers; this was versioned as referent v0.2 on
both branches. At reset, ray/render mask IoU was .998 under the correct convention,
versus .855 with integer-index rays. Pixel-center correction follows the camera
projection convention, not model outcomes.

One explicit recollection/replay used the same states/query/candidates/history/
question/models/rubric. Original artifacts remain intact and are **not final exact-
referent evidence**. Original truncated Laya artifacts from the previous stage also
remain invalid for complete-interface claims. No failed seed was removed.

## Reference-quality pilot

Task: **close** the top drawer, not open it. Init 0, seed 1. Twelve boundaries
were selected from prior collector telemetry before new model outputs; 155 is a
terminal sentinel. States are correlated samples from one trajectory, not n=12
independent experiments.

The same 11 offered atomic tokens were executed independently in full Jev snapshots
through AtomicExecutor. Simulator/controller/gripper state was restored; repeated
STOP endpoints matched exactly. Source trajectory maximum full-state error remains
`1.2720269282340269e-11`. All evaluator effects stayed out of both model inputs.

The predeclared rubric reports local support and near-best sets, using existing
task conventions: .25 mm incremental closure, 2 mm approach, nonregression and no
new sampled obstacle pairs. These are not safety certificates or a universal expert
label. Raw continuous outcomes remain primary. STOP-adjusted values account for
progress that would occur without the selected intervention. Native execution can
end early upon success; per-branch durations are retained.

Below, probabilities are normalized returned API values; full 11-way distributions
are saved. `Δclose` is closure beyond STOP. Oracle state columns show actual
remaining opening/contact available to Laya; all XYZ/relations/history are in the
linked paired records. Evaluator surface gap/effects are **not** Laya state fields.

| Step / phase | Oracle remaining mm / contact | Laya top-1 p; top-2 p | Margin | Independent physical evidence / assessment |
|---|---|---|---|---|
| 0 far | 151.659 / no | GRASP .912; RELEASE .085 | .827 | No closure; surface approach −7.629 mm vs STOP. MV_FWD offers +7.748 mm approach. Preparation unvalidated. |
| 20 approach | 151.659 / no | RELEASE .853; GRASP .143 | .710 | Identical to already-open STOP; translations/CCW provide approach. No incremental utility. |
| 24 approach | 151.659 / no | GRASP .577; RELEASE .423 | .154 | No closure; surface approach −25.942 mm vs STOP. RIGHT/DOWN approach available. Preparation unvalidated. |
| 29 near contact | 151.659 / no | RELEASE .981; GRASP .019 | .961 | Identical to STOP; RIGHT provides +3.815 mm Δclose. |
| 33 first contact | 150.887 / yes | RELEASE .883; GRASP .117 | .765 | Raw closure 4.790 mm, but Δclose=0. RIGHT adds 5.424 mm. Passive progress is not policy value. |
| 48 progressing contact | 113.550 / yes | RELEASE .814; GRASP .186 | .628 | Δclose=0; RIGHT adds 9.089 mm. |
| 80 late progress | 35.467 / no | RELEASE .935; GRASP .064 | .871 | Δclose=0; CW adds 2.725 mm. |
| 120 late / pause | 30.751 / no | RELEASE .605; GRASP .395 | .210 | Same as STOP; no offered action resolves local rubric. **Unresolved reference**, not labeled wrong. |
| 140 loaded contact | 17.516 / yes | GRASP .596; RELEASE .404 | .192 | Reopens 14.272 mm; Δclose=−21.261 mm. RIGHT instead adds 8.653 mm beyond STOP. Adverse task consequence. |
| 144 near completion | 13.873 / no | GRASP .782; RELEASE .217 | .565 | Δclose=−.030 mm; surface approach −22.975 mm. RIGHT adds 2.519 mm. No measured advantage. |
| 152 near completion | 10.436 / no | RELEASE .888; GRASP .109 | .779 | Same as STOP; RIGHT adds 6.765 mm. |
| 155 terminal sentinel | −1.157 / no | RELEASE .953; GRASP .044 | .909 | Success retained after one step, but new static-cabinet contact peaks at 40.624 N; other offered actions retain success without that sampled obstacle. Not ongoing-task accuracy. |

All twelve oracle choices are GRASP/RELEASE. This does **not** prove every possible
multi-step preparation wrong, but does not establish a useful task reference.
Do not call oracle/perceptual disagreement perception error or report one accuracy
percentage against these choices. Rule is a deterministic geometric comparison,
not an independently validated expert either.

### Candidate semantics and dynamic-state warning

**91/132** init-0 counterfactual probes exceed the existing reset-calibration
execution envelopes; init 1/2 have 20/33 each. Preserve these flags. No unexpected
gripper-command change was detected. The sample contains contact and in-flight
states; reset calibration never established ideal 10 mm/pose-hold realization here.

At step 144, prior 50 ms TCP displacement is `[1.059,-.418,3.068]` mm; contact was
present at 137–143 and absent at 144. STOP then moves `[46.591,-11.968,29.364]` mm
(56.358 mm total), rotates 3.022 degrees, and closes the drawer 1.757 mm in .4 s.
Grip stays −1; gap changes only −.017 mm. Repeated branches are exact, but
repeatability does not establish ideal holding or identify the mechanism.

Residual dynamics / inherited controller error are plausible, not established
causes: controller-goal/torque traces were not recorded. CDS includes one preceding
control/displacement but lacks explicit current orientation, velocity, controller
tracking error and loading. Thus even the oracle CDS is a partial interface.
Do not hide this by settling states, weakening contracts, or calling Stage 1
regressed without evidence. Characterize this regime before useful-policy claims.

### Repeatability and input completeness

12 pairs × 2 branches × 2 providers × 3 repeats = **144 decisions**, 72 complete
comparisons. Every repeated Rule and Laya input had one unique choice and maximum
returned probability difference **0.0**. Laya consumed-token hashes were stable;
state needs 382–582 tokens with 874 available, zero clipping. All 72 Laya calls have
audits; Rule's 72 entries correctly have no tokenizer audit. Laya decision latency
including input validation ranges 35.94–309.63 ms, including first-call warmup.

## Multi-initial-state collection

| LIBERO init ID | Initial → final opening mm | Full controls | Contact / progressing boundaries | Official success | Near-completion <=10 mm |
|---|---|---|---|---|---|
| 0 | 151.659 → −1.157 | 155 | 36 / 84 | yes | 2 nonterminal states |
| 1 | 148.507 → 29.879 | 155 | 38 / 77 | no | none |
| 2 | 146.252 → 15.696 | 155 | 39 / 82 | no | none |

All three have far/approach/near-contact/contact/progress coverage. Fixed-control
transfer is viable but **does not ensure matched near-completion coverage**.
The historical collector uses different primitives, hierarchy and simulator preview;
its success does not validate today's 11-token no-effect model.

Each actual benchmark-state hash differs. Pair identity is task/binding/assets +
init ID/benchmark hash + seed + source control-trajectory hash + physical boundary/
state hash + observation/belief/pair IDs. Only init 0 is compared to the init-0
archive. Init 1/2 have their own physical trajectories, not fabricated archive error.
All 18 rendered pairs preserve physical identity through inference and evaluator
restoration. Source trajectory SHA256:
`a53137c06e53fada1a32b94bfdb6d2c12512692be3672c19c0f3fa0235dd1d78`.

## STOP-only availability

The earlier uncertainty gate is unchanged: after one update, unobserved velocity
prior contributes about .48 m² of position trace growth at .4 s, versus .064 m²
process noise. With initial trace .009508 and limit .03, crossing occurs near
.0815 s, before TTL .75 s. The rule implements its uncalibrated assumptions; it is
not empirical proof of a calibrated safety boundary. No thresholds were loosened.

Paused offline paired probes keep C fixed and record natural feasibility separately;
all final init-0 fresh pairs had 10 naturally feasible tokens versus 11 offline
probes. STOP-only availability therefore does not prevent E0 data collection.
The distinct physical STOP drift discussed above does affect interpretation of
useful action semantics and must not be conflated with uncertainty gating.

## Conditional E0 proposal — not frozen or executed

The exact smallest proposed design is in [research.md](../../research.md): tested IDs
0/1/2, seed 1, fixed archived controls; two chronological quartile selections in
five measured strata, deduplicated to **29 physical boundaries**. Fresh and .4-s-old
histories at the same boundaries yield **58 pairs**, not hundreds of presumed
independent frames. Twenty windows actually have >.1 mm drawer motion; nine are
static-target controls. Init-0-only near-completion is separate, not pooled.

- Shared C: existing ordered six 10 mm translations, two world-Z rotations,
  STOP/GRASP/RELEASE. No filtering from evaluator outcomes; empty effect bundles.
- Same Laya bytes/API/question/compact-v0.1 presentation, matched proprioceptive
  history, three alternating-order repeats, RNG seeded once; Rule comparison.
- Primary descriptive metrics: top-1, top-2 with ties, JS in nats, oracle margin,
  latency and same-input variability. Stratify by init/phase, actual age, missingness,
  comparable position/relation error and natural availability. No claimed oracle
  natural-set agreement when it is unavailable.
- Sensitivity families: coherent target+relations, progress missingness, contact
  missingness, coherent quality/freshness/covariance. Do not silently recompute some
  dependencies but not others. No field-sensitivity grid was run in this stage.
- Freeze code/dependencies/model content IDs, task assets/success predicate,
  benchmark state vectors, controls/selection, referent/camera/pixel convention,
  query/parser/depth/covariance, temporal config/thresholds, candidate ordering/
  semantics, question/history/precision, inference config/repeats, metrics and
  failed/missing-state handling. Do not change these after formal collection begins.

**This design is currently defensible only as descriptive decision fidelity**, not
preservation of a demonstrated useful oracle policy. Before freezing, choose that
narrower claim explicitly, or run a separately approved small reference-interface
pilot with task-relative/dynamic evidence and characterized execution conditions.
A fixed-effect reference is another separate option; it is not this no-effect E0.
Do not silently change the question or add effects until a model looks good.

## Verification and evidence commands

Run from repository root. Executables actually used:

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
V=/home/junhongli/miniforge3/envs/locateanything/bin/python
T=/home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1
L=/home/junhongli/projects/LIBERO
K=/home/junhongli/runs/libero-config
Q='the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground'
```

```sh
$P -m pytest -q tests/test_reference_quality.py tests/test_target_referent.py tests/test_initial_state_audit.py tests/test_decision_interface.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Outputs: **62 focused passed; 152 full passed; All checks passed!; compileall exit 0**.

Real multi-init audit, exit 0, all three control trajectories retained:

```sh
CUDA_VISIBLE_DEVICES=2 MUJOCO_GL=egl $V -m embodied_runtime.experiments.audit_initial_states --trajectory "$T" --output runs/reference-pilot/multi-init --init-state-ids 0 1 2 --seed 1 --libero-root "$L" --config-dir "$K"
```

Final accepted collection commands (all exit 0; pairs 12,3,3):

```sh
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MUJOCO_GL=egl $V -m embodied_runtime.experiments.collect_pairs --trajectory "$T" --output runs/reference-pilot/init0-raycast-v02 --sample-steps 0 20 24 29 33 48 80 120 140 144 152 155 --reference-pilot --query "$Q" --libero-root "$L" --config-dir "$K"
CUDA_VISIBLE_DEVICES=4 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MUJOCO_GL=egl $V -m embodied_runtime.experiments.collect_pairs --trajectory "$T" --output runs/reference-pilot/init1-raycast-v02 --init-state-id 1 --sample-steps 0 48 144 --reference-pilot --query "$Q" --libero-root "$L" --config-dir "$K"
CUDA_VISIBLE_DEVICES=6 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 MUJOCO_GL=egl $V -m embodied_runtime.experiments.collect_pairs --trajectory "$T" --output runs/reference-pilot/init2-raycast-v02 --init-state-id 2 --sample-steps 0 48 144 --reference-pilot --query "$Q" --libero-root "$L" --config-dir "$K"
```

Replay and raw-derived reports (all exit 0):

```sh
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V -m embodied_runtime.experiments.replay_equivalence runs/reference-pilot/init0-raycast-v02/episodes.jsonl --output runs/reference-pilot/replay-init0-v02 --provider both --repeats 3 --seed 1
$P -m embodied_runtime.experiments.summarize_equivalence runs/reference-pilot/replay-init0-v02
$P -m embodied_runtime.experiments.reference_quality runs/reference-pilot/init0-raycast-v02/episodes.jsonl runs/reference-pilot/replay-init0-v02/episodes.jsonl --output runs/reference-pilot/replay-init0-v02/reference-summary.json
$P -m embodied_runtime.experiments.target_referent runs/reference-pilot/init0-raycast-v02 runs/reference-pilot/init1-raycast-v02 runs/reference-pilot/init2-raycast-v02 --output runs/reference-pilot/raw-referent-audit-v02
```

Summary outputs: 12 pairs, 144 decisions, 72 complete comparisons, zero incomplete;
72 oracle-decision rows including Rule/repeats. Every run has resolved config,
manifest and hash-chained JSONL; collection also has RGB-D frames. Final report
artifacts: `replay-init0-v02/reference-summary.json`,
`replay-init0-v02/equivalence_summary.json`, `replay-init0-v02/equivalence_summary.csv` and
`raw-referent-audit-v02/{referent_audit.json,referent_audit.csv}`.
There are no failure records/incomplete tails in accepted runs; contract flags are
retained inside evaluator probe records, not omitted because collection completed.
Commands refuse to overwrite run directories; choose an explicitly new attempt
path if a reviewed reproduction is needed.

## Human review gate

```text
Geometric reference comparable: YES (stated view/calibration definition)
Reference state usable as a validated useful-decision reference: NO
Multi-init collection viable: YES (near-completion coverage not matched)
Ready to freeze exp-e0-v0: NO
Ready to run formal E0: NO
```

Smallest next step: decide whether E0 claims **descriptive fidelity** or preservation
of **useful robotic decisions**. For the latter, validate a minimally revised oracle
interface/dynamic operating regime in a small, separately declared pilot. Preserve
the present negative evidence; do not start Stage 5/6 automatically.
