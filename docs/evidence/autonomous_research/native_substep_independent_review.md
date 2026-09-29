# Independent substep review: control-end contact sampling missed DOWN contact

The paired diagnostic demonstrates contact aliasing in the unchanged native
execution. `MV_DOWN` has nonhandle finger/panel contact in **seven integration
calls**, although all eight ordinary after-control contact lists are empty.
Its original commands, states, full result, 1.406205 mm drawer motion and failed
2 mm translation contract reproduce exactly. The apparent sampled-contact-free
progress witness is therefore not physically contact-free.

Independent pre-dynamics review covered the protocol, source and seven new
synthetic/source tests. The hooks pass through the native integration/forward
calls, record all contacts and forces without extra forward calculation, use
separate joint position/DoF addresses, detect observer changes to the native
integration state, restore hooks on failure and stop before another control if
the exact reference comparison fails. Additional Cartesian applied forces and
smooth generalized forces were included before freezing. No numerical outcome
motivated an instrumentation change.

The [independent checker](../../../embodied_runtime/experiments/native_substep_evidence_audit.py)
imports no producer helper or simulator. Its
[portable result](native_substep_independent_audit.json) passes all 2,451 record
hashes/chain links; frozen preflight/reference/source identities; 400 prefix and
16 native controls; 400 integrator calls/800 snapshots; direct joint/force and
contact-membership arithmetic; six artifact hashes and trajectory arrays. Both
full native results match the seven-arm reference exactly. The reviewer made no
physics, FK or model call.

| Measurement | MV_RIGHT | MV_DOWN |
| --- | ---: | ---: |
| Integrator calls / snapshots | 200 / 400 | 200 / 400 |
| Calls containing robot contact | 112 | 7 |
| Before/after robot contact cache rows | 224 | 14 |
| Maximum recorded normal force | 6.912957 N | 14.913734 N |
| First observed contact: control / call within control | 0 / 22 | 1 / 20 |
| Integration interval containing first direct drawer motion | 10.544–10.546 s | 10.590–10.592 s |
| Original after-control robot contact rows, summed | 5 | 0 |
| Endpoint translation error | 1.650032 mm | 2.114787 mm |
| Frozen translation contract | Pass | Fail |

All recorded robot contacts concern `gripper0_finger1_collision` and
`wooden_cabinet_1_g11`, outside the designated handle set. DOWN's contact call
indices are `[45, 57, 81, 107, 135, 162, 187]`, one in each control 1–7. Each
call has before/after cached contact rows. These rows must not be counted as
14 separate impacts, nor may 14 ms be reported as an exact contact duration.

DOWN's first direct drawer movement occurs in the same integration interval as
its first recorded nonhandle contact. Joint velocity changes from zero to
0.006334777 m/s. The drawer constraint-force component is 9.830527 N before and
9.818904 N after that call; its applied, actuator, passive, bias and smooth force
components are zero at the first observed contact. All recorded Cartesian
applied body forces are zero. This force/motion chronology supports the
nonhandle-interaction explanation for drawer motion. It does not independently
isolate the cause of the full endpoint tracking residual or quantify a unique
causal contribution from that contact.

The recorded integrator is Euler, timestep 0.002 s. Native code performs two
forward calls per integration call: the environment loop and controller update
both call `sim.forward()`. The logger counts 400 native forwards per arm and
adds none. Contact/geometry/force buffers after integration can represent an
earlier solver stage than their associated advanced qpos/time. The explicit
integration intervals preserve this distinction; the trace does not recover
continuous first-touch time or certify absence between finer samples.

This completes the decisive experiment proposed in the
[earlier information-boundary review](information_boundary_review.md). Its
historical “zero sampled contact” results remain correct. Its unresolved
within-control alternative is now observed. No valid contact-free progressing
native option has been established by these measurements, and information alone
still does not explain the action/controller failure.

The next justified observational question is whether the same sampling issue
affects **canonical Task1's historical interaction attribution**. Task1's
reported 0 mm designated-valid closure is an after-control measurement. The
current DOWN finding does not prove hidden valid handle interaction in Task1.
A separately frozen exact archived replay with unchanged historical selectors
and thresholds can attribute movement to observed finer contact classes without
changing policy or claiming causality. This independent review performed no
such replay.

Producer freeze: `ef5a4e0`; raw directory
`runs/autonomous-research/native-substep-observability-run-01` under the main
checkout. Raw SHA-256:
`7fce36f5df64da7009d3ddb71b98f01d2383065c13d3b88069af39aed997337a`.

```sh
python -m embodied_runtime.experiments.native_substep_evidence_audit \
  --raw-root /home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research \
  --output /tmp/native-substep-independent-new.json
```
