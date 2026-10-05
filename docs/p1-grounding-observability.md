# P1 grounding / observability — annotation handoff

The preserved infrastructure checkpoint is **92865a8** on
`feat/p1-rgbd-geometry`. New preparation is isolated on
`feat/p1-grounding-observability`. **Task acceptance remains pending.**

**Measured update:** the corrected v2 labels have been sealed and the original
100-call fixed-query condition has completed without truncation. Read
[P1 grounding results](p1-grounding-results.md) and the independent RGB review
for the current findings. The annotation preparation below is historical;
no re-annotation is presently required. Temporal coverage remains separately
evaluated, not inferred from acquisition count.

## Human annotation first

**Latest correction:** the user clarified that the submitted labels were already
made by a human who had not seen the AI draft; the negative provenance fields
were erroneous. See the [append-only correction receipt](evidence/p1_grounding/annotation_metadata_correction_20261005/README.md).
The same 50 annotations can be retained; redrawing is not required. All label
content and original timestamps remain unchanged. Independence is user-reported,
not independently verified. The v3 handoff below is historical preparation;
resolving v2 serialization compatibility must preserve the original rules and
registration chronology, rather than relabeling the existing export as new v3
annotation. No model call has run.

**Historical handoff: independent-human v3.** The user initially chose a new human annotator
who has never seen AI drafts or model results for these images. Follow the
[handoff instructions](p1-independent-annotation-handoff.md). The earlier v2
packet and submission remain preserved as historical records, not admitted
blind evaluation. The annotation is blinded to LocateAnything outputs.
Only raw RGB is displayed; no model ROI, candidate, geometry decision or success
label appears in the page. The [frozen rules](p1-annotation-rules.md) bind every
export by version and SHA256. There are 50 first camera views, two entities per
view, and no prefilled labels. UNKNOWN and NOT_VISIBLE are accepted outcomes.

Local packet: `runs/p1/human-annotation-packet-independent-v3-20261005/index.html`.
Portable download: `/home/junhongli/projects/laya/p1_blind_annotation_independent_v3_50views.zip`.
It needs no network: extract the folder and open `index.html` in a browser.
Partial export/resume is available; export regularly because browser autosave
is local to that browser/profile. Only a validated complete export qualifies.

- Dataset: `b4f09b3fae2529cb80cbaaab99280b0420366d1e3399845a734af4d5d516c4ae`.
- Rules: `p1-rgb-annotation-rules/3`.
- Rules SHA256: `1b0dc9af5491fbe4d26cc8dfd7664c4351e0da0cef71499dc58af0e82df18202`.
- Download SHA256: `a17932aac8c87c67e9af36d827c7d52938987a846eee36718d22cc868e258fe4`.

Browser QA checked the actual page under Chromium 141 / Playwright 1.56.1:
image load, exact status choices, two-entity saving, incomplete-final-export
rejection, JSON download, navigation and reload/autosave. One synthetic UI-test
export remains quarantined in `/tmp`, never used as human evaluation. The
offline validator rejects it for incomplete coverage. No evaluation labels have
been manufactured or filled by agents.

After the new annotator exports `annotations.independent-v3.complete.json`,
validate and seal it without overwriting the earlier submission:

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_annotation_packet validate \
  --packet runs/p1/human-annotation-packet-independent-v3-20261005 \
  --annotations /home/junhongli/projects/laya/p1_annotations_inbox/annotations.independent-v3.complete.json
