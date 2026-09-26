"""Prepare a frozen RGB-only semantic target-verification probe; no inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .point_grounding_probe import verified_calls
from .records import code_identity, file_hash, load_records

MODEL_REPO = 'Qwen/Qwen2.5-VL-3B-Instruct'
PROTOCOL = Path('docs/research/visual_target_verification_protocol.md')
LABELS = ('target_handle', 'other_handle', 'other_region', 'uncertain')
INSTRUCTION = (
    'The intended target is the metal handle on the top drawer of the small '
    'freestanding wooden cabinet in the foreground. The red crosshair marks a proposed '
    'target location. Classify which visible part the marked location denotes. '
    'Return exactly one label: target_handle (the intended handle), other_handle '
    '(a different drawer handle), other_region (another visible region), or uncertain '
    '(the visible evidence is insufficient). Do not infer contact or task completion.'
)
GENERATION = {'max_new_tokens': 32, 'do_sample': False, 'use_cache': True}


def mark_point(rgb, sample_pixel):
    if rgb.dtype != np.uint8 or rgb.ndim!=3 or rgb.shape[2]!=3:
        raise ValueError('uint8 RGB required')
    x, y = sample_pixel
    if (type(x) is not int or type(y) is not int
            or not 0<=x<rgb.shape[1] or not 0<=y<rgb.shape[0]):
        raise ValueError('in-frame integer pixel required; no clamping')
    marked = rgb.copy()
    touched = []
    for offset in range(2, 6):
        for dx, dy in ((offset, 0), (-offset, 0), (0, offset), (0, -offset)):
            px, py = x+dx, y+dy
            if 0<=px<rgb.shape[1] and 0<=py<rgb.shape[0]:
                marked[py, px] = [255, 0, 0]
                touched.append([px, py])
    return marked, touched


def parse_label(text):
    answer = text.strip()
    return {'status': 'valid' if answer in LABELS else 'invalid',
            'label': answer if answer in LABELS else None}


def tensor_fingerprint(tensor):
    """Hash exact contiguous processor tensor bytes, including bf16 without casting."""
    import hashlib
    import torch
    value = tensor.detach().cpu().contiguous()
    return {'dtype': str(value.dtype), 'shape': list(value.shape),
            'sha256': hashlib.sha256(value.view(torch.uint8).numpy().tobytes()).hexdigest()}


def prepare(source, rgb_source, output, revision):
    """Read trusted model evidence, select structurally, export RGB-only inputs."""
    source, rgb_source, output = map(Path, (source, rgb_source, output))
    if output.exists():
        raise FileExistsError('Use a fresh preparation directory')
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('pin a full lowercase 40-character upstream revision')
    records, diagnostics = load_records(source/'episodes.jsonl')
    if diagnostics:
        raise ValueError(f'incomplete/corrupt source: {diagnostics}')
    frames, calls, completeness = verified_calls(records)
    if len(frames)!=18 or completeness['missing_calls'] or completeness['failures']:
        raise ValueError('complete original18-frame probe required')
    start = next(r['data']['resolved_config'] for r in records if r['kind']=='run_start')
    if file_hash(rgb_source/'manifest.json') != start['source_manifest_sha256']:
        raise ValueError('RGB manifest differs from generation input')
    if json.loads((rgb_source/'manifest.json').read_text()) != start['safe_input_manifest']:
        raise ValueError('safe RGB manifest mismatch')
    selected, excluded = [], []
    for frame in frames:
        call = calls[frame['index'], 'point']
        if call['parsed']['status']!='single_point' or not call['generation_audit']['complete_generation']:
            excluded.append({'source_index': frame['index'], 'source_run': frame['source_run'],
                             'step': frame['environment_step'], 'status': call['parsed']['status'],
                             'complete_generation': call['generation_audit']['complete_generation']})
            continue
        selected.append((frame, call))
    if len(selected)!=14 or len(excluded)!=4:
        raise ValueError('registered14/4 structural selection changed')
    # All integrity checks precede creating output.
    raw_images = []
    for frame, call in selected:
        artifact = rgb_source/frame['rgb_artifact']
        if file_hash(artifact)!=frame['rgb_sha256']:
            raise ValueError('source RGB bytes changed')
        rgb = np.load(artifact, allow_pickle=False)
        if rgb.shape != (frame['height'], frame['width'], 3):
            raise ValueError('source RGB shape changed')
        point = call['parsed']['points'][0]
        marked, touched = mark_point(rgb, point['sample_pixel_xy'])
        raw_images.append((frame, point, rgb, marked, touched))
    output.mkdir(parents=True)
    examples = []
    for frame, point, rgb, marked, touched in raw_images:
        index = frame['index']
        raw_name, marked_name = f'{index:02d}-raw.png', f'{index:02d}-marked.png'
        Image.fromarray(rgb).save(output/raw_name)
        Image.fromarray(marked).save(output/marked_name)
        examples.append({'source_index': index, 'source_run': frame['source_run'],
                         'step': frame['environment_step'], 'source_rgb_sha256': frame['rgb_sha256'],
                         'source_npz_sha256': frame['source_npz_sha256'],
                         'raw_artifact': raw_name, 'raw_sha256': file_hash(output/raw_name),
                         'marked_artifact': marked_name, 'marked_sha256': file_hash(output/marked_name),
                         'width': frame['width'], 'height': frame['height'],
                         'point_continuous_xy': point['continuous_xy'], 'sample_pixel_xy': point['sample_pixel_xy'],
                         'marker_pixels_xy': touched})
    manifest = {'version': 'visual-target-verification-input-v1', 'model_repo': MODEL_REPO,
                'model_revision': revision, 'protocol_sha256': file_hash(PROTOCOL),
                'source_log_sha256': file_hash(source/'episodes.jsonl'),
                'rgb_source_manifest_sha256': file_hash(rgb_source/'manifest.json'),
                'code': code_identity(), 'instruction': INSTRUCTION, 'labels': list(LABELS),
                'generation_settings': GENERATION, 'repeats': 2,
                'planned_calls': [{'source_index': e['source_index'], 'repeat': repeat}
                                  for repeat in (1, 2) for e in examples],
                'excluded': excluded, 'examples': examples,
                'generator_input': 'marked full RGB only, one image, no history'}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    # No evaluator labels appear in the generator manifest.
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='runs/autonomous-research/point-grounding-probe-02')
    parser.add_argument('--rgb-source', default='runs/autonomous-research/point-grounding-inputs-01')
    parser.add_argument('--output', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    manifest = prepare(args.source, args.rgb_source, args.output, args.revision)
    print(json.dumps({'examples': len(manifest['examples']), 'excluded': manifest['excluded'],
                      'planned_calls': len(manifest['planned_calls'])}, indent=2))


if __name__=='__main__':
    main()
