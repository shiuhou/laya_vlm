# Supplied action-to-effector definitions v0.1

Registered before inference, 2026-09-27. One fixed wording tests whether making
primitive mechanics explicit is sufficient to improve the frozen local motor
decisions. The earlier coherent-situation probe left bare `open`/`close` IDs and
empty option descriptions; its failure does not establish correct action
interpretation. This is a separate matched intervention against the original
baseline, without the earlier situation prefix. No model output selects wording.

## Source and supplied conditions

Use `runs/privileged-reference/local-objective-task-adapter-episode-01/episodes.jsonl`,
SHA-256 `9b77651de9474ecb8cdf24d67ea54a71bfc8d19be33a4e3c1d5ee70c514cc3f2`.
The fixed steps **0, 1, 9, 10** are the previously selected first two approach
and first two advance boundaries, with **7, 7, 25, 16** candidates. Reposition
87 is outside this immediate-effect question. These are inspected development
states, not held-out examples or independent task trials.

Both arms retain explicitly privileged state, objective routing, candidate
admission and oracle-simulator effects. The intervention supplies action-schema
knowledge from the actual executor. It supplies no new scene observation,
geometry, grasp/contact fact, task outcome, winning primitive or ranking. Its
definitions are authored, not acquired by Laya or a VLM. Source target/contact
geometry concerns the moving top-drawer structure; designated handle interaction
and secure grasp remain unestablished.

## Fixed intervention and executor mapping

Arm B is the exact original input. Arm A prepends exactly this paragraph plus a
newline to the state. Every original state byte, effect number, history field,
objective instruction, empty criterion description, candidate ID and order stays
unchanged. No action selection, sorting, filtering, renaming or numeric edit occurs.

```
Primitive commands: x/y/z IDs move the gripper by the signed millimeters along that world axis, retaining orientation and finger command. rotate_axis IDs rotate the gripper by the signed world-axis degrees, retaining position and finger command. open/close command the gripper fingers open/closed while holding position and orientation. hold retains pose and finger command. These are commanded motions; achieved dynamics are the listed predictions.
```

The paragraph abbreviates the actual canonical `jev_libero.actions.ACTIONS`
definitions rather than inventing intended drawer effects. Source files:

- `/home/junhongli/projects/jev-libero/src/jev_libero/actions.py`: lines 4–17
  define signed x/y/z translations and world-axis rotations; lines 18–23 define
  open/close as gripper fingers with pose retained and hold as pose/finger command.
  SHA-256 `d705eeb245b73ba6698243778711ae465064db3f6f782d15b04836e456cc4301`.
- `/home/junhongli/projects/jev-libero/src/jev_libero/world.py`: `World.execute`,
  lines 241–290, initializes the end-effector position target at its current
  position, offsets one axis for translation, emits the rotation command on the
  first control, changes the finger command only for open/close, and runs up to
  eight controls with positional feedback. Open maps to −1 and close to +1;
  all other commands retain the supplied finger command.
  SHA-256 `02d210626b06aac738556b8d8b9b8d9178ed82029c884ce171437602c2aae0c1`.
- `embodied_runtime/experiments/privileged_reference.py:JevAtomicExecutor.execute`
  invokes those same primitives and persists the returned finger command;
  `privileged_task.py:TopDrawerTaskAdapter.actions` selects this action dictionary.

The archived source used Jev commit `3bdad985b225aeccc39fbe5863c6eea2e81c515a`;
the inspected local source is `11d450455d0307bd806c94a27fc7166efb1c483d`.
The diff confirms identical `actions.py` and unchanged motion/finger command
generation in `World.execute`; later measurement instrumentation adds relation
traces. These current source hashes document the mechanics audit, not a rerun
of the archived simulator under changed code.

Pose retention and magnitudes describe commands. They do not promise exact
achieved pose under controller/contact dynamics. The executor can produce drawer
motion even during hold or finger actuation; the unchanged effect table, not the
definition text, supplies those predicted consequences. No premise asserts that
closing fingers grasps an object, or that any nominal move achieves task progress.

## Frozen execution and audits

Commit protocol, code and tests before recorded CPU preflight and all calls.
No new model/download. Use frozen model content
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`, seed 1,
bfloat16, native cardinality temperature, GPU 0 and offline cached files.
The only tokenizer design check yields B/A lengths **372/461, 406/495,
923/1012, 652/741**. This selected wording was not changed after that check.

Require all raw and consumed heading/state/option IDs, their exact input order,
and full state/heading/options within **1,024 total / 256 heading** token limits.
Record original strings and decoded consumed text. Independently reconstruct
the whole input from raw components and compare it to the installed sequence
builder; match every actual forward-hook input and option marker to preflight.
Verify baseline audit identity against archived source and preserve checkpoint,
code, protocol, executor-source hashes and environment. The treatment constructor
receives only original visible state and option IDs for the definition paragraph;
hidden predictions and evaluator labels cannot change the payload.

Exactly **16 calls**: chronological steps, B then A, followed by the reverse
fixture traversal. Candidate order stays fixed. Stop on infrastructure failure,
truncation, token mismatch or invalid output; preserve the raw failure, invalid
and missing calls without retries or a replacement wording. Both valid and invalid
native outcomes remain evidence. Raw output roots are
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/action-binding-*`.
No simulator execution, live controller integration or extra model experiment
follows the first result. No semantic-recognition control or prompt sweep is planned.

## Outcomes and limits

Compare native choices, probabilities and logits across repeats and fresh B
against archive. Recompute effects only after choices. For approach, report
selected surface-gap reduction and same-pool maximum; "substantial" is not an
argmax correctness label. For advance, report closure and alternatives with
greater closure, no less gap reduction/terminal contact and equal obstacle force,
success flag and control horizon. Keep full numeric comparisons, not just binary
labels. Repeats test determinism, not independent sample size; no significance test.

Improvement on both advance states without approach loss would support narrow
utility of this supplied action-definition interface, not deployment or learned
world understanding. If weak advance selections persist, these definitions alone
are insufficient here. Mixed outcomes remain mixed. A selection change does not
certify semantic recognition; failure cannot distinguish unrecognized semantics
from ranking failure after correct interpretation. Added text changes length,
position and emphasis, so B versus A identifies the total intervention effect,
not its linguistic mechanism. This is not evidence that all coherent world
representations fail, that a VLM is necessary, or that any architecture should
be predetermined. No wording refinement follows this bounded diagnostic.
