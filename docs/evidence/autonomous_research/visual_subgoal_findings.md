# Visual local-objective proposals versus the task-only prior

The fixed Qwen2.5-VL-3B interface does not improve the three scored local-objective
proposals when given RGB. All three answers are `establish_grasp`, exactly the
task-only answer; one of the three matches the preregistered visual labels.
This is a small negative development result, not evidence that visual reasoning
or higher-level situation understanding is inherently useless.

## Condition and results

Seven unique calls at clean revision `3d64d7ccb7e15fd79cac626c66738489e79d8380`:
one task-only call and six full-camera RGB calls, all independent messages without
history. Same pinned Qwen2.5-VL-3B checkpoint, native BF16/SDPA, greedy generation,
32-token ceiling, seed 1 and four CPU threads as previous visual probes. The
instruction asks for a provisional local objective, explicitly subject to
independent physical-precondition verification. No candidate actions or oracle
variables enter the model.

| Image | Visible situation | Prespecified scored labels | Answer |
|---|---|---|---|
| none | task text only | baseline, not an independent physical case | establish_grasp |
| 0 | bottle on table, gripper well above | approach_object | establish_grasp |
| 1 | gripper near bottle neck | approach_object or establish_grasp | establish_grasp |
| 2 | bottle visibly suspended, outside drawer | transport_object | establish_grasp |
| 3 | bottle near/over drawer rim | unscored, ambiguous | establish_grasp |
| 4 | diagonal bottle in open drawer | unscored, ambiguous | establish_grasp |
| 5 | partly closed drawer, obscured bottle | unscored, ambiguous | uncertain |

Primary visual-label agreement and useful accepted proposal coverage are both
1/3, versus 1/3 for the sole task-only answer evaluated on the same three cases.
That reused baseline answer is one inference, not three independent trials.
All seven calls complete with EOS and valid labels; none truncates. Image 5
changes the categorical answer, so claiming the model ignores all image input
would be incorrect. No closed-loop control or successful planning is claimed.

## Image provenance and annotation boundary

The images are sequentially decoded frames 7,55,135,183,239,319 from the archived
Task-2 permissive diagnostic video, left 600-by-600 camera viewport only. They
are lossy, resampled views from a primitive-trace reconstruction, not original
control replay or newly collected raw camera observations. Two reviewers inspect
the isolated camera views; source-frame annotations and the right-hand HUD are
excluded. PNGs in input preparations 01 and 02 are byte-identical; preparation 02
binds the amended evaluation protocol.

Before inference, review identified a potential label confound: a provisional
drawer objective is not a declaration that hidden placement-fit conditions hold.
Consequently only images 0,1,2 receive primary labels. Images 3,4,5 are descriptive
and have no correctness, safety, fit or release-readiness score. The generator
never reads evaluator labels; its preflight and run record their frozen hash.

Actual consumed inputs are checked: task-only 126 tokens and no image; RGB cases
569 tokens including 441 image tokens, with native preprocessing from 600 to
588 pixels. Full forward input IDs, image tensor/grid, attention masks, generated
IDs, decoded text, full-vocabulary greedy logits and EOS all verify. The same
checks pass in the independent worktree's summary review. Full regression at the
run revision passes 728 tests.

## Interpretation and next decisions

Observed failure is phase-sensitive proposal selection on these three images.
Competing explanations remain: weak scene/relationship perception, inability to
bind those facts to the discrete objective vocabulary, or domination by the task
prior. The experiment does not isolate these causes or establish that a larger
model, another representation, or richer history would fail.

Three isolated investigations now proceed in parallel:

1. The same VLM reads visible image relationships without objective labels, with
   mirrored-image and task-prior controls. Test scene understanding directly.
2. The same Laya receives a correct, coherent supplied situation packet while
   holding physical candidates/effects fixed. Test use separately from acquisition.
3. A paired physical sensor diagnostic examines object retention during an
   existing grasp/lift prefix against a no-grasp intervention. Separate sensor
   observations from entity-tagged oracle contact and avoid width-equals-held.

These are tests of competing responsibilities, not three predetermined runtime
components. Nothing is integrated into the generic runtime on the strength of
this negative result. No extra model, threshold sweep or prompt search is started.

## Evidence

All raw paths are under `runs/autonomous-research/`:

- `visual-subgoal-inputs-01/independent-preinference-review.json`: independent
  exact image extraction and pre-inference annotation review.
- `visual-subgoal-inputs-02/`: model RGB PNGs, manifest, extraction evidence.
- `visual-subgoal-labels-01/labels.json`: frozen scope and primary labels.
- `visual-subgoal-preflight-01/`, `visual-subgoal-run-01/`: complete native inputs,
  forward traces, full logits, raw responses and audited summary.
- `regression-3d64d7c.log`: 728 passing tests.

The checked-in [summary](visual_subgoal_summary.json) retains results, revisions
and raw evidence hashes. The [protocol](../../research/visual_subgoal_probe_protocol.md)
and experiment module preserve the exact preparation and inference conditions.
