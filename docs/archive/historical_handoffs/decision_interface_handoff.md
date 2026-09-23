> Historical record; its plans and checkout paths are not current instructions.
> Current authority: [current_state.md](../../current_state.md).

# Decision-interface stage handoff

2026-09-23. Start: `33daba2`, clean. Scope: canonical state/effects, paired diagnostic
export/replay, task/cadence review and small stability smoke. No formal E0/E1, new
foundation model, learned predictor, tracking integration, dependency update or tag.

Implementation commits:

- `16c4fca`: canonical states, separate effects, experimental identity, collection,
  same-provider replay and raw-derived summaries.
- `9041f9d`: compact model presentation, fail-closed Laya token audit and backward-
  compatible interpretation of earlier replay logs.

The documentation-only successor contains this report. The implementation worktree
was clean at both replay launches. Collection ran from dirty `33daba2` during
development; its manifest preserves dirty status and package-source SHA256s. It is
not presented as a formal frozen dataset. No model/run directories were committed.

## Environment actually used

```text
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
V=/home/junhongli/miniforge3/envs/locateanything/bin/python
Python 3.10.21; NumPy 1.26.4; pytest 9.1.1; ruff 0.15.22
MuJoCo 3.5.0; robosuite 1.4.1; torch 2.2.0; CUDA 12.1
transformers 4.57.3; laya 0.3.4; NVIDIA RTX 4090
LIBERO: 8f1084e3132a39270c3a13ebe37270a43ece2a01
Jev-LIBERO: 3bdad985b225aeccc39fbe5863c6eea2e81c515a
```

Both upstream worktrees remained unchanged. Local model content IDs:

```text
LocateAnything: 4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f
Laya:          9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704
```

These are hashes of local model/config/code/tokenizer files, not asserted upstream
revision names. Existing upstream tokenizer/Gym/robosuite warnings remain; no
dependency or checkpoint changes were made to suppress them.

## What changed

| File | Purpose / behavioral change |
|---|---|
| `decision_interface.py` | v0.1 schema/projections, explicit unknown/oracle evidence, relations, labeled field interventions, separate effects, canonical probe input |
| `runtime_core.py` | existing Rule/Laya providers accept canonical inputs; live BeliefSnapshot branch remains; canonical Rule is a greedy geometric reference |
| `adapters/laya_input.py` | inspect actual installed tokenizer/sequence builder; reject canonical truncation and record consumed tokens |
| `adapters/libero.py`, `experiments/run_libero.py` | `init_state_id` explicitly passes through to benchmark reset and episode identity |
| `experiments/collect_pairs.py` | bounded archived-control replay, initial-state inventory, physical/event/belief pairing, no model-controlled actions |
| `experiments/equivalence.py`, `replay_equivalence.py` | matched state-only probes, repeatability, pair integrity and raw metrics |
| `experiments/summarize_equivalence.py` | independent regeneration/validation from raw decisions; interrupted comparisons stay incomplete |
| `tests/test_decision_interface.py`, `test_equivalence_summary.py` | projection, isolation, matching, metric, failure/integrity, presentation and clipping checks |
| README, research/architecture/current-state/vision docs | align current direction; historical handoffs remain historical |

The Stage 1 temporal equations, validity thresholds and atomic execution semantics
were not changed. The 74 Stage 2 tests still pass. New canonical probes are offline;
the legacy closed-loop runner was not silently switched to a new policy/interface.

## CanonicalDecisionState v0.1

```text
version
meta: branch, source belief ID, revision, asof simulation time, oracle source ID
fields[name]: value | source | basis | privileged
```

Twenty-four fields in seven families:

- Task: instruction and query identity, shared task context.
- Robot: world TCP XYZ, joint-opening width, retained gripper command, from legitimate
  robot observations; matched on both branches.
- Target: world position, position definition, velocity, current visibility. Perception
  uses temporal RGB-D belief; oracle uses moving-collision AABB center. Oracle velocity
  and current visibility stay unknown; a detected historic query does not prove visibility.
- Relations: target minus TCP, Euclidean distance, XY alignment norm, signed height
  error, deterministically derived with privilege propagation.
