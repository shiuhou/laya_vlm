import copy
import hashlib
import json

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.experiments.point_grounding_probe import generation_audit
from embodied_runtime.perception.grounding_observation import (
    build_grounding_observation, build_mapped_grounding_observation, make_model_crop,
    parse_locateanything_grounding, parse_qwen_grounding, validate_grounding_observation,
)
from embodied_runtime.perception.rgbd_geometry import GeometryConfig
from embodied_runtime.perception.semantic_prompt import grounding_point_prompt, point_prompt
from embodied_runtime.perception.surface_association import sensor_view_identity


def audit():
    return generation_audit([10, 11, 99], 2, 1000, 99)


def parse(text, mode="POINT", receipt=None):
    return parse_qwen_grounding(text, 384, 256, mode=mode, audit=receipt or audit(),
                                terminal_special_tokens=("<|im_end|>",))


def test_original_image_coordinates_full_reply_formats_and_actual_eos():
    text = '[{"label":"drawer_front_pushable","point_2d":[251.5,999]}]'
    for raw in (text, text+'<|im_end|>', '```json\n'+text+'\n```<|im_end|>'):
        reply = parse(raw)
        assert reply.admitted and reply.point_xy_px == (96.576, 255.744)
        assert reply.sample_pixel_xy == (96, 255)
        assert reply.raw_output == raw and reply.calibrated_confidence is None
    box = parse('[{"label":"drawer_front_pushable","bbox_2d":[0,0,1000,1000]}]', 'BOX')
    assert box.ordered_boxes_xyxy_px == ((0., 0., 384., 256.),)
    assert parse('[{"label":"drawer_front_pushable","bbox_2d":[100,0,10,1000]}]', 'BOX').reason == 'DEGENERATE_BOX'
    assert parse('[]').reason == 'EXPLICIT_ABSTAIN'
    assert parse(text, receipt=generation_audit([10, 11], 2, 1000, 99)).reason == 'INCOMPLETE_GENERATION'
    forged = dict(audit(), actual_generated_token_ids=[99, 11, 99])
    assert parse(text, receipt=forged).reason == 'INVALID_GENERATION_AUDIT'
    multi_eos = {k:v for k,v in audit().items() if k != 'eos_token_id'}
    multi_eos['eos_token_ids'] = [98, 99]
    assert parse(text, receipt=multi_eos).admitted


@pytest.mark.parametrize('raw', [
    '[{"label":"drawer_front_pushable","point_2d":[1,2]}] extra',
    'Here is JSON: [{"label":"drawer_front_pushable","point_2d":[1,2]}]',
    '[{"label":"drawer_front_pushable","point_2d":[1,2]},',
    '[{"label":"drawer_front_pushable","point_2d":[1,2],"point_2d":[3,4]}]',
    '[{"label":"drawer_front_pushable","point_2d":[true,2]}]',
    '[{"label":"drawer_front_pushable","point_2d":[NaN,2]}]',
    '[{"label":"drawer_front_pushable","point_2d":[1e999,2]}]',
    '[{"label":"drawer_front_pushable","point_2d":[1000,2]}]',
    '[{"label":"drawer_front_pushable","point_2d":[1,2],"confidence":0.9}]',
    '[{"label":"drawer_front_pushable","point_2d":[1,2]},{"label":"drawer_front_pushable","point_2d":[3,4]}]',
    '```json\n[]\n```\n[]',
])
def test_no_prefix_repair_coercion_or_winner(raw):
    assert not parse(raw).admitted


def fixture(raw):
    view = dict(rgb=np.zeros((10, 10, 3), np.uint8), depth_m=np.full((10, 10), .7),
        intrinsics_K=np.eye(3), T_base_camera=np.eye(4), frame_id='f', frame_seq=1,
        camera_id='c', frame='robot_base', episode_id='e', calibration_version='s',
        capture_sim_time_s=0., capture_monotonic_ns=1)
    reply = parse_qwen_grounding(raw, 10, 10, mode='POINT', audit=audit())
    source = sensor_view_identity(view)
    obs = build_grounding_observation(reply, request_id='point/1', source_identity=source,
        query='front', target_key='drawer_front_pushable', frontend_id='qwen3vl',
        model_identity={'revision':'model-pin'}, processor_identity={'revision':'processor-pin'},
        environment_identity={'sha256':'env-pin'}, audit=audit(),
        input_evidence={'query':'front','rgb_sha256':source['rgb_sha256'],'input_token_ids':[1,2]})
    return view, obs


def test_shared_geometry_boundary_and_source_checks_keep_legacy_behavior():
    raw = '[{"label":"drawer_front_pushable","point_2d":[550,550]}]'
    view, obs = fixture(raw)
    la_raw = '<box><550><550></box><|im_end|>'
    la = dict(source_identity=sensor_view_identity(view), query='front', evaluation_labels_used=False,
        status='COMPLETE', raw_output=la_raw, audit=audit(), response_sha256=hashlib.sha256(la_raw.encode()).hexdigest())
    kwargs = dict(query='front',config=GeometryConfig())
    for box in ([0,0,10,10], [5.2,0,10,10], [0,0,5.5,10]):
        assert grounding_point_prompt(view,box,obs,target_key='drawer_front_pushable',**kwargs) == point_prompt(view,box,la,**kwargs)
    with pytest.raises(ProtocolError):
        grounding_point_prompt(view,[0,0,10,10],obs,target_key='other',**kwargs)
    stale_view = dict(view, frame_seq=2)
    with pytest.raises(ProtocolError):
        grounding_point_prompt(stale_view,[0,0,10,10],obs,target_key='drawer_front_pushable',**kwargs)
    changed = copy.deepcopy(obs)
    changed['typed']['point_xy_px'] = [1., 1.]
    changed['observation_sha256'] = content_hash({k:v for k,v in changed.items() if k!='observation_sha256'})
    with pytest.raises(ProtocolError):
        grounding_point_prompt(view,[0,0,10,10],changed,target_key='drawer_front_pushable',**kwargs)
    changed = copy.deepcopy(obs)
    changed['model_identity']['revision'] = 'different-model'
    with pytest.raises(ProtocolError):
        grounding_point_prompt(view,[0,0,10,10],changed,target_key='drawer_front_pushable',**kwargs)
    assert json.loads(json.dumps(obs)) == obs
    la_reply = parse_locateanything_grounding(la_raw,10,10,mode='POINT',audit=audit())
    assert la_reply.point_xy_px == (5.5,5.5)


