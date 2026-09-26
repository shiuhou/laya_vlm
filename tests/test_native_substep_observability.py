from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import native_substep_observability as probe


class Recorder:
    def __init__(self): self.rows=[]
    def record(self,kind,value): self.rows.append((kind,deepcopy(value)))


def fake_world():
    model=SimpleNamespace(jnt_dofadr=[1],jnt_qposadr=[2])
    data=SimpleNamespace(time=1.,qpos=np.array([4.,5.,6.]),qvel=np.array([7.,8.]),
        qacc=np.array([9.,10.]),ctrl=np.array([.2]),geom_xpos=np.zeros((4,3)),xfrc_applied=np.zeros((4,6)),
        ncon=2,contact=[SimpleNamespace(geom1=0,geom2=1,pos=np.zeros(3),dist=-.001),
                       SimpleNamespace(geom1=2,geom2=3,pos=np.ones(3),dist=.001)])
    for key in ('qfrc_applied','qfrc_constraint','qfrc_passive','qfrc_bias','qfrc_actuator','qfrc_smooth'):
        setattr(data,key,np.array([11.,12.]))
    calls=[]
    def forward(*args,**kwargs): calls.append(('forward',args,kwargs));return 'forward_return'
    def step(*args,**kwargs): calls.append(('step',args,kwargs));data.time+=.002;return 'step_return'
    def contact_force(m,d,i,out): out[:]=[float(i),1,2,3,4,5]
    def state(m,d,out,spec): out[:]=np.r_[d.time,d.qpos,d.qvel,d.ctrl]
    api=SimpleNamespace(mj_step=step,mj_step1=step,mj_step2=step,mj_forward=forward,
        mj_contactForce=contact_force,mjtState=SimpleNamespace(mjSTATE_INTEGRATION=123),
        mj_stateSize=lambda m,s:7,mj_getState=state)
    env=SimpleNamespace(sim=SimpleNamespace(model=SimpleNamespace(geom_id2name=lambda i:f'g{i}')))
    return SimpleNamespace(model=model,data=data,mujoco=api,env=env,jid=0),calls


def test_snapshot_retains_all_contacts_native_force_frame_and_separate_addresses():
    world,_=fake_world();before=probe.integration_fingerprint(world)
    value=probe.snapshot(world,{0},{3},{3},None)
    assert len(value['contacts'])==2 and value['contacts'][1]['robot_sides']==[False,False]
    assert value['contacts'][0]['force_contact_frame']==[0.,1.,2.,3.,4.,5.]
    assert not value['contacts'][1]['above_original_1N']
    assert value['drawer_qpos_m']==6. and value['drawer_qvel_m_s']==8.
    assert value['drawer_qfrc_constraint']==12.
    assert before==probe.integration_fingerprint(world)


def test_snapshot_fails_on_native_state_mutation_from_observer():
    world,_=fake_world()
    def corrupt(m,d,i,out): d.qpos[0]+=1
    world.mujoco.mj_contactForce=corrupt
    with pytest.raises(ValueError,match='snapshot changed'):
        probe.snapshot(world,{0},{3},{3},None)


def test_integrator_hooks_pass_arguments_returns_and_restore_without_touching_other_worlds():
    world,calls=fake_world();api=world.mujoco;originals={k:getattr(api,k) for k in (*probe.FUNCTIONS,'mj_forward')}
    recorder=Recorder();tracking={'control':0}
    with probe.observe_integrators(world,recorder,'MV_DOWN',tracking,({0},{3},{3})) as (observed,forwards):
        assert api.mj_forward(world.model,world.data)=='forward_return'
        assert api.mj_step(world.model,world.data,nstep=1)=='step_return'
        assert len(observed)==1 and observed[0]['after']['time_s']==1.002
        assert observed[0]['before']['last_native_forward']['input_time_s']==1.
        assert len(forwards)==1 and calls[-1][2]=={'nstep':1}
        assert api.mj_step(object(),object())=='step_return'
        assert len(observed)==1
    assert all(getattr(api,k) is v for k,v in originals.items())
    assert [k for k,_ in recorder.rows]==['native_forward_completed','integrator_call_started','integrator_call_completed']


def test_hooks_restore_when_native_integrator_raises():
    world,_=fake_world()
    def failed(*args,**kwargs): raise RuntimeError('native failure')
    world.mujoco.mj_step=failed
    with pytest.raises(RuntimeError,match='native failure'):
        with probe.observe_integrators(world,Recorder(),'MV_RIGHT',{'control':0},({0},{3},{3})):
            world.mujoco.mj_step(world.model,world.data)
    assert world.mujoco.mj_step is failed


