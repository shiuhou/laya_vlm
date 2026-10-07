"""Source-bound positive semantic prompting; neither target proof nor control."""
from __future__ import annotations
import hashlib
import numpy as np
from ..contracts import require
from .semantic_output import parse_semantic_reply
from .surface_association import sensor_view_identity
from .rgbd_geometry import _roi

CONTRACT = "p1-positive-semantic-prompt/1"


def point_prompt(view, original_box, point_record, *, query, config):
    """Admit a complete same-source POINT in original BOX and its exact depth pixel.

    Continuous prompt is retained. Floor sampling must also be inside the ceil
    geometry ROI; this function never snaps, expands or infers semantic truth.
    """
    require(point_record['source_identity'] == sensor_view_identity(view)
            and point_record['query'] == query, 'POINT sensor/query mismatch', 'SOURCE_MISMATCH')
    require(point_record.get('evaluation_labels_used') is False, 'label-derived prompt forbidden', 'INFORMATION_BOUNDARY')
    h, w = view['depth_m'].shape
    result = dict(contract=CONTRACT, admitted=False, reason=None, point_xy=None,
                  sample_pixel_xy=None, geometry_roi_xyxy=None, sampled_depth_m=None,
                  calibrated_confidence=None, semantic_identity_verified=False, for_execution=False)
    if point_record['status'] != 'COMPLETE':
        return dict(result, reason=point_record.get('reason') or 'POINT_INFERENCE_FAILURE')
    require(hashlib.sha256(point_record['raw_output'].encode()).hexdigest() == point_record['response_sha256'],
            'POINT raw bytes mismatch', 'SOURCE_MISMATCH')
    audit = point_record['audit']
    if not audit.get('complete_generation') or not audit.get('terminal_eos_observed'):
        return dict(result, reason='INCOMPLETE_GENERATION')
    typed = parse_semantic_reply(point_record['raw_output'], w, h, mode='point', audit=audit)
    if not typed.admitted:
        return dict(result, reason=typed.reason)
    point = typed.selected[0]
    x, y = point.pixels
    u, v = point.sample_pixel_xy
    result.update(point_xy=list(point.pixels), sample_pixel_xy=[u, v])
    x0, y0, x1, y1 = map(float, original_box)
    roi = _roi(original_box, w, h)
    result['geometry_roi_xyxy'] = list(roi)
    if not (x0 <= x < x1 and y0 <= y < y1):
        return dict(result, reason='POINT_OUTSIDE_ORIGINAL_BOX')
    if not (roi[0] <= u < roi[2] and roi[1] <= v < roi[3]):
        return dict(result, reason='POINT_SAMPLE_OUTSIDE_GEOMETRY_ROI')
    d = float(view['depth_m'][v, u])
    if not np.isfinite(d) or not config.min_depth_m <= d <= config.max_depth_m:
        return dict(result, reason='POINT_DEPTH_UNAVAILABLE')
    return dict(result, admitted=True, sampled_depth_m=d)


def mask_point_admission(mask, prompt, ordinal):
    require(prompt['admitted'], 'mask diagnostic requires admitted native prompt')
    u, v = prompt['sample_pixel_xy']
    native = np.asarray(mask)
    require(native.dtype == bool and native.ndim == 2, 'native mask required')
    contains = bool(native[v, u])
    return dict(native_mask_ordinal=ordinal, sample_pixel_xy=[u, v],
                mask_contains_sample=contains, admitted=contains,
                reason=None if contains else 'POINT_MASK_CONTRADICTION',
                semantic_identity_verified=False, for_execution=False)
