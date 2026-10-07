# BOX role decomposition: both interventions recover the same frames

**Observed fact:** on the21 fully matched development frames, HH/HO/OH/OO yield
inside-region candidate existence **21/21,21/21,21/21,10/21**. Both substitutions
recover exactly the same11frames. **The primary repair ranking is INCONCLUSIVE**
under the preregistered equal-contribution/tie rule. No repair was implemented.

Execution `ed48728`; frozen source checkpoint `51be5f6`. H=human BOX, O=original
model BOX. First letter specifies the SAM prompt BOX; second specifies geometry
search domain. The human positive POINT is fixed. HH/OO reuse previous geometry;
HO/OH reuse exact previous masks and change only geometry ROI. Zero model calls.

[Protocol](research/p1_box_role_protocol.md) ·
[Evidence and all25 matched table](evidence/p1_grounding/box_role_20261008/README.md)

## Observed facts

| Condition | Masks available, frames | Candidate frames /25 | Inside proposals | Outside proposals, raw / admitted |
|---|---:|---:|---:|---:|
| HH: human SAM BOX, human geometry BOX (reused) |25|25|344|0 /0|
| HO: human SAM BOX, original geometry BOX |25|21|496|0 /0|
| OH: original SAM BOX, human geometry BOX |21|21|244|0 /0|
| OO: original SAM BOX, original geometry BOX (reused) |21|10|69|44,737 /43,188|

Candidate existence requires a point-containing native mask and a candidate
projecting inside the frozen human region. All native masks were retained and
evaluated before this separate admission accounting. Proposals across masks can
duplicate physical locations; neither counts nor ordinal frequency select a winner.
No geometry candidate is executable: usability UNKNOWN throughout.

OH/OO have no SAM outputs at init1/2/5/9, because the frozen original BOX excluded
the positive point at generation. These are **unavailable counterfactuals**, not
zero-success measurements of OH geometry. HO has masks on those four frames,
but the original domain excludes useful support; all four fail. The full factorial
therefore contains21frames, not25. No masks were regenerated or missing outcomes
imputed. The all25 coverage table must not be used as a complete factorial.

For the matched21:

| Fixed factor | Intervention | Candidate-frame change | Gains / losses |
|---|---|---:|---:|
| Human geometry domain | Original → human SAM prompt BOX, OH→HH |21→21|0 /0|
| Original geometry domain | Original → human SAM prompt BOX, OO→HO |10→21|11 /0|
| Human SAM prompt BOX | Original → human geometry domain, HO→HH |21→21|0 /0|
| Original SAM prompt BOX | Original → human geometry domain, OO→OH |10→21|11 /0|

The identical recovered init indices are0/3/4/6/10/12/17/18/19/23/24. Balanced
prompt and domain contributions are each5.5frame equivalents; interaction is−11.
This equal allocation is a descriptive convention, **not proof that each cause
accounts for50% of physical error**. Improvements are substitutable here; they
must not be added to claim22distinct repaired frames. Exact paired discordance
statistics are retained (11:0 gives0.0009765625), but these correlated, exposed
frames are not an independent population sample. No generalization/significance
claim or held-out perception score follows.

## Failure taxonomy and first divergence

All75 HO and63 OH masks were evaluated once, without inference or retries.
Native first boundaries:

| Boundary | HO /75 | OH /63 |
|---|---:|---:|
| Geometry candidates |58|48|
| INSUFFICIENT_CONNECTED_SUPPORT |11|0|
| PLANE_DEGENERATE |1|1|
| ERODED_PLANE_DEGENERATE |5|3|
| NO_TOOL_INTERIOR_CANDIDATE |0|11|

Neither crossed condition has AMBIGUOUS_DEPTH_COMPONENTS rejections. Their native
failures remain real even though at least one other mask succeeds in every
matched frame. Later stages after rejection remain NOT_EVALUATED. The original
OO condition retains17ambiguous-component,5plane-support and1eroded-plane rejection,
with40candidate-producing masks including wrong targets.

All25frame comparisons were inspected through five summary sheets, with a
full-resolution inspection of init12. Full-resolution per-frame images retain
all four conditions and every native ordinal. Cyan BOX=SAM prompt, red BOX=geometry
domain, yellow polygon=offline annotation, green/red proposals=inside/outside.

