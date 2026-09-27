# Fixed whole/neck POINT anchors with the original BOX endpoint guard

## Question and two fixed conditions

Does changing only the fixed sensor goal from the admitted whole-bottle native
POINT to the admitted explicit-neck native POINT change the outcome of the
existing approach-only rule with the same observed-surface endpoint veto?
This changes neither the objective to finite-gap distance nor the guard support.
The neck description was researcher supplied; this is not independent planning.

Register **whole then neck**, one fresh policy episode each, with one separate
exact raw-control verification replay after each normally terminated condition.
Keep both conditions regardless of favorable or unfavorable normal outcomes.
No result chooses an anchor, alters the other arm, supplies its decisions, or
triggers another episode. No model call, prompt, tracker, grasp, lift, placement,
support update, scene pose, contact rule, or new runtime is introduced.

| Condition | Exact archived question | Fixed POINT world position (m) |
|---|---|---|
| whole | `Point to: the wine bottle.` | [-0.11673469557117522, 0.058971097589474636, 0.9883583307522877] |
| neck | `Point to: the neck of the wine bottle.` | [-0.12337491393454869, 0.05776965007435101, 1.0288145621732854] |

Source is `task2-point-region-control-run-01`, exact two-call freeze
`d4045496dc330529eb8f637bd46d556fc9bc0598`. Pin its source journal, request, each
condition journal/manifest/native input/raw return/sensor result. Revalidate the
unchanged native POINT parser, terminal EOS, strict token-limit admission and
containing-pixel-center depth projection from the original frame. Preserve exact
coordinates; no offsets, rounding, selection, BOX median substitution or salvage.
Identity, resolved-depth ownership, current visibility and grasp quality remain
unknown. The visual/evaluator result is not a sensor cleanup or policy input.

## Goal and support remain separate

`goal_anchor` records native POINT condition/query, source hashes, normalized and
continuous coordinates, containing pixel, pixel center, sampled depth, world
projection, calibration identities and original admission. Canonical object
identity remains `the wine bottle` in both arms; the region query is provenance.

`support_guard_identity` binds the original full BOX [208,156,228,223), all 1,340
valid row-major depth points, own calibration and helper hashes. Reuse unchanged
`guard.prepare_geometry(frame, original_BOX_packet)` and `EndpointSelector`.
Do not pass the POINT as the BOX packet or make a POINT neighborhood. The old
BOX median-ray coordinate is not either goal. No mask filtering, support pruning,
refresh, gap objective, or support-derived target adjustment occurs.

Preserve all five separate solids, including both pads, audited body-to-site
mount, live returned own position/body quaternion/signed finger positions,
closed-halfspace numeric tolerance 1e-12, and no physical margin or swept volume.
Veto movement iff any support point is in any nominal endpoint solid. STOP is
never vetoed and terminates before executing a hold. Record all seven candidates,
exclusions, contained-point indices, eligible subset, unguarded rule and chosen
token. Apply the unchanged strict point-distance improvement and tuple tie-break.

## Minimal collector interface and unchanged execution

Reuse `task2_box_point_boundary.collect` and its preflight/protocol/selector hooks.
The only collector edit is optional `decision_fn=decision` and using that
function at its existing call site. Its default preserves original behavior.
The experiment POINT decision helper reuses the old state construction, corrects
the hardcoded BOX evidence basis to native POINT provenance, and rebuilds effects
with the resulting state identity using unchanged `geometric_effects`. Numerical
relations, seven candidates, rule and effects remain unchanged for the same goal
and own observation. No model sees the decision state.

Each condition uses a fresh Python/world process with normal Task2 seed1/init0
and ten existing open-jaw settling controls. No archived state or action prefix
initializes collection. The existing exact RGB/depth/K/T shape/dtype/byte gate
must match the original 384×384 fixture **after settling and before any approach
decision/action**. Each condition matches the same reference independently.
Reference NPZ SHA256:
`3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969`.

