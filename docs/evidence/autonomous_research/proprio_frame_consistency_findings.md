# Stored proprioceptive frame consistency

The saved Task2 data empirically supports the reviewed fixed body-to-TCP
rotation. Treating the returned end-effector body quaternion as TCP orientation
produces about **90°** disagreement. Applying the known mount rotation reduces
the maximum residual to **0.045301°** across 240 saved sensor rows. Exact sample
times differ or are unknown, so this is descriptive agreement with stored
matrices, not same-time calibration validation.

No mixed body/site rigid pose was found in the inspected current model-facing
path. The backend's proprioception and canonical state omit orientation; all
240 guarded model-state/effect comparisons are unchanged by poisoning the raw
body quaternion. The four actual execution validators instead use saved native
site matrices and reproduce. This omission does not establish that orientation
is unnecessary for a grasp.

## Evidence and fixed arithmetic

The [audit protocol](../../research/proprio_frame_consistency_protocol.md), code
and four synthetic tests were frozen at
`a083645bfb0cf4c2a5df79c31eb46713bb47b432`. All tests passed before the one offline
audit. No physics, model, rendering, new FK, successful-pose fit, action selection
or runtime edit was performed.

The static formula was already reviewed independently in `3065e87`,
`task2_point_tcp_pad_evidence_review.md`. This audit composes the saved fixed
`right_hand → right_gripper → eef → grip_site` calibration chain; it does not
derive the transform from observed target or successful grasp positions. The
body-to-site transform is translation `[0,0,0.097] m` and rotation `Rz(−90°)`.
Returned `robot0_eef_quat` is **XYZW for the right_hand body**; therefore
`R_world_site = R_world_body × R_body_site`.

Returned `robot0_eef_pos` already refers to the grip site. Its origin must not be
shifted by another 97 mm. The sensor records contain no independent world body
position, so body-to-site translation consistency cannot be empirically checked
here. That field remains unknown rather than being inferred from the very site
pose it would supposedly verify.

The audit retains all 240 local-grasp control sensor rows and checks their exact
lineage against the journal. Each has the returned quaternion and a previously
saved scratch-FK TCP matrix. All 30 primitive endpoints also retain native cached
site matrices, using native feature outputs for the first 13 primitives and
actual executor outputs for the last two in each arm. These populations remain
separate. No simulator state or matrix is recomputed.

## Absolute-frame comparison

| Saved comparison | Count | Minimum | Median | Maximum |
|---|---:|---:|---:|---:|
| Uncorrected body quaternion vs scratch TCP, degrees | 240 | 89.989773 | 89.999988 | 90.019717 |
| Mounted body quaternion vs scratch TCP, degrees | 240 | 0.000041 | 0.003643 | 0.045301 |
| Uncorrected body quaternion vs cached TCP, degrees | 30 | 89.998370 | 90.000005 | 90.000671 |
| Mounted body quaternion vs cached TCP, degrees | 30 | 0.000033 | 0.000837 | 0.010974 |
| Scratch TCP vs cached TCP, degrees | 30 | 0.000033 | 0.000818 | 0.010916 |
| Returned site position vs saved scratch site, mm | 240 | 0.000656 | 0.139275 | 0.697702 |

The saved wrist-frame and saved TCP-frame rotation matrices are elementwise
identical in all 240 rows, consistent with their calibrated identity relative
rotation. Their positions differ by a fixed site offset; no saved wrist position
is available for an independent positional comparison.

The corrected angular and positional residuals compare different stored
observation/cache paths. Returned sample timestamps are unknown; scratch FK was
recorded from current direct qpos, while native cached site geometry can retain
another stage. This audit neither isolates the cause of each residual nor aligns
samples, repairs observations, or replaces a validator's original matrix.
All calibration and saved simulator outputs share the same synthetic robot
model; this does not test physical calibration accuracy.

## Relative rotations and actual GRASP interface

For a constant mount C, `(R_after C)(R_before C)^T = R_after R_before^T`.
Consequently the body/site mount mismatch in an absolute pose cancels in a
same-frame world-relative rotation. The arithmetic reproduces this cancellation
to at most `5.56e-16` per matrix element across the four actual interventions.
It does not remove cache/timing differences between distinct saved observations.

