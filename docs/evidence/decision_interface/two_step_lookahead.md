# Original Jev two-step witness audit and reference extension

Current authority: [current_state.md](../../current_state.md).
This record follows the [one-step dead-end audit](dead_end_boundary_audit.md).
It evaluates the unchanged original Jev witness mechanism, then records the
human-authorized minimal privileged-reference extension. It is not an ablation,
planner, hierarchy, CDS change or non-oracle claim.

## Original implementation semantics

Original Jev runner commit `3bdad985b225aeccc39fbe5863c6eea2e81c515a`
uses two-step processing only when `lookahead == 2` and the complete one-step
`contracts()` pool is empty. `World.two_step_witnesses()` then:

1. restores the root snapshot and executes each of the 27 native primitives as
   a possible first action;
2. rejects a first branch that introduces an obstacle pair or leaves endpoint
   obstacle contact under the configured collision rules;
3. previews all 27 second primitives from every surviving first endpoint;
4. combines the second endpoint with the root state, including net task progress,
   net surface-gap change, unioned obstacle pairs and peak obstacle force;
5. requires that the combined result satisfy at least one existing configured
   effect contract;
6. retains, for each first primitive, the best second witness under the configured
   lexicographic score: success, `advance_target`, closing progress,
   `establish_contact`, then surface-gap reduction.

There is no first-step closure guard beyond collision safety. Temporary negative
closure is permitted. The combined result need not have positive closure: an
`approach_target` or `establish_contact` result within the existing regression
tolerance can qualify. The chosen witness is attached to the first primitive;
the existing `reposition` contract then admits that first primitive. The runtime
returns a first-action contract pool. It never returns or executes an open-loop
two-action command.

`Snapshot` saves and restores full MuJoCo data, controller state, robot recent
buffers and torques, gripper action, environment clock/cache, observables,
observation and NumPy/Python RNG state. The frozen audit independently verified
the simulator-state hash and controller context before and after search.

## Exact frozen-snapshot result

The source state is the same audited boundary:

- simulator-state SHA-256:
  `ba1d9ee0d186cfb04f94fb4f17f35a580cc350730b065def1f1950fd6d5e66fe`
- controller context:
  `ff643c9c992fe032fa31ea200b2d66aedf09333104ebde08bb8aef00c6a43673`
- drawer opening / gap: `151.65901295563316 / 2.732324299728142 mm`
- current target/obstacle contact: `false / false`

Original Jev evaluated all `27 x 27 = 729` second branches. Thirty-two
first/second pairs satisfied combined contracts. They covered 23 first-action
tokens and 22 physically distinct first actions because `open` and `hold` are
the same retained-open control. Original Jev selected one best witness per first
action and produced this `reposition` pool:

```text
x-10mm x-3mm x+3mm x+10mm
y-40mm y-10mm y-3mm y+3mm y+10mm
z-40mm z-10mm z-3mm z+3mm z+10mm
rotate_x-10deg rotate_x+10deg rotate_y-10deg rotate_y+10deg
rotate_z-10deg rotate_z+10deg open close hold
```

Four collision-safe first actions had no second branch satisfying a combined
contract:

| First | Closure mm | Gap change mm | Contact | Reason |
|---|---:|---:|---|---|
| x-40mm | 0 | -17.616324 | false | no second branch passed combined contracts |
| x+40mm | 0 | -8.971083 | false | no second branch passed combined contracts |
| y+40mm | -7.235189 | 2.528604 | false | no second branch passed combined contracts |
| z+40mm | 0 | -37.822328 | false | no second branch passed combined contracts |

The classification is **MULTIPLE VALID FIRST-STEP WITNESSES**, case A.

### All 32 qualifying first -> second pairs

`Best` identifies the one witness retained by original Jev for that first action.
Closure and gap values are millimetres. All pairs have peak obstacle force `0 N`
and predict no task success.

