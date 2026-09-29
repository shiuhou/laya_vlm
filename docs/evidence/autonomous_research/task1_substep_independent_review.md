# Independent canonical Task1 native-stage audit

The stored-evidence audit passes. The canonical successful replay contains **zero raw designated fingerpad/handle contact rows** in both native sampling stages, including rows at or below the historical force threshold. This extends the prior control-end result to the recorded 2 ms integration stages. It does not establish continuous-time impossibility, hardware behavior, or a causal allocation of drawer motion.

The independent checker is `embodied_runtime/experiments/task1_substep_evidence_audit.py`; its full output is `task1_substep_independent_audit.json`. It streams stored records and reads archived arrays. It does not import the producer's classification/summary helpers, create an environment, replay dynamics, perform FK, or estimate forces. The completed audit was run once against the raw artifact below.

| Identity | Value |
| --- | --- |
| Producer freeze | `f6efbcb4a1d461faf8a37720d50efacb76f37260` |
| Raw run | `runs/autonomous-research/task1-native-contact-run-01` |
| Raw episodes SHA-256 | `e8e253cefe4c694c6091e1bf944a8f269cfc47c7ed08c053419d97e1a73615d4` |
| Raw records | 100,158 |
| Canonical source | `runs/privileged-reference/local-objective-task-adapter-episode-01` |
| Source episodes SHA-256 | `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2` |
| Source manifest SHA-256 | `a19ddc51c95e094be6d4dbac3fbb1271902de30ede8f630d432c8e40f9ec4b2a` |
| Source reference-evidence SHA-256 | `063ad9585ca4bd5c9c5e7dbedff39efe522d51261a5a5e2e8246a94653cba008` |

## Replay and instrumentation

All 122 primitives and 970 archived controls are present: the first 121 primitives contain eight controls; the last contains two, preserving historical early success. Initial state, every archived before state, available after states, commands, primitive drawer position, and official success match exactly. Intermediate after states use the next archived before state; each final control uses the archived final state. The producer used fresh init0/seed1 and the standard ten settling controls, directly applying archived commands with native observation assignment. No policy regeneration or state restoration occurred. Original observation/controller caches were not archived, so exact measured trajectory equality is not proof of equality of every hidden cache.

There are 24,250 native `mj_step` calls, 48,500 stage snapshots, and 48,500 native forwards. The original Euler path uses a 0.002 s timestep and 25 integrations per control. Source review checked bounded per-primitive passive hooks and the absence of extra forwards. The checker verifies integration/forward lineage, qpos hashes, state chains, joint addresses, record hash chains, source artifact hashes, clean freeze/preflight identity, contact memberships and threshold arithmetic, and conservation of closure across all class partitions.

Wrist channels are existing sensor buffers, classified independently of contacts: three force values from `mjSENS_FORCE` (type 4, N) and three torque values from `mjSENS_TORQUE` (type 5, Nm), at site `gripper0_ft_frame` on `right_gripper`. Metadata includes the static site transform. Buffer read time is logged; actual sensor sample time is unknown. Cached contacts, geometry and force buffers may precede the advanced after-step qpos/time. Before/after rows are sampling stages, not separate physical impacts.

## Independently reconstructed result

Net drawer closure is **152.05189674218448 mm**, with official success preserved. Designated and bilateral relations are absent at both stages. Each stage contains 3,038 historical non-designated samples and 21,212 samples satisfying neither historical relation. The following interval table requires before/after classification agreement; six differing intervals retain their own class.

| Interval class | Intervals | Positive change (mm) | Negative change (mm) | Net change (mm) |
| --- | ---: | ---: | ---: | ---: |
| Historical non-designated only | 3,035 | 59.460246 | −3.506979 | 55.953266 |
| Neither historical relation | 21,209 | 98.564999 | −2.490217 | 96.074782 |
| Before/after disagreement | 6 | 0.028301 | −0.004452 | 0.023849 |
| Designated only or simultaneous | 0 | 0 | 0 | 0 |

Using the before stage alone assigns 55.953493 mm net change to historical non-designated samples and 96.098404 mm to neither; using the after stage assigns 55.976888 mm and 96.075008 mm. The ordinary control-end reconstruction exactly reproduces the earlier accounting: 134 non-designated controls/46.086120 mm and 836 neither controls/105.965776 mm. Finer sampling changes the descriptive partition; it does not identify the unique cause of subsequent motion.

## Historical semantics and limits

The historical non-designated expression is arm/drawer contact, gripper/explicit g11–g16 contact, or gripper/handle contact when designated pad/handle contact is absent. It is not the pairwise complement of pad contact: simultaneous pad and finger-body contact on the handle alone is not historically non-designated. “Neither” therefore does not mean no contact. The historical threshold is strictly greater than 1 N; the stronger zero-designated finding also checks all raw rows without that threshold.

The original TaskSpec at jev commit `d67cb50` (file SHA-256 `fb5cd2c73b27ff6ab244667a215dc0a16528eb9a52e25f72e846910dd2d14497`) and the later file at `11d4504` (`006395162b0ccafb5a8a632d56d6fdedf26590c788fb5ac095766c54f09dfe50`) retain identical original measurements and designated/bilateral/non-designated expressions. Later additions expose geometry, interaction evaluation and traces; they do not retroactively change the historical policy's success label.

This review supports a successful measured replay with no observed designated contact at the available native stages. It does not turn contact-class closure sums into contact-caused displacement, establish exact contact duration, or prove that no valid designated interaction is possible under another action sequence or controller. Later producer-only timing summaries are outside this completed independent audit.
