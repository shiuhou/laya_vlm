# Current research beliefs

## Latest bounded repair — 2026-10-07

Observed: [POINT+BOX repair](docs/p1-identity-prompt-results.md), clean execution
`b7f5409`, yields0 task-valid candidates.50 POINT rawcalls completed,23 typed
POINT admissions,7 originalBOX contradictions,16 SAM calls/48 masks. On25VISIBLE
wrist frames only2typed points match front,7do not,16unavailable. Agentview25UNKNOWN
remains unscored for semantic correctness. Original50labels/results were exposed:
matched reused-development diagnostic only, no independent acceptance.

Observed matched8wrist frames: outside proposals9,226→9,149; median contamination
94.218%→96.808%, no aggregate benefit. Two contradiction masks removed1,532outside
proposals deterministically; this is not a prompting gain. One correctPOINT is
excluded by oldBOX; the other produces a front-focused mask(native1,71.33%purity)
whose original tool-support gate rejects, while broad masks still propose tabletop.

Inference: positive-point containment alone does not establish target-component
or candidate identity; this exact addition is insufficient. Confidence high for
recorded measurements, low for generality/correct-prompt performance(only1correct
POINT reachesSAM). Against a simple 'all segmentation always useless' explanation:
one native mask localizes the front better. Against complete sensing invisibility:
wrist labels remain25VISIBLE. Against missing-depth explanation: all48 masks
availability1.0. Fixed-reference/VERIFY and continuous tracking still unproved.

Falsifier/next decision for review: independent prospective target-part association
and usable tool support without weaker gates, labels/oracle policy inputs or an
additional model compensating for unknown geometry. Do not auto-tune this example
or reopen decoder budgets. No P1 pass, no final scientific Gate C, no temporal/P2/
Qwen/Laya run. Six focused tests and independent source/scoring/image audits pass.
The original Formal-50 and development checkpoints below remain historical.


## Current implementation milestone — 2026-10-07

Latest observed result: [Formal-50](docs/p1-formal50-results.md), frozen clean
execution `e1ff472`, is COMPLETE.50 frames,150 native masks,0 inference failures,
0 retries,0 task-valid front candidates. Wrist25/25 human VISIBLE; agentview
25/25 UNKNOWN. Wrist BOX covers full target21/25 but median97.48% contamination;
50/75 wrist masks disjoint from target.33 masks generate45,252 geometric points,
all outside the human front region. Agentview0 candidates,68 plane-support
rejects +7 ambiguities. All-image inspection and two independent audits agree.

Belief: semantic-region specificity and segmentation part identity are the
strongest supported current interface bottleneck. Depth availability alone
is insufficient; a valid plane may describe tabletop/cavity. Confidence high
for these frozen observations, limited for generalization. Against a pure
camera-unobservability explanation: wrist has25 VISIBLE human regions. Against
a pure depth-dropout explanation:139/150 native masks have availability1.0,
only1 depth-availability gate fails. Components/plane rejection also remain
material; failing before tool evaluation cannot establish tool impossibility.
Falsifier: a future prospective identity-supported sensor condition produces
correct tool-interior candidates across independent initializations without
weakened geometry gates. No such condition is claimed here.

Next proposal: one scoped P1 grounding/identity representation repair (B),
not temporal qualification or a final sensing Gate C. Wrist is a better current
development source, neither camera control-qualified. Reference/VERIFY UNKNOWN.
**P2 remains blocked pending Formal-50 / temporal P1 gate**; Formal-50 complete,
temporal evidence unearned. Stop for review. No PUSH/Qwen/Laya/tracker run.
The historical checkpoints below keep their original context/status.

Previous observed result: the user-authorized
[mask-support repair](docs/p1-mask-support-results.md) at `5f97166` replays all six
sealed masks with zero model calls. Availability is1.0 for all six; all remain
AMBIGUOUS_DEPTH_COMPONENTS, candidates0. Narrow-mask components1924/1756 and
2776/2249 show the actual next boundary after denominator repair. Plane/tool
support and semantic identity remain unknown. Confidence high for these recorded
measurements, low for generalization; no claim of absent physical surface.
DefaultBOX2 and legacy-mask6 outputs match; thresholds/order/gates unchanged.
**No more init25/26 development tuning.** Frozen50-frame annotation/observability
evaluation is now the next milestone; its input/code/label/BOX packet is pinned,
native evaluation-mask corpus pending under this round's no-inference rule.
Formal candidate identity must be judged separately against human regions; an
outside-region point fails semantic identity, never becomes task-valid success.

The user subsequently selected the README/three-document implementation route:
Qwen3-VL brain → Laya local choice → continuous RGB-D geometry/deterministic servo,
with model contribution measured later by B0–B4. The paused exploratory research
record below is historical; the approved P0/P1 implementation work has resumed.

The bounded [P1 observability closure](docs/p1-observability-closure-results.md)
concludes **Gate C**. Observed: unchanged original tool-interior candidates have
positive drawer-region support at0/25 init states; median wrist BOX contamination
is97.48%. Complete inventories contain locally valid overlapping support at21/25
BOX searches and25/25 full-frame searches, which does not establish target identity.
Reference support overlaps25/25 visible agentview annotations, but fixedness and
the closed relation remain UNKNOWN. Ten fresh temporal recordings have zero
initialized target chains; continuous tracking is unproven. Three exhaustive live
cost runs publish stale geometry, not target-specific tracking evidence.

