# Image-motion population and post-seal report: independent review

PASS for extraction freeze `6e379ce604e9cb7b026ff7b3cc910d1bcdd7534a`
and the exact raw report artifacts bound below. This closes the existing four-cell
comparison. It does not freeze or authorize a future relocated-object feature run.

The [numerical audit](task2_image_motion_independent_audit.json) checked all
1,968 tracks / 91,512 rows against their whitelisted originals, every A/B vector,
status, null and metric, and all 186 fixed-denominator capture summaries. Counts,
missing counts, median, quartiles and extrema agree for every metric. A and B each
have 33,456 available rows; the 58,056 rows before preclose have null reference
metrics. All 492 native tracks remain admitted at every capture. The whole and
neck references remain captures 30 and 29, respectively. Seal, source, artifact,
protocol and review hashes, clean source freeze, runtime and terminal journal
records agree; no retry occurred.

The reviewer also independently checked 186 saved own-TCP projections using
scalar K/T arithmetic and the integer-center half-pixel convention, agreeing
within 1e-10 px. Vector subtractions agree exactly and metric norms within 1e-12
px. This was arithmetic verification of saved projections, not a new production
feature extraction. A uses native RGB-coordinate displacement. B subtracts
projected own-TCP displacement and therefore adds proprioception and calibration;
it is not RGB-only. Neither uses measured scene depth. Finite off-image own-TCP
coordinates remain admitted; missing own projection nulls B without nulling A.

The [report audit](task2_image_motion_report_independent_audit.json) independently
compared all 186 new curves and their timing/phase/projection metadata, all 186
stored 3D summaries, all 186 fixed exploratory history joins, and all 16
checkpoints to the sealed sources. All copies are exact, including all nine native
fields at each selected join. The old seeds remain 3/11/3/17 without reselection.
All report artifact hashes agree. Source review of report generator SHA-256
`455d58898bbe582bd3a43ba4f9b5a91897e37230f14bb1b376ab0f2c0f2e7f88`
confirms that it validates the complete new seal and every sealed output, then
writes the start receipt, before reading the old 3D summary. The receipt binds
the completed new seal and closed journal. No old 3D fields enter the new feature
files; the later join is explicitly recorded and does not recompute features.

Both actual figures were inspected at original resolution. The complete plot
shows all capture counts and post-preclose median, IQR and full ranges, with shared
scales per metric column and explicit image-down/pixel labels. The exploratory
plot preserves separate pixel and millimetre axes and compares temporal behavior
without equating amplitudes. The whole-open full-history largest jump is before
preclose; its plotted suffix correctly shows the separate later jump.

Final A norm medians are 3.870711 / 0.003165 / 4.129355 / 0.002232 px in fixed
cell order. B's close signed vertical medians are near zero while its vector norm
medians remain 2.067484 / 2.486473 px. Full close/open ranges overlap. The fixed
open examples also have small B residuals (1.120442 / 1.318093 px), so a small
residual is not evidence of holding. Smoother RGB trajectories avoid inheriting
the scene-depth discontinuity but do not authenticate target ownership, repair
occlusion or establish rigid attachment. Dense seeds are dependent samples, and
the four extrema were selected after observing the 3D outcomes. No holding
threshold, accuracy ranking, anchor ranking or general depth-necessity claim is
supported.

Bound SHA-256 identities:

- New sensor seal: `6524ae13db399bed62e5c7fa66ec7bff65e88bf448b85778298ef5ecdb69d777`.
- Closed journal: `1f32a218e402d0a7e0ebca0db5df1a0e6aa50235fe2d7717bf65dbaeb8f6bd63`.
- Extraction artifacts: `adf01c181da6f1d6416f58f907cb98240203a20dc5d587eb198b3a9a66a6cfec`.
- New summary: `4ea4021ead168b0d01dbdd5a35aa4c4dcabd924c635956a207d6dc3a3b083401`.
- Report-start receipt: `1ba455466536664875f818fc85bd995a8c08e1d26241a147a3bfee9b33bac7af`.
- Portable comparison: `2a9d4f1ce5f8630007cb4c4381ec8bc8ce6eea927f7173e0cb616a9698e1ead7`.
- Complete curves: `307da7d570565611a8ef51747332eaa90ad7107fe1512f2feee236a1396eaa57`.
- Fixed exploratory traces: `86c20a63929a784830f1ac7093d9ac1ae9ac25f5e04ba4cb91a361c79a38830f`.
- Report artifacts: `73b8872f4498ca3f878032c0a301a105e93ff25183b584e7484229e4d1d55ee2`.

No LK, FK, physics, simulator rendering or model calls were made in this review.
The already closed old 3D estimator audit remains its bulk arithmetic proof.
