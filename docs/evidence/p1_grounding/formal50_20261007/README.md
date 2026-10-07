# Formal-50 frozen evidence checkpoint

Completed at clean execution
`e1ff472936cfb906ea6d3bfaf08adfd8200c0805`; baseline `25f1e4a`.
[Full report](../../../p1-formal50-results.md),
[prospective protocol](../../../research/p1_formal50_protocol.md).

50 original frames →50 archived drawer BOXes →150 native masks →all frozen
geometry outputs →sealed blind scoring. No inference failures/retries/winner.
Task-valid drawer-front candidates0; all45,252 geometric proposals fall outside
the frozen VISIBLE human region. Wrist25VISIBLE, agentview25UNKNOWN.
No new LocateAnything, temporal/tracker, PUSH/P2, Qwen or Laya work.

- [Registration and full freeze/source hashes](registration.json).
- [Camera-separated full taxonomy/timing](summary.json).
- [Stage reached/rejected/not-evaluated diagnostics](stage-diagnostics.json).
- [Every native mask CSV](all-native-masks.csv), all150 ordinals and failures.
- [Independent corpus/scoring/visual review](independent-review.json).
- [Termination and remaining scope](termination.json).
- [Geometry environment (recorded after completion)](geometry-environment.json).
- [Artifact index and all archive member hashes](artifact-index.json).
- [Compact metadata evidence archive](metadata-evidence.tar.gz).
- [Packaging verification correction, no data rewrite](packaging-note.json).

Canonical raw corpus: `runs/p1/formal50-native-masks-20261007/`.
Contact sheets: `review/page-00.png` through `review/page-09.png`; every frame/
mask displayed, original RGB column0, learned masks pink, human evaluation
regions yellow, geometry candidates cyan. Parent and both reviewers inspected
all10 pages. Annotation is not runtime evidence.

The Git metadata archive retains complete per-frame/per-mask metrics/candidate
lists, first rejections, seals, JSON source receipts, process receipt/log and all
review images. It **does not contain native NPZ arrays or original recordings**.
The separate full companion archive is retained locally at
`runs/p1/formal50-native-masks-20261007-full-evidence.tar.gz`: all authentic
masks/logits/scores, complete output metadata and review, original sensor
recordings/packet/images, frozen annotations and100 BOX predictions, dependency
receipts and project source snapshots. Both archives' member bytes were verified.
The exact external SAM checkpoint/source revision and locked environment remain
identified dependencies; weights, installed venv and wheel cache are not packed.
A fresh Git clone alone does not contain raw native/sensor evidence; preserve
the indexed companion archive for transfer or independent reproduction.

Reproduction from original repository root and required pinned dependencies
(use a **new output path**, never overwrite or retry this frozen attempt):

```sh
git checkout e1ff472936cfb906ea6d3bfaf08adfd8200c0805
.venv-p1/bin/python -m embodied_runtime.experiments.p1_formal50 prepare --output NEW_RUN
.venv-p1/bin/python -m embodied_runtime.experiments.p1_formal50 launch --output NEW_RUN --gpu-uuid GPU_UUID
.venv-p1/bin/python -m embodied_runtime.experiments.p1_formal50 geometry --output NEW_RUN
.venv-p1/bin/python -m embodied_runtime.experiments.p1_formal50 score --output NEW_RUN
.venv-p1/bin/python -m embodied_runtime.experiments.p1_formal50 review --output NEW_RUN
```

Commands are reproduction instructions, not another experiment performed here.
Recorded archive URIs and local dependency paths bind the original repository
root; relocation requires explicit path mapping, not invented source values.
Compact evaluation-only diagnostics and packaging do not change pipeline gates.

**P2 remains blocked pending Formal-50 / temporal P1 gate.** Formal-50 is now
complete; temporal qualification was not earned. Next proposal B is a scoped
prospective identity/representation repair; not implemented this round. Neither
P1 pass nor a final scientific Gate A/B/C is assigned. Stop for review.
