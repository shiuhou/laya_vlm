> Evidence record; proposed next steps and reproduction commands require separate review.
> Current authority: [current_state.md](../../current_state.md).

# Bounded search for a task-sensitive interface

2026-09-23, baseline `0f62862`. Exploratory diagnostics, **not E0**.
Protocol and sequential selection decisions: [interface_search_protocol.md](interface_search_protocol.md).

## Conclusion

The smallest **tested positive interface** is a narrow task-progress judgment:

```text
observed articulation: open | partly open | closed
requested articulation: open | closed
    → DONE | CONTINUE
```

Rendered as two short sentences, it correctly handles all six combinations, both
option orders, and two identical-input repeats. It changes its answer when only
the requested goal changes. This is genuine but limited goal sensitivity.
It is **not** a validated action-selection interface, an autonomous drawer policy,
or proof of a mathematically minimal schema. No replacement CDS is promoted.

For eleven atomic actions, no tested non-answer-equivalent interface survived the
geometry/goal controls. Smaller inputs overcome some presentation failures but
do not establish quantitative comparison or goal-conditioned motion competence.
The evidence points more strongly toward a checkpoint/interface computational
mismatch than toward a need for more world-state fields.

## Experiment design and evidence

Four sequentially declared suites, 372 fixtures × two calls = **744 model calls**.
Some fixtures reuse identical categorical inputs: these are not 372 independent
states. Discovery informed validation; the final goal-placement extension followed
an observed question-insensitivity pattern. This adaptive search is not an unbiased
benchmark or evidence of generalization to arbitrary prompts.

All calls use the same local model bytes, CUDA/bfloat16, fixed seed 1 per process,
unchanged weights and calibration. All 372 same-fixture comparisons have identical
choices, returned distributions and raw logits. Token audits and actual forward
tokens agree; inputs use 45–182 total tokens, with no clipping. No calls failed,
no intents are missing, and planned fixture/repeat coverage is complete.

Eleven-action conditions retain all eleven identities with explicit mappings when
labels/order change. No ranking or feasibility pruning is silently introduced.
No history, privileged future effects or simulator predictions enter the selected
minimal inputs. No model choice is executed. Physics is checked against previously
recorded independent counterfactuals, not new collection conditioned on model choices.

### 1. Smaller geometry: encouraging discovery, failed validation

Discovery used six signed 30 mm axis offsets plus coincidence. One fixed approach
objective, no grip change, and eleven alternatives:

| Presentation | Correct nominal choices |
|---|---:|
| Absolute numeric XYZ, original compact action descriptions | 1/7 |
| Numeric relative XYZ, original descriptions | 1/7 |
| Spatial sentence, original descriptions | 3/7 |
| Spatial sentence, English action descriptions | 5/7 |
| Spatial sentence, English descriptions, neutral IDs | 7/7 |

Example selected state: `The target is 30 mm in negative X relative to the tool.`
Criteria use neutral `A00…A10` IDs mapped to physical tokens, with descriptions
such as `move in negative X`. These are geometric facts and nominal semantics,
not candidate-local predicted outcomes. Explicit request-matching controls scored
4/6; compact negative-X/negative-Y requests incorrectly selected rotation.

Validation of the selected sentence/neutral presentation:

| Diagnostic | Original order | Reversed order | Reassigned neutral IDs |
|---|---:|---:|---:|
| New 12/65 mm signed axes plus zero | 13/13 | 13/13 | 13/13 |
| Six mixed-axis vectors | 2/6 | 3/6 | 2/6 |
| Same six axial states, goal changed to move **away** | 0/6 | 0/6 | 0/6 |

With candidates matched to this presentation, absolute numeric XYZ scored 2/13
and numeric delta 3/13. Thus candidate naming alone does not explain the difference.
Archived oracle relations scored **1/18**, perceptual relations **4/18**, against
each branch's own nominal geometric label. This does not mean perception is better:
it demonstrates reference failure on mixed-axis inputs. The physical states are
the existing 18 pairs across init IDs 0/1/2, not new independent trajectories.

Moving toward/away intent into state did not solve motion choice: original order
got 6/12 (all toward, none away); reversed order 7/12. The successful single-axis
results mostly resemble directional matching, not robust use of the objective.
This is a behavioral interpretation, not a claim about internal attention or training.

### 2. Explicit applicability rules are not sufficient without pre-solving

A separate diagnostic gave candidates human-written conditions such as
`positive X error largest`. It scored 9/25 on mixed-axis/archived geometry.
When code retained only the dominant signed axis, it scored **25/25**.

That projection already performs the geometric argmax. It is intentionally labeled
`answer_equivalent_projection`, and the criteria `handwritten_policy_in_criteria`.
It cannot support a claim that Laya learned the policy or that these are minimally
sufficient observations. It demonstrates how easily an interface can conceal the
decision algorithm upstream.

Even this perfect nominal control has independent physical local support at only
9/18 archived boundaries, and matches the evaluator's near-best set at only 5/18.
The existing evaluator rubric was recomputed from raw native probes, not model
outputs. Examples:

| Boundary | Dominant-axis choice | Independent physical evidence |
|---|---|---|
| init 0, 0 | MV_FWD | +7.75 mm surface approach versus STOP; useful approach |
| init 0, 29 | MV_FWD | +0.19 mm versus STOP; no demonstrated local utility; MV_RIGHT supported |
| init 0, 48 | MV_FWD | +1.24 mm closure versus STOP; useful, but MV_RIGHT nearer best |
| init 0, 144 | MV_FWD | +0.004 mm closure versus STOP; shared drift dominates |
| init 0, 152 | MV_RIGHT | +6.77 mm closure versus STOP; locally supported |

