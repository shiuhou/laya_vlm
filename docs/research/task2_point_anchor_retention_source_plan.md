# Source/schema plan for POINT-anchor mechanical 2×2 temporal assessment

This is a prospective source/schema plan only. It authorizes no feature
extraction, model call, physics, new render, seed selection, classifier or policy.
The separate physical producer is preparing four fresh episodes: whole/neck
fixed POINT approach, each followed by existing GRASP versus executed open STOP
hold and exactly one existing10mm MV_UP. The temporal assessment reuses the
previously frozen LK/depth/co-motion estimator. Physical contact/rise criteria
remain separate evaluator evidence.

The existing estimator is descriptive: it has no calibrated holding threshold
to transfer. Its frozen gates are native LK status and valid-depth range;
forward/backward residuals are recorded without a rejection threshold. Reuse
these rules exactly. Do not invent a co-motion/retention decision threshold.

## Existing sources and unchanged computation

| Component | Source / identity |
| --- | --- |
| Previous admitted transfer | `docs/research/task2_short_lift_transfer_protocol.md`; adapter `embodied_runtime/experiments/task2_short_lift_transfer.py`, SHA-256 `71973b2f6f6e1f6d1500881250b2ac7740ee796cbd38ac38f191f449c45c9e63` |
| Single-seed tracker | `point_temporal_probe.py`, SHA-256 `86b5b12dd556e37b8b1d08443edd49ee5c852bcc4e63680e1c5928029ad21f36` |
| Motion/summary helpers | `task2_box_temporal_probe.py`, SHA-256 `655a6a84d1688be880d4348d7589251ad37392277102813fc91f5ee421f59b50` |
| Corrected nearest-center association | `task2_track_coordinate_association.py`, SHA-256 `b95245bab639fac6a54359dd51020b2b40d0fd5e23f71fb7d1b7020b2590c855` |
| Original fixed seed population | Raw `task2-box-support-run-02/sensor-representation.json`, SHA-256 `be102057222f2442ead64c8416709d5b2fd792b134271b49f9d8b14722507ead` |
| Original seed image | Raw `interaction-observability-paired-01/close/0000.npz`, SHA-256 `3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969` |