- init0: OO fails AMBIGUOUS_DEPTH_COMPONENTS on all masks. Holding its masks fixed
  while changing domain (OH) yields18inside proposals; changing SAM prompt while
  holding original domain (HO) yields26. Both boundaries are independently
  sufficient interventions on this fixed state.
- init1 (also the exclusion group): HO rejects all three masks for insufficient
  connected support. OH has no source masks and remains unassessed. This is
  genuine target exclusion, distinct from broad-domain contamination.
- init7: OO already has7inside proposals but3,146outside proposals. OH gives12inside
  and0outside, HO gives26inside and0outside. Frame existence alone would miss
  this contamination improvement. All masks, including unsuccessful ones, remain.
- init12: OO native0/2 yield1,449/1,424outside proposals. OH reuses those exact masks:
  native0 yields7inside, native2 rejects PLANE_DEGENERATE, native1 rejects NO_TOOL.
  HO reuses the human-prompt masks and yields10inside each from native0/2 while
  native1 remains ERODED_PLANE_DEGENERATE. Images show altered support domains,
  not a loosened geometry/tool gate.

## Inference

The data reject a sole-bottleneck claim that original BOX necessarily makes SAM
support irrecoverable: unchanged original-prompt masks become sufficient under
human search domains on all21available frames. They also reject a claim that the
original search BOX necessarily prevents useful geometry on those21frames:
human-prompt masks succeed within those same original domains.

The dominant observed pattern on the matched set is **an interaction between
contaminated/broad SAM support and a broad search domain**. Either intervention
removes enough contamination to restore candidate existence. This is more precise
than calling every failure geometry “truncation.” True target exclusion exists
separately in the four unavailable original-prompt frames.

The previous all25 C2−C3 contrast suggested BOX/search-localization priority; it
cannot rank these two implementations once the roles are separated. Under the
prospective rule the priority remains INCONCLUSIVE. We do not promote lower
candidate latency, native ordinal, or raw proposal count into an unregistered
tie-breaker. Geometry/tool thresholds remain frozen and are not the repair target.

## Unknown and next boundary

Unknown: which single autonomous repair transfers best—better semantic BOX
prompting or an independently justified target-support search domain. Human BOX
cannot supply that answer for deployment. In particular, OH does **not** test
removing the BOX constraint, widening to the full image, or choosing the nearest
plane: it substitutes a tight, correctly identified human region. No arbitrary
“decoupling” fallback is licensed by its success. SAM component identity and
candidate selection/feasibility remain unresolved; no continuous tracking or
cabinet-relative VERIFY has been demonstrated.

The next step is a bounded design review/preregistration of **one** BOX/interface
repair and its new held-out validation. This experiment does not scientifically
select either implementation as the winner. No further condition or tuning on
these25frames is justified to break the tie. Nothing was implemented or tuned
beyond the authorized offline diagnostic. No held-out collection, tracker,
temporal sequences, P2/PUSH, Qwen/Laya or fixed-reference research was started.

## Integrity and checks

Only a new offline runner/protocol/test file was added. Every new native evaluation
uses the frozen source mask/depth/K/T/EEF/timestamps/config/seed0/track and feature
identity; only roi_xyxy changes. Full-mask depth denominator and original mask
point-admission state are unchanged. Prompt eligibility is not reapplied to the
new geometry ROI. Original prompt BOX and geometry BOX remain separately recorded.
Human annotations enter only explicit offline prompts/domains and scoring.

Two targeted tests pass: ROI substitution preserves full masks, original depth
and frozen arguments; factorial accounting preserves conditional gains/losses
and interaction. `ruff check --select F` and Python compilation pass;
`git diff --check` passes. Read-only audit authenticates sources/seals and checks
all138new projections against scored candidate counts, unchanged full-mask depth
measurements and original admissions. This audit was performed by the main agent,
not represented as an independent-agent replication. No model/geometry rerun.

Offline geometry p50/p95: HO51.50/83.10ms, OH41.36/61.08ms per native mask. These
are not continuous end-to-end Hz or an efficiency experiment. Full raw outputs,
failures, matched denominator and images are sealed. Historical masks/logits and
HH/OO evidence are referenced by hash rather than duplicated or overwritten.
