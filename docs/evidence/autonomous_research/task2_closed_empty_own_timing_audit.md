# Matched-sham own-observation timing audit

The first-close returned jaw separation changed by **0.39401952693206255 mm**
between the old neck additional-GRASP archive and the new neck-present sham.
This is dominated by a changed observation sampling phase, not a comparably
large change in the native endpoint jaw state. No FK, LK, model, physics,
rendering, interpolation or new sensor timestamp was used for this audit.

## Exact correspondence in the saved records

For all eight first-GRASP controls (step 29), both components of returned
`robot0_gripper_qpos` **and** `robot0_gripper_qvel` exactly equal one unique
`native_after` record within that control. The stored named joint mapping places
`gripper0_finger_joint1/2` at qpos indices 7/8; the preceding scalar arm joints
also place their velocity entries at 7/8. These are joint-coordinate separations,
not a new geometric pad-distance calculation.

| Control | Native endpoint time (nominal s) | Old exact-match native index | New sham exact-match native index |
| --- | ---: | ---: | ---: |
| 0 | 12.15 | 23 | 22 |
| 1 | 12.20 | 48 | 47 |
| 2 | 12.25 | 73 | 72 |
| 3 | 12.30 | 98 | 97 |
| 4 | 12.35 | 123 | 122 |
| 5 | 12.40 | 148 | 147 |
| 6 | 12.45 | 173 | 172 |
| 7 | 12.50 | 198 | 197 |

The old matches precede their native endpoints by one 2 ms integration; the
new matches precede them by two. At the fixed final first-close boundary:

| Quantity | Old neck-close | New neck-present sham |
| --- | --- | --- |
| Returned packet journal sequence | 12637 | 12646 |
| Packet read / native endpoint time (s) | `12.500000000000844` | `12.500000000000844` |
| Exact-match native-after sequence | 12634 | 12641 |
| Exact-match native-after time (s) | `12.498000000000843` | `12.496000000000842` |
| Returned qpos (m) | `[0.010923780192142598, -0.01093260036511946]` | `[0.011121103288570364, -0.011129296795623755]` |
| Returned qvel (m/s) | `[-0.09865838755956356, 0.09841662931857144]` | `[-0.09862698613623345, 0.09833216308190476]` |
| Returned separation (mm) | `21.856380557262057` | `22.25040008419412` |
| Native final separation (mm) | `21.462008237157043` | `21.461863490618775` |

The native final joint-position differences (new minus old) are
`[6.1467640491419395e-09, 1.5089330231490838e-07]` m: maximum absolute difference
**0.15089330231490838 micrometres**. Final separation differs by only
`-0.0001447465382682367` mm.

An exact descriptive decomposition of the returned-separation difference is:

- Old native separation at index 197 minus index 198:
  `0.3941500337562722` mm.
- New minus old native separation at the same index 197/time:
  `-0.0001305068242096752` mm.
- Sum: `0.39401952693206255` mm, the returned-packet difference.

## What the sham refresh changed

In new neck-present, scene-state sequences 12215 (`before`) and 12219
(`after_refresh`) have the same simulation time `12.10000000000071` s and the
same environment clock. All **19** recorded observable timers advance by
`.002` s; the gripper qpos/qvel timers change from
`0.004000000000006717` to `0.006000000000006717`, with sampling timestep `.05` s,
zero configured delay and `_sampled=true` on both sides. The write and forward
stages do not change these observable timers or returned own packets; the
forced refresh does.

The before-scene jaw qpos/qvel exactly match approach step 28/native-after 198,
sequence 12205, time `12.09800000000071`. The refreshed jaw values exactly match
step 28/native-after 199, sequence 12207, time `12.10000000000071`. Thus the
scene refresh updates the cached returned jaw values while also advancing the
observable's internal clock without a physics step.

Available neck-away collection records show the same `.004...` to `.006...`
timer change for all 19 observables. Its full before and after-refresh own
packets exactly equal neck-present's corresponding packets. This does not
supply the missing away replay or complete matrix admission.

The inspected robosuite source explains the mechanism:
`base._get_observations(force_update=True)` calls `_update_observables`, which
passes `model_timestep` to each observable; `Observable.update` increments
`_time_since_last_sample` even with `force=True`. The gripper sensor functions
read simulator qpos/qvel directly through the named joint index arrays.

## Consequence and scope

The fresh present/away pair shares the same forced-refresh operation and initial
observable phase in its available collection records. The old positive suffix
lacks that event and is therefore confounded for a direct comparison of returned
own packets at the same read boundary. Native state histories must remain
separate from cached returned observations; a changed returned separation is
not by itself a changed physical endpoint.

The exact-match times above are **retrospective provenance evidence**, not
instrumented live sensor-call timestamps. Preserve the source's null exact
observation/sample-time fields. This audit does not backfill them, establish
RGB/own synchrony, or infer the timestamp of every other observable. It makes
no settled-empty, holding or threshold claim and does not release extraction.

## Source identity

All paths below are under
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/`.

| Source | SHA-256 |
| --- | --- |
| `task2-additional-stationary-grasp-run-01/neck-close/episodes.jsonl` | `eadf8b061bc3a77254b610d9603c648d058a5fd90fe4d33392a204eaf6670661` |
| `task2-closed-empty-scene-run-01/neck-present/episodes.jsonl` | `4529c644394177fc711e81a44e598dfc03f0837746c637a0e63f5bca577d9c72` |
| `task2-closed-empty-scene-run-01/neck-away/episodes.jsonl` | `c8571d9dcf5304e76b35fda95c756a5ac017a6f82169f94e596d9dee2e99c26e` |

Both run manifests pin the same `robosuite/environments/base.py` hash
`60eab4afd3dc95b4ac4cf0659fb9afe6360161912a4ac6931efe86ce1e1de519`.
The inspected installed `utils/observables.py` hash is
`19ea2e0e2cfb4ebcd5911cd2526dd645859535d25fc7bc55944c54a90e6672dc`;
`robots/single_arm.py` is
`38237d7b68c876b413f0df811b135ca3b2fb91061c011696baab07db5e87fa14`.
Those three files are byte-identical in the locateanything and laya-embodied
environments. The latter two hashes identify source inspected now, not a newly
invented historical run-time hash receipt. The stored joint mapping is in the
already reviewed `task2_closed_empty_static_bounds.json`; no model was loaded.
