# Offline temporal correspondence falsification probe v1

Prospectively frozen after retrospective static-sequence inspection; no live
policy or recovery implementation. One CPU run, no model inference, no simulator,
no threshold search, no new tracker. The source is coarse-point-boundary-01:
episodes SHA-256 d9ed0bc2b10b61b047e44ec37a03ea788b4e88e2f8d06edd8171bcd29677f319,
manifest SHA-256 99c46d8ebccee071b5a8840500579d26aedec184ff59e8a51f4c344e13024e54.
Verify the record chain and all 26 frame artifact hashes. Read RGB only from
the RGB-D artifacts. No depth, simulator membership, object pose or oracle score
enters either tracker. The primary seed is the first admitted sensor POINT's
containing pixel index, not the last retrospectively correct point.

Compare frozen-pixel propagation with OpenCV 4.11.0 pyramidal Lucas-Kanade,
exactly: winSize=(21,21), maxLevel=3, criteria=(COUNT|EPS,30,.01), flags=0,
minEigThreshold=.0001; grayscale COLOR_RGB2GRAY, float32 point coordinates.
These are the same explicit defaults as the prior inspection. A separate reverse
LK call measures forward/backward residual. No residual-to-confidence mapping,
new acceptance threshold, global search, reinitialization or missing-row deletion.
After a native forward/reverse status failure or nonfinite result, propagation
stops and later rows remain explicitly unknown. Retain attempted outputs even
on failure. The frozen-pixel baseline emits its initial point throughout, with
no visibility/identity claim.

Eight conditions, each 26 frames, in this order:

1. Unmodified recorded RGB sequence.
2. Frames 2–26 translated by (+8,0) integer pixels.
3. Frames 2–26 translated by (0,+8) integer pixels.
4. Frames 2–26 translated by (-8,-8) integer pixels.
5. Frames 2–26 have a 31x31 opaque RGB(127,127,127) patch centered on the primary
   seed; the target's local correspondence is unobservable.
6. Same 31x31 patch, centered at (floor(W/4),floor(H/4)), away from the seed.
7. Target occlusion as in 5 plus a copy of the first frame's original 31x31
   target patch placed at seed+(40,0), as a synthetic appearance distractor.
8. Unmodified RGB but the seed is (floor(W/4),floor(H/2)), a deliberately
   different initial location. Tracking that location does not establish that
   it is the requested target. No target-identity claim is made by this control.

All translations affect the full image, use constant grey fill without wrapping
or interpolation, and preserve frame 1 for initialization. Occlusion also begins
at frame 2. No condition parameters may be changed after observing results.
Before assigning static coordinate labels, require the original 21x21 RGB patch
at the primary seed to be byte-identical in all source frames. If this precondition
fails, stop this probe rather than treating an unverified stationary label as
ground truth. The wrong-seed condition does not receive an identity-correct label.

Evaluation is separate from propagation: synthetic displacement of the primary
seed is known by construction. Record raw predicted coordinates, native statuses,
forward/reverse patch error, forward/backward residual, distance to primary
reference and (when visible) primary correspondence error. For occluded frames,
do not score proximity to the hidden original coordinate as successful tracking;
count native successful statuses despite deliberately unavailable correspondence.
Such continuation demonstrates an uncertainty limitation, not recovered identity.
Report wrong-seed distance to primary reference separately, even if its tracking
status and forward/backward residual look favorable. No arbitrary success-error
cutoff is introduced: report all errors and descriptive extrema/medians.

Preserve transformed RGB inputs, exact hashes, full 8x26 rows, source provenance,
code identity, library/settings, and a contact sheet. This tests whether temporal
observations contain information beyond stale coordinates and whether native
tracking diagnostics can expose uncertainty. Synthetic image shifts/occlusion
are not physical camera motion, moving-object tracking validation, calibrated
confidence, semantic reacquisition, collision safety, or manipulation success.

Each shifted sequence contains one coordinate jump followed by nearly static
frames; the 25 subsequent rows are not independent moving-target tests. The
31-pixel occluder hides the original local patch, while pyramid levels can still
use broader surrounding image context. A successful native status under this
occlusion is insufficient evidence of local visibility; it does not by itself
prove the inferred coordinate is incorrect.
