"""Feedback lineage and terminal sensing; fixtures are not model competence evidence."""
from copy import deepcopy
from types import ModuleType, SimpleNamespace
import sys

import numpy as np
import pytest

from embodied_runtime.experiments import engineering_demo as demo
from embodied_runtime.experiments.demo_feedback import feedback_audit
from embodied_runtime.experiments.records import load_records


def loop_fixture(*, terminal=False):
    endpoint = {'tcp_xyz': [.001, 0., 1.], 'sim_time': .9, 'gripper_command': 1.}
    proprio = {'tcp_pos_world_m': endpoint['tcp_xyz'], 'gripper_width_m': .02, 'gripper_command': 'CLOSED'}
    first = {'step': 0, 'capture': {'capture_seq': 1},
        'execution': {'token': 'GRASP', 'execution_after': endpoint},
        'decision': {'token': 'GRASP'}, 'option_order': ['MV_FWD', 'STOP', 'GRASP'],
        'model_input': {'state': {'state': {'robot.gripper_width_m': .08, 'relations.distance_m': .2}}},
        'evaluation': {p: {'features': {'remaining_open_mm': 100., 'moving_contact': False}} for p in ('before', 'after')}}
    following = {'step': 1, 'execution': None, 'capture': {'capture_seq': 2, 'capture_sim_time': .9},
        'snapshot': {'snapshot': {'continuous': deepcopy(proprio),
            'validity': {'drawer': {'geometry_evidence_ids': [['locateanything+depth', 2]],
                                    'semantic_evidence_ids': [['locateanything+depth', 2]]}}, 'candidates': [
            {'token': 'GRASP', 'feasible': False, 'reason_codes': ['gripper_already_closed']},
            {'token': 'RELEASE', 'feasible': True, 'reason_codes': []}]}},
        'issues': [], 'verified_laya_execution': True, 'option_order': ['MV_FWD', 'STOP', 'RELEASE'],
        'decision': {'token': 'RELEASE'},
        'model_input': {'state': {'state': {'robot.gripper_width_m': .02, 'relations.distance_m': .2}}}}
    rows = [
        {'kind': 'vision_capture', 'data': {'capture_seq': 2, 'capture_sim_time': .9}},
        {'kind': 'demo_boundary', 'data': {'step': 1, 'capture_seq': 2}},
        {'kind': 'observation', 'data': {'accepted': True, 'event': {'source': 'locateanything+depth',
            'source_seq': 2, 'capture_sim_time': .9, 'track_id': 'drawer', 'value': {'position_world_m': [.2, 0., 1.]}}}},
        {'kind': 'observation', 'data': {'accepted': True, 'event': {'source': 'proprio', 'source_seq': 2,
            'capture_sim_time': .9, 'value': deepcopy(proprio)}}},
        {'kind': 'demo_sensing_complete', 'data': {'step': 1, 'capture_seq': 2, 'after_action_step': 0,
            'proprio_source_seq': 2, 'terminal_observation': terminal}}]
    return rows, [first] if terminal else [first, following]


def test_feedback_distinguishes_gate_alternation_from_model_sensitivity():
    rows, attempts = loop_fixture()
    report = feedback_audit(rows, attempts)
    transition = report['transitions'][0]
    assert report['verified_feedback_deliveries'] == 1
    assert report['net_drawer_closure_mm_evaluator_only'] == 0.
    assert report['translation_actions'] == 0
    assert transition['choice_changed'] and transition['previous_choice_removed_by_gate']
    assert transition['newly_vetoed'] == [{'token': 'GRASP', 'reasons': ['gripper_already_closed']}]
    assert transition['changed_model_state']['robot.gripper_width_m'] == {'before': .08, 'after': .02}
    assert 'does not isolate model sensitivity' in transition['interpretation']


@pytest.mark.parametrize('fault, issue', [('stale', 'execution endpoint'), ('robot', 'TCP endpoint'),
    ('belief', 'next belief'), ('rejected', 'visual event not admitted'), ('lineage', 'does not link'),
    ('fusion', 'next fused belief')])
def test_bad_feedback_is_never_verified(fault, issue):
    rows, attempts = loop_fixture()
    if fault == 'stale':
        rows[0]['data']['capture_sim_time'] = .5
    elif fault == 'robot':
        rows[3]['data']['event']['value']['tcp_pos_world_m'] = [9., 0., 1.]
    elif fault == 'belief':
        attempts[1]['snapshot']['snapshot']['continuous']['gripper_width_m'] = .08
    elif fault == 'rejected':
        rows[2]['data']['accepted'] = False
    elif fault == 'fusion':
        attempts[1]['snapshot']['snapshot']['validity']['drawer']['geometry_evidence_ids'] = []
    else:
        rows[4]['data']['after_action_step'] = 99
    result = feedback_audit(rows, attempts)
    assert result['verified_feedback_deliveries'] == 0
    assert any(issue in text for text in result['transitions'][0]['issues'])


def test_terminal_sensing_does_not_invent_a_next_choice():
    rows, attempts = loop_fixture(terminal=True)
    result = feedback_audit(rows, attempts, expect_final=True)
    assert result['terminal_observations'] == 1
    assert result['verified_feedback_deliveries'] == 0
    assert result['transitions'][0]['proposed_after'] is None
    assert not result['transitions'][0]['issues']
    failed = feedback_audit([], attempts, expect_final=True)
    assert failed['terminal_observations'] == 0
    assert 'post-action observation missing' in failed['transitions'][0]['issues']


