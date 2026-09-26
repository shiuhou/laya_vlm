from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import coarse_native_counterfactual as probe


class Recorder:
    def __init__(self):
        self.rows=[]
    def record(self,kind,data):
        self.rows.append((kind,deepcopy(data)))


def test_exact_source_candidates_prefix_and_initial_point_are_preserved():
    rows=probe.load_source()
    controls=probe.data(rows,'control_observation')
    boundary=probe.data(rows,'decision_boundary')[25]
    assert len(controls[:probe.PREFIX_CONTROLS])==200
    assert [c['token'] for c in boundary['canonical']['candidates']]==list(probe.ARMS)
    assert len(probe.ARMS)==7 and probe.ARMS[-1]=='STOP'
    assert boundary['admitted']==probe.one(rows,'initial_target_frozen')['admitted']


def test_actual_prefix_command_state_mismatch_stops_without_followon_control():
    original=[{'step':0,'control':i,'command':[float(i)],'state_before':[float(i)],'state_after':[float(i+1)]} for i in range(2)]
    state=np.array([0.]);calls=[]
    def step(command):
        calls.append(command);state[0]+=1
        return {'sample':float(state[0])},0,False,{}
    world=SimpleNamespace(env=SimpleNamespace(step=step,sim=SimpleNamespace(get_state=lambda:SimpleNamespace(flatten=lambda:state.copy()))),obs=None)
    recorder=Recorder()
    probe.replay_prefix(world,original,recorder,'MV_FWD')
    assert calls==[[0.],[1.]] and world.obs=={'sample':2.}
    assert [r[0] for r in recorder.rows]==['prefix_control_started','prefix_control_completed']*2
    state[0]=0.;calls.clear();bad=deepcopy(original);bad[1]['state_before']=[99.]
    with pytest.raises(ValueError,match='before'):
        probe.replay_prefix(world,bad,Recorder(),'MV_FWD')
    assert calls==[[0.]]


def contact(force,other='panel'):
    return {'normal_force_N':force,'geom_names':['robot',other]}


def test_raw_contact_absence_original_force_threshold_and_progress_are_distinct():
    no_contact=probe.classify([{'contacts':[]}],['handle'],2.,2.-1e-12)
    assert no_contact['no_observed_robot_contact_and_positive_approach']
    exact_zero=probe.classify([{'contacts':[]}],['handle'],2.,2.)
    assert not exact_zero['positive_measured_handle_approach']
    for force in (0.,1.):
        row=probe.classify([{'contacts':[contact(force)]}],['handle'],2.,1.)
        assert not row['no_observed_robot_contact_and_positive_approach']
        assert row['no_robot_contact_above_1N_and_positive_approach']
    row=probe.classify([{'contacts':[contact(1.01)]}],['handle'],2.,1.)
    assert row['robot_contact_above_1N'] and row['nonhandle_contact_above_1N']
    row=probe.classify([{'contacts':[contact(2.,'handle')]}],['handle'],2.,1.)
    assert row['no_observed_nonhandle_contact_and_positive_approach']
    assert not row['no_observed_robot_contact_and_positive_approach']


def test_observer_records_returned_robot_state_without_advancing_native_obs_assignment(monkeypatch):
    state=np.array([0.]);old={'robot0_eef_pos':np.array([0.,0.,0.])}
    returned={'robot0_eef_pos':np.array([1.,2.,3.]),'robot0_gripper_qpos':np.array([.04,-.04])}
    def step(command):
        state[0]+=.05
        return returned,0,False,{}
    world=SimpleNamespace(env=SimpleNamespace(step=step,sim=SimpleNamespace(get_state=lambda:SimpleNamespace(flatten=lambda:state.copy()))),
        obs=old,data=SimpleNamespace(time=.05,qpos=[-.1]),qindex=0)
    monkeypatch.setattr(probe.base,'contact_rows',lambda _:[])
    recorder=Recorder();gap=SimpleNamespace(minimum_mm=lambda _:23.)
    with probe.observe_arm(world,None,gap,recorder,'STOP') as rows:
        result=world.env.step(np.zeros(7))
        assert world.obs is old and result[0] is returned
    assert rows[0]['returned_robot_tcp_m']==[1.,2.,3.]
    assert rows[0]['robot_observation_exact_sample_time_s'] is None
    assert world.env.step is step
