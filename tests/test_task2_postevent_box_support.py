from dataclasses import asdict

import numpy as np
import pytest

from embodied_runtime.experiments import task2_postevent_box_support as probe
from embodied_runtime.experiments import task2_postevent_point_decision as point


def box_output(raw='<box><0><0><10><10></box>'):
    audit = {'complete_generation': True, 'actual_generated_token_count': 6}
    box, parsed = probe.box_source.admitted_box(raw, audit, 384, 384)
    return {'raw_output': raw, 'generation_audit': audit, 'parsed': parsed,
            'status': 'admitted_rgb_box' if box is not None else 'not_admitted', 'admitted_box': box}


def fresh_row():
    own = {'robot0_eef_pos': [0., 0., 0.], 'robot0_eef_quat': [0., 0., 0., 1.],
           'robot0_gripper_qpos': [.04, -.04], 'robot0_gripper_qvel': [0., 0.]}
    view = point.decision([1., 0., 0.], own, 12.1, 0, 'fresh', {})
    scores = {token: {'nominal_delta_m': delta, 'nominal_tcp_to_P_m': float(np.linalg.norm(np.array([1., 0., 0.])-delta)),
                     'excluded': False, 'contained_point_count': 0, 'proxies': {}}
              for token, delta in probe.geometry.MOVES.items()}
    vertices = [[2.+x, 2.+y, 2.+z] for x in (0., .1) for y in (0., .1) for z in (0., .1)]
    return {'case_id': 'present-postevent', 'arm': 'fresh', 'generation_mode': 'slow',
            'point_world_m': [1., 0., 0.], 'policy_status': 'evaluated_existing_rule',
            'all_seven_candidates': scores, 'canonical': asdict(view), 'own': own,
            'selection': {'own_packet': probe.geometry.own_packet(own),
                          'current_proxy_vertices_world_m': {k: vertices for k in probe.geometry.GEOMS}},
            'unguarded_token': 'MV_FWD', 'guarded_token': 'MV_FWD',
            'eligible_canonical': asdict(view), 'terminal_reason': 'rule_no_strict_nominal_improvement'}


@pytest.mark.parametrize('raw,depth', [('<box><1><2></box><box>', None),
                                    ('<box><0><0><10><10></box>', np.full((384, 384), np.nan))])
def test_unknown_support_cannot_turn_into_clearance_or_stop(raw, depth):
    frame = None if depth is None else {'depth_m': depth, 'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    result = probe.compare_case(fresh_row(), box_output(raw), frame)
    current = result['records'][1]
    assert current['guarded_token'] is None and current['eligible_canonical'] is None
    assert len(current['all_seven_candidates']) == 7
    assert all(v['excluded'] is None and v['contained_point_count'] is None for v in current['all_seven_candidates'].values())
    assert result['support']['full_support'] is None
    assert result['support']['depth_read'] is (depth is not None)


def test_full_rectangle_keeps_valid_edges_and_exact_saved_goal_scores(monkeypatch):
    depth = np.full((384, 384), 1.)
    depth[0, 0], depth[2, 2] = .01, 5.
    depth[1, 1] = np.nan
    frame = {'depth_m': depth, 'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    monkeypatch.setattr(probe.geometry, 'place', lambda *_: pytest.fail('new FK called'))
    fresh = fresh_row()
    result = probe.compare_case(fresh, box_output(), frame)
    support = result['support']
    assert support['integer_full_ROI_xyxy'] == [0, 0, 3, 3]
    assert support['ROI_pixel_count'] == 9 and support['valid_point_count'] == 8
    assert support['full_support'][0]['pixel_xy'] == [0, 0]
    assert support['full_support'][-1]['pixel_xy'] == [2, 2]
    assert support['full_support'][0]['position_world_m'] == [.005, .005, .01]
    old, current = result['records']
    assert old['all_seven_candidates'] == fresh['all_seven_candidates']
    assert current['guarded_token'] == 'MV_FWD'
    assert probe._sha256_json(current['canonical']) == probe._sha256_json(fresh['canonical'])
    assert all(v['nominal_tcp_to_P_m'] == fresh['all_seven_candidates'][k]['nominal_tcp_to_P_m']
               for k, v in current['all_seven_candidates'].items())
