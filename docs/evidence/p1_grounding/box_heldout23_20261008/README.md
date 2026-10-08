# HO23 generation evidence — human scoring pending

All23scenes and the authorized69LocateAnything calls completed once. Capture/
generation code f71e452; separate scorer a314003; approved design33c358c.
This checkpoint freezes model/geometry outputs, **not a completed blind score**.

If you are annotating these frames, use only the raw-RGB annotation packet until
your label export is sealed. Model results below belong to the later evaluation.

- [Report with explicit pending metrics](../../../p1-box-heldout23-results.md)
- [All23 operational rows; semantic fields null](all23-operational.csv)
- [Four-layer operational summary](operational-summary.json)
- [Registration/code/model/source/config pins](registration.json)
- [Generation-complete receipt](generation-complete.json)
- [Independent815-check audit](independent-audit.json)
- [Full raw generation/capture evidence](generation-evidence.tar.gz)
- [Verified549-member inventory](archive-index.json)
- [Raw-RGB-only blind annotation packet](blind-annotation-packet.zip)

Raw archive prefix `experiment/`,39,737,547bytes, SHA256
`c7671a0fd745dc687ce742c410f7cb54e96ad980fd65474e9eb42082ddc7d2e2`.
Every member was read back and checked against source bytes. Contains all23first
captures/both cameras, exposure audit,69model requests/raw tokens/outputs,46arm
slots,12native masks/logits/IoUs, all geometry, operational CSV, model/process
receipts and independent audit/script. No annotation export or final scoring is
present. Unpacked root: `runs/p1/box-heldout23-20261008/`.

No inference/SAM/geometry rerun is required to finish. Supply all23human labels
using the packet, then invoke the scorer command in the report. That scorer
verifies every generation seal before reading annotation. Append a separate
scoring evidence artifact/checkpoint; do not replace this generation archive.

Generation findings: BOX A23typed, B3typed+20noEOS; shared POINT4typed,
8cardinality failures,11noEOS. A generates12native masks across4frames;
B's remaining slots all fail upstream, so its SAM/geometry are NOT_EVALUATED.
A8,467raw geometry proposals (7,084after unchanged containment) are ungraded
for identity. B0proposals cannot meet19/23candidate coverage, independently of
labels; BOX localization and A candidate correctness remain UNKNOWN.

12focused synthetic tests and Ruff pass. No old development frame tuning,
query/checkpoint/threshold changes, retry-to-success, mask winner, human prompt,
or oracle input. No tracker/temporal/P2/Qwen/Laya. Current action: await label
export, complete blinded scoring/inspection, then stop for review.
