"""Frozen-mask BOX prompt/domain factorial, offline only; no model calls."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import math
import os
import time
import numpy as np
from ..contracts import content_hash,require
from ..perception.rgbd_geometry import estimate_visible_patch,_roi
from ..perception.surface_association import sensor_view_identity
from .p1_semantic_decomposition import registration as source_registration
from .p1_formal50 import frames,ledger
from .p1_formal50_scoring import score_mask,_percentiles
from .p1_mask_support_reanalysis import config
from .p1_segmentation_probe import read,write,seal,verify_seal
from .records import code_identity,file_hash,versions

SOURCE=Path('runs/p1/semantic-decomposition-20261007')
PROTOCOL=Path('docs/research/p1_box_role_protocol.md')
CONDITION='offline-box-role/1'


def crossed_rows(records):
    by={(x['init_index'],x['condition']):x for x in records};rows=[]
    for i in range(25):
        h,o=by[i,'C2'],by[i,'C3']
        require(h['image']==o['image'] and h['source_identity']==o['source_identity'],'frame mismatch')
        require(h['prompt_admission']['point_xy']==o['prompt_admission']['point_xy'],'POINT differs')
        for name,src,domain in (('HO',h,o),('OH',o,h)):
            rows.append(dict(input_index=len(rows),condition=name,init_index=i,source_record=src,
                sam_prompt_box_xyxy=src['box_xyxy'],geometry_box_xyxy=domain['box_xyxy'],
                evaluation_labels_used=True,for_execution=False))
    return rows


def registration(root):
    r=read(Path(root)/'registration.json')
    require(content_hash({k:v for k,v in r.items() if k!='registration_content_sha256'})==r['registration_content_sha256'],'registration changed')
    require(r['condition']==CONDITION and r['evaluation_labels_used'] and not r['for_execution'],'offline condition required')
    require(content_hash(r['geometry_config'])==content_hash(config().to_dict()),'config changed')
    for p,h in r['source_files_sha256'].items():require(file_hash(p)==h,'source changed: '+p)
    return r


def prepare(root):
    b=source_registration(SOURCE);verify_seal(SOURCE);code=code_identity()
    require(not code['dirty_status'],'freeze execution code first')
    rows=crossed_rows(read(SOURCE/'masks/outputs.json'))
    sources=dict(b['source_files_sha256'])
    paths=[Path(p) for p in code['source_sha256']]+[PROTOCOL]+[p for p in SOURCE.rglob('*') if p.is_file()]
    sources.update({str(p.absolute()):file_hash(p) for p in paths})
    r=dict(condition=CONDITION,source_checkpoint='51be5f6',code=code,entry=b['entry'],inputs=rows,
        source_files_sha256=sources,geometry_config=config().to_dict(),model_calls=0,evaluation_labels_used=True,
        for_execution=False,perception_acceptance=False,registered_at_utc=datetime.now(timezone.utc).isoformat(),
        matched_init_indices=[x['init_index'] for x in rows if x['condition']=='OH' and x['source_record']['status']=='COMPLETE'])
    r['registration_content_sha256']=content_hash(r);root=Path(root);root.mkdir(exist_ok=False);write(root/'registration.json',r)


def evaluate_native(view,proprio,native,src,domain):
    """Only ROI differs from the frozen source computation."""
    masked=view['depth_m'].copy();masked[~native]=np.nan
    return estimate_visible_patch(masked,view['intrinsics_K'],view['T_base_camera'],roi_xyxy=domain,
        source_frame_id=src['source_identity']['frame_id'],calibration_version=view['calibration_version'],
        track_id='offline-human-assisted',feature_id=f"{src['condition']}/mask-{src['ordinal']}",
        capture_sim_time_s=view['capture_sim_time_s'],capture_monotonic_ns=view['capture_monotonic_ns'],
        config=config(),seed=0,eef_position_base_m=proprio['eef_position_base_m'],depth_availability_mask=native).to_dict()


def geometry(root):
    root=Path(root);r=registration(root);out=root/'geometry';out.mkdir(exist_ok=False)
    source_geo={x['input_index']:x for x in read(SOURCE/'geometry/results.json')};sensor=frames(r['entry']);rows=[]
    write(out/'condition.json',dict(code=code_identity(),versions=versions(),pid=os.getpid(),geometry_config=config().to_dict(),
        registration_sha256=file_hash(root/'registration.json'),evaluation_labels_used=True,for_execution=False,model_calls=0,
        process_environment={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')}))
    for spec in r['inputs']:
        src=spec['source_record'];old=source_geo[src['input_index']]
        row=dict(spec,status=src['status'],native_results=[])
        if src['status']!='COMPLETE':
            row.update(first_boundary='SOURCE_MASK_UNAVAILABLE',source_failure=src['failure_stage'],geometry_evaluation='NOT_EVALUATED')
        else:
            view,proprio=sensor[src['image']['frame_id']]
            require(sensor_view_identity(view)==src['source_identity'] and file_hash(src['artifact_uri'])==src['artifact_sha256'],'sensor/mask changed')
            domain=spec['geometry_box_xyxy'];roi=_roi(domain,src['image']['width'],src['image']['height']);u,v=src['prompt_admission']['sample_pixel_xy'];x,y=src['prompt_admission']['point_xy']
            row.update(point_in_geometry_box=bool(domain[0]<=x<domain[2] and domain[1]<=y<domain[3]),
                point_sample_in_geometry_roi=bool(roi[0]<=u<roi[2] and roi[1]<=v<roi[3]))
            with np.load(src['artifact_uri'],allow_pickle=False) as data:
                require(np.array_equal(data['masks'],data['logits']>0) and len(data['masks'])==3,'native corpus changed')
                for ordinal,native in enumerate(data['masks']):
                    require(hashlib.sha256(native.tobytes()).hexdigest()==src['native_mask_sha256'][ordinal],'ordinal changed')
                    start=time.perf_counter();patch=evaluate_native(view,proprio,native,dict(src,ordinal=ordinal),domain);elapsed=time.perf_counter()-start
                    stages=ledger(patch);stages.pop('semantic_source_admission');stages['offline_human_prompt']='REUSED_NOT_RUNTIME_ADMISSION'
                    row['native_results'].append(dict(ordinal=ordinal,patch=patch,source_identity=src['source_identity'],
                        geometry_s=elapsed,stage_ledger=stages,mask_point_admission=old['native_results'][ordinal]['mask_point_admission'],
                        source_mask_sha256=src['native_mask_sha256'][ordinal],evaluation_labels_used=True,for_execution=False))
        write(out/f"input-{spec['input_index']:03d}.json",row);rows.append(row)
        print(spec['condition'],spec['init_index'],row['status'],flush=True)
    write(out/'results.json',rows);seal(out)


def contrast(table,a,b):
    gains=[x['init_index'] for x in table if x[a] and not x[b]];losses=[x['init_index'] for x in table if x[b] and not x[a]]
    n=len(gains)+len(losses)
    exact=min(1.,2*sum(math.comb(n,k) for k in range(min(len(gains),len(losses))+1))/2**n) if n else 1.
    return dict(a=a,b=b,denominator=len(table),gains=gains,losses=losses,net=len(gains)-len(losses),
        exact_discordance_p=exact,independent_sampling_assumed=False,population_significance_claim=False)


def attribution(table):
    counts={c:sum(x[c] for x in table) for c in ('HH','HO','OH','OO')}
    p=((counts['HH']-counts['OH'])+(counts['HO']-counts['OO']))/2
    d=((counts['HH']-counts['HO'])+(counts['OH']-counts['OO']))/2
    return dict(n=len(table),counts=counts,prompt_contribution_frames=p,domain_contribution_frames=d,
        interaction_frames=counts['HH']-counts['HO']-counts['OH']+counts['OO'],
        priority='BOX semantic grounding/prompt interface' if p>max(0,d) else
            'separate semantic BOX from geometry search domain' if d>max(0,p) else 'INCONCLUSIVE',
        contrasts=[contrast(table,a,b) for a,b in [('HH','OH'),('HO','OO'),('HH','HO'),('OH','OO')]])


def score(root):
    root=Path(root);r=registration(root);verify_seal(root/'geometry');out=root/'scoring';out.mkdir(exist_ok=False)
    labels={x['image_id']:x for x in read(r['entry']['annotation_path'])['annotations']};rows=[]
    for record in read(root/'geometry/results.json'):
        src=record['source_record'];row=dict(condition=record['condition'],init_index=record['init_index'],status=record['status'],
            failure=record.get('source_failure'),raw_inside=0,raw_outside=0,admitted_inside=0,admitted_outside=0,masks=[])
        if record['status']=='COMPLETE':
            with np.load(src['artifact_uri'],allow_pickle=False) as data:
                for result,native in zip(record['native_results'],data['masks']):
                    m=score_mask(src['image'],labels[src['image']['image_id']]['entities']['drawer_front_pushable'],native,result,
                        ordinal=result['ordinal'],box=record['geometry_box_xyxy'],stage_ledger=result['stage_ledger'])
                    m.update(mask_point_admission=result['mask_point_admission'],geometry_s=result['geometry_s'],
                        sam_prompt_box_xyxy=record['sam_prompt_box_xyxy'],geometry_box_xyxy=record['geometry_box_xyxy'])
                    row['masks'].append(m)
                    row['raw_inside']+=m['task_valid_candidate_count'];row['raw_outside']+=m['outside_region_candidate_count']
                    if m['mask_point_admission']['admitted']:
                        row['admitted_inside']+=m['task_valid_candidate_count'];row['admitted_outside']+=m['outside_region_candidate_count']
        rows.append(row)
    for src in read(SOURCE/'scoring/rows.json'):
        rows.append(dict(src,condition={'C2':'HH','C3':'OO'}[src['condition']],reused=True))
    table=[]
    for i in range(25):
        item=dict(init_index=i)
        for c in ('HH','HO','OH','OO'):
            row=next(x for x in rows if x['condition']==c and x['init_index']==i)
            item[c]=row['admitted_inside']>0 if row['status']=='COMPLETE' else None
            item[c+'_inside']=row['admitted_inside'];item[c+'_outside']=row['admitted_outside']
        table.append(item)
    matched=[x for x in table if all(x[c] is not None for c in ('HH','HO','OH','OO'))]
    require([x['init_index'] for x in matched]==r['matched_init_indices'],'matched denominator changed')
    summaries={}
    for c in ('HH','HO','OH','OO'):
        selected=[x for x in rows if x['condition']==c];native=[m for x in selected for m in x['masks']]
        summaries[c]=dict(all_frame_denominator=25,completed=sum(x['status']=='COMPLETE' for x in selected),
            unavailable=sum(x['status']!='COMPLETE' for x in selected),candidate_frames=sum(x['admitted_inside']>0 for x in selected),
            native_masks=len(native),raw_inside=sum(x['raw_inside'] for x in selected),raw_outside=sum(x['raw_outside'] for x in selected),
            admitted_inside=sum(x['admitted_inside'] for x in selected),admitted_outside=sum(x['admitted_outside'] for x in selected),
            first_boundary=dict(Counter(m['reason_codes'][0] if m['reason_codes'] else 'CANDIDATES' for m in native)),
            geometry_timing=_percentiles([m['geometry_s'] for m in native]))
    write(out/'rows.json',rows);write(out/'summary.json',summaries)
    write(out/'comparison.json',dict(all25=table,matched=attribution(matched),
        unavailable_init_indices=[x['init_index'] for x in table if x not in matched],model_calls=0,for_execution=False))
    import csv
    with (out/'all25.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    seal(out);print(summaries,flush=True);print(attribution(matched),flush=True)


def review(root):
    from PIL import Image,ImageDraw
    root=Path(root);r=registration(root);verify_seal(root/'scoring');out=root/'review';out.mkdir(exist_ok=False)
    sensor=frames(r['entry']);scores={(x['init_index'],x['condition']):x for x in read(root/'scoring/rows.json')}
    source={(x['init_index'],x['condition']):x for x in read(SOURCE/'masks/outputs.json')}
    labels={x['image_id']:x for x in read(r['entry']['annotation_path'])['annotations']};inventory=[]
    for i in range(25):
        h,o=source[i,'C2'],source[i,'C3'];rgb=sensor[h['image']['frame_id']][0]['rgb'];height,width=rgb.shape[:2]
        sheet=Image.new('RGB',(width*4,(height+50)*4),'white');draw=ImageDraw.Draw(sheet)
        for line,(c,src,domain) in enumerate((('HH',h,h),('HO',h,o),('OH',o,h),('OO',o,o))):
            y0=line*(height+50);sheet.paste(Image.fromarray(rgb),(0,y0))
            for box,color in ((src['box_xyxy'],'cyan'),(domain['box_xyxy'],'red')):
                draw.rectangle((box[0],y0+box[1],box[2],y0+box[3]),outline=color,width=2)
            x,y=src['prompt_admission']['point_xy'];draw.ellipse((x-2,y+y0-2,x+2,y+y0+2),fill='lime')
            draw.text((3,y0+height+3),f'init{i} {c}: SAM cyan / geometry red',fill='black')
            if src['status']!='COMPLETE':
                draw.text((width+3,y0+10),'SOURCE_MASK_UNAVAILABLE: '+src['failure_stage'],fill='red');continue
            with np.load(src['artifact_uri'],allow_pickle=False) as data:
                for ordinal,native in enumerate(data['masks']):
                    x0=(ordinal+1)*width;overlay=rgb.copy()
                    overlay[native]=(overlay[native]*.55+np.array([255,0,255])*.45).astype(np.uint8)
                    sheet.paste(Image.fromarray(overlay),(x0,y0))
                    for poly in labels[src['image']['image_id']]['entities']['drawer_front_pushable']['polygons']:
                        pts=[(x0+x,y0+y) for x,y in poly];draw.line(pts+[pts[0]],fill='yellow',width=2)
                    m=scores[i,c]['masks'][ordinal]
                    for candidate in m['candidates']:
                        if candidate['image_xy'] is not None:
                            x,y=candidate['image_xy'];draw.ellipse((x0+x-1,y0+y-1,x0+x+1,y0+y+1),fill='lime' if candidate['inside_annotated_region'] else 'red')
                    draw.text((x0+3,y0+height+3),f"native{ordinal} in:{m['task_valid_candidate_count']} out:{m['outside_region_candidate_count']}",fill='black')
                    draw.text((x0+3,y0+height+20),','.join(m['reason_codes']) or 'geometry candidates',fill='black')
        path=out/f'init-{i:03d}.png';sheet.save(path);inventory.append(dict(init_index=i,path=str(path),sha256=file_hash(path)))
    for page in range(5):
        thumbs=[]
        for i in range(page*5,page*5+5):
            im=Image.open(out/f'init-{i:03d}.png');im.thumbnail((960,765));thumbs.append(im.copy())
        sheet=Image.new('RGB',(960,sum(im.height for im in thumbs)),'white');y=0
        for im in thumbs:sheet.paste(im,(0,y));y+=im.height
        sheet.save(out/f'page-{page:02d}.png')
    write(out/'inventory.json',inventory);seal(out)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','geometry','score','review']);p.add_argument('--output',required=True);a=p.parse_args()
    try:globals()[a.stage](a.output)
    except Exception as exc:
        out=Path(a.output)/a.stage
        if out.is_dir() and not (out/'sealed.json').exists():
            write(out/'runtime-failure.json',dict(error=repr(exc),hidden_retry=False));seal(out)
        raise
if __name__=='__main__':main()
