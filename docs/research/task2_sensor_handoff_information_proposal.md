# Proposed next experiment: what sensor information supports the grasp handoff?

Status: proposal only; no new model calls, classifier, policy or physics is
implemented or authorized here.

The decisive next question is whether a decision maker can distinguish a completed
primitive from an established object relation using available sensor evidence.
A fixed second GRASP is not the proposed policy. The new experiment shows that an
additional retained-closure interval can establish the relation in these two
states, with rearrangement and contact confounds; it does not provide a universal
number of closing primitives.

Use a blinded offline information comparison on already sealed records. Include
both anchors before first GRASP, after first GRASP, all eight additional-interval
endpoints, and the lift endpoints; retain the original open-hold negative controls
and the already recorded empty-close counterexample. Do not rerun empty closure.
Keep the full predefined boundary set, rather than selecting clear or successful
images after inspecting the labels.

Compare three nested evidence packets at the same physical boundaries:

| Packet | Available information | Discriminating question |
| --- | --- | --- |
| Completion only | The primitive returned and its mechanical validator status | Does the same completion fact incorrectly stand in for an object relation? |
| Completion + own history | Returned TCP, raw jaw qpos/qvel, their actual read times and a short causal history | Can active closing still be identified after command completion, without turning settled jaws into a holding claim? |
| Completion + own + visual history | The same own data plus saved images and qualified sensor-only co-motion evidence where available | Does visual temporal evidence add support beyond jaw behavior, while preserving uncertainty under occlusion? |

Treat settling as an own-state observation and leave holding unknown. Admission
of a tracked pixel and finite depth does not establish bottle ownership or rigid
3D point identity. The parallel perception test compares matched 2D-only and 3D
co-motion features without filtering: subpixel depth-boundary crossings can
produce large 3D jumps. Keep those tails and the unresolved identity visible;
this handoff proposal must not silently convert them into object motion.

Remove condition names, "first/second GRASP" ordinal labels, evaluator fields and
future frames from the decision input. Preserve true elapsed times and source
linkage outside the blinded packet. Outputs at a boundary may use only evidence
available at that boundary; later lift frames cannot justify a prelift claim.
Historical command semantics can be stated accurately, but command count must not
be the intended success rule. Freeze the packet mapping and any decision prompt
before examining output differences. No new threshold is fitted to these runs.

Ask for an evidence-backed relation description and action-effect class, not a
unique token: closing still in progress, object-specific relation supported,
unsupported or unknown; supporting sensor IDs; and what remains unverified for a
lift. Under retained CLOSED, executed STOP-hold and GRASP have the same nominal
control and belong to the same closure-maintenance effect class. The approach
policy's non-executed STOP remains distinct. A redundant physical STOP arm would
not isolate closure latency and is not proposed.

Seal all packet responses before comparing them with existing evaluator labels.
Keep separate evaluation columns for designated bilateral-pad evidence at the
boundary, later recorded native maintenance, object motion relative to the wrist,
and non-designated/support-contact ambiguity. Do not score a unique GRASP token
as correct, equate evaluator contact with online observability, or infer clean
retention from settled jaws. The existing empty-close case is the critical
counterexample to that shortcut. "Unknown" is a legitimate answer when available
images/measurements do not resolve the relation.

Expected discriminating result: own history explains why the first primitive's
completion does not mean closing has stopped; qualified visual history may add
relation evidence beyond a merely settled empty jaw. Whether tracked pixels stay
on the bottle remains unresolved unless the available evidence supports it.
If the visual history remains ambiguous, the result is an information limit, not
permission to hard-code two GRASPs or fit a favorable threshold. This small stored-
data experiment should precede any new physical handoff policy. A particular
model, prompt, boundary history length and scoring implementation would need to
be fixed separately before execution; no extra dynamics are needed for this test.
