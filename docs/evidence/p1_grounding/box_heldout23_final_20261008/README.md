# HO23 final offline evaluation evidence — 2026-10-08

[Final report](../../../p1-box-heldout23-results.md). Separate companion to the
[immutable generation evidence](../box_heldout23_20261008/README.md).
No generation archive, model output or geometry output was modified.

- [All 23 scenes](all23.csv), [four-layer summary](summary.json).
- [All 26 completed BOX metrics](box-metrics.csv), [all 12 native-mask metrics](native-metrics.csv).
- [User-attested annotation metadata correction](annotation-correction-receipt.json).
- [Independent scoring audit: 340 checks](final-independent-audit.json), [focused checks](checks.json).
- [Complete companion archive](final-evidence.tar.gz), [verified member hashes](archive-index.json).

Raw RGB + all A/B BOX/POINT outcomes, including failures:
[init27–32](frames-sheet-1.png), [init33–38](frames-sheet-2.png),
[init39–44](frames-sheet-3.png), [init45–49](frames-sheet-4.png).
All native masks and projected proposals: [init34/35](masks-sheet-1.png),
[init40/49](masks-sheet-2.png). These were inspected after scoring, not shown
to the human annotator. Orange is human support; frame overlays use cyan A BOX,
magenta B BOX, yellow POINT; native overlays use blue mask and red outside proposals.

The archive contains the original annotation export/receipt, metadata-only
correction and validation, sealed scoring, every individual review image and
review generator, independent audit source/result and its preserved report-only
serialization failure, visual review observations, and checks. Polygon records
are unchanged. Human independence is user-attested, not independently verified.
The original export's contradictory AI-source metadata remains in the archive;
it was not silently discarded. All 23 human front labels are VISIBLE; fixed
reference remains UNKNOWN in all 23.

A/B clean frames 0/23 each; completed BOX localization 0/23 and 0/3. B20noEOS
is an output-availability failure, not measured semantic mislocalization.
A7,084 admitted proposals all outside annotated support. B's SAM/geometry are
NOT_EVALUATED upstream. No comparative SAM subset exists. Outside conservative
usable regions does not independently prove wrong physical object identity.
The frozen scoring summary's generic pending-scoring status string is stale;
annotation_status=SCORED and this companion establish final scoring complete.
No sealed file was rewritten to improve wording.

Reproduce scores with the scorer at a314003/db08a3e, restore the generation
archive and final annotation-correction folder, then use the command in the
scoring module with a new exclusive scoring output directory. Absolute artifact
paths in original manifests require the recorded repository path or an explicit
relocation audit; do not silently rewrite sealed paths. Do not run inference.

P1 not passed; P2 blocked. Batch stopped for review. No tracker, new temporal
sequence, PUSH, Qwen, Laya, query/decoder tuning or repair was run.
