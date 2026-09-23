# Research direction and evidence boundaries

The adopted research direction is **Interaction-Structured Decision Interfaces for
Foundation-Model Robotic Manipulation**:

> In the absence of task-specific robot-policy retraining, what interaction
> structure must a physical runtime expose to a frozen foundation decision model so
> its closed-loop choices are interaction-valid rather than merely sufficient to
> trigger a terminal success predicate?

The research object is the complete decision interface: current state, predicted
effects, local objective and interaction semantics. The last term covers target
affordance, designated effector, required/maintained relation, geometric
compatibility and forbidden contact. It constrains what counts as valid progress; it
must not encode an action sequence or winning primitive. The aim is physically
meaningful, task-valid interaction, not human-looking motion.

The present phase is privileged and deliberately holds Laya, primitives, controller,
executor and MuJoCo preview fixed. RGB-D replacement, CLAP or other learned world
models, sim-to-real, real robots, RL, deeper hierarchy, model scaling and trajectory
efficiency are later extensions rather than current variables.

## Latest specification evidence

Task 1 and Task 2 expose the same missing distinction. Official top-drawer success
was reproducible 3/3, but a control-level audit found zero designated fingerpad/handle
contact; goal completion did not establish drawer manipulation skill. In Task 2,
LIBERO `In(object, drawer)` admitted a bottle configuration that obstructed later
closure; symbolic containment did not establish a closeable placement.

Generic contact-relation and articulated-frame geometry measurements now let TaskSpec
express designated interaction and placement fit. The latest strict Task-2 fresh gate
did not validate that interface end to end: it retained a bilateral grasp but reached
an empty one-step and two-step transport pool before placement. This negative result
is the current boundary. Interaction semantics have not yet been shown sufficient to
improve a Laya trajectory, and Task-2 Laya has not run.

## Scientific gate

The authorized [privileged drawer reference v1](evidence/decision_interface/privileged_reference.md)
tests the strong original-style architecture before ablation. One-step preview and
task contracts produced 18 genuine approach decisions, exact effects and then an
empty menu. Contracts perform candidate-policy filtering and remain unchanged.
Hard-invalid-only remains a possible later ablation only after success.
The bounded [dead-end boundary audit](evidence/decision_interface/dead_end_boundary_audit.md)
reconstructed the exact state and every primitive clause. Original Jev and the
reference have identical empty one-step pools there, so the result is classified
as a **CONTRACT DEAD-END**, not a port bug. The successful Jev trajectory avoids
that contract state through a materially different pose and closure-positive
contact transition. This does not prove physical continuation from the dead state
impossible, and the original runner's two-step witness fallback was not evaluated.
That fallback has now been evaluated separately in the
[two-step witness record](evidence/decision_interface/two_step_lookahead.md). It
found 23 witness-backed first actions on the exact state, including multiple
temporary-regression contact transitions with positive two-step net closure. This
weakens the claim that the original architecture lacks transition coverage.

In a fresh closed-loop run, Laya selected `open` from the complete 23-option
witness menu. Only `open` executed and its real effect matched prediction. The
next one-step pool contained only `z-3mm`. The subsequent
[forced-singleton run](evidence/decision_interface/forced_singleton_reference.md)
executed such singleton pools without calling or crediting Laya. Across 92 actions,
86 were genuine Laya decisions and six were forced continuations; net closure was
15.173 mm. At the first new failure, both one-step contracts and existing two-step
lookahead returned no candidates. Official success remained false. Existing
lookahead and forced continuations repair earlier local boundaries; they have not
established a successful flat Laya reference policy.

The subsequent local-objective run first stopped at a different boundary after
96.168 mm net closure: all 25 lookahead candidates existed, but their complete
witness presentation exceeded the input budget. A lossless compact serializer
then retained the same pool/order and rounded effects while factoring repeated
metadata. Frozen replay fit at 943/1,024 total tokens with no clipping. A fresh run
reproduced the 87-action prefix exactly, consumed that 25-option input, and continued
to 111.488 mm net closure. It stopped at the fixed 100-action budget with 40.171 mm
remaining and official success false. Prediction/execution fidelity stayed exact.
This removes input capacity as that boundary's cause; it does not establish useful
reference success or show whether continuation beyond the registered budget works.

The authorized budget-only continuation answered that bounded question. With the
same architecture and all policy/interface settings fixed, three fresh processes
each reached official success after 122 primitives. Each contained 111 genuine
Laya choices, 11 forced singletons and one lookahead recovery; all previews and
1,093 replayed control boundaries per run matched exactly. The opening curve was
monotonic with local plateaus, rather than oscillatory. This establishes a useful,
reproducible privileged reference under the local-objective condition.

Freezing and the later `TaskSpec` / `TaskAdapter` extraction did not add research
behavior. The annotated `privileged-drawer-reference-v1` tag preserves the original
successful implementation. All frozen model inputs/routing boundaries were
reconstructed exactly under the adapter, and three new fresh-process runs plus
control replay reproduced the same trace and success. This validates the refactor;
it is not a new architecture comparison or evidence that the task logic generalizes.

**Formal E0 has not begun. Its previous missing-reference prerequisite is now
satisfied only for this explicitly privileged condition; the next scientific
comparison and claim boundary still require a human decision.**
Oracle/perceptual agreement in the reference pilot did not imply useful progress.
GRASP at step 140 reopened the drawer by 14.272 mm, 21.261 mm worse than STOP.
An oracle-conditioned decision is not automatically an expert reference.

