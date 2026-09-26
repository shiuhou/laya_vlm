# Task2 approach: fixed point versus saved jaw geometry

The fixed proxy P remains outside the finite pad-gap prism at the first-contact
control and at termination. The raw contact pair is **`gripper0_hand_collision`
(palm) / `wine_bottle_1_g6`**, at 0.081748 N in the first observed sample. This
corrects the earlier RGB-based finger impression. Images may suggest contact near
the cap/neck, but that qualitative impression does not identify the contacting
robot geometry; the raw geometry attribution is primary.

This is explanatory arithmetic on saved own observations and the unchanged BOX
point. It adds no estimator, policy, successful-prepose comparison, target offset,
physics, FK or model call. The source trace/provenance audit is separate.

## Saved point-to-pad relation

Use the previously checked transform `R_site = R_body × Rz(−90°)` and the already
site-referenced returned position. Signed returned finger joints and static pad
calibration supply the facing gap `q1−q2−1 mm`. The pad Y interval is ±8 mm and
the pad Z interval is `[−11.6, +4.4] mm` in TCP axes. These are static own-pad
boxes, not finger-body/palm collision geometry or observed bottle extent.

| Saved own packet | Read/control time | P in TCP axes (mm) | Facing pad gap (mm) | Nearest pad-box distance to P (mm) |
|---|---:|---|---:|---:|
| Start | 0.500 s | `[58.900, 101.763, 172.023]` | 76.446 | 192.483 |
| Before first-contact control | 10.100 s | `[29.328, 33.999, 34.505]` | 78.997 | 41.058 |
| After first-contact control | 10.150 s | `[29.130, 33.920, 33.367]` | 78.997 | 40.230 |
| Termination | 10.500 s | `[29.225, 33.336, 25.113]` | 78.998 | 34.300 |

At both contact-control boundaries and termination, P lies between the facing
pad X planes but outside their finite Y and Z ranges. Its terminal offsets from
the facing-gap midpoint are `[29.224, 33.336, 28.713] mm`. Thus an open gap of
about 79 mm does not by itself establish alignment with even this single point.
The terminal encoder aperture is 79.998 mm, 1 mm larger than the static facing
gap; the jaw command remains OPEN. Terminal TCP-to-P distance is 50.951275 mm.

The first observed contact is action 24 (`MV_DOWN`), control 0, native BEFORE
index 3 at 10.106 s. The preceding native AFTER index 2 has the same recorded
time. These are native cached contact stages, not an exact contact-onset clock.
No own pose packet is saved at that native contact stage. The two control packets
above bracket its control interval; exact observable sample times are unknown,
so no pose is interpolated at contact. The source stops after the already-started
atomic primitive, not immediately at the detected native sample.

P is the initial integer-box center ray at crop-median depth. It is neither a
verified surface sample nor bottle center, extent or contact point. The source
keeps it fixed without proving object stationarity. Point-to-pad distances cannot
explain the palm collision's full geometry or establish clearance from the
bottle. They show why reducing TCP-to-P distance alone is insufficient evidence
of pad alignment; they do not prescribe a correction or replacement action.

## Original scripted prefix and rotation scope

Source-only inspection of `interaction_observability.prefix()` and its pinned
strict-gate action identifiers finds 13 preclose translations: seven 40 mm and
six 10 mm primitives. There are no pitch, roll or yaw action tokens. Native
`World.execute` initializes rotation to zero and changes it only for a rotation
primitive. The original pregrasp therefore did not command an orientation change;
controller drift remains distinct from commanded pitch/roll.

Consequently this contrast does not establish that the seven-option approach
failed because it lacks pitch/roll actions: the existing local grasp was reached
by a different, privileged translation prefix at retained orientation. Its route,
step sizes and information source also differ. No successful-prepose coordinates,
target fit or replacement path were used in this interpretation.

## Reproducibility

Pure math/tests are commit `9e61588`; the bound four-packet interpreter is
`5fb06cc`. Three synthetic tests pass. The [portable summary](task2_point_jaw_interpretation_summary.json)
retains exact own packets, all scalar results, source record IDs and timestamps.
Selected source record sequences are 2, 10109, 10161 and 10528. No other trajectory
pose is used for point-to-pad geometry.

| Artifact | SHA-256 |
|---|---|
| Sealed approach journal, producer `9de837c` | `f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771` |
| Static robot calibration | `11d2d8c788439c7a10cd9a4e26022762096b712e55d9fb2d93bb51e3ee56bdaa` |
| Fixed BOX sensor output | `be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead` |
| Raw interpretation | `5df975320d33d4d8887fdb38fbd64546d41dd8e3e25bc7a6c36e3d08c98f09a5` |
| Inspected original prefix source | `6d2b9d347c4fe0576ab7400e4dd0f1995da09ed29f0900fca564ca483d281ce3` |

Raw output:
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-point-jaw-interpretation-01/interpretation.json`.
