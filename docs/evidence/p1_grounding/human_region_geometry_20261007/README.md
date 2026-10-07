# Frozen offline human-region geometry evidence

Execution `eb8028e`; baseline `e8cda1e`. One pass on 25 frozen VISIBLE wrist
frames, no new model inference or threshold change. Human annotation is an
offline support upper bound only, never perception performance or runtime input.

**25/25 frames, 130 geometry candidates, NO_TOOL_INTERIOR_CANDIDATE 0/25.**
All candidate usability remains UNKNOWN. Diagnostic complete; downstream blocked.

- [Full report](../../../p1-human-region-geometry-results.md)
- [Prospective protocol](../../../research/p1_human_region_geometry_protocol.md)
- [Every frame's depth/component/plane/edge/tool measurements](all25.csv)
- [Summary](summary.json)
- [Frozen registration and source hashes](registration.json)
- [Execution environment](condition.json)
- [Audit and grid-point rejection counts](audit.json)
- [Complete new raw evidence](raw-evidence.tar.gz)
- [Authenticated archive inventory](archive-index.json)

The archive's `diagnostic/` contains inputs, geometry, summary and review stages,
plus the evaluator-only review script. All 66 members were checked against their
source SHA256 after packaging. Original RGB-D is reused from the pinned Formal-50
recordings; it is not duplicated or replaced by annotation. Local unpacked root:
`runs/p1/human-region-geometry-20261007/`.

For offline inspection, review/page-00.png through page-04.png cover all25frames;
pink is human support, yellow the annotation boundary, cyan raw geometric points.
Each sheet explicitly states human assistance and UNKNOWN usability.

Archival reproduction at the execution commit, in a fresh output directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_human_region_geometry prepare --output NEW_RUN
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv-p1/bin/python -m embodied_runtime.experiments.p1_human_region_geometry evaluate --output NEW_RUN
```

This recipe requires original pinned source paths/annotations and the local
geometry environment. It is not an instruction to run a second condition.
