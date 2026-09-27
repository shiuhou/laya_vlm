# Current research beliefs

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
Implementation/review are pending. **No physical retargeting result is claimed.**
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
