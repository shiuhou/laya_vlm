# Two current native BOX support-refresh inputs

Development control, selected after the sealed two-image slow POINT result and
its independent audit. The bounded downstream question is whether replacing the
old full-BOX observed-depth support with current full-BOX support changes the
endpoint exclusions or decision while holding the CURRENT admitted POINT and
own state fixed. It is not safety certification, a holding test, a decoder
comparison, or a pure freshness comparison to a cached hybrid POINT.

Run only after a clean code freeze, CPU-only input preflight, exact prospective
review PASS and root's explicit two-call authorization. This protocol itself
is not launch authorization. No model calls have been made for this design.

Two cold native calls, fixed order: `present-postevent`, `away-postevent`.
Use precisely the source RGBs bound to the audited slow POINT run
`task2-closed-empty-slow-point-run-01`. Physical source admission remains
`57fa52a1ba5ffff73e7e197bbe352fe5f83209397c8cb972736cea389f0d7e42`,
with the original matrix still `interrupted_incomplete` and its separately
recorded second away verification unchanged. POINT audit SHA is
`e034ead7baad4f3dd24bb992aa556897563e08d5fb9cae034fd93485d575c251`.

The exact sole model question is the established object-level BOX template:
`Locate a single instance that matches the following description: the wine bottle.`
The checkpoint README documents this native single-box task; the same whole
query produced a 12-token EOS-terminated BOX on the archived initial image.
The archived neck-query failure remains rejected and is not retried here.

Use `generation_mode='hybrid'`, explicitly distinct from the fixed fresh slow
POINT goals. Retain original BOX native max_new_tokens256, use_cache=true,
temperature0, do_sample=false, verbose=false. Keep the same local checkpoint
content ID `4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f`,
original `locateanything` environment, BF16/eval, GPU2, seed1, EOS151645 and
maximum16384. The historical initial BOX used GPU0 and did not record seed1;
these new calls are not claimed as a bitwise repeat of that old call. Mode and
BOX description remain historical; current image contents are the new input.

Only full unaltered 384×384 uint8 RGB and the fixed question enter model
messages. No current POINT coordinate, earlier output, condition label, event,
path, depth, calibration, own state, mask, bounding annotation, crop or resize
enters the model. Reuse existing native processor/chat/call_once helpers. CPU
preflight must match current POINT RGB, image grid and BF16 visual tensor hashes
exactly; text and input token IDs deliberately change to the sole BOX question.
Seal those actual BOX input tokens and compare exact metadata at inference.
Keep all existing helpers, parsers and production runtime unchanged.

Use the existing `task2_box_support.admitted_box` with the existing token audit:
complete terminal EOS, actual token count 1..256, and whole-return parsed status
`single_box`. A point, mixed output, multiple boxes, degenerate/malformed box,
empty result or incomplete/over-cap generation yields `admitted_box:null`.
No fragment, prefix or first box is salvaged. No prompt/mode sweep, cap change,
fallback call or inference retry is allowed. A nonadmission stops that case's
current-support arm and remains explicit; the second registered BOX case still
runs. Infrastructure failure stops the unrun remainder with evidence preserved.

Per-case generation artifacts use the established schema: full `rgb-input.npy`,
`native-input.json`/`.npz`, `generation-settings.json`, raw `generation-return.json`
and strict `model-output.json`, all journal-sealed. The output contains only
continuous image `admitted_box` coordinates (or null), generation/token audit,
parsed status and explicit depth_read=false/support_extracted=false/holding=null.
This runner neither samples depth nor creates a BOX-median goal. Seal both cases
and the batch before any semantic inspection or downstream support extraction.

After independent saved-output audit and the separate downstream release, use
current depth/intrinsics/camera transform from the exact same saved source NPZ.
For an admitted box, convert nonnegative image coordinates with the established
integer truncation, require nonempty in-frame half-open bounds, and retain every
finite depth in [0.01,5]m inside the FULL rectangle. Reuse
`task2_observed_surface_sweep.support`: row-major enumeration, raster center+0.5,
existing camera/world projection, no mask cleanup or hand-selected subregion.
Do not use the old `sensor_representation` interior crop or `prepare_geometry`
that pins the old BOX[208,156,228,223] and1340 points. Empty valid support is an
explicit unavailable arm, never an allow-all cloud.

The companion offline comparison owns packet construction for the unchanged
EndpointSelector consumer (`calibration`, `full_support` rows with pixel_xy,
depth_m, position_world_m). Hold each audited fresh slow POINT, current depth
projection of that point, own packet and calibrated proxy geometry fixed within
its old-versus-current support pair. Reuse all existing seven candidate moves,
containment tolerance, canonical policy and tie behavior. Record per-candidate
containment counts/vetoes, eligible candidates and final token even if the token
is unchanged. The original support is the historical cloud, not old image BOX
coordinates resampled on current depth. No physical execution follows.

A current BOX is semantic region localization, not segmentation or certified
bottle-only geometry. Mixed surfaces, self-occlusion, partial visibility,
render/depth sample timing and calibration limitations remain. Refreshing this
support may alter an exploratory endpoint filter without establishing collision
freedom, path safety, contact, grasp quality or holding. Keep the full-frame
depth-only alternative separate rather than combining methods after seeing outputs.
