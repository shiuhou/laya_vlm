from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.runtime_core import AtomicExecutor, FakeBackend
from embodied_runtime.experiments.task2_pre22_counterfactual import (
    ARMS, BOUNDARY, PREFIX_CONTROLS, BranchRecorder, contact_summary, exact, own, require_prefix_complete)


class Recorder:
    def __init__(self):
        self.rows = []
    def record(self, kind, data):
        self.rows.append((kind, data))
        return str(len(self.rows))


def test_registered_order_prefix_and_stop_runs_existing_hold():
    assert ARMS == ('MV_FWD', 'MV_BACK', 'MV_LEFT', 'MV_RIGHT', 'MV_UP', 'MV_DOWN', 'STOP')
    assert BOUNDARY == 22 and PREFIX_CONTROLS == 22*8
    class Backend(FakeBackend):
        def __init__(self):
            super().__init__()
            self.holds = 0
        def hold(self):
            self.holds += 1
            self.pos[0] += .0005
    backend = Backend()
    result = AtomicExecutor(backend).execute('STOP')
    assert backend.holds == 1 and result['delta_m'][0] == .0005


def test_first_exact_mismatch_preserves_actual_and_expected_before_raise():
    recorder = Recorder()
    with pytest.raises(ValueError, match='Exact source'):
        exact([1, 2], [1, 3], recorder, 'state')
    assert recorder.rows == [('first_mismatch', {'description': 'state', 'actual': [1, 2], 'expected': [1, 3]})]


def test_branch_recorder_verifies_prefix_controls_and_fwd_probe_only():
    prefix = {'step': 21, 'control': 7, 'command': [1.]}
    probe = {'step': 22, 'control': 0, 'command': [2.]}
    rows = [{'kind': 'control_started', 'data': x} for x in (prefix, probe)]
    recorder = Recorder()
    fwd = BranchRecorder(recorder, 'MV_FWD', rows)
    fwd.record('control_started', prefix)
    with pytest.raises(ValueError):
        fwd.record('control_started', {**probe, 'command': [3.]})
    assert recorder.rows[-2][1]['command'] == [3.]
    assert recorder.rows[-1][0] == 'first_mismatch'
    alternative = BranchRecorder(Recorder(), 'MV_BACK', rows)
    alternative.record('control_started', prefix)
    alternative.record('control_started', {**probe, 'command': [-2.]})
    assert alternative.controls == {}


def test_native_mismatch_records_actual_snapshot_before_source_verifier_raises():
    expected = {'step': 22, 'control': 0, 'index': 0, 'time_s': 9.3}
    recorder = Recorder()
    observer = BranchRecorder(recorder, 'MV_FWD', [{'kind': 'native_before', 'data': expected}])
    with pytest.raises(ValueError, match='native replay'):
        observer.record('native_before', {**expected, 'time_s': 9.4})
    assert recorder.rows[0][0] == 'native_before' and recorder.rows[0][1]['time_s'] == 9.4
    assert recorder.rows[1][0] == 'first_mismatch'


def test_missing_prefix_sample_prevents_probe_even_with_matching_boundary_state():
    observer = SimpleNamespace(verifier=SimpleNamespace(states=[None]*8799, expected={}), controls={})
    with pytest.raises(ValueError, match='no probe admitted'):
        require_prefix_complete(observer)
    observer.verifier.states.append(None)
    require_prefix_complete(observer)
    observer.verifier.expected = {('native_before', 21, 7, 199): {}}
    with pytest.raises(ValueError):
        require_prefix_complete(observer)


def test_raw_and_strict_threshold_stage_summaries_include_every_robot_pair():
    groups = {'robot': {1, 2, 3}, 'gripper': {1, 2}, 'pads': {2}, 'bottle': {4}}
    def contact(a, b, force):
        return {'geom_ids': [a, b], 'geom_names': [str(a), str(b)], 'normal_force_N': force}
    native = [{'control': 0, 'before': {'time_s': 1., 'contacts': [contact(1, 4, .01), contact(2, 4, .05), contact(8, 9, 10.)]},
               'after': {'time_s': 1.002, 'contacts': [contact(1, 4, .051), contact(1, 3, .07)]}}]
    result = contact_summary(native, groups)
    assert result['before']['raw_robot_rows'] == 2 and result['before']['strict_above_005N_rows'] == 0
    assert result['after']['raw_robot_rows'] == 2 and result['after']['strict_above_005N_rows'] == 2
    assert result['before']['first_raw']['class'] == 'other_gripper/bottle'
    assert result['after']['all_strong_robot_pairs'] == [('1', '3'), ('1', '4')]


def test_own_packet_excludes_privileged_state_but_preserves_signed_jaws():
    obs = {'robot0_eef_pos': [1., 2., 3.], 'robot0_eef_quat': [0., 0., 0., 1.],
           'robot0_gripper_qpos': [.04, -.04], 'robot0_gripper_qvel': [0., 0.], 'object_pose': [np.nan]*7}
    result = own(SimpleNamespace(obs=obs))
    assert set(result) == set(obs)-{'object_pose'}
    assert result['robot0_gripper_qpos'] == [.04, -.04]
