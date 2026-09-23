> Historical record; its plans and checkout paths are not current instructions.
> Current authority: [current_state.md](../../current_state.md).

# Integration and architecture-review checkpoint

2026-09-23. Integration, verification and synthesis only. This report introduces
no new experiment, prompt, candidate semantics, planner or runtime architecture.
[current_state.md](../../current_state.md) remains the operational authority; historical
handoffs retain their original negative results and working-source identities.

## 1. MERGE RESULT

Previous shared baseline: `eddbcde04649419d8d5d44e62e433882578328eb`.

| Track | Integrated range, excluding old baseline | Track tip |
|---|---|---|
| Research | `eddbcde..84cd781` (one commit) | `84cd781` — six bounded diagnostic implementations, tests and reports |
| Demo | `eddbcde..59dae8a` (two commits) | `84abdb8` telemetry/inspector, then `59dae8a` feedback and diagnostic evidence |

Both tracks initially contained relevant uncommitted work. Integration stopped;
the user then explicitly authorized committing it. Research's 28 files and demo's
20 remaining files were committed separately after each track passed verification.
No unrelated changes or ignored runs were included.

Normal non-squash merges on `share_main`: research `21a7a32`, then demo `ffd184a`.
Only `docs/current_state.md` and `docs/development_tracks.md` conflicted. Resolution
retains the research progression and demo feedback evidence, replaces competing
checkout descriptions with the integration inventory, and records the original
worktree locations of ignored evidence. `docs/architecture.md` merged automatically;
both entry-point lists and information boundaries were reviewed. No code conflicts
or integration behavior fixes were needed.

The final checkpoint includes the documentation commit containing this report;
use `git rev-parse HEAD` on `share_main` for its complete identity. Track branches
retain their committed tips; there was no reset, squash, branch rename or push.

## 2. VERIFICATION

Existing interpreter: `/home/junhongli/miniforge3/envs/laya-embodied/bin/python`.

| Scope | pytest | ruff | compileall / whitespace |
|---|---:|---|---|
| Research before commit | 362 passed | pass | pass |
| Demo before commit | 266 passed | pass | pass |
| Integrated implementation | **384 passed, 0 failed** | pass | pass |

Commands from each checkout:

```sh
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m pytest -q
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m ruff check .
/home/junhongli/miniforge3/envs/laya-embodied/bin/python -m compileall -q embodied_runtime tests
git diff --check
```

Additional integration checks:

- All 13 research/demo/legacy CLI entry points load and execute `--help`; shared
  runtime, fusion, CDS, inspector and feedback modules import. The full suite
  exercises runtime execution with test backends and replay/evidence contracts.
- All changed Python files are under `embodied_runtime/experiments/`. Shared
  runtime, provider, executor, fusion, adapters, CDS and provenance recorder are
  unchanged from `eddbcde`. No tracked `runs/` files were introduced.
- Existing tests reject privileged visual inputs, preserve state/effect source,
  basis and privilege, propagate privilege through derived geometry, enforce
  empty effects in primary State-Gap pairing, and reject mismatched evidence.
  Demo code review confirms new evaluator metrics stay in recording/reporting;
  experimental text transformations are not wired into the live bridge.
- Read-only chain validation passes for seven research runs (effect binding,
  provider comparison, both completed clause-order providers, goal placement,
  selective grip, explicit consequence) and seven frozen/synthetic demo probes.
- Rebuilt evidence audits on disposable copies of the inspector run, completed
  feedback run and failed feedback startup. Respectively 4/8/0 verified executions,
  3/7/0 feedback deliveries, and 0/0/1 recorded failures; no audit issues. Original
  raw-log hashes remain unchanged. Existing successful control-replay reports
  match their raw-source hashes and recorded tolerances.

No full-suite failure or warning summary was emitted. A supplemental audit first
used a guessed geometry directory name; correcting it to the report's actual
`frozen-step0-geometry-reflection-v01` resolved that checker error without a repo
change. There were no detected pre-existing test failures or integration regressions.

