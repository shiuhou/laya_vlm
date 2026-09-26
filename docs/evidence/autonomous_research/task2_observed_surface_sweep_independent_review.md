# Independent observed-surface sweep review

**Proposal-only PASS at `ce27ee6`. No numerical features had been computed at this review.** The parent authorized narrow implementation, analytic checks, independent code review, then one offline computation. This receipt accepts the registered scope; it does not yet approve an unseen implementation or validate a physical predictor.

The proposal uses only the initial full-BOX depth support and its exact retained inner crop, the pre-21/pre-22 returned own-observation packets, and five separately calibrated convex gripper proxies. Placement keeps returned site position, eef-body XYZW orientation corrected by the fixed body-to-site mount, and signed finger joints together. Static own-subtree compatibility is required; current source/package agreement cannot establish unrecorded historical asset-byte identity. A mismatch blocks computation, while the explicitly conditional calibration claim does not warrant constructing a new scene.

All seven fixed nominal translations, including zero-displacement STOP, are represented. For each separate proxy the complete fixed-orientation translation sweep is the convex hull of its start and translated vertices. The gripper union is the minimum of the five distances and OR of the five containment flags; constructing a single convex hull around the entire gripper would incorrectly fill jaw gaps. The proposal now states this distinction explicitly.

Two mathematical degeneracies must remain visible in the output and report. Full BOX contains the inner crop, so its minimum cannot increase regardless of predictive usefulness. Every sweep contains the current solid, so current overlap can force all seven swept union minima to zero. Current, endpoint, per-proxy and complete per-pixel arrays are retained to disclose these effects rather than treating lower distances as directional evidence.

Actual outcomes exist only for DOWN at step 21 and FWD at step 22; all other candidate outcomes remain UNKNOWN. Their contact labels and witness RGB inspection occur after the sanitized numerical result is sealed. The known retrospective selection, cached surface age, unverified stationarity, generic depth-point ownership, nominal-versus-executed path difference, finite sampling and hidden space prevent claims of validated contact prediction, clearance, grasp readiness or an improved policy.

The implementation review will check the exact input and output schema, source/asset compatibility, analytic frame and sweep tests, support identity, excluded-field boundary, complete tie/witness retention and seal-before-evaluator ordering before the one authorized feature invocation.

## Prospective implementation PASS

**PASS for one registered offline computation at clean `cb394fdaaa90f4dd0ba984f657130c70bcae9dad`.** The reviewer inspected the full frozen implementation, protocol and tests, and independently ran the eight new analytic tests plus the existing own-geometry and point-to-proxy tests: **23 passed**. These use synthetic geometry; the reviewer did not calculate archived own placement, distances, projection, FK, physics or rendering. The parent's existing authorization covers the one producer invocation after this receipt; no additional approval is needed.

The implementation preserves the proposed four-field worker boundary: normalized own hand subtree, exactly two opaque own packets, full support rows containing only pixel/depth/world coordinates, and the ordered inner subset indices. Only the two signed finger encoders enter local own FK. Returned position is used directly as the site origin; body orientation is composed with the fixed site mount, and local proxy vertices are expressed in that site frame before placement. There is no added site offset, arm/base dependency, native-state substitution, scene label or neck-query input. Analytic signed-jaw geometry, rigid covariance, arm/base and forbidden-field exclusion, exact support arithmetic, full-sweep interior containment, STOP equivalence, jaw-gap preservation, current-overlap degeneracy, primary tie ordering, empty-support output and canonical candidate order are covered.

All 2×7×3 modes retain per-point/per-proxy distance, closest-point and containment arrays. Union summaries take the minimum over separate proxies and OR their containment; row-major point then proxy order defines the primary witness, while all exact ties remain in arrays. The worker never ranks or selects actions. The producer seals the complete feature directory after its single subprocess exits and before extracting actual contact labels. The adapter has access to the known retrospective journal for permitted-field extraction; this process separation does not make the condition blind or held out.

The actual no-own-geometry preflight 01 has SHA-256 `27a3fbdf90db23bc900f1e90fffc1de71cb393f30ab215cafa8e6004c6ac5489`, with clean `cb394fd` identity. It records exact equality to all 492 archived inner G rows and their ordered membership among 1,340 full-BOX rows. The reviewer verified the receipt, all five original source hashes, both pure-helper hashes and every recorded present-time XML/code/STL hash without repeating support projection. The selected stored records independently match step 21/control 0 (`2189fced7232dfed8d708c23dbf78494562e2a731568228e7b994d3833b2e8a7`) and step 22/control 0 (`2c5197a6dc12f2943101e2e4a7844c26ded2b1398af164caf54983bfbcbbadd6`), including the three returned-field shapes and read times. Their initial-support ages are approximately 8.4 and 8.8 s; exact sensor sample times remain unknown.

The producer's preflight checks static body transforms, signed-joint definitions, pad boxes and site mount against the sealed calibration. In addition, the reviewer independently checked every current XML gripper body parent link and all five collision geometry owners against sealed static metadata; all match. This supplements the fixed-input gate without refreezing code. Current hand/finger STL files are hashed but are not recompiled or claimed to match the historical compiled mesh byte-for-byte. The explicit `historical_asset_byte_identity_proven=false` and `compiled_mesh_vertices_reexported_or_compared_to_current_STL=false` fields remain material limits of this conditional proxy diagnostic.

