# Fresh POINT boundary-finding experiment v1

## Question and frozen parent

The 20-action coarse POINT rule episode reduced TCP-to-reported-point distance
from 231.19 to 85.02 mm and independent TCP-to-handle-center distance to 88.95 mm,
without contact or an execution-contract violation. Its endpoint is still
43.35 mm from the nearest gripper/handle surface. It therefore has not tested the
transition from coarse approach to a useful physical interaction.

Does the unchanged point-distance policy reach designated handle interaction
before it loses target grounding, creates non-designated contact, violates an
execution contract or terminates without useful contact? Competing hypotheses
are that one point suffices for this approach boundary, that missing pose/clearance
semantics fails first, or that visual grounding fails before physical interaction.

Preserve `coarse-point-rule-01` at commit
`a1c76d4764ce19ca25ea68042ceb4aebbafe2df8`, raw JSONL SHA-256
`6eb87f1b1e0f69376c9c62f926fcc741cecbf736221977eea00a715868bcd23c`.
This is one new episode from the original benchmark reset, not a continuation
loaded from the old endpoint. Reading the parent establishes provenance only;
no archived state or control enters execution. Do not overwrite or rerun the
historical 20-action result.

## Single authorized change

The new registered maximum is 40 executed primitives, with the existing 900-second
wall limit. Task remains top_drawer, benchmark init0, seed1. Freeze the new
revision before execution. The shared original CLI retains its 20-action ceiling.

Reuse `coarse_point_probe.run` directly. Keep the exact POINT query, checkpoint
content ID, greedy hybrid settings, complete-generation/depth admission, pixel
projection, canonical nominal-distance rule, tie-break, seven-action family,
executor, existing contact-force threshold, execution contracts and abort logic.
Unknown confidence, covariance, contact, holding and relation values remain unknown
to the selector. No Laya/VLM decision, fusion, new action family, grasp/rotation
policy, preview, recovery or prompt change is added.

The only shared-runner change is an optional protocol/experiment-profile metadata
argument. Record this distinct protocol, exact budget, parent identity and fresh
reset explicitly. The canonical state's admission-policy identifier stays the
same because admission behavior is unchanged.

## First-boundary outcome and evidence

Keep existing stops: first invalid POINT/depth/generation, paused-state violation,
execution-contract violation, newly observed robot-contact pair above the existing
force threshold, rule STOP, runtime/wall failure, or budget. Contact abort remains
at the completed atomic boundary; execute no additional primitive after it. Native
controls within that atomic action remain unchanged. Contact observation samples
after each native env control, not every simulator integration substep.

The first event is the primary result. If contact occurs, locate its first sampled
native control using raw all-robot contacts, then report robot geom/link names,
contacted geom names, force and whether designated handle/fingerpad interaction
is supported. Preserve simultaneous contacts and classify ambiguous cases as
ambiguous. The existing `valid_handle_contact` evaluator is available at atomic
boundaries; do not invent its state at earlier control samples. These oracle
labels are evaluation/external supervision only, never selector inputs. Report
contact and executor events separately if both occur in the same primitive.

A correctly grounded point followed by non-designated contact before designated
contact falsifies sufficiency of the point interface for this configuration's
interaction boundary. Rule STOP without useful contact is another negative
boundary. Wrong/invalid grounding instead identifies the perceptual bottleneck;
free-space executor failure identifies a controller-regime issue. Designated
contact would establish only this local transition, not maintained contact,
grasp, drawer closing, robustness or a hierarchical architecture.

Retain all sensor inputs, raw generation, canonical state, recommendations,
actual controls, contact rows, trajectory frames and independent oracle distance
measurements. Before interpreting any new boundary, independently compare the
first 20 executed primitives/160 controls, POINT outputs and decisions with the
parent as an implementation guard. Report any earlier divergence explicitly;
never restore the parent to force equality. Perform full actual-control replay
from another fresh reset, including completed controls of a partial primitive.

Do not increase the 40-action ceiling automatically. Do not reinterpret contact
as permission to manipulate further or add a recovery/interaction policy during
this experiment. Preserve failures; no hidden retries.
