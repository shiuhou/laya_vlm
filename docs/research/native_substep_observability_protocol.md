# Native within-control observability: RIGHT and DOWN

Prospectively frozen before dynamics, 2026-09-27. Exactly two diagnostic arms,
`MV_RIGHT` then `MV_DOWN`, at the same archived pre-action25 boundary. The question
is whether contacts missed by after-control sampling accompany drawer movement
and translation residual within native controls. Temporal conjunction cannot
establish a sole cause. No executor, validator, controller, horizon, primitive,
gripper command, target, action selector or 2 mm translation tolerance changes.

## Sources, reset and exact continuation gate

Original source `coarse-initial-point-02/episodes.jsonl`, SHA-256
`e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf`.
Completed seven-arm reference `coarse-native-counterfactual-run-01/episodes.jsonl`,
SHA-256 `23a5e0ea9a59317ad843141a4ec0017958d0c180fdbc7c2aed90cf41697943fa`.
Reference code was frozen at `e13bc36`; this diagnostic lives in a separate
worktree. All reference scientific Python files, simulator repositories, installed
versions, benchmark/init0/seed1, original world point and candidate definitions
must remain unchanged. Its own protocol, code/tests and installed stepping-source
hashes are committed before preflight and any world/control.

Each arm starts a fresh top_drawer world, standard ten settling controls, then
the exact archived200 low-level prefix. Require exact initial and all prefix
before/after flattened states. Restore no archived simulator/controller snapshot.
Match preboundary native execution state, available robot proprioception and
evaluator endpoint. Preserve original before/after RGB-D and native trajectory
rendering/capture timing. Use GPU6 with CUDA_VISIBLE_DEVICES=6, MUJOCO_GL=egl,
MUJOCO_EGL_DEVICE_ID=6. No models, policies, selection or recovery.

Execute the unchanged `AtomicExecutor`/`RecordingBackend` once per arm: eight
native0.05 s controls, nominal10 mm translation, original open gripper/orientation.
Every generated command and every before/after control state/contact/available
returned robot sample must equal the corresponding seven-arm reference exactly;
check before the next control. Full executor result and both evaluator endpoints
must also equal that arm's reference exactly. Stop at any mismatch/infrastructure
failure, retain all evidence and missing arms; no rerun or threshold relaxation.
Contact/contract violations matching the reference are retained outcomes.

## Actual call path and read-only observation

Installed robosuite1.4.1 `MujocoEnv.step` calls `sim.forward()`, `_pre_action`,
`sim.step()`, `_update_observables()` each model timestep. Installed
`binding_utils.MjSim.step` calls `mujoco.mj_step(model,data)` once. LIBERO's
`mj_step1` is in reset, before diagnostic hooks are installed. Preserve this path.
Record the actual model integrator enum/timestep/control timestep at the boundary.

Wrap the existing Python `mujoco.mj_step`, `mj_step1` and `mj_step2` entry points
only during each native arm. Each wrapper observes before and after exactly one
original call with untouched arguments and return. No extra integration,
`mj_forward`, state assignment, render, measurement/cache refresh, controller
call or early `world.obs` assignment is inserted. Count native `mj_forward` calls
and retain their input time/qpos fingerprint; call the original exactly once.
Expected native path is25 `mj_step` calls per control,200 per arm; split calls or
other counts are recorded and fail the frozen path gate without substitution.

At each integrator boundary read direct time, qpos/qvel/qacc, ctrl, generalized
forces (applied/constraint/passive/bias/actuator/smooth), Cartesian applied body
forces, drawer joint/DoF, cached handle
geometry positions, and all native contact rows with geom IDs/names, robot and
drawer membership, position, signed distance and all six `mj_contactForce` values.
Retain zero/subthreshold rows and original strict greater-than1 N flags separately.
Force vectors use MuJoCo's native contact frame; no world-force conversion claimed.
Use read-only `mj_getState(mjSTATE_INTEGRATION)` fingerprints before/after snapshot
collection to check that observations leave the native integration state unchanged.

Before `mj_step`, contact/geometry caches follow the native forward/controller
path. After `mj_step`, qpos/time are advanced but derived contact/geometry/force
fields may represent earlier dynamics stages, depending on the recorded native
integrator. Do not call those cached values fresh endpoint geometry. Record last
native forward input identity explicitly; do not run an extra forward to repair
cache timing. The ordinary after-control contact rows remain separately available
and must equal the completed reference.

## Evaluation, review and bounds

Independent read-only protocol/code review by joint_interface is required before
dynamics. Test observation call counts, unchanged arguments/returns, failure
restoration, read-only state checks and stop-before-next-control mismatch behavior
without simulator execution. Offline audit checks hash chains, frozen identities,
the400 replay and16 native controls, both complete reference results, all400
integrator calls with800 snapshots, artifact hashes and timing/joint arithmetic.

Before/after cached rows can duplicate a physical contact; their count is not a
count of distinct contact events. Report all within-control contact rows/forces, first observed robot and nonhandle
contact, per-control direct drawer change and contact presence, full translation
residuals and native contract results for both arms. Report whether ordinary
after-control sampling misses contacts present at actual integrator boundaries.
Do not infer contact freedom between those finer samples or a unique mechanism
for tracking residual from coincidence. No live gate, controller modification,
new physical action, second seven-arm replication or further dynamics is included.
