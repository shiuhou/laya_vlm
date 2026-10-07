# Bounded BOX / SAM2 development diagnostic — 2026-10-07

**STOPPED at a launcher error before any SAM model call.** This batch does not
provide a segmentation comparison or change P1 Gate C. Reference/VERIFY remain
UNKNOWN. No geometry stage, tracker, Qwen, Laya or robot action ran.

Condition/code: clean `1ef973afca11439c8af25fd5e38bb8468262c504` on
`feat/p1-segmentation-surface`; [protocol](../../../research/p1_box_sam2_protocol.md).
Two already-inspected development wrist frames, init25/26 seed1, 384×256;
not held-out evaluation. Queries, LocateAnything settings/checkpoint, typed
contract, original geometry gates and original BOX denominator are unchanged.
No evaluation annotations were read. All three native SAM mask hypotheses were
specified for retention without selection, but none was produced.

## Observed result and first boundary

- Isolated SAM2.1 tiny preparation passed dependency and import/API checks.
  Torch2.5.1+cu121, torchvision0.20.1+cu121, official pinned SAM source and
  checkpoint, full artifact-hash dependency lock. Existing environments unchanged.
  Initial packaging failure and separately recorded preparation correction retained.
- Init25 reused the authenticated original complete-EOS BOX. Init26 made exactly
  one fixed-query BOX call on explicit GPU0 UUID
  `GPU-dfe7bb45-8b97-0077-34a1-7012d2454d3b`. Both BOX records have 208 input
  tokens, 39 output tokens, terminal EOS and no truncation; BOX stage sealed.
- The parent launcher mistakenly used
  `str(Path('.venv-p1-sam2/bin/python').resolve())`. The venv executable is a
  symlink; resolving it invoked the base interpreter
  `/home/junhongli/miniforge3/envs/laya-embodied/bin/python3.10`, bypassing the
  prepared venv context. The mandatory Torch version guard failed, exit1.
  Actual wrong-interpreter Torch version is unrecorded; its mismatch is proven.
- Failure precedes GPU allocation, SAM import/build, checkpoint loading and
  `set_image`/`predict`. Native masks/logits/scores **0**; matched geometry
  evaluations **0**. No masked visual review is possible. Independent read-only
  code-path/receipt audit confirms this boundary. No retry followed.

This is experiment-launch infrastructure failure, not a model/perception result.
It provides no evidence about mask contamination, depth-support compatibility,
camera feasibility or executable patch availability. The preregistered mask
occupancy/original-BOX bound remains untested.

## Preserved evidence

[Summary](summary.json), [registration](registration.json),
[independent review](independent-review.json), [invariants](invariant-receipt.json),
[termination](termination.json) and [portable evidence archive](evidence.tar.gz).
[Artifact index](artifact-index.json) authenticates all archive members and the
existing RGB-D source archive dependency. The archive retains raw BOX inputs,
token IDs/outputs/audits, inherited request/response, stage logs/exit receipts,
failure trace, successful environment setup/lock and original packaging failure.
No weights, environment tree or disposable GPU cache is archived.

Core runtime, geometry, tracker, servo, scheduling, contracts, sensor adapter and
LocateAnything provider bytes match `1fedb9c`; see invariant receipt. Existing
wrapper verification remains ten focused passing tests plus changed-file Ruff;
no broad suite or duplicate model call was added in this execution batch.
Archive member bytes were checked against the canonical local experiment files.

## Next bounded step, not executed

Correct only the process launcher: invoke the absolute venv executable path
without symlink resolution. Record executable/prefix/Torch identity before any
new condition starts. Preserve this failed attempt; any follow-up gets a distinct
registration and may reuse sealed BOX data only under exact source/hash checks.
Do not alter query, model, mask settings, geometry gates or denominator to address
this launch error. No POINT/decoder work, tracker, PUSH or model integration is
earned by this result.
