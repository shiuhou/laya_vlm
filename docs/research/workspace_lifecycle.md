# Research workspace lifecycle

Completed 2026-09-27: removed **27 inactive worktree checkouts**, reclaiming
355,151,969 apparent bytes (338.7 MiB), including disposable Python/pytest caches.
Four worktrees remain: the main integration checkout plus three reused review,
Task2 surface-geometry and semantic-grounding environments. The local-grasp producer was
retired immediately after report integration and verification. No raw evidence,
failed-run log, branch, historical tag, model checkpoint or environment was deleted.

Before each removal, the cleanup checked clean tracked/untracked status, absence
of non-cache ignored files, and no process using that checkout as its cwd. All
active agents confirmed their old checkout dependencies were closed. Every removed
HEAD was pinned under `refs/archive/research-cleanup-20260927/`; original branches
remain. Those refs preserve exact source even for formerly detached checkouts.
The full inventory, planned mutations and completed receipts are retained at
`runs/maintenance/research-cleanup-20260927/{inventory,plan,result}.json`.

After the886-test approach/frame integration and canonical report closeout, an
additional3,196,180 bytes of main-checkout Python/pytest caches and one redundant
root inspection panel were removed. Every original RGB-D frame and the canonical
contact figure remain. Receipt:
`runs/maintenance/research-cleanup-20260927/closeout-cache-01.json`.

## Routine closeout

Before a new producer runs a model or simulator, check the actual frozen input
schema and dependency imports without computing outcome-sensitive features.
Synthetic API tests alone did not catch two recent bootstrap/schema failures.
Retain such failed setup attempts and separate corrected attempts by identity.

After each lane completes: review and integrate its useful source/report; seal
and retain raw evidence and failures in the canonical runs directory; preserve
exact source/configuration identities; remove the idle checkout after confirming
no current process or agent needs it. Reuse active worktrees for related next
questions. Remove reconstructible caches and proven duplicate generated outputs,
not unique observations or negative results. Uncommitted/untracked research stays
protected until disposition is explicit. Never count a deleted failed attempt as
an unattempted condition.

A historical checkout can be reconstructed without modifying the active branch:

```sh
git worktree add --detach /path/to/recreated-checkout <commit-below>
```

Scientific experiments that require frozen source should use the original commit;
expanded integration source is not silently substituted. Recorded historical paths
remain provenance, not requirements to keep every checkout alive permanently.

## Removed checkouts and preserved HEADs

| Checkout | Commit |
|---|---|
| `laya-approach-family` | `c70b88223fbe535895d545b3c1fd5c1e6b498b62` |
| `laya-approach-selector` | `ac4385a5852cdc08f638fe16df3bff683d1b24a0` |
| `laya-coarse-boundary` | `b72fcdc494522ea49cb7fd7d9f0b75f2789de49f` |
| `laya-coarse-initial-point-control` | `3abb31273d7958125881b7587eb15b5e2f47e08c` |
| `laya-coarse-native-counterfactual` | `aab3f6822fbce18d0e1d896f73e090e828647902` |
| `laya-coarse-point` | `a1c76d4764ce19ca25ea68042ceb4aebbafe2df8` |
| `laya-first-contact-observability` | `0dcb145831a64d3733aa7db30a1168b7bc7139c2` |
| `laya-gripper-visual-mask-control` | `850962a6d4139ed3d3bb62295208db78213d8eec` |
| `laya-grounding-probe` | `64366781439875274678adad72f9ffc58feb13cd` |
| `laya-interaction-observability` | `d23ed4d11baa8c3f274aa4860952e12fc3ba667e` |
| `laya-joint-interface-sufficiency` | `5f09dce2656cb5efcfaf6ec5ee9f9d605eb4cab5` |
| `laya-marker-control` | `14a05fc8a54b39889a96fe43703808657c3be053` |
| `laya-motor-control` | `2a42bcf0a7b994d08c0c4ef9b518f74779013958` |
| `laya-native-substep-observability` | `96e3e34389c0440f3d5f97d48dd34c6e16b169f7` |
| `laya-point-replay` | `ff4a57df8c43e396430767da7c3c8c5c30926bb3` |
| `laya-point-temporal` | `34114041c7e72f77659dd4cc553f53ad0c340f06` |
| `laya-predicate-verification` | `6c79ceef2dad3eeaca582a597661cd04d8fa8a08` |
| `laya-retention-independent-audit` | `64e34492eb1dd2e4a84f31a1c062e053fb441343` |
| `laya-robot-geometry-observability` | `d89f67080335c4462e66e9ecc37e99934c3cca16` |
| `laya-sensor-gripper-proximity` | `e8028e194f60806b2a8c877e98896368f4183a5a` |
| `laya-task1-native-contact-attribution` | `62f2ee96698ac977705d970734192a3e998a02a0` |
| `laya-visual-subgoal` | `3d64d7ccb7e15fd79cac626c66738489e79d8380` |
| `laya-visual-verification` | `a7dc274d543259a9d56dd5c0c6731fa6d4a01ece` |
| `laya-vlm-capability-control` | `495f709019558d9442297bcabaa3869ede535bb2` |
| `laya-vlm-world-understanding` | `0022e1a198c3c29f6b3f97da4d932449c3f761df` |
| `laya-worldview-sufficiency` | `03387f1b52741f2914cbec5b2485125361c0c041` |
| `laya-local-grasp-interface` | `a9dece388ff19139679262f92bee6c1f379a97c0` |
