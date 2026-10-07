# Complete BOX / SAM2 development evidence

Complete matched diagnostic at clean `b5ada28`:
[results and interpretation](../../../p1-segmentation-results.md),
[protocol](../../../research/p1_sam2_deterministic_grid_protocol.md).

Two recorded development wrist frames, init25/26 seed1; all six native masks.
No mask selected, all eight BOX/mask evaluations yield zero candidates.
Four broad-mask AMBIGUOUS results; two narrow masks fail original-BOX depth
coverage0.50 before components/planes. P1 Gate C unchanged. No labels/oracle
target truth, new LocateAnything calls, tracking, Qwen/Laya or control.

[Summary](summary.json), [registration](registration.json),
[independent review](independent-review.json), [root visual review](parent-visual-review.json),
[partial repeatability](partial-repeatability.json), [invariants](invariant-receipt.json),
[termination](termination.json), [contact sheet](all-masks-contact-sheet.png),
[portable archive](evidence.tar.gz), [artifact index](artifact-index.json).

The archive retains complete BOX/mask/geometry seals, raw high/lowres logits,
uncalibrated scores/masks, every candidate/metric, exact stage commands/logs,
position-grid raw-byte equivalence receipt, per-mask overlay/native silhouettes,
reproducible visualization source, source reviews and both attempt registrations.
`partial-reporting-failure/` preserves the earlier unsealed native init25 NPZ and
record-write traceback. That STOPPED attempt remains separate. The corrected
fresh process yielded an entirely byte-identical init25 NPZ, as recorded.

Existing sensor-source, preparation and preceding failure archives are dependency-
hashed in the index. No weights, venv trees or duplicate captures archived.
All archive members byte-verified against their canonical local files. Raw arrays
were not truncated or replaced with screenshots. The review index is externally
authenticated rather than incorrectly self-hashed.
