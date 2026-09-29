# Bounded reference-mechanism diagnostic protocol

2026-09-23. Baseline `0da1596`; follows Stage 4 and the E0 readiness audit.
Not formal E0, not policy improvement, and not a change to candidate/validity rules.

Question: why does the current no-effect oracle-conditioned reference fail to
demonstrate useful task decisions? Separate physical semantics from model-input
sensitivity. Existing observations are used to choose informative diagnostics;
these are targeted mechanism tests, not unbiased performance estimates.

## Physical intervention semantics

Replay the same archived 155 controls on benchmark init IDs 0/1/2, seed 1. Preserve
all source trajectories and native counterfactuals. Default boundary schedule:

```text
0: 0,24,29,33,48,80,120,140,144,153,155
1: 0,33,37,38,48,80,140,144,155
2: 0,35,36,37,48,80,140,144,155
```

These cover reset/far, precontact approach, first near-contact/contact, ongoing
contact/progress and late motion. Boundary 153 adds genuine <=10 mm near-completion
on init 0. Init 1/2 do not acquire nonexistent near-completion labels; 155 is terminal
only on init 0. Phase labels overlap and remain evaluator-only.

At each boundary, independently restore full Jev Snapshot plus backend gripper
command/last execution before every native one of the eleven actions. Log actual
TCP displacement/rotation, grip, drawer movement, contact, duration, contract flags,
controller goal errors and torque clipping. Record cached robot observation and
fresh forward kinematics separately: FK runs on **scratch MjData**, never forwards
or updates the native source simulator as an instrumentation side effect.

Repeat native STOP without wrappers to verify tracing does not change its endpoint
or mutable controller context. Check restoration after every branch using physical
state and integration/controller/robot/observable/RNG signatures. Full MjData is
restored; fingerprints do not assert support for arbitrary model-mutating tasks.

Three separately labeled STOP diagnostics form a 2x2 mechanism comparison:

- Native: existing entry target / feedback from `world.obs`, inherited orientation goal.
- Orientation reanchor: set only controller goal orientation to current scratch-FK
  orientation at entry; keep native position feedback and physical state unchanged.
- Fresh FK feedback: entry position target and per-control feedback from scratch FK;
  retain inherited orientation goal and physical state.
- Both: combine those diagnostic interventions.

The three variants are **not native candidates or proposed fixes**. No state settling,
velocity zeroing, threshold relaxation or action relabeling. Preserve eight-control
maximum and early-success termination, explicitly recording unequal durations.
Post-reset calibration envelopes remain descriptive, not universal safety bounds.

## Decision-model controls

Use accepted Stage 4 oracle fixtures and empty effects; do not feed independent
physical evaluator outcomes into the model. Keep eleven options so the checkpoint's
option-count temperature bucket is unchanged. Proposed bounded controls: baseline,
option-order reversal, neutral option aliases with original descriptions, masked
dynamic state, explicit nominal-distance-reduction objective, and a coherently
reflected geometric state under that objective. Add two instruction-following
sentinels, not robot-task success labels. Repeat identical inputs twice.

Capture exact payload/token audit, full API result including act/defer head output,
raw pre-temperature logits when supported, applied checkpoint temperature, actual
device/dtype and model-content identity. High returned confidence is not correctness.
These controls distinguish presentation and quantitative-state sensitivity from
task utility; they do not establish a useful closed-loop policy or exhaust hypotheses.

## Evidence discipline

Raw intent precedes probes/inference; completed evidence is fsynced. Record errors,
partial traces, restoration failures and contract anomalies; never overwrite runs.
Reports derive measurements from raw records, with exact aliases separated from
tolerance-based pairwise similarity and no transitive clustering assumptions.
Use equal-horizon comparisons or explicitly retain native-termination differences.
No formal experiment is frozen or launched by this protocol.
