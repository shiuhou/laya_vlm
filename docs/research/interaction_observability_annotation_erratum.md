# Annotation provenance correction

The v1 protocol and raw schema use `human_RGB_only_before_close`. In the actual
`interaction-observability-paired-01` run, the Codex assistant visually inspected
the raw seed RGB and chose the pixels; no human supplied them. The accurate
description is **assistant-provided RGB visual annotation before close**. It is
neither autonomous LocateAnything nor an oracle seed, and must not be reported
as a human study. This correction was communicated while collection was still
underway, before the sensor analysis and evaluator-label inspection.

The assistant viewed only `seed-required.png`, at the paused step-12 boundary,
then wrote the two bottle pixels `(223,174)`, `(216,217)` and tabletop reference
`(171,290)`. The collection process froze these before any step-13 control. Both
arms used identical seeds. No post-close image, sensor outcome, or evaluator
segmentation was used for selection; no point was changed after tracking failed.

Keep the original protocol, code commit and raw schema intact so the discrepancy
is visible. Reports correct the actor attribution explicitly. This provenance
correction changes neither physical protocol nor frozen analysis parameters.