- Interaction: target contact unknown perceptually, available from simulator for oracle;
  holding stays unknown unless independently observed. Closed grip is not holding.
- Progress: remaining_open_mm is oracle-only; no visual progress estimator is invented.
- Quality: geometry age/validity/covariance, calibrated flag, semantic age/validity/score,
  temporal consistency. Simulator observations do not fabricate visual confidence or
  sensor covariance. Perceptual source/uncalibrated status remains explicit.

Recent actual history is a separate shared one-item input: preceding recorded control,
TCP displacement, elapsed simulation time and grip command. No hidden object-state,
contact, success or task-progress result is copied into perceptual history.

Projection records preserve full precision and source metadata. The model-facing
`compact-v0.1` view contains values/nulls and quality, not branch/source/basis labels;
it rounds to six significant digits and has deterministic key order. This is a
versioned experimental choice. It makes full state available within the existing
checkpoint budget without silently enlarging the context. Full audit evidence is
not discarded just to shorten the prompt.

## Effects and candidate isolation

`CandidateEffectBundle(version, candidate_set_id, effects[token])` carries source,
privilege, supported values and assumptions. Sources: geometry, oracle_sim, learned
(reserved), unknown.

Tier-0 effects: nominal 10 mm translation with stationary target, producing signed
distance and XY-error change. No task dynamics, contact likelihood or collision
guarantee. Unsupported actions have unknown effects. An explicit oracle adapter can
package Jev closing_mm, surface-gap reduction, target contact and obstacle force;
this was unit-tested, not used to select the primary smoke candidates.

The canonical input rejects unmarked legacy preview text/risk/metadata. v0.1 permits
only fixed semantics-only offline probes. A separate `diagnostic_only` guard is
required for oracle states or oracle-tainted effects. Primary replay explicitly
requires empty effects and shares the exact candidate tuple, question and history
between branches. Natural visual feasibility is retained as a separate diagnostic;
natural oracle-set agreement is **unknown**, not fabricated as 100%.

## Paired collection and initial identity

Collection source:
`/home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1/`.
The old task JSON omitted the current declarative `joint_position` measurement
entry. An explicit, logged compatibility normalization accepts only that equivalent
legacy accessor; other config mismatches fail. Two preliminary CLI checks stopped
before run creation while identifying this mismatch; no simulator episodes or data
were discarded. No source trajectory files were modified.

Replayed all 155 controls, checked all 156 archived physical boundaries. Maximum
full-state deviation: `1.2720269282340269e-11` against the existing upstream replay
tolerance `1e-8`. Official collector success was true. Historical controls include
40 mm movements and privileged collection decisions; they are labeled recorded
controls, not runtime atomic decisions. No Rule/Laya probe output was executed.

The benchmark inventory contains 50 distinct 77-component initial vectors. Sixteen
components vary; initial drawer opening spans about 140.178–159.564 mm. This supplies
real reset diversity, not independent phase coverage. Only init 0 trajectory replay
is currently verified. New runs distinguish `task + init_state_id + seed`, with
benchmark-state hash, source trajectory/config hash, control index and physical-state
hash. Changing only the seed is not claimed to sample new benchmark initial states.

At each selected boundary, oracle evaluation and robot observation are saved; RGB-D
is captured and processed while simulation is paused; the physical hash is checked
again before pairing. The perceptual branch may use old evidence but is projected to
the same as-of boundary. Paired IDs link to camera artifacts/events, full belief and
the simulator evaluator. Different point definitions and missing fields are explicit.

## Smoke evidence

Artifacts under `runs/interface/`:

| Directory | Evidence |
|---|---|
| `trajectory-audit` | 50-state inventory, 156 checked physical boundaries, replay completion |
| `paired-smoke-attempt1` | five fresh frames plus one stale-history pair; RGB/depth/K/T, model outputs, observations, beliefs, physical states |
| `replay-smoke-attempt1` | retained early full-JSON replay, **invalid as full-interface evidence due to truncation** |
| `encoding-audit` | 24 tokenizer-only audits of old versus compact presentation; zero model calls |
| `replay-smoke-compact` | accepted 72-decision smoke, raw JSONL and independent CSV/JSON summaries |

