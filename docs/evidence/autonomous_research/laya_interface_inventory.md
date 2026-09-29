# Laya decision-interface inventory

The six-translation-plus-STOP family with sensor-derived nominal geometric
effects **has already been tested**. The closest experiment is
`approach-family-run-01`, not the older six-action visual probes or the privileged
native-action reference. Its negative result rules out describing the seven-option
family as a new intervention. It does not establish general directional incapacity
or performance on the present POINT payload. This inventory reads existing source,
receipts and outcomes only; it performs no inference, fixture edit or execution.

## Closest completed sensor experiment

[Selector protocol](../../research/approach_selector_probe_protocol.md),
[family protocol](../../research/approach_family_control_protocol.md),
[findings](visual_and_approach_findings.md), and
[portable source extract](laya_interface_inventory_summary.json) bind these facts.

The ten-option parent used six archived perceptual drawer states: init0 steps
0, 20, 24, 29 and init1/2 step0. `make_fixture` reconstructs the sensor belief and
natural candidate builder, passes no oracle argument, and derives
`geometric_effects` from that state. It presents the structured field values,
one previous proprioceptive outcome when present, and a compact two-column effect
table. Nontranslation effects are null. All 12 calls chose GRASP.

The family control removed exactly GRASP, ROTATE_CW and ROTATE_CCW plus their
null effect rows. It retained the six moves and STOP, including receding moves,
in canonical order. The model-facing state, remaining effects, history,
descriptions and instruction are otherwise unchanged. The preserved audit
`source.canonical` still has the original ten-option evidence; this must not be
mistaken for the actual seven-option model input. Both runs used the same
`choice:6-10` temperature, `1.0000158548355103`.

| Init / step | Seven-option choice | Supplied-geometry gain, mm | Existing rule | Rule gain, mm |
| --- | --- | ---: | --- | ---: |
| 0 / 0 | MV_BACK | -7.4391783952069135 | MV_FWD | 7.213687858176221 |
| 0 / 20 | MV_FWD | 6.305732069684156 | MV_FWD | 6.305732069684156 |
| 0 / 24 | MV_FWD | 5.455470690633055 | MV_DOWN | 6.727017685866393 |
| 0 / 29 | MV_FWD | 5.560739689871156 | MV_DOWN | 5.850533791335294 |
| 1 / 0 | MV_FWD | 6.325049215553408 | MV_FWD | 6.325049215553408 |
| 2 / 0 | MV_BACK | -6.7954213329122215 | MV_FWD | 6.536877130664115 |

The portable extract retains all six full-precision rows. Twelve of twelve calls
were valid and all six repeated choices,
probabilities and raw logits were exact. Two of six choices maximize the supplied
nominal gain; two increase distance. These are geometric comparisons, not observed
physical outcomes. The rule is a deterministic comparator, not an expert label.
At steps24/29, the nonmaximal sensor choice actually has greater oracle nominal
gain than the sensor rule, exposing target-estimation bias.

The exact model question already says:

> Minimize TCP-to-target Euclidean distance with one nominal 10mm world translation.
> Leave the gripper unchanged. Choose STOP only if no translation improves distance.
> This is a geometric command test, not a contact or dynamics prediction.

At the same time, `state.task.instruction` says **“close the top drawer of the
cabinet”**. Global drawer closure and local approach are logically compatible in
a hierarchy, and the question explicitly specifies the local criterion. Its
absence cannot explain the result. Task priority or presentation is a possible
confound, not a demonstrated conflict, prompt defect or cause of failure. The
observed failures cannot distinguish that possibility from numeric comparison,
candidate binding, or another presentation/checkpoint interaction. This condition
contains no separate phase variable; the explicit local question itself already
provides the requested objective.

## Exact differences from the current POINT approach

The current physical collector never calls Laya. It records
`CanonicalDecisionInput`, applies the endpoint exclusions, and calls the unchanged
`rule_token` on the remaining candidates. Consequently there is no consumed
“current Laya payload” or current Laya result to compare. Stock serialization
methods are available, but their outputs have not been admitted to a model in
this completed pair.

