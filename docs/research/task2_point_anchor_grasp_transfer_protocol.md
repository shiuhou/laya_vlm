# Task2 fixed POINT approach to scripted grasp/lift transfer

Status: prospective preparation only. No dynamics are authorized by this document.
Physical execution requires an independent PASS naming the exact clean implementation
commit and the SHA256 of its no-world preflight receipt.

## Registered four cells and source

Run exactly `whole-close`, `whole-open_hold`, `neck-close`, `neck-open_hold`, in that
order. Each cell is a fresh seed1/init0 world, including the original settling
controls and original byte-exact initial RGB/depth/K/T gate. Collect each cell once,
then perform its separate recorded-control verification replay before the next
cell. No repeat after a negative outcome, no winner selection, no action search,
posture offset, oracle pregrasp, target adjustment, new VLM call, or trial tuning.

The fixed native POINT anchors, full 1340-point original BOX support, all five
endpoint solids, original own-observation convention, unchanged strict nominal
improvement policy, and original endpoint containment veto are inherited literally
from `task2_point_anchor_approach`. The sealed `task2-point-anchor-approach-run-01`
whole/neck journals, both passed replays, independent full audit, and original
POINT/geometry physical admission are pinned by SHA256 in the new wrapper.
The whole endpoint's 43 mm own-anchor distance and the neck endpoint's 5 mm
own-anchor distance do not imply different grasp quality: their physical endpoints
are only about 9 mm apart and use different reference points.

## Fresh policy approach and verification boundary

The approach regenerates every action from the unchanged policy and live own
observations. Archived controls and states cannot seed it. The original 40-action,
900-second bound (including setup and the short suffix) remains. Approach STOP
executes nothing: no eighth-control hold, settling, posture change, or intervention
occurs at that decision.

Only after the original rule returns `rule_no_strict_nominal_improvement`, with no
new robot contact, compare the complete fresh prefix with its matching archived
anchor. Compare every decision including terminal STOP, selected token, candidate
and guard diagnostics, control command, before/after state, returned own packet,
native BEFORE/AFTER snapshot, endpoint, image metadata and RGB/depth/K/T shape,
dtype and bytes. Run IDs, wall-clock journal envelopes and manifest differences
are excluded; vision file hashes bind each archive independently. All prefix
record kinds and counts must match. Also require the exact original termination
payload. The comparison verifies what just happened; it never generates actions.
Any mismatch stops the entire matrix before the first scripted control.

## Fixed scripted suffix

At the verified endpoint execute these separate experimental interventions through
the unchanged `AtomicExecutor`:

| arm | first primitive | second primitive |
| --- | --- | --- |
| close | `GRASP`, eight controls with retained jaw +1 | one `MV_UP`, nominal 10 mm, eight controls with jaw +1 |
| open_hold | executed `STOP`, eight hold controls with jaw -1 | one `MV_UP`, nominal 10 mm, eight controls with jaw -1 |

The executed open STOP-hold is distinct from the approach's non-executed STOP.
Both suffix primitives have 200 native integrations, 25 per control. No relation,
contact, image, bottle motion or privileged label selects either primitive.
This is sensor-selected approach followed by a scripted postapproach intervention,
not an autonomous grasp decision or a holding classifier.

Reuse `local_grasp_interface.require_pass` and its thresholds literally. Reuse its
native `unexpected_contact` predicate literally: robot contact above 0.05 N is an
abort except the existing broad gripper/bottle allowance. This allowance includes
fingers and hand; it is not a valid-grasp predicate. Preserve both BEFORE and AFTER
native snapshots and all contacts, names, IDs and six force components. For a
completed primitive, persist its action result, endpoint and captures before
checking its validator/contact abort. Abort at the original after-primitive
boundary, not a new threshold or early contact response. Do not execute the next
primitive or cell after runtime, executor, count, unexpected-contact, prefix or
replay failure. Preserve partial evidence and explicit suffix phase/action counts.
A normal weak/no lift is a retained negative outcome, never an execution failure.

## Sensor and evaluator evidence

Keep the primary camera schedule and capture IDs identical through the entire
approach. Capture one additional primary frame after each suffix primitive.
A separate camera instance/counter writes `auxiliary/capture-NNNNNN.npz` after each
of the 16 suffix controls. No auxiliary capture occurs during the approach.
Every measurement uses the unchanged integration-state and cached-geometry/sensor
read-only checks. The just-returned own observation packet is passed explicitly
to the control callback: `world.obs` has not yet been updated at that boundary.

`sensor-captures.json` contains the initial frame, all approach endpoint frames,
then all 16 auxiliary suffix frames in chronological order. Each row names its
condition, anchor, arm, phase, absolute step/control, capture stream/sequence,
artifact/hash, capture/read time, exact returned own packet and source linkage.
Exact observation sample and cached geometry sample times remain null, as they
are unknown. The final approach image is the preintervention reference. The
sensor-only seal binds the manifest and every listed NPZ; it links but does not
include the privileged journal. No object pose, mask, contacts or evaluator labels
are included in that manifest. No LK/co-motion extraction or classifier changes
are part of this experiment.

Privileged endpoint labels and full raw contact snapshots are buffered after every
suffix control and written under `evaluator-only/` only after sensor sealing.
They never enter policy or suffix selection. The existing primary replay compares
all recorded commands, states, own observations, primary images and native
snapshots. Its optional callback additionally checks all 16 auxiliary RGB/depth/K/T
arrays, times, sequence, phase and own packets. Require unique complete 2×8 keys
and complete replay consumption, with separate auxiliary replay receipt.

## Registered descriptive outcomes, without outcome-based stopping

Reuse the original sampled-endpoint local witness literally, separately for each
anchor: all four atomic validations in its close/open pair pass; close bottle
center rise (final lift minus final close z) is greater than `max(0, open rise)`;
all eight close lift endpoints have both designated pads above the existing strict
0.05 N threshold; zero open lift endpoints do. Retain false as a normal result.
No new radial-distance, rise-size or success threshold is introduced.

Separately count bilateral designated-pad samples at all 200 lift BEFORE and 200
lift AFTER native stages. Only 200/200 in both stages supports maintenance at every
observed native stage; it does not establish continuous-time contact.

Preserve and report raw and >0.05 N robot/bottle link classes separately as pads,
fingers, hand and other robot links, including simultaneous bilateral-pad plus
non-designated contacts. The sampled witness is descriptive. Bilateral contact
plus rise must not be promoted to a clean interaction-valid grasp when any
simultaneous non-designated robot/bottle contact exists. Report contact mechanism
and ambiguity separately, and do not introduce a new holding classifier. Broad
abort allowance, strict pad measurement, local witness, native maintenance,
physical clearance, grasp mechanism and official task success remain distinct.
Do not claim completion of the full drawer task from this local lift.