Limits: this checkpoint did not run fresh Laya/vision inference, a new simulator
episode or a new physical control replay. Replay numbers below are archived
results whose source identities were checked, not new independent rollouts.
Historical upstream warnings, GPU startup failure and execution-envelope flags
remain in the evidence; passing tests do not remove those scientific limitations.

## 3. WHAT CHANGED SINCE THE PREVIOUS SHARE_MAIN

**A. Shared runtime/foundations:** no behavior or schema changes. Both tracks reuse
the existing belief, validity, canonical interfaces, execution and provenance.

**B. Decision-interface research:** six opt-in offline diagnostic modules:
`effect_binding`, `provider_comparison`, `clause_order`, `goal_placement`,
`selective_grip`, `explicit_consequence`. The Qwen adapter is research-only.
Their transformed descriptions, reassigned effects and questions are experimental
conditions, not shared defaults or deployed policies.

**C. Demo tooling:** live telemetry, a raw-derived HTML inspector, decision-to-control
checks, feedback delivery audits and opt-in final observation without another action.
Media/report tooling exposes missing outcomes, fallback/forced choices, candidate
vetoes and evaluator-only task progress. The model still receives no effects/history.

**D. Documentation/evidence:** six research protocol/handoff pairs; feedback and
reproduction documentation; decision autopsy; geometry, distance, local-objective,
translation-only, synthetic-direction and order diagnostics. Authoritative documents
now identify both merged tracks and put further experiments on hold for review.

**E. Tests:** six research test modules, demo feedback tests and expanded inspector/
execution-evidence tests. The combined suite adds 140 tests to the old 244-test baseline.

Raw runs remain ignored and local. Research successor paths belong to
`/home/junhongli/projects/laya-decision-interface/runs/`; demo successor paths to
`/home/junhongli/projects/laya-mujoco-demo/runs/`; earlier baseline evidence remains
in `laya-embodied-runtime/runs/`. Relative artifact links in historical reports
refer to the originating worktree, not automatically to copies in `share_main`.
A Git clone contains reports/code, not a complete evidence bundle. No artifacts
were moved or original source hashes rewritten during integration.

## 4. LATEST RESEARCH FINDINGS

These are bounded interventions with different fixtures, option counts and purposes;
their scores must not be pooled into a task-success rate.

| Progression | Observation | What it weakens or leaves open |
|---|---|---|
| Action semantics / distance effects | Demo descriptions already encode nominal direction and 10 mm displacement. Explicit nominal distance changes leave GRASP top-ranked and fail to establish consistent approach ranking. | Missing arithmetic annotations alone are not a demonstrated remedy; nominal geometry is not dynamics or task utility. |
| Fixed-option effects | With eleven actions, true absolute plus STOP-relative effects give native utility 0/16; anonymous full effects give 9/16, mostly opening. Reassignment changes identities. | Not complete effect insensitivity, nor simply absence of STOP-relative facts. Goal-conditioned binding still fails. |
| Independent provider / clause order | Qwen improves native utility to 8/16 but fails the gate. Reordering STOP clauses changes choices without resolving opening bias. | Not a demonstrated Laya-only defect; not explained solely by the last STOP clause. Two providers do not establish universal failure. |
| Goal position | Goal-last changes 25/64 choices; anonymous true utility 9/16 → 11/16, native remains 0/16. No context/assignment passes both goals and both orders. | Position matters; it does not establish useful goal/effect binding. |
| GRASP/RELEASE wording | Selective anonymization improves true utility 0/16 → 5/16, all opening; closing stays 0/8. Appropriate goal reversal is only 1/16. | Wording contributes but does not explain the core deficit. Length/position also change; this is not canonical representation. |
| Explicit desired consequence | Only 2/32 choices change; no corrections and one lost success. True utility 5/16 → 4/16; closing stays 0/8; goal reversal stays 1/16. | Supplying the desired consequence does not repair candidate matching. An exclusively upstream goal-transformation account is inadequate for these fixtures. |
| Candidate ordering | Frozen demo swap changes GRASP to MV_BACK, not a useful approach. Synthetic negative-pair permutation fixes -X and -Z but leaves -Y wrong. | Ordering materially affects ranking; neither a pure last-slot rule nor order-independent signed-direction incapacity explains all observations. |

