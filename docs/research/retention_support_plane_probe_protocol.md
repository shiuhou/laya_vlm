# Exploratory offline table-plane observability probe

Frozen before numerical plane fitting, 2026-09-27. The analyst has already read
the paired diagnostic, seen its outcome images and evaluator labels, and knows
the table correspondence failed. This is explicitly post-outcome exploration,
not a prospective physical condition, held-out validation or retention test.

Use only the sealed RGB-D artifacts of
`interaction-observability-paired-01`, all 33 frames per arm from step 12 onward.
Do not collect new physics, change seeds, replay, adjust cameras or alter sensor
tracking. Use the original assistant-selected table pixel `(171,290)` and one
fixed 31 by 31 pixel patch centered on it (inclusive x 156–186, y 275–305).
The patch radius is selected now; it was not part of the original preregistration.
The point has semantic tabletop attribution by visual annotation, not by an
autonomous support detector or evaluator mask.

Backproject every finite patch depth in the existing validity range 0.01–5 m
using recorded calibration and pixel centers. Fit a total least-squares plane
to all admitted points. Orient its normal toward positive world z. Preserve
valid count, centroid, normal, signed offset, covariance eigenvalues and the
complete signed residual distribution summaries. Report RMS, median absolute
and maximum absolute residual, both within each frame and against the seed
plane. No RANSAC, outlier trimming, patch search, robustification or tuned
acceptance threshold. A nonplanar or occluded patch remains a result.

Check camera calibration stability and all 961 patch RGB/depth values across
the trace. Report signed distances of the existing bottle and table point
estimates to the seed plane and corresponding changes. Do not correct any
off-bottle correspondence. Report failed table tracks as unknown.

For the first transition only, repeat the frozen LK call with OpenCV's
`OPTFLOW_LK_GET_MIN_EIGENVALS` diagnostic flag (which changes its error output),
and report native forward status and minimum eigenvalue for all three original
seeds against the unchanged `minEigThreshold=0.0001`. This is an explanation of
the recorded failure, not a replacement point or a revised tracker.

No oracle object pose, segmentation, geometry ID, contact or success label is
an input. Save and hash the sensor-only output before further evaluator
comparison. Do not call an interior visible bottle landmark's height a bottle
bottom clearance, support separation, holding probability or retained load.
Even a stable table plane cannot exclude another support or establish complete
object extent. The output is a camera/support-reference feasibility observation
in the already inspected development trace. Runtime `holding` remains unknown.
