from itertools import product

import numpy as np
import pytest

from embodied_runtime.experiments import task2_box_point_boundary as baseline
from embodied_runtime.experiments import task2_endpoint_containment_veto as guard


def view(point=(.02, .02, 0)):
    return baseline.decision({'position_world_m': list(point), 'definition': 'test_fixed_point'},
                             {'tcp_pos_world_m': [0, 0, 0], 'gripper_width_m': .08, 'gripper_command': 'OPEN'},
                             0, 0, 0)


def exclusions(blocked=()):
    return {token: {'excluded': token in blocked} for token in guard.geometry.MOVES}


def box(center, radius=.001):
    return np.asarray(list(product((-radius, radius), repeat=3)))+np.asarray(center)


def proxies(first):
    return {name: first if i == 0 else box([10*i, 0, 0]) for i, name in enumerate(guard.geometry.GEOMS)}


def test_exact_existing_containment_tolerance_no_added_margin_and_stop_is_terminal():
    # FWD endpoint touches the first point. The other is outside the existing 1e-12 tolerance.
    support = [{'position_world_m': [.011, 0, 0]}, {'position_world_m': [.011+2e-12, 0, 0]}]
    result = guard.endpoint_exclusions(support, proxies(box([0, 0, 0])))
    assert list(result) == list(guard.geometry.MOVES)
    assert result['MV_FWD']['excluded']
    assert result['MV_FWD']['contained_point_count'] == 1
    assert result['MV_FWD']['proxies'][guard.geometry.GEOMS[0]]['full_support_indices'] == [0]
    assert not any(result[token]['excluded'] for token in result if token != 'MV_FWD')
    overlap = guard.endpoint_exclusions([{'position_world_m': [0, 0, 0]}], proxies(box([0, 0, 0])))
    assert overlap['STOP']['contained_point_count'] == 1
    assert not overlap['STOP']['excluded']
    assert overlap['STOP']['reason'] == 'terminal_option_no_primitive'


def test_proxies_remain_separate_and_containment_is_endpoint_only():
    shapes = {name: box([10+i, 0, 0]) for i, name in enumerate(guard.geometry.GEOMS)}
    shapes[guard.geometry.GEOMS[0]] = box([-.01, 0, 0])
    shapes[guard.geometry.GEOMS[1]] = box([.01, 0, 0])
    result = guard.endpoint_exclusions([{'position_world_m': [0, 0, 0]}], shapes)
    assert result['STOP']['contained_point_count'] == 0  # Do not convex-fill the gap.
    result = guard.endpoint_exclusions([{'position_world_m': [.005, 0, 0]}], proxies(box([0, 0, 0])))
    assert not result['MV_FWD']['excluded']  # Along sweep, outside nominal endpoint.
    with pytest.raises(ValueError, match='five'):
        guard.endpoint_exclusions([{'position_world_m': [0, 0, 0]}], dict(list(shapes.items())[:1]))


def test_subset_preserves_original_rule_ties_strict_improvement_and_zero_pool():
    original = view()
    assert original.rule_token() == 'MV_FWD'
    token, eligible, _ = guard.select_remaining(original, exclusions())
    assert token == original.rule_token() and eligible == original
    token, eligible, _ = guard.select_remaining(original, exclusions(('MV_FWD',)))
    assert token == 'MV_LEFT'
    assert [c.token for c in eligible.candidates] == [c.token for c in original.candidates if c.token != 'MV_FWD']
    assert eligible.state is original.state and eligible.history == original.history
    assert len(original.candidates) == 7
    token, eligible, _ = guard.select_remaining(original, exclusions(tuple(baseline.MOVE)))
    assert token == 'STOP' and [c.token for c in eligible.candidates] == ['STOP']
    assert guard.select_remaining(view((.004, .004, .004)), exclusions())[0] == 'STOP'
    token, eligible, reason = guard.select_remaining(original, exclusions(tuple(guard.geometry.MOVES)))
    assert token == 'STOP' and not eligible.candidates and reason == 'endpoint_veto_zero_remaining_pool'
    with pytest.raises(ValueError, match='seven'):
        guard.select_remaining(original, {'MV_FWD': {'excluded': False}})


def test_selector_uses_only_returned_own_fields_and_records_actual_first_divergence(monkeypatch):
    supplied = []
    def place(calibration, own):
        supplied.append(own)
        return proxies(box([0, 0, 0])), {'body_to_site': 'test'}
    monkeypatch.setattr(guard.geometry, 'place', place)
    selector = guard.EndpointSelector({'calibration': {}, 'full_support': [{'position_world_m': [.01, 0, 0]}]})
    own = {'robot0_eef_pos': [0, 0, 0], 'robot0_eef_quat': [0, 0, 0, 1], 'robot0_gripper_qpos': [.04, -.04],
           'bottle_position': [99, 99, 99], 'contacts': [1], 'success': True, 'robot0_gripper_qvel': [0, 0]}
    token, evidence, _ = selector(view(), own)
    assert token == 'MV_LEFT'
    assert set(supplied[0]) == guard.geometry.OWN_KEYS
    assert evidence['unguarded_rule_token_at_same_state'] == 'MV_FWD'
    assert evidence['first_policy_divergence'] == {'step': 0, 'unguarded_token': 'MV_FWD', 'guarded_token': 'MV_LEFT'}
    assert len(evidence['all_seven_candidates']) == 7
    assert evidence['STOP_semantics'] == 'termination_before_execute'
