# Prospective independent local grasp-interface review

**PASS for frozen producer `ef58bf9d8f0f3238f4fb36ef14268ef183958cb4`**, before dynamics. This receipt covers the bounded two-arm diagnostic registered in `local_grasp_interface_protocol.md`, including its one verification replay only if both arms complete. It is not a result or a change to the execution contract.

The experiment invokes the existing `AtomicExecutor` through the unmodified bottle backend. That backend retains its 10 mm translation step and unchanged execution validator. GRASP maps to native close, STOP holds the retained open command, and MV_UP preserves the arm's jaw command. No new primitive, policy, search, recovery or model call is introduced.

The archived source, all sealed sensor/image artifacts and exact prefix are gated before intervention. Initial state and each comparable control's commands, sensor observations and evaluator/state are compared exactly, excluding sensor wall time. Prefix images/calibration use the same capture schedule. Actual observed states are recorded before equality checks so first-mismatch evidence remains available. The full state chain provides before-state equality from the preceding checked after state.

Native instrumentation is confined to the registered two primitives, wraps live `mj_step` while bypassing scratch objects, retains raw before/after contacts and wrist buffers, checks integration-state fingerprints and restores the original function on exit. Per-action counts require 200 calls and 25 per control. Sensor/evaluator/render operations additionally guard integration state and selected geometry, site, camera, sensor and acceleration caches. The previous sensor reader's forward call targets its scratch data, not live data.

The strict >0.05 N oracle abort allows gripper/bottle contacts and rejects other robot/external contacts plus robot self-contact, symmetrically across pair order. This broad allowed contact group is distinct from the positive witness's bilateral designated fingerpad relation. The abort is evaluated after the current atomic operation and cannot prevent that contact.

Any mismatch, unchanged-validator failure, contact abort, invalid count or runtime error exits the entire two-arm loop. There is no automatic continuation to the other arm, no threshold relaxation and no recovery action. Replay rejects failed/incomplete collection and checks exact clean source, protocol, jev repository, installed stepping sources, package versions and environment before constructing a world.

The positive sampled-endpoint criterion is now explicit before measurement: all four validations pass; close-arm bottle-center rise is positive and exceeds the open arm; close has bilateral contact at all eight lift endpoints and open has none. Native-stage maintenance is separate and requires bilateral relation in both stages of all 200 lift integrations. Neither claims continuous-time contact, verified support-free retention, autonomous grasping or Task-2 completion.

I independently ran `tests/test_local_grasp_interface.py`: **6 passed**, covering fixed actions, rejection of execution failure/count errors, exact source matching, hook restoration/scratch bypass, contact thresholds/pair order/self-contact, and mutation guards. The producer separately reports 22 focused tests. No physics was run during this review.

| Reviewed file | SHA-256 |
| --- | --- |
| `embodied_runtime/experiments/local_grasp_interface.py` | `e3feb7e6f2c167e14816a3fb8f79b9b4d0b422c54b8b9b233f1f3cd4b48a7783` |
| `docs/research/local_grasp_interface_protocol.md` | `2a90ef10c6b4f625876bbff7cf42fd0da638d1775f4de726069e667585c08eee` |
| `tests/test_local_grasp_interface.py` | `458b7e3bf6974ba7944234d437de72e2502fde5ed7570b3b9d2d48dd0bd68bef` |

## Pre-physics infrastructure amendment

Approval also covers **`9b85ad5bb48de68e097b233afef8ecfd84cdb993`**. Attempt 01 at the prior freeze failed during source introspection because LIBERO's path had not yet been installed; no world/reset/control/capture occurred. Its terminal log remains a failed setup attempt. The protocol now records this explicitly and requires a separately named attempt 02 after an import/source preflight without a world.

The reviewed change calls the existing `jev_libero.environment.load_libero` with the original root/config before installed-source introspection in collection and replay. That function runs the native path/config preparation and imports modules without constructing a world. Scientific actions, execution thresholds, measurement logic, abort scope and acceptance criteria are unchanged. The six focused tests are unchanged; no additional physical validation is claimed by this amendment.

The amended source SHA-256 is `17b5ec197ae55cdba6b4e0bd0725a4093c19760ed1446bd7f7c50037724291c7`; amended protocol SHA-256 is `fa620b16f7a61ef3882352ed7386c013f3eb9ad1d690f3d7d785a334776bb6a2`. The prior test-file hash remains valid.
