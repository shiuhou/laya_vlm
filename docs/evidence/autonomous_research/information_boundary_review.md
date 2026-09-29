# Information-boundary review: action and controller regime remain unresolved

The evidence does **not isolate an information bottleneck**. Recorded RGB-D has
nearby cabinet-surface support, and own joints plus known calibration recover the
robot's gripper geometry. However, the seven original options contain no
**execution-contract-valid, zero-sampled-contact, positive-handle-gap-gain**
witness at the inspected boundary. This is a local result for the retained open
jaw, orientation behavior, 10 mm request and eight-control execution regime.
It establishes neither global unreachability nor failure of a richer observation
to help. No model, controller, FK or physics was rerun for this review.

## Independent evidence checks

Review was read-only in the producer trees. After reviewing the completed
results, this separate worktree was created from main commit `eef21f3`.
The [standalone checker](../../../embodied_runtime/experiments/information_boundary_audit.py)
uses only stored files, Python standard libraries and NumPy; it imports no
producer helper, simulator, estimator or model. Its
[portable result](information_boundary_audit_summary.json) passes:

- All 2,971 seven-arm record hashes and chain links; matching frozen preflight,
  original source/reset/candidate/effect/protocol identities, software and
  simulator repositories; unchanged six controller-facing source files.
- All 1,400 replay commands and before/after states; 56 native control chains;
  21 rendered-artifact hashes and seven trajectory/control arrays.
- Exact original `MV_RIGHT` commands, states, contacts, complete native result
  and evaluator endpoint. All arms complete eight controls with gripper command
  −1. No native early termination explains an execution-contract failure.
- Independent contact/progress classifications, fixed-point gains, endpoint
  translation and rotation checks, unchanged contract thresholds, and direct
  drawer-joint displacement arithmetic.
- All 12 robot-probe artifact hashes and input/output seals; 264 stored numeric
  array comparisons; all eight poisoned packets and numeric outputs equal,
  including float64 signed-zero bits. No FK calculation was repeated.

Identity anchors:

| Evidence | Frozen producer / SHA-256 |
| --- | --- |
| Shared source `coarse-initial-point-02/episodes.jsonl` | `e09300d6ce11b86ba21339d92f52c86a24ac584f585a9fed8208ca51df7607cf` |
| Seven-arm producer | `e13bc36e3083bbd081669a4eb3e6724ffa3bed5c` |
| Seven-arm raw `episodes.jsonl` | `23a5e0ea9a59317ad843141a4ec0017958d0c180fdbc7c2aed90cf41697943fa` |
| Robot-probe producer | `554d2e7a23cbbfadd90ceefe019c263f1e5f86ed` |
| Robot `artifacts.json` | `8a23a3464173f37759342733d36f07dd92cb3bdae00b1c859d0c5349852ccb23` |
| Prior visibility evaluator `episodes.jsonl` | `ab277877b7eed50bf900bbf202f981af359e8ab18df90929003b4b7c576a8589` |

The successful robot run is `robot-geometry-observability-03`; its two setup
failures remain recorded. Seven-arm preflight01 failed before any world/control;
preflight02 and the first physical run completed. No outcome-driven physical
retry or revised validator is part of this review.

## What each information source establishes

The [visibility audit](first_contact_observability_findings.md) found an original
depth sample 1.655 mm from its retrospectively defined surface query. That query
uses privileged contact information to locate the inspected region. It shows
nearby raw surface support, not that a sensor-only method had identified the
hazard. Visual and collision geometry differ; the exact contact face, full
surface/free-space support and unstored contact-time depth remain unresolved.

The [robot probe](robot_geometry_observability_findings.md) receives nine own
joint positions and static calibration. Source inspection found no scene,
contact, target, camera or action input to its FK. Archive scenario labels are
opaque output keys. Its world-base transform is taken from standard task
construction and assumed known installation calibration; construction can depend
on static arena dimensions. It is not independently measured base/camera
registration. The process boundary is a reviewed serialization/code boundary,
not an enforced filesystem sandbox.

Its 21 body poses and two site poses agree with fresh same-qpos MuJoCo FK;
**collision extents cover only five gripper proxies**. Maximum position/vertex
error is `1.1103e-15 m`, rotation-element error `3.6638e-15`. Poisoning supports
independence from dynamic nonrobot state after extraction. It does not test
static-calibration independence or physical encoder/model fidelity. Both
implementations share compiled geometry. Fresh FK also does not recover the
historical contact-time cache; returned TCP sample times are unknown.

