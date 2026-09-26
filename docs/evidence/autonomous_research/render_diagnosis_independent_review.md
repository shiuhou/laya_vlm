# Independent stored-evidence render-diagnosis review

**PASS.** The native frames exactly reproduce the original pre24/pre25 RGB, optical depth, intrinsics and camera-to-world arrays. Changing actual multisampling from four samples to zero, with the recorded cache and other renderer configuration held fixed, changes depth substantially at several prospectively fixed witness pixels. This establishes a raster-sampling contribution to those measurements; residual pixel identity and scene clearance remain unresolved.

Producer freeze is `5b17822`; raw data are in `runs/autonomous-research/render-measurement-diagnosis-01`. The independent checker `embodied_runtime/experiments/render_diagnosis_evidence_audit.py` produced `render_diagnosis_independent_audit.json`. It rehashes all 12 sealed artifacts, compares saved native arrays against the original source arrays including dtype/shape/bytes, independently recomputes whole-frame differences and all **99** fixed neighborhood entries, and checks configuration and recorded cache/state-gate consistency. It performs no rendering, FK, projection, distance query, or dynamics.

The source review requested explicit native-versus-zero configuration guards before execution. The producer added them: geometry groups, collision/visual flags, framebuffer dimensions, depth mode, scene flags, integrator and timestep must match after buffer rebuild and after each capture. The stored result passes those guards. Native collision group 0 is disabled and visual group 1 is enabled. MuJoCo's actual sample count and GL bound-framebuffer sample count both report 4 natively and 0 after the intervention. RGB-D calibration remains unchanged.

| Boundary / fixed pixel (x,y) | Native optical depth (m) | Zero-sample optical depth (m) | Difference (mm) |
| --- | ---: | ---: | ---: |
| pre24 / (216,97) | 0.758036 | 1.471536 | +713.499 |
| pre24 / (237,102) | 0.761687 | 1.496464 | +734.777 |
| pre25 / (156,165) | 0.834427 | 1.216788 | +382.361 |
| pre25 / (236,145) | 0.793209 | 1.291032 | +497.823 |
| pre25 / (240,110) | 0.762937 | 1.420939 | +658.002 |
| pre25 / (156,155) | 0.834634 | 1.252815 | +418.181 |

The other four pre24 centers change by +0.904 to +1.387 mm; pre25 (119,126) changes by −1.123 mm. The full fixed neighborhoods, including unchanged/small differences, remain in the machine-readable evidence. No neighbor was selected to maximize an effect.

Whole-frame RGB differences affect 17,073 and 17,228 pixels; optical-depth differences affect 147,412 and 147,416 pixels, with mean absolute differences 3.615418 and 3.757131 mm. Counts include arbitrarily small floating-point differences and are not counts of mislabeled scene pixels. Maximum absolute depth differences are 1.599934 and 1.580974 m.

The separate cache comparison reports maximum projected-vertex discrepancies of 0.004568 and 0.004882 px between saved native geometry and own-qpos FK. The audit verifies saved pose-difference arithmetic and sealed identity, but does not rerun FK/projection. Small discrepancies do not prove they are irrelevant at every depth discontinuity. The controlled image difference and the numerical cache comparison are separate measurements, not a replacement mask or a complete causal explanation of every witness.

The producer recorded 402 exact archived-state gates and six copy/render-cache equality checks; this audit verifies their count, ordering and hash consistency. Actual replay states/full opaque MjData were not exported for independent reconstruction, so these live checks are supported by reviewed instrumentation and recorded gates, not a second replay. Counts distinguish bootstrap (10 controls, 250 `mj_step`, two `mj_step1`, 509 forwards), prefix reconstruction (200 controls, 5,000 `mj_step`, 10,000 forwards), and diagnosis (zero controls/steps/forwards). The source used GPU 4 and exact images were reproduced on assigned GPU 5 without retry.

The producer disclosed ignored EGL cleanup exceptions after numerical sealing and process exit 0. They do not alter the sealed arrays or successful equality gates; they are retained as an execution limitation rather than omitted from the record.

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `6e8d7db6edb80ad04692da0cf887aea14e63eb03360bef1c00e2a2b626750194` |
| `measurements.json` | `8b8c288538b89d707b84b931a9bef658f337c91edf26779994095b4c864462b4` |
| `output-seal.json` | `e3ea43709c6f6bf553e787ab032ad4bf4941c5c2fca7e2193517850bd33b9cec` |