The demo's translation-only reflection retains MV_FWD in both geometries. Minimal
synthetic directions initially score 3/6: positive axes pass, negative axes fail.
The ordering successor changes that attribution; the original negative results
remain valid for their original menus. No positive cases were tested in the new
order, so the two corrected negatives do not establish reliable sign reversal.

Current unresolved ambiguity includes predicate recognition versus competitive
selection, action wording/identity/context interactions, goal integration and useful
geometry grounding. Missing state may still matter for real manipulation, but
cannot alone explain failure on fully supplied local consequence predicates.
No unique internal mechanism or scientifically defensible useful manipulation
reference is established. Formal E0 remains blocked; the proposed binary predicate
diagnostic was not run at this checkpoint.

## 5. CURRENT DEMO FINDINGS

Established: sensor → belief → compact CDS → real Laya → validation → atomic
executor → MuJoCo connectivity, with inspectable decision/control provenance and
outcome-to-next-input delivery. The latest archived episode has eight GRASP/RELEASE
choices, nine captures, seven verified feedback deliveries, 64 controls and an
archived exact replay across 73 boundaries. The failed first startup is preserved.

Not demonstrated: target contact, useful drawer manipulation, task completion,
robust goal-sensitive policy, causal use of feedback or general asynchronous
robustness. Drawer closure is **0 mm**, contact **false**, success **false**.
Choice alternation coincides with the gate removing the previous action; fresh
inputs reaching Laya are not proof that it uses them usefully. Six translations
remain available but unchosen. Earlier asynchronous smoke is a separate historical
configuration, not this synchronous demo.

The local-objective pair leaves GRASP top-ranked (28.86% → 31.22%). It adds both
an objective and a contact premise; it does not isolate decomposition alone.
Local-objective/task-decomposition remains a hypothesis, not accepted architecture.

## 6. ARCHITECTURAL HISTORY

1. **Original senior idea (design intent):** structure world evidence and candidates;
   let Laya judge permitted behaviors while deterministic execution owns motor control.
2. **BeliefStore and physics candidates:** `cc3c330` integrates
   `PhysicsPreviewCandidateBuilder`, `World.predict_all()` and Jev contracts.
   Code produces feasibility/rejection and predicted contact/approach/force facts
   before Laya chooses. See [historical handoff](handoff.md).
3. **Vision/non-oracle path:** `138f50b` introduces a separate visual runner;
   temporal fusion follows, and `37c5daa` adds visual candidate validity and durable
   provenance. Geometry/validity are retained without simulator preview input.
4. **CDS and separate effects:** `16c4fca` introduces canonical state, explicitly
   separate CandidateEffectBundle and matched offline oracle/perceptual replay.
   Primary State Gap has empty effects; Effect Gap is a different comparison.
5. **Oracle agreement is not usefulness:** reference pilots and `0f62862`, `a7da3d8`,
   `3be0fc5` expose unhelpful oracle-conditioned choices, loaded controller drift,
   interface failures and a narrower positive status/missingness result.
6. **Privilege isolation clarified:** preview remains available in the legacy oracle
   branch and labeled diagnostics, but is excluded from visual inputs and primary
   no-effect replay. This isolation began before the usefulness findings; it was
   not a later deletion of World.predict_all().
7. **Recent flat-choice diagnostics:** frozen effects, providers, wording, goal
   placement and order reveal sensitivity without a useful manipulation reference.
8. **Reason to reassess:** working physical connectivity and richer information do
   not ensure useful atomic ranking. The state-to-candidate-to-judgment responsibility
   boundary needs review before another local intervention.

