# Source feasibility and matched scene-event design review

PASS for the source feasibility decision at `c97a8da`: the original proposed
three-packet model comparison lacks a sensor-complete closed-empty control.
The [independent inventory audit](task2_sensor_handoff_feasibility_independent_audit.json)
checked all 20 named modern boundaries against their sensor manifests, journal
record IDs, exact own packets and RGB-D schemas/hashes. Modern preclose packets
come from the approach endpoint; suffix packets come from the just-returned
control-7 observation. Explicit unknown sample times remain unknown.

Named old empty records 26/54 lack returned jaw qpos/qvel and RGB-D. Source review
confirms rendering was disabled, each action restored its fixture snapshot, and
the closed-gripper fixture used an unrecorded setup close. These records are not
a contiguous observed two-close history. The reported actual_joint_qpos_m is
drawer position. Flattened predicted simulator state cannot fill the missing
sensor channel. The separate drawer demo's records 11/27 and RGB-D 6/22 match
their inventory, but lack named qvel and use an unmatched scene/contract. The
proposed eight-output velocity ordering microprobe remains unexecuted and would
not establish holding or justify motor responsibility.

The selected neck present/away design is a reasonable narrow preparation:
independently regenerate the same approach, preserve the unexecuted STOP, perform
one declared sham/translation event with identical synchronization calls, then
execute GRASP/GRASP/MV_UP. Its causal contrast is target-near versus target-away
under that event. Relocation also changes visible scene layout, contact/support
configuration and the solver's derived state. A classifier could distinguish
the pair by visible target absence elsewhere without estimating grasp relation.
Positive discrimination alone would not validate grasp specificity. Equal
primitive schedule does not require identical feedback-generated control arrays
after the physical interaction differs.

The [independent static calculation](task2_closed_empty_static_bounds_independent_audit.json)
checks setup bounds from producer `361cf1e`. It validates source and mesh hashes,
the actual neck preclose qpos record and all finite collision-group counts. A
separate homogeneous-transform calculation uses transformed local mesh bounding
boxes for a deliberately looser robot envelope. It still gives at least 228.401
mm robot X separation; bowl, cabinet and rack bounds are respectively 133.227,
57.257 and 154.107 mm. Bottle bounds agree within 1e-14 m. Its entire translated
XY footprint stays inside the tabletop. The direct worldbody floor plane, outside
the producer's body traversal, has a separate 899.985 mm bottle Z gap. The
producer was asked to state that scope explicitly.

BDDL X placement ranges and yaw plus the reset source support the fixture bounds;
these are setup-contract assumptions, not measured current fixture transforms.
Live named-joint/model/fixture checks still matter. Pure horizontal translation
preserves the original bottle/table geometry, including its existing penetration.
These calculations do not prove new equilibrium, dynamic stability, camera
visibility or future swept clearance. The offset must stay fixed; a setup failure
cannot trigger placement search or an unreported retry.

Source hooks need an explicit event before the first suffix state and own-packet
checks. The existing replay handles controls only and otherwise either misses
the cause or fails at the edited state. Dispatch the recorded translation and
same forward/refresh sequence; never restore its recorded after-state. Check
exactly one expected event and reject missing, duplicated or unknown events.
Keep scene captures in their own stream so normal primary action/capture counts
remain meaningful. Ordinary read-only guards must not enclose mutation.

The forced observable update increments cache timers even with unchanged sim
time. One explicit forward and one forced refresh are required in each arm;
calling both a forced update and a forced getter would perform two refreshes.
Bind the actual returned own packet, preserve unknown sample-time fields and
record synchronization effects separately from the target-only explicit write.
Condition/event/pose/contact/solver provenance belongs outside future sensor
packets. A new event error must be recorded even before the first suffix action
initializes its phase/step variables.

The separately reviewed post-event image-region design at `1ee5215` is consistent
with this boundary: freshly initialize the same 492 numerical pixels in each
post-event image, retain all 25 frames and all failures, use sole reference 0 and
checkpoints 0/8/16/24, and do not track through the exogenous jump. Equal seed IDs
mean equal image coordinates, not common physical material. Finger/background
patch support may cause empty-hand local co-motion; that is the narrow confound
being tested. Event step 29 is pre-GRASP bookkeeping, not a completed action.
Neither the design review nor the static calculation releases physical dynamics,
model calls or a future feature extraction.
