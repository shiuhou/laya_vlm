# Visual verification and coarse-approach decision controls

Neither tested model interface yet earns integration into a manipulation policy.
All experiments below are offline development diagnostics. The simulator executor,
historical references and generic runtime remain unchanged.

## Full-image verification did not reject wrong targets

One prospectively chosen Qwen2.5-VL-3B-Instruct checkpoint, pinned revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`, received full 384×384 RGB with a fixed
hollow crosshair at each eligible LocateAnything POINT proposal. Native processing
resized the full image to 392×392; each input contained 304 tokens, including 196
image tokens. Four mixed POINT outputs were excluded by the predeclared structural
rule, leaving 14 proposals and two exact repeats.

Coarse labels were fixed before inference. Two reviewers agreed on 12 intended
handle proposals and two lower-handle proposals. Reviewers had seen earlier masks,
so this is not a blinded annotation study. Three precise mask misses still denote
the intended handle; exact surface membership is a separate geometric metric.

Every answer was `target_handle`. Correct-target retention is 12/12, wrong-handle
rejection 0/2 per repeat. Accuracy 12/14 equals an always-accept classifier and is
not useful verification. All actual forward token/image fingerprints, decoded
tokens, greedy vocabulary logits and EOS checks pass. Repeated logits are bitwise
identical. No fallback or response extraction was used.

The first CPU preflight failed because the text-model Python environment lacked
Torchvision. The failure is preserved. The existing vision environment passed the
next preflight and ran the experiment; no dependency installation or model/prompt
change was made to repair that environment failure.

## Image-only marker control also fails the requested classification

The next registered intervention used frames 0, 8, 11 and 17. It changed only marker
location: original proposal versus fixed image coordinate (192,288), visibly clear
tabletop in all four frames. The same marker was drawn from raw RGB, leaving no
old marker behind. Task wording, model, processor, label set and generation remained
unchanged. Eight inputs, two repeats, 16 calls.

All 16 answers were again `target_handle`; tabletop classification was 0/8.
Original-input logits reproduce the primary run exactly. Every marker intervention
changes the consumed image and the output logits, with maximum logit differences
0.625–1.141 across source frames, but none changes the categorical answer. Thus
the result is failed marker binding in this interface, not evidence that images
were ignored or that VLMs generally cannot reason visually. No planner, verifier
or further marker-prompt tuning is justified by these results.

## Explicit approach instructions do not establish reliable motor selection

Six sensor-only development states retain their natural ten-option pools,
proprioceptive history and uncertainty fields. Laya receives the existing explicit
nominal-approach instruction plus deterministic 10 mm geometric effects. Contact,
holding and effects of nontranslations remain unknown. Inputs consume 800–934
tokens; all twelve calls and exact repeats pass raw audits. Laya selects GRASP
throughout, contrary to the instruction to preserve the gripper.

The global drawer task remains in state alongside the local approach instruction.
Priority/framing and numerical reasoning are therefore not uniquely isolated.
Unknown GRASP effects are not assigned fictitious zero physical motion or regret.

One final candidate-family control removes only GRASP and the two rotations,
retaining six translations and STOP. All remaining wording, state, history and
effect values stay unchanged. This is explicit objective-family admission, not
the natural gate condition. Twelve calls reproduce exactly; independent raw,
token, checkpoint, effect-arithmetic and intervention audits pass.

| Init/step | Laya, seven options | Sensor nominal gain, mm | Existing rule | Rule gain, mm |
|---|---|---:|---|---:|
| 0/0 | BACK | −7.439 | FWD | 7.214 |
| 0/20 | FWD | 6.306 | FWD | 6.306 |
| 0/24 | FWD | 5.455 | DOWN | 6.727 |
| 0/29 | FWD | 5.561 | DOWN | 5.851 |
| 1/0 | FWD | 6.325 | FWD | 6.325 |
| 2/0 | BACK | −6.795 | FWD | 6.537 |

The restriction eliminates gripper changes, but two choices still move away under
the supplied geometry. Only two of six maximize the supplied nominal gain. The
oracle geometric optimum is FWD in all six states: at steps 24/29, the nonmaximal
sensor choices actually improve oracle nominal distance more than the sensor rule.
This exposes perception bias and prevents treating rule agreement as task truth.
None of these geometric quantities is a measured physical execution outcome.

## An honest physical diagnostic requires a different admission contract

The current fusion path replaces absent covariance with a fallback and marks it
unverified; the default candidate gate then permits only STOP. Supplying an
uncalibrated covariance admits translations even when semantic validity is false.
Small conditional projection noise does not cover categorical wrong-handle errors.
The existing projection also maps absent positive semantic evidence to confidence
zero, which is distinct from unknown correctness.

The next diagnostic therefore explicitly bypasses probabilistic fusion. Fresh,
complete single-POINT output and finite depth admit a reported surface point for
bounded coarse approach, without covariance, semantic confidence, velocity, holding
or contact assertions. The existing geometric rule and native atomic executor are
reused. A separately reset active-hold condition measures drift. Oracle all-robot
contact observation may abort at the next completed primitive, but cannot correct
the point or rank actions. This is experimental supervision, not perceptual safety.

This can test physical progress toward a reported point and independently measured
handle progress. It cannot establish correct grasping, manipulation, real-time
robustness, a generic fused runtime, or the necessity of high-level planning.

## Evidence

Raw local directories under `runs/autonomous-research/`:

- `visual-target-verification-{inputs,labels,run}-01/`
- `visual-target-verification-preflight-01/` (environment failure), `...-02/` (pass)
- `visual-marker-control-{inputs,labels,preflight,run}-01/`
- `approach-selector-{preflight,run}-01/`
- `approach-family-{preflight,run}-01/`

Each completed primary experiment includes independent audit code, raw hashes and
interpretation. Tracked summaries accompany this document. Native executor/runtime
source remains unchanged. Frozen revision `14a05fc`: 619 tests passed, 6 skipped.
