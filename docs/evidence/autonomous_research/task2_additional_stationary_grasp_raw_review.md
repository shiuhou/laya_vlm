# Additional stationary GRASP: independent stored-evidence review

PASS for the two-cell collection and both main plus auxiliary verification replays in `task2-additional-stationary-grasp-run-01`, freeze `945c96d81916f7952d9b40565c52b00085363544`. Both anchors satisfy the registered descriptive prediction: bilateral designated pads at the final additional-GRASP endpoint and all 200 lift BEFORE plus all 200 lift AFTER samples. No new matched close/open witness or holding classifier is claimed.

| Cell | Final first / added GRASP bilateral | Lift endpoints bilateral | Lift native bilateral BEFORE / AFTER | Center / bottom rise from added-GRASP end, mm |
| --- | --- | --- | --- | --- |
| Whole CLOSE | false / true | 8/8 | 200/200 / 200/200 | 9.402736783 / 9.387343409 |
| Neck CLOSE | false / true | 8/8 | 200/200 / 200/200 | 9.362801283 / 9.373159565 |

All six suffix action validators pass, with no unexpected-contact abort and all official success flags false. The original contact threshold and broad gripper/bottle allowance remain unchanged. Passing that validator is distinct from establishing a clean designated-pad mechanism.

The new lift intervals have no raw non-pad robot/bottle or bottle/table contacts at any saved native BEFORE/AFTER sample, including all eight control endpoints. Establishment is less clean: during the added GRASP, whole has 12 simultaneous bilateral-plus-raw-finger samples per stage, including one >0.05 N sample per stage, with maximum finger normal force **0.3858903552662356 N**. Neck has ten such raw finger samples per stage, all zero force. No hand or other robot-link/bottle contacts appear. Whole's transient finger contacts are missed by its auxiliary endpoint samples; neck's first added-GRASP endpoint includes a zero-force finger row.

During the added GRASP, raw table contact appears at 34/200 whole and 27/200 neck samples per stage; the respective >0.05 N counts are 32 and 27. Both first added-GRASP control endpoints still have table contact. Neither final added-GRASP endpoint does. The original first-GRASP prefixes retain their previously closed evidence, including no raw robot/bottle contact at their final endpoints. Sampled absences during the later lift do not establish clean continuous mechanism or continuous support-free retention. BEFORE/AFTER cached-contact timestamps are not independent continuous onset measurements.

| Cell / primitive | TCP translation norm, mm | Rotation change, degrees | Ending signed joint separation, mm | Ending separation rate, mm/s |
| --- | ---: | ---: | ---: | ---: |
| Whole first GRASP | 0.808049233 | 0.185572078 | 21.848372002 | −197.321674229 |
| Whole added GRASP | 0.203580097 | 0.057892898 | 12.096102086 | 0.004831877 |
| Neck first GRASP | 0.233004283 | 0.015010231 | 21.856380557 | −197.075016878 |
| Neck added GRASP | 0.070986466 | 0.005976239 | 14.958580256 | −0.006020252 |

The saved jaw arithmetic is descriptive and is not physical pad clearance, object width or holding evidence. Raw qpos/qvel and all 48 suffix own-state rows remain in the audit. Exact observation sample times remain unknown. The additional primitive supplies more closed-jaw time while allowing measured arm drift and contact rearrangement; it does not isolate closure latency. The old open-hold controls lack the extra interval. No fixed two-GRASP production policy or anchor superiority follows. Bottle rotation remains unknown without an archived source-specific address mapping.

The audit compares the complete fresh scientific prefixes through first GRASP against the closed source: **13,062 whole and 12,641 neck records**, with 40/39 primary-plus-auxiliary images and 39/38 merged sensor rows. Scientific capture IDs/times and arrays agree. Per-run journal-envelope record IDs bind separately to their respective journals. The original approach proof is reused; zero geometry memberships are recomputed.

New suffix coverage is six actions, 48 controls, 1,200 integrations and 2,400 native snapshots. Full collection/replay coverage is 65 actions, 520 controls, 13,000 integrations, 26,000 native snapshots, 67 primary captures and 48 auxiliary captures. The deduplicated sensor sequences contain 55/54 captures. Audit checks include independent command and validator arithmetic, state/own/native continuity, raw and thresholded contact families, evaluator snapshot bindings, all sensor seals, all exported replay states/fingerprints/equality gates, source/runtime identity and fixed stage ordering. Full replay contact/image comparison is performed by the reviewed verifier; only states/fingerprints/gates are separately exported. Sensor-before-label ordering is supported by reviewed code and file mtimes, without a dedicated journal seal timestamp.

The shared audit helpers were generalized only for the fixed schedule/counts; their defaults reproduce the closed whole-close and neck-open_hold suffix and contact receipts exactly. Ruff and diff checks pass. The independent auditor performs stored array/hash/journal comparisons and scalar arithmetic only: no physics, rendering, FK, archived projection, LK, model calls or membership recomputation.

Identities:

- [Independent audit](task2_additional_stationary_grasp_independent_audit.json): `13a6741bbf430be8c47a99217fe32acbe7f9d7cb5ad3e671ebd689eb24e95ad3`.
- Matrix journal: `40261179ca643c48cf81d76daa7521cb8e9ba61023859813e97661573605e8fa`.
- Request: `2c35c1eb4561262a7fbcecce81397c0d551662458eee8a4f959d1f580533be5a`.
- Prospective review: `0c884a05084e7bfbdab36e50d61997c35bc6d06b60555e68df816055b210b037`.
- Launch receipt: `10582a92f4b9b196cb5ec71ccf2b0dd44077e84bffc14be94a7aaa126afc6832`.
- Driver exit receipt: `632bc97a929c1543c65355a6b68cb2c47c5197f0de3c1c7fb8ec2e4919cc194b`, return code 0.

The audit above was generated before the producer's separate execution-closeout receipt was available; it already includes the completed matrix and driver exit.

The later [closeout review](task2_additional_stationary_grasp_closeout_review.json) separately verifies producer closeout SHA-256 `011564a3e1504080f4b10ce1095fd3280985d4b710147ef9b0ad381af7b2ae2b`: all artifact hashes, replay counts, copied phase labels/raw snapshots/own observations, full suffix action records, prefix receipt, native bilateral counts/first samples and rise arithmetic agree. Driver and outer tool status are both 0, with no discrepancy or retry. The immutable raw-audit hash above is unchanged; prefixes and physics were not repeated.
