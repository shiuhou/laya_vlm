# Registered evaluator: native raster sampling and cached robot geometry

This is an explicit evaluator-only reconstruction and render diagnostic on
development captures already inspected. No runtime estimator, mask, margin,
threshold, policy, action gate or sensor pipeline changes. Scene geometry may
exist only inside the evaluator needed to reproduce the original images; it
must not be passed to own-body FK or exported as a sensor estimate.

## Exact baseline gate

Use the same frozen `coarse-initial-point-02` archive and the same pre24/pre25
RGB-D frames pinned by the two preceding proximity protocols. Start the
standard seed-1/init-0 top_drawer world with the original configuration and
EGL rendering. The physical source used GPU 4; the evaluator uses GPU 5 under
the coordinator's final allocation before measurement. Exact image gates must
still pass, with no device-switch retry. Count constructor/setup controls and MuJoCo stepping
separately from historical-prefix reconstruction. Do not disguise bootstrap
steps as zero dynamics. Replay exactly the first 200 archived control commands
(actions 0–24); do not execute any action-25 command or a new candidate.

Require the constructed initial state to match the archived initial state
exactly. Require each of the 200 commands' full flattened state before and
after to match its archive exactly. At pre24 (after 192 controls) and pre25
(after 200), capture through the original RGB-D adapter and require **exact
array equality for RGB, depth_m, intrinsics and camera_to_world** with the
original recorded frame. Save comparisons, native frames, context metadata
and full `MjData` copies at both boundaries. No intervention begins until both
capture gates pass. Any mismatch stops the run; preserve failure evidence.
No render repair, changed settings, relaxed tolerance or baseline retry.

After reconstruction, block all stepping and forward calls. Subsequent work
uses full `mj_copyData` snapshots in the existing simulator data object, with
no continuation or changed control. Verify exact equality of the selected
state, sensor and render-cache arrays across copying and each render. The
copy operation preserves full MjData; report which arrays are independently
checked rather than claiming a raw byte hash of the entire opaque structure.

## Actual configuration records

Log environment collision/visual render flags, context `geomgroup`, model
requested `offsamples`, context actual `offSamples`, framebuffer dimensions,
depth-map mode, actual model integrator/timestep, and native gripper/camera
cache poses. Record GL vendor/renderer/version and bound-framebuffer sample
count/locations if available. Missing GL introspection remains explicitly
unavailable; do not infer actual sampling from the requested count alone.
No contact labels, forces, target lookup or scene-identity query is used.

## Sole image intervention

Once both native gates pass, preserve their original `MjData` copies. Rebuild
only the existing rendering buffers with model requested `offsamples=0`, using
the context's buffer rebuild method that does not call `sim.forward()`.
Require actual context samples to be zero. Render each saved cached boundary
through the same RGB-D adapter. Verify time/qpos/qvel, all checked robot/scene
render-pose arrays and camera caches remain exactly unchanged. If the native
actual sample count was already zero, record that the comparison is degenerate.
Do not create an additional fresh-FK image condition or change geometry groups.
Enforce equality of native and intervention geometry groups, collision/visual
render flags, framebuffer width/height, depth-map mode, scene flags, integrator
and timestep both after buffer rebuild and after each capture. A non-sampling
configuration change fails the run rather than being reinterpreted.

Report native-versus-zero whole-frame RGB/depth differences and the fixed
witness samples below. A difference supports a sampling contribution; lack of
difference does not prove the mask or pixel identity correct. Preserve native
and zero frames and seal all numerical results before visual interpretation.

## Separate numerical cache comparison

Use the already sealed robot-only collision and visual calibrations and the
nine own-joint positions at each boundary. Compute pure NumPy FK without the
full model or object state. Compare its eight gripper geom poses and projected
vertices with the corresponding **cached** evaluator poses. Record position,
rotation, world-vertex and projected-pixel discrepancies. Use recorded camera
calibration. Do not render these fresh FK poses, compute a replacement mask,
classify contact, or use scene geometry in this comparison.

This separate comparison tests cache-versus-own-qpos geometry while native
versus zero-MSAA rendering holds the cache fixed. It is not a 2-by-2 sweep.
Both effects may coexist, and their presence need not fully explain every
residual witness. No physical-calibration or sensor-accuracy claim follows.

## Frozen witness set and output

Use the union of previously sealed old/new per-proxy nearest witness pixels,
without target-region selection:

| Boundary | Pixel `(x,y)` set |
| --- | --- |
| 24 | `(216,97)`, `(147,162)`, `(147,163)`, `(165,176)`, `(165,177)`, `(237,102)` |
| 25 | `(119,126)`, `(156,165)`, `(236,145)`, `(240,110)`, `(156,155)` |

For all eleven centers, retain raw RGB, optical depth and differences for the
complete fixed 3-by-3 neighborhood. Do not select the best neighbor after the
result. Show fixed witness crops only after output sealing. Source identity,
code/protocol hashes, exact baseline failures, copied-cache checks, actual
configuration, replay/setup counts, images and numerical comparisons are raw
evidence. All measurements are descriptive and evaluator-only. Occluded space
and residual pixel identity remain unknown.
