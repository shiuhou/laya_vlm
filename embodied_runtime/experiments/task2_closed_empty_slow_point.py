"""Two matched cold native slow POINT calls; only generation mode changes."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np

from . import task2_closed_empty_fresh_point as hybrid
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

adapter = hybrid.adapter
native = adapter.native
baseline = native.baseline
ROOT = Path(__file__).resolve().parents[2]
MODULE = 'embodied_runtime.experiments.task2_closed_empty_slow_point'
VERSION = 'task2-two-cold-slow-point-v1'
PROTOCOL = ROOT / 'docs/research/task2_closed_empty_slow_point_protocol.md'
ORDER = ('present-postevent', 'away-postevent')
GPU = '2'
RAW = baseline.SOURCE.parent
HYBRID_RUN = RAW / 'task2-closed-empty-fresh-point-run-01'
HYBRID_PREFLIGHT = RAW / 'task2-closed-empty-fresh-point-preflight-02.json'
HYBRID_PREFLIGHT_SHA = '366b576db8398de8c51425f0e45a3cb1e5eda732e1eeefc677e53aeb8586308a'
HYBRID_AUDIT = ROOT / 'docs/evidence/autonomous_research/task2_closed_empty_fresh_point_independent_audit.json'
HYBRID_AUDIT_SHA = 'dd6e3e1463e2b6a00d9b4e31d6c16164e0dd471b21ea554b301c60f4bd5964d0'
HYBRID_EXIT = RAW / 'task2-closed-empty-fresh-point-run-01-exit.json'
HYBRID_EXIT_SHA = 'a3d807fb4d90a479e35e8cc0e6d6f615af14b0a76e8a25afcfee43773bd846ad'
HYBRID_SETTINGS = {'max_new_tokens': 256, 'use_cache': True, 'generation_mode': 'hybrid',
    'temperature': 0.0, 'do_sample': False, 'verbose': False}
SLOW_SETTINGS = {**HYBRID_SETTINGS, 'generation_mode': 'slow'}
_STARTED = False


def verify_helpers():
    adapter.verify_helpers()
    for module, sha in (
        (hybrid, '00dc92040a83763e2f3a5844b9b7c69ab21942b481e79b1e005449bba0ce4843'),
        (adapter, '875abd9a8d4108e9c793754aed4c91f89ff3ce1f6d59a5e72173e1db2f819b83'),
    ):
        if file_hash(module.__file__) != sha:
            raise ValueError('Archived hybrid helper bytes changed')
    if (native.SETTINGS != HYBRID_SETTINGS
            or SLOW_SETTINGS != {**HYBRID_SETTINGS, 'generation_mode': 'slow'}):
        raise ValueError('Only the explicit scoped generation_mode intervention is allowed')


def hybrid_packet():
    """Bind audited baseline, exact archived inputs and loaded configuration."""
    verify_helpers()
    for path, sha in ((HYBRID_PREFLIGHT, HYBRID_PREFLIGHT_SHA), (HYBRID_AUDIT, HYBRID_AUDIT_SHA),
                      (HYBRID_EXIT, HYBRID_EXIT_SHA)):
        if file_hash(path) != sha:
            raise ValueError('Exact audited hybrid baseline required')
    old = native.read_json(HYBRID_PREFLIGHT)
    audit, receipt = native.read_json(HYBRID_AUDIT), native.read_json(HYBRID_EXIT)
    journal_sha = file_hash(HYBRID_RUN / 'episodes.jsonl')
    rows, errors = load_records(HYBRID_RUN / 'episodes.jsonl')
    if (audit['status'] != 'PASS' or audit['raw_directory'] != str(HYBRID_RUN)
            or audit['journal_sha256'] != journal_sha or receipt['batch_journal_sha256'] != journal_sha
            or errors or rows[-1]['kind'] != 'termination' or rows[-1]['data']['model_calls'] != 4
            or receipt['tool_exit_code'] != 0 or old['settings'] != HYBRID_SETTINGS
            or old['source'] != hybrid.source_packet() or old['conditions'] != list(hybrid.ORDER)):
        raise ValueError('Completed unchanged hybrid batch and physical source required')
    cases = []
    for ordinal, case_id in enumerate(ORDER):
        directory = HYBRID_RUN / case_id
        spec = receipt['conditions'][ordinal]
        if spec['case_id'] != case_id:
            raise ValueError('Matched postevent baseline order required')
        for name, sha in spec['sha256'].items():
            if file_hash(directory / name) != sha:
                raise ValueError('Archived hybrid case bytes changed')
        result = hybrid.sealed_condition(directory)
        manifest = native.read_json(directory / 'manifest.json')
        metadata = native.read_json(directory / 'native-input.json')
        if (metadata != old['inputs'][ordinal] or manifest['versions'] != old['versions']
                or native.read_json(directory / 'resolved_config.yaml')['settings'] != HYBRID_SETTINGS
                or result['status'] != spec['status']):
            raise ValueError('Archived hybrid input/settings/environment mismatch')
        cases.append({'case_id': case_id, 'sha256': spec['sha256'], 'loaded': manifest['loaded'],
            'status': result['status']})
    packet = {'directory': str(HYBRID_RUN), 'preflight_sha256': HYBRID_PREFLIGHT_SHA,
        'audit_sha256': HYBRID_AUDIT_SHA, 'exit_receipt_sha256': HYBRID_EXIT_SHA,
        'journal_sha256': journal_sha, 'cases': cases}
    return packet, old


def slow_call_once(worker, inputs, pixels, output, recorder):
    """Replace one module binding, never mutate shared settings or model code."""
    verify_helpers()
    original = native.SETTINGS
    baseline.write_json(output / 'generation-settings.json', SLOW_SETTINGS)
    recorder.record('generation_settings_sealed', {'artifact': 'generation-settings.json',
        'sha256': file_hash(output / 'generation-settings.json')})
    native.SETTINGS = dict(SLOW_SETTINGS)
    try:
        return native.call_once(worker, inputs, pixels, output, recorder)
    finally:
        native.SETTINGS = original


def processor_preflight(output):
    """CPU processor/tensor preparation only; never construct model weights."""
    from transformers import AutoProcessor
    import torch
    identity = code_identity()
    if identity['dirty_status'] or os.environ.get('CUDA_VISIBLE_DEVICES') != '' or torch.cuda.is_initialized():
        raise ValueError('Clean freeze and CPU-only processor preflight required')
    reference, old = hybrid_packet()
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
    inputs = [adapter.prepare_native_input(processor, adapter.load_rgb(source['source_root'], row), row['case_id'])[2]
              for row in source['images']]
    if inputs != old['inputs'][:2]:
        raise ValueError('CPU inputs differ from exact archived hybrid postevent inputs')
    if torch.cuda.is_initialized():
        raise ValueError('Processor preflight initialized CUDA')
    value = {'version': VERSION, 'status': 'pass', 'code': identity, 'protocol_sha256': file_hash(PROTOCOL),
        'source': source, 'hybrid_reference': reference, 'conditions': list(ORDER),
        'question': adapter.QUESTION, 'settings': SLOW_SETTINGS,
        'model': model, 'source_model_config': config, 'description_provenance': references, 'inputs': inputs,
        'versions': versions(), 'physical_gpu_for_inference': GPU, 'processor_device': 'cpu',
        'model_constructions': 0, 'model_calls': 0, 'physics_calls': 0, 'render_calls': 0}
    baseline.write_json(output, value)
    return value


def load_preflight(path, expected_sha):
    if file_hash(path) != expected_sha:
        raise ValueError('Reviewed processor preflight changed')
    value = native.read_json(path)
    reference, old = hybrid_packet()
    source = {**old['source'], 'images': old['source']['images'][:2]}
    if (value['version'] != VERSION or value['status'] != 'pass' or value['code'] != code_identity()
            or value['protocol_sha256'] != file_hash(PROTOCOL) or value['source'] != source
            or value['hybrid_reference'] != reference or value['inputs'] != old['inputs'][:2]
            or value['conditions'] != list(ORDER) or value['question'] != adapter.QUESTION
            or value['settings'] != SLOW_SETTINGS or value['model']['content_id'] != baseline.MODEL_CONTENT_ID
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
        'model_calls_authorized': 2, 'physical_gpu': GPU, 'generation_settings': SLOW_SETTINGS,
        'hybrid_preflight_sha256': HYBRID_PREFLIGHT_SHA, 'hybrid_audit_sha256': HYBRID_AUDIT_SHA}
    if any(review.get(key) != value for key, value in expected.items()):
        raise ValueError('Exact two-call slow code/config/input PASS required')


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
        'settings': SLOW_SETTINGS, 'seed': 1, 'model_call_budget': 1, 'request_sha256': file_hash(batch / 'request.json')},
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
        if loaded != preflight['hybrid_reference']['cases'][ordinal]['loaded']:
            raise ValueError('Loaded configuration differs from matched archived hybrid case')
        if ordinal and loaded != native.read_json(batch / ORDER[0] / 'manifest.json')['loaded']:
            raise ValueError('Cold model/environment differs from first fixed case')
        inputs, pixels, metadata = adapter.prepare_native_input(worker.processor, rgb, case_id)
        if metadata != preflight['inputs'][ordinal]:
            raise ValueError('Actual native input differs from reviewed CPU preflight')
        np.savez_compressed(output / 'native-input.npz', pixel_values_float32=pixels.float().numpy())
        baseline.write_json(output / 'native-input.json', metadata)
        for name in ('native-input.npz', 'native-input.json'):
            recorder.record('native_input_sealed', {'artifact': name, 'sha256': file_hash(output / name)})
        raw = slow_call_once(worker, inputs.to('cuda'), pixels.to('cuda'), output, recorder)
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


def execute_two(recorder, launch):
    results = []
    for ordinal, case_id in enumerate(ORDER):
        recorder.record('condition_intent', {'ordinal': ordinal, 'case_id': case_id})
        launch(case_id)
        result = hybrid.sealed_condition(recorder.output / case_id)
        results.append({'case_id': case_id, 'status': result['status'],
            'sensor_sha256': file_hash(recorder.output / case_id / 'sensor-result.json')})
        recorder.record('condition_complete', results[-1])
    return results


def generate(output, preflight_path, review_path):
    preflight_sha = file_hash(preflight_path)
    preflight = load_preflight(preflight_path, preflight_sha)
    check_review(review_path, preflight, preflight_sha)
    if os.environ.get('CUDA_VISIBLE_DEVICES') != GPU:
        raise ValueError('Assigned GPU2 required for both cold slow calls')
    request = {'version': VERSION, 'preflight': str(Path(preflight_path).resolve()), 'preflight_sha256': preflight_sha,
        'review_sha256': file_hash(review_path), 'conditions': list(ORDER), 'planned_model_calls': 2,
        'fresh_process_per_condition': True, 'seed': 1, 'physical_gpu': GPU, 'retries': 0,
        'protocol_sha256': file_hash(PROTOCOL), 'source_admission_sha256': hybrid.ADMISSION_SHA,
        'settings': SLOW_SETTINGS, 'hybrid_preflight_sha256': HYBRID_PREFLIGHT_SHA,
        'hybrid_audit_sha256': HYBRID_AUDIT_SHA}
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
        recorder.record('termination', {'reason': 'two_fixed_cold_slow_points_complete', 'conditions': results,
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
