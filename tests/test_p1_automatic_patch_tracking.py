"""Small synthetic provenance/lineage fixtures; no model or real-data experiment."""
import copy
import hashlib
import json
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError
from embodied_runtime.sensor_api import Proprioception
from embodied_runtime.perception.recording import FrameRecorder, replay_frames
from embodied_runtime.perception.grounding_observation import build_grounding_observation, parse_qwen_grounding
from embodied_runtime.perception.semantic_prompt import grounding_point_prompt, mask_point_admission
from embodied_runtime.perception.surface_association import sensor_view_identity
from embodied_runtime.experiments.point_grounding_probe import generation_audit
from embodied_runtime.experiments import p1_automatic_patch_tracking as bridge
from embodied_runtime.experiments.p1_segmentation_probe import seal
from embodied_runtime.experiments.records import file_hash


def fixture(tmp_path):
    recording = tmp_path/'frames'
    rgb = np.random.default_rng(5).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    with FrameRecorder(recording, episode_id='unit', clock_domain='unit', condition='synthetic') as recorder:
        for i, wall in enumerate((100, 100000100, 600000100, 700000100)):
            v = dict(rgb=rgb, depth_m=np.full((64,64), .5, dtype=np.float32), intrinsics_K=np.array([[100.,0,32],[0,100.,32],[0,0,1]]),
                T_base_camera=np.eye(4), camera_id='wrist', frame_seq=i, frame_id=f'original/{i}', calibration_version='cal',
                capture_sim_time_s=1+i*.1, capture_monotonic_ns=wall, frame='robot_base')
            p = Proprioception(1+i*.1,wall,(0.,0.,0.),(0.,0.,0.,1.),(0.,),None,True,('robot',),reason_codes=('WIDTH_UNCALIBRATED',))
            recorder.append([v],p,emitted_monotonic_ns=wall+1)
    (tmp_path/'evaluator.jsonl').write_text('DO NOT READ ORACLE EVIDENCE')
    env, views = next(replay_frames(recording))
    view = dict(views[0], frame_id=views[0]['canonical_frame_id'], episode_id=env.episode_id)
    source = sensor_view_identity(view)
    audit = generation_audit([10,99],2,1000,99)
    obs = {}
    for mode, values in [('BOX',[0,0,1000,1000]),('POINT',[500,500])]:
        raw = json.dumps([dict(label='drawer_front_pushable', **{'bbox_2d' if mode=='BOX' else 'point_2d':values})])
        reply = parse_qwen_grounding(raw,64,64,mode=mode,audit=audit)
        obs[mode] = build_grounding_observation(reply,request_id=mode,source_identity=source,query='front',
            target_key='drawer_front_pushable',frontend_id='synthetic',model_identity={'id':'synthetic'},
            processor_identity={'id':'synthetic'},environment_identity={'id':'synthetic'},audit=audit,
            input_evidence={'query':'front','rgb_sha256':source['rgb_sha256'],'input_token_ids':[1,2]})
    masks = np.zeros((3,64,64),bool)
    masks[:,16:48,16:48] = True
    masks[1,32,32] = False  # Still has geometry; exact POINT containment must exclude this hypothesis.
    artifact = tmp_path/'native.npz'
    np.savez_compressed(artifact,masks=masks,logits=np.where(masks,1.,-1.))
    box = [0.,0.,64.,64.]
    prompt = grounding_point_prompt(view,box,obs['POINT'],query='front',target_key='drawer_front_pushable',config=bridge.config())
    record = dict(input_index=0,box_index=0,box_xyxy=box,query='front',source_identity=source,status='COMPLETE',
        input_record={'recording':str(recording),'source_identity':source,'box_observation':obs['BOX'],'point_observation':obs['POINT']},
        artifact_uri=str(artifact),artifact_sha256=file_hash(artifact),box_response_sha256=obs['BOX']['raw_output_sha256'],
        raw_mask_sha256=[hashlib.sha256(m.tobytes()).hexdigest() for m in masks],prompt_admission=prompt,native_results=[])
    for ordinal, native in enumerate(masks):
        binding=dict(source_identity=source,raw_mask_sha256=record['raw_mask_sha256'][ordinal],mask_index=ordinal,box_index=0,
            box_xyxy=box,box_response_sha256=record['box_response_sha256'],evaluation_labels_used=False)
        record['native_results'].append(dict(ordinal=ordinal,estimate={'source_identity':source,'mask_binding':binding,
            'patch':{'geometry_status':'VALID','reason_codes':[],'candidates':[{'point_id':'same-grid-id'}]}},
            mask_point_admission=mask_point_admission(native,prompt,ordinal)))
    return recording, view, [record]


def test_all_native_hypotheses_no_winner_and_mask_binding_rejects_tampering(tmp_path):
    _, view, records = fixture(tmp_path)
    seeds, decisions = bridge.seed_hypotheses(records,view)
    assert [s['native_mask_ordinal'] for s in seeds] == [0,2]
    assert len(decisions) == 3 and decisions[1]['first_boundary'] == 'POINT_MASK_CONTRADICTION'
    assert all(s['initial_candidate_count'] == 1 for s in seeds)
    changed = copy.deepcopy(records)
    changed[0]['native_results'][0]['estimate']['mask_binding']['raw_mask_sha256'] = '0'*64
    with pytest.raises(ProtocolError,match='binding differs'):
        bridge.seed_hypotheses(changed,view)
    with pytest.raises(ProtocolError,match='first recorded'):
        bridge.seed_hypotheses(records,dict(view,frame_seq=2))


def test_original_wall_gap_breaks_lineage_and_reappearance_does_not_reseed(tmp_path,monkeypatch):
    recording, _, records = fixture(tmp_path)
    geometry = tmp_path/'geometry'
    geometry.mkdir()
    (geometry/'receipt.json').write_text('{}')
    seal(geometry)
    monkeypatch.setattr(bridge,'verified_geometry',lambda root:records)
    calls = []
    def estimate(*args,**kwargs):
        calls.append(kwargs['source_frame_id'])
        return SimpleNamespace(to_dict=lambda:dict(geometry_status='VALID',reason_codes=[],metrics={},candidates=[{'point_id':'same-grid-id'}]))
    monkeypatch.setattr(bridge,'estimate_visible_patch',estimate)
    result = bridge.run(geometry,recording,tmp_path/'output')
    rows = [json.loads(s) for s in (tmp_path/'output/transitions.jsonl').read_text().splitlines()]
    assert result['frames'] == 4 and result['hypotheses'] == 2
    assert result['reseed_events'] == 0 and not result['online_freshness_evaluated']
    for key in ['box-0/native-0','box-0/native-2']:
        chain = [r for r in rows if r['hypothesis_id'] == key]
        assert [r['track']['status'] for r in chain] == ['TRACKED','TRACKED','LOST','LOST']
        assert chain[2]['first_boundary'] == 'TRACKING_GAP'
        assert chain[3]['first_boundary'] == 'RESEED_REQUIRED'
        assert chain[2]['geometry_evaluation'] == chain[3]['geometry_evaluation'] == 'NOT_EVALUATED'
        assert all(r['lineage']['track_generation'] == 1 and not r['reseed_event'] for r in chain)
    ids = [cid for r in rows for cid in r['candidate_evidence_ids']]
    assert len(ids) == len(set(ids)) == len(calls) == 4
    assert all(r['reference_status'] == r['verify_status'] == 'UNKNOWN' for r in rows)