## 7. WHAT WE MAY HAVE LOST

The earlier preview layer did two things at once: it accessed privileged simulator
information and processed actions into feasibility and consequences. Excluding its
outputs is necessary for honest visual research, but does not establish that the
processing role itself is unnecessary.

The visual builder still computes validity and soft geometric metadata. The compact
demo supplies only permitted nominal descriptions, omitting that soft metadata and
effects. The model therefore must bind raw relative geometry, nominal movements and
task intent. It is plausible that this burden weakens the intended division:
**code owns geometry/physics/candidate processing; model owns judgment**.

That is a hypothesis, not a measured causal loss. Earlier preview and later visual
paths differ in information, controllers/context and presentation; the successful
Jev collection trace used a different hierarchy and is not Laya competence evidence.
No matched ablation establishes that restoring preview would solve the deficit.
Processing can itself embed policy: precomputing a winning axis or filtering to one
action transfers judgment to code and must be disclosed and independently evaluated.

## 8. ARCHITECTURE OPTIONS TO REVIEW NEXT

Review alternatives only; none is implemented or selected by this checkpoint.

| Option | Scientific question | Leakage / attribution risk |
|---|---|---|
| A. Current flat atomic choice | Can this backend reliably consume the existing state/candidate interface? | Lowest additional processing confound, but oracle fixture inputs still require labels; presentation sensitivity can masquerade as State Gap. |
| B. Geometry-only candidate processor | Does explicit nominal consequence computation improve judgment without simulator future state? | Sensor-only geometry is non-oracle, but oracle geometry propagates privilege. Sorting by the desired winner can leak policy; distance is not task utility. |
| C. Feasibility/precondition subset | Does removing inapplicable options improve judgment? | Simulator contact/success can leak hidden state; hand-coded task rules may solve selection. Report coverage, rejected useful actions and singleton decisions. |
| D. Local intent → subset → Laya | Does separating task intent from atomic comparison help? | Intent/contact labels may reveal hidden phase or encode the answer. The failed objective-plus-contact pair does not validate this hierarchy. |
| E. Oracle World.predict_all() reference | How does decision quality change with privileged candidate processing/effects? | Explicitly privileged reference only; never vision competence. More information is an informational upper bound, not a guaranteed performance upper bound for an imperfect model. |
| F. Jev-LIBERO-like intent → strategy → motor | Is the appropriate model judgment at a higher abstraction than atomic motion? | Strategy/controller changes confound interface effects; privileged strategy selection or scripted success must not be credited to Laya. |

For every option, distinguish effect sources `oracle_sim`, deterministic `geometry`,
`learned` and `unknown`/none. A learned source may inherit privileged targets/data;
its label alone is not proof of deployment availability. No trained effect predictor
is established by the current source schema. State Gap and Effect Gap remain separate.

## 9. STOP POINT

**Facts:** both tracks are integrated; the full suite and evidence integrity checks
pass; connectivity/replay/feedback are inspectable; atomic selection remains
unreliable; no useful manipulation reference or Laya drawer completion is established.

**Hypotheses:** insufficient candidate processing, goal/intent decomposition,
competitive ranking, predicate recognition and presentation interactions. Neither
missing physical state nor removal of preview is a complete demonstrated cause.

**Do not change yet:** prompts, CDS, candidate semantics/order, live gates/executor,
planner or the visual/oracle boundary. Do not run the binary predicate proposal,
restore preview into the visual path, or begin E0 on the strength of this merge.

**Decisions needed before another experiment:**

1. Choose the judgment level and the exact claim: atomic ranking, consequence
   verification or higher-level intent/strategy.
2. Specify what upstream code may compute/filter, what remains model judgment,
   and which evidence sources are allowed in each condition.
3. Define an independent usefulness/reference gate, matched controls and a bounded
   protocol that separates changed processing from changed information or controller.

Review those decisions against options A–F before authorizing another experiment.
