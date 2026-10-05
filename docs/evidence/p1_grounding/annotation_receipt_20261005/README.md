# Received annotation: blind condition not admitted

The received file is preserved byte-for-byte as `annotations.received.json`;
SHA256 `6d57054fa839508745ce45396fc00e873b53942395f5d86fb6f81fe2247ed990`.
No region, provenance, attestation or timestamp has been changed.

All 50 image bindings and the rules version match the packet; 75 polygons pass
the finite/bounds/nondegenerate/self-intersection structural checks. This is
**structural integrity**, not approval of region semantics or blind eligibility.
The received export additionally contains provenance and source metadata fields
outside the frozen export schema.

Its own provenance declares prior AI-draft exposure, AI-draft origin, human
relabeling by self-attestation, and `eligible_for_human_blind_evaluation=false`.
That contradicts the affirmative independent-of-model-output checkbox. The
registered blind gate remains blocked with `ANNOTATION_BLINDNESS_CONFLICT`;
neither stripping metadata nor checking the checkbox can erase prior exposure.
No LocateAnything/Qwen/Laya calls or PUSH actions occurred.

An independent agent audited the original file read-only and confirmed the
source bindings, polygons and provenance conflict. The primary user has been
asked to choose between preserving the blind requirement with an unexposed
human annotator and explicitly changing this phase to a nonblind diagnostic.
No experimental condition has yet been changed. Re-labeling the same images
after prior exposure cannot be described as a fresh blind annotation.

`receipt.json` records coverage, structural checks, disclosure and gate result.
Visibility counts describe this unadmitted submission only and are not an
observability or model-performance conclusion.
