"""Finite sensor-supported reference hypotheses, never reference selection.

BOX is only a search region. Planes, support boundaries and touching-support
graphs expose observed geometry, not cabinet identity, fixedness or a closed
drawer relation. Those remain UNKNOWN even for a single stationary plane.
No annotation, simulator-object or evaluator input is consumed here.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from time import perf_counter

import numpy as np

from .rgbd_geometry import GeometryConfig, project_depth
from .surface_association import inventory_surfaces


def _mask_evidence(mask):
    """Preserve every original support pixel without inventing a polygon."""
    spans = []
    for y in np.flatnonzero(mask.any(axis=1)):
        xs = np.flatnonzero(mask[y])
        for part in np.split(xs, np.flatnonzero(np.diff(xs) != 1) + 1):
            spans.append([int(y), int(part[0]), int(part[-1]) + 1])
    return dict(support_row_spans=spans, support_pixel_count=int(mask.sum()),
                support_mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest())


def _boundary(mask):
    interior = mask.copy()
    interior[0, :] = interior[-1, :] = False
    interior[:, 0] = interior[:, -1] = False
    interior[1:, :] &= mask[:-1, :]
    interior[:-1, :] &= mask[1:, :]
    interior[:, 1:] &= mask[:, :-1]
    interior[:, :-1] &= mask[:, 1:]
    return mask & ~interior


def enumerate_reference_candidates(view, roi_xyxy, config=None, seed=0):
    """Return all finite observed features in raster order as JSON-able evidence.

    Uses the existing inventory and gates unchanged. Boundaries are support
    boundaries: they may be depth/ROI/occlusion boundaries, not physical edges.
    Pixel adjacency is accepted as observed geometric adjacency only when the
    ORIGINAL 3-D samples meet the existing connectivity distance. It does not
    imply mechanical attachment. No infinite plane-intersection edges are used.
    Stage timings are measurements and deliberately excluded from source IDs.
    """
    config = config or GeometryConfig()
    started = perf_counter()
    inventory = inventory_surfaces(view, roi_xyxy, config=config, seed=seed)
    inventoried = perf_counter()
    cloud = project_depth(view["depth_m"], view["intrinsics_K"], view["T_base_camera"],
                          source_frame_id=inventory.source["frame_id"],
                          calibration_version=view["calibration_version"], config=config,
                          roi_xyxy=roi_xyxy)
    xyz = np.full((*cloud.valid_mask.shape, 3), np.nan)
    uv = cloud.pixels_uv
    xyz[uv[:, 1], uv[:, 0]] = cloud.points_base_m
    surfaces = inventory.surfaces
    neighbors = {s.surface_id: [] for s in surfaces}
    adjacency = []
    overlaps = []
    # Canonical surface ordering comes from inventory's original pixel supports.
    for i, left in enumerate(surfaces):
        for right in surfaces[i + 1:]:
            overlap = left.support_mask & right.support_mask
            if overlap.any():
                overlaps.append(dict(surface_ids=[left.surface_id, right.surface_id],
                                     status="AMBIGUOUS", reason="OVERLAPPING_PLANE_SUPPORTS",
                                     **_mask_evidence(overlap)))
            pairs = []
            # Four-neighbor pairs only; no nearest-plane search or extrapolation.
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                h, w = left.support_mask.shape
                ys, xs = slice(max(0, -dy), min(h, h - dy)), slice(max(0, -dx), min(w, w - dx))
                yt, xt = slice(max(0, dy), min(h, h + dy)), slice(max(0, dx), min(w, w + dx))
                hits = left.support_mask[ys, xs] & right.support_mask[yt, xt]
                va, ua = np.nonzero(hits)
                va, ua = va + ys.start, ua + xs.start
                vb, ub = va + dy, ua + dx
                distances = np.linalg.norm(xyz[va, ua] - xyz[vb, ub], axis=1)
                for y, x, yy, xx, distance in zip(va, ua, vb, ub, distances):
                    if np.isfinite(distance) and distance <= config.connectivity_distance_m:
                        pairs.append([int(x), int(y), int(xx), int(yy)])
            if not pairs:
                continue
            pairs.sort(key=lambda p: (p[1], p[0], p[3], p[2]))
            neighbors[left.surface_id].append(right.surface_id)
            neighbors[right.surface_id].append(left.surface_id)
            adjacency.append(dict(surface_ids=[left.surface_id, right.surface_id],
                                  observed_pixel_pairs_uv=pairs, pair_count=len(pairs),
                                  geometric_adjacency=True, mechanical_attachment="UNKNOWN",
                                  cabinet_structure_relation="UNKNOWN",
                                  connectivity_distance_m=config.connectivity_distance_m,
                                  provenance="sensor-derived"))
    candidates = []
    reasons = Counter()
    for surface in surfaces:
        common = dict(source_surface_id=surface.surface_id, source=inventory.source,
                      provenance="sensor-derived", semantic_identity="UNKNOWN",
                      fixedness="UNKNOWN", reference_status="REFERENCE_UNKNOWN",
                      closed_reference_relation="UNKNOWN", for_execution=False,
                      calibrated_confidence=None,
                      uncertainty_calibrated=config.uncertainty_calibrated,
                      neighboring_surface_ids=neighbors[surface.surface_id],
                      ambiguity_reasons=["OVERLAPPING_PLANE_SUPPORTS"] if any(
                          surface.surface_id in overlap["surface_ids"] for overlap in overlaps) else [])
        reject = ["CABINET_IDENTITY_UNESTABLISHED", "FIXEDNESS_UNESTABLISHED",
                  "CLOSED_REFERENCE_RELATION_UNESTABLISHED"]
        if not surface.plane_valid:
            reject.insert(0, "PLANE_GATE_REJECTED")
        candidates.append(dict(**common, candidate_id=surface.surface_id + "/face",
                               feature_kind="observed_face", geometry_status=(
                                   "PLANE_VALID" if surface.plane_valid else "PLANE_REJECTED"),
                               geometry=surface.evidence(), rejection_reasons=reject))
        reasons.update(reject)
        mask = _boundary(surface.support_mask)
        if mask.any():
            candidates.append(dict(**common, candidate_id=surface.surface_id + "/boundary",
                                   feature_kind="observed_support_boundary", geometry_status="OBSERVED_ONLY",
                                   geometry=_mask_evidence(mask), physical_edge_identity="UNKNOWN",
                                   finite_observed_support_only=True,
                                   rejection_reasons=[*reject, "PHYSICAL_EDGE_UNESTABLISHED"]))
            reasons.update([*reject, "PHYSICAL_EDGE_UNESTABLISHED"])
    if not surfaces:
        reasons["NO_OBSERVED_PLANE_SUPPORT"] += 1
    inventory_evidence = inventory.evidence()
    finished = perf_counter()
    return dict(schema_version="p1-reference-candidates-v1", source=inventory.source,
                inventory=inventory_evidence, candidates=candidates,
                observed_adjacency=adjacency, overlapping_supports=overlaps,
                reference_status="REFERENCE_UNKNOWN", selected_candidate_id=None,
                rejection_reason_counts=dict(sorted(reasons.items())),
                evaluation_labels_used=False, geometric_inventory_is_not_semantic_selection=True,
                stage_timings_s=dict(surface_inventory=inventoried - started,
                                     candidate_geometry=finished - inventoried,
                                     total=finished - started))
