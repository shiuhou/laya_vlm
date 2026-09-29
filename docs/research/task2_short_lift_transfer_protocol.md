# Frozen BOX-track transfer to the archived visual executor 10 mm lift

One parent-authorized offline transfer uses the successful existing
`local-grasp-interface-run-02` archive. Run01 remains a zero-physics setup/import
failure; it is never substituted or erased. No new physics, model call, render,
FK, tracker variant, seed selection, smoothing, threshold fitting, classifier,
reinitialization, retry or additional movement is allowed. This tests transfer
to the actual visual atomic executor and shorter observation horizon. It is
not a clean amplitude-only ablation of the earlier native three-lift archive:
the lift executor, total displacement, control sequence and horizon differ.

## Admission before outcomes

Pin captures SHA-256
`1fa0469493a2b61f9c4a304fb323470680b5b1369ab501a14410bf76d6859b52`,
sensors `f3eead6a1556e2bbb64ea095aca6c251c6df7e95797099510d5aeb52fe662b58`,
sensor seal `2ac164126dcd9ca32e851c97da90db29657c0a7f0c6bf4a464cdd68862fd1326`,
and journal `9347eab2f1b48fe3799ccfbc3164f60406b6451bd194819ef66632df7d6464bb`.
The journal is hashed, never decoded to recover evaluator state. Admit exactly
30 captures per arm: reset0; approach1–13 (after steps0–12/control7);
close/STOP14–21 (step13/controls0–7); actual MV_UP22–29
(step14/controls0–7, nominal10mm). Require all60 NPZ hashes against source
capture manifest and sensor seal, 384×384 RGB/depth, finite3×3 K and4×4 T.

Require all first14 RGB/depth/K/T arrays per arm to equal the corresponding
original paired-observability prefix, and both arms' first14 sensor frames to
match. Initial frame SHA-256 remains the exact sealed BOX input
`3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`.
The saved BOX support remains all492 ordered integer seeds in
`[212,169,224,210)`, including initially outside-proxy seeds. No mask contents,
contact rows, object pose, target coordinates or evaluator labels enter sensor
admission, tracking or motion computation. Preflight performs hash/schema,
source-prefix equality and synthetic coordinate checks only: no archived LK,
projection, displacement or transfer membership outcomes.

Reuse unchanged single-seed `point_temporal_probe.track_lk` SHA-256
`86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36`
and OpenCV4.11.0 frozen settings. Retain the nearest-center association helper
SHA-256 `b95245bab639fac6a54359dd51020b2b40d0fd5e23f71fb7d1b7020b2590c855`.
Its componentwise `floor(x+0.5)` follows independently checked integer
array-index centers; exact half ties choose the higher index. A synthetic
OpenCV check and analytic epsilon/half-tie/bounds tests precede outcomes.
Backprojection separately retains `(selected_index+0.5)` and inclusive
0.01–5m valid depth. No depth interpolation or camera convention change.

## Fixed computation and unknowns

Call the original tracker once per seed per arm on all30 RGB frames. Preserve
all29,520 ordered rows, native attempted coordinates, statuses, errors and
forward/backward residuals. Native failure is permanent; later rows stay
unknown, without recovery or a residual threshold. Unknown or invalid depth
retains explicit status/null without changing native tracker status. All
492 seeds stay in each frame's denominator; no label-conditioned cohort.

Own TCP comes only from the exact saved `(arm,step,control)` sensor mapping.
This source has no initial own-TCP packet: capture0 own TCP and its timestamp
are explicitly null. Do not infer it from initial evaluator state, run FK,
read/borrow the earlier archive's endpoints or substitute reset calibration.
There are no initial-relative motion metrics. The only fixed reference is
preclose capture13; all relative metrics are absent before13. At/after13,
compute current surface-point displacement, its z and3-D norm, and the z and
3-D norm of point displacement minus saved own-TCP displacement. Missing
current/reference surface stays missing. Report count, missing count, median,
q25/q75 and fixed reference-surface-valid count. All observations are dependent
pixels, not492 independent trials. Identity and holding remain unknown.

The first14 RGB frames match the original archive, so causal deterministic LK
should produce exact native-prefix agreement. Compare all nine native fields
for each of492×14 rows/arm to the sealed original native rows. This comparison
never repairs, substitutes or selects tracks. Preserve every disagreement.
Complete and seal all sensor rows, summaries and prefix-agreement records;
if any native prefix differs, retain the complete batch and record failure,
stop before evaluator, and do not retry or change settings. Unexpected source
or runtime failure similarly preserves partial evidence with no retry.

## Evaluator and report

Only after full sensor seal, successful termination and exact29,520-row check
may a separate evaluator load the60 archived bottle masks. Use the existing
proxy-membership function at each selected sample index. Keep initially
outside, unknown and observed departures after earlier True distinct. A proxy
membership is not surface ownership, confidence, identity or a holding label.

Report all30 per-capture survivor/depth/proxy counts and capture13–29 motion
curves with fixed492 denominators. Fixed raw RGB/location checkpoints are
0,13,21,29; inspect actual lift RGB at22–29. Inspect first observed departure
overall, and separately the earliest observed adjacent True-to-False transition
within the lift (current capture>=22), with ties by lowest seed ID. If absent,
report null. Inspect the adjacent original RGB and limited proxy overlay for
those witnesses; never choose a repaired seed. Native first failure and unknowns
remain explicit even if null. No fitted co-motion threshold, discrimination
score, generalization or success claim follows from medians. Sensor cue strength
is reported descriptively; weak or failed transfer produces no retuning.

Preserve provenance, source read times, unknown exact RGB/depth sample/cache
times, initial mixed support, raster/mask ambiguity, occlusion/slip and highly
dependent overlapping LK windows. Any comparison to the old large lift states
executor and horizon differences, and remains descriptive.

## Freeze and one execution

Freeze adapter, protocol and meaningful synthetic tests before outcomes. Use
`/home/junhongli/miniforge3/envs/locateanything/bin/python` for preflight and run.
Obtain independent PASS naming the exact clean freeze and source-only preflight.
Then execute the already-authorized single batch autonomously, followed by
separate post-seal evaluation and reporting. No further parent approval gate.

Entry point: `python -m embodied_runtime.experiments.task2_short_lift_transfer`
with `preflight --output RECEIPT`; `run --output RUN --preflight RECEIPT
--review REVIEW`; separately `evaluate --output RUN`. Freeze remains immutable
after outcomes; only reporting additions may follow. Full result and report
require independent audit before closing the condition.
