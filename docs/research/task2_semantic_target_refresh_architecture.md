# Minimum target-refresh comparison after the four-POINT audit

A fixed stale guard can support a bounded **target-refresh effect on decisions**
comparison. It cannot establish a guarded approach to the relocated bottle's
current observed support. That stronger comparison needs a current BOX/depth
support packet supplied identically to both target arms at the shared boundary.
Four successful RGB POINT returns alone satisfy neither 3D admission nor support
refresh. This is source-only preparation: no new projection, geometry result,
model call, world, render or physical collection was performed.

## Existing interfaces and exact dependencies

Inspected the producer tree at `8cc19ebff9cec07eba4f416d35a157445b60f554`,
including the newer collection/replay hooks absent from the older sensor branch.

| Component | Existing behavior and consequence |
| --- | --- |
| `task2_closed_empty_point_adapter.analyze_rgb_return` | Admits native image coordinates only; explicitly reads no depth. Syntax admission and visual bottle localization are distinct. |
| `coarse_point_probe.admit_point` | Existing 3D convention: containing integer pixel, same-frame depth in inclusive 0.01–5 m, pixel center +0.5, saved K/T. Reuse this arithmetic after binding the completed raw token audit. Depth ownership remains unknown. |
| `task2_point_anchor_approach.source_anchors/point_decision` | Already separates POINT goal from BOX support. The helper still asserts cached initial-frame provenance; a refresh adapter must update metadata/source age without changing numerical rule/effects. |
| `task2_box_point_boundary.collect` | `decision_fn` receives the same fixed point throughout. Each movement already ends with RGB-D capture, but it never updates the goal. The current version has `after_approach`; a bounded experimental callback can reuse the verified approach prefix without a production runtime change. |
| `task2_endpoint_containment_veto.prepare_geometry` | Pins original BOX `[208,156,228,223)`, original RGB-D source and exactly 1,340 valid points. It cannot honestly prepare a different current BOX unchanged. |
| `task2_observed_surface_sweep.support` | Generic existing full-rectangle, row-major depth backprojection; retains every finite 0.01–5 m point. This is the reusable support primitive, not `task2_box_support.sensor_representation`'s inner crop or median-ray goal. |
| `EndpointSelector/endpoint_exclusions` | Accepts support/calibration independently of goal. Uses live returned own position/body quaternion/signed jaws, the audited mount, all five separate solids, nominal 10 mm endpoints and existing tolerance 1e-12. At identical own/support, exclusions are identical for both goals. |
| `CanonicalDecisionInput.rule_token`, `AtomicExecutor` | Keep strict nominal point-distance improvement, tuple tie-break, six translations and terminal STOP. STOP must be intercepted before the executor, whose STOP would execute a hold. Keep eight controls/200 integrations per completed move and the existing validator. |
| `task2_closed_empty_scene.event`, `verify_prefix`, replay hooks | Existing verified 29-action neck prefix, open-jaw post-event boundary and explicit +0.35 m/sham event can supply matched setup. Regenerate collection; archived controls remain replay-only. `before_action/after_replay` already support exact event verification. |

The cached comparator must be the archived **whole-bottle POINT** with the exact
question `Point to: the wine bottle.`, position
`[-0.11673469557117522, 0.058971097589474636, 0.9883583307522877]` m.
Using the neck POINT would additionally change the requested part. The historical
neck approach can remain common setup; both target arms switch to their registered
whole-bottle target source only after the scene boundary. This tests the effect
of observation refresh, including viewpoint/visible-surface changes, not pure
material correspondence or a relocation detector. A matched sham helps expose
those changes but is not required for the first away-only causal comparison.

## Two defensible designs

| Design | Held fixed | Defensible result and limit |
| --- | --- | --- |
| A: bounded retargeting with archived guard | Byte-identical original support/calibration, selector, rule, executor and action budget; only cached versus fresh POINT source differs. | Tests whether semantic refresh changes selected movements and a short executed response despite the inherited guard. The guard is explicitly stale after relocation; absence of its veto establishes no current bottle coverage or clearance. |
| B: bounded retargeting with common refreshed support | Obtain one native whole-bottle BOX on the shared post-event full RGB; use corresponding depth/K/T and unchanged full-support arithmetic. Give that exact new support packet to both target arms; retain selector/rule/executor. | Tests target refresh conditional on the same newly observed support. BOX remains unsegmented partial visible support, not object extent or clearance certification. If extended beyond the bounded interval, continued support freshness needs its own common capture/refresh schedule. |

