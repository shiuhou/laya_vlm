# Current research beliefs

Updated 2026-09-27. Living research memory, not a record of established competence.
The autonomous mission starts at `b73b5b43dbef29749677fae06b25e94ca27bad87`.
See [research log](docs/research/autonomous_research_log.md) for experiments and
the [first protocol](docs/research/predicate_verification_protocol.md).

| Belief / status | Supporting evidence | Against / unresolved | Confidence | Falsifier / next test |
|---|---|---|---|---|
| Observed: frozen privileged drawer goal completion is reproducible, but not designated handle manipulation. | Three fresh 122-action runs and exact replay; interaction audit measures 0 mm valid closure. | Contact attribution includes ambiguous transitions; no global causal attribution. | High within recorded runs. | Independent replay/contact audit contradicts recorded results. |
| Hypothesis: correct semantic subgoals alone will not repair all Laya motor decisions. | Explicit-consequence experiment leaves true closing 0/8; local-objective choices also have unexplained effect ranking. | Historical 11-action interface differs from the current 27-primitive reference. | Medium. | Correct grounded objectives reliably repair matched choices on current-interface and held-out states. |
| Observed: binary predicate verification also fails in the tested interface. | 768-call audit: balanced accuracy 56.45%, strong affirmative bias; exact controls and repeats. | Framing, negative-label spelling and clause interpretation remain confounded; current interface differs. | High within fixtures, generality open. | Spacing/single-clause or current-interface controls demonstrate a narrower cause. |
| Observed: current visual grounding is not full object geometry. | First LocateAnything box plus depth produces a point; no mask or contact estimator; archived support purity 11.7–52.5%. | Offline sensor centroid already backprojects points; richer deterministic geometry may help. | High for implementation; efficacy unknown. | Code/evidence demonstrates validated richer sensor-only geometry or relations. |
| Hypothesis: support contamination matters more than depth projection on archived drawer views. | Centroid errors of centimetres versus millimetre ray/depth residuals. | Point referents, temporal fusion, and calibration can confound comparisons. | Medium. | Same-frame raw recomputation attributes error mainly to another component. |
| Open: VLM planning is necessary or useful. | Semantic decomposition is plausible; controlled visual subgoal and visible-relation probes now exist. | The tested 3B VLM does not improve scored subgoals over task text; simple visible-relation responses are largely invariant. Model capacity and interface remain competing explanations. | Unestablished beyond these negative fixtures. | A pinned stronger-model control recovers image-sensitive relations/subgoals, followed by a matched downstream benefit. |
| Open: strict bottle-in-drawer placement is mechanically reachable. | Valid grasp/partial transport exist; transform recomputation is exact. | Both known routes dead-end; containment site equivalence to actual close envelope unverified. | Unestablished. | Valid full mechanical witness, or demonstrated specification/mechanical contradiction. |

## Update after first experiments

- **Observed, high confidence within fixtures:** binary verification is not reliable
  in the registered presentation: sensitivity 100%, specificity 12.89%, balanced
  accuracy 56.45%; all original controls/repeats reproduce. This rejects the simple
  explanation that only eleven-way competition fails while predicate recognition
  is already sound. It does not isolate conjunction versus framing/answer wording.
- **Observed, high confidence within archived views:** sensor support differences
  exceed same-support ray/depth residuals in all 18 raw-reconstructed frames.
- **Observed:** a fixed sensor-only depth split reduces median centroid error
  79.20 to 9.06 mm, but nominal direction agreement only 10/18 to 12/18, with three
  adverse directions still present. This weakens “improved XYZ alone suffices.”
- **Next falsifiers:** fixed single-clause and answer-spacing controls; current
  numeric-interface reproduction; semantic POINT versus BOX using the existing
  LocateAnything checkpoint. No new architecture is earned yet.

## Update after iteration 002