Inference: BOX-to-surface association is the strongest supported drawer bottleneck,
with geometry ambiguity and sensing limits still relevant. Confidence is high for
these frozen conditions, low for generality. A separate sensor-only segmentation/
sensing development condition that earns original-gate target patches and reliable
fresh continuous association would change this conclusion. No such acceptance has
been established. Reference POINT no-EOS work is closed; no budget/query/decoder repair continues.

The [completed BOX/SAM2 development diagnostic](docs/p1-segmentation-results.md)
adds a concrete interface finding at `b5ada28`: all six native masks retained,
four broad masks depth-ambiguous, two narrow masks rejected at22.004/36.783%
original-BOX depth coverage before component/plane checks. Zero candidates.
Observed: strict deterministic dense-grid repair passes raw-byte coordinate/PE
equivalence; no learned weights/gates/query change. A reporting-only partial
failure and explicit fresh-process continuation are preserved.

Inference: the original BOX-area depth gate conflates intentional outside-mask
UNKNOWN pixels with unavailable sensor depth. High confidence for this arithmetic
boundary; narrow-mask semantic identity, plane quality and actual tool support
remain unknown. Broad-mask part contamination is visually supported, with lower
confidence outside these two development views. No universal SAM incapacity claim.
Falsifier/next test: a prospectively specified mask-support measurement contract
could reveal whether sealed narrow masks have useful plane/interior support;
passing geometry still must establish target identity before tracking. No mask
winner or downstream execution is implemented automatically. The subsequently
authorized denominator repair is recorded above; this paragraph preserves the
earlier diagnostic hypothesis rather than scheduling further development tuning.
P2/Qwen/Laya/PUSH remain off. Historical evidence and annotations remain immutable.

## Historical exploratory stop record

**PAUSED at the user’s request.** Local tag: `research-checkpoint-20260927-paused`.
No experiments or automatic retries are authorized while paused.

Updated 2026-09-27 after iteration057. Baseline: `share_main` at `b73b5b4`.
Integration branch: `research/embodied-interface-discovery`; not merged/pushed
into `share_main`. Historical detail remains in the
[research log](docs/research/autonomous_research_log.md) and
[evidence index](docs/research/research_evidence_index.md).

**No competent hierarchical sensor-driven manipulation architecture has yet been
established.** The current responsibility hypothesis is semantic localization
for target proposals and calibrated deterministic geometry for local approach.
Neither tested high-level VLM planning nor Laya motor ranking has earned a larger
role. This is provisional allocation from bounded evidence, not universal model
incapacity or a completed sensor-driven manipulation system.

## What we currently believe

| Claim and kind | Evidence | Remaining uncertainty / confidence / falsifier |
|---|---|---|
| **Observed:** goal completion and interaction-valid manipulation differ. | Frozen drawer: official success3/3,122primitives, exact970control replay. Later native audit finds zero raw designated pad/handle rows in48,500snapshots. Strict Task2 has no qualifying witness among729pairs before22; an alternative trajectory later also becomes contract-empty. | High for recorded boundaries, not continuous causal attribution or impossibility. Falsifier: independently qualified intended-contact/full strict feasibility trajectory. |
| **Observed:** correct supplied context does not suffice for tested Laya ranking, and tested VLMs have not earned planning. | Situation/action/progress interfaces do not repair weak native choices. Seven-option sensed approach chooses maximal supplied gain2/6 and increases distance2/6. Matched3B/7B scene tests have coherent relations0/6 each; primary subgoals equal each model's task-only control. | High within inspected development fixtures; low generality. Different menus cannot be pooled. Falsifier: a prospectively new capability/interface transfers to held-out choices and behavior. No more local wording/prefix sweeps. |
| **Observed:** semantic points plus deterministic geometry can guide a local sensory approach and enable a local grasp slice. | Fresh guarded whole/neck approaches replay472controls exactly with zero raw contacts; both end near the neck despite very different own-goal errors. Adding one stationary GRASP interval establishes bilateral pads before10mm lift at both anchors; sampled lifts maintain200/200 per native stage and move bottle~9.4mm. | The grasp/lift suffix is scripted, one init; establishment contains transients. Command completion is not grasp completion. No full Task2, autonomous grasp, clean continuous interaction or Laya-policy claim. Falsifier: changed source or prospective sensor-selected relation handoff fails. |
| **Observed:** native localization admission depends on decoding procedure on two selected images. | Hybrid POINT rejects moved bottle with mixed POINT/BOX output; slow admits present[218,193] and away[228,328],10tokens/EOS each. Exact inputs audited; root sees both on bottle. Two separate nativehybrid BOX calls admit current bottle rectangles,12tokens/EOS each. | High for these calls only. No per-step hybrid trace, proven MTP bug, general AR superiority or ownership certification. Old malformed prefix stays invalid. Falsifier: fixed procedure fails a prospectively different relevant image. |
| **Observed:** current support representation can dominate candidate admission. | Stale1340point support makes all four cached/fresh goal records chooseFWD. Full current depth vetoes all moves; partial own silhouette leaves a housing-edge FWD witness. Current BOX: present1220points includes40 inside current handproxy and selectsSTOP; away2250points has no candidate containment and selectsFWD. | Root inspected complete witness overlays. BOX is not segmentation; raw/masked depth is not verified environmental support. High for source-bound vetoes, not safety. Falsifier: independently evaluated current geometry yields useful pools and survives actual execution. Do not fit a mask margin to these edge pixels. |
| **Observed:** temporal motion carries some retention information but does not establish ownership/holding. | Full dense close/open tracks retain descriptive median contrasts across local executor archives; tails include unflagged~200mm depth-surface switches. Same-track2D contrast needs no scene depth. Matched closed-empty source: present lift9.402435mm, away0 with zero raw robot/bottle contacts. Postevent image motion medians4.198/0.0588px but availability492/365 differs. | All failures/nulls retained. Smooth tracks and low residuals can follow robot/background. No calibrated holding classifier or certainty threshold. Falsifier: frozen features fail prospective physical/capture regimes; a valid classifier needs independent positive and hard-negative evidence. |
| **Observed:** own-state history and calibration help, but timestamps/relations remain distinct. | Robot-only FK matches recorded poses; native wrist-history ranking improves over endpoints on one trace. Jaw proprioception reveals continuing motion after first GRASP. Matched scene refresh shifts recorded own packets' retrospective native-state match from2ms to4ms before endpoints. | Joint-coordinate separation is not physical pad gap or holding. Exact live sample times stay unknown. Rendered edge depth can mix surfaces despite tiny projection error. High for arithmetic/source facts, low for transferable contact/holding inference. Falsifier: frozen sensor features fail a new contact regime or calibration. |

