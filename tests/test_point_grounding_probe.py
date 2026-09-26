import inspect

import numpy as np
import pytest

from embodied_runtime.experiments.point_grounding_probe import (
    evaluate_location, generate, generation_audit, parse_grounding, pixel_for_point,
)


def test_point_coordinate_boundaries_no_clamping():
    p = parse_grounding('<box><500><250></box>', 384, 384)
    assert p['status']=='single_point'
    assert p['points'][0]['continuous_xy']==[192., 96.]
    assert p['points'][0]['sample_pixel_xy']==[192, 96]
    assert parse_grounding('<box><1000><250></box>',384,384)['status']=='point_out_of_frame'
    assert pixel_for_point([-1, 1],384,384) is None
    assert pixel_for_point([float('nan'), 1],384,384) is None


@pytest.mark.parametrize(('raw','status'), [
    ('<box>none</box>', 'none'), ('hello', 'no_grounding'),
    ('<box><1><2></box><box><3><4></box>', 'multiple_points'),
    ('<box><1><2></box><box><1><2><3><4></box>', 'mixed'),
    ('<box><1><2><3></box>', 'malformed'), ('<box><1><2>', 'malformed'),
    ('<box><1001><2></box>', 'malformed'), ('<box><3><2><1><4></box>', 'malformed'),
])
def test_no_silent_grounding_fallback(raw,status):
    assert parse_grounding(raw,100,100)['status']==status


def test_parseable_point_not_eos_or_no_truncation_evidence():
    a = generation_audit([7]*256,100,16384,99)
    assert a['length_limit_reached'] and not a['complete_generation']
    assert generation_audit([7,99],100,16384,99)['complete_generation']
    assert generation_audit([7]*6,100,106,99)['length_limit_reached']


def test_evaluator_samples_pixel_center_and_preserves_invalid_depth():
    depth=np.ones((4,4))
    mask=np.zeros((4,4),bool)
    mask[1,1]=True
    r=evaluate_location([1.1,1.1],depth,np.eye(3),np.eye(4),mask,[1.])
    assert r['point_world_m']==[1.5,1.5,1.]
    assert r['target_member'] and r['nearest_ray_surface_distance_mm']==0
    depth[1,1]=np.nan
    r=evaluate_location([1.1,1.1],depth,np.eye(3),np.eye(4),mask,[1.])
    assert r['depth_status']=='invalid' and r['point_world_m'] is None


def test_generator_uses_rgb_only_artifact_without_evaluator_imports():
    source=inspect.getsource(generate)
    assert "['depth_m']" not in source and 'oracle_mask' not in source
    assert 'audit_run' not in source and '_restore_support' not in source
    assert 'rgb_artifact' in source and "'source_manifest_sha256'" in source


def _records_fixture():
    from embodied_runtime.experiments.point_grounding_probe import generation_audit
    frame={'index':0,'width':100,'height':100,'order':['box','point']}
    raw='<box><500><500></box>'
    return [
        {'kind':'run_start','data':{'resolved_config':{'safe_input_manifest':{'frames':[frame]}}}},
        {'kind':'call_started','data':{'frame':frame,'mode':'point','input_token_ids':[1,2]}},
        {'kind':'call_completed','data':{'frame':frame,'mode':'point','raw_output':raw,
            'parsed':parse_grounding(raw,100,100), 'generation_audit':generation_audit([7,99],2,16384,99)}},
    ]


def test_incomplete_planned_frame_retains_missing_call_and_denominator():
    from embodied_runtime.experiments.point_grounding_probe import verified_calls
    records=_records_fixture()
    frames, completed, status=verified_calls(records)
    assert len(frames)==1 and len(completed)==1 and status['planned_calls']==2
    assert status['missing_calls']==[{'index':0,'mode':'box','started':False}]
    assert status['terminations']==[]
    frames, completed, status=verified_calls(records[:1])
    assert len(frames)==1 and not completed and len(status['missing_calls'])==2


def test_duplicate_completed_call_rejected_not_overwritten():
    from embodied_runtime.experiments.point_grounding_probe import verified_calls
    records=_records_fixture()
    with pytest.raises(ValueError,match='duplicate call'):
        verified_calls(records+[records[-1]])


@pytest.mark.parametrize('corruption',['parse','tokens','frame','start'])
def test_corrupt_derived_grounding_or_audit_rejected(corruption):
    from embodied_runtime.experiments.point_grounding_probe import verified_calls
    records=_records_fixture()
    if corruption=='parse':
        records[-1]['data']['parsed']['status']='none'
    elif corruption=='tokens':
        records[-1]['data']['generation_audit']['complete_generation']=False
    elif corruption=='frame':
        records[-1]['data']['frame']={**records[-1]['data']['frame'],'width':99}
    else:
        records.pop(1)
    with pytest.raises(ValueError):
        verified_calls(records)


def test_model_config_nested_torch_dtype_conversion_is_explicit_and_reversible():
    import json
    import torch
    from embodied_runtime.experiments.point_grounding_probe import serialize_model_config
    original={'vision':{'dtype':torch.bfloat16,'layers':[{'dtype':torch.float32}]},
              'label':'torch.bfloat16','shape':(2,3),'unused':None,'id2label':{0:'a',1:'b'}}
    result=serialize_model_config(original)
    restored=json.loads(json.dumps(result))['value']
    for conversion in reversed(result['type_conversions']):
        node=restored
        for part in conversion['path'][:-1]:
            node=node[part]
        key=conversion['path'][-1]
        if conversion['python_type']=='torch.dtype':
            node[key]=getattr(torch,node[key].removeprefix('torch.'))
        elif conversion['python_type']=='int_dict_key':
            node[int(key)]=node.pop(key)
        elif conversion['python_type']=='tuple':
            node[key]=tuple(node[key])
    assert restored==original
    assert original['vision']['dtype'] is torch.bfloat16
    assert result['value']['label']=='torch.bfloat16'
    with pytest.raises(TypeError,match='unsupported config value'):
        serialize_model_config({'unexpected':object()})
