# Finite-gap objective changes STOP to LEFT by only 1.959 µm

The single frozen offline intervention **passes its literal decision-change
gate**: the original guarded STOP becomes MV_LEFT. Its nominal Euclidean
P-to-gap distance decreases by only **0.001958849 mm = 1.959 µm**, from
36.772006876 to 36.770048027 mm. This establishes a different arithmetic choice
under the registered strict-improvement rule. It does not establish a useful
physical improvement, reachable capture relation or permission to execute LEFT.
No dynamics, model, mask, threshold adjustment or further variant followed.

The [protocol](../../research/task2_finite_gap_control_protocol.md), source and
synthetic tests were frozen at `1fd6324fd35c5e42fe05923b4986ccf6f69e8a7c`.
Independent prospective PASS `1e69894` reproduced the source-only preflight and
passed 12 tests (producer's five new tests plus existing related tests). The one
worker run completed exit 0 and sealed its result. The scientific freeze remains
unchanged. The weak prospective prediction that STOP would remain was rejected
by this small strict improvement; no after-the-fact noise floor was added.

## Same packet, same exclusions, one changed distance

Use only terminal decision 28 of the existing endpoint-veto run: unchanged P,
all 1340 retained full-BOX points, own orientation/jaws and the original seven
nominal candidates. The saved mount and all five current robot proxy vertex
sets reproduced exactly. Every original exclusion, contained-point index and
P-distance effect is retained; no exclusion was recomputed or relaxed.

Current TCP-to-P distance is 45.729794657 mm. Calibrated finite-gap limits in
site axes are X [−39.498278,+39.498594] mm, Y [−8,+8] mm, and
Z [−11.6,+4.4] mm. Current P is `(0.633685,43.311821,14.659425)` mm in those
axes: it is between the X faces but outside the finite Y and Z extents.

| Candidate | Original TCP-to-P (mm) | P-to-gap (mm) | Gap change (mm) | Original veto / contained points |
|---|---:|---:|---:|---|
| FWD | 36.643004083 | 27.541023304 | −9.230983571 | Excluded /7 |
| BACK | 55.133642094 | 46.323352687 | +9.551345811 | Eligible /0 |
| LEFT | 46.672976989 | 36.770048027 | −0.001958849 | Eligible /0 |
| RIGHT | 46.947432920 | 36.773965773 | +0.001958897 | Eligible /0 |
| UP | 50.322274317 | 41.188555553 | +4.416548678 | Eligible /0 |
| DOWN | 43.012753299 | 34.754335989 | −2.017670887 | Excluded /1 |
| STOP | 45.729794657 | 36.772006876 | 0 | Terminal option /0 |

All seven endpoints leave P outside the finite gap. The two millimeter-scale
improving directions, FWD and DOWN, remain excluded. LEFT worsens the original
TCP-to-P objective but marginally improves the finite-region objective, so the
unchanged strict comparison admits it.

For LEFT, stored P in site axes becomes
`(−9.366315,43.309567,14.660162)` mm. Its dominant change is along the jaw axis,
where P was already inside the permitted interval. The nominal world LEFT translation changes the stored local point by
`(−9.999999719, −0.002254080, +0.000737270)` mm. The X term contributes
zero to distance because both X coordinates are inside the gap. Y and Z exceed
their upper faces, so their stored positive excesses determine the norm:

| Component from stored rows only | Current excess (mm) | LEFT excess (mm) | Contribution to distance change |
|---|---:|---:|---:|
| Y | 35.311820778 | 35.309566698 | −2.164561 µm |
| Z | 10.259425083 | 10.260162352 | +0.205712 µm |
| Sum | | | −1.958849 µm |

Each contribution is exactly
`(new_excess² − old_excess²) / (new_distance + old_distance)`; their sum is
the full Euclidean distance change. This algebra exposes sensitivity to the
small components of the saved own rotation along the axes where P is outside
the gap. It neither substitutes a perfectly aligned pose nor rounds axes or
reranks candidates. No additional pose or physical movement was computed.
No uncertainty bound was measured here that would establish this gain as
robust physical progress.

## What this changes, and what remains unknown

The finite jaw region changes the local ordering, so this boundary cannot be
summarized as “every eligible move worsens every possible grasp relation.” It
still offers no substantial improving direction under this particular metric
and veto. The original goal-cell exclusion concerns the original point-rule
stopping cell; this calculation neither extends that certificate to the larger
gap region nor finds a path to it.

The unchanged endpoint veto treats **all five solids identically**, including
the pads. It is an approach-only rule against observed-point containment, not a
grasp-validity contract and not a model of intended pad contact. Zero contained
points is not collision-free space or target capture. P remains a cached
median-ray proxy; surface ownership, identity, object extent, exact sample
staging, grasp qualification and holding remain unknown. No opposed-support
metric or semantic cleanup was introduced. The registered offline condition
ends here on its formal PASS; it does not automatically authorize dynamics.

The [complete stored result](task2_finite_gap_control_summary.json) retains the
current gap, all seven local coordinates/distances/booleans, original nested
guard rows, calibrated pad vertices, mount and explicit unknowns.

Raw output:
`/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task2-finite-gap-control-run-01`.
The sibling `.log` preserves the single execution.

| Artifact | SHA-256 |
|---|---|
| Source-only preflight | `ff1153929b7d3957a890d5605febe08571e42e930787d87bc7a818a951806c13` |
| Sanitized request | `49df0c6413a0161ed0900e5962d6844161089775c369e646baad6372f4f3e8a3` |
| Manifest | `12ca28ba50e45eef80519aff709dc73d8577d6c68c009626df7c9c114841fd33` |
| Result / portable copy | `dc569f9a564c59faa3686254f6fa726ad304fdcdce37b753a10108e05e821a13` |
| Sensor seal | `af9d221f996c1ad5cefab7cb5a92fcba5b71d258bcf58370d4273d05ebe64d6e` |

Independent closure: reviewer commit `1a0e7f3` verified all 11,793 source
records, exact sensor inputs/exclusions/P effects, all seven gap rows and the
report/portable copy. Independent quaternion, calibrated-pad and nearest-prism
arithmetic differed by at most `2.776e−17 m`; the Y/Z contributions also
reproduced. The formal PASS and tiny-gain interpretation passed without changes.
Review: `docs/evidence/autonomous_research/task2_finite_gap_control_independent_review.md`
in the `laya-render-measurement-semantics` worktree.
