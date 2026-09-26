# Integrity replay of sensor probe v1

Frozen after the paired probe and before replay, 2026-09-27. This validation uses
the **newly recorded diagnostic** low-level controls. The archived Task-2 gate
provided primitive names, not these controls. Do not call the new probe an
original archived control replay.

Create one fresh standard benchmark init-0/seed-1 world for each condition. Do
not restore simulation/controller state. Apply the 136 recorded 7-D controls
per arm in original order, bypassing primitive feedback recomputation. Compare
the full 51-value simulator state at reset and after every control with the
recorded evaluator state; require exact equality. Keep actual timings and stop
at the first mismatch without retry. No rendering, new decisions, policy,
recovery, sensor adaptation, additional physical condition, or task continuation.

This checks that passive scratch FK, sensor reads, rendering and recording did
not change the recorded dynamics relative to applying those same controls
without instrumentation. It does not prove equivalence to the historical gate
controller context, generalization, real sensor validity or full task success.
