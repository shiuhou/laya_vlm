from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments.task2_box_point_boundary import (
    OBS_KEYS, PassiveContactRecorder, above_threshold_robot_pairs, contact_class,
    decision, observe_controls, require_exact_frame,
)


def packet(position=(.02, 0, 0)):
    return {'position_world_m': list(position), 'definition': 'cached_BOX_center_ray_at_fixed_crop_median_depth'}


def proprio(position=(0, 0, 0)):
    return {'tcp_pos_world_m': list(position), 'gripper_width_m': .08, 'gripper_command': 'OPEN'}


def test_rule_uses_unchanged_seven_options_and_live_tcp_with_fixed_proxy():
    point = packet()
    first = decision(point, proprio(), 1, 1, 0)
    second = decision(point, proprio((.02, 0, 0)), 1, 2, 1)
    assert first.rule_token() == 'MV_FWD'
    assert second.rule_token() == 'STOP'
    assert {c.token for c in first.candidates} == {'MV_FWD', 'MV_BACK', 'MV_LEFT', 'MV_RIGHT', 'MV_UP', 'MV_DOWN', 'STOP'}
    assert first.state.fields['target.position_m'].value == second.state.fields['target.position_m'].value == point['position_world_m']
    assert second.state.fields['quality.geometry_age_s'].value == 1
    assert second.state.meta['stationarity_assumption_verified'] is None
    assert not first.state.privileged and not first.effects.privileged
    assert decision(packet((.02, .02, 0)), proprio(), 0, 0, 0).rule_token() == 'MV_FWD'
    assert decision(packet((.004, .004, .004)), proprio(), 0, 0, 0).rule_token() == 'STOP'


def test_extra_oracle_payload_cannot_enter_selector_fields_or_history():
    clean = decision(packet(), proprio(), 0, 0, 0)
    poisoned = {**proprio(), 'bottle_position': [99, 99, 99], 'contacts': ['touch'], 'success': True}
    other = decision(packet(), poisoned, 0, 0, 0)
    assert clean.snapshot_id() == other.snapshot_id()
    assert clean.state.fields['target.position_definition'].value == packet()['definition']


@pytest.mark.parametrize('point, own, source, now', [
    (packet((np.nan, 0, 0)), proprio(), 0, 0),
    (packet(), proprio((np.nan, 0, 0)), 0, 0),
    (packet(), proprio(), 1, 0),
])
def test_nonfinite_or_invalid_age_stops_admission(point, own, source, now):
    with pytest.raises(ValueError):
        decision(point, own, source, now, 0)


def test_initial_frame_gate_requires_dtype_shape_and_signed_zero_bytes():
    frame = {'rgb': np.zeros((2, 3, 3), dtype=np.uint8), 'depth_m': np.zeros((2, 3), dtype=np.float32),
             'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    assert all(require_exact_frame(frame, frame).values())
    changed = {key: value.copy() for key, value in frame.items()}
    changed['depth_m'][0, 0] = -0.
    with pytest.raises(ValueError, match='mismatch'):
        require_exact_frame(changed, frame)
    changed['depth_m'] = frame['depth_m'].astype(np.float64)
    with pytest.raises(ValueError, match='mismatch'):
        require_exact_frame(changed, frame)


GROUPS = {'robot': {1, 2, 3, 4}, 'gripper': {1, 2, 3}, 'pads': {2, 3}, 'bottle': {10}}


def snapshot(pairs=(), t=0.):
    return {'time_s': t, 'contacts': [{'geom_ids': list(pair), 'normal_force_N': force} for pair, force in pairs]}


def test_contact_threshold_is_strict_and_contact_classes_do_not_filter_target():
    row = snapshot([((2, 10), .05), ((1, 10), .051), ((4, 20), 1.), ((10, 20), 5.), ((2, 3), .2)])
    assert above_threshold_robot_pairs(row, GROUPS['robot']) == {(1, 10), (4, 20), (2, 3)}
    assert [contact_class(pair, GROUPS) for pair in ((2, 10), (1, 10), (1, 20), (4, 20), (2, 3))] == [
        'pad/bottle', 'other_gripper/bottle', 'gripper/other_scene', 'arm/scene', 'self']


def test_native_recorder_records_first_contact_and_keeps_observing_without_throwing():
    class Recorder:
        def __init__(self):
            self.rows = []
        def record(self, kind, row):
            self.rows.append((kind, row))
            return str(len(self.rows))
    records = Recorder()
    observer = PassiveContactRecorder(records, GROUPS, snapshot([((4, 20), 1.)]))
    identifiers = {'step': 2, 'control': 0, 'index': 0}
    observer.record('native_before', {**identifiers, **snapshot([((4, 20), 1.)], 1.)})
    assert observer.first is None
    observer.record('native_after', {**identifiers, **snapshot([((2, 10), .1)], 1.002)})
    first = observer.first
    for index in range(1, 25):
        observer.record('native_after', {**identifiers, 'index': index, **snapshot([((2, 3), .5)], 1.002 + .002*index)})
    assert observer.first is first
    assert first['new_pairs'] == [{'geom_ids': [2, 10], 'class': 'pad/bottle'}]
    assert first['previous_observed_sample']['stage'] == 'native_before'
    assert first['first_observed_sample']['stage'] == 'native_after'
    assert sum(kind == 'native_after' for kind, _ in records.rows) == 25
    assert sum(kind == 'first_new_robot_contact' for kind, _ in records.rows) == 1


def test_control_observer_preserves_eight_calls_open_jaws_and_restores_method():
    class Recorder:
        def record(self, kind, row):
            return None
    class Env:
        def __init__(self):
            self.calls = 0
            self.sim = SimpleNamespace(get_state=lambda: SimpleNamespace(flatten=lambda: np.array([self.calls], dtype=float)))
        def step(self, command):
            self.calls += 1
            return ({key: np.zeros(3) for key in OBS_KEYS}, None)
    env, tracking = Env(), {'control': None}
    with observe_controls(SimpleNamespace(env=env), Recorder(), 0, tracking) as controls:
        for _ in range(8):
            env.step(np.array([0., 0, 0, 0, 0, 0, -1]))
        with pytest.raises(RuntimeError, match='control'):
            env.step(np.array([0., 0, 0, 0, 0, 0, -1]))
    assert len(controls) == env.calls == 8 and 'step' not in env.__dict__
    assert tracking['control'] is None