```

## Frozen semantic experiment

Update: a 50-record export was received and preserved, but its own provenance
declares prior AI-draft exposure and blind-evaluation ineligibility. The
[receipt](evidence/p1_grounding/annotation_receipt_20261005/README.md) records
matching source bindings and structural polygon checks separately from that
conflict. It is **not admitted** to the preregistered blind condition. The user
chose a new unexposed human annotator; the empty v3 packet is ready. No model
call has run and no condition has been silently relaxed.

Current registration, prepared before receiving any v3 labels:
`runs/p1/grounding-preregistration-independent-v3-20261005.json`. The original
v2 registration remains unchanged as historical evidence. The v3 registration
preserves queries and all model/geometry conditions. It binds original sensor
records, packet/rules, exact queries, model bytes/settings and **unchanged
92865a8 geometry code and configuration**. No model call has run.

The prepared condition has 100 calls: two preregistered queries per RGB. Only
RGB and the fixed query reach LocateAnything. Depth, annotations and evaluator
state do not enter its input. Every ordered box, malformed/no detection,
native token/EOS audit, geometry result and candidate is preserved. Truncation
fails without retry. Predictions are sealed before annotation-based scoring.

The optional preregistered evaluator-only human-mask intervention keeps original
depth inside the annotated region and replaces outside depth with unknown. It
measures geometric support under correct region information, **not a policy**.
Its evidence is separately marked human-mask-plus-sensor, never an ordinary
sensor estimate, robot self-mask, tracker seed or executable candidate.

After the complete annotation seal, recheck GPU availability and run the existing
dedicated environment with one explicit allocation. The real loader refuses an
unset/multiple GPU allocation and records device identity; this command is
**not to be run while labels are pending**:

```sh
CUDA_VISIBLE_DEVICES=2 /home/junhongli/miniforge3/envs/locateanything/bin/python \
  -m embodied_runtime.experiments.p1_semantic_grounding run \
  --packet runs/p1/human-annotation-packet-independent-v3-20261005 \
  --annotations /home/junhongli/projects/laya/p1_annotations_inbox/annotations.independent-v3.complete.json \
  --preregistration runs/p1/grounding-preregistration-independent-v3-20261005.json \
  --output runs/p1/new-independent-fixed-query-evaluation
```

The existing dedicated LocateAnything environment and checkpoint are reused;
Qwen and Laya remain off. Exact generation and geometry settings are not tuned
against partial labels. Readiness tests explicitly ensure incomplete/mismatched
annotations reject before the real model loader is called.

## Observational VERIFY

`perception/relative_verify.py` represents face and reference with separate
tracks/features/lineages. It computes
`g = n_reference · (p_face - p_reference)` and conservative correlated position
and normal uncertainty. LOST, AMBIGUOUS, stale/reused frames, context changes or
capture discontinuity reset the three-update streak.

Only a declared visible coplanarity relation supports `g_closed=0`; structural
attachment and visible-reference artifacts are required. Stationarity is not
fixedness. Missing reference, unknown relation or unvalidated uncertainty yields
UNKNOWN. The helper never reads joints or official success. The evidence
registrar must validate artifact content/digests before constructing support
records; this checkpoint does not supply real calibration or such verified
reference artifacts. Synthetic tests are not observation-based acceptance.

## Live throughput probe already measured

A separate read-only static fresh reset measured the frozen diagnostic workload
(four manual ROIs, two cameras), with zero runtime actions and no models. This
is independent of the pending human labels and is **not a semantic-ROI control
test**. It is a serial baseline, not a runtime scheduling change.

- 23 complete persisted cycles over 10.153 s: **2.265 Hz**, requested 10 Hz.
- Capture p95: **5.56 ms**; single ROI p95: **188.63 ms**.
- Complete capture-to-geometry-publication p95: **430.68 ms**.
- All 23 cycle deadlines missed; at publication none of the 92 ROI records
  met existing 0.3 s free / 0.2 s contact freshness limits.
- Sim time remains fixed in this static test, but wall-clock age advances;
  timestamps are never rebased to hide processing delay.

Local raw frames/cycles and manifest: `runs/p1/live-throughput-20261005/`.
Recorded revision `f0e179a` was exploratory with other new modules untracked;
its source hashes and packages are in the manifest. The workload depends only
on the committed stream probe and unchanged P1 capture/geometry; it is not
presented as a clean-revision closed-loop experiment.

This establishes a timing limitation of that workload, not which semantic
query or camera is the dominant manipulation bottleneck. Do not relax geometry
or freshness gates to hide it.

## Still pending

The three static questions now have qualified measured answers in the
[results](p1-grounding-results.md): visible wrist face support exists, adjacent
cabinet geometry exists, and semantic surface association is the first drawer
failure. Fixedness/closed-reference relation, calibrated uncertainty, safe push
eligibility and live freshness remain unestablished.

The [ten-case temporal protocol](p1-temporal-sequence-protocol.md) has ten acquired
exploratory attempts, with 354 dual-view bundles. All initial semantic hypotheses
are LOST and VERIFY remains UNKNOWN. Their declared square image resolution
differs from the original static condition; no target-valid qualifying temporal
sequence is established. Unsupported occlusion coverage and losses remain
explicit. Neither these attempts nor the static throughput record establish
P1 task acceptance; no PUSH or full P2 follows.
