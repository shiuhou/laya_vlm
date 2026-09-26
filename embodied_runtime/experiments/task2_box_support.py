"""One fixed Task2 BOX call and sealed support analysis; no scene pipeline."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time

import numpy as np

from ..vision import LocateAnythingProvider, depth_statistics
from .point_grounding_probe import SETTINGS, generation_audit, parse_grounding, serialize_model_config
from .records import RunRecorder, code_identity, file_hash, jsonable, load_records, model_identity, versions

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/interaction-observability-paired-01')
FRAME_SHA = '3753552576da3254ecac0e061bc75910be598550b6efd1d2415f76710aa27969'
MASK_SHA = '2a474be6d469dc2df45edfb03c97b23a1adf021f9a48551994a619f501a0b747'
PROTOCOL = ROOT / 'docs/research/task2_initial_grasp_geometry_proposal.md'
QUERY = 'the wine bottle'
QUESTION = f'Locate a single instance that matches the following description: {QUERY}.'
MODEL = '/home/junhongli/models/huggingface/LocateAnything-3B'
MODEL_CONTENT_ID = '4b5384cddedaa8d10e7205536ebde4893d8e20c396ad861dda2a32ed3bbcd10f'
SENSOR_KEYS = {'rgb', 'depth_m', 'intrinsics', 'camera_to_world'}


def write_json(path, value):
    with Path(path).open('x') as f:
        json.dump(jsonable(value), f, indent=2, allow_nan=False)
        f.write('\n')


def sensor_frame():
    path = SOURCE / 'close/0000.npz'
    if file_hash(path) != FRAME_SHA:
        raise ValueError('initial RGB-D changed')
    with np.load(path, allow_pickle=False) as frame:
        return {k: frame[k].copy() for k in SENSOR_KEYS}


def admitted_box(raw, audit, width, height):
    parsed = parse_grounding(raw, width, height)
    if (not audit['complete_generation'] or not 0 < audit['actual_generated_token_count'] <= 256
            or parsed['status'] != 'single_box'):
        return None, parsed
    return parsed['boxes'][0]['continuous_xyxy'], parsed


def interior_bounds(shape, box):
    """Same clipping/integer conversion and interior slice as depth_statistics."""
    h, w = shape
    x1, y1, x2, y2 = map(int, box)
    x1, x2 = max(0, min(w, x1)), max(0, min(w, x2))
    y1, y2 = max(0, min(h, y1)), max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    px, py = max(1, (x2-x1)//5), max(1, (y2-y1)//5)
    return [x1+px, y1+py, min(x2-px, x2), min(y2-py, y2)]


def sensor_representation(frame, box):
    """Pure sensor input: no paths, evaluator masks or successful context."""
    if set(frame) != SENSOR_KEYS:
        raise ValueError('unexpected sensor input fields')
    rgb, depth = np.asarray(frame['rgb']), np.asarray(frame['depth_m'])
    k, transform = np.asarray(frame['intrinsics']), np.asarray(frame['camera_to_world'])
    if (rgb.dtype != np.uint8 or rgb.shape != (*depth.shape, 3)
            or depth.ndim != 2 or k.shape != (3, 3) or transform.shape != (4, 4)
            or not np.isfinite(k).all() or not np.isfinite(transform).all()
            or k[0, 0] <= 0 or k[1, 1] <= 0):
        raise ValueError('sensor shapes/calibration invalid')
    box = list(map(int, box))
    bounds = interior_bounds(depth.shape, box)
    selected = np.zeros(depth.shape, bool)
    if bounds is not None:
        x1, y1, x2, y2 = bounds
        selected[y1:y2, x1:x2] = True
    selected &= np.isfinite(depth) & (depth >= .01) & (depth <= 5.)
    ys, xs = np.nonzero(selected)
    values = depth[ys, xs]
    stats = depth_statistics(depth, tuple(box))
    result = {'status': 'unknown_empty_valid_crop', 'box_xyxy': box, 'crop_xyxy': bounds,
              'shape': list(depth.shape), 'point_P': None, 'depth_statistics': stats,
              'support_G': [], 'median_contributor_indices': {'lower': [], 'upper': []},
              'resolved_depth_ownership': None, 'support_is_segmentation': False,
              'support_pixel_center_offset': .5, 'min_depth_m': None, 'max_depth_m': None,
              'center_sample': None}
    if not len(values):
        return result
    provider = LocateAnythingProvider(lambda *_: None, k)
    event = provider.observe(rgb, depth, QUERY, episode_id='offline-task2', source_seq=0,
                            capture_sim_time=.5, camera_to_world_matrix=transform,
                            inference_result={'boxes_xyxy': [box]})
    if event is None:
        raise ValueError('provider/support validity disagrees')
    result['point_P'] = {name: event.value[name] for name in ('position_camera_m', 'position_world_m', 'box_xyxy')}
    z = values.astype(np.float64)
    camera = np.column_stack(((xs+.5-k[0, 2])*z/k[0, 0], (ys+.5-k[1, 2])*z/k[1, 1], z))
    world = camera @ transform[:3, :3].T + transform[:3, 3]
    result['support_G'] = [{'pixel_xy': [int(x), int(y)], 'rgb': rgb[y, x].tolist(),
                            'depth_m': float(depth[y, x]), 'position_world_m': p.tolist()}
                           for x, y, p in zip(xs, ys, world)]
    ordered = np.sort(values)
    for name, rank in (('lower', (len(values)-1)//2), ('upper', len(values)//2)):
        result['median_contributor_indices'][name] = np.flatnonzero(values == ordered[rank]).tolist()
    u, v = (box[0]+box[2])/2., (box[1]+box[3])/2.
    x, y = math.floor(u), math.floor(v)
    center = {'continuous_xy': [u, v], 'sample_pixel_xy': None, 'depth_m': None,
              'depth_valid': False, 'depth_minus_median_m': None}
    if 0 <= x < depth.shape[1] and 0 <= y < depth.shape[0]:
        center['sample_pixel_xy'] = [x, y]
        value = float(depth[y, x])
        if np.isfinite(value):
            center.update(depth_m=value, depth_valid=.01 <= value <= 5.,
                          depth_minus_median_m=value-stats['median_m'])
    result.update(status='candidate_support_recorded', min_depth_m=float(values.min()),
                  max_depth_m=float(values.max()), center_sample=center)
    return result


def proxy_strata(mask):
    """Existing rendered-mask strata only; no resolved-depth ownership claim."""
    mask = np.asarray(mask)
    if mask.ndim != 2 or mask.dtype != np.bool_:
        raise ValueError('boolean rendered membership proxy required')
    h, w = mask.shape
    padded = np.pad(mask, 1, constant_values=False)
    shifts = [padded[y:y+h, x:x+w] for y in range(3) for x in range(3)]
    interior = np.logical_and.reduce(shifts)
    dilation = np.logical_or.reduce(shifts)
    return {'proxy_interior': interior, 'proxy_boundary_band': dilation & ~interior,
            'proxy_exterior': ~dilation}


def evaluate_proxy(sensor, mask):
    if list(mask.shape) != sensor['shape']:
        raise ValueError('proxy/sensor shape differs')
    strata = proxy_strata(mask)
    xy = [r['pixel_xy'] for r in sensor['support_G']]
    labels = [bool(mask[y, x]) for x, y in xy]
    n, hits, visible = len(xy), sum(labels), int(mask.sum())
    def membership(indices):
        vals = [labels[i] for i in indices]
        return {'count': len(vals), 'rendered_proxy_agreement_count': sum(vals),
                'rendered_proxy_agreement_fraction': sum(vals)/len(vals) if vals else None}
    center = sensor['center_sample']
    pixel = None if center is None else center['sample_pixel_xy']
    return {'evaluator': 'archived_ID_rendered_membership_proxy',
            'resolved_depth_ownership': None, 'semantic_confidence': None,
            'selected_count': n, 'proxy_visible_count': visible,
            'selected_proxy_overlap_count': hits,
            'selected_proxy_overlap_fraction': hits/n if n else None,
            'proxy_visible_coverage_fraction': hits/visible if visible else None,
            'selected_strata_counts': {name: sum(bool(m[y, x]) for x, y in xy) for name, m in strata.items()},
            'median_contributors': {name: membership(ids) for name, ids in sensor['median_contributor_indices'].items()},
            'center_pixel_proxy_membership': None if pixel is None else bool(mask[pixel[1], pixel[0]]),
            'selected_pixel_proxy_membership': labels,
            'limitations': ['MSAA_depth_label_ownership_ambiguity', 'shared_synthetic_calibration',
                            'cached_sample_times_unknown', 'no_label_based_sensor_cleanup']}


def generate(output):
    from PIL import Image
    from ..adapters.locateanything import LocateAnythingWorker
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('freeze clean code before model call')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '0':
        raise ValueError('fixed GPU0 assignment required')
    frame = sensor_frame()
    recorder = RunRecorder(output, {'question': QUESTION, 'settings': SETTINGS,
        'protocol_sha256': file_hash(PROTOCOL), 'source_frame_sha256': FRAME_SHA,
        'model_call_budget': 1, 'timeout_s': 300, 'initial_image_previously_inspected': True,
        'expected_model_content_id': MODEL_CONTENT_ID},
        {'run_id': Path(output).name, 'code': identity, 'versions': versions(),
         'environment': {k: os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES', 'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')}})
    output = Path(output)
    (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
    calls = 0
    try:
        model = model_identity(MODEL)
        recorder.manifest_update({'model': model})
        if model['content_id'] != MODEL_CONTENT_ID:
            raise ValueError('existing checkpoint identity changed; no model call')
        np.save(output/'rgb-input.npy', frame['rgb'], allow_pickle=False)
        recorder.record('rgb_input_sealed', {'artifact': 'rgb-input.npy', 'sha256': file_hash(output/'rgb-input.npy'),
                                           'rgb_bytes_sha256': hashlib.sha256(frame['rgb'].tobytes()).hexdigest()})
        worker = LocateAnythingWorker(MODEL, device='cuda')
        torch = worker.torch
        recorder.manifest_update({'model_config': serialize_model_config(worker.model.config.to_dict()),
                                 'gpu': torch.cuda.get_device_name('cuda'), 'dtype': str(worker.dtype)})
        image = Image.fromarray(frame['rgb']).convert('RGB')
        messages = [{'role': 'user', 'content': [{'type': 'image', 'image': image}, {'type': 'text', 'text': QUESTION}]}]
        text = worker.processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        images, videos = worker.processor.process_vision_info(messages)
        inputs = worker.processor(text=[text], images=images, videos=videos, return_tensors='pt').to('cuda')
        ids = inputs['input_ids'].detach().cpu().tolist()[0]
        pixels = inputs['pixel_values'].to(worker.dtype)
        grid = inputs.get('image_grid_hws')
        grid_list = (None if grid is None else grid.detach().cpu().tolist()
                     if hasattr(grid, 'detach') else np.asarray(grid).tolist())
        original_decode, observed = worker.tokenizer.batch_decode, []
        def audit_decode(sequences, *args, **kwargs):
            observed.append(sequences.detach().cpu().tolist())
            return original_decode(sequences, *args, **kwargs)
        worker.tokenizer.batch_decode = audit_decode
        def timeout(_signum, _frame):
            raise TimeoutError('single inference exceeded300s; no retry')
        old_handler = signal.signal(signal.SIGALRM, timeout)
        recorder.record('call_started', {'question': QUESTION, 'input_token_ids': ids,
            'image_grid_hws': grid_list, 'pixel_shape': list(pixels.shape), 'pixel_dtype': str(pixels.dtype),
            'pixel_bytes_sha256': hashlib.sha256(pixels.contiguous().view(torch.uint8).cpu().numpy().tobytes()).hexdigest()})
        calls += 1
        started = time.perf_counter()
        signal.alarm(300)
        try:
            with torch.no_grad():
                raw = worker.model.generate(pixel_values=pixels, input_ids=inputs['input_ids'],
                    attention_mask=inputs['attention_mask'], image_grid_hws=inputs.get('image_grid_hws'),
                    tokenizer=worker.tokenizer, **SETTINGS)
            # Preserve the actual response even if token auditing or parsing fails.
            normalized = raw[0] if isinstance(raw, tuple) else raw
            write_json(output/'generation-return.json', {
                'raw_response': normalized if isinstance(normalized, str) else repr(normalized),
                'raw_response_type': type(normalized).__name__, 'returned_value_repr': repr(raw),
                'observed_decoded_token_sequences': observed,
                'latency_to_return_s': time.perf_counter()-started})
            recorder.record('generation_return_sealed', {'artifact': 'generation-return.json',
                'sha256': file_hash(output/'generation-return.json')})
            torch.cuda.synchronize()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        raw = normalized
        if len(observed) != 1 or len(observed[0]) != 1:
            raise ValueError('actual generated token audit missing')
        audit = generation_audit(observed[0][0], len(ids), worker.tokenizer.model_max_length,
                                 worker.tokenizer.convert_tokens_to_ids('<|im_end|>'))
        box, parsed = admitted_box(raw, audit, image.width, image.height)
        model_output = {'raw_output': raw, 'generation_audit': audit, 'parsed': parsed,
                        'latency_s': time.perf_counter()-started, 'admitted_box': box}
        write_json(output/'model-output.json', model_output)
        recorder.record('model_output_sealed', {'artifact': 'model-output.json', 'sha256': file_hash(output/'model-output.json')})
        if box is None:
            recorder.record('termination', {'reason': 'grounding_not_admitted', 'model_calls': calls,
                                           'physics_calls': 0, 'renders': 0, 'retries': 0})
            return
        result = sensor_representation(frame, box)
        write_json(output/'sensor-representation.json', result)
        recorder.record('sensor_outputs_sealed', {'artifact': 'sensor-representation.json',
            'sha256': file_hash(output/'sensor-representation.json'), 'status': result['status'],
            'selected_count': len(result['support_G']), 'evaluator_opened': False})
        recorder.record('termination', {'reason': 'sensor_outputs_complete', 'model_calls': calls,
                                       'physics_calls': 0, 'renders': 0, 'retries': 0})
    except Exception as exc:
        recorder.record('failure', {'reason': repr(exc), 'model_calls_started': calls, 'retries': 0})
        raise
    finally:
        recorder.close()


def sealed_sensor(output):
    output = Path(output)
    rows, errors = load_records(output/'episodes.jsonl')
    if errors:
        raise ValueError(errors)
    kinds = [r['kind'] for r in rows]
    if kinds.count('call_started') != 1 or kinds.count('model_output_sealed') != 1 or kinds.count('sensor_outputs_sealed') != 1:
        raise ValueError('one complete sealed model/sensor result required')
    if kinds.index('model_output_sealed') >= kinds.index('sensor_outputs_sealed') or kinds[-1] != 'termination':
        raise ValueError('seal order differs')
    for r in rows:
        if r['kind'].endswith('_sealed'):
            d = r['data']
            if file_hash(output/d['artifact']) != d['sha256']:
                raise ValueError('artifact seal changed')
    model = json.loads((output/'model-output.json').read_text())
    box, _ = admitted_box(model['raw_output'], model['generation_audit'], 384, 384)
    sensor = json.loads((output/'sensor-representation.json').read_text())
    if sensor_representation(sensor_frame(), box) != sensor:
        raise ValueError('sensor recomputation differs')
    return sensor


def evaluate(output):
    output = Path(output)
    sensor = sealed_sensor(output)
    directory = output/'evaluation'
    directory.mkdir(exist_ok=False)
    write_json(directory/'evaluation-start.json', {'wall_time_unix_s': time.time(),
        'source_journal_sha256': file_hash(output/'episodes.jsonl'),
        'sensor_sha256': file_hash(output/'sensor-representation.json'), 'labels_opened': False})
    mask_path = SOURCE/'evaluator-only/close-0000-bottle-mask.npy'
    if file_hash(mask_path) != MASK_SHA:
        raise ValueError('rendered membership proxy changed')
    proxy = np.load(mask_path, allow_pickle=False)
    result = evaluate_proxy(sensor, proxy)
    result.update(sensor_sha256=file_hash(output/'sensor-representation.json'), mask_sha256=MASK_SHA,
                  source_journal_sha256=file_hash(output/'episodes.jsonl'))
    write_json(directory/'proxy-analysis.json', result)
    plot(sensor_frame(), sensor, proxy, directory/'diagnostic.png')
    write_json(directory/'artifacts.json', {p.name: file_hash(p) for p in directory.iterdir() if p.is_file()})
    print(json.dumps({k: v for k, v in result.items() if k != 'selected_pixel_proxy_membership'}, indent=2))


def plot(frame, sensor, proxy, target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8))
    rgb = frame['rgb']
    axes[0].imshow(rgb)
    for coords, color, label in ((sensor['box_xyxy'], 'orange', 'Model BOX'), (sensor['crop_xyxy'], 'cyan', 'Fixed depth crop')):
        if coords is not None:
            x1, y1, x2, y2 = coords
            axes[0].add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False, edgecolor=color, linewidth=1.5, label=label))
    axes[0].legend(fontsize=8, loc='lower left')
    axes[0].set_title('Actual RGB + unchanged BOX/crop')
    shown = np.full(frame['depth_m'].shape, np.nan)
    for row in sensor['support_G']:
        x, y = row['pixel_xy']
        shown[y, x] = row['depth_m']
    im = axes[1].imshow(shown, cmap='viridis')
    if sensor['crop_xyxy'] is not None:
        x1, y1, x2, y2 = sensor['crop_xyxy']
        if x2 > x1 and y2 > y1:
            axes[1].set_xlim(x1-.5, x2-.5); axes[1].set_ylim(y2-.5, y1-.5)
    fig.colorbar(im, ax=axes[1], shrink=.7, label='Depth (m)')
    axes[1].set_title('All valid selected depths')
    overlay = rgb.astype(float)/255
    overlay[proxy] = .5*overlay[proxy]+.5*np.array([1., 0., 1.])
    axes[2].imshow(overlay)
    axes[2].set_title('EVALUATOR rendered-mask proxy\nNot resolved-depth ownership')
    for ax in axes:
        ax.set_xlabel('Image x'); ax.set_ylabel('Image y')
    fig.suptitle('One inspected Task2 initial fixture; no sensor cleanup from labels')
    fig.tight_layout()
    fig.savefig(target, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['generate', 'evaluate', 'audit'])
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.mode == 'generate':
        generate(args.output)
    elif args.mode == 'evaluate':
        evaluate(args.output)
    else:
        sensor = sealed_sensor(args.output)
        print(json.dumps({'status': 'pass', 'selected_count': len(sensor['support_G']), 'model_calls': 1,
                          'physics_calls': 0, 'render_calls': 0}))


if __name__ == '__main__':
    main()