All runs retain config/manifest and durable JSONL. Captured frames are under the
paired collection's `frames/`. Six pairs share candidate ID prefix `1d30b49d6fe5`.
Representative compact Laya results below are descriptive, not accuracy labels:

| step / variant | pair ID prefix | oracle contact / remaining mm | perceptual age / natural feasible count | oracle choice → perceptual choice | JS, nats |
|---|---|---|---|---|---|
| 0 fresh | 40e14d928eca | false / 151.659 | 0 s / 10 | GRASP → GRASP | .02879 |
| 24 fresh | f793988b6fbb | false / 151.659 | 0 s / 10 | GRASP → STOP | .28653 |
| 48 fresh | c2c92137de6e | true / 113.550 | 0 s / 10 | RELEASE → GRASP | .30667 |
| 144 fresh | 4ba284a03a9c | false / 13.873 | 0 s / 1 | GRASP → STOP | .38029 |
| 152 stale | 267f0bd30cf6 | false / 10.436 | .4 s / 1 | RELEASE → GRASP | .16123 |
| 152 fresh | dad84904c692 | false / 10.436 | 0 s / 10 | RELEASE → GRASP | .25233 |

Both step-152 variants have identical physical ID prefix `951f862c13de`, shared
history and candidates. Only the perceptual evidence is refreshed. Perceptual
covariance trace goes from 2.165758 m² to .009869 m², restoring natural availability
without threshold changes. Primary offline candidates remain 11 for both variants.

At step 0 the oracle position is approximately `[-.01164, -.15007, 1.08809]` m and
the visual estimate `[-1.40878, -.55929, .61324]` m. The query response box was
`[0,36,152,131]` in the 384-pixel image. Its relevance requires inspection; no oracle
data was used to correct it. The point definitions differ, so this discrepancy is
not reported as calibrated position error. Contact/progress are available on the
oracle branch and explicitly null perceptually.

Rule's deterministic reference selected MV_FWD versus MV_BACK at step 0, MV_RIGHT
versus MV_BACK at contact, and MV_RIGHT versus STOP at the stale boundary. These
are greedy geometric references, not an expert closing controller. Laya oracle
choices likewise have not been validated as useful. No task-level policy result
follows from a successful independent collector trajectory.

## Model input and repeatability findings

The initial JSON presentation required 1,722–2,021 state tokens with only 775
available. All 12 branch inputs clipped state; translation descriptions also clipped,
even losing the Z-direction detail for MV_UP/MV_DOWN. Branch-dependent missing text
confounded the earlier oracle/perceptual disagreement. Matching Python snapshots
alone did not establish a matched complete model interface.

The corrected compact view requires 364–562 state tokens within 874 available;
heading and all options survive unchanged. No checkpoint/config/dependency upgrade.
The adapter records actual consumed token IDs/hash and actual device/dtype, and
raises before model inference if any component would be truncated. Old records use
their explicit legacy renderer during summary regeneration; their missing encoding
audit is not interpreted as an untruncated pass.

Accepted replay: six pairs × two branches × two providers × three repeats = 72
decisions, 36 complete paired comparisons, zero incomplete comparisons. Branch order
alternates and RNG is seeded once, not before every call. For every repeated input:

```text
Rule unique choices: 1
Laya unique choices: 1
maximum returned probability difference: 0.0
Laya consumed-token hashes: identical
state / heading / option truncation: none
```

This is repeatability at the API's returned precision on this hardware/checkpoint,
not a universal determinism claim. GPU deterministic algorithms are disabled and
logged. Laya outputs rounded probabilities; metric normalization is recorded in
code, raw probabilities remain available. Top-2 ties are explicit, missing distributions
stay missing, and unavailable natural-oracle candidate agreement stays unknown.

## Stage 2 availability explained

After one position observation, velocity remains unobserved with variance 1 m²/s²
per axis and zero position–velocity cross covariance. With Stage 1 defaults:

```text
trace(Pposition(t)) = 0.009508 + 3*t² + t³
at 0.4 s:           = 0.009508 + 0.480000 + 0.064000 = 0.553508 m²
configured limit:     0.030000 m²
```

