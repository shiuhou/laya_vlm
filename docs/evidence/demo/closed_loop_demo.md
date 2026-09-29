> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# An auditable embodied loop that still fails to make task progress

2026-09-23, `feat/mujoco_demo`, after `84abdb844151aeb3fa89f346390921e2b4b2c721`.
Engineering observation and execution evidence only; no formal E0 or interface study.

## Goal and prior capability

The goal is a **sustained, interpretable, task-directed embodied loop**: world changes
must reach the decision state, inform useful Laya choices and lead to measurable
physical task progress. Laya selects atomic robotic decisions; deterministic code
owns geometry, validity checks, physical semantics and low-level motor control.

This branch did not create the embodied loop from zero. Earlier work already ran:

```text
LIBERO RGB-D -> LocateAnything -> 3D observation -> MultiRateFusion / BeliefStore
            -> Laya -> validation -> AtomicExecutor -> MuJoCo -> next observation
```

The [historical handoff](../../archive/historical_handoffs/handoff.md) and [Stage 0 audit](../../archive/historical_handoffs/stage0_audit.md) record the
non-oracle path and two-step asynchronous `vision_laya` smoke. Its local raw artifact,
`/home/junhongli/runs/laya-runtime-vision-async/20260922-173221/`, was inspected again:
both rows have `oracle=false`; both choices are MV_FWD. Step 0 consumed capture 1;
step 1 continued with no newly completed visual result (`vision_capture_seq=null`,
`vision_completed=1`). This demonstrated that slow perception need not block control.
It did not demonstrate task success, and its older input/candidate configuration is
not equivalent to the current compact synchronous demo.

The [four-action inspector milestone](demo_runbook.md) made existing capability
cleaner, reproducible, observable, replayable and auditable. Those results and raw
artifacts are preserved. The broader task-directed milestone is **still not met**.

## What inspection found

The four-action run already refreshed RGB-D, proprioception and fused state before
each decision. It was not a prerecorded decision sequence or a disconnected sensor
path. Measured gripper opening, TCP coordinates, relative geometry and quality values
changed in the next model input. Yet Laya selected only free-space GRASP/RELEASE.

At roughly 218 mm sensed TCP-to-target distance, all six translations remained
permitted. The existing validity gate does not certify that GRASP is a useful or
contacting action. Following GRASP, the measured joint opening caused
`gripper_already_closed` to veto another GRASP. Following RELEASE, the retained OPEN
command and unknown holding state caused `holding_state_unknown` to veto RELEASE.
Thus every alternating choice also coincided with removal of the previous choice.
That is **not isolated evidence that Laya interpreted the changed world usefully**.

The observable blocker is useful action selection under the current model/interface:
fresh feedback and available movement choices did not produce an approach or task
progress. The episode does not distinguish a model limitation from insufficient
representation, nor prove that any particular added field would fix it. Empty
previous-action history is documented, not promoted to a causal explanation.
We did not add history, change prompts, tighten gates into a task script, rank actions,
insert effects or alter CDS to manufacture a more successful-looking run.

## Small engineering change

- `demo_sensing_complete` records the capture, admitted visual/proprioceptive events
  and preceding executed step at each boundary.
- `--observe-final` performs one final RGB-D/LocateAnything/proprioception update after
  the action budget or success, with **no additional decision or physical action**.
  The existing synchronous schedule and model presentation otherwise remain intact.
- The offline feedback audit links an execution endpoint to its fresh next capture,
  robot observations, used geometry/semantic fusion evidence, next belief, audited
  model input and next execution. Store admission and fusion use are distinct checks.
- The inspector shows changed model fields, newly allowed/vetoed tokens and reasons,
  whether the previous choice was gated out, and evaluator-only physical progress.
  The video includes explicit post-action sensing intervals and the final observation.
- Interrupted/mismatched feedback remains an audit issue. Expected terminal captures
  are identified separately from unassigned or unfinished sensing attempts.

This is instrumentation of the existing loop, not a replacement provider, executor,
safety policy or shared decision interface. Model history remains empty; effects
remain absent. Only the live gate's natural permitted atomic tokens reach Laya.
Simulator drawer/contact/progress values remain evaluator-only. A gate pass is not
collision approval or a guarantee that the chosen action is useful.

## New bounded episode and preserved failure

Two startup attempts were made; there was one completed model-driven episode.

| Artifact under `runs/engineering-demo/` | Outcome |
|---|---|
| `top-drawer-init0-seed1-feedback-v01/` | GPU 1 memory contention caused LocateAnything loading to fail before any capture or decision. Exit 1; raw failure, termination and HTML report preserved. |
| `top-drawer-init0-seed1-feedback-v02/` | Same code/model/task settings, GPU 6, eight decisions plus final sensing. Exit 0; no policy tuning or trajectory retries. |

Both have adjacent `.console.log` files. The completed run also has an adjacent
`.replay.log`. GPU selection is recorded in `demo_invocation`; source/model hashes,
benchmark initial-state identity and resolved configuration are retained. The failed
startup is an infrastructure retry, not a discarded manipulation outcome.

