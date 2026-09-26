# Frozen Task2 observed-surface nominal sweep diagnostic

The root approved the narrow implementation of the [reviewed proposal](task2_observed_surface_sweep_proposal.md). Its source limits, retrospective status, competing explanations, seven-candidate completeness and prohibited interventions all apply. This protocol fixes the concrete worker, input and output details before the first archived pose/proximity computation. No simulator construction, rendering, dynamics, controller, inference, action selection, feasibility change or new mask is admitted.

## Registered source and admission

The source hashes are the proposal's collection journal, initial frame, saved sensor representation and sealed calibration, additionally pinning calibration03 `static-setup.json` to `cd500c2464cd9692796e89ce5a9ce1485576d8ba8c17398a490b89f8f2be2bab`. Reuse unchanged `robot_only_geometry.py` SHA `c8563e80070a7081a43c9d92d1f6f86446732c77964c2c55665ab76bd32d147c` and `sensor_gripper_proximity.py` SHA `4f52b9e168cdb802daca4eea1bd26115750957430e1e5e1fe89ec47fba233db6`.

The no-world preflight reads the actual hashed files, validates the approach journal chain, reproduces original inner G with the identical row-major arithmetic and scalar conversion used by `task2_box_support.sensor_representation`, and requires exact Python-value equality for every pixel/depth/world-point row in saved G. It also requires exact row equality when those inner pixels are selected from full BOX support. Numerical inverse-K substitution is disallowed. Retain exactly the existing inclusive 0.01–5 m depth validity and half-pixel centers. This admission may construct initial sensor point packets, but it does not place own geometry or compute any own-point distance.

The fixed half-open bounds are inner `[212,169,224,210)` and full `[208,156,228,223)`. There is no label filtering, target-point repair or neck-query input. The two pose packets are zero-based step 21/control 0 and step 22/control 0 `previous_returned_own_observations`. Retain only returned grip-site position, eef-body xyzw quaternion and signed finger joints. Preserve original source record IDs/read times and unknown exact observable times in the adapter receipt, outside the numerical worker. Static initial support persistence across approximately 8.4/8.8 s remains unverified.

Source inspection confirms current World construction uses ControlEnv defaults, whose Panda selects PandaGripper. The preflight compares current static gripper XML body transforms, named signed slide-joint definitions, exact pad boxes and grip-site local mount with the sealed own calibration, and pins current XML/code/hand/finger STL bytes. No STL compilation, compiled mesh reexport or task scene inspection is added. These current checks and the sealed compiled calibration support a conditional proxy calculation; they do not prove historical asset-byte identity. That gap is a report limit, distinct from the exact Task2 replay. A demonstrated current static mismatch stops admission.

## Worker boundary and geometry

The numerical subprocess receives only `request.json` with these four fields:

- `calibration`: hand-root identity subtree, one grip site, named signed finger joints and all five sealed own collision vertex sets;
- `own_packets`: exactly opaque `sample0`/`sample1`, each containing only the three returned fields above;
- `full_support`: row-major records containing only pixel coordinates, unmodified depth and backprojected world point;
- `inner_indices`: ordered exact subset indices into full support.

RGB, cached P, raw archive path, source step/action selection, contact/force/classification, scene model/state, success labels and evaluator metadata are absent. The adapter may read its complete historical journal to extract the permitted fields; feature computation occurs in the separate sanitized worker. Numerical output is sealed before contact evaluator extraction or witness RGB inspection. The condition is retrospective and the producer already knows the outcome; this process boundary does not make it blind or held out.

Use the unchanged pure FK helper only on the normalized gripper subtree rooted at `robot0_right_hand`. Discard arm/base transforms and encoders. Calculate the calibrated body-to-site mount, map each proxy into site coordinates, and place it with returned site origin and body quaternion multiplied by the fixed mount. Keep the signed snapshot jaws and orientation fixed over each nominal motion. No direct/native jaw qpos, cached site rotation or contact-frame pose is substituted.

Canonical output order is FWD, BACK, LEFT, RIGHT, UP, DOWN, STOP. Translations are the original world ±X/±Y/±Z 10 mm; STOP is zero nominal displacement, not an integrated hold. For each separate convex proxy V and displacement d, current=conv(V), endpoint=conv(V+d), sweep=conv(V ∪ (V+d)). The union across five proxies is minimum distance / logical OR containment, never a combined hull that fills jaw gaps. Use the existing triangle/hull distance and 1e-12 numerical half-space tolerance. No physical safety margin or fitted threshold is introduced.

## Complete outputs and evaluator

For each of the 2 samples × 7 candidates, one NPZ retains current/endpoint/sweep distances, closest solid points and containment booleans for **all full-support pixels × all five proxies**. Inner results use exact subset indexing. Each mode/support retains all per-proxy and union minimum distances, contained-point counts, exact-minimizer counts and one deterministic primary witness (row-major pixel then calibration proxy order). Arrays preserve every tie and contained pixel, so later plotting cannot hide alternate witnesses. Empty support returns `minimum_m=null`, `nearest=null`, count 0.

`features.json` records every registered candidate, each array hash, all summaries and the placed own vertices/mount. A separate `feature-seal.json` hashes the complete feature directory. Only then does `evaluator-after-seal.json` append the actual selected token and all raw robot contact rows for steps 21 and 22; the other six candidate outcomes remain null. Step 21 DOWN has the observed no-raw-contact outcome and step 22 FWD has the first raw pair. The later >0.05 N DOWN crossing at step 24 remains a different boundary. No observer buffer time is promoted to a continuous-time onset or exact sensor sample time.

All seven results remain in canonical order with no ranking, filtering, action selection or feasibility flag. Full BOX is a superset, so lower minima alone are tautological. Sweeps contain their current solid, so swept minima cannot exceed current minima; any current containment makes all seven swept union minima zero. Report such degeneracy explicitly using retained endpoint/per-proxy data. Neither a positive finite point distance nor missing containment proves free space, object ownership, alternative-action success or grasp readiness. Nominal rigid sweeps do not reproduce controller tracking, orientation/jaw motion or contact dynamics.

## Verification and invocation

Before computation, pass analytic tests for mounted direct-site pad placement/signed jaws, arm/base exclusion and forbidden-field poisoning, rigid-pose covariance, original support arithmetic/ordering and inclusion, full-sweep interior containment, STOP equivalence, preservation of jaw gaps, current-overlap degeneracy, deterministic ties, empty support and canonical filtered candidate order. Reuse the existing tested point-to-hull geometry. Run a real-source preflight without own placement or proximity features, preserve its receipt, and obtain independent prospective PASS identifying the clean exact code commit.

Entry: `python -m embodied_runtime.experiments.task2_observed_surface_sweep --preflight --output RECEIPT.json`; then, after independent PASS, `--output RUN --review REVIEW.md`. The adapter requires a clean producer, copies the protocol/review, seals sanitized inputs, invokes one numerical worker and seals all output before evaluation. Preserve a failed computation/partial artifacts without changing registered geometry rules or automatically retrying. Report generation may read sealed arrays and source RGB after completion; it cannot alter scores or add a policy.
