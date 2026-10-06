# Bounded P1 observability closure evidence

Outcome: **Gate C**, no P2/Qwen/Laya/PUSH. Read
[the measured report](../../../p1-observability-closure-results.md).
Reference POINT decoder/budget/query research is closed.

The baseline freeze and preregistration were committed before the new runs.
Static/temporal/init0 cost code is `fb2b299`; init12/24 used the isolated
reporting-only `eb39068`, preserved by tag
`p1-stream-reporting-condition-eb39068`. Its one-line production fix is integrated
as `daf6a26`. Queries, geometry code/config and executor are unchanged.

## Portable contents

- `freeze.json`, `preregistration.json`: baseline hashes and fixed finite scope.
- `static-evidence.tar.xz`: all50 generated sensor inventories/complete hypotheses,
  original patches, generation seal, offline evaluation and original100-call
  prediction/raw-output/request/model-input/audit records. No raw controls are
  warm-start inputs. `static-archive-members.json` hashes every archived file;
  `archive-validation.json` verifies all53 generation-sealed files before cleanup.
- `static-summary.json`: evaluator-only original target/tool support0/25;
  annotated plane overlap21/25 BOX searches, with reference identity still unknown.
- `offline-evaluation-contact-sheet.*`: actually inspected raw RGB plus explicitly
  evaluator-only model BOX/label/original-candidate projections at init0/12/24.
- `temporal-evidence.tar.gz`: all10 case manifests, empty seeds, uninitialized
  perception logs, raw contact sheets, timing summaries and isolated evaluator
  fixture journals. Evaluator journals must never feed perception/policy.
- `temporal-review.json`, `temporal-artifact-index.json`: AI-agent review,
  qualification limits, hashes for the610-bundle raw recordings and temporal
  packet. Agent inspection is not completed independent-human annotation.
- `stream-evidence.tar.gz`, `stream-summary.json`: exact six-search workload,
  candidates, timings, seven persisted sensor snapshots, source receipts,
  operational/reporting registrations, init0 reporting failure and corrected
  recoverable statistics. Valid-target Hz0; target tracking was not measured.
- `stream-initial-failure.tar.gz`: the preceding Mesa hardware-default failure,
  before any capture. The temporal archive similarly retains its two failures.
- `scope-gate.json`: exact blocked criteria and no automatic recovery decision.
- `validation.json`, `cleanup.json`, `checksums.json`: focused checks, lossless
  preservation and removed reconstructible copies/caches/worktree.

The static human annotations remain at
`../corrected_v2_seal_20261005/annotations.corrected-v2.complete.json`; unchanged
version2/dataset/rules/sha bindings are validated before evaluation. Independence
is user-reported. UNKNOWN is never scored as NOT_VISIBLE.

## Local raw data and reconstruction

Original frozen capture:
`runs/p1/static-25init-20261005/`.
Original100-call source:
`runs/p1/corrected-v2-fixed-query-evaluation-20261005/`.
New temporal raw data:
`runs/p1/observability-closure-temporal-software7-20261007/`.
Raw-only human review:
`runs/p1/observability-closure-temporal-software7-packet-20261007/index.html`
(160 images,20 full videos, no model/geometry overlays).
New live cost data:
`runs/p1/observability-closure-stream-software7-20261007/`.

Raw temporal RGB-D is preserved locally (about821MiB); raw source datasets and
full temporal videos are not supplied by a Git clone. Their artifact hashes
remain in the index. The portable archives permit result inspection and static
score reconstruction; fresh sensor regeneration additionally requires the
identified original capture, not newly generated substitute images.

The expanded static per-frame JSON cache was removed **after** lossless archive
validation. Restore into a new empty directory before rerunning the scorer:

```sh
mkdir /tmp/p1-closure-inspection
tar -xJf docs/evidence/p1_grounding/observability_closure_20261007/static-evidence.tar.xz -C /tmp/p1-closure-inspection
.venv-p1/bin/python -m embodied_runtime.experiments.p1_observability_closure score \
  --generated /tmp/p1-closure-inspection/static \
  --annotations docs/evidence/p1_grounding/corrected_v2_seal_20261005/annotations.corrected-v2.complete.json \
  --output /tmp/p1-closure-rescore
```

For a full sensor-only regeneration, use the tagged `fb2b299` code with original
datasets and exclusive new output directories:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv-p1/bin/python \
  -m embodied_runtime.experiments.p1_observability_closure generate \
  --source runs/p1/static-25init-20261005 \
  --predictions runs/p1/corrected-v2-fixed-query-evaluation-20261005 \
  --packet runs/p1/human-annotation-packet-v2-20261005 \
  --output runs/p1/new-exclusive-closure-generation
```

This does not launch a model. Do not retune queries/gates or replace recorded
images. Live environment details are in the operational registrations: explicitly
inventoried Mesa software EGL device7, dual384×256, original seed/init/reset.
Do not assume device7 is the software device on another host without enumeration.