- **Observed:** all ten exact current motor calls reproduce the frozen successful
  run, including probabilities and logits. At advance boundaries 9/10, Laya
  chooses `open` with predicted closure 1.756/0.056 mm while admitted alternatives
  predict 34.177/31.888 mm. Correct local objectives and complete effects therefore
  do not ensure strong immediate progress. This is not a counterfactual full-task
  or interaction-validity result.
- **Observed:** the 1,184-call predicate decomposition does not rescue recognition.
  With the spaced negative label, all closed-goal cases receive the negative
  answer and all open-goal cases the positive answer, including both single-clause
  conditions. Per-goal balanced accuracy is 0.5. Pooled scores obscure this failure.
  Incomplete Boolean coverage prevents a general conjunction-capacity diagnosis.
- **Observed:** POINT grounding completes with EOS on 18/18 frames and produces
  9 target hits, 5 misses and 4 mixed-output unknowns. All six hard late cases
  remain unsuccessful. Clear lower-handle errors show unresolved target identity.
- **Observed:** fresh BOX prefixes reproduce all archived boxes, but 9/18 outputs
  reach the generation cap and another is malformed without EOS. Historical
  prefix acceptance hid incomplete generation. Parsed output is not proof that
  generation completed; completeness must remain an explicit admission variable.
- **Inference, moderate confidence:** adding a semantic high-level planner alone
  is unlikely to resolve both identified downstream bottlenecks. Neither a VLM
  planner nor a live POINT adapter is justified by these results yet.
- **Next discriminator:** unchanged current motor payloads through the existing
  local Qwen provider. This tests whether another provider-plus-adapter can use
  the evidence; it does not isolate model size/training or establish a hierarchy.
  Stop prompt micro-tuning on the predicate corpus.

See [iteration 002 findings](docs/evidence/autonomous_research/iteration_002.md).

## Update after current-provider control

- **Observed:** the existing Qwen text provider does not rescue the two advance
  choices. It chooses `close` at boundaries 9/10 (1.748/0.05684 mm predicted
  closure), despite admitted `y-40mm` effects of 34.177/31.888 mm with no worse
  reported fields. This is a provider-plus-adapter result, not a general model claim.
- **Observed:** it then returns literal `17` at boundary 87, violating the native
  action-ID interface. The run stops: 10 planned, 5 observed, 4 valid, 1 invalid,
  5 unattempted. Every observed answer has EOS and verified greedy logits; output
  budget and truncation are not the cause. No repeatability or full-run success.
- **Research decision:** do not patch IDs or continue a motor prompt search. Test
  the simpler existing deterministic nominal-distance selector on a sensor-derived
  coarse-approach slice, against Laya with the same state and natural gates.
- **Parallel discriminator:** one pinned general VLM may contribute visual target
  verification. It must reject lower-handle proposals while retaining correct
  proposals; scene description alone is not useful evidence. This earns neither
  a planner nor a live verifier before results exist.

## Update after visual verification and approach controls

- **Observed:** Qwen2.5-VL-3B returns `target_handle` in all 28 primary calls:
  12/12 correct-target retention but 0/2 wrong-handle rejection per repeat. A
  marker-only intervention on four frames also yields the same label for all
  16 calls, including eight markers on clear tabletop. Actual images, tokens,
  logits and EOS are audited; image interventions change logits. This fails the
  fixed categorical marker-binding interface, not proof that images are ignored.
- **Observed:** Laya selects GRASP in all 12 full-pool nominal-approach calls,
  despite the explicit instruction to translate and preserve the gripper. All
  ten naturally admitted candidates, state and effects fit without truncation.
- **Observed, independently audited:** removing only gripper/rotation families
  yields BACK,FWD,FWD,FWD,FWD,BACK, exactly repeated. Four choices reduce supplied
  point distance; two increase it. Two of six equal the deterministic sensor
  optimum. Family admission improves menu compliance but does not ensure useful
  direction selection. No further prompt/menu search is planned on these fixtures.
