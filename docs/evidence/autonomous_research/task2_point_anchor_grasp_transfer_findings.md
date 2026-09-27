# Fixed POINT approaches transferred to scripted close/open-hold and lift

All four fresh cells completed once, with eight passing atomic validations and
four exact full replays plus four exact 16-image auxiliary replays. Each approach
matched its own archived source before the scripted intervention. There were no
unexpected-contact aborts, model calls, retries or selected winners.

| Cell | Bottle center rise (mm) | Bottom rise (mm) | Bilateral lift endpoints | Native BEFORE; AFTER |
| --- | ---: | ---: | ---: | ---: |
| whole-close | 8.261958 | 8.216198 | 7/8 | 172/200; 172/200 |
| whole-open_hold | 0.000000 | 0.000000 | 0/8 | 0/200; 0/200 |
| neck-close | 9.012689 | 9.157942 | 8/8 | 183/200; 183/200 |
| neck-open_hold | 0.000000 | 0.000000 | 0/8 | 0/200; 0/200 |

Rise uses the final close/hold endpoint as the reference. The literal registered
sampled-endpoint witness is **false for whole** (7/8 rather than required 8/8) and
**true for neck** (8/8 with positive rise versus the open control's zero rise and
0/8 bilateral endpoints). All four validators in each matched pair passed.
These are descriptive local results, not a clean interaction-valid grasp or
full drawer-task success. Neither close arm maintained bilateral pads at all
200 BEFORE and all 200 AFTER lift samples.

Both final GRASP endpoints had no raw robot/bottle contact and no bilateral-pad
relation. Whole had no robot/bottle contact during GRASP; neck had brief unilateral
pad contact during GRASP (8 raw pad rows, 4 above 0.05 N, at each native stage),
then no contact at its final GRASP endpoint. Bilateral pad contact was established
during the subsequent lift. Command completion therefore did not establish the
registered contact relation before lift.

The full suffix traces preserve every raw contact, force vector and geom identity.
During lift, raw finger contacts overlapped bilateral pads in 9 whole and 8 neck
samples at each native stage. Those finger rows had zero normal force; there
were no above-threshold non-pad robot/bottle rows. Hand and other robot/bottle
families had no recorded rows. Keeping raw and thresholded evidence separate is
necessary: the neck sampled witness is not promoted to an unambiguous contact
mechanism. Both conditions retained early native bottle/table contacts (whole
28 raw/23 strong samples; neck 17 raw/15 strong, at each stage). Whole's first lift
endpoint still had table contacts; its later seven and all eight neck lift
endpoints had none. These sampled contact absences do not establish support-free
retention or a clean continuous grasp. Bottle rotation is unknown without a
recorded source-specific quaternion mapping; center and bottom changes are
reported separately.

The experiment used sensor-selected approaches followed by fixed scripted
interventions: eight-control GRASP versus executed eight-control STOP-hold, then
one nominal 10 mm MV_UP. Approach STOP itself executed nothing. Whole and neck
approach endpoints were already about 9 mm apart; the earlier own-anchor 43 mm
versus 5 mm distances do not establish grasp superiority. No target, posture,
threshold or action sequence was adjusted after outcomes.

Execution used the literal source environment, `laya-embodied`, at clean freeze
`1702cb2739bfdb2817a329c8047e16bcb7836657` with preflight02
`3bc68d41b02d3a17f1f9354ff2369d5256edf842ef0371d8c186af602c55b787`. Preflight03 is an unexecuted alternative-environment
preparation. The matrix journal records normal completion and the matrix subprocess
returned 0. The outer tool's final poll returned 143 despite printed driver status
0 and the complete exit receipt. That launcher discrepancy remains explicit in
the audit and execution closeout; there was no repeated physics attempt.

Independent raw audit: `6051e9a498f73e8399b232a2d64b9a0174e8e0ab8d3187cffdb69a4c31a9a018`. Matrix journal:
`39d2a972869d98944bdfb29cce721174cdb9d617ec3696b5139ac5ffd8b139f4`. The audit reuses the byte-exact closed approach
prefixes; it does not rerun their geometry tensor computation. See the
[summary](task2_point_anchor_grasp_transfer_summary.json) and
[lossless full suffix traces](task2_point_anchor_grasp_transfer_suffix_traces.json.gz) for all four results,
source hashes, action validations, native-stage aggregates and complete suffix
records. Existing RGB interpretations are retained separately; no images are
duplicated here.

The next prepared hypothesis is whether one additional stationary GRASP interval
establishes bilateral contact before lift and throughout all sampled native lift
stages. Geometry or slip may remain limiting. Preparation does not authorize new
dynamics.
