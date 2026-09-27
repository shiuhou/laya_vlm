"""Four fixed cold native POINT calls on admitted full RGB; no simulator or LK."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np

from . import task2_closed_empty_point_adapter as adapter
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

native = adapter.native
baseline = native.baseline
ROOT = Path(__file__).resolve().parents[2]
MODULE = 'embodied_runtime.experiments.task2_closed_empty_fresh_point'
VERSION = 'task2-four-cold-full-rgb-point-v1'
PROTOCOL = ROOT / 'docs/research/task2_closed_empty_fresh_point_protocol.md'
BINDING = ROOT / 'docs/evidence/autonomous_research/task2_closed_empty_image_motion_source_binding.json'
BINDING_SHA = '49dbc6e182a6e516e43142537005234c7559264fd69c9f051a10e1b7b4f4d04f'
ADMISSION = ROOT / 'docs/evidence/autonomous_research/task2_closed_empty_scene_independent_audit.json'
ADMISSION_SHA = '57fa52a1ba5ffff73e7e197bbe352fe5f83209397c8cb972736cea389f0d7e42'
ORDER = tuple(row[0] for row in adapter.CASES)
GPU = '2'
_STARTED = False


def source_packet():
    """Read sensor manifests; hash mixed journals and privileged receipts only."""
    adapter.verify_helpers()
    if file_hash(BINDING) != BINDING_SHA or file_hash(ADMISSION) != ADMISSION_SHA:
        raise ValueError('Exact independently qualified composite source required')
    binding = native.read_json(BINDING)
    if (binding['source_admitted'] is not True or binding['source_admission_status'] != 'observational-source-qualified'
            or binding['original_matrix_status'] != 'interrupted_incomplete'):
        raise ValueError('Preserve qualified observations and incomplete original matrix')
    source = Path(binding['source_root'])
    if file_hash(source / 'episodes.jsonl') != binding['matrix_journal_sha256']:
        raise ValueError('Original incomplete matrix journal changed')
    manifests = {}
    for role in ('present', 'away'):
        spec = binding['cells'][role]
        if spec['directory'] != 'neck-' + role or spec['condition'] != 'neck-' + role:
            raise ValueError('Fixed source cells required')
        directory = source / spec['directory']
        for name, expected in spec['sha256'].items():
            if file_hash(directory / name) != expected:
                raise ValueError('Bound source manifest/seal changed')
        rows = native.read_json(directory / 'sensor-captures.json')
        seal = native.read_json(directory / 'sensor-seal.json')
        expected = {'sensor-captures.json': spec['sha256']['sensor-captures.json'],
            'own-controls.json': file_hash(directory / 'own-controls.json'),
            **{r['artifact']: r['artifact_sha256'] for r in rows}}
        if (seal['sha256'] != expected or seal['journal_parse_errors'] or seal['holding'] is not None
                or file_hash(directory / 'episodes.jsonl') != seal['journal_sha256_linkage_only']):
            raise ValueError('Complete original sensor seal required')
        manifests[role] = rows
    images = adapter.select_images(manifests)
    for image in images:
        adapter.load_rgb(source, image)
    return {'source_root': str(source), 'binding_sha256': BINDING_SHA, 'source_admission_sha256': ADMISSION_SHA,
        'original_matrix_status': 'interrupted_incomplete', 'images': images}


def processor_preflight(output):
    """CPU processor/tensor preparation only; never construct model weights."""
    from transformers import AutoProcessor
    import torch
    identity = code_identity()
    if identity['dirty_status'] or os.environ.get('CUDA_VISIBLE_DEVICES') != '' or torch.cuda.is_initialized():
        raise ValueError('Clean freeze and CPU-only processor preflight required')
    source = source_packet()
    model = model_identity(baseline.MODEL)
    if model['content_id'] != baseline.MODEL_CONTENT_ID:
        raise ValueError('Existing checkpoint changed')
    config, references = native.source_config()
    processor = AutoProcessor.from_pretrained(baseline.MODEL, trust_remote_code=True, local_files_only=True)
    inputs = [adapter.prepare_native_input(processor, adapter.load_rgb(source['source_root'], row), row['case_id'])[2]
              for row in source['images']]
    if torch.cuda.is_initialized():
        raise ValueError('Processor preflight initialized CUDA')
    value = {'version': VERSION, 'status': 'pass', 'code': identity, 'protocol_sha256': file_hash(PROTOCOL),
        'source': source, 'conditions': list(ORDER), 'question': adapter.QUESTION, 'settings': native.SETTINGS,
        'model': model, 'source_model_config': config, 'description_provenance': references, 'inputs': inputs,
        'versions': versions(), 'physical_gpu_for_inference': GPU, 'processor_device': 'cpu',
        'model_constructions': 0, 'model_calls': 0, 'physics_calls': 0, 'render_calls': 0}
    baseline.write_json(output, value)
    return value


def load_preflight(path, expected_sha):
    if file_hash(path) != expected_sha:
        raise ValueError('Reviewed processor preflight changed')
    value = native.read_json(path)
    if (value['version'] != VERSION or value['status'] != 'pass' or value['code'] != code_identity()
            or value['protocol_sha256'] != file_hash(PROTOCOL) or value['source'] != source_packet()
            or value['conditions'] != list(ORDER) or value['question'] != adapter.QUESTION
            or value['settings'] != native.SETTINGS or value['model']['content_id'] != baseline.MODEL_CONTENT_ID
            or value['model_constructions'] != 0 or value['model_calls'] != 0
            or value['physical_gpu_for_inference'] != GPU or value['processor_device'] != 'cpu'):
        raise ValueError('Frozen code/configuration/input provenance mismatch')
    return value


def check_review(path, preflight, preflight_sha):
    review = native.read_json(path)
    expected = {'status': 'PASS', 'freeze_commit': preflight['code']['commit'],
        'preflight_sha256': preflight_sha, 'protocol_sha256': file_hash(PROTOCOL),
        'source_admission_sha256': ADMISSION_SHA, 'conditions': list(ORDER),
        'model_calls_authorized': 4, 'physical_gpu': GPU}
    if any(review.get(key) != value for key, value in expected.items()):
        raise ValueError('Exact four-call code/config/input PASS required')


def loaded_configuration(worker, torch):
    return {'model_config': native.serialize_model_config(worker.model.config.to_dict()),
        'dtype': str(worker.dtype), 'parameter_dtype': str(worker.model.dtype), 'model_training': worker.model.training,
        'tokenizer_model_max_length': worker.tokenizer.model_max_length,
        'eos_token_id': worker.tokenizer.convert_tokens_to_ids('<|im_end|>'),
        'physical_gpu': GPU, 'gpu_name': torch.cuda.get_device_name('cuda'),
        'torch_threads': torch.get_num_threads(), 'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
        'vision_attention_implementation': worker.model.config.vision_config._attn_implementation,
        'text_attention_implementation': worker.model.config.text_config._attn_implementation}


def condition_run(batch, case_id):
    global _STARTED
    if _STARTED:
        raise RuntimeError('One cold condition per fresh Python/model process')
    _STARTED = True
    batch = Path(batch)
    request = native.read_json(batch / 'request.json')
    preflight = load_preflight(request['preflight'], request['preflight_sha256'])
    if file_hash(batch / 'review.json') != request['review_sha256']:
        raise ValueError('Prospective review changed')
    check_review(batch / 'review.json', preflight, request['preflight_sha256'])
    rows, errors = load_records(batch / 'episodes.jsonl')
    ordinal = ORDER.index(case_id)
    if (errors or rows[-1]['kind'] != 'condition_intent' or rows[-1]['data'] != {'ordinal': ordinal, 'case_id': case_id}
            or [r['data']['case_id'] for r in rows if r['kind'] == 'condition_intent'] != list(ORDER[:ordinal + 1])
            or os.environ.get('CUDA_VISIBLE_DEVICES') != GPU):
        raise ValueError('Fixed order/budget/GPU batch intent required')
    image_spec = preflight['source']['images'][ordinal]
    output = batch / case_id
    recorder = RunRecorder(output, {'case_id': case_id, 'question': adapter.QUESTION, 'image_source': image_spec,
        'settings': native.SETTINGS, 'seed': 1, 'model_call_budget': 1, 'request_sha256': file_hash(batch / 'request.json')},
        {'run_id': case_id, 'code': code_identity(), 'pid': os.getpid(), 'pgid': os.getpgrp()})
    try:
        rgb = adapter.load_rgb(preflight['source']['source_root'], image_spec)
        np.save(output / 'rgb-input.npy', rgb, allow_pickle=False)
        recorder.record('rgb_input_sealed', {'artifact': 'rgb-input.npy', 'sha256': file_hash(output / 'rgb-input.npy')})
        model = model_identity(baseline.MODEL)
        if model != preflight['model']:
            raise ValueError('Checkpoint bytes changed since preflight')
        from ..adapters.locateanything import LocateAnythingWorker
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        worker = LocateAnythingWorker(baseline.MODEL, device='cuda')
        loaded = loaded_configuration(worker, torch)
        recorder.manifest_update({'model': model, 'loaded': loaded, 'versions': versions()})
        if (loaded['model_config'] != preflight['source_model_config'] or loaded['model_training']
                or loaded['dtype'] != 'torch.bfloat16' or loaded['parameter_dtype'] != 'torch.bfloat16'
                or loaded['tokenizer_model_max_length'] != 16384 or loaded['eos_token_id'] != 151645):
            raise ValueError('Existing loaded model configuration/BF16/eval/tokenizer changed')
        if ordinal and loaded != native.read_json(batch / ORDER[0] / 'manifest.json')['loaded']:
            raise ValueError('Cold model/environment differs from first fixed case')
        inputs, pixels, metadata = adapter.prepare_native_input(worker.processor, rgb, case_id)
        if metadata != preflight['inputs'][ordinal]:
            raise ValueError('Actual native input differs from reviewed CPU preflight')
        np.savez_compressed(output / 'native-input.npz', pixel_values_float32=pixels.float().numpy())
        baseline.write_json(output / 'native-input.json', metadata)
        for name in ('native-input.npz', 'native-input.json'):
            recorder.record('native_input_sealed', {'artifact': name, 'sha256': file_hash(output / name)})
        raw = native.call_once(worker, inputs.to('cuda'), pixels.to('cuda'), output, recorder)
        result = adapter.analyze_rgb_return(raw, len(metadata['input_token_ids']),
            loaded['tokenizer_model_max_length'], loaded['eos_token_id'])
        baseline.write_json(output / 'sensor-result.json', result)
        recorder.record('sensor_result_sealed', {'artifact': 'sensor-result.json',
            'sha256': file_hash(output / 'sensor-result.json'), 'evaluator_opened': False})
        recorder.record('termination', {'reason': 'fixed_rgb_point_condition_complete', 'status': result['status'],
            'model_calls': 1, 'retries': 0, 'physics_calls': 0, 'render_calls': 0})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'retries': 0})
        raise
    finally:
        recorder.close()


def sealed_condition(directory):
    directory = Path(directory)
    rows, errors = load_records(directory / 'episodes.jsonl')
    kinds = [row['kind'] for row in rows]
    if (errors or any(kind == 'failure' for kind in kinds) or kinds[-1] != 'termination'
            or any(kinds.count(kind) != 1 for kind in ('call_started', 'generation_return_sealed', 'sensor_result_sealed'))
            or kinds.index('generation_return_sealed') >= kinds.index('sensor_result_sealed')):
        raise ValueError('One complete raw-before-sensor condition required')
    for row in rows:
        if row['kind'].endswith('_sealed') and file_hash(directory / row['data']['artifact']) != row['data']['sha256']:
            raise ValueError('Condition artifact seal changed')
    metadata = native.read_json(directory / 'native-input.json')
    loaded = native.read_json(directory / 'manifest.json')['loaded']
    result = adapter.analyze_rgb_return(native.read_json(directory / 'generation-return.json'),
        len(metadata['input_token_ids']), loaded['tokenizer_model_max_length'], loaded['eos_token_id'])
    if result != native.read_json(directory / 'sensor-result.json'):
        raise ValueError('Native RGB point analysis recomputation differs')
    return result


def execute_four(recorder, launch):
    results = []
    for ordinal, case_id in enumerate(ORDER):
        recorder.record('condition_intent', {'ordinal': ordinal, 'case_id': case_id})
        launch(case_id)
        result = sealed_condition(recorder.output / case_id)
        results.append({'case_id': case_id, 'status': result['status'],
            'sensor_sha256': file_hash(recorder.output / case_id / 'sensor-result.json')})
        recorder.record('condition_complete', results[-1])
    return results


def generate(output, preflight_path, review_path):
    preflight_sha = file_hash(preflight_path)
    preflight = load_preflight(preflight_path, preflight_sha)
    check_review(review_path, preflight, preflight_sha)
    if os.environ.get('CUDA_VISIBLE_DEVICES') != GPU:
        raise ValueError('Assigned GPU2 required for all four cold calls')
    request = {'version': VERSION, 'preflight': str(Path(preflight_path).resolve()), 'preflight_sha256': preflight_sha,
        'review_sha256': file_hash(review_path), 'conditions': list(ORDER), 'planned_model_calls': 4,
        'fresh_process_per_condition': True, 'seed': 1, 'physical_gpu': GPU, 'retries': 0,
        'protocol_sha256': file_hash(PROTOCOL), 'source_admission_sha256': ADMISSION_SHA}
    recorder = RunRecorder(output, request, {'run_id': Path(output).name, 'code': code_identity(),
        'versions': versions(), 'pid': os.getpid(), 'pgid': os.getpgrp()})
    baseline.write_json(Path(output) / 'request.json', request)
    (Path(output) / 'review.json').write_bytes(Path(review_path).read_bytes())
    (Path(output) / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    def launch(case_id):
        with (Path(output) / (case_id + '.log')).open('x') as stream:
            subprocess.run([sys.executable, '-m', MODULE, 'condition', '--output', str(Path(output).resolve()),
                '--case', case_id], stdout=stream, stderr=subprocess.STDOUT, check=True)
    try:
        results = execute_four(recorder, launch)
        recorder.record('termination', {'reason': 'four_fixed_cold_rgb_points_complete', 'conditions': results,
            'model_calls': 4, 'retries': 0, 'physics_calls': 0, 'render_calls': 0, 'evaluator_opened': False})
    except BaseException as exc:
        recorder.record('failure', {'exception': repr(exc), 'retries': 0, 'remaining_conditions': 'not_run'})
        raise
    finally:
        recorder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'generate', 'condition'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight')
    parser.add_argument('--review')
    parser.add_argument('--case', choices=ORDER)
    args = parser.parse_args()
    if args.mode == 'preflight':
        processor_preflight(args.output)
    elif args.mode == 'generate':
        if not args.preflight or not args.review:
            parser.error('generation requires exact preflight and prospective review')
        generate(args.output, args.preflight, args.review)
    else:
        if not args.case:
            parser.error('condition requires one fixed case')
        condition_run(args.output, args.case)


if __name__ == '__main__':
    main()
