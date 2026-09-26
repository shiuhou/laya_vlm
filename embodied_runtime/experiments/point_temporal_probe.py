"""Frozen CPU RGB correspondence controls; no live policy, model, depth or oracle."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from .point_grounding_probe import parse_grounding, generation_audit
from .records import RunRecorder, code_identity, file_hash, load_records

PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/point_temporal_probe_protocol.md'
SOURCE_EPISODES_SHA256 = 'd9ed0bc2b10b61b047e44ec37a03ea788b4e88e2f8d06edd8171bcd29677f319'
SOURCE_MANIFEST_SHA256 = '99c46d8ebccee071b5a8840500579d26aedec184ff59e8a51f4c344e13024e54'
CV2_VERSION = '4.11.0'
LK_SETTINGS = {'winSize':(21,21),'maxLevel':3,'criteria':(3,30,.01),'flags':0,'minEigThreshold':.0001}
CONDITIONS = (
    {'name':'static','shift':(0,0),'occlusion':None,'distractor':False,'wrong_seed':False},
    {'name':'shift_x8','shift':(8,0),'occlusion':None,'distractor':False,'wrong_seed':False},
    {'name':'shift_y8','shift':(0,8),'occlusion':None,'distractor':False,'wrong_seed':False},
    {'name':'shift_xy_minus8','shift':(-8,-8),'occlusion':None,'distractor':False,'wrong_seed':False},
    {'name':'target_occluded','shift':(0,0),'occlusion':'target','distractor':False,'wrong_seed':False},
    {'name':'offtarget_occluded','shift':(0,0),'occlusion':'offtarget','distractor':False,'wrong_seed':False},
    {'name':'target_occluded_distractor','shift':(0,0),'occlusion':'target','distractor':True,'wrong_seed':False},
    {'name':'wrong_seed','shift':(0,0),'occlusion':None,'distractor':False,'wrong_seed':True},
)


def translate_rgb(rgb, shift):
    dx,dy = shift
    h,w = rgb.shape[:2]
    result = np.full_like(rgb,127)
    sx0,sx1,sy0,sy1 = max(0,-dx),min(w,w-dx),max(0,-dy),min(h,h-dy)
    if sx1>sx0 and sy1>sy0:
        result[sy0+dy:sy1+dy,sx0+dx:sx1+dx] = rgb[sy0:sy1,sx0:sx1]
    return result


def patch_slices(center, shape, radius=15):
    x,y=map(int,center)
    h,w=shape[:2]
    if x-radius<0 or y-radius<0 or x+radius>=w or y+radius>=h:
        raise ValueError('predeclared patch lies outside image; no clipping/resizing')
    return slice(y-radius,y+radius+1),slice(x-radius,x+radius+1)


def condition_frames(frames, primary_seed, condition):
    h,w = frames.shape[1:3]
    seed = np.asarray([w//4,h//2] if condition['wrong_seed'] else primary_seed,dtype=np.float32)
    result = frames.copy()
    labels = []
    primary = np.asarray(primary_seed,dtype=float)
    for i in range(len(frames)):
        shift = condition['shift'] if i else (0,0)
        if i:
            result[i] = translate_rgb(frames[i],shift)
            if condition['occlusion']:
                center = primary_seed if condition['occlusion']=='target' else [w//4,h//4]
                result[i][patch_slices(center,result[i].shape)] = 127
            if condition['distractor']:
                result[i][patch_slices(primary+np.array([40,0]),result[i].shape)] = frames[0][patch_slices(primary,result[i].shape)]
        labels.append({'primary_reference_pixel_index_xy':(primary+shift).tolist(),
            'primary_local_correspondence_visible':not(i and condition['occlusion']=='target'),
            'seed_is_primary_reference':not condition['wrong_seed'],
            'semantic_identity_verified_by_tracker':False})
    return result,seed,labels


def track_lk(frames, seed, cv2):
    """Only RGB, a supplied seed and frozen settings. No labels/geometry/world."""
    point=np.asarray(seed,np.float32).reshape(1,1,2)
    rows=[{'frame':0,'status':'seeded','point_pixel_index_xy':point.reshape(2).tolist(),
           'forward_status':None,'backward_status':None,'forward_backward_residual_px':None,
           'forward_patch_error':None,'backward_patch_error':None}]
    alive=True
    for i in range(1,len(frames)):
        if not alive:
            rows.append({'frame':i,'status':'unknown_after_native_failure','point_pixel_index_xy':None,
                'forward_status':None,'backward_status':None,'forward_backward_residual_px':None,
                'forward_patch_error':None,'backward_patch_error':None})
            continue
        previous=cv2.cvtColor(frames[i-1],cv2.COLOR_RGB2GRAY)
        current=cv2.cvtColor(frames[i],cv2.COLOR_RGB2GRAY)
        nxt,status,error=cv2.calcOpticalFlowPyrLK(previous,current,point,None,**LK_SETTINGS)
        fs=int(status[0,0]) if status is not None else None
        point_finite=nxt is not None and np.isfinite(nxt).all()
        back,bs,be=None,None,None
        if point_finite and fs==1:
            back,back_status,back_error=cv2.calcOpticalFlowPyrLK(current,previous,nxt,None,**LK_SETTINGS)
            bs=int(back_status[0,0]) if back_status is not None else None
            # OpenCV error is undefined on native failure; do not serialize junk as evidence.
            be=float(back_error[0,0]) if bs==1 and back_error is not None and np.isfinite(back_error[0,0]) else None
        back_finite=back is not None and np.isfinite(back).all()
        alive=bool(point_finite and back_finite and fs==1 and bs==1)
        rows.append({'frame':i,'status':'native_status_ok' if alive else 'native_failure',
            'point_pixel_index_xy':nxt.reshape(2).tolist() if point_finite else None,
            'forward_status':fs,'backward_status':bs,
            'forward_backward_residual_px':float(np.linalg.norm(back-point)) if back_finite and bs==1 else None,
            'forward_patch_error':float(error[0,0]) if fs==1 and error is not None and np.isfinite(error[0,0]) else None,
            'backward_patch_error':be})
        if alive:
            point=nxt
    return rows


def evaluate_rows(tracked, seed, labels):
    rows=[]
    for observed,label in zip(tracked,labels,strict=True):
        p=observed['point_pixel_index_xy']
        reference=np.asarray(label['primary_reference_pixel_index_xy'])
        distance=None if p is None else float(np.linalg.norm(np.asarray(p)-reference))
        visible=label['primary_local_correspondence_visible']
        primary=label['seed_is_primary_reference']
        rows.append({**observed,**label,
            'tracked_distance_to_primary_reference_px':distance,
            'visible_primary_correspondence_error_px':distance if visible and primary and observed['status'] in ('seeded','native_status_ok') else None,
            'native_ok_while_target_occluded':not visible and observed['status']=='native_status_ok',
            'frozen_pixel_prediction':np.asarray(seed).tolist(),
            'frozen_pixel_distance_to_primary_reference_px':float(np.linalg.norm(np.asarray(seed)-reference)),
            'frozen_pixel_visibility_claim':None})
    return rows


def summary(rows):
    def describe(key):
        values=[r[key] for r in rows[1:] if r[key] is not None]
        return {'n':len(values),'median':float(np.median(values)) if values else None,
                'max':float(max(values)) if values else None}
    return {'frames':len(rows),'native_status_ok_after_seed':sum(r['status']=='native_status_ok' for r in rows),
        'unknown_or_native_failure_after_seed':sum(r['status'] in ('native_failure','unknown_after_native_failure') for r in rows),
        'native_ok_while_target_occluded':sum(r['native_ok_while_target_occluded'] for r in rows),
        'visible_primary_correspondence_error_px':describe('visible_primary_correspondence_error_px'),
        'tracked_distance_to_primary_reference_px':describe('tracked_distance_to_primary_reference_px'),
        'frozen_pixel_distance_to_primary_reference_px':describe('frozen_pixel_distance_to_primary_reference_px'),
        'forward_backward_residual_px':describe('forward_backward_residual_px')}


def load_source(source):
    source=Path(source)
    if file_hash(source/'episodes.jsonl')!=SOURCE_EPISODES_SHA256 or file_hash(source/'manifest.json')!=SOURCE_MANIFEST_SHA256:
        raise ValueError('frozen source identity differs')
    rows,errors=load_records(source/'episodes.jsonl')
    if errors:
        raise ValueError('invalid source record chain')
    captures=[r['data'] for r in rows if r['kind']=='vision_capture']
    if [c['capture_seq'] for c in captures]!=list(range(1,27)):
        raise ValueError('26 ordered source captures required')
    first=next(r['data'] for r in rows if r['kind']=='point_call_completed' and r['data']['capture_seq']==1)
    decision=next(r['data'] for r in rows if r['kind']=='decision_boundary' and r['data']['capture_seq']==1)
    images=[]
    for c in captures:
        path=source/c['artifact']
        if file_hash(path)!=c['artifact_sha256']:
            raise ValueError('source frame artifact differs')
        with np.load(path) as data:
            images.append(data['rgb'].copy())  # depth/calibration deliberately not accessed
    frames=np.stack(images)
    if frames.dtype!=np.uint8 or frames.shape!=(26,384,384,3):
        raise ValueError('unexpected frozen image shapes/type')
    parsed=parse_grounding(first['raw_output'],384,384)
    a=first['generation_audit']
    if generation_audit(a['actual_generated_token_ids'],a['input_token_count'],a['model_max_length'],a['eos_token_id'])!=a:
        raise ValueError('first POINT generation audit mismatch')
    if parsed!=first['parsed'] or parsed['status']!='single_point' or not a['terminal_eos_observed'] or a['length_limit_reached']:
        raise ValueError('first POINT not admitted')
    seed=parsed['points'][0]['sample_pixel_xy']
    if seed!=decision['admitted']['sample_pixel_xy']:
        raise ValueError('first admitted seed differs from raw POINT')
    patch=patch_slices(seed,frames[0].shape,radius=10)
    if any(not np.array_equal(frame[patch],frames[0][patch]) for frame in frames):
        raise ValueError('static primary correspondence label unsupported: source patch changed')
    return frames,seed,captures


def run(source,output):
    import cv2
    if cv2.__version__!=CV2_VERSION:
        raise ValueError('use prospectively fixed OpenCV version')
    recorder=RunRecorder(output,{'version':'offline-point-temporal-probe-v1','source':str(source),
        'source_episodes_sha256':SOURCE_EPISODES_SHA256,'source_manifest_sha256':SOURCE_MANIFEST_SHA256,
        'protocol_sha256':file_hash(PROTOCOL),'cv2_version':cv2.__version__,'lk_settings':LK_SETTINGS,
        'conditions':CONDITIONS,'inference':False,'oracle_tracker_inputs':False,'policy_changes':False},
        {'run_id':Path(output).name,'code':code_identity()})
    (Path(output)/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    try:
        frames,seed,captures=load_source(source)
        recorder.record('source_verified',{'captures':captures,'primary_seed_pixel_index_xy':seed,
            'primary_21x21_patch_byte_identical_all_frames':True,'tracker_reads':'RGB and provided seed only'})
        results=[]
        for condition in CONDITIONS:
            transformed,condition_seed,labels=condition_frames(frames,seed,condition)
            relative=f"{condition['name']}-rgb.npz"
            with (Path(output)/relative).open('xb') as stream:
                np.savez_compressed(stream,rgb=transformed)
            recorder.record('condition_started',{'condition':condition,'seed':condition_seed.tolist(),
                'artifact':relative,'artifact_sha256':file_hash(Path(output)/relative),
                'rgb_bytes_sha256':hashlib.sha256(transformed.tobytes()).hexdigest()})
            raw=track_lk(transformed,condition_seed,cv2)
            rows=evaluate_rows(raw,condition_seed,labels)
            for row in rows:
                recorder.record('correspondence',{'condition':condition['name'],**row})
            result={'condition':condition['name'],'summary':summary(rows),'rows':rows}
            recorder.record('condition_completed',result)
            results.append(result)
        report={'results':results,'no_identity_confidence_claim':True,'no_physical_camera_validation':True}
        (Path(output)/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        contact_sheet(output,results)
        recorder.record('termination',{'reason':'completed','conditions':len(results),'rows':sum(len(x['rows']) for x in results)})
        return report
    except BaseException as exc:
        recorder.record('failure',{'reason':repr(exc),'retries':0})
        raise
    finally:
        recorder.close()


def contact_sheet(output,results):
    from PIL import Image,ImageDraw
    out=Path(output)
    canvas=Image.new('RGB',(384*4,430*2),'white')
    d=ImageDraw.Draw(canvas)
    for i,result in enumerate(results):
        with np.load(out/f"{result['condition']}-rgb.npz") as data:
            rgb=data['rgb'][1]
        x,y=(i%4)*384,(i//4)*430
        canvas.paste(Image.fromarray(rgb),(x,y+24))
        d.text((x+4,y+4),result['condition'],fill='black')
        row=result['rows'][1]
        p=row['point_pixel_index_xy']
        if p is not None:
            u,v=p
            d.ellipse((x+u-5,y+24+v-5,x+u+5,y+24+v+5),outline='red')
        d.text((x+4,y+411),f"frame2 native status: {row['status']}",fill='black')
    canvas.save(out/'conditions-frame2.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='runs/autonomous-research/coarse-point-boundary-01')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=run(args.source,args.output)
    print(json.dumps([{k:v for k,v in r.items() if k!='rows'} for r in result['results']],indent=2))


if __name__=='__main__':
    main()
