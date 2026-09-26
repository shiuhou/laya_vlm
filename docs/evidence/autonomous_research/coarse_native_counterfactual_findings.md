# Seven native options at the first-contact boundary

At archived pre-action boundary25, none of the seven original options produced
both a contract-valid native execution and positive designated-handle approach
with zero sampled robot contacts. `MV_DOWN` alone met the sampled contact/progress
conjunction, but its translation residual was 2.114787 mm against the unchanged
2 mm tolerance. It also moved the drawer joint by 1.406205 mm despite zero
after-control contact rows. Therefore it cannot be called physically contact-free.
These results do not support treating selection or information as the only
bottleneck in this action pool at this state.

## Conditions and lineage

The [frozen protocol](../../research/coarse_native_counterfactual_protocol.md)
and implementation were committed as `812d99e5a20dbaccedbd05c3093e7fd37265e4ed`.
Preflight01 failed before loading LIBERO because of import order; its start,
failure and termination remain retained, with zero worlds/resets/controls/captures
or model calls. The sole setup correction was committed as `e13bc36` before
preflight02 and before any physical arm. Preflight02 passed and run01 completed
all seven arms without an infrastructure failure or retry.

Each arm created its own fresh top_drawer init0/seed1 world, performed the original
ten settling controls and replayed exactly the archived 200-control prefix. All
initial and prefix before/after flattened states matched exactly. Native
preboundary execution state and available endpoint robot proprioception matched.
The frozen world point was
`[0.003321375780614755,-0.06019141953353715,1.0961857009378837]` m;
initial designated-handle surface gap was 24.48619499135853 mm.

The original candidates ran in their original order, using unchanged
`AtomicExecutor`/`RecordingBackend`, eight 0.05-second controls per primitive,
10 mm translations or native STOP hold, and the original open gripper command.
There was no model, new policy, candidate selection, state restore or recovery.
The selected original `MV_RIGHT` continuation reproduced all eight commands,
states and contact lists, the full executor result and evaluator endpoint exactly.
Archived intermediate full robot observations/controller caches are absent; their
identity is not claimed. Recording the returned observation preserved native
`world.obs` assignment timing.

## All seven measured outcomes

Gains are before minus after distance, so positive means approach. Contact rows
are all robot-geometry contacts after each complete native control, including
zero/subthreshold forces. Translation residual is the norm of measured minus
nominal displacement; STOP uses the existing 1.5 mm hold tolerance.

| Arm | Nominal fixed-point gain (mm) | Measured fixed-point gain (mm) | Handle-gap gain (mm) | Sampled robot contact rows | Translation residual (mm) | Contract valid | Drawer joint change (mm) |
|---|---:|---:|---:|---:|---:|---|---:|
| MV_FWD | 4.207975 | 4.143665 | -0.036381 | 0 | 0.315646 | yes | 0 |
| MV_BACK | -5.528618 | -4.896673 | -1.492075 | 0 | 3.032152 | no | 0 |
| MV_LEFT | -6.746793 | -6.359075 | -0.557487 | 0 | 1.380412 | yes | 0 |
| MV_RIGHT | 5.683326 | 5.069833 | -0.755405 | 5 | 1.650032 | yes | 6.844671 |
| MV_UP | -6.532713 | -6.207308 | -10.119414 | 0 | 0.962328 | yes | 0 |
| MV_DOWN | 5.418954 | 5.313088 | 8.466454 | 0 | 2.114787 | no | 1.406205 |
| STOP | 0 | 0.091299 | -0.674366 | 0 | 1.238022 | yes | 0 |

Both violations were `translation_error`; there was no rotation violation.
`MV_RIGHT`'s five contact rows were all nonhandle contacts, maximum normal force
4.839180784535814 N. It alone crossed the original strict greater-than-1 N flag.
The zero-nonhandle-contact and no-contact-above-1 N positive-gap lists also contain
only `MV_DOWN`; the contract-valid zero-robot-contact positive-gap list is empty.
No outcome had official success or valid designated-handle contact.

Cached handle-center displacement was 6.826182 mm for RIGHT and 1.402021 mm for
DOWN, zero for the other arms. Those cached geometry displacements are distinct
from the direct drawer-joint changes in the table. Native measurement/cache timing
was retained; no fresh physics forward replaced it.

The fixed-point metric and the handle-gap metric disagree concretely: FWD and
RIGHT improve the point distance while worsening the handle gap. DOWN improves
both but misses its native translation contract and moves the drawer. STOP is an
active hold over advancing simulation; it is not a zero-dynamics control.

## Audit and bounds

The offline audit passes the raw hash chain, frozen preflight/code/protocol,
initial states, seven exact archived prefixes, new control/state chains, full
RIGHT continuation equality, raw-contact classifications, direct joint arithmetic,
14 before/after RGB-D artifacts and seven native eight-frame trajectory artifacts.
It checks 1,456 prefix/arm control pairs: 1,400 diagnostic prefix controls and
56 counterfactual controls. There are seven primitives and zero model calls.
The three relevant experiment test suites passed 24 tests before execution.

After-control sampling leaves within-control contact onset and disappearance
unresolved. DOWN's direct drawer motion makes that limitation material, rather
than merely hypothetical. Its zero sampled rows do not establish continuous-time
contact freedom, and drawer movement alone does not identify its cause. An
independent raw-evidence review is retained in the separate
`laya-information-boundary-review` worktree, commit
`a9750371a2823b78f6f53dd1b3d119e4de52bfeb`: checker
`embodied_runtime/experiments/information_boundary_audit.py`, report
`docs/evidence/autonomous_research/information_boundary_review.md`, and results
`docs/evidence/autonomous_research/information_boundary_audit_summary.json`.
That review used its own standard-library/NumPy implementation without producer
helpers or physics reruns, and passed all 2,971 record hashes, prefix/arm chains,
artifact lineage and metric/contract arithmetic.

This is one-step evaluator-only evidence at one archived state. It neither proves
global unreachability nor licenses a live gate, a different primitive, a changed
pose/horizon, or a manipulation policy. The next useful diagnostic is native
within-control contact/cache timing and tracking residual, with exact reproduction
required; it must not relax the executor contract based on these outcomes.

Raw evidence root:
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.
Retain `coarse-native-counterfactual-preflight-01`, `-preflight-02`, `-run-01`
and their sibling stdout/stderr logs. The compact
[summary](coarse_native_counterfactual_summary.json) records identities, all seven
metrics and exact contract results.

| Identity | SHA-256 |
|---|---|
| Original source episodes | `e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf` |
| Seven-arm episodes | `23a5e0ea9a59317ad843141a4ec0017958d0c180fdbc7c2aed90cf41697943fa` |
