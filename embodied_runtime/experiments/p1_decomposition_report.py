"""Postseal all-native comparison and visual review for offline decomposition."""
from pathlib import Path
import argparse
import csv
import numpy as np
from .p1_semantic_decomposition import HUMAN, MODEL, registration
from .p1_formal50 import frames
from .p1_segmentation_probe import read, write, seal, verify_seal
from .records import file_hash


def run(root):
    root=Path(root);r=registration(root);verify_seal(root/'scoring')
    rows=read(root/'scoring/rows.json');out=root/'comparison';out.mkdir(exist_ok=False)
    c1=read(HUMAN/'geometry/results.json')
    c4=[x for x in read(MODEL/'scoring/rows.json') if x['camera_id']=='robot0_eye_in_hand']
    old_geo={x['image']['init_index']:x for x in read(MODEL/'geometry/results.json') if x['image']['camera_id']=='robot0_eye_in_hand'}
    table=[]
    for i in range(25):
        human=next(x for x in c1 if x['image']['init_index']==i)
        old=next(x for x in c4 if x['init_index']==i);g=old_geo[i]
        masks=[m for b in old['boxes'] for m in b['masks']]
        admitted=[m for m,a in zip(masks,g.get('mask_point_admission',[])) if a['admitted']]
        item=dict(init_index=i,C1=sum(human['candidate_inside_original_human_polygon']),
            C4=sum(m['task_valid_candidate_count'] for m in admitted),C4_completed=g['status']=='COMPLETE',
            C4_raw_inside=sum(m['task_valid_candidate_count'] for m in masks),
            C4_raw_outside=sum(m['outside_region_candidate_count'] for m in masks),
            C4_admitted_outside=sum(m['outside_region_candidate_count'] for m in admitted))
        for c in ('C2','C3'):
            row=next(x for x in rows if x['condition']==c and x['init_index']==i)
            item[c]=row['admitted_inside'];item[c+'_completed']=row['status']=='COMPLETE'
        table.append(item)
    counts={c:sum(x[c]>0 for x in table) for c in ('C1','C2','C3','C4')};contrasts=[]
    for a,b,name in (('C1','C2','target-specific segmentation/support'),('C2','C3','BOX grounding'),('C3','C4','POINT identity/completion')):
        contrasts.append(dict(a=a,b=b,repair=name,signed_frame_gap=counts[a]-counts[b],
            a_only=[x['init_index'] for x in table if x[a]>0 and x[b]==0],
            b_only=[x['init_index'] for x in table if x[b]>0 and x[a]==0]))
    best=max(contrasts,key=lambda x:x['signed_frame_gap'])
    matched=[x for x in table if x['C3_completed'] and x['C4_completed']]
    result=dict(all25=table,candidate_frame_counts=counts,comparisons=contrasts,
        matched_C3_C4=dict(init_indices=[x['init_index'] for x in matched],n=len(matched),
            C3_candidate_frames=sum(x['C3']>0 for x in matched),C4_candidate_frames=sum(x['C4']>0 for x in matched)),
        primary_future_repair=best['repair'] if best['signed_frame_gap']>0 else 'none earned',
        causal_attribution=False,independent_heldout=False,perception_acceptance=False,for_execution=False)
    write(out/'results.json',result)
    with (out/'all25.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    seal(out);print(result,flush=True)
    review(root,r,rows)


def review(root,r,rows):
    from PIL import Image,ImageDraw
    out=root/'review';out.mkdir(exist_ok=False)
    sensor=frames(r['entry']);scores={(x['condition'],x['init_index']):x for x in rows}
    humans={x['image']['init_index']:x for x in read(HUMAN/'registration.json')['inputs']}
    records=read(root/'masks/outputs.json');inventory=[]
    for i in range(25):
        selected=[x for x in records if x['init_index']==i]
        rgb=sensor[selected[0]['image']['frame_id']][0]['rgb'];h,w=rgb.shape[:2]
        sheet=Image.new('RGB',(w*4,(h+60)*2),'white');draw=ImageDraw.Draw(sheet)
        for line,record in enumerate(selected):
            offset=line*(h+60);sheet.paste(Image.fromarray(rgb),(0,offset))
            draw.text((3,offset+h+3),f"init{i} {record['condition']} original + prompt",fill='black')
            box=record['box_xyxy'];draw.rectangle((box[0],box[1]+offset,box[2],box[3]+offset),outline='red',width=2)
            u,v=record['prompt_admission']['point_xy'];draw.ellipse((u-3,v+offset-3,u+3,v+offset+3),fill='cyan')
            if record['status']!='COMPLETE':
                draw.text((w+3,offset+10),record['failure_stage'],fill='red');continue
            scored=scores[(record['condition'],i)]
            with np.load(record['artifact_uri'],allow_pickle=False) as data:
                for ordinal,mask in enumerate(data['masks']):
                    overlay=rgb.copy();overlay[mask]=(overlay[mask]*.55+np.array([255,0,255])*.45).astype(np.uint8)
                    x=(ordinal+1)*w;sheet.paste(Image.fromarray(overlay),(x,offset))
                    for poly in humans[i]['human_polygons']:
                        points=[(x+p[0],offset+p[1]) for p in poly]
                        draw.line(points+[points[0]],fill='yellow',width=2)
                    m=scored['masks'][ordinal]
                    for c in m['candidates']:
                        if c['image_xy'] is not None:
                            u,v=c['image_xy'];draw.ellipse((x+u-1,offset+v-1,x+u+1,offset+v+1),fill='lime' if c['inside_annotated_region'] else 'red')
                    draw.text((x+3,offset+h+3),f"native{ordinal} in:{m['task_valid_candidate_count']} out:{m['outside_region_candidate_count']}",fill='black')
                    draw.text((x+3,offset+h+20),','.join(m['reason_codes']) or 'geometry candidates',fill='black')
                    draw.text((x+3,offset+h+37),f"purity {m['mask_overlap']['annotated_purity']:.3f}; point {m['mask_point_admission']['admitted']}",fill='black')
        path=out/f'init-{i:03d}.png';sheet.save(path);inventory.append(dict(init_index=i,path=str(path),sha256=file_hash(path)))
    for page in range(5):
        thumbs=[]
        for i in range(page*5,page*5+5):
            im=Image.open(out/f'init-{i:03d}.png');im.thumbnail((1152,474));thumbs.append(im.copy())
        sheet=Image.new('RGB',(1152,sum(im.height for im in thumbs)),'white');y=0
        for im in thumbs:sheet.paste(im,(0,y));y+=im.height
        sheet.save(out/f'page-{page:02d}.png')
    write(out/'inventory.json',inventory);seal(out)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);run(p.parse_args().output)
