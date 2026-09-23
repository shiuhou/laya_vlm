# Engineering demo: claims and evidence

The demo proves inspectable RGB-D → Laya → atomic executor → MuJoCo connectivity.
It does **not** prove useful drawer manipulation, task competence, decision
sufficiency or a useful oracle reference.

## Supported path

`engineering_demo` is the live entry point; `demo_report` is the offline
report/inspection entry point. `demo_inspector` and `demo_feedback` are libraries.
The old --render-report alias and run_libero smoke runner remain for reproduction.

The synchronous visual path uses LocateAnything + RGB-D, temporal belief, compact
CDS and the existing visual gate's permitted nominal tokens. Choices pass
identity/expiry/membership validation before atomic execution.
Model history/effects remain empty. Simulator contact/progress/success are
evaluator-only. Tracking is inactive; covariance/probabilities are uncalibrated.

## Latest completed feedback episode

Eight Laya choices, nine captures and seven verified feedback deliveries.
All 64 recorded controls replay exactly at 73 checked boundaries.
Drawer closure **zero**, target contact **false**, task success **false**.
The preceding GPU-memory startup failure is retained.

This supports local control replay and traceability, not reproducibility of a new
model rollout or useful task-directed behavior. Gate changes alone do not prove
the model uses feedback well. STOP/GRASP/RELEASE may drift in loaded states.

## Evidence index

| Record | Scope |
|---|---|
| [Original connectivity](evidence/demo/visual_connectivity.md) | Historical four-action run, media, telemetry and environment |
| [Inspector runbook](evidence/demo/demo_runbook.md) | Reproduction and offline inspection |
| [Feedback episode](evidence/demo/closed_loop_demo.md) | Eight-action run, feedback and replay |
| [Decision autopsy](evidence/demo/decision_autopsy.md) | Decision-to-control trace/action semantics |
| [Translations only](evidence/demo/frozen_step0_translations_only.md) | Frozen vocabulary intervention |
| [Geometry sensitivity](evidence/demo/frozen_step0_geometry_sensitivity.md) | Frozen geometry intervention |
| [Distance effects](evidence/demo/frozen_step0_distance_effects.md) | Kinematic annotations did not rescue frozen choice |
| [Local objective](evidence/demo/frozen_step0_local_objective.md) | No rescue; contact premise confounds decomposition |
| [Position swap](evidence/demo/frozen_step0_position_swap.md) | Candidate-position sensitivity |
| [Synthetic direction](evidence/demo/synthetic_direction_probe.md) | Controlled directional semantics |
| [Negative-direction order](evidence/demo/synthetic_negative_order_probe.md) | Ranking/order sensitivity, not a policy repair |

Semantics/distance annotations alone do not establish useful atomic choice.
Local objectives remain a hypothesis. New live collection requires separate review.

## Artifacts and inspection

Raw artifacts are preserved in the main worktree's ignored runs/engineering-demo.
Historical checkout names in manifests are provenance, not required directories.
Fresh clones do not contain runs/media/model weights or external simulator setup.

Offline CLI help (no inference):

```sh
python -m embodied_runtime.experiments.demo_report --help
```

The runbook describes inspection of existing artifacts. Reporting can write
derived files; use copies when auditing archival evidence.
No new replay or collection is required to interpret recorded findings.
[Current state](current_state.md) supersedes all old next steps.
