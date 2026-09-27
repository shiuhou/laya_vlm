# Matched target-present and closed-empty observations

The new pair supplies a mechanically qualified local positive and empty-grasp
negative with the same approach and commanded suffix. Both collections completed;
their controls, native snapshots and images now have exact verification. The
original matrix remains **interrupted and incomplete**: its final verification
was interrupted, then a separately recorded second verification passed. No
collection was repeated and no original evidence was rewritten.

This is sensor-selected approach plus scripted diagnostic actions, not autonomous
Laya grasping or full Task2 success. Both official combined-task predicates remain
false. Source freeze: `cf00088824f4b74bd121cb6e8b3c89cc702fe9ab`.

## Intervention and actual observations

Each fresh init0/seed1 collection regenerates the same 29-action neck-POINT
approach (232 controls). At its non-executed STOP, the present arm receives a
zero-translation sham; the away arm receives +0.35m world-X bottle translation.
Both perform exactly one forward and forced observation refresh, with no clock
advance or controller reset. The complete mutation/cache inventory is preserved.
This is an explicit privileged experimental scene intervention, never a sensor
estimate, online policy or hidden winning action. Then both execute unchanged
GRASP / GRASP / 10mm MV_UP: 24 more controls, 32 actions per collection.

Root inspected all ten original full RGB panels in the
[source sheet](task2_closed_empty_source_boundaries.png). The bottle remains
visible on the tabletop in the away arm; it is absent from the gripper region.
The [image ledger](task2_closed_empty_source_boundaries.json) binds every unchanged
RGB tile to its original archive. Both prefix histories and post-event own packets
match across arms before executing the suffix.

| Recorded result | Present | Away |
| --- | ---: | ---: |
| First GRASP qualified endpoint labels | 0/8 | 0/8 |
| Second GRASP qualified endpoint labels | 8/8 | 0/8 |
| Lift qualified endpoint labels | 8/8 | 0/8 |
| Lift raw bilateral pad samples, each native stage | 200/200 | 0/200 |
| Bottle center rise from prelift | 9.402435mm | 0mm |
| Bottle bottom rise from prelift | 9.412844mm | 0mm |
| Official full-task success | false | false |

The [mechanical summary](task2_closed_empty_mechanical_summary.json) retains all
three phase counts, both native stages, endpoint predicates and source hashes.
Present's second GRASP has 184/200 bilateral samples per native stage, nine raw
non-pad robot/bottle samples with zero reported force, and 27 raw table-contact
samples. Its lift has no raw non-pad robot/bottle or bottle/table contacts at the
recorded native stages. This does not establish continuous-time force closure,
clean continuous establishment or support-free retention.

Away has zero raw robot/bottle contacts across all 1,200 suffix native snapshots
and 24 endpoint snapshots, including zero-force rows. The intended negative is
therefore qualified at the recorded samples. It is **same-exposure empty**, not
proven settled-empty: after the second GRASP its signed joint-coordinate
separation is 2.199971mm and separation rate is −2.354314mm/s; after lift those
are 1.545948mm and −1.356602mm/s. Present's prelift values are 14.958597mm and
−0.006108mm/s. No settling threshold is fitted. Joint-coordinate differences are
not physical pad gaps or measured object widths. All 50 selected own packets
remain in the [own-observation extract](task2_closed_empty_own_observations.json).

## Refresh changes reported sampling phase

The new sham is not byte-equivalent to the older positive suffix. At first-GRASP
end, its returned separation differs from that old trace by 0.394020mm, while
the maximum final physical jaw-coordinate difference is only 0.150893µm.
The independent [stored-source timing audit](task2_closed_empty_own_timing_audit.md)
finds all eight old returned qpos/qvel pairs exactly match native states 2ms
before their endpoints; all eight new sham pairs match 4ms before. The forced
refresh advances all 19 observable timers by 2ms without advancing simulation
time. Both new cells share that change and their before/after own packets agree.

These are retrospective state matches, not newly recorded sample timestamps.
The manifest's exact sample-time fields remain null. Comparing new present
against new away preserves the matched refresh; substituting the historical
positive would confound that comparison. Extra exposure also includes physical
rearrangement and small arm motion, so this is not a pure latency experiment.

## Interruption and separate verification

Original raw root: `runs/autonomous-research/task2-closed-empty-scene-run-01`.
Its launcher returned 143 without a recorded driver return code. The journal ends
at away-replay intent. The signal origin and interrupted replay's executed control
count are unknown; an empty result directory does not prove no dynamics occurred.
Both collections and present replay were already complete. This incident differs
from the historical four-cell launcher143 whose matrix had actually completed.

After independent partial-source audit found no hidden collection failure, root
authorized a separately reviewed **second away verification attempt** using the
same frozen replay/event/auxiliary functions and sealed away controls. It passed
in 57.159493s, launcher/tool exit0, no signals and no recollection. Output:
`runs/autonomous-research/task2-closed-empty-scene-away-verification-01`.
Its exact checks cover 256 controls, 12,800 native snapshots, 33 primary and
24 auxiliary images, and all nine scene-event records. Present's original
verification covers the same counts. Both event images are included separately.
Original matrix file inventories are byte-identical before and after verification.

The [composite source audit](task2_closed_empty_scene_independent_audit.json) says
`observational-source-qualified`, with `original_matrix_status=interrupted_incomplete`.
It qualifies the two sealed observations with their separate exact replays; it
does not repair the old matrix journal or pretend the first verification succeeded.
The [original partial audit](task2_closed_empty_scene_partial_independent_audit.json),
outer-exit sidecar and second attempt's launch/signal/exit receipts remain intact.

## Decision and validation

Use this pair for the prospectively fixed post-event 492-pixel motion assay.
It can test whether robot-local motion appears without a bottle in the grasp
region. It cannot certify ownership of every tracked pixel or a holding estimator.
Fresh semantic localization is a separate prospective question. No result here
earns a fixed two-GRASP production policy or a deeper hierarchy.

Integrated event/source regression: 1,131 tests pass in43.44s at `1e665a2`;
producer104 focused tests and reviewer94 focused tests passed. Protected runtime,
LIBERO backend and decision interface remain baseline-identical. The report's
stored-only generator is `experiments/task2_closed_empty_mechanical_summary.py`.