## Immediate experiment and its decision rule

The current BOX comparison is complete; see
[fixed-goal support findings](docs/evidence/autonomous_research/task2_postevent_box_support_findings.md).
It preserves every candidate and all41present witness pixels. The upper BOX edge
meets the visible gripper/neck boundary; precise depth ownership remains unknown.
No ROI trimming, fitted margin or new self mask follows.

The next experiment is the preregistered
[two-action fresh-reset retargeting pair](docs/research/task2_short_retargeting_trajectory_proposal.md).
Two away-scene resets regenerate the29action sensor-selected prefix and explicit
+0.35m object scene intervention. Same currentBOXsupport; cached-hybrid versus
refreshed-slow goal. Existing rule predicts cachedDOWN/freshFWD at boundary0.
At most2moves per arm, own-state feedback, one exact replay each. Archived model
outputs can be reused only under exact RGB-D/K/T/own input-equivalence checks;
no archived controls initialize collection. This is a one-time combined packet
intervention, not pure freshness or continual visual-model feedback.

Root has authorized one batch conditional on clean implementation freeze,
no-world preflight and independent mechanical review. Contact, validation or
replay failure halts the remaining batch; no retry, recovery or budget extension.
Implementation/review completed, but the first launch exited1 at the preflight
matching gate before creating its batch directory or any worker/world. No
controls/actions/model calls occurred; no diagnosis, repair or retry followed.
**No physical retargeting result is claimed. Work is now paused by the user.**
If first-arm failure leaves the second unrun, report a partial contrast with no
comparative winner. Compare both arms against the same fresh sensor goal; it is
not proven bottle material or official task success.

## Closed lines and preserved boundaries

- Binary predicate probes, generic effect/action/prefix variations and the
  tested model-size control did not earn a planner or motor-model deployment.
  Do not repeat them without a new falsifiable capability mechanism.
- Render sampling and point-goal incompatibility investigations establish local
  measurement limits, not a newly calibrated collision/holding gate.
- Production `runtime_core.py`, `adapters/libero.py` and `decision_interface.py`
  remain byte-identical to baseline. Experimental hooks do not fork production.
- Simulator truth, sensor observations, proprioception, calibrated geometry,
  learned estimates and unknowns remain separate. Candidate admission and
  external oracle aborts also carry provenance; a source replay is not safety.
- Matched scene source is observationally qualified, but its original matrix
  remains interrupted/incomplete143. A separately recorded second away replay
  passed; no recollection occurred, and first interrupted-replay activity is
  unknown. Never relabel the original matrix PASS.
- Raw evidence/failures stay under canonical `runs/`; hashes and reports are
  tracked. A fresh clone does not contain all raw data. Clean only proven
  duplicates, obsolete downloads and reconstructible inactive artifacts.

## What would justify the next architectural step

A model proposal must be useful under a matched downstream intervention;
current identity, obstacle support and interaction state must be distinguished.
A successful short approach does not establish grasp, holding, placement fit,
full task completion or generalization. Identical-init repetition establishes
repeatability only. Preserve a development/evaluation boundary before tuning.

Build a new component only when the observed failure requires it. The next
physical probe tests realization of the chosen goal interface; it does not by
itself earn high-level planning or settle the missing relation verifier.