Raw paths are relative to
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research`.
The completed previous transfer has independent review at
`docs/evidence/autonomous_research/task2_short_lift_transfer_independent_review.md`.
Its outcome does not provide labels or thresholds for this new condition.

All492 row-major seeds in `[212,169,224,210)` remain, including initially
outside-proxy seeds. Use the unchanged OpenCV4.11.0 single-seed tracker:
`winSize=(21,21)`, `maxLevel=3`, `criteria=(3,30,.01)`, `flags=0`,
`minEigThreshold=.0001`. Each seed/episode is one complete chronological call;
native forward/backward failure is permanent. There is no reseeding,
reinitialization, smoothing, survivor selection or residual cutoff.

Sampling uses componentwise `floor(x+0.5)` with exact half ties choosing the
higher array index. Backprojection independently uses the sampled pixel center
`(index+0.5)` and saved K/T. Finite depth in the inclusive0.01–5m interval is
valid. Depth failures retain explicit status/null without changing native RGB
tracker status. Full492 denominators and dependent-pixel interpretation remain.

## Required source capture schedule

The producer plans a sensor-only `sensor-captures.json` and `sensor-seal.json`.
Primary initial/approach captures retain their existing recorder and replay
schedule. An auxiliary `LiberoRgbdSource` supplies the eight control endpoints
of close/STOP-hold and the eight control endpoints of lift, without modifying
primary capture numbering. The adapter will merge the two declared streams;
it must not select whichever frame looks better.

For each anchor with A executed approach movements, the merged chronological
population is exactly:

| Merged capture index | Meaning | Source control |
| --- | --- | --- |
|0| Fresh initial frame | null |
|1…A| Each executed approach endpoint |7|
|A+1…A+8| GRASP or explicitly executed open STOP hold |0…7|
|A+9…A+16| Existing MV_UP retaining jaw command |0…7|

The final approach frame A is the sole **preclose** motion reference. Approach
STOP terminates the decision loop without executing a hold; the subsequent
mechanical STOP arm explicitly executes eight controls. These must remain
distinct phases. Do not add a second copy of the same preclose boundary to the
tracker sequence. The two subarms of each anchor must have identical source
approach packets and actions up to that boundary, independently of their later
outcomes. Whole and neck may have different approach lengths.

The completed approach-only pair had A=30 whole and A=29 neck. If the fresh
mechanical source exactly reproduces those prefixes, the full schedules are47
and46 captures per episode, respectively:1,968 seed trajectories and91,512 rows
over four episodes. These are prospective expected counts, not observed new
outcomes. A later extraction freeze must bind the actual admitted complete
source schedule and exact hashes. An abort remains an incomplete comparison;
it must not cause a retry, another endpoint, a shorter favorable cohort, or an
unregistered extraction schedule.

All four initial RGB/depth/K/T arrays must equal the original sealed seed frame
in dtype, shape and bytes. Source artifact bytes may differ due to metadata;
retain both artifact hashes and the explicit array comparison. Do not infer
image equivalence from target-point equality or reset name alone.

## Sensor-only metadata contract

Each row needs the following fields or explicit adapter mappings:

| Field | Required meaning |
| --- | --- |
| `anchor`, `arm`, `capture_id` | Whole/neck, close/open_hold, unique merged chronological zero-based index |
| `phase`, `after_step`, `control` | Exact reset/approach/close-or-hold/lift phase, absolute source action step, endpoint control index |
| `source_capture_stream`, `source_capture_seq` | Primary/auxiliary provenance and its original one-based capture number; never silently renumber source records |
| `artifact`, `artifact_sha256`, source record ID | Relative NPZ path, byte hash, and exact recorded capture linkage |
| `capture_sim_time`, `capture_read_sim_time_s` | Original saved time and explicit read-boundary alias; not an asserted exact RGB/depth sensor sample time |
| `cached_geometry_sample_time_s`, `exact_observation_sample_time_s` | Actual saved values when known; otherwise null, without inventing synchronization |
| `own_tcp_world_m`, `tcp_read_sim_time_s`, `tcp_source_field`, own source record ID | Exact saved own-TCP observation, its read time and unambiguous returned-packet provenance |

NPZ keys stay `rgb`, `depth_m`, `intrinsics`, `camera_to_world` with384×384 RGB-D,
uint8 three-channel RGB, finite3×3 K and4×4 T. Do not import evaluator object
pose, target points, masks, contact rows, contact groups, privileged labels or
source state vectors into this sensor manifest. Sensor source paths/hashes and
nonsemantic episode identities are provenance, not features.

Initial own TCP may be retained only if actually saved by the producer. It must
remain null when absent; no fresh FK, evaluator reset state, earlier archive
endpoint or borrowed arm supplies it. Even when present, keep the previous
transfer's single preclose-reference analysis rather than introducing an
initial-relative outcome. At/after preclose, missing current/reference TCP or
surface must produce explicit unavailable motion metrics, not a fabricated zero.
The suffix hook executes inside `env.step` before `world.obs` updates: its TCP
must use the explicit just-returned observation, not that stale cached packet.

The sensor seal must cover the exact manifest and all referenced NPZ bytes.
Any saved own packet kept outside that manifest also needs a bound sensor-only
artifact/hash. The journal may be hashed for source identity; decoding evaluator
records is outside sensor extraction. Preserve read times and unknown sample
times in output rows.

## Later fixed output schema and separation

Retain all nine original native tracker fields, seed ID/initial pixel, merged
and source capture provenance, nearest sample pixel, depth/status, surface XYZ,
saved own TCP, and `reference_deltas.preclose`. Identity and holding stay null.
Before preclose all reference deltas are null. At/after preclose retain the
unchanged four metrics: point displacement z/norm and point-minus-TCP displacement
z/norm, plus underlying vectors. Summaries retain counts, missing counts,
median,q25/q75, fixed492 denominator and reference-surface-valid count.

Each matched close/open approach prefix should reproduce all nine native fields
exactly when RGB prefixes match. This is a causal consistency check, never a
reason to copy tracks, repair mismatches or choose another run. Whole/neck share
only their verified common physical/RGB prefix; do not demand post-divergence
agreement. The previous privileged-boundary transfer is not an exact native
prefix reference for these new longer sensor-derived approaches.

Seal all four complete sensor row files, summaries and prefix checks before any
optional evaluator read. If the new source independently saves masks, a later
separately admitted evaluator may reuse the existing proxy-membership function;
absence of masks does not justify new rendering or a sensor classification.
Keep initially outside, unknown, and observed departure after prior True distinct.
Membership is not surface ownership, semantic identity or holding.

Report the existing preclose-relative curves and fixed raw checkpoints initial,
preclose, after close/hold and after lift, plus all eight actual lift RGBs per
episode. Per-anchor close/open contrasts are descriptive and dependent on the
same seed support. Compare against mechanical contact/rise only after sensor
sealing, without tuning or converting this into a holding classifier. Across
anchors, paths and endpoints differ; larger visual co-motion cannot establish
grasp superiority or support-free retention.

The initial source plan produced no executable adapter or feature output. The later
freeze must bind complete source receipts, actual schema and schedule, unchanged
helper hashes, synthetic-only coordinate tests, a source-only preflight and an
independent prospective review before the one authorized extraction. Until then,
only documentary/source-schema work is in scope.
These are checks for the later offline extraction, not additional gates on the
already approved physical collector. The physical producer's16 auxiliary
control-end captures per episode remain the complete suffix capture budget.

## Subsequent implementation, before source outcomes

`embodied_runtime/experiments/task2_point_anchor_retention_adapter.py` now provides
a small prospective library, with no CLI, execution wrapper or evaluator route.
It reads only the pinned sensor manifests/seals and bound NPZs; it hashes source
journals for linkage without decoding them. The four source hash pairs must be
supplied after matrix completion and review. This code introduces no additional
gate on the physical collector and has not consumed actual matrix sources.

The source schedule is fixed to whole47/preclose30 and neck46/preclose29, matching
the producer's exact required approach prefixes plus16 suffix control endpoints.
The adapter rejects incomplete/reordered source schedules rather than selecting
a shorter comparison. It verifies initial source arrays and paired prefixes,
preserves returned-own packet/time linkage and every native row, and adapts only
the old transfer's hardcoded frame count/reference index. The existing tracker,
nearest-center depth association, `reference_delta` and percentile helper remain
unchanged and source-hash pinned. Missing own TCP prevents a reference-delta
calculation and stays explicit; available own TCP with a missing surface follows
the existing helper's null metric behavior. No missing value becomes zero.

The API is `load_inputs(matrix, source_hashes)` for stored source/schema admission;
`iter_cell_tracks(packet, seeds, cv2)` for a later admitted once-per-seed batch;
`summarize_tracks(tracks, packet)` for full492-denominator curves; and
`prefix_disagreements(left, right, count)` for complete nine-field prefix checks.
The later execution wrapper must still seal complete outputs and retain any
failure without retry. There is no automatic extraction, registration or source
freeze implied by importing this library.

The actual producer schema has no bottle masks. Therefore this transfer omits
proxy memberships and departure witnesses entirely. It will not render masks,
borrow old masks or replace them with an inferred ownership/holding classifier.
Synthetic manifest/array tests verify schedule integrity, sensor-only loading,
hash failures, unknown own packets, prior arithmetic compatibility, all492 calls
and rows, fixed denominators and cross-anchor prefixes with different horizons.
