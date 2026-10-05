# P1 grounding / observability — annotation handoff

The preserved infrastructure checkpoint is **92865a8** on
`feat/p1-rgbd-geometry`. New preparation is isolated on
`feat/p1-grounding-observability`. **Task acceptance remains pending.**

## Human annotation first

The project user is the primary human annotator, not an independent third-party
reviewer. The annotation is blinded to this condition's LocateAnything outputs.
Only raw RGB is displayed; no model ROI, candidate, geometry decision or success
label appears in the page. The [frozen rules](p1-annotation-rules.md) bind every
export by version and SHA256. There are 50 first camera views, two entities per
view, and no prefilled labels. UNKNOWN and NOT_VISIBLE are accepted outcomes.

Local packet: `runs/p1/human-annotation-packet-v2-20261005/index.html`.
Portable download: `/home/junhongli/projects/laya/p1_blind_annotation_50views.zip`.
It needs no network: extract the folder and open `index.html` in a browser.
Partial export/resume is available; export regularly because browser autosave
is local to that browser/profile. Only a validated complete export qualifies.

- Dataset: `934a821132b6cbb0a15715444f05a87ce798d5ea4de3e580dad2f6c984323e04`.
- Rules: `p1-rgb-annotation-rules/2`.
- Rules SHA256: `d595017579fd4acabe16c563b74de8486ca64e5ee9650c294d78b30d7048ecfe`.
- Download SHA256: `77fe954bb55249113d7ac9c0f293a3c63b503f6acc2fadd98944b958ea3a32b2`.

Browser QA checked the actual page under Chromium 141 / Playwright 1.56.1:
image load, exact status choices, two-entity saving, incomplete-final-export
rejection, JSON download, navigation and reload/autosave. One synthetic UI-test
export remains quarantined in `/tmp`, never used as human evaluation. The
offline validator rejects it for incomplete coverage. No evaluation labels have
been manufactured or filled by agents.

After the user exports `annotations.complete.json`, validate and seal it:

```sh
.venv-p1/bin/python -m embodied_runtime.experiments.p1_annotation_packet validate \
  --packet runs/p1/human-annotation-packet-v2-20261005 \
  --annotations PATH/annotations.complete.json
```

## Frozen semantic experiment

Registration prepared before exposing the packet:
`runs/p1/grounding-preregistration-20261005.json`. It binds original sensor
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
  --packet runs/p1/human-annotation-packet-v2-20261005 \
  --annotations PATH/annotations.complete.json \
  --preregistration runs/p1/grounding-preregistration-20261005.json \
  --output runs/p1/new-fixed-query-evaluation
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

The three requested conclusions require the complete human annotations and
fixed semantic outputs: usable drawer-front support, fixed-reference
observability, and failure attribution among semantics, contamination, geometry
ambiguity and camera observability. None is declared resolved here.

The [ten-case temporal protocol](p1-temporal-sequence-protocol.md) is prospective:
**zero qualifying temporal sequences have been run**. The static throughput
recording does not satisfy it. Acquire/inspect those observation sequences after
the static grounding boundary is understood, without PUSH or full P2.
