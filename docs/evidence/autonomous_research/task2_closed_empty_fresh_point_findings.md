# Four cold POINT calls: two admitted present results, two malformed away results

The fixed four-call batch completed, but the native POINT interface admitted
only the two present-image outputs. Both away-image calls returned the same
malformed mixture of POINT and BOX content; their admitted `point` remains
**null**. The first blocking stage is a well-formed typed localization output.
The [eight-decision experiment](../../research/task2_closed_empty_point_decision_protocol.md)
remains **on hold** because neither away case supplies an admitted fresh goal.
No depth projection or policy evaluation was performed.

| Call / case | Local capture | Status | Admitted normalized POINT | Containing pixel | Generated tokens |
| --- | ---: | --- | --- | --- | ---: |
| 1 / present-postevent | 0 | admitted RGB point | [568, 503] | [218, 193] | 10 |
| 2 / away-postevent | 0 | malformed; point=null | null | null | 22 |
| 3 / away-prelift | 16 | malformed; point=null | null | null | 22 |
| 4 / present-prelift | 16 | admitted RGB point | [564, 503] | [216, 193] | 10 |

All four calls terminated with EOS ID **151645**, below the **256-token** limit;
none was incomplete or length-limited. The complete away return contains one
two-coordinate POINT, a four-coordinate BOX and a degenerate BOX. The unchanged
full-return parser rejects it; the first parseable point is not salvaged.
This is retained output failure, not evidence of target absence or deliberate
semantic abstention. Admission alone does not verify bottle identity.

Exact raw output, present-postevent:

```text
<ref>the wine bottle</ref><box><568><503></box><|im_end|>
```

Exact raw output, **both away-postevent and away-prelift**:

```text
<ref>the wine bottle</ref><box><594><856></box><box><607><855><1000><857></box><box><607><855><1000><855></box><|im_end|>
```

Exact raw output, present-prelift:

```text
<ref>the wine bottle</ref><box><564><503></box><|im_end|>
```

The [full RGB sheet](task2_closed_empty_fresh_point_rgb.png) preserves each
384×384 source image at one display pixel per source pixel. Each row has an
unchanged original and a repeated image; only admitted present points receive
a hollow ring. Both away repeats remain byte-identical to the input RGB, with
no salvaged point or BOX marker. Raw text and generation counts appear beneath
every case. The [report manifest](task2_closed_empty_fresh_point_report.json)
retains exact source/image/output bindings, full-precision admitted coordinates
and token audits. Its generation-time pending-inspection field is preserved;
the subsequent [layout inspection receipt](task2_closed_empty_fresh_point_visual_inspection.json)
records actual original-resolution viewing of all eight panels. Semantic image
interpretation is reserved for root's separate inspection.

The sole model question was `Point to: the wine bottle.` on each complete
unannotated RGB image. No depth, calibration, own observations, history, condition
labels or motion results entered model messages. The batch used **four distinct
cold Python/model processes**, one call each, with **zero inference retries**.
It retained the LocateAnything-3B checkpoint, BF16/eval, seed 1, GPU2 and native
hybrid generation with temperature 0, `do_sample=false`, `use_cache=true` and
`max_new_tokens=256`. The
[independent audit](task2_closed_empty_fresh_point_independent_audit.json), commit
`4322eeb`, passed source/tensor/token/admission checks; that PASS does not mean
all four responses were admitted points.

Preparatory **preflight01 failed** in the `laya-embodied` environment because
`decord`, `lmdb` and `torchvision` were absent. Its retained failure receipt
records zero processor constructions, model constructions and model calls.
**Preflight02 passed** at freeze
`8cc19ebff9cec07eba4f416d35a157445b60f554` using the existing archived
`locateanything` environment, without installing packages or changing the
checkpoint. This setup correction was not an inference retry.

These four fixed views demonstrate a typed-output limit in the native semantic
localization interface. No holding, planner, executed-progress, persistent
correspondence or general reliability claim follows. The physical source retains
`observational-source-qualified` status and the original matrix remains
`interrupted_incomplete`.

Raw calls: `/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-closed-empty-fresh-point-run-01`.
Separate report: `task2-closed-empty-fresh-point-report-01` under the same raw root.

| Artifact | SHA-256 |
| --- | --- |
| Failed preflight01 receipt | `2ae80018cc0b5756e778320113893feffe003b805364780ce40faf42818862ed` |
| Passed preflight02 | `366b576db8398de8c51425f0e45a3cb1e5eda732e1eeefc677e53aeb8586308a` |
| Four-call request | `94384cd5c2f46dd9f73470dce4bbf47f9627b3a8eaa8118a21f99784d72c8e1b` |
| Closed batch journal | `5e3e146be17297a28b512a44e6b1e6710f1277db60c2b7be4c975f4856f78720` |
| Completed exit receipt | `a3d807fb4d90a479e35e8cc0e6d6f615af14b0a76e8a25afcfee43773bd846ad` |
| Independent audit | `dd6e3e1463e2b6a00d9b4e31d6c16164e0dd471b21ea554b301c60f4bd5964d0` |
| Full RGB sheet / tracked copy | `b4fa37602657cbf19a21950bb0d3506045c18a69e68d2383beb85d5d104bd527` |
| Report manifest / tracked copy | `52575c32bb40edf610312dbadb1649cd52c5f60045fff3d5b2466826139321f4` |
| Layout inspection / tracked copy | `b92a2f58cc4dc9e780175d474caf0b21a95f682f8f3fc0eee9cca808c041a47f` |
