from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_short_retargeting as runner
from embodied_runtime.experiments import task2_short_retargeting_callback as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


def test_passive_restoration_uses_original_initial_baseline_and_actual_last_sample(tmp_path):
    recorder = RunRecorder(tmp_path / 'run', {}, {'run_id': 'run'})
    groups = {'robot': {1}, 'gripper': {1}, 'bottle': {2}, 'pads': {1}}
    initial = {'time_s': .5, 'contacts': [{'geom_ids': [1, 2], 'normal_force_N': .06}]}
    recorder.record('initial_frame_gate', {'groups_evaluator_only': {k: sorted(v) for k, v in groups.items()},
        'initial_contact_snapshot_evaluator_only': initial, 'initial_above_threshold_robot_pairs': [[1, 2]]})
    record_id = recorder.record('native_after', {'step': 28, 'control': 7, 'index': 24, 'time_s': 12.1})
    passive = probe.restore_passive(recorder, groups)
    assert passive.baseline == {(1, 2)} and passive.first is None
    assert passive.previous == {'stage': 'native_after', 'raw_record_id': record_id,
        'step': 28, 'control': 7, 'index': 24, 'time_s': 12.1}
    recorder.record('first_new_robot_contact', {'new_pairs': [[1, 3]]})
    with pytest.raises(ValueError, match='cannot be cleared'):
        probe.restore_passive(recorder, groups)
    recorder.close()


@dataclass
class View:
    point: list
    own_tcp: list


