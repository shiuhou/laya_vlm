import json

import numpy as np
import pytest

from embodied_runtime.experiments.visual_target_verification import (
    mark_point, parse_label, prepare, tensor_fingerprint,
)
from embodied_runtime.experiments.records import file_hash


def test_marker_preserves_center_and_unmarked_pixels_without_mutating_raw():
    raw=np.zeros((20,20,3),np.uint8)
    marked,pixels=mark_point(raw,[10,10])
    assert len(pixels)==16 and not raw.any()
    assert not marked[10,10].any()
    expected=np.zeros((20,20),bool)
    for x,y in pixels:
        expected[y,x]=True
    assert np.array_equal(np.any(marked!=raw,axis=2),expected)
    with pytest.raises(ValueError,match='no clamping'):
        mark_point(raw,[20,10])
    edge,pixels=mark_point(raw,[0,0])
    assert len(pixels)==8 and not edge[0,0].any()


def test_strict_label_parser_rejects_prose_json_and_quotes():
    assert parse_label(' target_handle\n')=={'status':'valid','label':'target_handle'}
    for value in ['{"label":"target_handle"}','"target_handle"','It is target_handle.','TARGET_HANDLE']:
        assert parse_label(value)=={'status':'invalid','label':None}


def test_tensor_hash_preserves_bfloat16_bits_and_records_dtype():
    import torch
    x=torch.tensor([1,2,3],dtype=torch.bfloat16)
    a=tensor_fingerprint(x)
    assert a['dtype']=='torch.bfloat16' and a['shape']==[3]
    assert a==tensor_fingerprint(x.clone())
    assert a['sha256']!=tensor_fingerprint(x.float())['sha256']


def test_preparation_structural_selection_and_generator_provenance(tmp_path,monkeypatch):
    from embodied_runtime.experiments import visual_target_verification as m
    source,rgb=tmp_path/'source',tmp_path/'rgb'
    source.mkdir()
    rgb.mkdir()
    (source/'episodes.jsonl').write_text('test records supplied by fixture')
    np.save(rgb/'rgb.npy',np.zeros((20,20,3),np.uint8))
    frames=[{'index':i,'source_run':'test','environment_step':i,'rgb_artifact':'rgb.npy',
             'rgb_sha256':file_hash(rgb/'rgb.npy'),'source_npz_sha256':'raw-parent-hash',
             'width':20,'height':20} for i in range(18)]
    safe={'frames':frames}
    (rgb/'manifest.json').write_text(json.dumps(safe))
    config={'source_manifest_sha256':file_hash(rgb/'manifest.json'),'safe_input_manifest':safe}
    records=[{'kind':'run_start','data':{'resolved_config':config}}]
    calls={(i,'point'):{'parsed':{'status':'single_point' if i<14 else 'mixed',
             'points':[{'continuous_xy':[10.1,10.1],'sample_pixel_xy':[10,10]}]},
             'generation_audit':{'complete_generation':True}} for i in range(18)}
    monkeypatch.setattr(m,'load_records',lambda _: (records,[]))
    monkeypatch.setattr(m,'verified_calls',lambda _: (frames,calls,{'missing_calls':[],'failures':[]}))
    result=prepare(source,rgb,tmp_path/'output','a'*40)
    assert len(result['examples'])==14 and len(result['excluded'])==4
    assert len(result['planned_calls'])==28
    assert [c['repeat'] for c in result['planned_calls']]==[1]*14+[2]*14
    assert all('oracle' not in key and 'depth' not in key for key in result)
    with pytest.raises(FileExistsError):
        prepare(source,rgb,tmp_path/'output','a'*40)
    (rgb/'rgb.npy').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='RGB bytes changed'):
        prepare(source,rgb,tmp_path/'corrupt-output','a'*40)
    assert not (tmp_path/'corrupt-output').exists()