These two audits have not yet jointly produced a validated sensor-only
scene-to-gripper clearance estimate. Even such a measurement would require its
own scope limits: masking these five gripper proxies leaves other robot links
and all remaining surface identities unresolved.

## Seven actions distinguish point approach from physical continuation

Gains are before minus after, so positive values mean a smaller distance.
Contacts are recorded only after each complete 0.05 s native control. Every
recorded contact is nonhandle contact; the five `MV_RIGHT` rows have maximum
normal force 4.839181 N. The strictly-greater-than-1 N variant and the zero
nonhandle-contact variant identify the same sole raw progress arm, `MV_DOWN`.

| Original option | Fixed-point gain (mm) | Handle-gap gain (mm) | Sampled robot contacts | Translation error (mm) | Contract | Drawer joint delta (mm) |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| MV_FWD | +4.143665 | −0.036381 | 0 | 0.315646 | Pass | 0 |
| MV_BACK | −4.896673 | −1.492075 | 0 | 3.032152 | Fail | 0 |
| MV_LEFT | −6.359075 | −0.557487 | 0 | 1.380412 | Pass | 0 |
| MV_RIGHT | +5.069833 | −0.755405 | 5 | 1.650032 | Pass | +6.844671 |
| MV_UP | −6.207308 | −10.119414 | 0 | 0.962328 | Pass | 0 |
| MV_DOWN | +5.313088 | +8.466454 | 0 | 2.114787 | Fail | +1.406205 |
| STOP | +0.091299 | −0.674366 | 0 | 1.238022 | Pass | 0 |

`MV_DOWN` ends with TCP displacement `[+1.336996, +0.019224, −8.361588] mm`
against a `[0, 0, −10] mm` request. Its 2.114787 mm error exceeds the frozen
2 mm translation tolerance; rotation passes. This is completed but inaccurate
tracking, not a rejected command or proof that the controller can never reach
the target. Do not silently relax the validator to turn it into a valid witness.

The same arm moves the drawer by 1.406205 mm despite zero sampled contact rows.
This is **not proof of physical contact**, and zero rows are **not proof of its
absence**. Within-control contacts, other force pathways and sample timing were
not resolved. Its scalar gap gain also combines robot and handle motion; it
does not establish a useful grip or interaction affordance. `MV_RIGHT`'s direct
joint change is 6.844671 mm; its cached handle-center shift is separately
6.826182 mm. They must not be substituted for each other.

`MV_FWD` illustrates the objective mismatch: it validly approaches the fixed
point while slightly increasing the designated-handle surface gap. `STOP`
advances eight controls and drifts; it is not a frozen state. Exact native replay
and exact `MV_RIGHT` continuation provide strong local behavioral matching, but
the source lacks full intermediate observations/controller caches, so universal
hidden-state equality is not established.

## One next decisive experiment

Freeze one **paired `MV_RIGHT` / `MV_DOWN` within-control observability
diagnostic** from the same exact-history boundary. Retain the controller,
commands, eight-control duration, open jaws, validator and candidate semantics.
Record existing contacts and forces at every native integration step, including
nonrobot contacts and drawer motion/force terms, with explicit buffer-time
semantics. Insert no additional forward calculation, state restoration or
integration. Require the original commands and states at all eight control
boundaries to remain exact; an instrumentation-induced difference invalidates
the comparison. `MV_RIGHT` supplies the known-contact comparator.

The decisive question is whether `MV_DOWN`'s unobserved within-control dynamics
explain drawer motion and the tracking residual. Transient contact would remove
the apparent physical contact-free interpretation; continued absence would
require locating the recorded drawer force source. Either outcome improves the
mechanistic evidence without changing its failed native motion contract. This
is a proposed diagnostic, not a new policy, a tuned executor, or a claim that
information alone limits manipulation. No further experiment was executed here.

Reproduce only this independent file audit into a new output:

```sh
python -m embodied_runtime.experiments.information_boundary_audit \
  --raw-root /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research \
  --output /tmp/information-boundary-audit-new.json
```
