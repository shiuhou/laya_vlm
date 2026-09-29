# Image motion preserves a local contrast; identity and holding remain unresolved

The fixed full-population RGB displacement retains the close/open-hold motion
contrast without using sampled scene depth. Final median image displacement is
3.870711 px whole-close and 4.129355 px neck-close, versus 0.003165 px and
0.002232 px in the respective open-hold cells. Adding projected saved own-TCP
motion gives another descriptive view of this contrast. Neither representation
establishes that a track belongs to the bottle or that the bottle is held.

The one reviewed execution at freeze
`6e379ce604e9cb7b026ff7b3cc910d1bcdd7534a` completed **1,968 trajectories /
91,512 rows**, with zero retries. All 492 native tracks remain admitted at each
capture, and all 492 A/B metrics are available at all 17 preclose-or-later
captures per cell. Earlier reference metrics remain null with 492 missing
values. The original four conditions, seeds, ordering, native fields and source
times are retained. No native tracking, model, physics, FK, rendering, masks,
depth filter or holding threshold was added.

The [fixed protocol](../../research/task2_point_anchor_image_motion_comparison_proposal.md)
defines two distinct input contracts. **A** uses only saved native RGB-coordinate
displacement from preclose. **B** subtracts the displacement of saved own TCP
projected with saved camera K/T, so B adds proprioception and calibration and is
not RGB-only. Neither feature branch reads measured scene depth. Five synthetic
tests and independent prospective review passed for the exact whitelist,
K/T-only NPZ access, coordinate convention, missing-value separation, off-image
TCP retention and complete population. The new features were sealed before the
report read any old 3D result; the post-seal join is recorded separately.

The [independent output review](task2_image_motion_independent_review.md) passed
all 91,512 rows, the A/B/reference/null arithmetic and source identities, and
the portable report's 186 capture summaries, 186 fixed-seed joined rows and 16
checkpoints. Both report figures were independently inspected. Its extraction
and report audit receipts are recorded alongside that review.

## Complete distributions

All values below are pixels from the sole preclose reference: whole capture 30
and neck capture 29. Positive v is **image-down**, not world-up. Brackets are
q25–q75 of 492 dependent dense samples, not confidence intervals or independent
trials. The [portable comparison](task2_point_anchor_image_motion_summary.json)
preserves full precision, all 186 capture summaries, minima/maxima, missing
counts, projected TCP motion, four checkpoints and the existing 3D summaries.

| Cell | A: Δv median | A: displacement norm median [q25, q75] | B: relative Δv median | B: relative norm median [q25, q75] |
| --- | ---: | ---: | ---: | ---: |
| whole-close | −3.492569 | 3.870711 [2.608202, 4.304614] | 0.133115 | 2.067484 [1.869074, 2.457856] |
| whole-open_hold | −0.001007 | 0.003165 [0.001086, 0.006791] | 3.637229 | 3.648610 [3.643258, 3.650744] |
| neck-close | −3.479240 | 4.129355 [2.917722, 4.427200] | 0.184392 | 2.486473 [2.272708, 2.720197] |
| neck-open_hold | 0 | 0.002232 [0.000892, 0.004488] | 3.675788 | 3.689048 [3.685380, 3.690762] |

The full final ranges overlap and remain in every summary:

| Cell | A norm minimum–maximum (px) | B norm minimum–maximum (px) |
| --- | ---: | ---: |
| whole-close | 0.101480–8.773667 | 1.243589–5.265849 |
| whole-open_hold | 0.000022–3.241999 | 0.423838–3.674324 |
| neck-close | 0.333567–8.201120 | 1.616919–4.999512 |
| neck-open_hold | 0.000015–2.681402 | 1.008798–3.699809 |

The [complete curves](task2_point_anchor_image_motion_curves.png) show median
lines, blue IQR bands and gray full-range bands with shared scales per column.
All capture counts are shown; A/B reference availability before preclose is
zero by definition. Dotted lines mark preclose and dashed lines the end of
close/hold. These figures were inspected in full.

Motion during closing is retained: after close/hold, A norm medians are
`0.02139468869210172` px whole-close and `0.5530587278303845` px neck-close,
versus `0.0012922675509560847` and `0.00078214531956203` px in their open-hold
controls. Final values therefore include the close/hold interval rather than
isolating the lift. The projected own-TCP preclose-to-final displacements are:

| Cell | Saved own-TCP image displacement [u,v] (px) |
| --- | --- |
| whole-close | `[0.2852574970887929, -3.6256838085759853]` |
| whole-open_hold | `[0.2880755518008584, -3.638236082911334]` |
| neck-close | `[0.3098961438099366, -3.6636320644372233]` |
| neck-open_hold | `[0.3124934077803516, -3.6757879448921926]` |

