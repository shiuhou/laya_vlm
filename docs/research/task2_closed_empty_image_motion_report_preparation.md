# Prepared post-event image-motion report

The stored-output function
`task2_closed_empty_image_motion_report.report(source, expected_seal_sha256)`
is ready for the later admitted extraction. It first verifies the reviewed
complete sensor seal, closed journal, all 24,600 ordered rows, frame bindings,
fixed reference, denominators and stored missing counts. It does not run LK,
project TCP, recompute motion/quantiles, read physical labels or join mechanical
evidence. There is no CLI and no report from the future source has been run.

The report creates one new `report/` directory with:

- `image-motion-curves.png`: all 25 captures in both cells, native status and
  A/B availability/missing curves, plus the four stored motion metrics with
  median, IQR and full range; scales are shared by column.
- `present-endpoint-rgb.png` and `away-endpoint-rgb.png`: full uncropped native
  RGB at local 0/8/16/24 above overlays of every defined forward position.
  Admitted positions and failed attempts use separate marks. Undefined and
  off-image positions retain explicit counts; they never define a cohort.
  The fixed initial pixel region is shown only as a spatial reference.
- A small `index.json` that links the existing sealed summary and tracks by
  hash, records endpoint display counts, and leaves actual-source RGB visual
  inspection pending. It does not duplicate the metric tables or trajectories.
- `report-start.json` and `artifacts.json` with exact source/report identities.

Only `rgb` is decoded from the eight bound source archives. The originals are
displayed without point marks in the upper panels; overlays do not alter source
images. All plotted points retain native index coordinates. Positions outside
the fixed full-image viewport remain in the arrays/rows and are counted even
though the canvas cannot show them. Report output never assigns ownership or
holding.

Five synthetic tests pass, including a complete sealed synthetic report, and
the synthetic curve and endpoint layouts were visually inspected. Real source
images and results remain unavailable; the root lane owns subsequent actual
image inspection, mechanical/qvel comparison and interpretation.
