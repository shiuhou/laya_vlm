# BOX role decomposition — prospective offline protocol

Freeze 51be5f6 and runs/p1/semantic-decomposition-20261007. No SAM or
LocateAnything inference. Reuse exact C2/C3 masks, logits, POINTs and admissions.
H/O denote human/original BOX. First letter is SAM prompt BOX, second geometry
search BOX: HH=C2 and OO=C3 are reused; HO and OH are the only new evaluations.

HO evaluates all75 C2 native masks with original BOX as geometry ROI. OH evaluates
all63 available C3 native masks with human BOX as geometry ROI. Four C3 rows have
no masks because the original prompt excluded its human point (init1/2/5/9).
They remain unavailable, never imputed or regenerated. This is an incomplete
factorial on all25 and a complete matched factorial on21 frames.

Source POINT admission belongs to the original SAM generation condition. Do not
reapply it to the new geometry domain: that would conflate prompt eligibility
with the domain intervention. Record point-in-new-domain as a diagnostic only.
All native masks, including point contradictions, receive raw geometry. Point
containment is preserved as the separate preexisting mask-admission diagnostic.
No mask winner, component fallback, query change, annotation change or threshold
change. No retry. Human inputs remain explicitly offline and nonexecutable.

Only roi_xyxy changes for each reused native mask. Same masked sensor depth,
full-native-mask depth denominator, K/T, EEF, timestamps, cfg, seed0, track/feature
identifiers and geometry gates. Do not intersect native masks with annotations.
Score only after geometry seal. Keep source prompt BOX and geometry BOX separate;
use geometry BOX for scoring-domain overlap while preserving source BOX evidence.

Primary outcome: at least one inside-human-region candidate in a point-admitted
native mask. Report all25 coverage with unavailable rows distinguished, and the
21 complete matched frames. Raw/admitted outside candidates, native ordinal
boundaries, reached/NOT_EVALUATED stages and candidate counts are secondary.
No inference from aggregate counts alone: inspect all frames and first divergence.

On the matched21, report conditional count effects:
SAM prompt at human domain = HH-OH; at original domain = HO-OO.
Geometry domain at human prompt = HH-HO; at original prompt = OH-OO.
Interaction = HH-HO-OH+OO. Report framewise gains/losses, not just net counts.
Balanced contributions split interaction equally:
P=((HH-OH)+(HO-OO))/2; D=((HH-HO)+(OH-OO))/2.
These are finite-sample descriptive causal interventions, not population estimates
or an identification of a unique physical mechanism. Paired exact discordance
statistics are descriptive on correlated exposed frames, not generalization proof.

Priority rule: if positive P>D choose BOX semantic grounding/prompt interface;
if positive D>P choose explicit separation of semantic BOX from geometry search
domain. If both positive report both and recommend only the larger. Positive tie
or neither positive is inconclusive: stop, do not add another condition. Strong
conditional reversals/interaction limit a single-main-effect interpretation and
must be disclosed. Upstream missing4 remain a separate prompt-admission blocker.

Stop after offline analysis, imagery, tests/lint, evidence and clean checkpoint.
No repair implementation, held-out tuning, tracker/temporal/P2/PUSH/Qwen/Laya or
fixed-reference work. Next implementation/validation requires a separate round.