Open the [episode inspector](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/demo.html),
[video](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/demo.mp4),
[trajectory report](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/demo.md),
[raw records](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/episodes.jsonl),
[derived evidence](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/demo-evidence.json),
and [control replay](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v02/replay-check.json).
The [failed startup inspector](../../../runs/engineering-demo/top-drawer-init0-seed1-feedback-v01/demo.html)
is also available. These are ignored local artifacts, not files included in a clone.

| Measurement | Completed episode |
|---|---|
| Task / benchmark reset / seed | `top_drawer` / `init_state_id=0` / `1` |
| Laya choices | GRASP, RELEASE, GRASP, RELEASE, GRASP, RELEASE, GRASP, RELEASE |
| Natural permitted choices | 10 at every decision, including all six translations |
| Executed translations | 0 |
| Sensor captures | 9: eight decision boundaries and one final observation |
| Verified feedback deliveries to subsequent Laya executions | 7 of 7 |
| Choice changes coinciding with prior-choice veto | 7 of 7 |
| Controls / simulation time | 64 / 0.5 → 3.7 s |
| Sensed target distance in model inputs | 218.049 → 218.101 mm; not ground truth |
| Drawer remaining opening (evaluator only) | 151.659 mm throughout |
| Net drawer closure / target contact / task success | 0 mm / false / false |
| Forced choices / fallbacks / execution contract flags | None |
| Actual consumed tokens | 591, 594, 588, 594, 589, 594, 590, 591; no clipping |
| Control replay | 73 boundaries, maximum recorded state error 0 |

The final RGB-D and joint readings were obtained at 3.7 s, after the last RELEASE;
they were not followed by a fabricated ninth decision. Approximate wall duration:
42.9 s including startup/hashing; this is not a latency benchmark. Eight decisions
are a bounded continuation check, not validation of long-horizon robustness.

Raw completed-run SHA-256:
`bf3f990c19d0ea576d43f523de2a13d81c9b49ed922caf4c94aa4a64aee8eeb3`.
The original source hashes remain in the run manifest; report-generator source
hashes identify subsequent presentation edits separately.

## Claims and remaining failure

Verified: genuine Laya decisions repeatedly execute; their physical robot outcomes
are reobserved; fresh visual evidence is used by fusion; updated robot/relative state
and natural candidates reach the next audited Laya input. Failure is now inspectable
across boundaries rather than only action by action.

Not demonstrated: useful task-directed sensitivity to the world, an approach to the
handle, drawer contact or measurable drawer progress. Gate-induced availability
changes confound an interpretation of the alternating choices as learned adaptation.
The failure is not hidden by substituting a script or adding oracle target information.

No claim follows about decision-interface validity, a sufficient state abstraction,
perception accuracy, general safety, asynchronous robustness or E0 readiness. This
run deliberately pauses simulation for inference; prior asynchronous evidence keeps
its own scope. Replay repeats recorded controls, not independent model decisions.
No new research hypothesis or formal experiment is promoted by this engineering run.

## Reproduce and verify

Use a free GPU and a **fresh output directory** for every attempt. Models and upstream
simulation dependencies are the existing local installations; see [server setup](../../../README.md#environment).

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
V=/home/junhongli/miniforge3/envs/locateanything/bin/python
DEMO_OUT="runs/engineering-demo/feedback-$(date -u +%Y%m%dT%H%M%SZ)"
CUDA_VISIBLE_DEVICES=6 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$V" \
  -m embodied_runtime.experiments.engineering_demo \
  --output "$DEMO_OUT" --steps 8 --seed 1 --init-state-id 0 --observe-final
MUJOCO_GL=egl "$V" -m embodied_runtime.experiments.engineering_demo \
  --output "$DEMO_OUT" --replay-check
"$V" -m embodied_runtime.experiments.demo_report --output "$DEMO_OUT" --media
"$P" -m pytest -q tests/test_demo_feedback.py tests/test_engineering_demo.py
"$P" -m pytest -q
"$P" -m ruff check .
"$P" -m compileall -q embodied_runtime tests
git diff --check
```

Verification: **30 focused tests, 266 full tests passed**; ruff, compileall and
whitespace checks passed. Tests reject stale or mismatched endpoints, rejected or
unused visual evidence, inconsistent next beliefs and broken feedback lineage.
Scheduling tests verify terminal observation after both budget exhaustion and success,
no extra action, and preservation of completed actions if terminal sensing fails.
The real eight-decision episode and 73-boundary control replay both exited 0.
The old four-action artifact remains readable; its three feedback deliveries and
zero drawer progress can also be reconstructed without altering its raw records.

Share the entire run directories, including raw chained logs, RGB-D arrays,
trajectories, manifests, reports/media and adjacent console/replay logs. Keep the
failed startup alongside the completed episode. None are committed to Git.

No shared-component fix was required. Changes are confined to demo runner/reporting,
feedback tests and framing documentation. Shared fusion, CanonicalDecisionState,
LayaProvider, gates, validation and executor semantics are unchanged. Demo tooling
can later be reviewed for `share_main` integration as one scoped engineering change.
