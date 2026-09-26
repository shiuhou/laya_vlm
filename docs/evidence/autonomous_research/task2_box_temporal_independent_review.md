# Independent initial-BOX temporal review

**Prospective PASS at clean `9a34f297abf8bc47ba1cf589dfe9cc9e31c303f0` for the one registered offline batch.** The parent's standing authorization permits the producer to execute after this receipt. The reviewer examined the complete adapter/protocol/tests and unchanged LK helper and independently ran the five new analytic tests plus seven existing helper tests: **12 passed**. No archived tracking or projection was executed by the reviewer.

The actual source-only preflight 01 has SHA-256 `804b0a18c3159ca60b2a556fc3980845eb314a07d3eaad4b72d77c1713b8c791`, records the clean freeze, LocateAnything interpreter, OpenCV 4.11.0 and existing 256-thread default, and declares zero LK/model/physics/render/evaluator calls. The reviewer verified that receipt, all four source-receipt hashes, all 92 capture hashes, the fixed row-major 492-seed population and the untouched LK helper hash. The preflight checks all actual frame/calibration/TCP schemas, 46-capture schedules, identical initial sensor fields and common-prefix RGB. Capture 0 uses the saved initial endpoint TCP; every later capture selects its exact saved step/control TCP. No FK, old landmark file, neck output, target pose, force/contact field or evaluator enters the numerical input packet.

Each integer pixel-index seed independently uses the original single-seed `track_lk` over all 46 frames per arm. Native failure is permanent, with raw attempted coordinates/status/error/residual retained and every later unknown row present. The depth adapter admits only seeded/native-successful tracks, floors the coordinates, checks bounds and inclusive 0.01–5 m validity, and projects the containing pixel at its half-pixel center. Depth invalidity never terminates or restores RGB tracking; explicit reasons and nulls preserve strict JSON. The half-pixel offset is not applied to LK seeds.

All 984 tracks and 45,264 rows are retained. Every frame keeps denominator 492, native survival/failure/unknown and valid-surface counts. Initial-reference summaries cover 0–45. Preclose capture 13 defines a fixed valid cohort for 13–45 only; its count is null before 13 and later missing rows remain explicit. Fixed linear quartiles summarize existing per-seed displacement/residual values; missing values are never zero or evidence of holding. Overlapping windows, common prefix, one paired trace, depth ownership, sparse approach cadence and survivor bias prevent independent-trial or classifier claims.

The complete track/summary seal and journal termination precede the separately invoked mask evaluator. Proxy membership cannot change any track or summary. Initially outside pixels are distinct from departure: departure requires a prior observed True followed by observed False, with unknown gaps not establishing an exact crossing time. The evaluator reports all memberships and unknowns and creates a current hash receipt for archived masks; it does not invent historical ownership provenance. No label-selected survivors, reseeding, threshold fitting, alternative setting or automatic retry is admitted. Preserve partial files and failure counts if execution fails.

| Reviewed file | SHA-256 |
| --- | --- |
| `embodied_runtime/experiments/task2_box_temporal_probe.py` | `655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50` |
| `tests/test_task2_box_temporal_probe.py` | `11e3a6bc6f2a9d14ba3242f4fde67fbd4329baef1593a064b1a1a23abc54fabd` |
| `docs/research/task2_initial_box_temporal_probe_proposal.md` | `00cf740936af6f1caaa79696a4df0d44bd744894f7d71215841cf078b6b5e6f0` |
| Unchanged `point_temporal_probe.py` | `86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36` |

## Independent sealed-result audit

**Stored-evidence PASS for `task2-box-temporal-run-01`.** The [independent checker](../../../experiments/task2_box_temporal_evidence_audit.py) and [complete audit receipt](task2_box_temporal_independent_audit.json) verify all six journal records, source/preflight/protocol identity, all track/summary seals, every one of the 45,264 saved rows, stable seed/capture identity, native-status/failure semantics, exact floor/bounds/source-depth admission, saved-TCP correspondence, all displacement/residual arithmetic, every fixed-cohort summary and all post-seal mask membership/departure rows. No LK, projection, FK, model, physics or rendering was rerun. Stored world-point generation was source-reviewed; initial points also agree with the original saved support to 1e-15 m. Raw LK outputs match exactly across both arms throughout the common RGB prefix.

