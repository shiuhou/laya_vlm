# Independent audit of the fixed four-cell temporal transfer

PASS. All **91,512** saved rows retain the expected seed/capture order and source
metadata. All **32,964** registered common-prefix rows agree in all nine native
tracker fields. The complete matrix has 1,968 trajectories and 186 captures.

The audit independently reconstructs nearest-pixel selection, depth validity and
camera/world projection from the saved source frames. Maximum projection
difference is 2.220446049250313e-16 m under a 1e-12 m arithmetic audit tolerance.
Every available preclose-relative vector and norm matches exactly, including all
33,456 preclose-or-later rows. Before-preclose deltas remain null. All 186
fixed-denominator count/median/quartile summaries were independently recomputed;
no seed or native failure was removed. In this matrix every capture happens to
retain 492 native-admitted, depth-valid points. That is not identity validation.

The audit checks all source manifest/seal/frame hashes, complete output seals,
journal termination and protocol/source links. It does not rerun LK, read object
or contact labels, invent masks, or establish contact, holding or support-free
retention. Separate tracking-code review and the unchanged helper identities
support the native implementation; this numerical audit does not independently
reimplement the optical-flow algorithm.

The final all-seed median vertical changes are 8.281058 mm and 8.448493 mm for
whole/neck CLOSE, versus 0/0 for their OPEN controls. Median 3D point-minus-TCP
change norms are 5.112751/5.159369 mm for CLOSE and 9.899415/9.413874 mm for OPEN.
These are descriptive differences in a mixed original image crop. They are not
a calibrated classification boundary or estimates of object pose error. Original
reference timing includes both jaw closure and lift.

Reproducible audit code: `embodied_runtime/experiments/task2_point_anchor_retention_evidence_audit.py`
at commit `72f0d81`. Ruff passes. Complete [receipt](task2_point_anchor_retention_transfer_independent_audit.json)
binds the source seal `39ede31f44f5782fe24b68e623ba2e7eb6131e23c5d769ebf92cd3715fbeda60`
and output artifacts `5a510ca3e4e9d0110b819f690a66c14feb6d051aafbe9d65b5f5e036bc34e5bc`.
Raw run: `runs/autonomous-research/task2-point-anchor-retention-transfer-run-01`.

```sh
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m embodied_runtime.experiments.task2_point_anchor_retention_evidence_audit runs/autonomous-research/task2-point-anchor-retention-transfer-run-01 runs/autonomous-research/task2-point-anchor-grasp-transfer-run-01 /tmp/task2-retention-audit.json
```