| Layer | Historical seven-option family | Current fixed POINT approach |
| --- | --- | --- |
| State task | Global close-drawer instruction and handle identity | `Approach the cached reported point.` and `the wine bottle` |
| Question / phase | Explicit local Euclidean-minimization question above; global drawer task remains in state | Rule executes directly. Stock `model_questions()` would say `Choose for task. Offline probe, not safety approval. Null means unknown. Moves retain orientation/grip; rotations retain position/grip.` No model phase routing occurs. |
| Target estimand | Accepted historical RGB-D/fused visible-handle surface-centroid estimate; target identity unverified | Unchanged native whole/neck POINT, containing-pixel-center depth projection, admitted by exact initial frame match; identity and depth ownership unknown |
| Temporal / quality fields | Geometry and semantic validity, heuristic covariance, `covariance_calibrated=False`, semantic score, temporal consistency and velocity supplied when archived | Geometry finite under an unverified fixed-target assumption; age grows from initial capture. Covariance, semantic validity/confidence, temporal consistency, velocity, current visibility, holding and contact remain unknown. |
| Provenance | Perceptual belief and natural gate retained in audit; model gets compact field values | POINT query/projection and separate original full-BOX guard support retained in audit metadata; compact provider serialization would omit metadata |
| Effects | Same `geometric_effects` arithmetic; table carries shared source/assumptions and rows `[distance_change_m, xy_error_change_m]`; STOP null | Same arithmetic. Stock `provider_input()` emits per-token records with source, privilege, assumptions, geometry validity and named values; STOP has unknown source/empty values. No compact table rewrite occurs in collection. |
| Numeric presentation | Existing six-significant-digit model rounding; rule checked against rounded delta | Full precision logged; stock provider method would apply the same rounding. No current consumed-token audit exists. |
| Candidate admission | Natural ten-option pool first; explicit objective-family removal yields all seven | Seven created directly for an approach-only diagnostic, then unchanged geometric endpoint veto removes candidates. This is distinct from the old natural gate and objective-family removal. |
| Selection / STOP | Offline model choice; no action executed. STOP description means active hold, effect unknown | Deterministic eligible-set rule. Selected approach STOP terminates before execution, although shared candidate description still says hold. |
| History | At most one previous actual proprioceptive outcome | Same permitted history schema; actual histories differ with source trajectory |

For the completed POINT pair, initial and decision5 eligible pools contain all
seven options. At decision5, the physical/RGB-D prefix and exclusion lists match;
whole selects DOWN and neck FWD from their distinct targets. At both terminal
boundaries DOWN is excluded, leaving six candidates including STOP. A proposed
terminal “seven-option” test that restores DOWN would change the current guard
contract. Also, a model interpreting STOP as executed hold would not share the
approach collector's termination semantics. These are concrete interface issues,
not evidence that one anchor is a better grasp location.

## Other completed interface families

