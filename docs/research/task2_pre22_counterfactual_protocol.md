# Frozen Task2 pre-action-22 physical counterfactuals

One prescribed seven-branch batch examines the actual primitives corresponding to the already sealed [observed-surface diagnostic](../evidence/autonomous_research/task2_observed_surface_sweep_findings.md). Each branch starts from a fresh Task2 seed 1 / init 0 world and explicitly replays the original **22 completed actions / 176 recorded controls**, then executes exactly one registered primitive. This is retrospective counterfactual mechanics with an openly declared replay prefix, not a fresh sensor policy, hidden warm start or held-out validation. There is no archived simulator-state restoration, recovery, continuation, fitting, action filtering or new model call.

## Fixed source, schedule and identity

Source: `task2-box-point-boundary-run-01/episodes.jsonl`, SHA-256 `f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771`, producer `9de837c8a1348d8eac16bbe4616b40bcf0b0613f`. Boundary is **zero-based pre-action 22**, original selected token **MV_FWD**. The branch order is the original canonical order: **FWD, BACK, LEFT, RIGHT, UP, DOWN, STOP/hold**. Each is attempted at most once; no selection or order depends on a computed geometry score or physical result.

Pin the prior comparison's feature seal `2272dd32051a5965b1188360c993bf89e0b1a77d9f569b053351b5e65c8e9601` and complete feature JSON `4468151c3cf9e9abecb199131189fab02752ebdd7bf179234d30725c7bc9a55b`. Hash verification does not pass scores into execution; these artifacts are used only in the post-collection comparison.

Use unchanged `AtomicExecutor`, `LiberoWorldBackend`, World/controller, native observer, RGB-D source, strict 0.05 N contact convention and execution validators. Reuse the source preflight/provenance, exact native replay verifier, control recorder and read-only guards. Pin the original runtime, observer, task helper, source frame/perception and source capture hashes; require source package versions, stepping sources, clean Jev identity and GPU4/EGL4 environment to match. Whole current wrapper commit differs by design and is separately frozen/reviewed.

Each World follows its normal benchmark reset/initial-state construction and **ten settling controls**. Those setup operations are disclosed separately from 176 replay controls and the final eight-control probe; they are not an archived trajectory-state restore. Do not call privileged phase routing or `prepare_world`. Oracle reads inherited from World/backend/executor remain evaluation/validation only.

Before physics, run actual-source/import preflight without constructing a world and obtain independent prospective PASS naming the exact clean harness commit. GPU4 must have zero reported utilization and no more than 100 MiB allocated at batch admission; preserve the `nvidia-smi` snapshot. Use only CUDA/EGL device 4 and touch no other process. Whole batch cap is **3,600 s**, seven fresh branches, no retries. An occupied GPU prevents physics admission; it is not a scientific failed branch.

## Exact prefix and FWD qualification

Require every fresh initial flattened state, returned own packet, geometry-ID group and complete native snapshot to equal the source, alongside byte-identical initial RGB/depth/K/T. Preserve all 176 exact raw commands; do not recompute them through a selector. Match every before/after flattened state and returned/previous own packet, all **8,800 native BEFORE/AFTER stage samples**, and all **23 initial/prefix RGB-D captures** against the source. Record actual native samples even when an equality gate fails.

At pre-22, additionally require exact controller-facing execution state and previous returned own packet. Record the explicit replay receipt and open-jaw retained command. No source snapshot, controller target, own pose or joint value is injected to repair a mismatch. Controller state/history arises only from fresh construction and the recorded controls.

Save the first branch's current assembled XML and fingerprint relevant compiled model arrays, dimensions and native options. Require that current reset-model identity in every other branch. This establishes within-batch current-model comparability, not historical XML/STL byte identity; exact prefix/FWD reproduction is separate empirical qualification. Do not start an extra scene-export or model-calibration experiment.

FWD is both the first registered branch and the original continuation qualification. Execute it through the unchanged executor and require its **eight commands, complete control state/own packets, all 400 native stage snapshots including contact/force/caches/fingerprints, full executor result and endpoint RGB/depth/K/T** to match the original action 22 exactly. Preserve any first mismatch and abort the remaining batch without repair/retry. Only after this qualification can subsequent branches be interpreted as registered counterfactual continuations.

## One complete primitive and STOP semantics

All six translations retain OPEN and request the existing 10 mm world-axis action. Each normal branch completes **eight controls × 25 native 2 ms integrations = 200 integrations / 0.4 s** even if raw contact or >0.05 N contact appears. The observer is passive; no contact-based exception, shortening, threshold-dependent steering or second action is allowed. Keep inherited early-success behavior unchanged; an unexpected shortened primitive is recorded as a count failure, not silently accepted.

The seventh branch is explicitly an **executed STOP/hold diagnostic**: `AtomicExecutor.execute('STOP')` calls backend hold/World `hold`, initializes its target from the current returned TCP position, retains the jaw command and executes the same eight-control horizon. It can drift or contact while dynamics continue; retain its target, all actual controls and unchanged hold validator.

This differs from the original point-approach loop's STOP semantics: selecting STOP there terminates before calling the executor, so there is no further primitive. Record that analytical interpretation without constructing an eighth world. Do not count executed hold as policy progress or claim that it reproduces the loop's physical behavior after selecting STOP. Its zero nominal geometric displacement is not a physical no-op assumption.

## Evidence, failures and report

Preserve complete native BEFORE/AFTER raw rows for prefix and probe, including all robot pairs, names, force vectors, integration states/fingerprints, wrist buffers and reported times. Report **raw contact presence** and **strict `normal_force_N >0.05`** separately; never relabel the threshold crossing as first raw onset. Include designated bottle, pad, other gripper, self, arm and scene interactions. Summaries are stage-separated and retain first raw/strong samples, pair sets and peaks. Complete raw rows remain authoritative. Cached-stage timestamps do not establish continuous-time onset or exact returned sensor time.

Record full executor validation, actual TCP delta/rotation, retained jaw command/aperture and endpoint own observation/RGB-D for each probe. A completed primitive with a validator violation is a measured branch outcome and does not suppress later independent fresh branches. A source/identity/invariant mismatch, runtime error, nonfinite command, unexpected native count, wall timeout or partial primitive aborts the batch, preserving completed/missing branches and first failure without retry. There is no within-branch recovery or continuation after the endpoint.

On a fully completed batch, expected registered counts are **1,232 prefix controls +56 probe controls**, **32,200 integrations /64,400 native stage samples**, and **168 captures**, plus seven standard resets/ten-control settling sequences. The chained journal distinguishes each physical branch and prefix/probe step.

After sealing collection, inspect actual branch endpoint RGB images and report all seven outcomes in canonical order: raw pairs, threshold pairs, validator outcome, motion/proxy-distance progress and relation to the **already frozen inner/full current/endpoint/sweep flags**. No post-outcome margin, mask, threshold, score change or selected subset is permitted. Distinguish measured absence of contact over this 0.4 s fixture from environmental clearance, successful future approach, grasp readiness or a validated safety filter. Hold is compared separately from analytical loop termination. Preserve failures and incomplete qualification plainly.

Entry: `python -m embodied_runtime.experiments.task2_pre22_counterfactual --preflight --output RECEIPT.json`, then `--output RUN --review REVIEW.md` with `CUDA_VISIBLE_DEVICES=4 MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=4`. Complete all frozen checks and independent review before the one batch.
