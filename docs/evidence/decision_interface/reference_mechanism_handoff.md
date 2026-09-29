> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Why the current oracle reference is not task-useful

2026-09-23. Bounded diagnostics after baseline `0da1596`, not formal E0.
Protocol: [reference_mechanism_protocol.md](reference_mechanism_protocol.md).

## Strongest supported explanation

There are **two independently demonstrated failures**, not one missing perception
field. The current checkpoint/presentation does not reliably follow even explicit
action-selection instructions; separately, nominal action descriptions omit
controller memory and loaded dynamics that substantially change their physical
meaning. Oracle geometry fixes neither. High model probability and repeatability
are not evidence of task competence.

The evidence does not isolate model weights from representation mismatch, prove
that all Laya interfaces fail, or establish a complete dynamics explanation.
Adding arbitrary oracle fields or effects is not justified as a cure. The original
task question also lacks an explicit horizon/utility; however, ambiguity alone
cannot explain the instruction-following controls below.

## Model controls: 52 calls, no effects or action execution

Four accepted Stage 4 oracle fixtures, six conditions, two identical repeats;
two additional command-following fixtures repeated twice. Eleven options in every
condition; original history retained. Evaluator outcomes never enter these inputs.
Entries below show selected token and its API probability, **not** the separate
API entropy-derived confidence field.

| Boundary / regime | Baseline | Reversed option order | Neutral option IDs | Explicit nominal approach | Mirrored approach geometry |
|---|---|---|---|---|---|
| 0 / far | GRASP .9118 | RELEASE .9943 | GRASP .9664 | GRASP .9567 | GRASP .9943 |
| 29 / approach | RELEASE .9805 | RELEASE .9951 | GRASP .5846 | RELEASE .9946 | RELEASE .8253 |
| 48 / loaded contact | RELEASE .8137 | RELEASE .9990 | GRASP .8269 | RELEASE .8739 | RELEASE .5061 |
| 140 / late contact | GRASP .5958 | RELEASE .9913 | RELEASE .4147 | RELEASE .8465 | RELEASE .7760 |

- All eight unique approach controls fail the explicitly requested nominal
  distance-reduction criterion. This criterion is a simple diagnostic, **not** a
  claim about the best physical task action in contact.
- At boundary 0, “choose exactly MV_FWD” returns GRASP .9989; “choose exactly
  MV_BACK” returns GRASP .9987. Required tokens receive .0004/.0007. Neither test
  needs dynamics prediction or drawer expertise.
- Masking target/relational/interaction/progress evidence still yields GRASP with
  probability 1.0000/.9983/.9998/.9973. Robot/task/history remain: this is not proof
  of total input independence. Geometry and presentation do change distributions.
- All 26 identical-input comparisons have identical choices, API probabilities
  and reconstructed pre/post-temperature distributions. Actual device/dtype:
  CUDA/bfloat16. All calls are accepted without clipping. No unmatched intents,
  recorded errors, or source/fixture consistency failures in raw reconstruction.
- The act/defer output is 1.0 for all calls; recovering that previously unused
  signal does not rescue abstention here.
- The checkpoint uses temperature **0.1005828083** for `choice:11+`. At boundary 0,
  GRASP's untempered softmax mass is .2075, versus returned .9118; the margin grows
  from .0440 to .8265. At 140 it grows from .00846 to .19174. Temperature preserves
  argmax, so it explains overstated apparent certainty, **not the wrong choice**.
  Untempered values are diagnostics, not independently calibrated probabilities.
- Captured scorer logits, typed marker mapping and returned argmax agree. There
  is no observed option-index decoding error. These checks do not prove the whole
  model/interface stack correct or distinguish training mismatch from encoding.

## Physical controls: 29 boundaries, three actual initial states

Replayed the archived 155 low-level collector controls on init IDs 0/1/2, seed 1.
These are collector boundaries, not settled atomic-policy endpoints. All 468
source boundaries match the previous multi-init simulator trajectories exactly.
435 independent probes comprise 319 native primary actions, 29 uninstrumented
STOP repeats, and 87 explicitly diagnostic STOP variants. All restoration checks
pass; every traced/untraced STOP matches endpoint and mutable context exactly.
No source state is silently settled. Init 1/2 still lack strict near-completion.

