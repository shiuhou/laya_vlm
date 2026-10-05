# Annotation provenance correction

The project user clarified that the submitted annotations were already completed
by a human who had never seen the AI draft, and that the JSON provenance was
wrong. This supersedes the earlier inference of exposure from those fields.
No new drawing is required on account of that metadata error.

`../annotation_receipt_20261005/annotations.received.json` preserves the original bytes; no duplicate copy is needed. The separately named
`annotations.metadata-corrected.json` records the corrected provenance based on
the user's report; it does not claim independently verified identity or
non-exposure. `correction-receipt.json` preserves the exact user statement,
changed paths and both file hashes. The source of the erroneous metadata has
not been established.

All 50 image bindings and polygon structures were rechecked. Every region,
visibility status, reason, reference type and original export timestamp remains
unchanged. No model inference or geometry/query tuning took place.

The corrected copy remains a v2 document with extra provenance and source fields;
it is not presented as a fresh v3 export. The v3 validator has not been weakened
or bypassed. Evaluation must retain the original v2 image/rule identity and
preregistration chronology when resolving serialization compatibility. A later
metadata correction must not be presented as annotations collected after the
v3 preregistration. The optional empty v3 packet does not require replacement
labels now that the user has clarified the factual situation.
