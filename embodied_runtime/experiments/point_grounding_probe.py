"""Frozen RGB-only grounding generation and separate privileged offline evaluation."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from pathlib import Path

import numpy as np

from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

QUERY = 'the metal handle on the top drawer of the small freestanding wooden cabinet in the foreground'
PROTOCOL = Path('docs/research/point_grounding_probe_protocol.md')
SETTINGS = {'max_new_tokens': 256, 'use_cache': True, 'generation_mode': 'hybrid',
            'temperature': 0.0, 'do_sample': False, 'verbose': False}
BOX = re.compile(r'<box>(.*?)</box>', re.DOTALL)


def pixel_for_point(point, width, height):
    u, v = point
    if not (math.isfinite(u) and math.isfinite(v) and 0 <= u < width and 0 <= v < height):
        return None
    return [math.floor(u), math.floor(v)]


def parse_grounding(raw, width, height):
    points, boxes, empty, invalid = [], [], 0, []
    for body in BOX.findall(raw):
        if body.strip() == 'none':
            empty += 1
            continue
        tokens = re.findall(r'<(\d+)>', body)
        if ''.join(f'<{s}>' for s in tokens) != body.strip() or len(tokens) not in (2, 4):
            invalid.append(body)
            continue
        coords = [int(x) for x in tokens]
        if any(x>1000 for x in coords):
            invalid.append(body)
            continue
        pixels = [x/1000*(width if i % 2 == 0 else height) for i, x in enumerate(coords)]
        if len(coords)==2:
            points.append({'normalized': coords, 'continuous_xy': pixels,
                           'sample_pixel_xy': pixel_for_point(pixels, width, height)})
        elif coords[2]<=coords[0] or coords[3]<=coords[1]:
            invalid.append(body)
        else:
            boxes.append({'normalized': coords, 'continuous_xyxy': pixels})
    if raw.count('<box>') != len(BOX.findall(raw)) or raw.count('</box>') != len(BOX.findall(raw)):
        invalid.append('unbalanced_box_tags')
    if invalid:
        status = 'malformed'
    elif sum(bool(x) for x in (points, boxes, empty))>1:
        status = 'mixed'
    elif points:
        status = 'multiple_points' if len(points)>1 else 'single_point' if points[0]['sample_pixel_xy'] is not None else 'point_out_of_frame'
    elif boxes:
        status = 'multiple_boxes' if len(boxes)>1 else 'single_box'
    else:
        status = 'none' if empty else 'no_grounding'
    return {'status': status, 'points': points, 'boxes': boxes, 'empty_count': empty,
            'invalid': invalid, 'confidence': None}


def generation_audit(ids, input_count, model_max_length, eos_token_id):
    limit = min(SETTINGS['max_new_tokens'], model_max_length-input_count)
    eos = bool(ids) and ids[-1] == eos_token_id
    return {'actual_generated_token_ids': ids, 'actual_generated_token_count': len(ids),
            'input_token_count': input_count, 'model_max_length': model_max_length, 'eos_token_id': eos_token_id,
            'effective_limit': limit, 'terminal_eos_observed': eos,
            'length_limit_reached': len(ids)>=limit,
            'complete_generation': eos, 'truncation_status': 'eos_terminated' if eos else 'no_terminal_eos'}


def prepare(output, audit_path):
    from .perception_support_audit import audit_run
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a fresh preparation directory')
    audit = json.loads(Path(audit_path).read_text())
    # Reverify all raw sources before extracting image-only inputs.
    verified = [audit_run(r['source']) for r in audit['runs']]
    if [r['episodes_sha256'] for r in verified] != [r['episodes_sha256'] for r in audit['runs']]:
        raise ValueError('source log changed since prior support audit')
    output.mkdir(parents=True)
    frames = []
    for run in verified:
        for row in run['rows']:
            source = Path(row['frame_artifact'])
            if file_hash(source)!=row['frame_sha256']:
                raise ValueError('source frame changed')
            with np.load(source) as frame:
                rgb = frame['rgb'].copy()
            name = f'rgb-{len(frames):02d}.npy'
            np.save(output/name, rgb, allow_pickle=False)
            frames.append({'index': len(frames), 'rgb_artifact': name, 'rgb_sha256': file_hash(output/name),
                           'source_npz_sha256': row['frame_sha256'], 'source_run': row['run'],
                           'capture_seq': row['capture_seq'], 'environment_step': row['environment_step'],
                           'width': rgb.shape[1], 'height': rgb.shape[0],
                           'order': ['box', 'point'] if len(frames)%2==0 else ['point', 'box']})
    manifest = {'version': 'point-grounding-input-v1', 'query': QUERY, 'settings': SETTINGS,
                'source_audit_sha256': file_hash(audit_path), 'protocol_sha256': file_hash(PROTOCOL),
                'generator_allowed_fields': 'RGB only; no depth/calibration/mask/world/pose', 'frames': frames}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return manifest


def generate(source, output, model_path, device):
    from PIL import Image
    from ..adapters.locateanything import LocateAnythingWorker
    source = Path(source)
    manifest = json.loads((source/'manifest.json').read_text())
    if (manifest['query']!=QUERY or manifest['settings']!=SETTINGS
            or manifest['protocol_sha256']!=file_hash(PROTOCOL)):
        raise ValueError('frozen input changed')
    recorder = RunRecorder(output, {'source_manifest_sha256': file_hash(source/'manifest.json'),
                           'query': QUERY, 'settings': SETTINGS, 'protocol_sha256': manifest['protocol_sha256'],
                           'oracle': False, 'safe_input_manifest': manifest}, {'run_id': Path(output).name,
                           'code': code_identity(), 'model': model_identity(model_path), 'versions': versions(),
                           'device': device, 'dtype': 'bfloat16',
                           'environment': {k: os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES', 'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')}})
    try:
        worker = LocateAnythingWorker(model_path, device=device)
        torch = worker.torch
        recorder.manifest_update({'model_config': worker.model.config.to_dict(),
            'gpu': {'name': torch.cuda.get_device_name(device),
                    'total_memory_bytes': torch.cuda.get_device_properties(device).total_memory},
            'tokenizer_model_max_length': worker.tokenizer.model_max_length,
            'eos_token_id': worker.tokenizer.convert_tokens_to_ids('<|im_end|>')})
        original_decode = worker.tokenizer.batch_decode
        observed = []

        def audit_decode(sequences, *args, **kwargs):
            observed.append(sequences.detach().cpu().tolist())
            return original_decode(sequences, *args, **kwargs)

        worker.tokenizer.batch_decode = audit_decode
        for frame in manifest['frames']:
            artifact = source/frame['rgb_artifact']
            if file_hash(artifact)!=frame['rgb_sha256']:
                raise ValueError('RGB input changed')
            image = Image.fromarray(np.load(artifact, allow_pickle=False)).convert('RGB')
            for mode in frame['order']:
                question = f'Point to: {QUERY}.' if mode=='point' else f'Locate a single instance that matches the following description: {QUERY}.'
                messages = [{'role': 'user', 'content': [{'type': 'image', 'image': image}, {'type': 'text', 'text': question}]}]
                text = worker.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                images, videos = worker.processor.process_vision_info(messages)
                inputs = worker.processor(text=[text], images=images, videos=videos, return_tensors='pt').to(device)
                input_ids = inputs['input_ids'].detach().cpu().tolist()[0]
                grid = inputs.get('image_grid_hws')
                grid = None if grid is None else grid.detach().cpu().tolist() if hasattr(grid, 'detach') else np.asarray(grid).tolist()
                recorder.record('call_started', {'frame': frame, 'mode': mode, 'question': question,
                                'input_token_ids': input_ids, 'input_token_count': len(input_ids), 'image_grid_hws': grid})
                observed.clear()
                torch.cuda.synchronize(device)
                torch.cuda.reset_peak_memory_stats(device)
                started = time.perf_counter()
                with torch.no_grad():
                    raw = worker.model.generate(pixel_values=inputs['pixel_values'].to(worker.dtype),
                        input_ids=inputs['input_ids'], attention_mask=inputs['attention_mask'],
                        image_grid_hws=inputs.get('image_grid_hws'), tokenizer=worker.tokenizer, **SETTINGS)
                torch.cuda.synchronize(device)
                latency = time.perf_counter()-started
                if len(observed)!=1 or len(observed[0])!=1:
                    raise ValueError('actual generated tokens unavailable')
                raw = raw[0] if isinstance(raw, tuple) else raw
                audit = generation_audit(observed[0][0], len(input_ids), worker.tokenizer.model_max_length,
                                         worker.tokenizer.convert_tokens_to_ids('<|im_end|>'))
                recorder.record('call_completed', {'frame': frame, 'mode': mode, 'raw_output': raw,
                    'parsed': parse_grounding(raw, image.width, image.height), 'generation_audit': audit,
                    'latency_s': latency, 'peak_allocated_bytes': torch.cuda.max_memory_allocated(device),
                    'peak_reserved_bytes': torch.cuda.max_memory_reserved(device)})
        recorder.record('termination', {'reason': 'completed', 'call_count': 2*len(manifest['frames'])})
    except Exception as exc:
        recorder.record('failure', {'reason': repr(exc), 'retries': 0})
        raise
    finally:
        recorder.close()


def evaluate_location(point, depth, k, t, mask, ray_depths):
    from ..vision import camera_to_world, pixel_to_camera
    pixel = pixel_for_point(point, depth.shape[1], depth.shape[0]) if point is not None else None
    if pixel is None:
        return {'status': 'unknown_or_out_of_frame', 'target_member': None}
    x, y = pixel
    ys, xs = np.nonzero(mask)
    distance = float(np.min(np.hypot(xs+.5-point[0], ys+.5-point[1]))) if len(xs) else None
    result = {'status': 'evaluated', 'continuous_xy': point, 'sample_pixel_xy': pixel,
              'target_member': bool(mask[y, x]), 'nearest_target_pixel_distance': distance,
              'point_world_m': None, 'nearest_ray_surface_distance_mm': None}
    z = float(depth[y, x])
    if not np.isfinite(z) or not .01<=z<=5:
        result['depth_status'] = 'invalid'
        return result
    result['depth_status'] = 'valid'
    pos = camera_to_world(pixel_to_camera(x+.5, y+.5, z, k), t)
    result['point_world_m'] = pos.tolist()
    if len(xs):
        zs = np.asarray(ray_depths)
        cloud = np.column_stack(((xs+.5-k[0, 2])*zs/k[0, 0], (ys+.5-k[1, 2])*zs/k[1, 1], zs))
        world = cloud@t[:3, :3].T+t[:3, 3]
        result['nearest_ray_surface_distance_mm'] = float(np.min(np.linalg.norm(world-pos, axis=1))*1000)
    return result


def verified_calls(records):
    """Validate complete records; retain every planned frame and incomplete call."""
    starts = [r['data'] for r in records if r['kind']=='run_start']
    if len(starts)!=1:
        raise ValueError('exactly one run_start required')
    manifest = starts[0]['resolved_config']['safe_input_manifest']
    frames = manifest['frames']
    if len({f['index'] for f in frames})!=len(frames):
        raise ValueError('duplicate planned frame')
    planned = {(f['index'], mode): f for f in frames for mode in f['order']}
    completed, started = {}, {}
    for row in records:
        if row['kind'] not in ('call_started', 'call_completed'):
            continue
        data = row['data']
        key = (data['frame']['index'], data['mode'])
        if key not in planned or data['frame']!=planned[key]:
            raise ValueError('call frame differs from planned manifest')
        target = started if row['kind']=='call_started' else completed
        if key in target:
            raise ValueError('duplicate call record')
        if row['kind']=='call_completed':
            if key not in started:
                raise ValueError('completed call lacks start')
            parsed = parse_grounding(data['raw_output'], planned[key]['width'], planned[key]['height'])
            if parsed!=data['parsed']:
                raise ValueError('stored grounding differs from independent parse')
            audit = data['generation_audit']
            if audit['input_token_count']!=len(started[key]['input_token_ids']):
                raise ValueError('input token count mismatch')
            expected = generation_audit(audit['actual_generated_token_ids'], audit['input_token_count'],
                                        audit['model_max_length'], audit['eos_token_id'])
            if audit!=expected:
                raise ValueError('generation token audit mismatch')
        target[key] = data
    return frames, completed, {
        'planned_calls': len(planned), 'started_calls': len(started), 'completed_calls': len(completed),
        'missing_calls': [{'index': i, 'mode': m, 'started': (i, m) in started} for i, m in planned if (i, m) not in completed],
        'terminations': [r['data'] for r in records if r['kind']=='termination'],
        'failures': [r['data'] for r in records if r['kind']=='failure'],
        'generation_complete_calls': sum(c['generation_audit']['complete_generation'] for c in completed.values()),
    }


def evaluate(run, audit_path, output):
    from .target_referent import _restore_support
    from .perception_support_audit import audit_run
    audit = json.loads(Path(audit_path).read_text())
    for source in audit['runs']:
        checked = audit_run(source['source'])
        if checked['episodes_sha256'] != source['episodes_sha256']:
            raise ValueError('evaluator source log changed')
    source_rows = {(r['run'], r['capture_seq']): r for s in audit['runs'] for r in s['rows']}
    records, diagnostics = load_records(Path(run)/'episodes.jsonl')
    if diagnostics:
        raise ValueError(diagnostics)
    frames, completed, completeness = verified_calls(records)
    results = []
    for frame_id in frames:
        index = frame_id['index']
        calls = {m: completed.get((index, m)) for m in ('box', 'point')}
        source = source_rows[(frame_id['source_run'], frame_id['capture_seq'])]
        if source['frame_sha256']!=frame_id['source_npz_sha256']:
            raise ValueError('generation/evaluation frame mismatch')
        raw, _ = load_records(Path(source['frame_artifact']).parents[1]/'episodes.jsonl')
        ref = next(r['data'] for r in raw if r['record_id']==source['referent_record_id'])
        point_call = calls['point']
        valid_point = (point_call is not None and point_call['parsed']['status']=='single_point'
                       and point_call['generation_audit']['complete_generation'])
        point = point_call['parsed']['points'][0]['continuous_xy'] if valid_point else None
        fresh_boxes = (calls['box']['parsed']['boxes'] if calls['box']
                       and calls['box']['generation_audit']['complete_generation']
                       and calls['box']['parsed']['status'] in ('single_box', 'multiple_boxes') else [])
        fresh = fresh_boxes[0]['continuous_xyxy'] if fresh_boxes else None
        old = source['box_xyxy']
        centers = {'point': point, 'fresh_box_center': None if fresh is None else [(fresh[0]+fresh[2])/2, (fresh[1]+fresh[3])/2],
                   'archived_box_center': [(old[0]+old[2])/2, (old[1]+old[3])/2]}
        with np.load(source['frame_artifact']) as frame:
            mask = _restore_support(ref['oracle'], frame['depth_m'].shape)
            evaluated = {name: evaluate_location(p, frame['depth_m'], frame['intrinsics'], frame['camera_to_world'], mask, ref['oracle']['selected_depths_m']) for name, p in centers.items()}
        results.append({'index': index, 'run': source['run'], 'step': source['environment_step'], 'evaluations': evaluated,
                        'call_statuses': {m: c['parsed']['status'] if c else 'missing_call' for m, c in calls.items()},
                        'generation_audits': {m: c['generation_audit'] if c else None for m, c in calls.items()},
                        'fresh_first_box_float': fresh, 'archived_first_box_int': old,
                        'fresh_box_int_matches_archive': fresh is not None and [int(v) for v in fresh]==old})
    summary = {name: {'target_members': sum(r['evaluations'][name]['target_member'] is True for r in results),
                          'unknown': sum(r['evaluations'][name]['target_member'] is None for r in results)} for name in ('point', 'fresh_box_center', 'archived_box_center')}
    output = Path(output)
    if output.exists():
        raise FileExistsError('Use a fresh evaluation file')
    output.write_text(json.dumps({'source_log_sha256': file_hash(Path(run)/'episodes.jsonl'),
                     'source_audit_sha256': file_hash(audit_path), 'n': len(results), 'completed_calls': len(completed),
                     'completeness': completeness, 'summary': summary, 'rows': results}, indent=2, allow_nan=False)+'\n')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'generate', 'evaluate'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--source')
    parser.add_argument('--audit', default='runs/autonomous-research/perception-support-audit-01/audit.json')
    parser.add_argument('--model-path', default='/home/junhongli/models/huggingface/LocateAnything-3B')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    if args.mode=='prepare':
        prepare(args.output, args.audit)
    elif args.mode=='generate':
        generate(args.source, args.output, args.model_path, args.device)
    else:
        evaluate(args.source, args.audit, args.output)


if __name__=='__main__':
    main()
