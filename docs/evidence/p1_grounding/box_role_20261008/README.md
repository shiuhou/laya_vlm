# Frozen BOX role decomposition evidence

Execution `ed48728`; source `51be5f6`. No new inference. Crossed conditions reuse
exact old SAM masks and change geometry ROI only. Full matched21 results for
SAM-BOX/geometry-BOX HH/HO/OH/OO: **21/21/21/10** candidate frames. Both interventions
recover the same11. Preregistered repair priority **INCONCLUSIVE**; stopped.

- [Report: observed fact / inference / unknown](../../../p1-box-role-results.md)
- [Prospective protocol](../../../research/p1_box_role_protocol.md)
- [All25 outcomes, including unavailable values](all25.csv)
- [Matched effects, gains/losses, interaction and denominator](comparison.json)
- [Native-mask boundaries and raw/admitted candidate totals](summary.json)
- [Source registration](registration.json), [execution condition](condition.json)
- [Read-only projection/source audit](audit.json)
- [Complete new raw evidence](raw-evidence.tar.gz)
- [Verified94-member archive index](archive-index.json)

Raw root: `runs/p1/box-role-20261008/`. Archive prefix: `diagnostic/`.
Archive size17,353,170bytes; SHA256
`e24b8924366f1a4e626f0bbc8474a22769a664601a7d88ca49eafacada1e27d7`.
All94members were checked byte-for-byte against source. Includes all new geometry,
scoring, native failures, source-mask references,25full-resolution comparison
images,5summary sheets, visual inspection and audit records. No source evidence
was overwritten. Reused masks/logits and HH/OO raw results are authenticated from
`../semantic_decomposition_20261007/` and its two-part archive; they are not
needlessly duplicated here. Original RGB-D remains in pinned Formal-50 sources.

Four OH source-mask-unavailable rows (init1/2/5/9) remain unassessed, not imputed.
HO evaluated all25frames and fails on these4. Primary factorial denominator21.
All native ordinals retained; all candidate usability UNKNOWN. Annotation is
explicitly offline diagnostic input/scoring, never runtime evidence or autonomous
perception performance. Original prompt BOX and geometry domain are separate.

Tests:2focused tests passed. Static names/import checks (`ruff --select F`),
compilation and whitespace checks passed. Main-agent audit independently computes
candidate projections from raw geometry and checks mask/depth/admission invariants;
it is not represented as an independent-agent replication. No geometry rerun.

Archival reproduction requires execution code and original pinned source paths,
`.venv-p1`, and a new output directory. No GPU or model process is required:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_box_role prepare --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_box_role geometry --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_box_role score --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_box_role review --output NEW_RUN
```

No repair, held-out tuning, tracker/temporal/P2/PUSH/Qwen/Laya/fixed-reference work
was executed. No further condition was added to break the priority tie.