def scheduling_fixture(monkeypatch, tmp_path, *, observe_final=True, success=False, fail_final=False):
    """Stub models/physics; exercise the production runner's sensing/termination."""
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(manual_seed=lambda _: None))
    jev = ModuleType('jev_libero')
    jev.world = ModuleType('jev_libero.world')
    monkeypatch.setitem(sys.modules, 'jev_libero', jev)
    monkeypatch.setitem(sys.modules, 'jev_libero.world', jev.world)
    monkeypatch.setitem(sys.modules, 'libero', ModuleType('libero'))
    monkeypatch.setattr(demo, 'model_identity', lambda _: {})
    monkeypatch.setattr(demo, 'initial_state_inventory', lambda *a: {'count': 1, 'binding': 'fake', 'state_ids': ['fake']})
    monkeypatch.setattr(demo, 'package_directory', lambda _: tmp_path)
    monkeypatch.setattr(demo, 'repository_identity', lambda _: {})
    world = SimpleNamespace(data=SimpleNamespace(time=.5), config={}, task='fixture')
    world.env = SimpleNamespace(sim=SimpleNamespace(get_state=lambda: np.array([world.data.time])))
    world.features = lambda: {'remaining_open_mm': 100., 'finger_gap_mm': 20., 'moving_contact': False, 'success': success}
    backend = SimpleNamespace(world=world, execution_state=lambda: {}, close=lambda: None,
        proprioception=lambda: {'tcp_pos_world_m': [0., 0., 1.], 'gripper_width_m': .02, 'gripper_command': 'CLOSED'})
    monkeypatch.setattr(demo.RecordingBackend, 'from_task', lambda *a, **kw: backend)
    monkeypatch.setattr(demo, 'load_laya_provider', lambda *a, **kw: SimpleNamespace(agent=object()))
    counter = {'capture': 0, 'actions': 0}

    class Source:
        def __init__(self, _world):
            pass

        def capture(self):
            counter['capture'] += 1
            return {'rgb': np.zeros((4, 4, 3), dtype=np.uint8), 'depth_m': np.ones((4, 4)),
                'intrinsics': np.eye(3), 'camera_to_world': np.eye(4), 'camera_name': 'fixture',
                'capture_seq': counter['capture'], 'capture_sim_time': world.data.time}

    def infer(*a):
        if fail_final and counter['actions'] == 2:
            raise RuntimeError('injected final sensor failure')
        return {}

    monkeypatch.setattr(demo, 'LiberoRgbdSource', Source)
    monkeypatch.setattr(demo, 'LocateAnythingWorker', lambda *a, **kw: SimpleNamespace(infer=infer))
    monkeypatch.setattr(demo, 'LocateAnythingProvider', lambda *a: SimpleNamespace(observe=lambda *a, **kw: {'sensor': True}))

    class Runtime:
        def __init__(self, *a, event_sink, **kw):
            self.store = SimpleNamespace(episode_id='fixture')
            self.source_seq = 0
            self.emit = event_sink

        def ingest(self, *a, **kw):
            return True

        def observe(self, *a):
            self.source_seq += 1
            return True

        def step(self, *a, **kw):
            self.emit('action', {'step': counter['actions'], 'execution': {'token': 'STOP',
                'environment_step_count': 8, 'delta_m': [0., 0., 0.], 'execution_contract_violation': False}})
            counter['actions'] += 1
            world.data.time += .4
            return {'result': {'success': success}}

    monkeypatch.setattr(demo, 'Runtime', Runtime)
    monkeypatch.setattr(demo, 'save_trajectory', lambda *a: None)
    monkeypatch.setattr(demo, 'summarize', lambda *a: None)
    args = demo.parser().parse_args(['--output', str(tmp_path/'run'), '--steps', '2'] +
                                   (['--observe-final'] if observe_final else []))
    return args, counter


@pytest.mark.parametrize('observe_final,success,expected_actions,expected_captures',
                         [(False, False, 2, 2), (True, False, 2, 3), (True, True, 1, 2)])
def test_final_observation_never_executes_an_extra_action(monkeypatch, tmp_path, observe_final, success,
                                                        expected_actions, expected_captures):
    args, counter = scheduling_fixture(monkeypatch, tmp_path, observe_final=observe_final, success=success)
    out = demo.run(args)
    assert counter == {'actions': expected_actions, 'capture': expected_captures}
    rows, errors = load_records(out/'episodes.jsonl')
    assert not errors
    sensing = [r['data'] for r in rows if r['kind'] == 'demo_sensing_complete']
    assert sensing[-1]['terminal_observation'] is observe_final
    assert rows[-1]['data']['step'] == expected_actions - 1


def test_failed_final_observation_preserves_completed_actions(monkeypatch, tmp_path):
    args, counter = scheduling_fixture(monkeypatch, tmp_path, fail_final=True)
    with pytest.raises(RuntimeError, match='injected final sensor failure'):
        demo.run(args)
    rows, errors = load_records(tmp_path/'run'/'episodes.jsonl')
    assert not errors and counter['actions'] == 2
    assert sum(r['kind'] == 'action' for r in rows) == 2
    assert rows[-1]['data']['reason'] == 'demo_error'
    assert rows[-2]['kind'] == 'failure'
