# Run and inspect the live engineering demonstration

2026-09-23 successor to the [historical demo report](engineering_demo.md), on
`feat/mujoco_demo`. This is engineering instrumentation and communication work.
No shared runtime, CDS, provider, gate, executor or research interface was changed.

This records the inspector/connectivity milestone. The non-oracle embodied loop
and asynchronous smoke already existed before this branch. See the
[feedback successor](closed_loop_demo.md) for the corrected task-directed goal,
cross-decision audits, final sensing and the next bounded live episode.

## Start here

Open the new local [evidence inspector](../runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/demo.html).
It contains sensor/endpoint images, exact recorded API arguments, the offered
candidate order and vetoes, raw Laya output and consumed tokens, validated intent,
actual controls, physical measurements, failures and provenance. Native expandable
sections work offline; no web service or model is needed to view the HTML.

Also available: [video](../runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/demo.mp4),
[trajectory report](../runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/demo.md),
[derived evidence](../runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/demo-evidence.json),
[raw records](../runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/episodes.jsonl),
and [control replay](../runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/replay-check.json).
These are ignored local artifacts; they are not included in a clone.

## Run in the existing environment

From `laya-mujoco-demo`, check `git branch --show-current`, `git status --short`
and `git rev-parse HEAD`. The expected branch is `feat/mujoco_demo`.
See [server setup](server_setup.md) for the existing environment and upstream
repositories. The commands below use the installed local model weights; they
neither download weights nor change dependencies. Select an available GPU.

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
V=/home/junhongli/miniforge3/envs/locateanything/bin/python
DEMO_OUT="runs/engineering-demo/live-$(date -u +%Y%m%dT%H%M%SZ)"

CUDA_VISIBLE_DEVICES=1 MUJOCO_GL=egl HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 "$V" \
  -m embodied_runtime.experiments.engineering_demo \
  --output "$DEMO_OUT" --steps 4 --seed 1 --init-state-id 0

MUJOCO_GL=egl "$V" -m embodied_runtime.experiments.engineering_demo \
  --output "$DEMO_OUT" --replay-check

