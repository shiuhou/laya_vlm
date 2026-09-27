# Four matched POINT records: no immediate guarded-token divergence

All four offline records select **`MV_FWD` after the guard**. In away, the fresh
slow POINT changes the unguarded preference from `MV_DOWN` to `MV_FWD`, but the
unchanged original support already redirects the cached goal to `MV_FWD`.
The fixed comparison therefore supplies no immediate guarded-token divergence.
No movement was executed.

| Boundary / goal | Goal mode | TCP-to-goal distance (m) | Unguarded | Guarded | Vetoed movements |
| --- | --- | ---: | --- | --- | --- |
| present / cached whole | hybrid | 0.0446341995086555 | MV_DOWN | MV_FWD | MV_DOWN |
| present / fresh whole | slow | 0.051349225174366575 | MV_DOWN | MV_FWD | MV_DOWN |
| away / cached whole | hybrid | 0.0446341995086555 | MV_DOWN | MV_FWD | MV_DOWN |
| away / fresh whole | slow | 0.360367058755538 | MV_FWD | MV_FWD | MV_DOWN |

Both fresh image points pass the unchanged same-frame depth projection:

| Boundary | Containing pixel / center | Sampled depth (m) | Projected world point (m) |
| --- | --- | ---: | --- |
| present | [218,193] / [218.5,193.5] | 0.996310830116272 | [-0.11448930842921246, 0.056959039053213485, 0.9818929984918171] |
| away | [228,328] / [228.5,328.5] | 0.7207057476043701 | [0.23124448687135746, 0.05675092948859591, 0.9924375643970897] |

The cached whole-bottle point remains
`[-0.11673469557117522, 0.058971097589474636, 0.9883583307522877]` m.
The question is identical in every goal packet: `Point to: the wine bottle.`
Cached versus fresh changes **both observation and native generation mode**;
this does not isolate a pure freshness effect. Root separately inspected both
slow points on visible upper bottle bodies. That image judgment is not a policy
input or verified ownership of the sampled depth.

The recorded own packet is identical in all four records.
Each selector uses all **1,340 original full-BOX points** and the same five own
proxies. `MV_DOWN` has 36 contained support points in every record; the other
five movements are not vetoed. The guard is stale after relocation, and its
unchanged exclusions do not certify current observed support, safety or
clearance. All **28 candidate records**, per-proxy indices, canonical inputs,
effects, eligible sets and scores remain in the
[sealed full result](/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-postevent-slow-point-decision-run-01/result.json).

The raw `terminal_reason` string is preserved as
`rule_no_strict_nominal_improvement` in every row. This is the reused selector's
**dormant STOP-reason label**, returned alongside any selected token. All four
selected tokens are moves; the string does not mean the rule selected STOP,
found no improvement, terminated an action or executed a hold. No logging or
policy algorithm was changed to reinterpret it.

Exactly one authorized calculation ran at clean freeze
`8a6906de95ac000a9cd49516a12e7f8c5207b249`: two same-frame projection attempts,
four independent selector calls, four retained records, zero nonadmissions and
zero retries. The complete source binding and intent were written before
features; the result was sealed before interpretation. No model, physics or
render call occurred. The original eight-record hybrid proposal stays on hold;
this is the separately prepared two-boundary slow-source comparison.

The [prepared adapter](../../../embodied_runtime/experiments/task2_postevent_point_decision.py)
passed seven focused synthetic tests covering same-frame/mode/hash rejection,
unchanged numerical rule/effects, matched guard evidence, and null tokens on
malformed or invalid-depth fresh inputs. Related existing parser/guard tests
also passed. No real-data feature run was used as a test or repeated for this
report. No current-support, holding, planner or trajectory-success claim follows.

The [source binding](task2_postevent_slow_point_decision_source_binding.json)
preserves original physical matrix `interrupted_incomplete` and composite
`observational-source-qualified`, the saved-output slow audit and all exact
artifact links. Raw directory is
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-postevent-slow-point-decision-run-01`.

| Artifact | SHA-256 |
| --- | --- |
| Prepared feature code | `6ce59bcf02112e979c01677d0015c2500cf6f5cf47c5d6a08c1ad89b9933ed03` |
| Independent slow-output audit | `e034ead7baad4f3dd24bb992aa556897563e08d5fb9cae034fd93485d575c251` |
| Source binding / tracked copy | `1034338d0e51620393f0e9d3490d57415d01f7e4f1cc7b4c5d5b154c62d9f020` |
| Pre-feature intent | `53849b56e80d7349a589b3bde20ed6dc5159a17e214ac9009ed9e81fcb6384a4` |
| Full result | `126a8f18bfd9f9b8ef716c2977e1c7df7cafea8af03748f428250ad3b4a25901` |
| [Completion seal](task2_postevent_slow_point_decision_seal.json) / tracked copy | `08bd7ab7b2d8c75a035bf49c1273b7658db84c8cd1e6dea22a8ed1407cf6d59b` |
| Original guard packet, canonical digest | `5782d1905481f14903ea66d10dc91da1fb10382c929fc3da6e4d878b5d57c378` |
