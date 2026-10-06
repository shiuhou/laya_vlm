# P1 observability closure

This bounded round implements the approved return to the README milestone route:
P1 → P2/B0 visual geometry/servo → P3/B1 Qwen + rules → P4/B2 zero-shot Laya →
P4/B3 domain-trained Laya → P5 held-out and latency perturbations.
The immutable baseline is `d1ed91e`, tagged `p1-observability-baseline-d1ed91e`.
The 256/1024-token fixed-reference POINT condition is
`UNSUPPORTED_INCOMPLETE_GENERATION`. No further decoder, query or budget work is
part of this round. Reference and VERIFY remain UNKNOWN until measured.

## Inputs and independence

Reuse `runs/p1/static-25init-20261005`, the sealed 100 BOX responses in
`runs/p1/corrected-v2-fixed-query-evaluation-20261005`, and the **already completed**
50-frame corrected-v2 evaluation annotations. The original rules/regions/statuses
and seals remain unchanged; independence is user-reported, not independently
authenticated. Each entity has 25 VISIBLE and 25 UNKNOWN frames. UNKNOWN is neither
a success nor a negative. No redrawing or relabeling as version3 is required.

The sensor-only generation stage must finish and seal every hypothesis before
the separate offline scorer opens labels. Evaluation polygons cannot seed a
track, pick a plane, infer fixedness or enter the runtime. Original BOX geometry
and complete inventory are separate experimental outputs. A plane, an interior
point, a target association and an executable USABLE patch are different claims.
Uncalibrated confidence stays null; uncalibrated uncertainty remains explicit.

## Fixed-reference search

Every archived semantic BOX is a search region only. Enumerate all RGB-D face
supports, finite observed support boundaries and measured support adjacency;
also enumerate an explicitly recorded full-frame scene-context search. Preserve
raw pixel supports, residuals, source identity, overlaps and rejection reasons.
No largest/nearest-plane winner, BOX-center reference, annotation reference or
oracle cabinet state is allowed. Observed adjacency is not mechanical attachment;
stationarity alone is not cabinet fixedness. A side face is not automatically a
closed-front reference. Missing identity/structural/closed relation means
REFERENCE_UNKNOWN, not proof that the scene contains no reference.

## Temporal and cost measurements

One fresh-reset attempt each for T01–T10, init0–9, seed1, dual 384×256 cameras.
The frozen recipes distinguish perspective, actual scene-motion fixtures,
occlusion and delayed semantic reply. Evaluator fixture/contact records are
isolated from perception. No target-bound feature and conservative swept-volume
clearance are currently available for EEF occlusion; T03–06/T10 therefore collect
fresh HOLD observations and explicitly report unsupported event coverage.
No fabricated occlusion or delayed reply is counted as a qualifying sequence.
Empty source-bound seed sets leave independent drawer/reference tracks UNSEEDED.
Archived development seeds are never transplanted into fresh observations.
Losses and explicit reseeds/generations remain visible. Raw RGB contact sheets and
full videos are inspected; a separate blank raw-only temporal human packet supports
evaluation. Missing human temporal labels cannot certify the 95% identity metric.

Three 30s live streams at init0/12/24 request10Hz and use a capacity-one dual-view
queue. Capture, inventory/candidate assembly, publication and persistence timings
are separate. Record p50/p95, drops, gaps, wall/sim geometry ages and end-to-end Hz.
Stored BOX windows are diagnostic workloads, never fresh semantic seeds. Without
a target association this measures computational cost, with valid-target Hz0;
it does not establish continuous target tracking or target freshness.

## Finite scope gate

The exact frozen thresholds are in `configs/p1_observability_closure.json`.
Drawer readiness requires ≥20/25 correct target/interior init states, zero known
wrong-part admissions, all10 attempts reviewed with required actual drawer events,
≥95% correct available geometry in evaluable visible temporal intervals, zero
invalid identity/lineage continuation and ≥95% live visible target publications
meeting the unchanged0.3s age limit. Missing evaluation cannot pass a gate.

- **A:** drawer readiness plus reliable fixed reference, structural/temporal
  evidence and observable closed relation with original pairing gates. Next P2a,
  then controlled P2b; this does not claim VERIFY SATISFIED without calibration.
- **B:** drawer readiness passes, reference/closed relation blocked. P2a may follow;
  full close/VERIFY remains blocked.
- **C:** drawer readiness fails or qualification remains unavailable. Finish this
  bounded round, report the failure breakdown and choose a sensing/segmentation
  intervention separately. Do not prolong the decoder route or add models.

## Implementation and checks

`p1_observability_closure.py` owns offline generation/scoring;
`reference_candidates.py` owns sensor-only reference hypotheses;
`p1_temporal_probe.py` owns source-bound temporal acquisition/replay;
`p1_temporal_annotation_packet.py` exports raw-only review;
`p1_observability_stream.py` measures the live workload. Existing geometry,
executor, controller and generic runtime scheduling are reused unchanged.
Only focused tests for the new boundaries and necessary tracker regression run.
Code/config is committed before evidence runs. Historical evidence is append-only.
Reconstructible caches may be removed after recording cleanup; raw/canonical
evidence is preserved. No PUSH, official-success substitution, Qwen/Laya inference,
query/model changes or geometry-gate relaxation occurs in this round.
