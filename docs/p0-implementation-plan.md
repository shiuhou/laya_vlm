# Approved P0 implementation plan

Baseline: `ea853019d3343ef4cb8eff8a2fdb43a91e760642` on `share_main`.
Implementation branch: `feat/p0-runtime-contracts`.

## Fixed direction

Qwen3-VL brain → Laya local choice → continuous RGB-D geometry and deterministic
servo. This architecture is selected for implementation. B0–B4 evaluate model
contributions later; P0 neither reopens architecture search nor claims success.
The first task uses the visible drawer front for pushing, with no inherited
fingerpad/handle grasp prerequisite.

The three original design documents are copied verbatim. Their archive source
and SHA256 are recorded in `p0-design-sources.json`:

- R2: `brain-cerebellum-plan-v2.md`, §§8–12.
- R3: `target-point-perception.md`, geometry, uncertainty and visible features.
- R4: `protocols-and-inference-example.md`, §§2–4 and acceptance requirements.

## Ordered work packages

| Package | Original basis | Implementation | Required evidence |
|---|---|---|---|
| A0 | R2 §11 | source hashes, baseline inventory, hash-pinned P0 environment | clean environment install, `pip check` |
| A | R4 §2 | `contracts.py`, `router.py`, P0 config | immutable envelope, identities, idempotence, reject-before-state-update |
| B | R2 §8; R4 §3.2–3.4 | `state_store.py` over existing fusion | pure snapshot reads, capture age, OOSM, delayed categorical binding, lineage |
| C | R4 §3.5–3.7 | `control/action_catalog.py`, `local_candidates.py`, `action_contracts.py` | all27 in robot_base, no utility pruning, exact binding, one proposal/segment |
| D | R2 §9; R4 §3.1–3.7 | `sensor_api.py`, `policy_observation.py`, `evaluation.py`, minimal vision fix | robot-only whitelist, null uncalibrated confidence, no oracle policy access |
| E | R4 §4; R2 §8 | `workers.py`, `control/scheduler.py`, `control/servo.py`, synthetic probe | bounded async inference, reliable controls, cancel/reset, dual deadlines, measured feedback |

A precedes B/C/D, which precede E integration. Existing fusion algorithms,
legacy executor and successful privileged evidence are not rewritten. The new
sensor path does not call the legacy truth-bearing backend or Runtime.step.
Legacy label fallback is disabled only for explicitly categorical evidence.

The first A batch establishes Envelope/Receipt/Rejection/BlobRef/FrameBundle,
strict schema/config validation, registered frame/request identities, and a
single ingress that rejects before consumer dispatch. Later payloads are added
by their owning packages. All work is committed by concern.

## Concrete contracts

Use R4 names/units, protocol `embodied.protocol/1`, robot_base coordinates and
xyzw quaternions. Capture time is never replaced by arrival time. One request
cannot renew its deadline. Proposal revalidation may accept an old snapshot
with reliable current lineage; it cannot substitute another primitive.

Keep base27-v1 in canonical order. Every ALLOWED action is model-facing; hard
unknowns remain UNKNOWN. Preserve raw hard evidence and canonical hash even
when invariant metadata is omitted from the model projection. No top-k.

One proposal authorizes at most one ≤100ms, ≤5mm/≤2° segment (contact ≤2mm).
Remaining magnitude is feedback, never continuation permission. KEEP/HOLD
retain the backend-owned gripper command. Every tick checks sim and monotonic
wall deadlines and current identity/state. Equality to deadline is expired.

Only calibrated robot jaw width is a width measurement; retained command,
joint opening and holding are different facts. Calibration/holding unknowns
remain unknown. LocateAnything boxes do not imply confidence=1. Geometry quality
and model confidence are separate. Official success belongs to the evaluator.

## P0/P1/P2 boundary

P0 uses synthetic measurements, fake selectors and a kinematic fake backend,
with virtual clocks plus a short real-wall worker test. It validates contracts,
not collision checking, camera correctness, neural latency, grasping or closing.

P1 owns same-capture RGB-D, non-square reprojection, point geometry, visible
patches/normals, fast tracking, and visible cabinet reference. P2 owns actual
tick-interruptible control, observed-space/sweep gates, B0 approach and pushing.
Qwen/Laya integration, true token-consumption audit and B0–B4 follow later.

P0 must not claim visual completion where cabinet reference is unobservable.
P1/P2 report UNKNOWN rather than substituting hidden official success.

## Acceptance

Run package-specific tests, relevant legacy tests, Ruff on changed Python, and
the synthetic probe. Persist code/config/dependency hashes, exact model-facing
inputs, raw replies, pool identity, contracts, feedback and rejection timelines.
Inspect individual valid/expired/cancelled transitions, not just totals.
No real model or simulator is loaded. No existing evidence is overwritten.
