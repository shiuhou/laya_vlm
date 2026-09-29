# Research handoff: Laya Embodied Intelligence

## Purpose and status

This package is for a new ChatGPT session or researcher to understand the Laya
embodied manipulation project without assuming access to the original machine.
It records a paused research checkpoint, not an instruction to resume work.

The source repository is `/home/junhongli/projects/laya/laya-embodied-runtime`.
At packaging time it was clean at commit
`ea853019d3343ef4cb8eff8a2fdb43a91e760642`, on branch
`research/embodied-interface-discovery`, with local tag
`research-checkpoint-20260927-paused`. Its original experimental baseline is
`share_main` commit `b73b5b43dbef29749677fae06b25e94ca27bad87`.

The owner explicitly paused autonomous research. No physical or model
experiments were launched to assemble this handoff. The latest attempted
Task-2 retargeting batch stopped at a no-world preflight gate; do not describe it
as a physical result. The checkpoint says resumption requires a new explicit
user request.

## Research question

The project asks:

> What information must a perceptual embodied system recover, and at what
> abstraction level, to preserve competent robot decisions and closed-loop
> behavior under perceptual uncertainty?

The starting hypothesis assigned full-RGB semantic planning to a VLM, structured
sensor-derived bounded motor decisions to Laya, and atomic execution and
feasibility to deterministic controllers. This remains a hypothesis. Evidence
has **not** established a useful VLM-planner/Laya closed loop, nor a competent
sensor-driven hierarchical manipulation architecture. The current provisional
division gives semantic localization a role in target proposals and calibrated
deterministic geometry a role in local approach; local grasp/lift evidence is
still bounded and partly scripted.

## What the evidence says

### Established goal completion is not interaction-valid manipulation

The older privileged `top_drawer` Laya reference achieved official LIBERO
success in three same-condition runs. Its canonical trajectory used 122
primitives / 970 controls and reproduced exactly in replay. A subsequent native
contact audit inspected 48,500 snapshots covering 24,250 integrations. It found
zero raw designated fingerpad/handle contact rows. The recorded run closed the
drawer, but closure was associated with non-designated robot/drawer contacts and
intervals classified as neither historical relation. These measurements are
association partitions, not an exact causal decomposition. Preserve the claim
as **privileged goal-completion reference**; it does not establish intended
handle manipulation or an acquired skill.

### Task 2 has local mechanical evidence, not full task success

The task is to pick a tabletop wine bottle, place it in the bottom drawer,
release, and close the drawer. An earlier permissive diagnostic reached
`In(bottle, drawer)`, released, and partially closed the drawer, but the
placement orientation/extent prevented full closure. That was not the later
strict feasibility result.

Sensor-based work later demonstrated guarded local approaches and a narrow
grasp/lift slice. A registered executor test showed a bottle lift of about
9.28 mm with bilateral designated-pad contact maintained across the sampled
lift stages; the prefix was scripted and privileged-selected. This does not
demonstrate autonomous grasping, stable long-term holding, full Task-2
completion, or Laya policy competence.

Several strict Task-2 feasibility attempts found no qualifying interaction or
retention witness under their registered conditions. Later sensor-goal and
support studies expose unresolved issues: semantic point decoding varies with
the decoding procedure in a two-image diagnostic; current BOX support can
include gripper pixels; full depth can treat the robot itself as an obstacle;
temporal image motion alone does not establish ownership/holding. These results
are source- and fixture-bounded, not general impossibility claims.

### VLM and Laya roles remain unearned

The latest pinned Qwen2.5-VL 3B/7B capability probes did not produce coherent
scene relations or useful task-phase proposals on the selected reconstructed
images. A small 3B visual-subgoal probe matched only 1/3 prespecified primary
images, exactly its task-only control. The 7B comparison improved some isolated
relation labels but had zero coherent all-field scenes and zero primary subgoal
agreement. Constant answers account for several apparent correct labels.
These are bounded negative results, not proof that VLM visual reasoning is
universally ineffective.

Laya interface tests supplied coherent situation, action definitions, and
candidate effects. Their combination did not repair the tested candidate
choices. This means correct context alone did not rescue those tested rankings;
it does not prove all structured interfaces will fail. No modern VLM+Laya
combined closed-loop Task-1 run has been conducted.

### Most recent attempted physical experiment

The planned two-arm, fresh-reset Task-2 retargeting pair failed its required
`Matching clean no-world preflight` gate before the run directory or worker was
created. The checkpoint records zero worlds, controls, actions, and model calls,
and no retry or repair. There is **no physical result** from that attempt.

## Interpretation discipline

Keep these categories separate:

- **Observed:** directly supported by a cited frozen report/artifact.
- **Inference:** a bounded interpretation of those observations.
- **Unknown:** not measured or not identified by the intervention.

In particular, do not infer holding from gripper width, semantic identity from
unqualified depth points, safe clearance from BOX containment, a learned skill
from official success, or model incapacity from a small fixed interface test.
Simulator oracle values, sensor observations, proprioception, deterministic
geometry, learned estimates, and unknowns must remain separately labeled.

## Reading path

1. [`current_state.md`](current_state.md) — authoritative project snapshot at
   the pause checkpoint.
2. [`CURRENT_BELIEFS.md`](../CURRENT_BELIEFS.md) — concise living assessment and
   current falsifiers/confidence.
3. [`research_evidence_index.md`](research/research_evidence_index.md) — links to
   the most relevant findings and protocols.
4. [`autonomous_research_log.md`](research/autonomous_research_log.md) — full
   historical research record through iteration 57.
5. [`evidence/autonomous_research/pause_checkpoint_20260927.json`](evidence/autonomous_research/pause_checkpoint_20260927.json)
   — machine-readable pause state and final attempt details.
6. Start with the Task-1 native contact audit, Task-2 local grasp and sensor
   support findings, and the VLM/Laya capability/interface findings linked from
   the index.

## Data and reproducibility limits

This Git repository contains selected Markdown reports, JSON summaries,
protocols, and some figures. It does **not** contain the canonical raw
`runs/autonomous-research/` directory, all RGB-D/native episode records, full
per-token logits/traces, model checkpoints or weights, MuJoCo/LIBERO assets, or
the complete Python runtime repository. Absolute paths in reports refer to the
original workstation and will not resolve elsewhere.

The source checkpoint itself records that ignored raw artifacts are not backed
up by a Git tag. SHA-256 values and source paths for imported files are listed
in [`source_manifest.json`](../evidence/source_manifest.json). A manifest hash
can identify a missing raw artifact; it cannot reconstruct it.

## If research is later resumed

First obtain explicit authorization to resume, then inspect the source runtime
and its exact checkpoint locally. Do not treat this document package as
executable code or infer that prior preflight failures permit retries. Select a
new experiment only after checking the frozen beliefs, applicable protocols,
and development/evaluation boundary. Preserve the paused checkpoint and its
historical evidence.
