import pytest

from embodied_runtime.experiments.local_grasp_interface import (
    equal, fixed_token, native_observer, require_pass, required,
)


def test_registered_plan_and_no_extra_step():
    assert [fixed_token(a,s) for a in ('close','open_hold') for s in (13,14)] == ['GRASP','MV_UP','STOP','MV_UP']
    with pytest.raises(ValueError):
        fixed_token('close',15)
    with pytest.raises(ValueError):
        fixed_token('wrong',13)


def test_invalid_execution_cannot_continue():
    result={'execution_contract_violation':False,'execution_contract_reason':[], 'environment_step_count':8}
    require_pass(result)
    with pytest.raises(RuntimeError,match='translation_error'):
        require_pass({**result,'execution_contract_violation':True,'execution_contract_reason':['translation_error']})
    with pytest.raises(RuntimeError,match='control count'):
        require_pass({**result,'environment_step_count':7})


def test_exact_source_matching_and_ambiguity():
    with pytest.raises(ValueError):
        equal([1,2],[1,2.00000000001],'mismatch')
    with pytest.raises(ValueError):
        required([{'i':1},{'i':1}],i=1)
    assert required([{'i':1},{'i':2}],i=2)=={'i':2}


def test_observer_restores_after_exception_and_ignores_scratch():
    from types import SimpleNamespace
    calls=[]
    def step(*args,**kwargs):
        calls.append((args,kwargs))
        return 'original'
    api=SimpleNamespace(mj_step=step)
    world=SimpleNamespace(mujoco=api,model=object(),data=object())
    with pytest.raises(RuntimeError,match='outside'):
        with native_observer(world,None,'close',13,{'control':None},{}) as rows:
            assert api.mj_step(world.model,object())=='original'
            assert not rows
            api.mj_step(world.model,world.data)
    assert api.mj_step is step
    assert len(calls)==1


def test_unexpected_contact_respects_force_and_both_sides():
    from embodied_runtime.experiments.local_grasp_interface import unexpected_contact
    g={'robot':{1,2},'gripper':{2},'bottle':{3}}
    for a,b in ((2,3),(3,2),(3,4)):
        assert not unexpected_contact(a,b,10.,g)
    for a,b in ((1,3),(2,4),(1,2),(2,1)):
        assert unexpected_contact(a,b,.050001,g)
        assert not unexpected_contact(a,b,.05,g)
