# Objective-family approach control v0.1

## Question, evidence and competing hypotheses

The completed ten-option sensory approach probe selected GRASP on all six
development fixtures and both exact repeats, despite the explicit request to
retain the gripper command and minimize nominal distance. Does objective-family
admission expose useful directional ranking, or does ranking still fail within
the requested translation family? The earlier six-translation reflection pair
had a generic drawer instruction and no candidate effects; it does not answer
this matched question. The current ten-option translation scores are also not a
substitute for rerunning the encoder with a seven-option menu.

This is exactly one 12-call intervention, without prompt tuning or additional
order/model searches. It is not a new natural validity gate or live policy. The
deterministic rule-versus-hold physical probe proceeds independently; its value
does not depend on rescuing Laya.

## Frozen source and permitted input change

Source: `runs/autonomous-research/approach-selector-run-01`, raw JSONL SHA-256
`2ed444a6ee96519a60b276df0462c0230f227676365464a5e4df5e72c17a947e`.
Require its complete 12-call run, exact repeats, original model configuration,
full token integrity, six parent fixtures and underlying sensory source hashes.

Keep the same six fixtures: init0 steps 0, 20, 24, 29; init1 step0; init2 step0.
Preserve the exact instruction, structured state, history, assumptions, all
remaining numeric effects and candidate descriptions. Remove only GRASP,
ROTATE_CW and ROTATE_CCW from the menu and their null effect-table rows. Retain:

```
MV_FWD, MV_BACK, MV_LEFT, MV_RIGHT, MV_UP, MV_DOWN, STOP
```

This restriction follows the already supplied objective: one nominal 10 mm
translation, unchanged gripper, STOP only when no translation improves distance.
It selects a family, never an axis, sign, primitive winner or favorable effect.
Keep every translation, including receding choices. Keep STOP's effect unknown;
active hold is not known to have zero physical effect. No positive-effect filter,
reranking, new threshold, oracle correction or hidden contact assertion is added.

Preserve the complete ten-option parent fixture, natural allowed mask/gate
evidence, raw unrounded effects, perceptual provenance and parent payload ID in
each evidence fixture. Explicitly label the menu restriction
`objective_family_admission`; the archived source canonical representation still
describes the original ten-option condition. No evaluation or rule token enters
the model input.

## Execution and validation

Use the identical frozen Laya checkpoint/configuration, dtype, seed and inference
environment as the ten-option source. Both cardinalities use the unchanged
`choice:6-10` temperature. Call all six fixtures once chronologically, then once
in reverse fixture order; menu order stays canonical. Exactly 12 calls, no retries
or warm-up inference. No simulator, new sensor capture, perception model or
physical execution is constructed.

First run CPU tokenizer-only preflight with the installed sequence builder.
Require every state/header/option token to fit and persist exact consumed IDs and
markers. GPU inference must reproduce the preflight IDs/markers and use unchanged
code/protocol/model hashes. Validate choice, probability distribution and raw
logits at each boundary, failing immediately on invalid input/output. Audit
per-call temperature against the frozen model configuration.

Report each family choice against its archived ten-option counterpart and the
unchanged deterministic comparator. Use sensor nominal gain/regret, unknown-effect
status, repeat equality and separate post-choice oracle nominal gain. Membership
in the seven-option family is not itself success. The deterministic comparator
is not an expert label; nominal gain does not establish physical controller
displacement or useful contact.

## Interpretation and stopping rule

Useful choices would justify testing this family boundary, not claim a general
architecture or Laya advantage over deterministic arithmetic. Failure would argue
against promoting this specific Laya approach interface. It would not establish
that every hierarchical Laya role fails. Menu removal also changes encoder context;
this experiment does not isolate attention competition from token-position effects.

Historical sensory target estimates remain unverified; all results are development
diagnostics. Strict live grounding and honest unknown confidence/covariance remain
separate requirements before physical execution. Stop this control after the
registered calls or its first concrete failure, with no further prompt or menu
search. No runtime behavior changes follow automatically from either outcome.
