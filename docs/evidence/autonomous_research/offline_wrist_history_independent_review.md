# Prospective independent wrist-history review

**PASS before extraction/evaluation**, for clean producer freeze `adc7eb4e448615a271e58951f19a3dbe1c64e44a` in `laya-offline-wrist-history`. This is source/protocol approval for the authorized bounded offline comparison, not approval of an unseen result or a deployable contact detector.

The independently reviewed pipeline projects sensor-only rows from the canonical native-stage archive, seals that file, computes four pure sensor features, seals features, and only then writes separate contact labels. Source hash and record chains are verified. No simulator or model is constructed.

Features use the same first-BEFORE baseline for endpoint and maximum-across-25-AFTER changes, keeping force and torque separate in native moving local axes. The protocol explicitly records that including the endpoint makes the maximum no smaller without proving better discrimination. Actual sensor sample time remains unknown.

The evaluator uses AFTER contacts at strict >1 N. It preserves upstream arm, gripper, mixed, self and no-strong-robot/scene cohorts; self-contact takes precedence. Primary positives and negatives, the endpoint-missed subset, tie-aware AUROC, quantiles and overlap descriptions are fixed. No threshold or classifier is fit. The audit independently rereads source sensor/contact rows, checks sealing order and hashes, reconstructs cohorts and fixed subset membership, then recomputes features and scores.

I independently ran `tests/test_offline_wrist_history.py`: **6 passed**. Tests exercise baseline arithmetic, sensor schema isolation and timing, AUROC direction/ties/undefined cases, strict contact threshold and group separation, and the distinction between a larger temporal value and improved AUROC. No data associations were inspected during this prospective review.

| Reviewed file | SHA-256 |
| --- | --- |
| `docs/research/offline_wrist_history_protocol.md` | `2fe1d7d7ff98bd5dc82d180635a51b0e13dda93703a6d0518d3cf34ab76ac82d` |
| `embodied_runtime/experiments/offline_wrist_history.py` | `7cb241aa821fc707f508d48f850cdc0cbc7e7d5afb3324ffd5c5f2682c140501` |
| `tests/test_offline_wrist_history.py` | `43b7241481a105908b14353c44b52ba205228e3a17ae42467614c75ea1c188c6` |

Any resulting association remains descriptive for one dependent trajectory. It does not isolate contact force from inertia, gravity, changing axes or cache timing, and does not infer object identity, holding or generalization.