"$P" -m embodied_runtime.experiments.demo_report --output "$DEMO_OUT"
# Optional: GIF, MP4 (when ffmpeg is installed), contact sheet and Markdown.
"$V" -m embodied_runtime.experiments.demo_report --output "$DEMO_OUT" --media
```

Open `demo.html` in that directory. The report commands require NumPy and Pillow;
no model weights, CUDA, LIBERO environment or running simulator are needed.
`engineering_demo --render-report` remains an alias for the media report path.
Collection requires a **fresh** output directory and refuses an existing one.
The bounded demo accepts 1–8 actions and defaults to a 300-second timeout. The CLI
also exposes checkpoint paths, LIBERO root/config directory and device overrides.
A new attempt must use a new directory, including after a failure.

Console lines prefixed `[demo:...]` show sensing boundaries, all offered tokens,
forced-singleton status, proposed source/token, validated source/token and fallback
reason, actual control count/TCP motion, evaluator-only gripper/drawer/contact
measurements, failures and termination. Raw evidence is persisted before these
messages are printed. A closed console pipe does not abort execution.

## Read the evidence

1. **World and sensors:** actual RGB-D, intrinsics and camera transform, query,
   detector output, admitted observations and full visual belief. The unchanged
   live estimator uses the first query box and interior median depth. It is not the
   research pilot's common-referent estimator. Sensing pauses the simulation.
2. **What Laya received:** compact state and question arguments, canonical source
   audit and actual consumed token IDs. JSON object keys in raw records are sorted
   for hashing; offered option order is recovered from the canonical candidate list.
   No oracle target/contact/progress, effects or history enter the visual input.
3. **Available choices:** every offered token, nominal meaning, returned probability,
   and the gate's excluded tokens/reasons. Natural soft candidate metadata remains
   audit-only. Probabilities, covariance and semantic confidence are uncalibrated.
4. **Decision to executor:** proposed token/source, raw response, validated intent,
   explicit fallback reason and measured low-level controls. A forced singleton
   or STOP fallback never counts as a verified Laya execution.
5. **Physical outcome:** endpoint frame, measured TCP displacement, gripper opening,
   contract flags and before/after drawer/contact/success readouts. Simulator
   measurements are labeled evaluator-only and are separate from model inputs.
6. **Failures and reproducibility:** unfinished attempts, missing outcomes, all
   recorded failures, termination, configuration, invocation/environment, model
   content hashes and code/upstream identities. Report-generator source hashes are
   recorded separately from the original collection manifest.

The inspector checks the raw hash chain, snapshot/capture/trajectory identities,
reconstructed visual model input, token consumption, raw response versus proposal,
causal stage order, validated intent identity/membership/expiry, and saved trajectory
commands/counts versus executor evidence. A verified chain does not require task
success or a clear contract flag: those are separate physical outcomes shown beside it.
It establishes recorded connectivity, not independent attestation of a machine/model.

Interrupted execution is **outcome unknown**, even if a command intent exists.
Startup/model failures with no completed actions still produce an HTML report when
the complete raw records are intact. Semantic gaps are displayed as audit issues;
media generation stops at the inspector when attempts have such gaps or the run has
no termination record. Corrupt hashes,
missing referenced artifact files or an unterminated JSONL tail cause explicit
verification failure. Preserve the original files; `experiments.summarize` can derive
recovery CSVs from complete lines of an interrupted log. Never repair the raw log to
make a run appear complete. A missing termination remains visible as an incomplete run.

Replay status includes whether its `raw_source_sha256` matches the current log.
Replaying **recorded controls** is not another independent Laya policy rollout.
Media uses real recorded frames, motion at 0.5x, shortened decision pauses and
explicitly labeled action-end telemetry during those pauses. Do not infer a model
rationale from a selected action.

## Verified new run

Fresh output: `runs/engineering-demo/top-drawer-init0-seed1-inspector-v01/`.
Collection and replay both exited 0. This was one new live run, with no retries or
policy tuning. Code baseline: `eddbcde04649419d8d5d44e62e433882578328eb` plus the
working Python source hashes preserved in its manifest. Subsequent presentation
edits are not the collected policy; the raw run retains its original source identity.
Console and replay logs are retained beside the run directory as `.console.log`
and `.replay.log`.

| Evidence | Result |
|---|---|
| Task / actual benchmark reset / seed | `top_drawer` / `init_state_id=0` / `1` |
| Genuine Laya choices | GRASP, RELEASE, GRASP, RELEASE |
| Offered choices at each boundary | 10 natural permitted tokens |
| Raw response → validated intent → saved controls | All four chains verified |
| Singleton / fallback / failure / contract flags | None |
| Consumed tokens | 591, 594, 588, 594; no clipping |
| Controls / simulation time | 32 / 0.5 → 2.1 s |
| Finger gap, mm | 76.45 → 20.81 → 57.43 → 20.57 → 57.43 |
| Remaining drawer opening | 151.659 mm throughout |
| Target contact / task success | False / False |
| Control replay | 37 boundaries, maximum recorded state error 0 |

Raw log SHA-256:
`af65adf39abb43fb704312db8bf80911cb6ae2bec83173c4c0f1b479a457292b`.

The new run confirms the **model-to-actuator pipeline is connected and executable**.
It does **not** demonstrate useful drawer manipulation, task competence, calibrated
perception, asynchronous robustness, decision sufficiency or research readiness.
The research gate remains unchanged; no formal E0 was started.

The historical v01 artifact was also inspected successfully from a separate local
copy at `runs/engineering-demo/historical-v01-inspection-copy/`. That copy is a
compatibility check, not a new rollout; the original evidence in the integration
worktree was left intact.

Verification: **254 tests passed**, including 18 demo tests; ruff, compileall and
`git diff --check` passed. Failure regressions cover unknown execution outcome,
forced singleton, validation fallback, raw-choice/control mismatch, injected oracle
progress, stale replay identity and corrupted artifacts. The annotated contact sheet
was visually inspected. Browser rendering was not automated in this environment.

## Share a reproducible artifact

Share the entire run directory, including `episodes.jsonl`, `manifest.json`,
`resolved_config.yaml`, `frames/`, `trajectory/`, `replay-check.json` and generated
reports/media. Include the console/replay logs and this branch's source changes.
HTML embeds its images and evidence for presentation, but the raw arrays and chained
records are needed for independent inspection. Model weights remain external;
match the recorded model content IDs rather than assuming an equivalent path.
A code clone alone is not an evidence bundle.
