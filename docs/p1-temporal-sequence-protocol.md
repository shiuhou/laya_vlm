# P1 temporal observation protocol — prospective

Status: **NOT RUN**. These are ten separate acquisition cases, not ten repeats
of the static collection. This document fixes coverage and evaluation boundaries;
it is not a manipulation recipe or permission to bypass the current gates.

Acquire only after the sealed static human annotations and fixed-query semantic
evaluation answer drawer-front support, fixed-reference observability and the
first grounding failure. No PUSH, Qwen, Laya or official-success-based VERIFY.
Observation-only acquisition must stop if it would require unvalidated contact.

| Case | Required observable change |
|---|---|
| T01 | Modest wrist-view perspective change, both surfaces still visible |
| T02 | Larger perspective change; association may legitimately become uncertain |
| T03 | Partial EEF occlusion of the drawer face |
| T04 | Full face occlusion followed by reappearance |
| T05 | Partial EEF occlusion of the cabinet reference |
| T06 | Full reference occlusion followed by reappearance |
| T07 | Visible drawer movement while cabinet reference remains unchanged |
| T08 | Drawer movement reversal / opening–closing observation boundary |
| T09 | Reference movement or identity discontinuity; prior fixed-reference support must not remain valid silently |
| T10 | Combined perspective/occlusion boundary with a delayed semantic reply |

Each case must preserve same-exposure dual RGB-D, capture-time K/T and robot-only
proprioception; save pre-boundary, boundary and post-boundary frames, requests,
outputs, independent face/reference tracks, raw geometry and source IDs. Record
every LOST, AMBIGUOUS, lineage break, explicit reseed, skipped update and stale
reply. A failed association is an observation, not an excuse to reconstruct an
old ID silently. Mark cases that lack either observable surface as unsupported.

Any scene perturbation used to test a movement boundary belongs to a separate,
explicit evaluation fixture. Save its commands/configuration as evaluator-only
provenance; never provide drawer joints/body IDs to perception or use fixture
truth as VERIFY evidence. Such a fixture is not robot manipulation competence.
Free-space robot observation motion must use the existing actuator semantics;
it must not introduce a new P2 runtime or a task-specific executor.

Camera configurations cannot silently change while keeping a calibration ID.
Wrist motion uses the existing camera attachment and capture-time FK; a changed
attachment/intrinsic configuration starts a new calibration lineage.

Count a sequence only after raw frames and actual perturbation/occlusion are
inspected. Image warps, synthetic masks, reset swaps, repeated static frames and
unit-test fixtures do not count as these ten sequences. Keep sequence support,
tracking correctness, geometric availability and live freshness separate.

For throughput, report requested versus achieved capture and geometry rates,
single-ROI time, complete publication/persistence rate, update gaps, source ages
in both clocks and deadline misses. An old frame must remain old; replay clocks
and capture-time diagnostics cannot substitute for live freshness measurements.
