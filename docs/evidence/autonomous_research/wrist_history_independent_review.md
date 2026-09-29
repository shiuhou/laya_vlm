# Independent wrist-history evidence audit

**PASS.** The fixed within-control force-change feature separates the registered gripper-only contact cohort from the no-strong-robot/scene cohort better than the endpoint feature on this single trajectory. The result remains descriptive, with overlap; it is not a calibrated contact classifier, holding estimator or task-valid interaction detector.

The producer ran freeze `adc7eb4` after [prospective independent review](offline_wrist_history_independent_review.md). Raw results are in `runs/autonomous-research/offline-wrist-history-run-01`. The independent checker `embodied_runtime/experiments/wrist_history_evidence_audit.py` produced `wrist_history_independent_audit.json` without importing the producer's feature/cohort/score functions.

The audit streamed the original canonical source and checked its complete record chain and SHA-256, then reconstructed all 970 baseline/25-AFTER sensor projections and all 24,250 AFTER-contact labels. It verified source metadata, all control identities, strict >1 N membership, robot/gripper/arm partition, self-contact precedence, each cohort reduction, and the fixed endpoint-missed subset. It independently recomputed the four features, pairwise AUROC with half-credit ties, all cohort distributions, overlap counts, negative ranks and every preserved missed-contact interval. Six journal records establish the sensor → feature → label sealing order; all sealed artifact hashes pass. No physics, model, FK, projection, new feature or threshold fitting occurred.

| Cohort | Controls |
| --- | ---: |
| Gripper only | 163 |
| Arm only | 164 |
| Gripper and arm | 2 |
| No robot/scene contact above 1 N | 641 |
| Robot self-contact present | 0 |

The registered endpoint-missed subset contains **99** gripper-only controls: an earlier AFTER sample has gripper/scene contact above 1 N but the last AFTER sample does not. All are retained; no favorable examples were selected.

| Channel / positive set, against the same 641 negatives | Endpoint AUROC | Temporal AUROC | Difference |
| --- | ---: | ---: | ---: |
| Force / all 163 gripper-only | 0.787248 | 0.987634 | +0.200387 |
| Force / 99 endpoint-missed | 0.653918 | 0.993602 | +0.339684 |
| Torque / all 163 gripper-only | 0.765455 | 0.932822 | +0.167367 |
| Torque / 99 endpoint-missed | 0.663342 | 0.949448 | +0.286106 |

For the primary force comparison, 32/163 temporal positive values remain within the negative cohort's observed range; the endpoint-missed subset has 14/99 such values. Torque has wider overlap: 117/163 and 72/99. Range overlap is descriptive and does not choose a decision threshold.

Each feature uses the same first-BEFORE force/torque baseline. Endpoint change is the norm at the final AFTER stage; temporal change is the maximum norm across all 25 AFTER stages. The latter includes the former by construction. Improved AUROC is an independently measured ordering result, not a consequence of that algebraic inclusion alone.

The wrench is expressed in moving local wrist axes; actual sensor sample times are unknown. Contact labels are native cached AFTER samples. Acceleration, gravity, orientation change, preceding contact and cache timing can all contribute. “No contact above 1 N” does not mean literal contact freedom. The independent canonical audit found no designated fingerpad/handle rows anywhere in this trajectory, so these gripper-contact results cannot validate designated grasp/closure sensing. Repeated controls and contacts are dependent observations from one trajectory, with no held-out generalization claim.

| Identity | SHA-256 |
| --- | --- |
| Canonical source, 100,158 records | `e8e253cefe4c694c6091e1bf944a8f269cfc47c7ed08c053419d97e1a73615d4` |
| Analysis journal, 6 records | `055ecd9561e4306598f95d178ed785e9c7e2fa561f3279d42358abc09dbf810d` |
| Sealed sensor projection | `83b998611fbe72e9bbca4cd0128943244ffb485aacdf6d676ac422c2c1184cca` |
| Sealed features | `4722f64b2102990b6472484389c66319a932560bbbc2f3d1cf0961358925dea5` |
| Sealed labels | `060023831d58c0949a4eee21c9f600cc8501993c8dbc743f0c2777ca29cb5ff7` |
| Producer summary | `c75b15a3ffbfb67a70210d2d471fc6501096d33364707dbdf6e8fd50641de8c4` |