Refreshing the old rectangle's depth does not relocate its semantic support.
Translating old points by the POINT difference would assume correspondence and
rigidity not supplied by POINT. A POINT-centered box/neighborhood, full-image
guard, support pruning or a new tracker would change the intervention; none is
needed here. B requires a small source/provenance adapter around generic
`support`, not a change to the containment policy. A short action budget does
not make A's stale support current.

For the smallest actual feedback trial, use the open-jaw **post-event/preclose**
boundary, never the later closed prelift boundary by convenience. Register the
away scene and two target arms, at most **two** existing translations each:
observe/select/act, then observe/select/act. The fresh arm uses a new cold
whole-bottle POINT at each executed decision boundary; the cached arm retains
the original 3D goal while observing its own current state. Both use identical
capture cadence, controller, guard design, candidate set and limits. A lone
action with only endpoint inspection is a one-step response, not evidence of
continued visual feedback. Preserve rule STOP without an equalizing hold,
nonadmissions and partial failures; no retries or fallback target. This cap is a
prospective experimental budget, not a new distance/contact threshold. Retain
the existing passive contact boundary and exact control/image/own replay.

Use the existing cold subprocess pattern for new native calls. Calling
`call_once` directly inside the collector would replace its SIGALRM handler and
cancel the outer timer via `signal.alarm(0)`; a subprocess preserves separate
call and collection wall limits. Freshness metadata must preserve unknown exact
sample times. A sealed old result reused after exact live RGB-D/K/T equivalence
is an explicitly archived sensor injection, not a newly timed model call.

## Cheapest decisive next experiment

After independent admission of all four actual POINT outputs, first run one
bounded **stored-sensor decision audit**, not a physical trial:

1. Bind each of the four predetermined source images to its own saved depth/K/T
   and named own packet. Apply the existing POINT projection to all four outputs;
   preserve every invalid depth/nonadmission without repair.
2. At each fixed boundary, evaluate cached whole-bottle and fresh whole-bottle
   goals with the same original support and own packet: at most **eight decision
   evaluations**, each retaining all seven nominal scores, per-proxy containment
   indices, exclusions, eligible set, unguarded token and guarded token. No model,
   renderer, physics or new support call is needed. Keep both post-event and both
   prelift results; neither chooses a more favorable physical start.
3. Report whether localization changes 3D admission, unguarded choice and guarded
   choice separately. Equal guarded choices show no immediate executable
   distinction at those sampled states, not general POINT uselessness. Different
   choices establish an actionable decision contrast, not achieved target
   progress. No dynamics are needed to resolve this first interface question.

This audit is the recommended next experiment. If physical current-support
behavior is the intended claim, choose B and obtain the common post-event BOX
before that trial. Otherwise A supports only the explicitly bounded stale-guard
retargeting claim. No code was added: the existing arithmetic suffices for the
decision audit; the physical refresh callback and B's support adapter should be
implemented only for the selected design.

Source hashes at the inspected producer freeze:

| Source | SHA-256 |
| --- | --- |
| `task2_box_point_boundary.py` | `a8ed44da4fce016fdb3cdaa06c4bb65447ea11d1e3b6772de60f12438a0e62cf` |
| `task2_point_anchor_approach.py` | `7081fe31ac0773086d97ac7a4f184e869748ca3f0737de0ac0e558f815b91bb6` |
| `task2_endpoint_containment_veto.py` | `a61ce7c1bbf15c317dcfd50b939765d0c121254c95ae9badb3ee70fa08ec35a6` |
| `task2_observed_surface_sweep.py` | `5d12ce8cf3389746b8e44e3b08b34f6cc2475ae5ac5e0d134476594c440b3e7d` |
| `task2_closed_empty_scene.py` | `697279c2d642130803a046470dbaa3ee8c5669a14777fd35d5d4424c66492315` |
| `task2_closed_empty_point_adapter.py` | `875abd9a8d4108e9c793754aed4c91f89ff3ce1f6d59a5e72173e1db2f819b83` |
| `coarse_point_probe.py` | `1448c7a4f4b3c4de02d0938e9951e352ae28437dab3c43885076eb9683914c70` |
| `decision_interface.py` | `92c87afe4b28e90bc50ec25293bb09ca6a93c8d52b598ae465e36d4d54f4c917` |
| `runtime_core.py` | `04be07b6be4d287d9b93e6376fb837cfa1a914eb0f81d9d2cf90b7c7f16763c7` |