| Family / primary evidence | Menu and information | What is established / why it is not the same test |
| --- | --- | --- |
| [Frozen visual step0](../demo/frozen_step0_local_objective.md), distance/reflection/order controls | Ten visual atomic options; original drawer task. Step0 effects/history empty; local-objective intervention also adds a manual no-contact premise. | GRASP persists. Neither pure sensor approach-only framing nor current seven-effect payload. |
| [Translation-only reflection](../demo/frozen_step0_translations_only.md), [synthetic directions](../demo/synthetic_direction_probe.md), [negative-order control](../demo/synthetic_negative_order_probe.md) | Six moves; no STOP and no explicit effect bundle. Real reflected fixture or synthetic signed states. | Reflection pair selects FWD twice; signed/order controls expose order sensitivity. Do not generalize to all signed reasoning or call this the seven-option effect test. |
| [Paired reference pilot](../decision_interface/reference_pilot_handoff.md), [mechanism controls](../decision_interface/reference_mechanism_handoff.md) | Eleven atomic options; perceptual/oracle drawer states, original history, no effects supplied to primary replay. Mechanism suite has52 calls. | Matched states do not establish a useful no-effect motor reference. Explicit approach, mirror, masked-field, exact-command and order controls already exist. Stored collector geometry effects were marked `not_supplied_to_primary_replay`. |
| [Bounded interface search](../decision_interface/interface_search_handoff.md) | Eleven actions, synthetic and archived perceptual/oracle relations; smaller geometry sentences, neutral IDs/order, toward/away, explicit applicability. Separate DONE/CONTINUE judgments. |744 calls; some axis-only interfaces work but mixed/goal controls fail. Answer-equivalent upstream filtering is labeled. Narrow known-articulation status success is not motor competence. |
| [Status/effect gate](../decision_interface/reference_gate_handoff.md), [effect binding](../decision_interface/effect_binding_handoff.md), [provider comparison](../decision_interface/provider_comparison_handoff.md) | Known-state categorical status or eleven-action privileged drawer effect fixtures; true/shifted effects, goal/order/labels. | Some supplied-fact sensitivity exists. No reliable all-state motor reference; short sentence projection is distinct from complete CDS. |
| [Clause order](../decision_interface/clause_order_handoff.md), [selective grip](../decision_interface/selective_grip_handoff.md), [explicit consequence](../decision_interface/explicit_consequence_handoff.md), [goal placement](../decision_interface/goal_placement_handoff.md) | Same privileged eleven-action effect fixtures with fixed wording/layout interventions | These negative or mixed prompt controls are already complete; repeating variants is not a new information-boundary experiment. |
| [Native local-objective reference](../decision_interface/local_objective_reference.md), [action binding](action_semantics_binding_findings.md), [progress duplication](native_option_progress_sufficiency_findings.md) | Native Jev 27-action universe with oracle state, local-objective routing, privileged candidate filtering/effects. Recent selected boundaries have7,7,25,16 candidates; IDs include `x+40mm`, rotations, open/close. | These seven-option pools are not six10mm moves+STOP. W/A/W+A/progress controls already tested; rankings cannot be transferred to the sensor POINT menu. The instruction prefers substantial progress, not a newly invented strict argmax. |
| [Current provider comparison](current_motor_provider_findings.md) | Qwen on the privileged native motor fixtures; original Laya comparator |10 planned,5 observed,4 valid,1 invalid,5 unattempted repeats. Weak advance decisions precede transport failure; no complete repeat claim or sensor-interface rescue. |

## Is another bounded test justified?

No additional generic seven-option, explicit-approach, order, instruction-rewording,
or effect-duplication run is justified by this inventory. The closest missing
condition is **approach-only task semantics on the actual current POINT
states**, with a declared provider serialization and STOP contract. That is a
source/interface transfer gap, not evidence that a prompt change will rescue Laya.
Historical task priority remains an unresolved hypothesis; changing several POINT
fields and presentation together would not isolate it causally or establish a
prompt bug. The negative outcomes remain negative evidence for the tested inputs.

If a later architecture decision specifically requires whether Laya tracks the
current target change, the smallest distinct transfer question is the already
fixed whole/neck **decision5 pair**, whose physical prefix and full seven-option
pool match and whose existing deterministic selections differ. One frozen
presentation, one call per target and one exact reverse-order repeat would be
four calls. It would test bounded target-conditioned choice on those two inspected
development states only. No terminal state, mask, success label, rule winner,
upstream positive-gain filter or chosen contact premise should enter the input.
It would not establish arithmetic incapacity, physical usefulness, grasp-region
selection or superiority to the existing rule. This is a conditional design
description, not a registered or recommended execution; no fixture was constructed.
Without that concrete architecture decision, stop at the existing evidence.

## Raw identities and verification

Raw root is `runs/autonomous-research/` in the canonical repository.

| Artifact | SHA-256 |
| --- | --- |
| `approach-selector-run-01/episodes.jsonl` | `2ed444a6ee96519a60b276df0462c0230f227676365464a5e4df5e72c17a947e` |
| Selector independent audit | `16f30e6cd187b898a6108a25ff68c4e86496eb44f87793f94de7571ce03df72b` |
| `approach-family-run-01/episodes.jsonl` | `fe7007183616ca8883c5ea062ca736528e98b86b60c2005f57fbbb41c1a715a0` |
| Family independent audit | `c60e39e72be65241b4ef543a3bc658fd63f0947a171eca5a8c0d51effd9369d9` |
| Family report | `b812491c7d6716734403ef9cc5bbbf8021a2510b9a7420d48af5c243d27f7a17` |
| Current POINT interpretation | `bfb681e9913dfb154843542685b6ee140e90200b90601188e15b1e7160e90aea` |

The source extract verifies receipt hashes, reads the recorded fixture questions,
states and menus, and retains all six existing first-repeat result rows. Current
snapshots are copied from the already closed interpretation; no model input,
geometry, tracking feature or physical outcome is newly computed. Older rows
above cite their existing audited reports, not new independent reaudits.