The close-cell median image-down residuals are near zero, but the relative
vector norms are nonzero. Projection perspective and differing point/TCP
locations mean B is not a calibrated rigid-attachment error; no distance in
pixels is converted to a physical slip distance.

## Comparison with the fixed depth-tail examples

The four previously selected post-outcome 3D-extreme seeds are retained as
exploratory references, with no new selection. Their
[paired representation traces](task2_point_anchor_image_motion_extremes.png)
and the earlier [RGB/depth contexts](task2_point_anchor_extreme_track_findings.md)
show gradual native image motion alongside abrupt near/far sampled-surface
changes in the old 3D representation. These panels have distinct units;
their numeric amplitudes are not interchangeable error measures.

| Cell / fixed seed | Final A norm (px) | Final B norm (px) | Existing final 3D point norm (m) |
| --- | ---: | ---: | ---: |
| whole-close / 3 | 4.542173826940458 | 1.2435887671579429 | 0.23911424759242372 |
| whole-open_hold / 11 | 2.533718790927088 | 1.120441699082584 | 0.21025119213709395 |
| neck-close / 3 | 4.624474767498644 | 1.7190965513944152 | 0.24191386788810873 |
| neck-open_hold / 17 | 2.3743591460587394 | 1.318092823477114 | 0.2300962850736131 |

The 2D summaries provide the observed local close/open median contrast without
requiring scene-depth lifting. Thus the alternative that sampled depth is
necessary for **this particular median motion contrast** is not supported by
these traces. This does not establish that depth is unnecessary for other
directions of motion, metric localization, geometry or manipulation.

The image representation avoids inheriting the discontinuous scene-depth jump,
but it does not repair semantic correspondence. The fixed open-hold examples
still move 2.37–2.53 px and have B residuals of only 1.12–1.32 px. A small
projected-TCP residual therefore occurs in an open-hold condition too. The
closed extrema include the visible finger/background switch documented earlier.
Smoother 2D traces can describe the wrong local surface, and native successful
status cannot resolve that ownership. No sample is removed or reclassified.

The experiment supports **observing local motion** in these saved images.
Holding additionally requires intended-object identity and evidence that the
interaction retains that object under the task's conditions. The existing
close/open commands are not validated held/not-held labels. Perspective,
camera-ray motion, occlusion, external support, slipping and source read-time
uncertainty remain limits. Neither representation is selected as a holding
classifier or used to rank grasp anchors.

## Next experiment proposed

The next useful falsifier is the separately prepared **matched closed-empty
condition at the fixed neck anchor**: two fresh matched approaches, a logged
sham versus a fixed target-relocation scene event, then the same
GRASP/GRASP/MV_UP command sequence. This holds jaw-command history fixed while
testing whether local visual/own-motion cues also occur when the target is
absent from the closing region. The physical lane owns placement feasibility,
event/cache/replay semantics and independent mechanical source qualification;
this report authorizes no scene mutation or dynamics.

The post-event measurement protocol remains to be designed and reviewed before
any future source is analyzed. It needs a prospective point definition based on
available sensor evidence after the event, applied identically to both arms,
and a declared reference and capture schedule. The original 492 seeds describe
the original bottle/background region and cannot automatically define an
empty-scene target measurement. Tracking them through the relocation could
provide a separate continuity stress diagnostic, but would not establish target
identity or the post-event relation being tested. Any eventual comparison must
retain its complete declared population and failures/nulls, distinguish empty
gripper self-motion from target motion, and use separately established
mechanical evidence without assuming the target-present arm is retained. No
future point policy, feature extraction, scene mutation or dynamics is approved
by this report.

## Artifact identity

Raw output is
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-point-anchor-image-motion-run-01`.

| Artifact | SHA-256 |
| --- | --- |
| New sensor seal | `6524ae13db399bed62e5c7fa66ec7bff65e88bf448b85778298ef5ecdb69d777` |
| Closed journal | `1f32a218e402d0a7e0ebca0db5df1a0e6aa50235fe2d7717bf65dbaeb8f6bd63` |
| Extraction artifacts | `adf01c181da6f1d6416f58f907cb98240203a20dc5d587eb198b3a9a66a6cfec` |
| Post-seal report-start receipt | `1ba455466536664875f818fc85bd995a8c08e1d26241a147a3bfee9b33bac7af` |
| Portable comparison / tracked summary | `2a9d4f1ce5f8630007cb4c4381ec8bc8ce6eea927f7173e0cb616a9698e1ead7` |
| Full image-motion curves / tracked figure | `307da7d570565611a8ef51747332eaa90ad7107fe1512f2feee236a1396eaa57` |
| Fixed exploratory traces / tracked figure | `86c20a63929a784830f1ac7093d9ac1ae9ac25f5e04ba4cb91a361c79a38830f` |
| Report artifacts | `73b8872f4498ca3f878032c0a301a105e93ff25183b584e7484229e4d1d55ee2` |
