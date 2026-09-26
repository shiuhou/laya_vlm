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
