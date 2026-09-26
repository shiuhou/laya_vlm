"""Prepare fixed tabletop-marker controls without changing the VLM instruction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .records import code_identity, file_hash
from .visual_target_verification import (
    GENERATION, INSTRUCTION, LABELS, MODEL_REPO, PROTOCOL as PRIMARY_PROTOCOL, mark_point,
)

PROTOCOL = Path('docs/research/visual_marker_control_protocol.md')
SOURCE_INDICES = (0, 8, 11, 17)
REVISION = '66285546d2b821cf421d4f5eb2576359d3770cd3'


def table_point(width, height):
    if type(width) is not int or type(height) is not int or width<=0 or height<=0:
        raise ValueError('positive integer image dimensions required')
    return [width//2, (3*height)//4]


def prepare(source, output):
    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError('Use a fresh control input directory')
    manifest = json.loads((source/'manifest.json').read_text())
    if (manifest['version']!='visual-target-verification-input-v1'
            or manifest['model_repo']!=MODEL_REPO or manifest['model_revision']!=REVISION
            or manifest['instruction']!=INSTRUCTION or manifest['labels']!=list(LABELS)
            or manifest['generation_settings']!=GENERATION
            or manifest['protocol_sha256']!=file_hash(PRIMARY_PROTOCOL)):
        raise ValueError('primary input settings changed')
    originals = {e['source_index']:e for e in manifest['examples']}
    if len(originals)!=len(manifest['examples']):
        raise ValueError('duplicate source image')
    verified = []
    for index in SOURCE_INDICES:
        item = originals[index]
        for kind in ('raw','marked'):
            path = source/item[f'{kind}_artifact']
            if path.resolve().parent!=source.resolve() or file_hash(path)!=item[f'{kind}_sha256']:
                raise ValueError('source image integrity failure')
        with Image.open(source/item['raw_artifact']) as image:
            if image.mode!='RGB' or image.size!=(item['width'],item['height']):
                raise ValueError('source raw RGB shape mismatch')
            raw = np.asarray(image).copy()
        with Image.open(source/item['marked_artifact']) as image:
            marked = np.asarray(image).copy()
        reproduced,_ = mark_point(raw,item['sample_pixel_xy'])
        if not np.array_equal(reproduced,marked):
            raise ValueError('primary marker does not reconstruct')
        point = table_point(item['width'],item['height'])
        control,pixels = mark_point(raw,point)
        verified.append((item,control,point,pixels))
    output.mkdir(parents=True)
    examples=[]
    for item,control,point,pixels in verified:
        original_index=item['source_index']
        raw_name=f'{original_index:02d}-raw.png'
        original_name=f'{original_index:02d}-original.png'
        table_name=f'{original_index:02d}-table.png'
        (output/raw_name).write_bytes((source/item['raw_artifact']).read_bytes())
        (output/original_name).write_bytes((source/item['marked_artifact']).read_bytes())
        Image.fromarray(control).save(output/table_name)
        for variant,name in (('original',original_name),('table',table_name)):
            examples.append({**item,'source_index':len(examples),'parent_source_index':original_index,
                'variant':variant,'raw_artifact':raw_name,'raw_sha256':file_hash(output/raw_name),
                'marked_artifact':name,'marked_sha256':file_hash(output/name),
                'point_continuous_xy':item['point_continuous_xy'] if variant=='original' else point,
                'sample_pixel_xy':item['sample_pixel_xy'] if variant=='original' else point,
                'marker_pixels_xy':item['marker_pixels_xy'] if variant=='original' else pixels})
    result={'version':'visual-marker-control-input-v1','model_repo':MODEL_REPO,'model_revision':REVISION,
        'protocol_sha256':file_hash(PROTOCOL),'parent_input_manifest_sha256':file_hash(source/'manifest.json'),
        'instruction':INSTRUCTION,'labels':list(LABELS),'generation_settings':GENERATION,'repeats':2,
        'code':code_identity(),'examples':examples,'excluded':[],
        'planned_calls':[{'source_index':e['source_index'],'repeat':r} for r in (1,2) for e in examples],
        'generator_input':'marked full RGB only, one image, no history'}
    (output/'manifest.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='runs/autonomous-research/visual-target-verification-inputs-01')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=prepare(args.source,args.output)
    print(json.dumps({'inputs':len(result['examples']),'planned_calls':len(result['planned_calls'])}))


if __name__=='__main__':
    main()
