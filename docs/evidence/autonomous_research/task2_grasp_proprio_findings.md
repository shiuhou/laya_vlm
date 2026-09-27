# A completed GRASP still has moving jaw joints

The saved proprioceptive observations independently show that jaw closure was
still progressing at the first GRASP endpoint in both original CLOSE cells.
This is a descriptive examination of the completed four-cell experiment, not a
new contact detector or a prospectively registered classification result.

| Cell | Joint separation after close/hold, mm | Joint separation rate, mm/s | Separation after lift, mm | Rate after lift, mm/s |
| --- | ---: | ---: | ---: | ---: |
| whole-close | 21.848372 | -197.321674 | 12.096128 | 0.004594 |
| whole-open_hold | 79.998531 | 0.001289 | 79.998965 | 0.000908 |
| neck-close | 21.856381 | -197.075017 | 14.958430 | -0.005218 |
| neck-open_hold | 79.997973 | 0.001779 | 79.998573 | 0.001253 |

“Joint separation” is the arithmetic difference of the two saved signed
prismatic joint coordinates, and its rate is the corresponding velocity
difference. It is **not** a pad-surface gap, object width, or contact measurement.
The first and second endpoints were read 0.4 and 0.8 simulated seconds after the
preclose observation. Exact observation sample times are not archived; only the
read times are known.

The [complete extract](task2_grasp_proprio_summary.json) keeps all 68 own-state
rows: preclose and all sixteen suffix control endpoints per cell, including raw
joint coordinates/velocities, TCP, source linkage, and source manifest/seal
hashes. The generator reads only the sealed sensor manifests. It reads no
contact, object pose, holding labels, image, or simulator state. All 68
differences were cross-checked using separate NumPy arithmetic; Ruff passes.

The independently established [contact audit](task2_point_anchor_grasp_transfer_raw_review.md)
shows no contact at either final first-GRASP endpoint. That observation is
consistent with these moving jaws, but the own-state extract alone does not
establish contact absence or causality. A closed stationary gripper may be empty;
a stopped jaw does not certify a valid grasp. No velocity threshold or holding
classifier is introduced.

The already planned intervention remains one additional existing stationary
GRASP before the unchanged lift, at both approach endpoints. A positive result
would support explicit relation/settling evidence at phase handoff. It would not
justify silently lengthening the executor or implementing a fixed two-GRASP
manipulation policy. Model use of this information is still untested.

Reproduce the extract without simulator or model inference:

```sh
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m embodied_runtime.experiments.task2_grasp_proprio_report runs/autonomous-research/task2-point-anchor-grasp-transfer-run-01 /tmp/task2-grasp-proprio-summary.json
```
