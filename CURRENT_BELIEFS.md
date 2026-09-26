# Current research beliefs

Updated 2026-09-26. Living research memory, not a record of established competence.
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
| Open: VLM planning is necessary or useful. | Semantic decomposition is plausible; no controlled VLM comparison exists. | Jev comparison reused archived answers; deterministic routing and model quality were not isolated. | Unestablished. | Matched VLM subgoals fail to help or a simpler architecture matches performance. |
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
