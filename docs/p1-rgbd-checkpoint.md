# P1 RGB-D checkpoint — 2026-10-05

**Capture, conservative geometry, tracking infrastructure and exact offline
replay are implemented. P1 task acceptance is NOT passed.** The first task
boundary is reliable drawer-front grounding: neither current diagnostic ROI
isolates a supported pushing patch. Cabinet-relative visual VERIFY is also not
established. No model inference, policy decision or manipulation was run.

The selected Qwen3-VL → Laya → RGB-D geometry / deterministic servo architecture
is unchanged. This checkpoint does not reopen architecture research or add a
pad/handle contract. P2 servo execution remains gated by P1 perception evidence.

## Frozen condition

Implementation branch: `feat/p1-rgbd-geometry`, from P0
`5d706bf697fe90bb3ad1517bdd121874fab4d36f`. Canonical capture and replay revision:
**`c6fe3aef5e712227f7e1b067920f8afc5acfde9f`**, clean at capture launch.
Following evidence/documentation commits do not modify this condition.

- LIBERO `top_drawer`, seed 1, benchmark init indices 0–24.
- `agentview` and `robot0_eye_in_hand`, **384 × 256**.
- Two captures per fresh reset; no simulator steps between them.
- The existing Jev World constructor applies ten zero-motion, open-gripper
  settling controls; these are declared in the manifest. There are **zero
  runtime actions after reset** and no archived-control initialization.
- Fixed manual diagnostic ROIs from init-0 RGB, explicitly unverified. They
  are not LocateAnything results, independent labels or a policy condition.
- All thresholds were frozen before the 25-init collection. No threshold or
  seed tuning was performed against the collection.

Exact configuration: [capture](../configs/p1_capture.json) and
[geometry](../configs/p1_geometry.json). Full local evidence:
`runs/p1/static-25init-20261005/`; fresh-process replay:
`runs/p1/static-25init-20261005-replay/`.

## Implemented interfaces and evidence boundary

| Component | Implementation | Behavior |
|---|---|---|
| Capture | `adapters/libero_rgbd.py`, `libero_sensor_env.py` | One render returns RGB + depth; both flipped once; height/width K order; capture-time camera transform into robot_base; narrow read-only sensing port |
| Robot evidence | `sensor_api.Proprioception` reused | Arm encoders, velocity and registered robot EEF FK; retained semantic gripper command; jaw width null with reason; no inferred holding |
| Geometry | `perception/rgbd_geometry.py` | Valid depth, 3D components, voxel sampling, seeded RANSAC/SVD, visible-boundary erosion, multiple canonically ordered grid points; raw rejection metrics retained |
| Association | `perception/visual_tracker.py` | Fixed appearance/context, local search/reprojection and depth/base gates; LOST/AMBIGUOUS break lineage; explicit reseed; delayed semantics require uninterrupted registered history |
| Recording | `perception/recording.py` | SHA256 arrays, strict R4 FrameBundles, append-only original/canonical identity mapping, sealed record count and hash chain; mixed episode/clock, corrupt or incomplete recordings rejected |
| Diagnostics | `plane_consistency.py`, `visualization.py` | Explicit assumed plane correspondence; raw angle/residuals and conservative uncertainty bounds; all projected candidates retained; amber means UNKNOWN |
| Probe | `experiments/p1_rgbd_probe.py` | Fresh capture or model/simulator-free replay; matched result comparison; source manifests, package/source identities and diagnostic images |

Geometry outputs position, camera-facing normal, position/normal covariance,
edge margin, EEF-relative errors, point density, source frame/calibration, tool
erosion, raw support/rejection counts and every point candidate. The calibration
floor is added once and never reduced by treating same-frame samples as
independent measurements. It remains an **uncalibrated engineering assumption**.
Reachability/swept-link feasibility remain unknown; no point becomes execution
usable merely because a plane fits.

Tracker association is not semantic identity verification. Confidence stays
null. Identical-lookalike substitution is unresolved; competing matches fail
closed. No tracker result is silently promoted into a target after loss.

The probe keeps fixed-ROI `diagnostic_patch` separate from tracked `patch`.
Only a TRACKED association can supply the latter's ROI; otherwise it contains
UNKNOWN and no candidates. Both raw diagnostics and rejections remain logged.

This is perception infrastructure and recording integration, **not a live
P0-state-store/servo control loop**. Continuous runtime publication, robot
swept-space certificates and physical cancellation/stopping remain P2 gates.

### What “no oracle inputs” means here

No target body/site pose, joint opening, collision/contact, segmentation ID or
official success enters perception. The capture manifest's
`oracle_inputs_to_perception=false` refers specifically to those **task/target
oracle fields**. RGB and depth are rendered sensors; K, camera attachment,
capture-time camera transform and fixed base use simulator calibration/setup.
EEF uses registered robot-owned FK. These are declared sensing configuration
and proprioception, **not experimentally validated physical-camera calibration**.
The consumer receives no World or execution capability.

## Observed results

The collection has **50 reset-camera views**, **50 FrameBundles**, **100 recorded
camera exposures**, and **50 different camera/RGB/depth hash combinations**.
Repeated exposures of a static scene do not add initial-state diversity or
temporal motion evidence. Each exposure has two ROI records: 200 total.