- **Observed abstraction issue:** absent POINT covariance forces STOP in current
  fusion/gates. Supplying a small conditional projection covariance would permit
  translation despite unknown semantic identity. Neither inventing covariance nor
  semantic confidence is an honest fix. Missing semantic evidence also appears as
  confidence 0 in the existing projection, which differs from unknown correctness.
- **Next empirical boundary:** an explicitly different fresh-point coarse-approach
  admission policy, with unknown covariance/velocity/semantic confidence preserved,
  directly supplies the existing geometric selector and native executor. It bypasses
  probabilistic temporal fusion. A rule-versus-active-hold physical diagnostic with
  external oracle contact abort will test this limited boundary; it is not a
  validation of the generic fused runtime or manipulation competence.

See [visual and approach findings](docs/evidence/autonomous_research/visual_and_approach_findings.md).

## Update after coarse physical approach and first boundary failure

- **Observed:** fresh POINT plus the existing deterministic geometric selector
  reduces TCP-to-handle-center distance from 227.258 to 88.945 mm in 20 native
  actions. Matched active hold ends at 227.272 mm. Both execute 160 controls;
  both replay with zero state error. No contact, drawer motion or task success.
  This is a sensor-driven coarse approach, with external oracle contact abort,
  not Laya motor competence or validation of the default probabilistic fusion.
- **Observed:** evaluator-only rays hit the designated handle for all 21 points
  in each 20-action arm. Every recorded rule recommendation is also unchanged
  when recomputed with the initial point: repeated semantic grounding has not
  shown a decision contribution on this static target/camera slice.
- **Observed:** a separately declared fresh 40-action boundary probe reproduces
  the first 20 actions exactly, then stops after 25 actions on an incomplete
  258-token POINT output. All 200 controls replay exactly; no contacts or executor
  violations. The first semantic error precedes that stop: at boundary 21, a
  structurally valid point jumps 74 pixels / 154.331 mm from the visible handle
  to the drawer interior. Four RIGHT actions follow. Handle-center distance keeps
  improving while gripper/handle surface gap worsens 34.673 to 38.098 mm.
- **Observed:** the old target's 21-by-21 RGB patch is byte-identical through the
  failed boundaries; this is not full target occlusion. Default retrospective
  optical flow retains the point, but a frozen pixel is equally sufficient in
  this stationary scene. Flow status does not establish semantic correctness.
- **Inference, moderate confidence:** semantic identity continuity is a distinct
  bottleneck from projection accuracy and arithmetic action ranking. Freshness,
  valid syntax and positive distance progress do not establish correct identity.
- **Next discriminators:** exact frozen RGB calls in two fresh process orders to
  distinguish image-specific failure from inference history; fixed synthetic
  translation/occlusion controls to test correspondence against frozen pixels.
  Neither changes live policy, substitutes old truth, or invents covariance.

See [physical approach findings](docs/evidence/autonomous_research/coarse_physical_findings.md).

## Update after first-failure controls

- **Observed:** all six frozen-RGB POINT calls reproduce archived tokens and text
  in two fresh process orders. Wrong-referent boundary 21 and malformed boundary
  25 each reproduce cold. Prior episode inference history is not necessary for
  either failure; this is not a claim of universal model statelessness.
- **Observed:** fixed default RGB correspondence follows three synthetic image
  shifts with maximum error 0.001167 px versus frozen-pixel errors 8/8/11.314 px.
  Both target-patch occlusions stop on reverse native-status failure; forward
  status alone remains successful. Static control/off-target occlusion continue.
  No residual-to-probability mapping, real camera-motion or identity validation.
- **Decision:** do not expand a tracker/recovery architecture around the one known
  failure. Test the originally proposed visual high-level role directly using
  the same frozen VLM: full-camera RGB versus task-text-only local-objective
  proposals on visually distinguishable archived Task-2 states. Marker-binding
  failure is insufficient evidence that high-level planning is also ineffective.
- **Guardrail:** provisional subgoals do not certify grasp, placement fit, or safe
  closing. The new test must preserve ambiguity and measure useful coverage so
  always returning unknown cannot count as competent planning.

