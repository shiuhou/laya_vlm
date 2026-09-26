from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task1_native_contact_attribution as probe
from embodied_runtime.experiments.records import RunRecorder


def geometry():
    return {k:{'ids':v} for k,v in {'robot':[0,1,2,3],'arm':[0],'gripper':[1,2,3],
        'left_pad':[1],'right_pad':[2],'drawer':[10,11,12],'handle':[10],
        'explicit_nonhandle':[11]}.items()}


def contact(a,b,f=2.):return {'geom_ids':[a,b],'normal_force_N':f}


def test_exact_historical_selector_rule_differs_from_pairwise_complement():
    # Pad+finger-body handle is designated, not historical N; broad complement remains visible.
    r=probe.classify_contacts([contact(1,10),contact(3,10)],geometry())
    assert r['class']=='designated_only' and not r['historical_non_designated']
    assert r['raw_pairwise_non_designated_above_1N']==1
    r=probe.classify_contacts([contact(1,10),contact(0,10)],geometry())
    assert r['class']=='simultaneous'
    r=probe.classify_contacts([contact(3,12)],geometry())
    assert r['class']=='neither_historical_relation' and r['robot_drawer_above_1N']==1
    assert r['raw_pairwise_non_designated_above_1N']==1


def test_threshold_strictness_bilateral_and_robot_other_scene_are_separate():
    for f in (0.,1.):
        r=probe.classify_contacts([contact(1,10,f)],geometry())
        assert r['class']=='neither_historical_relation' and r['raw_designated_rows']==1
    r=probe.classify_contacts([contact(1,10,1.00001),contact(2,10),contact(3,20),contact(0,1)],geometry())
    assert r['designated'] and r['bilateral'] and r['robot_other_scene_above_1N']==1
    assert r['robot_self_contact_above_1N']==1
    assert probe.classify_contacts([contact(3,10)],geometry())['class']=='historical_non_designated_only'


def test_stage_disagreement_is_ambiguous_and_each_partition_sums_once():
    assert probe.interval_class('designated_only','designated_only')=='designated_only'
    assert probe.interval_class('designated_only','neither_historical_relation')=='ambiguous_stage_difference'
    table=probe.table(probe.INTERVAL_CLASSES)
    probe.accumulate(table,'designated_only',2.);probe.accumulate(table,'ambiguous_stage_difference',-.5)
    assert sum(x['net_change_mm'] for x in table.values())==1.5
    assert sum(x['intervals'] for x in table.values())==2


def test_native_wrist_slice_cached_frame_and_no_mutation(monkeypatch):
    w=SimpleNamespace(data=SimpleNamespace(sensordata=np.arange(10.),site_xpos=np.array([[1.,2.,3.]]),
        site_xmat=np.eye(3).reshape(1,9),time=1.))
    monkeypatch.setattr(probe.native,'integration_fingerprint',lambda _: 'unchanged')
    result=probe.wrist_buffers(w,[{'key':'force_ee','address':2,'dimension':3,'site_id':0}])
    assert result['force_ee']['values']==[2.,3.,4.]
    assert result['force_ee']['actual_sample_time_s'] is None
    assert result['force_ee']['cached_site_position_world_m']==[1.,2.,3.]


def test_wrist_metadata_preserves_static_body_frame_and_checks_physical_type():
    model=SimpleNamespace(sensor_objid=[0,0],sensor_objtype=[6,6],sensor_dim=[3,3],sensor_adr=[0,3],
        sensor_type=[4,5],sensor_needstage=[3,3],site_bodyid=[7],site_pos=np.array([[.1,.2,.3]]),
        site_quat=np.array([[1.,0.,0.,0.]]))
    ids=SimpleNamespace(sensor_name2id=lambda name:{'force':0,'torque':1}[name],site_id2name=lambda _: 'wrist',body_id2name=lambda _: 'hand')
    w=SimpleNamespace(model=model,mujoco=SimpleNamespace(mjtObj=SimpleNamespace(mjOBJ_SITE=6),
        mjtSensor=SimpleNamespace(mjSENS_FORCE=4,mjSENS_TORQUE=5)),env=SimpleNamespace(sim=SimpleNamespace(model=ids),
        robots=[SimpleNamespace(gripper=SimpleNamespace(important_sensors={'force_ee':'force','torque_ee':'torque'}))]))
    metadata=probe.sensor_metadata(w)
    assert metadata[0]['body_name']=='hand' and metadata[0]['site_position_in_body_m']==[.1,.2,.3]
    assert [m['unit'] for m in metadata]==['N','Nm']
    model.sensor_type[1]=4
    with pytest.raises(ValueError,match='physical type'):probe.sensor_metadata(w)


def test_wrist_wrapper_restores_frozen_snapshot_on_exception(monkeypatch):
    original=lambda *a,**k:{'native':True}
    monkeypatch.setattr(probe.native,'snapshot',original)
    monkeypatch.setattr(probe,'wrist_buffers',lambda *a:{'force_ee':{'values':[1,2,3]}})
    with pytest.raises(RuntimeError):
        with probe.with_wrist_snapshots([]):
            assert probe.native.snapshot(None)['native']
            assert 'wrist_sensor_buffers' in probe.native.snapshot(None)
            raise RuntimeError('test')
    assert probe.native.snapshot is original


def test_streaming_hash_chain_rejects_tamper_and_partial_record(tmp_path):
    p=tmp_path/'records';r=RunRecorder(p,{}, {'run_id':'test'});r.record('termination',{'ok':True});r.close()
    assert len(list(probe.stream_records(p/'episodes.jsonl')))==2
    original=(p/'episodes.jsonl').read_bytes()
    (p/'episodes.jsonl').write_bytes(original.replace(b'"ok": true',b'"ok": false'))
    with pytest.raises(ValueError,match='integrity'):list(probe.stream_records(p/'episodes.jsonl'))
    (p/'episodes.jsonl').write_bytes(original[:-1])
    with pytest.raises(ValueError,match='incomplete'):list(probe.stream_records(p/'episodes.jsonl'))


def test_hard_replay_gate_stops_before_next_control_on_each_state_mismatch():
    calls=[];state=np.array([1.]);obs=object()
    def step(command):calls.append(command);state[0]+=1;return {'new':True},0,False,{}
    w=SimpleNamespace(obs=obs,env=SimpleNamespace(step=step,sim=SimpleNamespace(get_state=lambda:SimpleNamespace(flatten=lambda:state.copy()))))
    recorder=SimpleNamespace(record=lambda *a:None)
    with pytest.raises(ValueError,match='before'):probe.replay_control(w,[0],[99.],[2.],recorder,0,0,0)
    assert calls==[] and w.obs is obs
    with pytest.raises(ValueError,match='after'):probe.replay_control(w,[0],[1.],[99.],recorder,0,0,0)
    assert calls==[[0]] and w.obs=={'new':True}


def test_canonical_archive_identity_and_shortened_final_primitive_without_current_code_equality():
    source=probe.load_source()
    assert len(source['primitives'])==122
    assert sum(len(p['commands']) for p in source['primitives'])==970
    assert len(source['primitives'][-1]['commands'])==2
    assert source['primitives'][-1]['outcome']['official_success']