Unobserved initial velocity contributes 88.2% of growth; process noise contributes
11.8%. The limit is crossed around .0815 s, before the .75 s age TTL. At .8 s,
trace reaches 2.441508 m² and age/semantic TTL also expire. The implementation is
consistent with its assumptions; the assumptions are not calibrated bounds on drawer
motion. It is not evidence that the real drawer position is that uncertain.

The first inference took 2.551 s wall time during paused warmup. Three decision
boundaries completed in .426 s wall time after it; capture 2 returned after episode
termination. Thus the original smoke had no recovery opportunity. Do not loosen
thresholds. Paused paired collection/shared offline probes remove availability as a
confound for State Gap, while keeping natural live gating visible. Calibrating a
motion prior is a separate later intervention, not a hidden change in this stage.

## Verification

From the repository root, using P and V above:

```sh
$P -m pytest -q tests/test_decision_interface.py tests/test_equivalence_summary.py
# 29 tests (13 interface + 16 summary)
$P -m pytest -q
# 103 passed
$V -m pytest -q
# 103 passed
$P -m ruff check .
# All checks passed!
$P -m compileall -q embodied_runtime tests
# exit 0
git diff --check
# exit 0
```

Exact simulator / model smoke commands:

```sh
MUJOCO_GL=egl $P -m embodied_runtime.experiments.collect_pairs --trajectory /home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1 --output runs/interface/trajectory-audit --audit-only --libero-root /home/junhongli/projects/LIBERO --config-dir /home/junhongli/runs/libero-config
CUDA_VISIBLE_DEVICES=1 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V -m embodied_runtime.experiments.collect_pairs --trajectory /home/junhongli/projects/jev-libero/examples/records/top_drawer_seed1 --output runs/interface/paired-smoke-attempt1 --sample-steps 0 24 48 144 152 --stale-step 152 --libero-root /home/junhongli/projects/LIBERO --config-dir /home/junhongli/runs/libero-config
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $V -m embodied_runtime.experiments.replay_equivalence runs/interface/paired-smoke-attempt1/episodes.jsonl --output runs/interface/replay-smoke-compact --provider both --repeats 3 --seed 1 --device cuda
$P -m embodied_runtime.experiments.summarize_equivalence runs/interface/replay-smoke-compact
# {"pair_count":6,"decision_count":72,"complete_comparisons":36,"incomplete_comparisons":0,"terminated":true}
```

All exited 0. Two independent summary regenerations produced byte-identical CSV and
JSON. The initial truncated replay used the same replay command with output
`replay-smoke-attempt1` before the compact fix; it is retained, not pooled with the
new results. No new atomic calibration was required; Stage 1/2 tests are unchanged.

## Readiness and recommended next gate

```text
Canonical schema / unknowns / provenance: READY for controlled diagnostic use
Separate effects and privilege boundary: READY for diagnostic use
Same-physical-state pairing: VERIFIED on init 0 recorded trajectory
Same-provider replay / actual-token matching: VERIFIED in bounded smoke
Same-input Rule/Laya stability: observed stable at returned precision, 3 repeats
Phase coverage: verified in the collector, not autonomous canonical policy
Ready to freeze exp-e0-v0: NO
Ready for formal E0: NO
```

Smallest blockers: common target referent/query validation; independently assessed
usefulness of oracle-input decisions without changing effects; collection coverage
for more than one actual initial state. No threshold loosening or model scaling
addresses these by itself.

Recommendation: first approve a 12-state reference-quality pilot, then conditionally
five benchmark initial states × twelve phase-stratified boundaries × fresh/.4-s-old
sensor evidence (up to 120 pairs). Freeze candidate/question/history/model/presentation,
keep effects empty, and analyze top-1/top-2/JS/margin/latency with actual age, missingness,
natural availability and same-input variability. First field interventions: coherent
target+relations, progress, contact, freshness/validity, covariance. See the exact
conditional design in [research.md](../../research.md). Treat trajectories, not repeated
frames or inference calls, as the primary independent units.

STOP for human review. No formal collection or freeze tag was created.
