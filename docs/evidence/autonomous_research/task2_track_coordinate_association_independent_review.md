# Independent track coordinate-association review

**Prospective PASS at clean `dc1ec6c44d84f3337aec2f7fc0f7fc14a03f6d43` for the one registered offline batch.** The parent's standing authorization permits the producer to execute immediately after this receipt. The reviewer examined the complete adapter, protocol and tests and independently passed all **nine focused tests**. The source-only preflight `task2-track-association-preflight-01.json`, SHA-256 `b301f53378ff1968a8e0be65f21538880091df4e5124356dee9d0a90a52cd67d`, records clean provenance and zero archived reassociation, LK, model, physics or render calls. Original source/track hashes and exact input admission were independently checked. No archived tracking or projection was rerun by the reviewer.

The condition reuses all 984 original tracks and 45,264 saved rows. It changes only discrete association of OpenCV center-index coordinates to `floor(x + 0.5)` on each axis, with exact half ties assigned to the higher index. Independent analytic checks include epsilon perturbations, half boundaries and negative edges. Installed OpenCV 4.11 documentation and an actual synthetic `getRectSubPix` check establish that integer coordinate `(2,2)` samples array `[2,2]`. Selected source depth remains uninterpolated and uses the original validity gate; backprojection remains at selected `(index + 0.5)`. Native fields are copied unchanged and the original floor outputs remain preserved.

The registered producer run first recomputes old-floor surface outputs for exact baseline validation, then executes the single alternative association/projection pass. Initial/preclose references, fixed 492 denominator and summary definitions remain unchanged. Every capture retains exact changed-pixel and changed-depth counts. Alternative rows, summaries and paired-change counts are sealed before the unchanged, separately invoked proxy-only evaluator. No label-selected subset, retracking, threshold fitting or new source is admitted.

This tests the coordinate contract on the existing paired trace. It cannot establish repaired semantic identity, depth ownership, held-out improvement or universal removal of older observed tracking failures. In particular, the historical assistant-cap trajectory and its observed failure remain separate evidence; this condition does not reassociate that archive.

| Reviewed file | SHA-256 |
| --- | --- |
| `embodied_runtime/experiments/task2_track_coordinate_association.py` | `b95245bab639fac6a54359dd51020b2b40d0fd5e23f71fb7d1b7020b2590c855` |
| `docs/research/task2_track_coordinate_association_protocol.md` | `8f32d642890faeb7d8e78f6ccc8418c540bd2a40d8e54accfd3a4650cde147f6` |
| `tests/test_task2_track_coordinate_association.py` | `e15de45ef61b49eca11e22e2017e296892e8d889308436c460d67269c8a564ed` |
| Reused `task2_box_temporal_probe.py` | `655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50` |

## Independent sealed-result audit

**Stored-evidence PASS for `task2-track-association-run-01`.** The [independent checker](../../../experiments/task2_track_association_evidence_audit.py) and [complete receipt](task2_track_coordinate_association_independent_audit.json) verify the five-record chain, frozen provenance/preflight, original source/track hashes, complete sensor/evaluator seals, all **45,264 rows / 984 tracks**, and exact preservation of every nonassociation field. All selected pixels, source depths, validity reasons, reference displacement arithmetic, fixed cohorts, summary quartiles, per-capture pixel/depth changes and proxy/departure rows were independently checked. Changed-pixel projection was source-reviewed; unchanged pixels reproduce original stored world points exactly. No LK, projection, FK, model, physics or rendering was rerun.

All 492 samples remain native-successful and depth-valid at every capture in both arms. The original seed-5/capture-1 coordinate now selects `(217,169)` at `0.9750217199325562 m` and proxy True; its original floor outcome remains intact. The earliest remaining observed departure in both arms is seed 124/capture 6, sampled at `(216,178)`. Close/open have **30/25** departure seeds and final proxy counts **419/73/0** and **402/90/0** (True/False/unknown). These departures require a preceding True and do not include initial False alone.

| Same-track result | Close | Open hold |
| --- | ---: | ---: |
| Changed selected pixels across all rows | 15,883 | 15,002 |
| Changed depth values across all rows | 15,138 | 14,349 |
| Final preclose-relative point vertical median | 110.934858 mm | 0.003971 mm |
| Final preclose-relative point-minus-TCP norm median | 4.404283 mm | 114.328997 mm |

The specific near-zero-coordinate association switch disappears under the center-index convention, while later departures and mixed proxy support remain. This establishes an implementation-semantic difference on the same tracks, not semantic repair, held-out improvement or a holding classifier. The old assistant-cap sample failure is untouched. The first reviewer checker attempt required identical field sets; it was corrected to admit the registered added `sampling_convention` field while requiring every original nonassociation field exactly unchanged. Experimental artifacts were not modified.

| Result artifact | SHA-256 |
| --- | --- |
| Journal | `b68ddf216f1164273301d58f35caf2a9b53f79d32b6e0c3e152a61ac7d20cbb3` |
| Sensor seal | `d0bbf1a0671a34c8af96e10fd50321697200d5c07d775eb44b7f83c09862ec22` |
| Sensor summary | `282cbb97218622bf9575863bebd0c299461107d7f0aa29a2e3e6dd4773f847fa` |
| Post-seal proxy memberships | `5fadd07e60a134a305333056b844b22e828377a805087f7efefd1e2b055ec051` |