| Frozen file | SHA-256 |
| --- | --- |
| `embodied_runtime/experiments/task2_observed_surface_sweep.py` | `5d12ce8cf3389746b8e44e3b08b34f6cc2475ae5ac5e0d134476594c440b3e7d` |
| `docs/research/task2_observed_surface_sweep_protocol.md` | `d4c6fbee81c4979a113ee0fed2ea030c0f7152ecdb5c210f58af5ee32601ebfe` |
| `tests/test_task2_observed_surface_sweep.py` | `e1f4ac2355bb62b874f0f7db64ae12e6b3c99309e6c4f25a6a62d78e2ab4a296` |

No archived feature result was available during this review. Preserve a failed computation and partial artifacts without changing definitions or automatically retrying. Later result auditing is limited to seals, stored arrays and arithmetic; any geometric recomputation or new physical test requires its own allocation. All proposal limits and UNKNOWN unexecuted-candidate outcomes remain in force.

## Independent sealed-result audit

**Stored-evidence PASS for `task2-observed-surface-sweep-run-01`, produced at the reviewed clean freeze.** [The checker](../../../experiments/task2_surface_sweep_evidence_audit.py) and [complete arithmetic receipt](task2_surface_sweep_independent_audit.json) verify the sanitized input and review/protocol identities, exact preflight/admission equality, all original source hashes, both unmodified returned own packets, normalized static own subtree, all archived inner-support values and full-BOX pixel/depth inclusion, and all 15 numerical artifact seals. The checker recomputes every per-proxy/union summary, containment count, primary witness and exact-tie count from all stored arrays. It also checks identical current arrays across candidates, exact STOP equivalence, sweep/current/endpoint and full/inner minimum inequalities, and the complete separate evaluator records. It does not execute own FK, support projection, hull construction or point-to-solid distance computation.

For every stored point/proxy/mode, the displacement norm between the stored support point and stored closest-solid witness agrees with the stored distance; maximum arithmetic residual is `5.551115123125783e-17` m. This checks array consistency, not an independent reconstruction of the solid. The feature-seal-before-evaluator ordering is verified in the frozen source; this adapter does not emit a separate timestamped event journal, so that ordering is not independently reconstructed from raw event timestamps.

The following table includes all candidates in the registered order. Values are swept union minima in millimetres; the actual executed candidate is indicated in the last column. Every unexecuted candidate outcome remains UNKNOWN.

| Candidate | Pre-21 inner | Pre-21 full | Pre-22 inner | Pre-22 full | Actual execution |
| --- | ---: | ---: | ---: | ---: | --- |
| FWD | 16.859457 | 4.948461 | 16.081006 | 0.000000 | Step 22 |
| BACK | 26.650255 | 10.980201 | 25.589299 | 7.677037 | None |
| LEFT | 26.650255 | 10.974951 | 25.570112 | 7.677037 | None |
| RIGHT | 26.050073 | 10.980201 | 25.076891 | 7.668088 | None |
| UP | 26.650255 | 10.980201 | 25.589299 | 7.677037 | None |
| DOWN | 25.198353 | 7.557041 | 19.137165 | 4.668090 | Step 21 |
| STOP | 26.650255 | 10.980201 | 25.589299 | 7.677037 | None |

There is no current-solid containment at either sample. At pre-22 FWD, full support has exactly one contained point in the hand proxy, in both the endpoint and swept solid: source pixel `[221,158]`, unmodified depth `0.9664809107780457` m, world point `[-0.13719116338778747,0.061508817852240764,1.057485005518255]`. It lies outside the inner crop. It is the sole exact minimizing pixel/proxy tie. There is no contained point in any other registered candidate/sample/mode, or anywhere in inner support. Thus the registered current-overlap degeneracy is absent here; it remains an intrinsic limitation of this feature.

For the two actually executed motions, pre-21 DOWN retains full minimum 7.557041 mm with a hand witness and inner minimum 25.198353 mm with a hand witness; pre-22 FWD has the contained full hand witness while the inner minimum is 16.081006 mm at finger 2. The full-support primary witness for both executed sweeps is `[221,158]`; the inner primary witness is `[217,169]` with depth `0.9750217199325562` m. The separately extracted evaluator contains zero raw robot contacts at step 21 and all 26 raw stage records at step 22 (13 BEFORE and 13 AFTER), matching the already-audited first raw hand/bottle boundary. The >0.05 N crossing remains the later step 24 and is not relabeled first contact.

The full-support superset necessarily weakly lowers every candidate minimum; a lower number alone is tautological. The observed full-support containment at the known first-raw boundary is a descriptive conditional match for this retained resolved-depth point and nominal hand sweep. It is not object ownership, a physical collision prediction, a seven-way validated classifier, a safe alternative action, grasp readiness or evidence that another policy succeeds. Initial-surface age/stationarity, exact own-observation sample times, historical asset-byte identity, finite sampling, hidden space and nominal-versus-executed path differences remain unresolved.

| Audited artifact | SHA-256 |
| --- | --- |
| Sanitized request | `b1e815e896c4059163cc367deb0c84abfa960f3146f829278fdaadebd61183ed` |
| Complete feature seal | `2272dd32051a5965b1188360c993bf89e0b1a77d9f569b053351b5e65c8e9601` |
| Feature summary | `4468151c3cf9e9abecb199131189fab02752ebdd7bf179234d30725c7bc9a55b` |
| Separate actual-outcome evaluator | `ee6be86bf83ccdc90ab826506a23b50727a92c73347a4fc5cf762a7a1db6a905` |