def crop_fixture():
    view, _ = fixture('[{"label":"drawer_front_pushable","point_2d":[550,550]}]')
    view = dict(view,rgb=np.arange(20*40*3,dtype=np.uint8).reshape(20,40,3),depth_m=np.full((20,40),.7))
    source = sensor_view_identity(view)
    common = dict(source_identity=source,frontend_id='qwen3vl',model_identity={'id':'m'},
        processor_identity={'id':'p'},environment_identity={'id':'e'},audit=audit())
    raw = '[{"label":"tabletop_cabinet","bbox_2d":[250,250,750,750]}]'
    coarse = parse_qwen_grounding(raw,40,20,mode='BOX',audit=audit(),expected_label='tabletop_cabinet')
    observation = build_grounding_observation(coarse,request_id='coarse/1',query='cabinet',
        target_key='tabletop_cabinet',expected_label='tabletop_cabinet',**common,
        input_evidence={'query':'cabinet','rgb_sha256':source['rgb_sha256'],'input_token_ids':[1,2]})
    return view,common,observation


def test_model_crop_exact_inverse_mapping_and_native_evidence_preserved():
    view,common,coarse = crop_fixture()
    crop,binding = make_model_crop(view,coarse)
    assert binding['crop_xyxy_px'] == [7,3,33,17]
    assert np.array_equal(crop,view['rgb'][3:17,7:33])
    for mode,coords in [('POINT',[250,750]),('BOX',[0,0,1000,1000])]:
        raw = json.dumps([{'label':'drawer_front_pushable','point_2d' if mode=='POINT' else 'bbox_2d':coords}])
        reply = parse_qwen_grounding(raw,26,14,mode=mode,audit=audit())
        mapped = build_mapped_grounding_observation(reply,crop_binding=binding,request_id='fine/'+mode,
            query='front',target_key='drawer_front_pushable',**common,
            input_evidence={'query':'front','rgb_sha256':hashlib.sha256(crop.tobytes()).hexdigest(),'input_token_ids':[1,2]})
        verified = validate_grounding_observation(mapped,view=view)
        assert mapped['native_typed']['width'] == 26 and mapped['typed']['width'] == 40
        assert mapped['native_typed']['raw_output'] == mapped['typed']['raw_output'] == raw
        if mode=='POINT':
            assert verified.point_xy_px == (13.5,13.5) and verified.sample_pixel_xy == (13,13)
            prompt = grounding_point_prompt(view,[7,3,33,17],mapped,query='front',target_key='drawer_front_pushable',config=GeometryConfig())
            assert prompt['admitted'] and prompt['point_xy'] == [13.5,13.5]
        else:
            assert verified.ordered_boxes_xyxy_px == ((7.,3.,33.,17.),)
        altered = copy.deepcopy(mapped)
        altered['typed']['width'] = 26  # Mistaking crop coordinates for full source pixels must fail.
        altered['observation_sha256'] = content_hash({k:v for k,v in altered.items() if k!='observation_sha256'})
        with pytest.raises(ProtocolError):
            validate_grounding_observation(altered,view=view)


def test_crop_rule_and_actual_pixel_binding_cannot_be_rehashed_away():
    view,common,coarse = crop_fixture()
    crop,binding = make_model_crop(view,coarse)
    reply = parse_qwen_grounding('[]',26,14,mode='POINT',audit=audit())
    def build(bound):
        return build_mapped_grounding_observation(reply,crop_binding=bound,request_id='fine',query='front',
            target_key='drawer_front_pushable',**common,
            input_evidence={'query':'front','rgb_sha256':bound['crop_rgb_sha256'],'input_token_ids':[1,2]})
    changed = copy.deepcopy(binding)
    changed['crop_xyxy_px'][0] += 1
    changed['crop_binding_sha256'] = content_hash({k:v for k,v in changed.items() if k!='crop_binding_sha256'})
    with pytest.raises(ProtocolError):
        build(changed)
    changed = copy.deepcopy(binding)
    changed['crop_rgb_sha256'] = '0'*64
    changed['crop_binding_sha256'] = content_hash({k:v for k,v in changed.items() if k!='crop_binding_sha256'})
    # Without raw RGB the record can establish internal provenance only. The
    # mandatory view-aware downstream bridge authenticates actual crop bytes.
    forged = build(changed)
    with pytest.raises(ProtocolError,match='crop bytes'):
        validate_grounding_observation(forged,view=view)
    valid = build(binding)
    assert not validate_grounding_observation(valid,view=view).admitted
    assert valid['typed']['reason'] == 'EXPLICIT_ABSTAIN'  # No full-frame fallback.