| Regime | Evidence | Interpretation |
|---|---|---|
| Reset/far, step 0, all three inits | All 11 tokens pass reset-calibrated envelopes | Labels locally interpretable; not a general safety guarantee |
| Approach, init 0 step 24 | All 11 flagged | Contact alone does not explain departures |
| First contact, init 1 step 38 | All 11 pass | Contact is not sufficient to predict failure either |
| Loaded palm contact, step 48 | Only rotations pass on all three inits; STOP translates about 1.2–1.35 mm | Small translation can coexist with orientation-contract failure |
| Late contact, step 140 | About 100–106 N finger contact; native STOP drift 6.85/6.77/1.87 mm | Controller effort and inherited goals matter |
| In-flight late, step 144 | STOP drift 55.96/63.58/61.71 mm | Nominal hold is a misleading absolute intervention description |
| Near-completion/terminal | Init 0 step 153 includes a .30 s branch; step 155 actions last .05 s | Compare horizons explicitly; not ordinary .40 s actions |

182/319 native primary probes trigger at least one reset-calibrated contract flag
(init 0: 80/121; init 1: 50/99; init 2: 52/99). This targeted sample is not a
population failure rate and differs from Stage 4's sample.

| Native token | Flagged / 29 | Median / maximum true TCP displacement, mm |
|---|---:|---:|
| MV_FWD | 20 | 8.86 / 71.46 |
| MV_BACK | 15 | 9.15 / 56.16 |
| MV_LEFT | 15 | 9.45 / 62.87 |
| MV_RIGHT | 16 | 9.62 / 65.65 |
| MV_UP | 17 | 9.21 / 65.91 |
| MV_DOWN | 18 | 9.12 / 62.52 |
| ROTATE_CW | 12 | .93 / 32.80 |
| ROTATE_CCW | 18 | 1.34 / 42.06 |
| STOP | 17 | 1.25 / 63.58 |
| GRASP | 17 | 1.25 / 63.57 |
| RELEASE | 17 | 1.25 / 63.58 |

### What causes motion under STOP?

Installed robosuite OSC retains `goal_ori` when the angular command is zero;
native STOP/translations/grip actions therefore track an **inherited orientation
goal**, not necessarily current measured orientation. STOP anchors observed entry
position and runs feedback for up to eight 50 ms controls. Retained grip command
also continues driving the gripper, rather than freezing measured aperture.

At step 144, reanchoring only the orientation objective reduces STOP displacement
from 55.96/63.58/61.71 to 32.19/34.64/34.85 mm. Fresh-FK position feedback alone
leaves 55.71/63.26/61.36 mm. Thus inherited orientation demand is a causal
contributor; observation cache error is not the main explanation at these states.
Init 0's observation/FK discrepancy is only about .33 mm, while its orientation
goal error is 12.67 degrees. Torque-clipped joint-steps fall from 73 to 27 with
orientation reanchoring. Entry TCP velocity is already nonzero and increases
during native execution. Residual drift remains large; momentum, contact,
controller tracking and actuator limits are not separately identified.
Reanchoring worsens some states (init 0 step 153: 3.40 to 11.35 mm), so it is
**not a proposed universal fix**.

At init 0 step 144, true X displacements are STOP +46.39, MV_FWD +55.74,
MV_BACK +37.04 mm. Opposite nominal translations both move +X, yet their
STOP-relative increments are distinguishable. Such differences require the same
initial full controller context and horizon; they are not context-free 10 mm
motions. One unequal-horizon branch is explicitly excluded from this comparison.

### Aliases and interpretation limits

All 29 native STOP/RELEASE pairs have identical command traces and simulator
endpoints because these source states retain an open gripper command. No additional
near-endpoint pairs pass the report's declared .1 mm/.01 degree tolerances and grip
conditions. GRASP's similar TCP trajectory is **not** an intervention alias when
its grip command/aperture differ. This study did not sample retained-closed source
states; STOP/GRASP equivalence there is an implementation expectation, not new
measured evidence. Grip closure reaches 21.40 mm in this sample.

Native tokens are most interpretable in measured reset-like regimes. Loaded
regimes remain reproducibly probeable, but require controller-context and duration
conditioning. Neither discarding loaded states nor changing labels retroactively
would validate the original reference.

