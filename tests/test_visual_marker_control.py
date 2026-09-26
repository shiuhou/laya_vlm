import json

import numpy as np
import pytest
from PIL import Image

from embodied_runtime.experiments.records import file_hash
from embodied_runtime.experiments.visual_marker_control import (
    REVISION, SOURCE_INDICES, prepare, table_point,
)
from embodied_runtime.experiments.visual_target_verification import (
    GENERATION, INSTRUCTION, LABELS, MODEL_REPO, PROTOCOL, mark_point,
)
from embodied_runtime.experiments.visual_target_verification_run import protocol_for_manifest


def test_table_location_is_fixed_image_fraction_not_target_dependent():
    assert table_point(384,384)==[192,288]
    assert table_point(101,99)==[50,74]
    with pytest.raises(ValueError):
        table_point(0,384)


def test_control_constructed_from_raw_preserves_original_bytes_and_fixed_order(tmp_path):
    source=tmp_path/'source'
    source.mkdir()
    examples=[]
    raw=np.full((40,40,3),180,np.uint8)
    marked,pixels=mark_point(raw,[10,10])
    for i in SOURCE_INDICES:
        Image.fromarray(raw).save(source/f'{i}-raw.png')
        Image.fromarray(marked).save(source/f'{i}-marked.png')
        examples.append({'source_index':i,'width':40,'height':40,'source_run':'test','step':i,
            'raw_artifact':f'{i}-raw.png','raw_sha256':file_hash(source/f'{i}-raw.png'),
            'marked_artifact':f'{i}-marked.png','marked_sha256':file_hash(source/f'{i}-marked.png'),
            'sample_pixel_xy':[10,10],'point_continuous_xy':[10.1,10.1],'marker_pixels_xy':pixels})
    manifest={'version':'visual-target-verification-input-v1','model_repo':MODEL_REPO,'model_revision':REVISION,
              'instruction':INSTRUCTION,'labels':list(LABELS),'generation_settings':GENERATION,
              'protocol_sha256':file_hash(PROTOCOL),'examples':examples}
    (source/'manifest.json').write_text(json.dumps(manifest))
    out=tmp_path/'output'
    result=prepare(source,out)
    assert len(result['examples'])==8 and len(result['planned_calls'])==16
    assert [e['parent_source_index'] for e in result['examples']]==[0,0,8,8,11,11,17,17]
    assert [e['variant'] for e in result['examples']]==['original','table']*4
    original,control=result['examples'][:2]
    assert (out/original['marked_artifact']).read_bytes()==(source/'0-marked.png').read_bytes()
    with Image.open(out/control['marked_artifact']) as image:
        control_rgb=np.asarray(image)
    assert np.array_equal(control_rgb[8:13,8:13],raw[8:13,8:13])
    assert control['sample_pixel_xy']==[20,30]
    assert protocol_for_manifest(result).name=='visual_marker_control_protocol.md'
    result['examples'][0]['variant']='table'
    with pytest.raises(ValueError,match='selection mismatch'):
        protocol_for_manifest(result)


def test_unknown_probe_profile_is_rejected():
    with pytest.raises(ValueError,match='unregistered'):
        protocol_for_manifest({'version':'arbitrary'})
