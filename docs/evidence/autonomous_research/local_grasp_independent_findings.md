# Independent local grasp-interface findings

**The registered local mechanical witness passes.** At the archived pre-grasp boundary, the unchanged visual `AtomicExecutor` executes GRASP followed by one nominal 10 mm MV_UP within its original validation limits. The bottle rises 9.279539 mm while both designated pads contact it at all eight lift endpoints and both recorded native stages of all 200 lift integrations. The paired open/hold arm rises 0.001081 mm and establishes no bilateral relation.

This validates one local transfer from the demonstrated native grasp to the actual visual action executor. The approach prefix is scripted and privileged-selected. No perception or model selected an action; this is not sensory approach, autonomous grasping, general grasp competence or Task-2 completion.

The reviewed freeze is `9b85ad5bb48de68e097b233afef8ecfd84cdb993`, with its [prospective receipt](local_grasp_interface_independent_review.md). Raw collection is `runs/autonomous-research/local-grasp-interface-run-02`; verification is `local-grasp-interface-replay-02`. Attempt 01 remains a failed import/source-introspection setup with zero world construction or controls. Its log and the no-world setup preflight for attempt 02 are retained; neither is a successful physical run.

The independent stored-only checker `embodied_runtime/experiments/local_grasp_evidence_audit.py` passes and writes `local_grasp_independent_audit.json`. It verifies source and sensor seals, record chains, all 224 comparable commands/sensor observations/evaluator states through step 13, and 28 prefix RGB/depth/K/T frames including dtype/shape/bytes. The initial states and complete 240-control before/after chains match. It reconstructs every contact relation and unexpected-contact flag in 1,600 stage snapshots, verifies native timing/state chains, recalculates all four unchanged executor validations, and checks all 240 stored verification states against collection. No additional physics, FK or projection was run by the reviewer.

| Action | Translation residual | Retained-orientation change | Original limit | Result |
| --- | ---: | ---: | --- | --- |
| Close arm GRASP | 0.220081 mm | 0.028737° | Hold 1.5 mm / 1° | Pass |
| Close arm MV_UP | 0.600963 mm | 0.028998° | Translation 2 mm / 1° | Pass |
| Open arm STOP | 0.310048 mm | 0.022354° | Hold 1.5 mm / 1° | Pass |
| Open arm MV_UP | 0.542131 mm | 0.024102° | Translation 2 mm / 1° | Pass |

Actual returned TCP rise is 9.423957 mm close and 9.484801 mm open. Jaw commands remain closed and open respectively throughout each lift. There are zero unexpected robot-contact rows above the configured 0.05 N threshold in either instrumented primitive of either arm. That oracle-assisted abort was diagnostic and checked after the current atomic operation; it is not a deployable sensor gate.

The close operation contains 21 bilateral before-stage and 21 bilateral after-stage samples. Its subsequent lift contains 200/200 at each stage. The open arm contains none. These are cached native stage samples, not separate impacts or proof of uninterrupted continuous-time contact. The threshold and effector groups are the existing bottle TaskSpec's strict >0.05 N bilateral pad relation. The allowed gripper/bottle contact group used for the abort is broader than the designated pad relation used for positive evidence.

The sampled-endpoint criterion was fixed prospectively: all four validator results pass, close rise is positive and greater than open rise, close has bilateral contact at all eight lift endpoints, and open has none. The separate stronger native-stage condition also passes. Neither condition establishes support-free retention, a calibrated holding estimate, or task completion. Official combined success remains false in both arms.

| Artifact | SHA-256 |
| --- | --- |
| Collection journal, 2,149 records | `9347eab2f1b48fe3799ccfbc3164f60406b6451bd194819ef66632df7d6464bb` |
| Sensor seal | `2ac164126dcd9ca32e851c97da90db29657c0a7f0c6bf4a464cdd68862fd1326` |
| Verification result, 240 exact states | `24a6ddf3785556acdc65fdfd767ca0c58a099b7ed20cd207f1841a04099ad5e4` |
