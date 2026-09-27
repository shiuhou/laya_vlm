"""Offline current full-BOX support against saved POINT/own decision evidence.

No model, projection of a POINT, FK, rendering, physics, or action execution.
Source release and exact file bindings belong to the caller.
"""
from copy import deepcopy
from dataclasses import asdict

import numpy as np

from ..decision_interface import CanonicalDecisionInput, CanonicalDecisionState, CandidateEffectBundle
from ..runtime_core import Candidate, _sha256_json
from . import task2_box_support as box_source
from . import task2_endpoint_containment_veto as guard
from . import task2_observed_surface_sweep as geometry

ORDER = ('present-postevent', 'away-postevent')


def restore_view(data):
    """Restore the exact saved input, including existing numerical effects."""
    view = CanonicalDecisionInput(
        CanonicalDecisionState.from_dict(data['state']),
        tuple(Candidate(**row) for row in data['candidates']),
        CandidateEffectBundle(**data['effects']), tuple(data['history']),
        data['diagnostic_only'])
    if _sha256_json(asdict(view)) != _sha256_json(data):
        raise ValueError('Saved canonical input did not round-trip exactly')
    return view


def current_support(output, frame):
    """Established integer truncation, full half-open ROI, unchanged support()."""
    box, parsed = box_source.admitted_box(output['raw_output'], output['generation_audit'], 384, 384)
    expected = 'admitted_rgb_box' if box is not None else 'not_admitted'
    if output['status'] != expected or output['admitted_box'] != box or output['parsed'] != parsed:
        raise ValueError('Audited strict BOX admission changed')
    packet = {'status': 'unknown_nonadmitted_box', 'continuous_box_xyxy': box,
              'integer_full_ROI_xyxy': None, 'full_support': None,
              'valid_point_count': None, 'ROI_pixel_count': None,
              'depth_read': False, 'support_is_segmentation': False,
              'resolved_depth_ownership': None, 'holding': None,
              'box_median_goal_created': False, 'self_mask_applied': False}
    if box is None:
        return packet
    packet['depth_read'] = True
    depth, k, transform = (np.asarray(frame[name]) for name in
                          ('depth_m', 'intrinsics', 'camera_to_world'))
    if (depth.shape != (384, 384) or k.shape != (3, 3) or transform.shape != (4, 4)
            or not np.isfinite(k).all() or not np.isfinite(transform).all()
            or k[0, 0] <= 0 or k[1, 1] <= 0):
        packet['status'] = 'unknown_invalid_depth_or_calibration'
        return packet
    bounds = list(map(int, box))
    x1, y1, x2, y2 = bounds
    if not (0 <= x1 < x2 <= 384 and 0 <= y1 < y2 <= 384):
        packet['status'] = 'unknown_empty_or_invalid_integer_ROI'
        return packet
    packet.update(integer_full_ROI_xyxy=bounds, ROI_pixel_count=(x2-x1)*(y2-y1))
    full = geometry.support(depth, k, transform, bounds)
    packet['valid_point_count'] = len(full)
    if not full:
        packet['status'] = 'unknown_empty_valid_support'
        return packet
    if not np.isfinite([r['position_world_m'] for r in full]).all():
        packet['status'] = 'unknown_nonfinite_projected_support'
        return packet
    packet.update(status='admitted_full_rectangle_observed_support', full_support=full)
    return packet


def compare_case(fresh, output, frame):
    """Reuse the old arm; only current support/veto/eligible selection are new."""
    if (fresh['case_id'] not in ORDER or fresh['arm'] != 'fresh'
            or fresh['generation_mode'] != 'slow' or fresh['point_world_m'] is None
            or fresh['policy_status'] != 'evaluated_existing_rule'
            or list(fresh['all_seven_candidates']) != list(geometry.MOVES)):
        raise ValueError('Complete fixed fresh-slow POINT decision required')
    view = restore_view(fresh['canonical'])
    if (view.state.fields['target.position_m'].value != fresh['point_world_m']
            or view.rule_token() != fresh['unguarded_token']):
        raise ValueError('Saved POINT or rule changed')
    support = current_support(output, frame)
    shared = {'case_id': fresh['case_id'], 'point_world_m': deepcopy(fresh['point_world_m']),
        'canonical': deepcopy(fresh['canonical']), 'own': deepcopy(fresh['own']),
        'own_packet': deepcopy(fresh['selection']['own_packet']),
        'current_proxy_vertices_world_m': deepcopy(fresh['selection']['current_proxy_vertices_world_m']),
        'canonical_meta_is_unchanged_source_metadata': True,
        'unguarded_token': fresh['unguarded_token'], 'new_FK_calls': 0}
    old = {**deepcopy(shared), 'support_arm': 'old_full_BOX',
        'support_status': 'admitted_original_full_rectangle_observed_support',
        'support_count': 1340, 'guarded_token': fresh['guarded_token'],
        'all_seven_candidates': deepcopy(fresh['all_seven_candidates']),
        'eligible_canonical': deepcopy(fresh['eligible_canonical']),
        'terminal_reason': fresh['terminal_reason'], 'policy_status': 'reused_sealed_decision'}
    current = {**deepcopy(shared), 'support_arm': 'current_full_BOX',
        'support_status': support['status'], 'support_count': support['valid_point_count'],
        'guarded_token': None, 'eligible_canonical': None, 'terminal_reason': None,
        'policy_status': 'not_evaluated_unknown_support'}
    if support['full_support'] is None:
        current['all_seven_candidates'] = {token: {
            'nominal_delta_m': deepcopy(details['nominal_delta_m']),
            'nominal_tcp_to_P_m': details['nominal_tcp_to_P_m'],
            'excluded': None, 'contained_point_count': None, 'proxies': None,
            'reason': support['status']}
            for token, details in fresh['all_seven_candidates'].items()}
    else:
        exclusions = guard.endpoint_exclusions(support['full_support'], shared['current_proxy_vertices_world_m'])
        for token, details in exclusions.items():
            details['nominal_tcp_to_P_m'] = fresh['all_seven_candidates'][token]['nominal_tcp_to_P_m']
        token, eligible, reason = guard.select_remaining(view, exclusions)
        current.update(guarded_token=token, eligible_canonical=asdict(eligible),
            terminal_reason=reason, all_seven_candidates=exclusions,
            policy_status='evaluated_existing_rule')
    return {'support': support, 'records': [old, current]}