## Evidence, tools, limitations

Ignored raw artifacts under `runs/reference-mechanism/`:

- `physics-smoke-attempt1`: preserved LIBERO bootstrap/import failure, zero probes.
- `physics-smoke-attempt2`: successful 15-probe instrumentation check.
- `physics-pilot-v01`: all source boundaries, intents, 435 probes and restorations.
- `physics-report-v01`: raw-derived JSON and per-probe CSV, including anomalies.
- `model-diagnostic-v01`: source fixtures, payload hashes/token audits, intents,
  complete API responses and observed scorer logits for all 52 calls.

New reusable modules: `operating_regime_probe`, `operating_regime_report`, and
`reference_model_diagnostic`. Reports reject inconsistent/orphaned evidence and
do not trust cached analysis. Raw runs contain working-source provenance; they
were not collected under a frozen release. Raw artifacts remain local/ignored.

Instrumentation caveat: per-control trace `after.gripper_width_joint_m` is read
before the caller updates its observation cache and is therefore the preceding
cached width. Use probe-level before/after telemetry or physical finger-pad gap
for aperture changes; those endpoints are current. TCP trace observations are
explicitly updated from the returned observation. This does not affect execution.

Tracking remains inactive, covariance heuristic/uncalibrated, perceptual unknowns
unknown. STOP-only natural availability is unchanged: it concerns uncertainty
gating, not the physical drift of the STOP intervention. The offline diagnostics
do not authorize bypassing that gate online. No effects entered the model.

## Smallest next test and research decision

First run a **predeclared, tiny model/interface capability ladder**, not more
perception collection: explicit token selection, signed relational comparisons,
then nominal geometric action choice. Separate robot-free minimal typed payloads
from the current robot payload, keep option count/calibration fixed, counterbalance
order/aliases, and verify exact consumed tokens. A deterministic solver supplies
labels only for these well-defined tests. This distinguishes basic typed-interface
competence from interference by robot context before adding state fields.

In parallel, define and validate a physical operating envelope using existing
measurements, including inherited controller goals and equal horizons. If a new
action implementation is proposed, test it as a new intervention; do not repair
old labels by fiat. Only after these gates pass should a small task-utility pilot
compare an explicit no-effect objective to a separately labeled fixed-effect
diagnostic. Effects would change the scientific condition, not rescue the original
State-Gap claim retroactively.

**Useful oracle decision reference: NO. E0 freeze/run: NO.** Descriptive fidelity
to this fixed classifier remains measurable, but is not evidence that perception
preserves useful robotic decisions. Multi-init collection itself remains viable.

## Reproduction and verification

Runtime: Python 3.10.21, MuJoCo 3.5.0, robosuite 1.4.1, NumPy 1.26.4,
torch 2.2.0, transformers 4.57.3, laya 0.3.4. Commands from repository root:

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
MUJOCO_GL=egl $P -m embodied_runtime.experiments.operating_regime_probe \
  --trajectory /home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1 \
  --output runs/reference-mechanism/physics-pilot-v01 \
  --libero-root /home/junhongli/projects/LIBERO \
  --config-dir /home/junhongli/runs/libero-config
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.reference_model_diagnostic \
  runs/reference-pilot/init0-raycast-v02/episodes.jsonl \
  --output runs/reference-mechanism/model-diagnostic-v01 \
  --repeats 2 --seed 1 --device cuda \
  --laya-path /home/junhongli/models/huggingface/laya/typed-decisions
$P -m embodied_runtime.experiments.operating_regime_report \
  runs/reference-mechanism/physics-pilot-v01 \
  --output runs/reference-mechanism/physics-report-v01
$P -m embodied_runtime.experiments.reference_model_diagnostic \
  --summarize runs/reference-mechanism/model-diagnostic-v01
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Both completed simulator runs and the model run exited zero. Existing output
directories must not be reused for new collection; choose a fresh attempt path.
Final verification: **211 tests passed in 5.24 s; ruff and compileall passed**.
The three new focused test modules contribute 38 tests (7 probe, 11 report,
20 model diagnostic). No formal E0, release tag, upstream edits or downloads.
