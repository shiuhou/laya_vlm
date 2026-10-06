# P1 fixed-reference completion diagnostic — preregistration

User freezes tracker infrastructure `ab361eb` and evidence `065ad2b` and authorizes
one independent decoder condition. This diagnostic is separate from the old
incomplete eight-call experiment. No result redefinition or prefix acceptance.

## Single intervention

POINT generation budget **256 → 1024**, chosen once before inference (fourfold
headroom). All other native generation kwargs remain fixed: hybrid mode, cache,
BF16, temperature0, do_sampleFalse, same native EOS handling. No forced EOS,
custom stop strings, decoder mode switch, query/template change or checkpoint
change. One fresh POINT call from the original input; no prefix/cache/archived
control warm start, no rerun if the ceiling is reached again. A larger budget is
not proof that repetition is resolved. This condition tests completion by1024,
not arbitrary eventual completion.

Use the sealed init25 agentview RGB and reference POINT request in
`runs/p1/surface-dev-gpu-20261006/`, original source RGB-D/calibration in
`runs/p1/surface-dev-20261006-capture02/`. Preserve the old completed BOX reply
byte-for-byte; do not infer BOX again. Model content ID, full prompt/input token
IDs, processed pixel hash/grid, versions/model config, reference query,
`p1-semantic-output/typed-v1`, original independent BOX ROI, inventory seed and
all geometry/tracker gates remain fixed. Use the same identifiable GPU2 UUID as
the old failure; sharing/load is recorded, not silently called matched latency.
A clean implementation revision, before-call registration, source seals and
GPU allocation are required. One process, one model call, 900-second wall ceiling.

## Ordered gates

1. Observe actual complete generated token IDs/count, model-facing input budget,
   terminal EOS and no over-limit tokens; preserve full raw reply regardless.
2. **Only if EOS/completion passes**, apply the unchanged whole typed POINT
   contract. No parsing incomplete replies into geometry or extracting prefixes.
3. If typed POINT is legal, combine it with the unchanged archived BOX and run
   unchanged support inventory/exact-pixel association. Preserve all supports,
   residuals and AMBIGUOUS/UNKNOWN. Archived BOX reuse is explicit: one old BOX
   plus one new POINT is not two fresh calls.
4. If unique valid support exists, inspect actual RGB/support to establish
   development evidence for the requested fixed front-facing frame, not a top,
   side, moving drawer, cavity, rim, tabletop or background substitute.
5. Only after that requested-reference association review passes, separately
   register and initialize the independent reference tracker with original
   recorded episode/capture clocks and unchanged gates. Static initialization
   does not establish fixedness or a closed-state relation.
6. After successful reference grounding/initialization, define the next
   drawer/reference temporal relation and VERIFY observability gate from observed
   evidence. Do not invent attachment, coplanarity, hidden surfaces or official
   success to fill gaps. No PUSH occurs in this phase.

Stop at the first concrete failure at any gate; no alternative decoder, larger
budget, retry, query tuning, annotation seed, box-center fallback or geometry
gate relaxation follows automatically. Report completion, legal format,
requested-surface grounding, tracker initialization and observable fixed relation
separately. Negative result remains canonical evidence.

## Competing predictions

- EOS before1024, legal POINT, relevant unique support: the earlier ceiling was
  consequential; physical reference identity/fixedness still need independent
  evidence.
- EOS but illegal/wrong/unsupported POINT: output completion is insufficient for
  grounding; report the first format or semantic/geometry boundary.
- Still no EOS at1024: fourfold budget alone is insufficient in this condition;
  do not claim infinite nontermination or model impossibility.

Only focused output-budget/completion tests and lint are required. No models,
controllers, schedules, typed contract or geometry implementation are modified.