| First | Second | Best | First closure | First gap | First contact | Second closure | Second contact | Net closure | Final gap | Final contact | Combined contracts |
|---|---|---|---:|---:|---|---:|---|---:|---:|---|---|
| x-10mm | z-3mm | yes | 0 | 0.690235 | false | 0.031289 | true | 0.031289 | 0 | true | advance, establish, approach |
| x-3mm | z-3mm | yes | 0 | 1.080496 | false | 0.094004 | true | 0.094004 | 0 | true | advance, establish, approach |
| x+3mm | z-3mm | yes | 0 | 1.366776 | false | 0.067767 | true | 0.067767 | 0 | true | advance, establish, approach |
| x+10mm | z-3mm | yes | 0 | 1.225737 | false | 0.006264 | true | 0.006264 | 0 | true | establish, approach |
| y-40mm | z-10mm | yes | 0 | 1.676634 | false | 0.395136 | true | 0.395136 | 0 | true | advance, establish, approach |
| y-40mm | z-3mm | no | 0 | 1.676634 | false | 0.071393 | true | 0.071393 | 0 | true | advance, establish, approach |
| y-40mm | rotate_y-10deg | no | 0 | 1.676634 | false | 0 | false | 0 | 0.426789 | false | approach |
| y-10mm | y+40mm | yes | 0 | 1.238489 | false | 0 | false | 0 | 0.466737 | false | approach |
| y-10mm | z-3mm | no | 0 | 1.238489 | false | -0.008144 | true | -0.008144 | 0 | true | establish, approach |
| y-3mm | z-3mm | yes | 0 | 1.247005 | false | 0.041559 | true | 0.041559 | 0 | true | advance, establish, approach |
| y+3mm | z-3mm | yes | 0 | 1.140861 | false | 0.091814 | true | 0.091814 | 0 | true | advance, establish, approach |
| y+10mm | z-3mm | yes | 0 | 1.006252 | false | 0.154423 | true | 0.154423 | 0 | true | advance, establish, approach |
| z-40mm | y-40mm | yes | -2.670249 | 2.732324 | true | 14.165596 | false | 11.495347 | 0.009125 | false | advance, approach |
| z-40mm | y-10mm | no | -2.670249 | 2.732324 | true | 5.126328 | true | 2.456080 | 0 | true | advance, establish, approach |
| z-10mm | y-40mm | yes | -0.265756 | 2.732324 | true | 5.883951 | false | 5.618195 | 0.027545 | false | advance, approach |
| z-10mm | y-10mm | no | -0.265756 | 2.732324 | true | 1.666518 | false | 1.400762 | 0.000716 | false | advance, approach |
| z-10mm | y-3mm | no | -0.265756 | 2.732324 | true | 0.340801 | false | 0.075046 | 0 | false | advance, approach |
| z-10mm | rotate_x-10deg | no | -0.265756 | 2.732324 | true | 0.835811 | false | 0.570055 | 15.913065 | false | advance |
| z-3mm | y-40mm | yes | -0.108773 | 2.732324 | true | 1.656312 | false | 1.547539 | 0.079855 | false | advance, approach |
| z-3mm | rotate_x-10deg | no | -0.108773 | 2.732324 | true | 0.170506 | false | 0.061733 | 15.395889 | false | advance |
| z+3mm | z-10mm | yes | 0 | -1.651745 | false | 0.011817 | true | 0.011817 | 0 | true | advance, establish, approach |
| z+10mm | rotate_x+10deg | yes | 0 | -8.450831 | false | 1.209178 | true | 1.209178 | 0 | true | advance, establish, approach |
| rotate_x-10deg | z-40mm | yes | 0 | -14.350248 | false | 0.170577 | true | 0.170577 | 0 | true | advance, establish, approach |
| rotate_x+10deg | y-40mm | yes | -2.215683 | 2.732324 | true | 10.966277 | false | 8.750594 | 0.021046 | false | advance, approach |
| rotate_x+10deg | y-10mm | no | -2.215683 | 2.732324 | true | 6.625941 | true | 4.410258 | 0 | true | advance, establish, approach |
| rotate_y-10deg | rotate_y-10deg | yes | 0 | 0.730205 | false | 0 | false | 0 | 0.286184 | false | approach |
| rotate_y+10deg | z-10mm | yes | -0.101071 | -0.073633 | false | 0.416886 | true | 0.315815 | 0 | true | advance, establish, approach |
| rotate_z-10deg | rotate_x+10deg | yes | 0 | -0.510917 | false | 0.015293 | true | 0.015293 | 0 | true | advance, establish, approach |
| rotate_z+10deg | z-10mm | yes | 0 | -0.320142 | false | 0.310904 | true | 0.310904 | 0 | true | advance, establish, approach |
| open | z-3mm | yes | 0 | 1.225532 | false | 0.060077 | true | 0.060077 | 0 | true | advance, establish, approach |
| close | z-3mm | yes | 0 | 1.225964 | false | 0.060545 | true | 0.060545 | 0 | true | advance, establish, approach |
| hold | z-3mm | yes | 0 | 1.225532 | false | 0.060077 | true | 0.060077 | 0 | true | advance, establish, approach |

The three most direct temporary-regression transitions are:

| First -> second | First closure | Two-step net closure |
|---|---:|---:|
| z-3mm -> y-40mm | -0.108773 | +1.547539 |
| z-10mm -> y-40mm | -0.265756 | +5.618195 |
| z-40mm -> y-40mm | -2.670249 | +11.495347 |

`rotate_x+10deg -> y-40mm` similarly changes `-2.215683` first-step
closure into `+8.750594 mm` net closure. The existing mechanism therefore
contains the physical contact-transition capability excluded by the one-step
contracts. It does not guarantee that the decision model selects those actions.

## Minimal privileged-reference extension

The opt-in reference keeps its one-step path unchanged. When its one-step pool
is empty, `ReferenceBuilder` calls original `two_step_witnesses()`, attaches the
unchanged best witness payloads, recomputes original contracts, and offers every
witness-backed first action in native vocabulary order. It does not select a
winner. Laya sees first-step effects and all original witness fields. Execution
runs only the chosen first primitive, measures the real endpoint, and rebuilds
candidates from that endpoint.

