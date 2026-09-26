from copy import deepcopy

import numpy as np

from embodied_runtime.experiments import coarse_point_probe as base
from embodied_runtime.experiments.coarse_initial_point_control import InitialPointGrounding, VERSION
from embodied_runtime.experiments.point_grounding_probe import generation_audit, parse_grounding


class Recorder:
    def __init__(self):
        self.rows = []

    def record(self, kind, value):
        self.rows.append((kind, deepcopy(value)))


def test_only_initial_rgbd_is_consumed_and_age_is_not_refreshed(monkeypatch):
    calls = []
    parsed = parse_grounding('<box><275><275></box>', 4, 4)
    audit = generation_audit([12,99], 100, 16384, 99)

    def call(worker, frame, recorder):
        calls.append(frame['capture_seq'])
        return parsed, audit

    monkeypatch.setattr(base, 'point_call', call)
    first = {'depth_m':np.ones((4,4)), 'intrinsics':np.eye(3), 'camera_to_world':np.eye(4),
             'capture_seq':1, 'capture_sim_time':.5}
    g, recorder = InitialPointGrounding(), Recorder()
    initial = g.admit_point(*g.point_call(None, first, recorder), first, recorder)
    # A later frame has no RGB/depth/calibration members: it cannot re-ground the target.
    later = {'capture_seq':22, 'capture_sim_time':8.9}
    reused = g.admit_point(*g.point_call(None, later, recorder), later, recorder)
    assert initial == reused and initial is not reused and calls == [1]
    robot = {'tcp_pos_world_m':[1.4,1.45,1.], 'gripper_width_m':.08, 'gripper_command':'OPEN'}
    view = g.decision_input(reused, robot, later)
    fresh = base.decision_input(initial, robot, later)
    assert view.rule_token() == fresh.rule_token()
    assert view.candidates == fresh.candidates
    for token in view.effects.effects:
        assert view.effects.effects[token].get('values') == fresh.effects.effects[token].get('values')
    assert view.state.fields['quality.geometry_age_s'].value == 8.4
    assert view.state.fields['quality.semantic_age_s'].value == 8.4
    assert view.state.meta['target_source_capture_seq'] == 1
    assert view.state.meta['admission_policy'] == VERSION
    assert not view.state.meta['current_rgbd_consumed_for_target']
    for field in ('target.visible_now','target.velocity_mps','quality.semantic_confidence',
                  'quality.semantic_valid','quality.position_covariance_m2',
                  'interaction.target_contact','interaction.holding'):
        assert view.state.fields[field].value is None
    # Caller edits cannot mutate the frozen target.
    reused['position_world_m'][0] = 999.
    assert g.initial == initial