| Arm / action | Original cached-site rotation | Returned-body relative rotation | Relative-matrix disagreement |
|---|---:|---:|---:|
| Close / GRASP | 0.028736803° | 0.029369887° | 0.000682836° |
| Close / MV_UP | 0.028998160° | 0.029212634° | 0.000218358° |
| Open / STOP | 0.022353621° | 0.022966294° | 0.000628921° |
| Open / MV_UP | 0.024102204° | 0.024269976° | 0.000170313° |

The original four cached-site validator rotations reproduce within `5.4e-10°`
using independent matrix-angle arithmetic. All are below the existing 1°
retained-orientation limit; each recorded full contract result passes. All eight
control commands in each of these four actions have zero rotation components.
GRASP closes the jaws while preserving the controller's retained pose; it does
not construct a TCP orientation from the raw quaternion or choose a new grasp
alignment. This check leaves the previously established local mechanical witness
intact without extending it to a new approach or pose.

## What a misuse would change, and what the current interface exposes

As a clearly hypothetical error, apply the body matrix directly to the known
TCP-local pad centers at each saved direct finger position. Relative to the
correctly mounted matrix, the two pad centers would be misplaced by
**26.033–61.510 mm** over the 480 pad observations (median 61.351 mm). The jaw axis
would rotate by 90° in the local transverse plane. These are own-robot frame
errors, not measured collisions, clearances, target offsets or an observed runtime
failure.

The actual `LiberoWorldBackend.proprioception()` was exercised on all 240 saved
robot-only packets with a dictionary guard permitting only site position and
finger-joint reads. Any quaternion read would fail. No world features or execution
method was available. Poisoning the raw body quaternion leaves proprioception,
canonical model input and candidate effects **identical in 240/240 cases**.
The six nominal world-translation effects use only the target-minus-TCP world
vector. GRASP's geometric effect remains explicitly unknown in every packet.
No action recommendation was selected during this audit.

Source inspection covers the current backend, canonical model-input projection,
candidate effects and atomic executor, with exact hashes matching the archived
local-grasp producer. The broader source search found the raw quaternion retained
as an observation in sensor evidence and used for relative-rotation diagnostics;
it did not identify an unadjusted body quaternion packaged with site position as
a current model-facing rigid pose. This is a bounded statement about the inspected
repository/version, not all possible external consumers of the raw observations.

## Fixed BOX point illustration and explicit unknowns

The local-grasp collector has no separate initial robot sensor packet. For the
initial illustration only, the audit reads the paired archive's close-arm
endpoint −1 and preserves that distinct provenance. Its initial RGB-D is
byte-identical to both local-grasp02 and the sealed BOX source. The unchanged P
expressed at the returned site origin is:

| Orientation convention | Local coordinate of P, mm |
|---|---|
| Unadjusted body axes at site origin | `[101.763334, −58.899585, 172.023150]` |
| Correctly mounted TCP axes at site origin | `[58.899585, 101.763334, 172.023150]` |

The transverse components change basis; the Euclidean world distance does not.
No coordinate here establishes bottle surface ownership, center, extent, opposing
pad contact or a grasp offset. The earlier BOX audit's mixed support remains
unchanged. Absolute body position, exact returned sample times, same-time full
pose consistency and target surface validity remain unknown.

## Reproduction and hashes

Run the offline module against the fixed stored sources into a fresh directory:

```sh
/home/junhongli/miniforge3/envs/laya-embodied/bin/python \
  -m embodied_runtime.experiments.proprio_frame_consistency --output /tmp/frame-audit-new
```

The [portable summary](proprio_frame_consistency_summary.json) retains exact
metrics, source hashes and all four interventions. All 240 rowwise comparisons
and 30 endpoint comparisons remain in
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/proprio-frame-consistency-01/audit.json`.

| Artifact | SHA-256 |
|---|---|
| Audit output | `deb58e4e61f08935f95d9f47b484af2ebda54da59d04047a87bf500c523e8765` |
| Frozen protocol | `9226db3ae4af643864f710a41ba451d74a1c1a90cad3e455f5d9e727162dec45` |
| Local-grasp journal | `9347eab2f1b48fe3799ccfbc3164f60406b6451bd194819ef66632df7d6464bb` |
| Local-grasp sensors | `f3eead6a1556e2bbb64ea095aca6c251c6df7e95797099510d5aeb52fe662b58` |
| Static robot calibration | `11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa` |
| Sealed BOX sensor output | `be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead` |