The fixed instruction is unchanged. Normal one-step state text is protected by
a byte-exact regression test. The first witness serialization was too verbose:
the frozen menu required 2,241 state tokens for an 872-token state budget and
was rejected before inference. The final mechanical serialization preserves all
23 tokens and effect values, moves identical values to a common declaration, and
uses compact field codes. Its actual encoding audit retained all 23 option
markers: 865/872 state tokens, 1,017/1,024 total tokens, with no state, heading or
option truncation. This is serialization needed to carry the existing mechanism,
not a changed decision instruction or candidate filter.

## Fresh closed-loop result

The valid fresh process used clean commit
`3fe6b0dcedc9fc2c14cd55aae4eae9607e2b427f`, the unchanged local Laya
checkpoint, CUDA/bfloat16, benchmark init 0 and seed 1.

- Steps 0–17 reproduced the one-step v1 action prefix exactly.
- Step 18 triggered one two-step search and offered all 23 witness-backed first
  actions, representing 22 physically distinct operations.
- Laya selected `open` with probability `0.9984` and confidence `0.9955`.
- The attached witness was `open -> z-3mm`, predicting `+0.060077 mm` net
  closure, full gap removal and terminal contact.
- Only `open` executed. Its predicted and real immediate effect matched exactly:
  closure `0`, gap reduction `1.225532 mm`, no target/obstacle contact and no
  task success.
- The next real state had gap `1.506793 mm`, opening `151.659013 mm` and no contact.
- At step 19, unchanged one-step contracts admitted only `z-3mm`, in both
  `advance_target` and `establish_contact`. It predicted `+0.060077 mm` closure
  and new contact. Since this was one physical operation, the genuine-choice
  gate stopped before Laya or execution. Lookahead did not trigger because the
  one-step pool was non-empty.

Action trace:

```text
x+3mm x10
x+10mm x2
x+40mm
rotate_x+10deg x5
open
```

There were 19 genuine Laya decisions and executions, 152 controls, zero drawer
closure, no task contact at the executed endpoints and official success `false`.
All 19 selected predictions matched real execution with zero state/effect error.
Recorded-control replay passed all 172 checked boundaries with maximum error zero.

This run shows that existing lookahead solves the original empty-pool transition
coverage problem and supplies a genuine decision menu. It does not establish a
successful privileged reference. The first remaining failure is a singleton
one-step contract pool after Laya selected a passive witness-backed transition.
The acceptance rule correctly refused to treat or execute that singleton as model
competence. No prompt tuning, threshold change, hierarchy, planner, new contract,
CDS change, ablation, non-oracle work or E0 followed.

The later authorized [forced-singleton continuation](forced_singleton_reference.md)
executes such one-candidate pools without calling or crediting Laya. It passes this
boundary and accumulates 15.173 mm net closure, but eventually reaches a later
state where unchanged one-step contracts and two-step witnesses are both empty.
Thus the singleton boundary is resolved as an attribution/control-flow issue; it
was not the final task-success boundary.

## Preserved attempts and artifact identity

`lookahead-episode-01` was deliberately interrupted after discovering that an
early integration draft changed normal one-step serialization; it is invalid as
reference evidence and remains preserved. `lookahead-episode-02` restored the
normal input exactly, then failed closed before the boundary-18 model call because
the verbose witness state was truncated. No action executed from truncated input.

Ignored local audit v02 artifacts:

- `runs/privileged-reference/two-step-lookahead-audit-v02/episodes.jsonl`:
  `993c5b2cb20cf9e9a18a7aaae01e97702f60b535c7eb12e560bf5a08c2601b08`
- `two-step-lookahead-audit.json`:
  `6b1e67e94fa56c0ca10092f845af0f8b5aba97ea7ad549d49b95df7119541299`
- `two-step-lookahead-report.md`:
  `5d7c245f1e81ceadfc57ce588a30a6ff740e8411c8dabe6c54ccea1642503e9b`

Ignored local valid episode-03 artifacts:

- `runs/privileged-reference/lookahead-episode-03/episodes.jsonl`:
  `dc64a31185e27a7314fb45be482c19ebb5d28d9fe4fa1552d9ae09c02f1a9c54`
- `reference-evidence.json`:
  `b9f88df313f34c374556be30fd2ca789a83575294c9ae29ac74e0b765527af6a`
- `reference-report.md`:
  `678e933671c33b47e831db9c18f25282e29503dfc5d540e52d0f171cdbc2b829`
- `replay-check.json`:
  `4e89dec3cff36929d4dade772c7a30e366e6212340fe3537f7f6dc7ce0e96f07`

Raw artifacts include every one-step prediction, witness payload, pool,
rejection, exact model input and response, real execution outcome, trajectory
state and provenance identity. They remain ignored and are absent from a fresh
clone; this tracked record preserves the result and hashes.
