# Rendering and cache semantics: source audit

The source supports two distinct explanations for residual robot-edge depth
points: multisample raster readback and cached geometry that is not refreshed
after the final integration step. It does not identify their numerical
contributions at the registered witnesses. The standard recording path disables
collision-group rendering, so directly rendered collision-pad boxes are not
supported by that code path. Actual historical renderer settings were not
logged and remain unverified until an exact reproduction succeeds.

This audit only read code/assets, downloaded version-matched upstream source,
and constructed an empty generic MuJoCo model to inspect static defaults. It
performed no scene construction, rendering, recorded-state evaluation,
integration, mask change or policy work.

## Geometry groups

The original probe creates `World(render=True)`. LIBERO defaults to
`render_collision_mesh=False`, `render_visual_mesh=True`; robosuite reset
sets renderer option groups 0 and 1 accordingly. The expected option vector
is `[0,1,1,0,0,0]` after applying those flags to MuJoCo's defaults. The gripper
XML assigns the collision pads to group 0 and its three visual meshes to group
1. MuJoCo's scene builder skips disabled groups before constructing render
geometries. A light-gray pad-shaped RGB region is therefore not evidence that
the group-0 collision pad itself was rendered.

The capture adapter and original experiment code exactly match the source
hashes saved by the physical run. The jev-libero and LIBERO checkouts still
match its recorded commits and are clean. Installed dependency source is
fingerprinted in the audit. These checks support a code-path reconstruction;
they do not replace the missing historical context flag record.

## Raster depth is not guaranteed to be a center-ray sample

Installed MuJoCo 3.5.0 gives an empty model `vis.quality.offsamples = 4`.
No override was found in the relevant robosuite/LIBERO assets or caller code.
This is a default, **not a measurement of the historical framebuffer**.
The native renderer copies the requested sample count into its context, clamps
it to device capability, allocates multisample buffers, then queries the actual
sample count. The actual context value and sample locations must be logged in
the proposed reproduction rather than inferred from the request.

Version-matched upstream `render_gl3.c` enables `GL_MULTISAMPLE` for normal
rendering. `render_gl2.c:mjr_readPixels` resolves a multisample offscreen buffer
to a separate buffer with `glBlitFramebuffer(..., GL_NEAREST)` before reading
color and depth. This is not an analytic center-ray query. The source does not
establish that resolved depth is a mean, nearest surface or center sample; no
such interpretation is assumed. Edge RGB and depth can therefore require
pixel-footprint reasoning that an ideal-center silhouette test does not express.

The adapter makes separate RGB and depth render calls without stepping between
them, vertically flips both, converts normalized depth using the near/far
formula, and records camera intrinsics/extrinsics. Its square 384-by-384 frames
avoid the width/height argument-order ambiguity in the camera helper. The
pixel-center convention remains fixed; it has not been shifted to fit results.

## Cached poses versus recorded own positions

Robosuite's control loop calls `sim.forward()`, applies control, calls
`sim.step()`, then updates observables. MuJoCo `mj_step` computes forward
quantities and then integrates. It does not append another forward pass after
integration. The expected default Euler path therefore leaves kinematic
geometry associated with the pre-integration configuration until refreshed.
The actual model integrator and timestep should still be logged in the
reproduction rather than assumed from defaults.

The capture adapter does not call `forward()`. The existing render context
passes cached data to `mjv_updateScene`; the scene builder uses
`geom_xpos/geom_xmat` and the camera's cached pose. Context construction calls
`forward()` once, which is distinct from later captures on that same context.
The original recorder's unchanged-state check covers time/qpos/qvel, explicitly
excluding caches. Matching a capture timestamp to an archived joint packet
therefore does not prove that the renderer used FK of that packet.

These mechanisms are separable: hold copied caches fixed while changing only
MSAA for a render comparison, and independently compare those cached robot
poses with own-qpos FK numerically. Rendering a fresh-FK condition as well is
unnecessary for the first diagnostic and would add another image intervention.

## Evidence and next evaluator

The [portable source summary](render_measurement_source_summary.json) contains
ten local source hashes and numbered excerpts, repository identities, generic
defaults, seven upstream C source hashes, and the installed MuJoCo binary hash.
Raw downloads and failed initial network attempts are preserved at
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/render-measurement-source-audit-01`.
Upstream sources are pinned to the
[MuJoCo 3.5.0 tag](https://github.com/google-deepmind/mujoco/tree/3.5.0);
matching the version is not a binary reproducibility proof.

The [registered evaluator protocol](../../research/render_measurement_diagnosis_protocol.md)
requires byte-exact RGB/depth/K/T reproduction of both original captures and
exact prefix-state replay before any intervention. It then compares native
versus zero-MSAA rendering on copied unchanged caches, alongside a separate
own-qpos versus cached-robot projection comparison. No third mask variant,
margin, action gate or sensor-pipeline change is proposed.