The visible-handle centroid is not a universal contact/closing setpoint. Correct
point-approach arithmetic is not equivalent to correct drawer behavior; loaded
semantics and multi-step strategy remain separate limitations. Lack of one-step
support does not prove an action can never prepare later success.

### 3. A narrow, genuinely goal-sensitive progress interface

Numeric joint position with open/close thresholds in the question scored 4/6;
categorical observed state with the requested goal only in the question also
scored 4/6 (5/6 with reversed options). On archived states × two goals, these
scored 24/36 and 28/36. Majority CONTINUE and repeated phase labels make pooled
accuracy misleading; goal contrasts are essential.

The successful tested presentation is:

```text
State: The drawer is currently open. The requested state is closed.
Question: Does the observed drawer state satisfy the requested goal?
A: DONE: goal satisfied
B: CONTINUE: goal not satisfied
```

| Observed | Requested | Choice | Selected probability | Margin |
|---|---|---|---:|---:|
| open | open | DONE | .5548 | .1096 |
| open | closed | CONTINUE | .5563 | .1126 |
| partly open | open | CONTINUE | .5852 | .1704 |
| partly open | closed | CONTINUE | .5650 | .1300 |
| closed | open | CONTINUE | .6015 | .2030 |
| closed | closed | DONE | .6281 | .2562 |

Both option orders score 6/6. The equivalent two-field JSON representation scores
4/6 in each order. Representation matters even when information content matches.
The sentence condition consumes only 12–13 state tokens. These modest margins
must not be compared directly with sharpened eleven-option probabilities: the
checkpoint uses a different temperature bucket for two choices.

The categorical measurement is **goal-independent**, unlike the dominant-axis
answer projection. Installed `WoodenCabinet` predicates define open as joint
qpos < -0.14 m and closed as qpos > 0 m; otherwise the state is intermediate.
These fixed current-state thresholds were not tuned. The requested goal remains
a separate input; code does not compute their equality before inference.

The existing 18 physical boundaries contain seven open, ten intermediate and one
closed state. Their observed categories come from archived **before.qpos_m**,
explicitly privileged. Closed classification agrees with the recorded native
success predicate at every boundary. Rendering each boundary under both requested
goals produces exactly the already-tested six payloads: 36 payload-reuse checks,
**not 36 new inference trials**. Opening goals are diagnostic counterfactual tasks,
not claims of collected opening trajectories. Current perception cannot supply
this articulation estimate; it remains unknown, not oracle-filled.

The extension changes both goal placement and comparative question/criterion
wording. It establishes a working combination, not an isolated causal effect of
moving one string. Unseen paraphrases, ambiguous categories, unknowns and temporal
instability have not been validated. DONE/CONTINUE are status judgments, **not**
STOP or another atomic intervention. Do not deploy them as physical commands.

## What this changes—and does not

- Full CDS geometry is not necessary for the narrow completion judgment; two
  categorical facts suffice on this finite test. A deterministic comparator is
  also sufficient and should remain the exact reference baseline.
- More contact, history, uncertainty or provenance fields are not justified by
  these failures. They were not individually falsified as useful for other tasks.
- No robust minimal interface for full atomic drawer decisions was found.
  Missing effects remain a separate hypothesis; none were supplied here.
- Candidate semantics, loaded dynamics, and task-level utility still require
  separate validation. No thresholds, runtime CDS, candidate gates or executor
  semantics changed. Tracking inactive; covariance still heuristic/uncalibrated.
- **Useful full-task oracle reference: NO. E0 freeze/run: NO.** A revised,
  explicitly narrow task-progress fidelity study is now a plausible proposal,
  not an automatic redefinition of the original E0.

Smallest next test: preregister held-out linguistic presentations and unknown /
near-boundary articulation cases for this two-field progress interface, against
the deterministic comparator. Then decide whether a task-progress reference is
scientifically useful enough to study its sensor-derived counterpart. For action
selection, first validate goal-sensitive primitive competence in a known operating
envelope; do not collect hundreds of perceptual pairs against the current model.

## Artifacts, implementation and verification

`embodied_runtime/experiments/interface_search.py` is an offline CLI with four
bounded fixture suites and raw-only summary recovery. It preserves intents,
outputs, logits, token audits, fixture/source identities and calibration. Summary
rejects corrupt/missing inference evidence and checks planned repeat coverage.
It never imports a simulator or executes a model action.

Raw ignored artifacts: `runs/interface-search/{discovery,validation,final,goal-placement}-v01/`.
All four exited zero. Local model content identity:
`9fba4af58ef08fd2703a011f5678c9a999223c939380048b9f2b7383b6b9e704`.
Runtime: Python 3.10.21, torch 2.2.0, transformers 4.57.3, laya 0.3.4,
NumPy 1.26.4. MuJoCo 3.5.0 / robosuite 1.4.1 remain installed; no new simulator
execution or vision inference was needed. Runs record dirty source hashes and
are not frozen-release experiments. Historical handoffs/artifacts remain intact.

Commands (each collection needs a fresh output directory):

```sh
P=/home/junhongli/miniforge3/envs/laya-embodied/bin/python
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 $P \
  -m embodied_runtime.experiments.interface_search --suite discovery \
  --output runs/interface-search/discovery-v01
# Same command with --suite validation / final / goal-placement and matching output.
$P -m embodied_runtime.experiments.interface_search \
  --summarize runs/interface-search/goal-placement-v01
$P -m pytest -q tests/test_interface_search.py
$P -m pytest -q
$P -m ruff check .
$P -m compileall -q embodied_runtime tests
```

Verification: **15 focused tests; 226 full tests passed in 5.35 s; lint and
compileall passed**. No formal E0/E1, release tag, dependency change or download.