See [failure controls](docs/evidence/autonomous_research/point_failure_controls.md).

## Update after direct visual subgoal test

- **Observed:** on three prelabelled visual phase cases, the fixed Qwen VLM answers
  `establish_grasp` throughout, exactly matching its task-only prior: useful label
  agreement 1/3 in both conditions. All seven scheduled calls are valid and
  complete; the last unscored image changes the answer to `uncertain`. No claim
  that RGB is ignored, or that all high-level reasoning architectures fail.
- **Open competing causes:** scene/relationship reading, binding visible facts to
  objective vocabulary, and task-prior interference. The three late images are
  deliberately unscored: proposals cannot be judged as physical certificates.
- **Parallel next tests:** VLM image-relation reading with task/mirror controls;
  Laya use of an ideal coherent supplied situation with unchanged action effects;
  sensor observability of retention in an existing grasp/lift prefix. Each owns
  an isolated worktree and assigned compute, without runtime integration.

See [visual subgoal findings](docs/evidence/autonomous_research/visual_subgoal_findings.md).

## Update after supplied situation sufficiency

- **Observed:** one coherent, truthful paraphrase of the current privileged
  target/phase/intent/relation changes all four Laya motor choices, but retains
  weak advance effects and reduces both approach gains. All 16 calls are valid,
  both repeats exact, and all eight baseline logits reproduce archive. No
  truncation, candidate/effect/order change, or new oracle observation.
- **Limit:** this rejects sufficiency of one packet, not every possible coherent
  worldview. Input length/positions change; no visual acquisition is tested.
  Bare `open`/`close` action IDs only implicitly identify gripper commands in the
  original heading, leaving action-to-effector binding as a concrete confound.
- **Next discriminator:** one fixed canonical action-definition condition against
  the original baseline, separately registered. This is an actuator-meaning test,
  not another situation-wording search or instruction to select an effect winner.

See [situation findings](docs/evidence/autonomous_research/worldview_sufficiency_findings.md).

## Update after parallel action, visual-relation and retention probes

- **Observed:** canonical action definitions alone leave both weak advance choices
  at `open` and change both approach choices to less productive rotations. All
  16 calls repeat exactly and every baseline reproduces archived logits; longest
  treatment consumes 1,012/1,024 tokens. Definitions change model behavior without
  establishing that the model applies their meanings. The joint situation plus
  action-definition intervention remains a separate, bounded sufficiency test.
- **Observed:** the 3B VLM's composite relation probe has 9/12 invalid outputs.
  The separately frozen single-field follow-up has 24/24 valid outputs, but returns
  `aligned` for all horizontal questions and `uncertain` for every gap/orientation
  question, across real, mirrored, gray and absent images. Useful scene agreement
  is 2/18 fields and 0/6 coherent scenes. Native pixels, forward inputs, greedy
  logits and EOS were audited. This distinguishes format compliance from useful
  scene understanding; it does not establish inability of all VLMs.
- **Decision:** acquire one pinned same-family 7B VLM and repeat the exact 24
  single-relation plus seven subgoal calls. Preserve inputs, labels and inference
  settings and audit processor equivalence. This isolates a bounded checkpoint
  intervention before drawing an architecture-level conclusion; no model tournament.
- **Observed:** in a paired fresh close/lift versus open-jaw/lift diagnostic,
  assistant-initialized body-point RGB-D motion is +109.810 versus 0 mm while TCP
  moves +114.133/+114.320 mm. Both complete 17 primitives/136 controls and all 272
  newly recorded controls replay with zero state error. This is a scripted sensor
  diagnostic with privileged source primitives, not an autonomous grasp policy.
- **Observed limitation:** the cap track samples off-bottle depth starting at
  step 14/control 5 despite successful flow and 0.0011765-pixel round-trip error.
  The tabletop track immediately fails. Co-motion is useful here, but neither
  semantic correspondence nor automated support separation/retention is validated.
  Bilateral pad relation flickers while the bottle continues moving; the independent
  audit identifies continued contacts on both physical fingers during that interval.
