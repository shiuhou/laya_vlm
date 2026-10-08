import copy
import pytest
from embodied_runtime.contracts import ProtocolError
from embodied_runtime.experiments import p1_box_grounding_heldout as run


def test_fixed_single_box_intervention_cannot_change_point_or_decoder():
    config=run.read(run.CONFIG);run.validate_condition(config)
    for key,value in [('point_query',config['query_B']),('query_B','another target'),('frame_retry_count',1)]:
        altered=copy.deepcopy(config);altered[key]=value
        with pytest.raises(ProtocolError):run.validate_condition(altered)


def test_failed_point_does_not_suppress_either_box_measurement(tmp_path,monkeypatch):
    config=run.read(run.CONFIG)
    sensor={i:({'image':{'width':384,'height':256},'source_identity':{'frame_id':str(i)}},{'rgb':None},None) for i in range(27,50)}
    monkeypatch.setattr(run,'inputs',lambda root:({'config':config},sensor))
    monkeypatch.setattr(run,'_load_worker',lambda:(None,{'mock':True}))
    (tmp_path/'registration.json').write_text('{}')
    calls=[]
    def point(worker,rgb,query,emit):
        calls.append(('POINT',query));return 'incomplete',{'complete_generation':False,'terminal_eos_observed':False},.1
    def box(worker,rgb,query,emit):
        calls.append(('BOX',query));emit('raw-output',{'inference_s':.2})
        return 'incomplete',{'complete_generation':False,'terminal_eos_observed':False}
    monkeypatch.setattr(run,'infer_point',point);monkeypatch.setattr(run,'infer_audited',box)
    run.grounding(tmp_path)
    output=run.read(tmp_path/'grounding/outputs.json')
    assert len(calls)==len(output)==69
    assert sum(x['kind']=='POINT' for x in output)==23
    assert sum(x['kind']=='A' for x in output)==sum(x['kind']=='B' for x in output)==23
    assert [x['kind'] for x in output[:6]]==['POINT','B','A','POINT','A','B']
    assert all(x['reason']=='INCOMPLETE_GENERATION' and not x['source_admitted'] and not x['evaluation_labels_used'] for x in output)
