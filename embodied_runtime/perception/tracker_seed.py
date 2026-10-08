"""Propose a supported RGB-D feature without weakening tracker admission.

The semantic point stays fixed. Rectangle proposal checks the same depth and
context rules that VisualTracker.initialize will check; it neither certifies
identity nor chooses a native mask. Geometry/tool thresholds are not involved.
"""
from __future__ import annotations

import numpy as np

from ..contracts import require
from .visual_tracker import TrackerConfig, VisualTracker


def depth_supported_rectangle(view, support_mask, point_xy, *, config=TrackerConfig()):
    mask = np.asarray(support_mask)
    depth = np.asarray(view['depth_m'])
    point = np.asarray(point_xy, dtype=float)
    require(mask.dtype == bool and mask.shape == depth.shape and depth.ndim == 2,
            'same-frame bool support and metric depth required')
    require(point.shape == (2,) and np.isfinite(point).all(), 'finite semantic point required')
    h, w = mask.shape
    receipt = dict(method='depth-supported-rectangle/1', point_xy=point.tolist(),
                   support_rectangles=0, depth_admitted_rectangles=0,
                   max_depth_spread_m=config.max_depth_spread_m,
                   min_depth_support_ratio=config.min_depth_support_ratio,
                   semantic_point_moved=False, point_quantization='floor-to-existing-pixel-center', reason=None)
    if not (0 <= point[0] < w and 0 <= point[1] < h):
        return None, dict(receipt, reason='POINT_OUT_OF_VIEW')
    x, y = np.floor(point).astype(int)
    if not mask[y, x]:
        return None, dict(receipt, reason='POINT_OUTSIDE_SUPPORT')
    center = np.array([x + .5, y + .5])
    widths = np.arange(4, min(w, int(2 * min(center[0], w-center[0]))) + 1)
    heights = np.arange(4, min(h, int(2 * min(center[1], h-center[1]))) + 1)
    # Same width-then-height enumeration/tie order as tracker_seed_rectangle.
    ww, hh = np.meshgrid(widths, heights, indexing='ij')
    sizes = np.column_stack((ww.ravel(), hh.ravel()))
    lo = np.floor(center - sizes * config.template_context_scale / 2).astype(int)
    hi = np.ceil(center + sizes * config.template_context_scale / 2).astype(int)
    inside = (lo >= 0).all(1) & (hi[:, 0] <= w) & (hi[:, 1] <= h)
    sizes, lo, hi = sizes[inside], lo[inside], hi[inside]
    integral = np.pad(np.cumsum(np.cumsum(~mask, axis=0), axis=1), ((1, 0), (1, 0)))
    bad = integral[hi[:, 1], hi[:, 0]] - integral[lo[:, 1], hi[:, 0]] - integral[hi[:, 1], lo[:, 0]] + integral[lo[:, 1], lo[:, 0]]
    sizes = sizes[bad == 0]
    receipt['support_rectangles'] = len(sizes)
    if not len(sizes):
        return None, dict(receipt, reason='NO_SUPPORTED_RECTANGLE')
    # Reuse the actual tracker sampling/gates, avoiding a subtly different
    # depth quantile implementation in the initializer proposal.
    probe = VisualTracker('seed-proposal', config=config)
    centers = np.repeat(center[None, :], len(sizes), axis=0)
    good, _, _, ratios, spreads = probe._geometry(
        depth, centers, sizes, np.asarray(view['intrinsics_K']), np.asarray(view['T_base_camera']))
    receipt['depth_admitted_rectangles'] = int(good.sum())
    if not good.any():
        return None, dict(receipt, reason='NO_DEPTH_SUPPORTED_RECTANGLE')
    # Stable maximum observed support area, not model IoU or downstream success.
    order = np.argsort(-np.prod(sizes, axis=1), kind='stable')
    for i in order[good[order]]:
        _, in_view = probe._sample(np.asarray(view['rgb']), centers[i:i+1], sizes[i:i+1],
                                  side=config.template_side, context=config.template_context_scale)
        if in_view[0]:
            rectangle = np.r_[center-sizes[i]/2, center+sizes[i]/2].tolist()
            return rectangle, dict(receipt, rectangle_xyxy=rectangle,
                                   depth_support_ratio=float(ratios[i]), depth_spread_m=float(spreads[i]))
    return None, dict(receipt, reason='NO_IN_VIEW_CONTEXT')
