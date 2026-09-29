import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
raw=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research')
source=raw/'task2-postevent-box-support-run-01/result.json'
r=json.loads(source.read_text())
out=raw/'task2-postevent-box-support-report-01'
out.mkdir(exist_ok=False)
(out/'report-source.py').write_bytes(Path(__file__).read_bytes())
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
sheet=Image.new('RGB',(808,900),'white')
draw=ImageDraw.Draw(sheet)
entries=[]
for column,case in enumerate(r['case_order']):
    x=12+400*column
    rgb_path=raw/'task2-closed-empty-current-box-run-01'/case/'rgb-input.npy'
    rgb=np.load(rgb_path,allow_pickle=False)
    original=Image.fromarray(rgb)
    row=next(z for z in r['records'] if z['case_id']==case and z['support_arm']=='current_full_BOX')
    packet=r['support_packets'][case]
    full=packet['full_support']
    by_candidate={token:sorted({i for proxy in v['proxies'].values() for i in proxy['full_support_indices']})
                  for token,v in row['all_seven_candidates'].items()}
    union=sorted({i for ids in by_candidate.values() for i in ids})
    current=set(by_candidate['STOP'])
    endpoint_extra=sorted(set(union)-current)
    overlay=original.copy()
    od=ImageDraw.Draw(overlay)
    od.rectangle(packet['continuous_box_xyxy'],outline=(0,180,255),width=1)
    for i in union:
        px,py=full[i]['pixel_xy']
        overlay.putpixel((px,py),(225,0,190) if i in current else (255,130,0))
    label=case.replace('-postevent','')
    draw.text((x,8),label+' | complete original RGB',font=font,fill='black')
    sheet.paste(original,(x,32))
    draw.text((x,434),f'{label} | all {len(union)} witness pixels + current BOX',font=font,fill='black')
    sheet.paste(overlay,(x,458))
    draw.text((x,849),f'Current proxy: {len(current)}; endpoint-only: {len(endpoint_extra)}',font=small,fill='black')
    entries.append({'case_id':case,'rgb_npy_path':str(rgb_path),'rgb_npy_sha256':hashlib.sha256(rgb_path.read_bytes()).hexdigest(),
        'continuous_box_xyxy':packet['continuous_box_xyxy'],'integer_full_ROI_xyxy':packet['integer_full_ROI_xyxy'],
        'candidate_full_support_indices':by_candidate,'all_witness_full_support_indices':union,
        'all_witness_pixel_xy':[full[i]['pixel_xy'] for i in union],
        'current_proxy_full_support_indices':sorted(current),'endpoint_only_full_support_indices':endpoint_extra,
        'all_points_marked':True,'original_panel_xy':[x,32],'overlay_panel_xy':[x,458],
        'image_size':[384,384]})
draw.text((12,875),'Cyan: full BOX | Magenta: current proxy witness | Orange: additional endpoint witness',font=small,fill='black')
figure=out/'full-rgb-witnesses.png'
sheet.save(figure)
check=np.asarray(Image.open(figure))
for entry in entries:
    x,y=entry['original_panel_xy']
    assert np.array_equal(check[y:y+384,x:x+384],np.load(entry['rgb_npy_path'],allow_pickle=False))
index={'source_result_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'entries':entries,
       'full_resolution_unresized':True,'all_original_panels_pixel_exact':True,
       'no_geometry_or_support_recomputed':True,'figure_sha256':hashlib.sha256(figure.read_bytes()).hexdigest(),
       'report_source_sha256':hashlib.sha256((out/'report-source.py').read_bytes()).hexdigest()}
(out/'overlay-index.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({'figure':str(figure),'figure_sha256':index['figure_sha256'],
    'index_sha256':hashlib.sha256((out/'overlay-index.json').read_bytes()).hexdigest(),
    'witness_counts':[{x['case_id']:len(x['all_witness_full_support_indices'])} for x in entries]},indent=2))