State Gap changes state evidence while holding effects/the decision problem fixed.
Effect Gap changes consequences with state/candidates fixed. The primary paired
State-Gap replay uses empty effects. Oracle preview, oracle-derived geometry,
deployable geometry, learned predictions and unknowns retain distinct provenance.
Evaluator outcomes cannot back-fill perceptual inputs.

The visible-handle surface centroid is not a rigid grasp pose. Unknown
contact/holding/progress remain unknown in visual state. Loaded controller
anomalies remain evidence; reset calibration does not prove exact nominal motion
or pose holding at every boundary.

## Research evidence index

Sibling *_protocol.md files are preserved historical specifications, not work orders.

| Record | Result and boundary |
|---|---|
| [Reference pilot](evidence/decision_interface/reference_pilot_handoff.md) | Agreement fails the usefulness gate. |
| [Reference mechanism](evidence/decision_interface/reference_mechanism_handoff.md) | Loaded/in-flight execution limits nominal assumptions. |
| [Interface search](evidence/decision_interface/interface_search_handoff.md) | Narrow status judgments can work; mixed geometry/atomic selection remain deficient. Precomputing winning axes transfers policy upstream. |
| [Reference gate](evidence/decision_interface/reference_gate_handoff.md) | Status missingness and consequence use differ; neither qualifies a manipulation policy. |
| [Effect binding](evidence/decision_interface/effect_binding_handoff.md) | Native/anonymous and absolute/STOP-relative effects separate presented consistency from physical utility. |
| [Provider comparison](evidence/decision_interface/provider_comparison_handoff.md) | Provider-specific offline controls, not a live backend replacement. |
| [Clause order](evidence/decision_interface/clause_order_handoff.md) | STOP-rule ordering is a presentation diagnostic. |
| [Goal placement](evidence/decision_interface/goal_placement_handoff.md) | Goal-last anonymous utility 9/16 → 11/16; native 0/16. Useful binding remains unestablished. |
| [Selective grip](evidence/decision_interface/selective_grip_handoff.md) | Native 0/16 → 5/16, opening only; closing 0/8. Wording matters but is not the sole deficit. |
| [Explicit consequence](evidence/decision_interface/explicit_consequence_handoff.md) | Explicit conjunction 5/16 → 4/16, no prior errors corrected; target predicates do not reliably repair ranking. |
| [Dead-end boundary audit](evidence/decision_interface/dead_end_boundary_audit.md) | Original Jev and the reference exactly agree on an empty one-step contract pool; the successful Jev path avoids the same pose regime. |
| [Two-step witness audit](evidence/decision_interface/two_step_lookahead.md) | Existing Jev lookahead returns 23 first-action witnesses at the dead end; closed-loop Laya selects `open`, then the acceptance gate stops at a singleton `z-3mm` pool. |
| [Forced-singleton reference](evidence/decision_interface/forced_singleton_reference.md) | Explicit non-model singleton execution yields 15.173 mm closure over 92 actions, then one-step and two-step processing both return an empty pool; success remains false. |
| [Local-objective privileged reference](evidence/decision_interface/local_objective_reference.md) | Lossless compact witness input repairs the 25-option boundary; after a budget-only extension, three fresh privileged runs each reach official success after 122 actions with exact preview/execution and replay. |

These are bounded correlated fixtures/repeats, not population estimates.
Anonymization, ordering and question edits are manipulations, not canonical
candidate representations.

## Related demo diagnostics

[Distance effects](evidence/demo/frozen_step0_distance_effects.md) and
[direction probes](evidence/demo/synthetic_direction_probe.md) weaken the simple
“only missing semantics” explanation without proving state/effects sufficient.
[Local-objective text](evidence/demo/frozen_step0_local_objective.md) also adds a
contact premise, so decomposition was not isolated.
[Directional order](evidence/demo/synthetic_negative_order_probe.md) and
[position swaps](evidence/demo/frozen_step0_position_swap.md) show ranking
sensitivity; ordering is not a solved policy.

Flat atomic ranking is under review. Missing physical state remains possible;
label interference, consequence binding and competition also remain plausible.
No clean result proves a hierarchy necessary, geometry-only effects sufficient,
or binary verification successful.

## Before further experiments

The reference boundary now includes existing two-step witnesses after an empty
one-step union, explicit forced-singleton execution without model attribution and
lossless presentation of a full witness pool. The registered privileged reference
has met its engineering success and three-run reproducibility gate. That success
does not identify which privileged component is necessary, validate the non-oracle
path or authorize an ablation automatically. The deployable judgment boundary and
effect sources remain open.

The next work is limited to observational classification of the frozen Task-1 trace
and exact audit of the frozen Task-2 transport boundary. It must preserve raw contact
evidence, allow an ambiguous attribution class and measure joint-axis compatibility
before choosing any new live threshold. A new feasibility or Laya run requires a
separate decision after that audit.

The earlier binary predicate proposal and conditional E0 plan are on hold.
Historical details remain in the
[explicit-consequence record](evidence/decision_interface/explicit_consequence_handoff.md),
[reference pilot protocol](evidence/decision_interface/reference_pilot_protocol.md)
and [integration review](archive/historical_handoffs/integration_checkpoint.md).
A next experiment requires one agreed falsifiable question and claim boundary.
[Current state](current_state.md) is the operational authority.
