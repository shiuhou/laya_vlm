# Frozen-input GPU diagnostic — first failure boundary

**GPU access is restored. Surface association is not established.** The fixed
eight-call experiment stopped at its first incomplete generation after two
calls. Tracker and geometry analysis did not run; six calls, including both
drawer-front pairs, were never started. No controls, PUSH, Qwen, Laya or P2 ran.

## Condition and actual result

Run code: clean `1af81e4`. Recorded RGB-D: original init 25/26, seed 1,
384×256 software-EGL source. No new acquisition or labels. The frozen queries,
model checkpoint content ID, BF16 dtype, hybrid generation settings, 256-token
output ceiling and geometry/tracker settings were preserved.

GPU allocation: physical index 2 at launch, UUID
`GPU-293fca5f-bdb8-2235-fa2e-18ab6c488b36`, RTX 4090, logical `cuda:0`.
The other GPU processes were untouched. GPU 2 was shared; measured generation
latencies are not exclusive-GPU throughput or end-to-end freshness results.

| Call, registered order | Input tokens | Generated tokens | Terminal EOS | Result |
| --- | ---: | ---: | --- | --- |
| init 25 agentview, fixed reference BOX | 217 | 48 | Yes | One box; 0.653274 s generation |
| init 25 agentview, fixed reference POINT | 209 | 256 | No | Mixed: one point plus 35 boxes; 1.690100 s generation; rejected |

The POINT reaches the exact output-token ceiling and continues generating boxes
after its initial point. This is **output truncation/incomplete mixed generation**,
not oversized input, OOM, wall-time exhaustion, geometry rejection or robot
execution failure. Neither the first point nor any subsequent box is salvaged.
The failed response is preserved verbatim with all 256 generated token IDs.
There is no inference retry, prompt/decoder tuning or token-budget increase.

The existing stop policy therefore prevented completion of all eight calls.
`stopped-seal.json` hashes the partial evidence and explicitly labels the
experiment incomplete; it does not substitute for a successful `complete.json`.
No geometric support inventory, accepted anchor or tracker seed was constructed.

## Evidence inspection and limits

Both GPU requests exactly equal their existing CPU request JSONs: source
identity, prompt, input token IDs, processor pixel hash and image grid. All
27 original evidence files remain unchanged. An independent agent audit
confirmed token completion/limit accounting, source/model/config identity and
the required stop. This is a code/evidence audit, not new human annotation.

The [raw-RGB/BOX diagnostic image](reference-box-rgb.png) shows a broad cabinet
body region containing top/side surfaces. It does not establish the frozen
query's front-facing frame around the opening. No inadmissible POINT prefix is
displayed as an accepted anchor or used for geometry. Visual interpretation is
development diagnosis; fixedness/reference relation and VERIFY remain UNKNOWN.

GPU versus CPU BOX differs only at normalized top coordinate 335 versus 340
(1.28 pixels); this does not violate input equality, but device/backend numerical
effects are a confounder. There is no complete CPU POINT counterpart. We cannot
claim GPU caused the POINT failure, POINT is always unusable, or geometric
association/tracking is impossible. The narrower observed fact is that this
first frozen-query native POINT failed its admission protocol.

## Gate decision

- Requested drawer-front surface association: **NOT EVALUATED**, not a failed
  geometry result; its model calls were never reached.
- Fixed-reference surface association: **NOT EVALUATED**; no admissible POINT.
- Tracker initialization: **NOT TESTED**.
- Fixed cabinet reference observability and drawer-relative VERIFY: **UNKNOWN**.

Stop here. No later experiment is run automatically. The next design decision
must address this concrete semantic-generation boundary while retaining the
recorded negative result; do not enlarge the token ceiling, truncate to the
first point, switch decoding modes, change queries, use labels or relax geometry
under the current condition. If association is established in a future authorized
condition, independent fixed cabinet reference observability remains the next
gate; it never grants permission to PUSH by itself.

Exact requests/responses, loading identities/config, GPU launch registration,
runtime log, stopped seal and diagnosis are in
[the portable evidence archive](gpu-diagnostic-evidence.tar.gz), with
[SHA256 index](artifact-index.json). The original source remains local at
`runs/p1/surface-dev-20261006-capture02/`; GPU outputs are separate at
`runs/p1/surface-dev-gpu-20261006/`. Only the process-specific trusted-module cache
was cleaned after exit. No code changes or broad test reruns were needed.