All **492/492** seeds remain native-successful and depth-valid through all 46 captures in both arms. No native-failure example exists, and the preclose cohort is the entire initialized population. The raw rows imply 44,280 native forward/backward LK calls per arm; this is a count derived from saved statuses and the frozen helper, not a separate native-call trace. All initially outside proxy samples remain in the population.

| Registered final preclose-relative metric | Close | Open hold |
| --- | ---: | ---: |
| Point vertical displacement median | 110.376114 mm | 0.003887 mm |
| Point displacement norm median | 112.174428 mm | 0.050405 mm |
| Point-minus-TCP vertical displacement median | -3.756488 mm | -114.316305 mm |
| Point-minus-TCP displacement norm median | 5.036417 mm | 114.328997 mm |
| Final proxy True / total seeds | 402 / 492 | 399 / 492 |
| Seeds with observed False after prior True | 34 | 32 |

Both arms start with 414 proxy-True and 78 proxy-False seeds; capture 1 has 396 True and 96 False. The earliest registered departure is seed 5 in both arms at capture 1. Its initial seed `(217,169)` changes to LK coordinate `(216.99996948242188,169.00015258789062)` with forward/backward residual `0.0001220703125` px. The faithfully implemented floor rule selects `(216,169)`, whose depth is `1.2016721963882446` m, instead of initial `(217,169)` at `0.9750217199325562` m. Capture 2 selects `(217,169)` again. This is a concrete containing-pixel quantization/depth-support switch under negligible LK coordinate movement; it does not show that the whole tracked image patch lost its identity. The original registered floor rule remains unchanged in this result. Whether that rule is the appropriate mapping from OpenCV pixel-center coordinates is a separate implementation-semantic question, not a reason to erase this outcome.

The differing aggregate close/open motion is descriptive correspondence/surface evidence on this known paired trace. It is not a holding classifier or an independent-trial success rate. Native survival does not imply target identity, the originally outside points were not removed, proxy membership is not depth ownership, and a low flow residual does not prevent sample association jumps. The sensor-before-evaluator ordering is reviewed in frozen code and the evaluator references the complete sensor seal/journal; its start receipt has no independent wall timestamp. Current mask hashes identify the bytes actually evaluated, not an invented historical ownership seal.

| Result artifact | SHA-256 |
| --- | --- |
| Journal | `0e7bd76d3f6b11244729bc767ec1b1f9a2625aa6069e494adf9743ea5900cf05` |
| Sensor seal | `bae9793115ededab12b6b5bca242af9cdb0c2ed8c1e8d62219af3bbce65cc30b` |
| Sensor summary | `4b46a6bddaa87b545de1f6d5f31e1aa6f77836e9b904fe5e71877cd47d6ce933` |
| Separate proxy membership | `be859c241cfae6e2da5446a0a9429c89b50e70b1d57eeea1de1f26298eba4ea2` |

The producer's final report at `1f1aa44` passes factual and figure review. The reviewer separately inspected original RGB, all-sample-location overlays at all six fixed captures, complete curves and the first-departure sheet. All report hashes, inspected original PNG source seals, all 46 portable sensor/proxy summary rows per arm, exact first-departure selection and native-failure nulls were verified; both arms' departure sheets are byte-identical. The differing motion-panel scales are disclosed, every track remains represented, and the report preserves the concrete floor-association explanation without calling it whole-patch identity loss. Portable summary SHA-256: `7aebe2bea0d28d8418bf25a79919cb7203353c3ba0729972db4013776cf55a33`. This closes the original registered condition; a coordinate-association amendment requires a separate reviewed condition and must preserve these original results.
