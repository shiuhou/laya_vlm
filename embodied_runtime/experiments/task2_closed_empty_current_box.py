"""Two current full-RGB native BOX calls; no depth or policy execution."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np

from . import task2_closed_empty_slow_point as slow
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

hybrid = slow.hybrid
adapter = hybrid.adapter
native = adapter.native
baseline = native.baseline
ROOT = Path(__file__).resolve().parents[2]
MODULE = 'embodied_runtime.experiments.task2_closed_empty_current_box'
VERSION = 'task2-two-cold-current-box-v1'
PROTOCOL = ROOT / 'docs/research/task2_closed_empty_current_box_protocol.md'
ORDER = ('present-postevent', 'away-postevent')
GPU = '2'
RAW = baseline.SOURCE.parent
POINT_RUN = RAW / 'task2-closed-empty-slow-point-run-01'
POINT_PREFLIGHT = RAW / 'task2-closed-empty-slow-point-preflight-01.json'
POINT_PREFLIGHT_SHA = '35ff93678d77b147bf1f5e0f4767de9ea2e62d915e2f2db3526eeeece2ce1903'
POINT_AUDIT = ROOT / 'docs/evidence/autonomous_research/task2_closed_empty_slow_point_independent_audit.json'
POINT_AUDIT_SHA = 'e034ead7baad4f3dd24bb992aa556897563e08d5fb9cae034fd93485d575c251'
SETTINGS = dict(slow.HYBRID_SETTINGS)
QUESTION = baseline.QUESTION
_STARTED = False


def verify_helpers():
    slow.verify_helpers()
    if (file_hash(slow.__file__) != '6416abcf0c990864efea5a6c29677d5c137c3eff73d3847be78cbee953050a31'
            or native.SETTINGS != SETTINGS or SETTINGS != slow.HYBRID_SETTINGS
            or QUESTION != 'Locate a single instance that matches the following description: the wine bottle.'):
        raise ValueError('Unchanged native BOX helpers/question/hybrid settings required')


def point_packet():
    """Bind both current images and separately sealed fresh slow POINTs."""
    verify_helpers()
    if file_hash(POINT_PREFLIGHT) != POINT_PREFLIGHT_SHA or file_hash(POINT_AUDIT) != POINT_AUDIT_SHA:
        raise ValueError('Exact audited current POINT source required')
    old = native.read_json(POINT_PREFLIGHT)
    audit = native.read_json(POINT_AUDIT)
    source = hybrid.source_packet()
    source = {**source, 'images': source['images'][:2]}
    if (audit['status'] != 'PASS' or audit['raw_directory'] != str(POINT_RUN)
            or file_hash(POINT_RUN / 'episodes.jsonl') != audit['journal_sha256']
            or old['source'] != source or old['conditions'] != list(ORDER)):
        raise ValueError('Current POINT and physical source binding mismatch')
    cases = []
    for ordinal, case_id in enumerate(ORDER):
        directory = POINT_RUN / case_id
        spec = audit['conditions'][ordinal]
        for name, key in (('manifest.json', 'manifest_sha256'), ('sensor-result.json', 'sensor_sha256'),
                          ('native-input.json', 'native_input_sha256')):
            if file_hash(directory / name) != spec[key]:
                raise ValueError('Current POINT case bytes changed')
        result = hybrid.sealed_condition(directory)
        metadata = native.read_json(directory / 'native-input.json')
        manifest = native.read_json(directory / 'manifest.json')
        if (spec['case_id'] != case_id or result['status'] != 'admitted_rgb_point'
                or metadata != old['inputs'][ordinal] or manifest['versions'] != old['versions']):
            raise ValueError('Exact admitted current POINT and input required')
        cases.append({'case_id': case_id, 'sensor_sha256': spec['sensor_sha256'],
            'loaded': manifest['loaded']})
    packet = {'directory': str(POINT_RUN), 'preflight_sha256': POINT_PREFLIGHT_SHA,
        'audit_sha256': POINT_AUDIT_SHA, 'journal_sha256': audit['journal_sha256'], 'cases': cases}
    return packet, old


def prepare_native_input(processor, rgb, case_id):
    if case_id not in ORDER or rgb.dtype != np.uint8 or rgb.shape != (384, 384, 3):
        raise ValueError('One registered full native RGB required')
    return native.native_input(processor, rgb, {'condition': case_id,
        'query': baseline.QUERY, 'question': QUESTION})


def same_visual_input(current, point):
    return all(current[key] == point[key] for key in
        ('rgb', 'image_grid_hws', 'pixel_values_original_dtype', 'pixel_values_float32'))


def analyze_box_return(raw, input_count, model_max_length, eos):
    """Existing strict whole-return BOX admission; no support or goal extraction."""
    observed = raw['observed_decoded_token_sequences']
    if raw['raw_response_type'] != 'str' or len(observed) != 1 or len(observed[0]) != 1:
        raise ValueError('Native return or actual generated token audit unavailable')
    audit = native.generation_audit(observed[0][0], input_count, model_max_length, eos)
    box, parsed = baseline.admitted_box(raw['raw_response'], audit, 384, 384)
    return {'raw_output': raw['raw_response'], 'generation_audit': audit, 'parsed': parsed,
        'status': 'admitted_rgb_box' if box is not None else 'not_admitted', 'admitted_box': box,
        'depth_read': False, 'holding': None, 'semantic_target_identity_verified': False,
        'support_extracted': False, 'box_median_goal_created': False}


def call_once(worker, inputs, pixels, output, recorder):
    verify_helpers()
    baseline.write_json(output / 'generation-settings.json', SETTINGS)
    recorder.record('generation_settings_sealed', {'artifact': 'generation-settings.json',
        'sha256': file_hash(output / 'generation-settings.json')})
    return native.call_once(worker, inputs, pixels, output, recorder)


def processor_preflight(output):
    """CPU processor/tensor preparation only; never construct model weights."""
    from transformers import AutoProcessor
    import torch
    identity = code_identity()
    if identity['dirty_status'] or os.environ.get('CUDA_VISIBLE_DEVICES') != '' or torch.cuda.is_initialized():
        raise ValueError('Clean freeze and CPU-only processor preflight required')
    reference, old = point_packet()
    source = {**old['source'], 'images': old['source']['images'][:2]}
    model = model_identity(baseline.MODEL)
    if model['content_id'] != baseline.MODEL_CONTENT_ID:
        raise ValueError('Existing checkpoint changed')
    config, references = native.source_config()
    original_versions = native.read_json(Path(references[0]['directory']) / 'manifest.json')['versions']
    if (versions() != original_versions or versions() != old['versions']
            or config != old['source_model_config'] or model != old['model']):
        raise ValueError('Exact archived native POINT model environment required')
    processor = AutoProcessor.from_pretrained(baseline.MODEL, trust_remote_code=True, local_files_only=True)
    inputs = [prepare_native_input(processor, adapter.load_rgb(source['source_root'], row), row['case_id'])[2]
              for row in source['images']]
    if not all(same_visual_input(row, point) for row, point in zip(inputs, old['inputs'])):
        raise ValueError('BOX visual tensors differ from current POINT source')
    if torch.cuda.is_initialized():
        raise ValueError('Processor preflight initialized CUDA')
    value = {'version': VERSION, 'status': 'pass', 'code': identity, 'protocol_sha256': file_hash(PROTOCOL),
        'source': source, 'point_reference': reference, 'conditions': list(ORDER),
        'question': QUESTION, 'settings': SETTINGS,
        'model': model, 'source_model_config': config, 'description_provenance': references, 'inputs': inputs,
        'versions': versions(), 'physical_gpu_for_inference': GPU, 'processor_device': 'cpu',
        'model_constructions': 0, 'model_calls': 0, 'physics_calls': 0, 'render_calls': 0}
    baseline.write_json(output, value)
    return value


def load_preflight(path, expected_sha):
    if file_hash(path) != expected_sha:
        raise ValueError('Reviewed processor preflight changed')
    value = native.read_json(path)
    reference, old = point_packet()
    source = {**old['source'], 'images': old['source']['images'][:2]}
    if (value['version'] != VERSION or value['status'] != 'pass' or value['code'] != code_identity()
            or value['protocol_sha256'] != file_hash(PROTOCOL) or value['source'] != source
            or value['point_reference'] != reference or len(value['inputs']) != 2
            or not all(same_visual_input(row, point) for row, point in zip(value['inputs'], old['inputs']))
            or value['conditions'] != list(ORDER) or value['question'] != QUESTION
            or value['settings'] != SETTINGS or value['model']['content_id'] != baseline.MODEL_CONTENT_ID
            or value['model_constructions'] != 0 or value['model_calls'] != 0
            or value['physical_gpu_for_inference'] != GPU or value['processor_device'] != 'cpu'
            or value['versions'] != versions()):
        raise ValueError('Frozen code/configuration/input provenance mismatch')
    return value


def check_review(path, preflight, preflight_sha):
    review = native.read_json(path)
    expected = {'status': 'PASS', 'freeze_commit': preflight['code']['commit'],
        'preflight_sha256': preflight_sha, 'protocol_sha256': file_hash(PROTOCOL),
        'source_admission_sha256': hybrid.ADMISSION_SHA, 'conditions': list(ORDER),
        'model_calls_authorized': 2, 'physical_gpu': GPU, 'generation_settings': SETTINGS,
        'point_preflight_sha256': POINT_PREFLIGHT_SHA, 'point_audit_sha256': POINT_AUDIT_SHA}
    if any(review.get(key) != value for key, value in expected.items()):
        raise ValueError('Exact two-call current BOX code/config/input PASS required')


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
    recorder = RunRecorder(output, {'case_id': case_id, 'question': QUESTION, 'image_source': image_spec,
        'settings': SETTINGS, 'seed': 1, 'model_call_budget': 1, 'request_sha256': file_hash(batch / 'request.json')},
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
        loaded = hybrid.loaded_configuration(worker, torch)
        recorder.manifest_update({'model': model, 'loaded': loaded, 'versions': versions()})
        if (loaded['model_config'] != preflight['source_model_config'] or loaded['model_training']
                or loaded['dtype'] != 'torch.bfloat16' or loaded['parameter_dtype'] != 'torch.bfloat16'
                or loaded['tokenizer_model_max_length'] != 16384 or loaded['eos_token_id'] != 151645):
            raise ValueError('Existing loaded model configuration/BF16/eval/tokenizer changed')
        if loaded != preflight['point_reference']['cases'][ordinal]['loaded']:
            raise ValueError('Loaded configuration differs from matched current POINT case')
        if ordinal and loaded != native.read_json(batch / ORDER[0] / 'manifest.json')['loaded']:
            raise ValueError('Cold model/environment differs from first fixed case')
        inputs, pixels, metadata = prepare_native_input(worker.processor, rgb, case_id)
        if metadata != preflight['inputs'][ordinal]:
            raise ValueError('Actual native input differs from reviewed CPU preflight')
        np.savez_compressed(output / 'native-input.npz', pixel_values_float32=pixels.float().numpy())
        baseline.write_json(output / 'native-input.json', metadata)
        for name in ('native-input.npz', 'native-input.json'):
            recorder.record('native_input_sealed', {'artifact': name, 'sha256': file_hash(output / name)})
        raw = call_once(worker, inputs.to('cuda'), pixels.to('cuda'), output, recorder)
        result = analyze_box_return(raw, len(metadata['input_token_ids']),
            loaded['tokenizer_model_max_length'], loaded['eos_token_id'])
        baseline.write_json(output / 'model-output.json', result)
        recorder.record('model_output_sealed', {'artifact': 'model-output.json',
            'sha256': file_hash(output / 'model-output.json'), 'evaluator_opened': False})
        recorder.record('termination', {'reason': 'fixed_rgb_box_condition_complete', 'status': result['status'],
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
    if (errors or 'failure' in kinds or kinds[-1] != 'termination'
            or any(kinds.count(kind) != 1 for kind in ('call_started', 'generation_return_sealed', 'model_output_sealed'))
            or kinds.index('generation_return_sealed') >= kinds.index('model_output_sealed')):
        raise ValueError('One complete raw-before-BOX condition required')
    for row in rows:
        if row['kind'].endswith('_sealed') and file_hash(directory / row['data']['artifact']) != row['data']['sha256']:
            raise ValueError('BOX condition artifact seal changed')
    metadata = native.read_json(directory / 'native-input.json')
    loaded = native.read_json(directory / 'manifest.json')['loaded']
    result = analyze_box_return(native.read_json(directory / 'generation-return.json'),
        len(metadata['input_token_ids']), loaded['tokenizer_model_max_length'], loaded['eos_token_id'])
    if result != native.read_json(directory / 'model-output.json'):
        raise ValueError('BOX analysis recomputation differs')
    return result


def execute_two(recorder, launch):
    results = []
    for ordinal, case_id in enumerate(ORDER):
        recorder.record('condition_intent', {'ordinal': ordinal, 'case_id': case_id})
        launch(case_id)
        result = sealed_condition(recorder.output / case_id)
        results.append({'case_id': case_id, 'status': result['status'],
            'model_output_sha256': file_hash(recorder.output / case_id / 'model-output.json')})
        recorder.record('condition_complete', results[-1])
    return results


def generate(output, preflight_path, review_path):
    preflight_sha = file_hash(preflight_path)
    preflight = load_preflight(preflight_path, preflight_sha)
    check_review(review_path, preflight, preflight_sha)
    if os.environ.get('CUDA_VISIBLE_DEVICES') != GPU:
        raise ValueError('Assigned GPU2 required for both cold native BOX calls')
    request = {'version': VERSION, 'preflight': str(Path(preflight_path).resolve()), 'preflight_sha256': preflight_sha,
        'review_sha256': file_hash(review_path), 'conditions': list(ORDER), 'planned_model_calls': 2,
        'fresh_process_per_condition': True, 'seed': 1, 'physical_gpu': GPU, 'retries': 0,
        'protocol_sha256': file_hash(PROTOCOL), 'source_admission_sha256': hybrid.ADMISSION_SHA,
        'settings': SETTINGS, 'point_preflight_sha256': POINT_PREFLIGHT_SHA,
        'point_audit_sha256': POINT_AUDIT_SHA}
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
        results = execute_two(recorder, launch)
        recorder.record('termination', {'reason': 'two_fixed_cold_current_boxes_complete', 'conditions': results,
            'model_calls': 2, 'retries': 0, 'physics_calls': 0, 'render_calls': 0, 'evaluator_opened': False})
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
