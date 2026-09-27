"""Two fixed, fresh-process native POINT calls; offline sensor/evaluator separation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

import numpy as np

from . import task2_box_support as baseline
from .coarse_point_probe import admit_point
from .point_grounding_probe import SETTINGS, generation_audit, parse_grounding, serialize_model_config
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

VERSION = 'task2-matched-native-point-region-v1'
MODULE = 'embodied_runtime.experiments.task2_point_region_control'
PROTOCOL = baseline.ROOT / 'docs/research/task2_point_region_control_protocol.md'
CONDITIONS = (
    {'condition': 'whole', 'query': 'the wine bottle', 'question': 'Point to: the wine bottle.'},
    {'condition': 'neck', 'query': 'the neck of the wine bottle', 'question': 'Point to: the neck of the wine bottle.'},
)
REFERENCES = (
    ('task2-box-support-run-02', '5b95a3e9e3389e64fcb87d9965cb283507e955dd6254fac769532d9b81b1a87b',
     '6dc6afda0ae46ce4ae15bf9b3aeb638fa50deaa45fd0da1b9e3a6c2bba80fd66'),
    ('task2-neck-box-support-run-01', '49a7f858226515ee7e0c4960e48184195fe414369f812fddc414a6ba50119fcc',
     '23233eed89a0f6312ee9edd58a2683f361e44a2c8a92152cb9138d350efaf23f'),
)
_CONDITION_STARTED = False


def read_json(path):
    return json.loads(Path(path).read_text())


def array_identity(array):
    array = np.asarray(array)
    return {'shape': list(array.shape), 'dtype': str(array.dtype),
            'bytes_sha256': hashlib.sha256(array.tobytes(order='C')).hexdigest()}


def source_config():
    configs, provenance = [], []
    for condition, (name, manifest_sha, config_sha) in zip(CONDITIONS, REFERENCES):
        directory = baseline.SOURCE.parent / name
        for filename, expected in [('manifest.json', manifest_sha), ('resolved_config.yaml', config_sha)]:
            if file_hash(directory / filename) != expected:
                raise ValueError('original BOX configuration identity changed')
        manifest, config = read_json(directory / 'manifest.json'), read_json(directory / 'resolved_config.yaml')
        if (config['question'] != f"Locate a single instance that matches the following description: {condition['query']}."
                or config['settings'] != SETTINGS or manifest['dtype'] != 'torch.bfloat16'
                or manifest['model']['content_id'] != baseline.MODEL_CONTENT_ID):
            raise ValueError('original description/settings/model mismatch')
        configs.append(manifest['model_config'])
        provenance.append({'directory': str(directory), 'manifest_sha256': manifest_sha,
                           'resolved_config_sha256': config_sha, 'original_question': config['question']})
    if configs[0] != configs[1]:
        raise ValueError('original whole and neck loaded model configurations differ')
    return configs[0], provenance


def native_input(processor, rgb, condition):
    """Full RGB and one registered question; no sensor depth or evaluator inputs."""
    from PIL import Image
    import torch
    messages = [{'role': 'user', 'content': [
        {'type': 'image', 'image': Image.fromarray(rgb).convert('RGB')},
        {'type': 'text', 'text': condition['question']}]}]
    text = processor.py_apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    images, videos = processor.process_vision_info(messages)
    inputs = processor(text=[text], images=images, videos=videos, return_tensors='pt')
    if set(inputs) != {'input_ids', 'attention_mask', 'pixel_values', 'image_grid_hws'}:
        raise ValueError('unexpected processor input schema')
    if inputs['input_ids'].shape[0] != 1:
        raise ValueError('one image/question per call required')
    pixels = inputs['pixel_values'].to(torch.bfloat16)
    metadata = {**condition, 'formatted_text': text,
        'input_token_ids': inputs['input_ids'].tolist()[0], 'attention_mask': inputs['attention_mask'].tolist(),
        'image_grid_hws': baseline.grid_metadata(inputs['image_grid_hws']),
        'pixel_values_original_dtype': str(pixels.dtype),
        'pixel_values_float32': array_identity(pixels.float().numpy()),
        'rgb': array_identity(rgb)}
    return inputs, pixels, metadata


def processor_preflight(output):
    """Actual processor and local byte hashing only: never constructs a model."""
    from transformers import AutoProcessor
    identity = code_identity()
    if identity['dirty_status']:
        raise ValueError('freeze clean code before processor preflight')
    model = model_identity(baseline.MODEL)
    if model['content_id'] != baseline.MODEL_CONTENT_ID:
        raise ValueError('checkpoint changed')
    config, references = source_config()
    frame = baseline.sensor_frame()
    processor = AutoProcessor.from_pretrained(baseline.MODEL, trust_remote_code=True, local_files_only=True)
    rows = [native_input(processor, frame['rgb'], condition)[2] for condition in CONDITIONS]
    if rows[0]['pixel_values_float32'] != rows[1]['pixel_values_float32'] or rows[0]['image_grid_hws'] != rows[1]['image_grid_hws']:
        raise ValueError('matched full RGB preprocessing differs across descriptions')
    result = {'version': VERSION, 'status': 'pass', 'code': identity, 'protocol_sha256': file_hash(PROTOCOL),
        'source_frame_sha256': baseline.FRAME_SHA, 'conditions': list(CONDITIONS), 'settings': SETTINGS,
        'model': model, 'source_model_config': config, 'description_provenance': references,
        'inputs': rows, 'model_constructions': 0, 'model_calls': 0, 'physics_calls': 0, 'render_calls': 0}
    baseline.write_json(output, result)
    return result


def load_preflight(path, expected_sha):
    if file_hash(path) != expected_sha:
        raise ValueError('reviewed preflight changed')
    result = read_json(path)
    if (result['version'] != VERSION or result['status'] != 'pass' or result['code'] != code_identity()
            or result['protocol_sha256'] != file_hash(PROTOCOL) or result['conditions'] != list(CONDITIONS)
            or result['source_frame_sha256'] != baseline.FRAME_SHA or result['settings'] != SETTINGS
            or result['model']['content_id'] != baseline.MODEL_CONTENT_ID
            or result['model_constructions'] != 0 or result['model_calls'] != 0):
        raise ValueError('frozen preflight/configuration mismatch')
    return result


def seal_return(output, recorder, raw, observed, latency):
    """Preserve every native return/token before any validation or parsing."""
    normalized = raw[0] if isinstance(raw, tuple) else raw
    data = {'raw_response': normalized if isinstance(normalized, str) else repr(normalized),
            'raw_response_type': type(normalized).__name__, 'returned_value_repr': repr(raw),
            'observed_decoded_token_sequences': observed, 'latency_to_return_s': latency}
    baseline.write_json(Path(output) / 'generation-return.json', data)
    recorder.record('generation_return_sealed', {'artifact': 'generation-return.json',
        'sha256': file_hash(Path(output) / 'generation-return.json')})
    return data


def analyze_return(raw, input_count, model_max_length, eos, frame):
    observed = raw['observed_decoded_token_sequences']
    if raw['raw_response_type'] != 'str' or len(observed) != 1 or len(observed[0]) != 1:
        raise ValueError('native return or actual generated token audit unavailable')
    audit = generation_audit(observed[0][0], input_count, model_max_length, eos)
    parsed = parse_grounding(raw['raw_response'], frame['rgb'].shape[1], frame['rgb'].shape[0])
    result = {'raw_output': raw['raw_response'], 'generation_audit': audit, 'parsed': parsed,
        'status': 'not_admitted', 'point': None, 'reason': None,
        'resolved_depth_ownership': None, 'semantic_confidence': None,
        'semantic_target_identity_verified': False, 'grasp_quality': None,
        'source_frame_sha256': baseline.FRAME_SHA, 'capture_read_time_s': .5,
        'cached_rgb_sample_time_s': None, 'cached_depth_sample_time_s': None,
        'calibration': {k: array_identity(frame[k]) for k in ('intrinsics', 'camera_to_world')},
        'native_point_projection': 'normalized/1000*dimension -> floor -> depth[y,x] -> pixel center +0.5 -> K/T'}
    try:
        result['point'] = admit_point(parsed, audit, frame)
        result['status'] = 'admitted_sensor_point'
    except ValueError as exc:
        if not str(exc).startswith('point_admission:'):
            raise
        result['reason'] = str(exc)
    return result


def call_once(worker, inputs, pixels, output, recorder):
    original, observed = worker.tokenizer.batch_decode, []
    def decode(sequences, *args, **kwargs):
        observed.append(sequences.detach().cpu().tolist())
        return original(sequences, *args, **kwargs)
    def timeout(_signal, _frame):
        raise TimeoutError('single native POINT call exceeded 300s; no retry')
    previous = signal.signal(signal.SIGALRM, timeout)
    worker.tokenizer.batch_decode = decode
    started = time.perf_counter()
    recorder.record('call_started', {'model_call_ordinal': 1, 'timeout_s': 300})
    try:
        signal.alarm(300)
        with worker.torch.no_grad():
            raw = worker.model.generate(pixel_values=pixels, input_ids=inputs['input_ids'],
                attention_mask=inputs['attention_mask'], image_grid_hws=inputs['image_grid_hws'],
                tokenizer=worker.tokenizer, **SETTINGS)
        signal.alarm(0)
        return seal_return(output, recorder, raw, observed, time.perf_counter() - started)
    except BaseException as exc:
        baseline.write_json(Path(output) / 'generation-exception.json', {
            'exception': repr(exc), 'observed_decoded_token_sequences': observed,
            'elapsed_s': time.perf_counter() - started, 'retries': 0})
        recorder.record('generation_exception_sealed', {'artifact': 'generation-exception.json',
            'sha256': file_hash(Path(output) / 'generation-exception.json')})
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
        worker.tokenizer.batch_decode = original


def condition_run(batch, condition_name):
    global _CONDITION_STARTED
    if _CONDITION_STARTED:
        raise RuntimeError('one condition per fresh Python/model process')
    _CONDITION_STARTED = True
    batch = Path(batch)
    request = read_json(batch / 'request.json')
    preflight = load_preflight(request['preflight'], request['preflight_sha256'])
    rows, errors = load_records(batch / 'episodes.jsonl')
    if errors or rows[-1]['kind'] != 'condition_intent' or rows[-1]['data']['condition'] != condition_name:
        raise ValueError('condition requires its registered batch intent')
    condition = next(c for c in CONDITIONS if c['condition'] == condition_name)
    ordinal = list(CONDITIONS).index(condition)
    if [r['data']['condition'] for r in rows if r['kind'] == 'condition_intent'] != [c['condition'] for c in CONDITIONS[:ordinal+1]]:
        raise ValueError('condition budget/order changed')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != request['physical_gpu']:
        raise ValueError('both fresh conditions require the same assigned physical GPU')
    output = batch / condition_name
    recorder = RunRecorder(output, {**condition, 'settings': SETTINGS, 'model_call_budget': 1,
        'seed': 1, 'request_sha256': file_hash(batch / 'request.json'), 'source_frame_sha256': baseline.FRAME_SHA,
        'protocol_sha256': file_hash(PROTOCOL)}, {'run_id': output.name, 'code': code_identity(), 'pid': os.getpid()})
    try:
        frame = baseline.sensor_frame()
        np.save(output / 'rgb-input.npy', frame['rgb'], allow_pickle=False)
        recorder.record('rgb_input_sealed', {'artifact': 'rgb-input.npy', 'sha256': file_hash(output / 'rgb-input.npy')})
        model = model_identity(baseline.MODEL)
        if model != preflight['model']:
            raise ValueError('checkpoint bytes changed since preflight')
        from ..adapters.locateanything import LocateAnythingWorker
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        worker = LocateAnythingWorker(baseline.MODEL, device='cuda')
        loaded = {'model_config': serialize_model_config(worker.model.config.to_dict()),
            'dtype': str(worker.dtype), 'parameter_dtype': str(worker.model.dtype), 'model_training': worker.model.training,
            'tokenizer_model_max_length': worker.tokenizer.model_max_length,
            'eos_token_id': worker.tokenizer.convert_tokens_to_ids('<|im_end|>'),
            'physical_gpu': request['physical_gpu'], 'gpu_name': torch.cuda.get_device_name('cuda'),
            'torch_threads': torch.get_num_threads(), 'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'vision_attention_implementation': worker.model.config.vision_config._attn_implementation,
            'text_attention_implementation': worker.model.config.text_config._attn_implementation}
        recorder.manifest_update({'model': model, 'loaded': loaded, 'versions': versions()})
        if (loaded['model_config'] != preflight['source_model_config'] or loaded['model_training']
                or loaded['dtype'] != 'torch.bfloat16' or loaded['parameter_dtype'] != 'torch.bfloat16'
                or loaded['tokenizer_model_max_length'] != 16384 or loaded['eos_token_id'] != 151645):
            raise ValueError('existing loaded model configuration/BF16/eval/tokenizer changed')
        if ordinal and loaded != read_json(batch / 'whole' / 'manifest.json')['loaded']:
            raise ValueError('fresh condition model/environment differs from whole condition')
        inputs, pixels, metadata = native_input(worker.processor, frame['rgb'], condition)
        if metadata != preflight['inputs'][ordinal]:
            raise ValueError('actual native input differs from reviewed processor preflight')
        np.savez_compressed(output / 'native-input.npz', pixel_values_float32=pixels.float().numpy())
        baseline.write_json(output / 'native-input.json', metadata)
        for name in ('native-input.npz', 'native-input.json'):
            recorder.record('native_input_sealed', {'artifact': name, 'sha256': file_hash(output / name)})
        raw = call_once(worker, inputs.to('cuda'), pixels.to('cuda'), output, recorder)
        result = analyze_return(raw, len(metadata['input_token_ids']), loaded['tokenizer_model_max_length'],
                                loaded['eos_token_id'], frame)
        baseline.write_json(output / 'sensor-result.json', result)
        recorder.record('sensor_result_sealed', {'artifact': 'sensor-result.json',
            'sha256': file_hash(output / 'sensor-result.json'), 'evaluator_opened': False})
        recorder.record('termination', {'reason': 'fixed_condition_complete', 'status': result['status'],
            'model_calls': 1, 'retries': 0, 'physics_calls': 0, 'render_calls': 0})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'retries': 0})
        raise
    finally:
        recorder.close()


def sealed_condition(directory):
    directory = Path(directory)
    rows, errors = load_records(directory / 'episodes.jsonl')
    kinds = [r['kind'] for r in rows]
    if (errors or kinds.count('call_started') != 1 or kinds.count('generation_return_sealed') != 1
            or kinds.count('sensor_result_sealed') != 1 or kinds[-1] != 'termination'
            or kinds.index('generation_return_sealed') >= kinds.index('sensor_result_sealed')):
        raise ValueError('one complete raw-before-sensor condition required')
    for row in rows:
        if row['kind'].endswith('_sealed'):
            if file_hash(directory / row['data']['artifact']) != row['data']['sha256']:
                raise ValueError('condition artifact seal changed')
    metadata, loaded = read_json(directory / 'native-input.json'), read_json(directory / 'manifest.json')['loaded']
    result = analyze_return(read_json(directory / 'generation-return.json'), len(metadata['input_token_ids']),
        loaded['tokenizer_model_max_length'], loaded['eos_token_id'], baseline.sensor_frame())
    if result != read_json(directory / 'sensor-result.json'):
        raise ValueError('strict native point admission/projection recomputation differs')
    return result


def execute_pair(recorder, launch):
    """Fixed two calls; nonadmission proceeds, infrastructure failure stops without retry."""
    results = []
    for ordinal, condition in enumerate(CONDITIONS):
        recorder.record('condition_intent', {'ordinal': ordinal, **condition})
        launch(condition['condition'])
        result = sealed_condition(recorder.output / condition['condition'])
        results.append({'condition': condition['condition'], 'status': result['status'],
                        'sensor_sha256': file_hash(recorder.output / condition['condition'] / 'sensor-result.json')})
        recorder.record('condition_complete', results[-1])
    return results


def generate_pair(output, preflight_path, preflight_sha, physical_gpu):
    load_preflight(preflight_path, preflight_sha)
    if not physical_gpu.isdigit() or os.environ.get('CUDA_VISIBLE_DEVICES') != physical_gpu:
        raise ValueError('one explicitly assigned physical GPU required')
    request = {'version': VERSION, 'preflight': str(Path(preflight_path).resolve()), 'preflight_sha256': preflight_sha,
        'physical_gpu': physical_gpu, 'conditions': list(CONDITIONS), 'planned_model_calls': 2,
        'fresh_process_per_condition': True, 'seed': 1, 'retries': 0, 'protocol_sha256': file_hash(PROTOCOL)}
    recorder = RunRecorder(output, request, {'run_id': Path(output).name, 'code': code_identity(), 'versions': versions()})
    baseline.write_json(Path(output) / 'request.json', request)
    (Path(output) / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    def launch(condition):
        with (Path(output) / f'{condition}.log').open('x') as stream:
            subprocess.run([sys.executable, '-m', MODULE, 'generate-condition', '--output', str(Path(output).resolve()),
                '--condition', condition], stdout=stream, stderr=subprocess.STDOUT, check=True)
    try:
        results = execute_pair(recorder, launch)
        recorder.record('termination', {'reason': 'fixed_pair_complete', 'conditions': results,
            'model_calls': 2, 'retries': 0, 'physics_calls': 0, 'render_calls': 0, 'evaluator_opened': False})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'retries': 0, 'remaining_conditions': 'not_run'})
        raise
    finally:
        recorder.close()


def evaluate(output):
    """Open the archived whole-bottle proxy only after both sensor outputs seal."""
    output = Path(output)
    rows, errors = load_records(output / 'episodes.jsonl')
    if (errors or rows[-1]['kind'] != 'termination' or rows[-1]['data']['reason'] != 'fixed_pair_complete'
            or [r['data']['condition'] for r in rows if r['kind'] == 'condition_complete'] != ['whole', 'neck']):
        raise ValueError('both fixed condition rows must seal before evaluator access')
    sensors = [sealed_condition(output / c['condition']) for c in CONDITIONS]
    directory = output / 'evaluation'
    directory.mkdir(exist_ok=False)
    baseline.write_json(directory / 'evaluation-start.json', {'source_journal_sha256': file_hash(output / 'episodes.jsonl'),
        'sensor_sha256': {c['condition']: file_hash(output / c['condition'] / 'sensor-result.json') for c in CONDITIONS},
        'labels_opened': False})
    mask_path = baseline.SOURCE / 'evaluator-only/close-0000-bottle-mask.npy'
    if file_hash(mask_path) != baseline.MASK_SHA:
        raise ValueError('archived rendered proxy changed')
    mask = np.load(mask_path, allow_pickle=False)
    if mask.dtype != np.bool_ or mask.shape != (384, 384):
        raise ValueError('unexpected evaluator proxy schema')
    strata = baseline.proxy_strata(mask)
    results = []
    for condition, sensor in zip(CONDITIONS, sensors):
        point = sensor['point']
        pixel = None if point is None else point['sample_pixel_xy']
        results.append({**condition, 'sensor_status': sensor['status'], 'sample_pixel_xy': pixel,
            'whole_bottle_rendered_proxy_membership': None if pixel is None else bool(mask[pixel[1], pixel[0]]),
            'proxy_stratum': None if pixel is None else next(k for k, v in strata.items() if v[pixel[1], pixel[0]]),
            'resolved_depth_ownership': None, 'neck_membership': None, 'grasp_quality': None})
    baseline.write_json(directory / 'proxy-analysis.json', {'mask_sha256': baseline.MASK_SHA, 'conditions': results,
        'limitation': 'Whole-bottle rendered membership proxy only; no neck label or resolved-depth ownership.',
        'actual_rgb_inspection': 'pending separate human/model visual receipt; no automatic semantic judgment'})
    plot_rgb(baseline.sensor_frame()['rgb'], sensors, directory / 'actual-rgb-points.png')
    baseline.write_json(directory / 'artifacts.json', {p.name: file_hash(p) for p in sorted(directory.iterdir()) if p.is_file()})
    return results


def plot_rgb(rgb, sensors, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    axes[0].imshow(rgb)
    axes[0].set_title('Actual full RGB')
    for axis, condition, sensor in zip(axes[1:], CONDITIONS, sensors):
        axis.imshow(rgb)
        if sensor['point'] is not None:
            x, y = sensor['point']['sample_pixel_xy']
            axis.scatter([x], [y], s=100, marker='+', c='cyan', linewidths=1.5)
        axis.set_title(condition['query'] + '\n' + sensor['status'])
    for axis in axes:
        axis.set_xlim(-.5, rgb.shape[1]-.5)
        axis.set_ylim(rgb.shape[0]-.5, -.5)
        axis.set_xlabel('Image column')
        axis.set_ylabel('Image row')
    fig.suptitle('Two native POINT conditions; no grasp or depth-ownership claim')
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['processor-preflight', 'generate-pair', 'generate-condition', 'evaluate'])
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight')
    parser.add_argument('--preflight-sha256')
    parser.add_argument('--physical-gpu')
    parser.add_argument('--condition', choices=['whole', 'neck'])
    args = parser.parse_args()
    if args.mode == 'processor-preflight':
        processor_preflight(args.output)
    elif args.mode == 'generate-pair':
        if not all((args.preflight, args.preflight_sha256, args.physical_gpu)):
            parser.error('generate-pair requires preflight, reviewed SHA256 and physical GPU')
        generate_pair(args.output, args.preflight, args.preflight_sha256, args.physical_gpu)
    elif args.mode == 'generate-condition':
        if args.condition is None:
            parser.error('condition required')
        condition_run(args.output, args.condition)
    else:
        evaluate(args.output)


if __name__ == '__main__':
    main()