Keep original GPU4/EGL4 environment, camera, backend, own observations,
orientation/open-jaw behavior, executor/validator and passive native observer.
At most 40 approach actions and 900 s including each collection's setup;
normally completed actions have eight controls and 200 native integrations.
Record native BEFORE/AFTER evidence and raw contacts. The original new-robot-pair
force >0.05 N boundary finishes the already-started primitive and stops before
the next action. It supplies no movement scores or exclusions.

Normal rule STOP, new-contact boundary or action-budget termination is retained,
then exactly replayed, then the next fixed fresh arm proceeds. Runtime/admission
failure, execution-contract violation (even if simultaneous with contact),
count/invariant failure, wall timeout or replay mismatch stops the batch with
remaining stages unrun and no retry. Preserve original wall-timeout semantics:
SIGALRM can interrupt a primitive; the collector records failure and rethrows.
Do not manufacture complete controls or attempt replay of partial evidence.

Replay uses the existing verifier in its own fresh process, with POINT goal and
support identities added to provenance comparisons. Verify every recorded
control-before/after state, returned own packet, native snapshot and image byte;
never rerun policy or model during replay. Archived controls are permitted only
for this explicitly labeled verification. Keep the exact clean freeze throughout
both collection/replay pairs; edit reports afterward. Existing executor `success`
and privileged execution evidence remain audit fields. Rule STOP, contact,
finite geometry or replay PASS is never relabeled grasp, holding or task success.

## Separate source preparation and physical admission

No-outcome preflight hashes sources, verifies both fixed native POINT projections,
builds the identical original BOX support/calibration packet and records the
unexecuted pair. It constructs no world, model or renderer, computes no new
placement outcome, and explicitly records `physical_execution_admitted: false`.
It is independent of the forthcoming scientific geometry result.

Before any dynamics, require these separately bound receipts:

1. Full independent POINT source/raw/report audit `77c415d`, SHA256
   `c083504fe4574f01a472c4cf957a61ff016055ebc069b4fcb23f752d8bc467d1`.
   Its immutable JSON uses `status=pass`, `source_admission=pass`; retain that
   existing lowercase convention.
2. Independently reviewed matched 18-placement whole/neck original goal-cell
   result. Require the exact common source support/own/calibration, both original
   POINT anchors, nine placements each, all sealed 9×1340×5 tensors and the
   combined ordered result. The geometry audit uses `status=PASS`, binds the
   feature seal, request, source audit and both sensor hashes.
3. **Neck exact TCP=P must have no observed-solid containment**, checked against
   its sealed tensor and reported aggregate. A positive result rejects this
   trial before dynamics and leaves preparation intact. This is a narrow
   scientific prerequisite, not proof of physical clearance or reachability;
   terminal orientation/jaws in the offline test need not equal all live poses.
   No corner result or whole-anchor result selects away either registered arm.
4. Prospective paired-approach PASS naming the exact clean implementation freeze
   **and** SHA256 of the final admission JSON. Its schema is `point_audit`
   `{path,sha256}`, `geometry_directory`, `geometry_seal` `{path,sha256}` and
   `geometry_audit` `{path,sha256}`. Recheck unchanged admission before every stage.

Use the default module CLI with `--output PREFLIGHT.json` for no-world source
preflight. Physical collection is only `--run-pair --output RUN --review REVIEW
--admission ADMISSION.json`, after the above gates. There is no authorized
standalone condition or extra policy episode.

## Required mechanical checks and reporting

Tests compare legacy default collector results with its explicit original
decision function; verify the POINT helper changes metadata only, retains rule
and numerical effects, and preserves all endpoint exclusions at identical own
state/goal; use a fake backend to prove an exact-image mismatch prevents even the
decision hook and any approach action. Test fixed stage order, fail-stop behavior,
executor-violation handling and rejection of altered/unclosed geometry or positive
neck exact-P containment. Reuse original collector/guard tests. No test constructs
a real world or loads a model.

Report both action sequences, exact source/initial gates, candidate exclusions,
first policy divergence, target-distance traces, declared endpoints, validator
outcomes, contacts and replay receipts. Interpretation concerns these two fixed
anchors under the unchanged approach machinery on one development fixture. It
does not certify a grasp or add an inherited success label.