- **Provenance correction:** historical collector metadata says human annotation;
  an append-only erratum records Codex assistant RGB annotation. Exact annotator
  model/session provenance is unavailable. Do not claim autonomous LocateAnything
  initialization, human labels, calibrated holding, or real-sensor validation.
- **Next falsifiers:** independent seal/contact/replay audit and a fixed exploratory
  RGB-D table-plane probe; a mechanically justified same-closed-command retention
  control if one can be established. No runtime `holding=True`, policy integration,
  full Task-2 continuation or new task success is earned by these results.

See [action definitions](docs/evidence/autonomous_research/action_semantics_binding_findings.md),
[visual relations](docs/evidence/autonomous_research/vlm_world_understanding_findings.md),
and [sensor observability](docs/evidence/autonomous_research/interaction_observability_findings.md).

## Update after joint sufficiency and independent sensor audit

- **Observed:** W+A selects the same actions as W on steps 0/1/10: rotations
  with 4.128/7.282-mm gap gain and gripper close with 0.05684-mm drawer closure.
  All six calls exactly repeat and root independently reconstructs every actual
  consumed token/option marker and selected predicted effect. There is no repair
  from combining these particular prefixes. Step 9 was prospectively excluded:
  full 1,085-token input exceeds 1,024, with no truncation or model call.
- **Next interface discriminator:** a single existing progress number duplicated
  verbatim into each native criterion, with the entire original state preserved.
  This tests placement/association/salience jointly, not pure semantic binding.
  Full six-column relocation is infeasible for the advance pools under the native
  256-token heading/options cap; total input count alone can hide option clipping.
  No model setting, ranking, pruning or task policy is changed.
- **Observed, independently audited:** 30 retention checks pass, including all
  188 sealed sensor artifacts, independent LK and backprojection. A fixed 31×31
  table RGB-D patch remains identical across all 66 frames and fits a plane with
  0.001284-mm RMS residual. The table LK eigenvalue is below its native texture
  threshold. Failed image tracking therefore does not imply missing depth geometry.
  These are ideal static-depth internal residuals, not real-sensor accuracy.
- **Limit:** bottle-body point height over that plane is 18.237→128.046 mm versus
  18.237→18.237 mm. This is not bottle-bottom clearance, exclusion of other support,
  or a retention classifier. Exact annotation-model provenance remains unavailable.
- **Next physical control:** one fresh initial POINT followed by that fixed observed
  world point and live proprioception, under the same bounded coarse selector and
  executor. It tests whether repeated semantic reacquisition is necessary in this
  static slice and exposes the next physical boundary. Target age remains stale;
  captured later RGB-D is logged but not consumed for target updates. This does
  not establish moving-target competence or repair generic uncertainty gates.

See [joint sufficiency](docs/evidence/autonomous_research/joint_interface_sufficiency_findings.md)
and [independent retention audit](docs/evidence/autonomous_research/retention_independent_audit.md).

See [initial findings](docs/evidence/autonomous_research/initial_findings.md) for
independently audited counts, source identities, limitations and example failures.

## Responsibility and evidence rules

- A model answer, simulator success flag, and interaction-valid task outcome are
  separate measurements. Oracle-conditioned model answers are not expert labels.
- Candidate membership, objective routing, history, witness search, and completion
  signals carry provenance, just as coordinates and predicted effects do.
- Unknown contact/holding remains unknown without a legitimate estimator/sensor.
  LocateAnything box presence is not calibrated confidence.
- Raw clouds belong in perception/evidence by default. Laya currently consumes
  text (1,024-token agent limit), not RGB or point clouds natively.
- The VLM/Laya split, primitives, representations, and task choice can be revised
  when evidence supports a change. Preserve controls and distinguish interventions.
- Identical-init repeats measure repeatability; archived init states are development
  data. Generalization requires prospectively held-out physical conditions.