| Diagnostic | Result |
|---|---|
| Tabletop plane fits | 100/100 VALID |
| Drawer ROI fits | 44 UNKNOWN, 56 AMBIGUOUS, **0 VALID** |
| Agentview drawer | 38 insufficient support, 12 ambiguous components |
| Wrist drawer | 6 insufficient support, 44 ambiguous components |
| Association, all ROIs | 47 TRACKED, 150 LOST, 3 AMBIGUOUS; tracked cases are tabletop controls |
| Execution-usable candidates | **0** |
| Numeric inverse consistency | Maximum **2.266 × 10⁻¹³ px**; this is not external calibration validation |
| Fresh-process offline replay | **200/200 full records identical**, excluding only geometry/tracker computation durations; plane checks also identical |

The two tabletop fits have normal differences **0.09866–0.09943°** and maximum
centroid-to-other-plane separations **2.548–2.588 mm**. Their comparison remains
UNKNOWN in all 50 bundles: conservative normal/position uncertainty exceeds the
prospective engineering resolution. We did not relax these bounds. Table
correspondence is an explicit analyst assumption, not verified target identity.

Capture-process geometry time: median **102.61 ms**, p95 **196.55 ms per ROI**.
Tracker p95: **8.47 ms**. These are offline subcomponent timings, excluding
rendering, recording, numeric reprojection, dispatch and queue delay. They do
not demonstrate end-to-end 10 Hz. Even the per-ROI geometry p95 exceeds 100 ms.
Offline tracking evaluates at capture time; online freshness is not tested.

### Images inspected and first boundary

Both complete 25-init contact sheets and init-0 diagnostic crops were inspected;
another agent independently reviewed the init-0 RGB/depth crops. This is agent
visual review, **not independent human annotation**.

- Agentview shows a narrow outward-facing sliver mixed with drawer rim/interior,
  handle-like protrusion and background. Init-0 dominant component plane support
  is only 26.6%, so it is rejected.
- Wrist view is predominantly top-down cavity/top-visible surfaces and background.
  Init-0 has two sizeable depth components (7,524 and 6,651 points), so it abstains.
- Fixed cabinet body is globally visible, but no fixed reference track, closed
  offset or measurable flush relation is established. The table control is not
  that reference. Static repeats do not demonstrate moving-versus-fixed identity.

This proves **failure of the current unverified diagnostic grounding**. It does
not prove that no useful surface exists, that the cameras are inherently
inadequate, or that Qwen/LocateAnything/Laya fail; none of those models ran.

## Verification and remaining acceptance

**396 tests passed**, including the existing 279-test P0 regression selection
and new capture/geometry/tracker/recording/probe/diagnostic tests. Ruff and
`pip check` passed. Tests cover non-square camera math, one render/exposure,
whitelisted robot reads, persistent uncertainty floors, ambiguous components,
visible holes/tool erosion, source identity preservation, corrupt/mixed/tail
record rejection, candidate order in replay and conservative plane-bound checks.

The following P1 gates remain unmet:

1. Reliable target/part ROI and an actual interior pushing patch.
2. Observable fixed cabinet reference and drawer-relative VERIFY geometry.
3. At least 50 independently annotated evaluation frames; these static views
   are inputs for review, not completed annotation evidence.
4. Ten real temporal sequences with approach/perspective change, EEF occlusion
   and opening/closing boundaries; none were run.
5. Calibrated uncertainty coverage and measured continuous throughput/freshness.

The next work is target/reference grounding on this recorded evidence, then
bounded observation-sequence validation. Do not proceed to PUSH or substitute
official success for visual VERIFY. Keep the architecture, controller contracts,
model settings and historical privileged reference unchanged.

## Reproduce and inspect

Use the [P1 offline dependency lock](../requirements/README.md). Capture requires
the existing simulator inventory recorded in the manifest:

```sh
MUJOCO_GL=egl MUJOCO_EGL_DEVICE_ID=2 \
LIBERO_ROOT=/home/junhongli/projects/LIBERO \
JEV_LIBERO_CONFIG_DIR=/tmp/laya-p1-libero \
/home/junhongli/miniforge3/envs/laya-embodied/bin/python \
  -m embodied_runtime.experiments.p1_rgbd_probe --output runs/p1/new-capture

.venv-p1/bin/python -m embodied_runtime.experiments.p1_rgbd_probe \
  --replay-only runs/p1/new-capture --output runs/p1/new-replay
```

Outputs must be new directories. Replay validates original configurations,
recorded array/metadata identity and every non-timing output. `--no-images`
supports numerical replay without Pillow. No simulator package/model is imported
for replay. Exact floating-point equality was tested under NumPy 1.26.4; other
numeric stacks are not claimed equivalent.

Tracked [evidence index](evidence/p1/20261005/README.md) includes full raw geometry
and candidates, summaries, manifests, sheets, examples, complete-artifact hashes,
tests and one portable checksummed raw sensor sample. The full 64 MiB collection
remains local. Development smoke a/b/c and their replay records remain separate;
they are not extra replications or acceptance datasets.