def test_controls_stop_before_mismatched_native_command_and_preserve_obs_assignment():
    calls=[];state=np.array([1.]);old=object();world=SimpleNamespace(obs=old)
    def step(command): calls.append(command);return {},0,False,{}
    world.env=SimpleNamespace(step=step,sim=SimpleNamespace(get_state=lambda:SimpleNamespace(flatten=lambda:state.copy())))
    expected=[{'arm':'MV_DOWN','control':0,'command':[1.],'state_before':[1.]}]
    with probe.observe_controls(world,None,None,Recorder(),'MV_DOWN',expected,{'control':None},[]):
        with pytest.raises(ValueError,match='before'):
            world.env.step([2.])
    assert calls==[] and world.obs is old and world.env.step is step


def test_controls_check_full_reference_after_return_before_second_control(monkeypatch):
    world,_=fake_world();world.qindex=2;state=np.array([1.]);old=object();world.obs=old
    returned={'robot0_eef_pos':np.zeros(3),'robot0_gripper_qpos':np.array([.04,-.04])};calls=[]
    def step(command): calls.append(command);state[0]+=1;return returned,0,False,{}
    world.env.step=step;world.env.sim.get_state=lambda:SimpleNamespace(flatten=lambda:state.copy())
    expected=[{'arm':'MV_RIGHT','control':0,'command':[1.],'state_before':[1.],
        'state_after':[999.],'sim_time_s':1.,'contacts':[],'gripper_to_designated_handle_surface_mm':2.,
        'drawer_joint_qpos_m':6.,'returned_robot_tcp_m':[0.,0.,0.],'returned_gripper_qpos':[.04,-.04],
        'robot_observation_exact_sample_time_s':None}]
    monkeypatch.setattr(probe.reference.base,'contact_rows',lambda _:[])
    with probe.observe_controls(world,None,SimpleNamespace(minimum_mm=lambda _:2.),Recorder(),'MV_RIGHT',expected,{'control':None},[]):
        with pytest.raises(ValueError,match='after'):
            world.env.step([1.])
    assert calls==[[1.]] and world.obs is old and world.env.step is step


def test_reference_guard_accepts_frozen_source_and_rejects_modified_source(tmp_path,monkeypatch):
    root=tmp_path/'producer'
    source=root/'embodied_runtime'/'original.py'
    source.parent.mkdir(parents=True)
    source.write_text('original scientific source\n')
    archive=tmp_path/'archive'
    archive.mkdir()
    episodes=archive/'episodes.jsonl'
    episodes.write_text('registered evidence bytes\n')
    rows=[{'kind':'frozen_inputs','data':{'code':{'source_sha256':{
        'embodied_runtime/original.py':probe.file_hash(source)}}}},
        {'kind':'termination','data':{'reason':'seven_arms_complete'}}]
    monkeypatch.setattr(probe,'__file__',str(root/'embodied_runtime'/'experiments'/'probe.py'))
    monkeypatch.setattr(probe,'REFERENCE',archive)
    monkeypatch.setattr(probe,'REFERENCE_SHA256',probe.file_hash(episodes))
    monkeypatch.setattr(probe,'load_records',lambda path:(rows,[]))
    assert probe.load_reference()==rows
    source.write_text('changed scientific source\n')
    with pytest.raises(ValueError,match='reference scientific source changed'):
        probe.load_reference()
    source.write_text('original scientific source\n')
    episodes.write_text('changed reference bytes\n')
    with pytest.raises(ValueError,match='completed seven-arm reference changed'):
        probe.load_reference()


def test_registered_archive_has_expected_native_contract_results():
    # Optional historical-evidence check, independent of the current checkout.
    # Executing the experiment still requires load_reference's strict source guard;
    # unrelated integrated experiments must not invalidate ordinary regression tests.
    path=probe.REFERENCE/'episodes.jsonl'
    if not path.is_file():
        pytest.skip('local frozen seven-arm evidence is not installed')
    assert probe.file_hash(path)==probe.REFERENCE_SHA256
    rows,errors=probe.load_records(path)
    assert not errors
    assert probe.ARMS==('MV_RIGHT','MV_DOWN')
    arms={r['arm']:r for r in probe.data(rows,'arm_completed')}
    assert not arms['MV_RIGHT']['result']['execution_contract_violation']
    assert arms['MV_DOWN']['result']['execution_contract_reason']==['translation_error']
