# Frozen offline semantic decomposition evidence

Execution `f60cc1d`; starting checkpoint `f5cc1ce`. Wrist init0–24 development
frames only. Human support / human BOX+POINT / original BOX+human POINT /
original BOX+model POINT yield candidate-frame counts **25/25,25/25,10/25,0/25**.
Single next priority: **target-part BOX/search-support localization**, with the
SAM-prompt versus geometry-ROI confound unresolved. No repair was executed.

- [Full report and limitations](../../../p1-semantic-decomposition-results.md)
- [Prospective protocol](../../../research/p1_semantic_decomposition_protocol.md)
- [All25 matched table](all25.csv)
- [Summary: every new native boundary and candidate count](summary.json)
- [Four-condition comparison and matched completion subset](comparison.json)
- [Independent audit](independent-audit.json)
- [Registration and source hashes](registration.json)
- [SAM process/condition](sam-condition.json), [geometry condition](geometry-condition.json)
- [Offline timing and native ordinal measurements](timings.json)
- [Raw archive part00](raw-evidence.tar.gz.part00), [part01](raw-evidence.tar.gz.part01)
- [Part SHA256 and reassembly digest](archive-parts.json)
- [All200 archived members and hashes](archive-index.json)

All 46 new SAM calls,138 native masks, raw logits/low-resolution logits/IoUs,
4prompt-incompatibility failures, all geometry/scoring stages, every candidate,
25full-resolution review sheets and5summary sheets are preserved. No ordinal
or failure is removed. Native/candidate counts include overlapping hypotheses.
All candidate usability UNKNOWN. Human-assisted diagnostics are never autonomous
perception performance or runtime evidence. No new LocateAnything, model tuning,
tracker, control, Qwen or Laya.

Local raw root: `runs/p1/semantic-decomposition-20261007/`. Archive prefix is
`diagnostic/`. The200members were byte-verified against local source files.
The complete gzip stream is102,865,084bytes, SHA256
`9ab323bae2d612d96006621e6ac5cbb95b5a6f85e72d7ebee68afd51deb4079d`.
It was split into64MiB-or-smaller parts and the concatenated digest verified;
the redundant complete packaging intermediate was removed. No historical
or raw experimental evidence was deleted.

From this directory, inspect the archive without creating another copy:

```sh
cat raw-evidence.tar.gz.part00 raw-evidence.tar.gz.part01 | tar -tzf -
```

To extract into a new empty location:

```sh
mkdir /tmp/p1-decomposition-review
cat raw-evidence.tar.gz.part00 raw-evidence.tar.gz.part01 | tar -xzf - -C /tmp/p1-decomposition-review
```

RGB-D and C1/C4 are reused without duplicating their old archives. Their exact
bindings and source paths/hashes are in registration. The C1 companion is
`../human_region_geometry_20261007/`; C4 is `../identity_prompt_20261007/`;
original sensor recordings come from the pinned Formal-50 sources. No use of
simulator segmentation, changed calibration or human masks as runtime evidence.

Reproduction requires the execution revision and original pinned source paths,
prepared `.venv-p1` / `.venv-p1-sam2` environments, SAM source/checkpoint and an
explicit available GPU UUID. Use a fresh output directory, with the original
working directory as registered. This recipe is archival, not authorization
for another development tuning round:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_semantic_decomposition prepare --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_semantic_decomposition launch --output NEW_RUN --gpu-uuid GPU_UUID
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_semantic_decomposition geometry --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_semantic_decomposition score --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_decomposition_report --output NEW_RUN
```

Tests: two focused prompt/admission tests passed. Independent audit verified
frozen source/configuration, stage seals, exact native masks and reprojection
counts. Parent visually reviewed all25frames. Stop for review; next spatial
held-out validation and all temporal/control work remain unexecuted.