@pytest.mark.parametrize('outcome', ['two_moves', 'stop_zero', 'stop_second', 'contact', 'contract', 'input_mismatch'])
def test_callback_budget_fresh_own_feedback_abort_and_no_hold(tmp_path, monkeypatch, outcome):
    frame = {'rgb': np.zeros((2, 2, 3), np.uint8), 'depth_m': np.ones((2, 2), np.float32),
        'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}
    source = tmp_path / 'source.npz'
    np.savez_compressed(source, **frame)
    own = {'robot0_eef_pos': [0., 0., 0.], 'robot0_eef_quat': [0., 0., 0., 1.],
        'robot0_gripper_qpos': [.04, -.04], 'robot0_gripper_qvel': [0., 0.]}
    world = SimpleNamespace(obs={k: list(v) for k, v in own.items()}, data=SimpleNamespace(time=12.1))
    backend = SimpleNamespace(world=world, step_m=.01, _grip_cmd=-1)
    backend.proprioception = lambda: {'tcp_pos_world_m': list(world.obs['robot0_eef_pos']),
        'gripper_width_m': .08, 'gripper_command': 'OPEN'}
    recorder = RunRecorder(tmp_path / 'run', {}, {'run_id': 'run'})
    passive = SimpleNamespace(first=None, baseline={(1, 2)})
    monkeypatch.setattr(probe, 'restore_passive', lambda *_: passive)
    monkeypatch.setattr(probe.prior, 'verify_prefix', lambda *_: {'exact': True})
    event_calls, sampled_own, selected_goals, executions = [], [], [], []
    class Event:
        def __init__(self, condition):
            assert condition == 'neck-away'
            self.sensors = []
        def before_scene(self, **kwargs):
            event_calls.append(1)
            artifact = 'scene/capture-000002.npz'
            (recorder.output / 'scene').mkdir()
            actual = {k: v.copy() for k, v in frame.items()}
            if outcome == 'input_mismatch':
                actual['depth_m'][0, 0] = 2.
            np.savez_compressed(recorder.output / artifact, **actual)
            self.sensors.append({'phase': 'scene_after', 'capture_read_sim_time_s': 12.1,
                'own_observations': own, 'artifact': artifact})
    monkeypatch.setattr(probe.scene, 'SceneSuffix', Event)
    monkeypatch.setattr(probe.local, 'read_only_measurement', lambda *_: nullcontext())
    def decision(goal, proprio, *args):
        selected_goals.append(list(goal['position_world_m']))
        sampled_own.append(list(proprio['tcp_pos_world_m']))
        return View(list(goal['position_world_m']), list(proprio['tcp_pos_world_m']))
    monkeypatch.setattr(probe, 'retarget_decision', decision)
    class Selector:
        def __init__(self, packet): assert len(packet['full_support']) == 1
        def __call__(self, view, observations):
            assert view.own_tcp == observations['robot0_eef_pos']
            stop = outcome == 'stop_zero' or (outcome == 'stop_second' and view.own_tcp[0] > 0)
            return ('STOP' if stop else 'MV_FWD'), {'own': observations}, 'rule_no_strict_nominal_improvement'
    monkeypatch.setattr(probe.prior.approach.guard, 'EndpointSelector', Selector)
    @contextmanager
    def controls(*args, **kwargs):
        assert kwargs['expected_grip'] == -1
        yield list(range(8))
    @contextmanager
    def native(world, observer, phase, step, tracking, groups):
        assert observer is passive and phase == 'retarget'
        yield [{'control': i // 25} for i in range(200)]
        if outcome == 'contact':
            passive.first = {'new_pairs': [[1, 3]]}
    monkeypatch.setattr(probe.base, 'observe_controls', controls)
    monkeypatch.setattr(probe.local, 'native_observer', native)
    def execute(token):
        executions.append(token)
        before = world.data.time
        world.data.time += .4
        world.obs['robot0_eef_pos'][0] += .01
        return {'execution_contract_violation': outcome == 'contract', 'delta_m': [.01, 0., 0.],
            'execution_before': {'sim_time': before}, 'execution_after': {'sim_time': world.data.time}}
    def capture():
        return {**frame, 'capture_seq': 30 + len(executions), 'capture_sim_time': world.data.time,
            'camera_name': 'test'}
    callback = probe.RetargetingCallback('cached', goal={'position_world_m': [.1, 0., 0.], 'definition': 'test'},
        goal_source_read_time_s=.5, goal_provenance={'test': True}, guard_packet={'full_support': [{}]},
        postevent_frame=source, postevent_frame_sha256=file_hash(source), postevent_read_time_s=12.1,
        postevent_own=own, common_evaluation_point=[.3, 0., 0.])
    kwargs = {'backend': backend, 'executor': SimpleNamespace(execute=execute),
        'camera': SimpleNamespace(capture=capture), 'recorder': recorder, 'groups': {},
        'approach': {'completed_actions': 29, 'attempted_actions': 29}}
    if outcome == 'input_mismatch':
        with pytest.raises(ValueError, match='RGB/depth/K/T mismatch'):
            callback(**kwargs)
        assert not executions
    else:
        term = callback(**kwargs)
        expected = 0 if outcome == 'stop_zero' else 2 if outcome == 'two_moves' else 1
        assert len(executions) == expected == term['retarget_completed_actions']
        assert 'STOP' not in executions
        assert all(point == [.1, 0., 0.] for point in selected_goals)
        if len(sampled_own) == 2:
            assert sampled_own[1] == [.01, 0., 0.]
        if outcome in ('contact', 'contract'):
            assert term['reason'] == ('new_robot_contact' if outcome == 'contact' else 'execution_contract_violation')
    assert event_calls == [1]
    with pytest.raises(RuntimeError, match='One retarget callback'):
        callback(**kwargs)
    recorder.close()


@pytest.mark.parametrize('moves', [0, 1, 2])
def test_replay_dispatches_one_event_with_explicit_new_phase_including_zero_moves(tmp_path, monkeypatch, moves):
    recorder = RunRecorder(tmp_path / 'source', {}, {'run_id': 'source'})
    for i in range(moves):
        recorder.record('action_completed', {'step': 29+i, 'native_phase': 'retarget', 'token': 'MV_FWD'})
    recorder.close()
    dispatched = []
    def initialize(self, source, output):
        self.invocations = 0
    def dispatch(self, backend, action):
        if action['step'] < 29 or self.invocations:
            return
        assert action['native_phase'] == probe.scene.SCHEDULE[0][0]
        dispatched.append((backend, action))
        self.invocations += 1
    def finish(self): assert self.invocations == 1
    monkeypatch.setattr(probe.scene.SceneReplay, '__init__', initialize)
    monkeypatch.setattr(probe.scene.SceneReplay, '__call__', dispatch)
    monkeypatch.setattr(probe.scene.SceneReplay, 'finish', finish)
    replay = probe.RetargetReplay(recorder.output, tmp_path / 'out')
    backend = object()
    replay(backend, {'step': 28, 'token': 'MV_FWD'})
    for i in range(moves):
        replay(backend, {'step': 29+i, 'native_phase': 'retarget', 'token': 'MV_FWD'})
    replay.finish()
    assert len(dispatched) == 1
    with pytest.raises(ValueError, match='phase mismatch'):
        replay(backend, {'step': 29, 'native_phase': 'grasp'})


@pytest.mark.parametrize('fails_at', [None, 0, 1, 2])
def test_pair_stage_order_budget_and_failure_stops_remaining(tmp_path, fails_at):
    recorder = RunRecorder(tmp_path / 'batch', {}, {'run_id': 'batch'})
    called = []
    def launch(arm, stage):
        called.append((arm, stage))
        if len(called)-1 == fails_at:
            raise RuntimeError('contact execution or replay failure')
    if fails_at is None:
        runner.execute_stages(recorder, launch)
    else:
        with pytest.raises(RuntimeError, match='failure'):
            runner.execute_stages(recorder, launch)
    recorder.close()
    order = [('cached', 'collect'), ('cached', 'replay'), ('refreshed', 'collect'), ('refreshed', 'replay')]
    assert called == order[:4 if fails_at is None else fails_at+1]
    rows, errors = load_records(recorder.output / 'episodes.jsonl')
    assert not errors and sum(r['kind'] == 'stage_intent' for r in rows) == len(called)
