# Stage 0 audit — pre-modification evidence

Baseline: `75d810784fd0d7accfad91cd8c2f550518885638`, 2026-09-22.
Working tree initially contains only the user's untracked `docs/mix.md`.
Existing environment: Python 3.10.21, NumPy 1.26.4, MuJoCo 3.5.0,
robosuite 1.4.1, torch 2.2.0, transformers 4.57.3, laya 0.3.4.
Baseline verification: `python -m pytest -q`: 12 passed; `python -m ruff check .`: passed.

## Atomic execution

AtomicExecutor maps six translations to world XYZ, with backend step size 10 mm.
It starts `grip_cmd=+1`, assigns -1 on GRASP and +1 on RELEASE, and passes this
number on every translation. LiberoWorldBackend starts at -1, but overwrites
its gripper command with that number. Its explicit close/open use +1/-1.
This polarity mismatch predicts unintended close on initial translation and
unintended open on translation after GRASP. Experimental isolation is pending.

The existing `laya-runtime-vision-async/20260922-173221/episodes.jsonl` has two
MV_FWD actions: finger gap 76.4455 → 20.8133 → 1.1950 mm. Their simulation
duration is 0.4 s each. These are raw telemetry observations, not evidence of
visual task success (both success flags are false).

Jev revision `3bdad985b225aeccc39fbe5863c6eea2e81c515a` executes up to eight
environment control steps per primitive, ending early on success. Position
feedback targets the current TCP plus requested translation; rotation is sent
on the first step only. robosuite OSC left-multiplies the rotation increment,
so rotations are world-frame. Zero angular commands preserve the controller's
orientation goal. STOP delegates to Jev hold: current TCP target, retained
orientation goal, retained finger command, up to eight steps; it is not a pause.
The underlying MuJoCo substep count must be measured separately from eight
control steps. Reset already executes ten zero-delta/open control steps; residual
settling can still change measured position and finger gap.

## Temporal behavior

Geometry filters by capture simulation time. Arrival wall time is retained on
events but unused by the filter. In-window geometry is sorted by capture time;
duplicates are detected only among retained events, sequence regressions otherwise
enter geometry. BeliefStore rejects sequence regressions, but Runtime calls fusion
even when the store rejects an event. Episode identity is not checked by the store.

Pruning removes old events without advancing the original anchor, losing their
posterior contribution. Gate counters increase again during read-only estimates.
The age timestamp may advance on a gated-out measurement. Runtime only publishes
fusion on ingest, so decision-time position/covariance can remain at an old
reference time. Geometry has no control-validity status or maximum age.

Semantic fusion rejects regressing sequence numbers even when geometry accepts
the same event. Its evidence decay does not reliably transfer mass to unknown.
Publishing fusion resets semantic capture time to now and renews TTL. The direct
BeliefStore expiry path raises unknown without renormalizing. Geometry and semantics
can therefore represent different evidence histories with no mismatch indicator.

## Active paths and privilege

The real runner instantiates LatestFrameWorker and MultiRateFusion for vision,
but never calls QueryTrackManager. `track_id` is the query string; tracking is
implemented but inactive. LocateAnythingProvider uses the first box, median depth,
capture transform and a fixed 0.75 s TTL. It emits no position covariance; fusion
silently substitutes 0.01 m² identity. The parser's score is 1 for any box, not a
calibrated probability. No model inference is needed for the current calibration.

VisionCandidateBuilder offers 11 unconditional tokens (including GRASP and RELEASE).
DONE is conditional, but the visual runner always supplies satisfied=false.
RuleProvider uses feasibility and token priority, with a small aligned/holding
condition; it ignores descriptions, risk and reason codes. Laya receives feasible
token descriptions and continuous/semantic/goal state, but not snapshot ages/flags
or candidate risk/reason fields. Existing RuleProvider would select GRASP repeatedly
on the unconditional visual vocabulary. Candidate policy work is deferred to P0-C.

Visual candidate generation does not call physics preview. The runner reads
world.features() for before/after evaluation logging and uses backend success for
termination, but does not put those object features into the visual belief.
Oracle candidates use predict_all and Jev contracts. Their preview defaults to -1
because World has no `_grip`; this can disagree with live execution after grasp.
That candidate-preview issue is recorded for the P0-C review, not changed here.

## Existing output and limitations

The runner writes per-action episodes.jsonl, a per-action summary.csv, summary.md
and a small manifest. It omits full belief snapshots, input event provenance,
resolved temporal config, low-level commands and execution contracts. It buffers
records until normal completion, so failures can lose records. This instrumentation
is deferred to P0-D except atomic contract evidence required by P0-A.

Latest available real evidence is the two-step async run above; earlier directories
are `laya-runtime-vision/20260922-163923` and `laya-runtime-smoke/20260922-161533`.
Old prose includes contradictory status claims. No E1 experiment has begun.

## Authorized plan

Calibrate atomic actions independently from the same restored simulator/controller
state; characterize settling before choosing tolerances; repair command preservation.
Then repair capture-time replay, posterior-preserving pruning, coherent admission,
TTL and explicit geometry/semantic validity metadata, with deterministic tests.
Run focused/full tests, lint and simulator calibration. Stop at Stage 1 human review.
P0-C/D and all formal experiments remain outside this invocation.
