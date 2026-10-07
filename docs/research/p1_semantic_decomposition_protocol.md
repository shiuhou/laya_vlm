# Bounded wrist25 semantic decomposition (prospective)

Baseline f5cc1ce. Only the exposed init0–24 wrist images are used. C1 reuses
human-region geometry; C4 reuses the original BOX+model POINT run. No new
LocateAnything, threshold changes, tracking, control, Qwen or Laya.

C2 uses annotation-derived BOX and positive POINT; C3 uses the original sealed
model BOX and the same human POINT. Both are offline human-assisted diagnostics,
never sensor-only perception scores or executable evidence.

Prompt construction uses only the already frozen raster annotation: minimal
half-open bounding BOX [xmin,ymin,xmax+1,ymax+1]; POINT at the pixel of greatest
Euclidean distance to the complement of the one-pixel false-padded mask,
row-major tie break, continuous pixel centre (u+.5,v+.5). Exact integer squared
distances suffice; no new dependency is required. No depth, scores, original
POINT or geometry results enter prompt selection. Continuous BOX containment,
floor sample in ceil geometry ROI and exact sampled-depth availability are
checked afterward. Incompatible C3 prompts remain failures, without snapping.

Use the frozen SAM source/checkpoint/settings/deterministic overlay. Retain all
three native ordinals, raw logits/IoUs/low-resolution logits, all failures and
point-containment diagnostics. No mask selection or retry. Each native mask
runs unchanged geometry with its supplied BOX as ROI and depth outside the mask
NaN; depth availability denominator is the complete native mask. Run geometry
even on point-contradictory masks. Human-assisted provenance stays explicit;
call the pure geometry function, not the learned-only admission wrapper.

After sealing geometry, score candidates against frozen annotation. Report raw
and point-admitted frame existence, all native outcomes and wrong-target
candidates. Existence across masks is diagnostic, not a deployable selector.
All25 and the C3/C4 jointly completed subset are reported separately.

Primary future repair rule (priority heuristic, not causal decomposition):
compare signed frame-count gaps in point-admitted, inside-region candidate
existence: C1-C2 (target-specific segmentation/support), C2-C3 (BOX grounding),
C3-C4 (POINT identity/completion). Choose the largest positive gap; ties prefer
support, BOX, POINT in that order. If none is positive, no repair is earned.
Record nonmonotonic per-frame changes and matched-subset contrasts. C1-C2 also
changes support/search/proposal domains; C2-C3 changes both prompting and ROI;
C3-C4 all25 includes generation/admission losses. None is a factorial causal
attribution or held-out evaluation. Calibration confidence remains unknown.

Stop after reporting and checkpointing. Recommend exactly one future repair,
to be validated on new held-out frames; do not execute it this round.
