"""Six registered RGB-only calls in two fresh-process POINT replay orders."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace

import numpy as np

from ..runtime_core import _sha256_json
from . import coarse_point_probe as base
from .point_grounding_probe import generation_audit, parse_grounding, serialize_model_config
from .predicate_verification import one_record
from .records import RunRecorder, code_identity, file_hash, load_records, model_identity, versions

VERSION = 'point-replay-order-v1'
SOURCE_SHA256 = 'd9ed0bc2b10b61b047e44ec37a03ea788b4e88e2f8d06edd8171bcd29677f319'
PROTOCOL = Path(__file__).resolve().parents[2] / 'docs/research/point_replay_order_probe_protocol.md'
BOUNDARIES = (20, 21, 25)
ORDERS = {'target_first': [21, 20, 25], 'terminal_first': [25, 20, 21]}
INPUT_KEYS = ('question', 'formatted_text', 'input_token_ids', 'input_token_count', 'image_grid_hws',
              'pixel_values_original_dtype', 'storage', 'attention_mask')
_RUN_STARTED = False


def array_identity(value):
    array = np.asarray(value)
    return {'shape':list(array.shape), 'dtype':str(array.dtype),
            'values_sha256':hashlib.sha256(array.tobytes(order='C')).hexdigest()}


def prepare(source, output):
    source, output = Path(source), Path(output)
    if file_hash(source / 'episodes.jsonl') != SOURCE_SHA256:
        raise ValueError('immutable boundary-run source identity mismatch')
    rows, errors = load_records(source / 'episodes.jsonl')
    start = one_record(rows, 'run_start')
    config = start['resolved_config']
    models = [r['data'] for r in rows if r['kind'] == 'manifest_update']
    model = next(m['model'] for m in models if 'model' in m)
    loaded = next(m for m in models if 'model_config' in m)
    if (errors or config['query'] != base.QUERY or config['settings'] != base.SETTINGS
            or model['content_id'] != base.EXPECTED_MODEL_CONTENT_ID
            or one_record(rows, 'termination')['boundary'] != 25):
        raise ValueError('frozen POINT settings/model and completed boundary evidence required')
    captures = {r['data']['capture_seq']:r['data'] for r in rows if r['kind'] == 'vision_capture'}
    starts = {r['data']['capture_seq']:r['data'] for r in rows if r['kind'] == 'point_call_started'}
    outputs = {r['data']['capture_seq']:r['data'] for r in rows if r['kind'] == 'point_call_completed'}
    output.mkdir(parents=True, exist_ok=False)
    fixtures, references = [], []
    for boundary in BOUNDARIES:
        seq = boundary + 1
        capture, native = captures[seq], starts[seq]
        capture_path, pixels_path = source / capture['artifact'], source / native['pixel_values_artifact']
        if file_hash(capture_path) != capture['artifact_sha256'] or file_hash(pixels_path) != native['pixel_values_sha256']:
            raise ValueError('source image/native pixel artifact changed')
        # Explicit named-array access: no depth, calibration, state or oracle array is extracted.
        with np.load(capture_path, allow_pickle=False) as archive:
            rgb = archive['rgb']
        with np.load(pixels_path, allow_pickle=False) as archive:
            pixels = archive['pixel_values_float32']
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3 or pixels.dtype != np.float32:
            raise ValueError('unexpected source RGB/native pixel representation')
        rgb_name, pixels_name = f'rgb-{boundary}.npy', f'native-pixels-{boundary}.npy'
        np.save(output / rgb_name, rgb, allow_pickle=False)
        np.save(output / pixels_name, pixels, allow_pickle=False)
        fixture = {'boundary':boundary, 'source_capture_seq':seq, 'source_capture_sha256':capture['artifact_sha256'],
                   'rgb_artifact':rgb_name, 'rgb_sha256':file_hash(output / rgb_name), 'rgb_array':array_identity(rgb),
                   'native_pixels_artifact':pixels_name, 'native_pixels_sha256':file_hash(output / pixels_name),
                   'native_pixels_array':array_identity(pixels), 'native_input':{k:native[k] for k in INPUT_KEYS}}
        fixture['fixture_id'] = _sha256_json(fixture)
        fixtures.append(fixture)
        references.append({'boundary':boundary, 'source_capture_seq':seq, 'source_output':outputs[seq]})
    manifest = {'version':VERSION, 'source_sha256':SOURCE_SHA256, 'protocol_sha256':file_hash(PROTOCOL),
                'source_commit':start['manifest']['code']['commit'], 'query':base.QUERY, 'settings':base.SETTINGS,
                'model_content_id':base.EXPECTED_MODEL_CONTENT_ID, 'source_model_config':loaded,
                'generator_allowed_frame_fields':['rgb', 'capture_seq'], 'fixtures':fixtures, 'orders':ORDERS}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    # Generator never opens this evaluator/reference file; no archived answer is a model input.
    (output / 'archive-reference.json').write_text(json.dumps({
        'source':str(source.resolve()), 'source_sha256':SOURCE_SHA256,
        'input_manifest_sha256':file_hash(output / 'manifest.json'), 'outputs':references}, indent=2)+'\n')
    (output / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    return manifest


def load_inputs(directory):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    allowed = {'version', 'source_sha256', 'protocol_sha256', 'source_commit', 'query', 'settings',
               'model_content_id', 'source_model_config', 'generator_allowed_frame_fields', 'fixtures', 'orders'}
    fixture_keys = {'boundary', 'source_capture_seq', 'source_capture_sha256', 'rgb_artifact', 'rgb_sha256',
                    'rgb_array', 'native_pixels_artifact', 'native_pixels_sha256', 'native_pixels_array',
                    'native_input', 'fixture_id'}
    if (set(manifest) != allowed or manifest['version'] != VERSION
            or manifest['source_sha256'] != SOURCE_SHA256 or manifest['protocol_sha256'] != file_hash(PROTOCOL)
            or manifest['query'] != base.QUERY or manifest['settings'] != base.SETTINGS
            or manifest['model_content_id'] != base.EXPECTED_MODEL_CONTENT_ID or manifest['orders'] != ORDERS
            or manifest['generator_allowed_frame_fields'] != ['rgb', 'capture_seq']
            or [f['boundary'] for f in manifest['fixtures']] != list(BOUNDARIES)):
        raise ValueError('registered RGB-only input manifest changed')
    for fixture in manifest['fixtures']:
        if (set(fixture) != fixture_keys or set(fixture['native_input']) != set(INPUT_KEYS)
                or fixture['fixture_id'] != _sha256_json({k:v for k,v in fixture.items() if k != 'fixture_id'})):
            raise ValueError('unexpected fixture fields or changed identity')
        for kind in ('rgb', 'native_pixels'):
            path = directory / fixture[kind+'_artifact']
            if path.parent.resolve() != directory.resolve() or file_hash(path) != fixture[kind+'_sha256']:
                raise ValueError('input artifact changed or outside prepared directory')
            if array_identity(np.load(path, allow_pickle=False)) != fixture[kind+'_array']:
                raise ValueError('prepared array content changed')
    return manifest


def check_native_input(data, fixture, input_dir, output_dir):
    if {k:data[k] for k in INPUT_KEYS} != fixture['native_input']:
        raise ValueError('actual POINT question/tokens/attention/grid differ from archived input')
    actual_path = Path(output_dir) / data['pixel_values_artifact']
    if file_hash(actual_path) != data['pixel_values_sha256']:
        raise ValueError('actual native pixel artifact changed')
    with np.load(actual_path, allow_pickle=False) as archive:
        actual = archive['pixel_values_float32']
    expected = np.load(Path(input_dir) / fixture['native_pixels_artifact'], allow_pickle=False)
    if array_identity(actual) != fixture['native_pixels_array'] or not np.array_equal(actual, expected):
        raise ValueError('actual native image tensor differs from archived input')


def check_output(data, fixture, worker_config):
    audit = data['generation_audit']
    height, width, _ = fixture['rgb_array']['shape']
    if (data['parsed'] != parse_grounding(data['raw_output'], width, height)
            or audit != generation_audit(audit['actual_generated_token_ids'],
                fixture['native_input']['input_token_count'], worker_config['tokenizer_model_max_length'],
                worker_config['eos_token_id'])):
        raise ValueError('recorded parsing/generation audit differs from raw output/tokens')
    # Malformed or length-limited output is the measurement, not an infrastructure failure.
    return {'structurally_admissible_point': data['parsed']['status'] == 'single_point'
            and audit['terminal_eos_observed'] and not audit['length_limit_reached'],
            'semantic_target_identity_verified': False}


def execute_calls(worker, manifest, input_dir, recorder, arm, worker_config):
    by_boundary = {f['boundary']:f for f in manifest['fixtures']}
    for ordinal, boundary in enumerate(ORDERS[arm]):
        fixture = by_boundary[boundary]
        call_seq = ordinal + 1
        recorder.record('replay_call_intent', {'arm':arm, 'ordinal':ordinal, 'boundary':boundary,
            'fixture_id':fixture['fixture_id'], 'call_capture_seq':call_seq,
            'source_capture_seq':fixture['source_capture_seq'], 'prior_boundaries':ORDERS[arm][:ordinal]})
        observed = {}
        def record(kind, data):
            if kind in observed or data.get('capture_seq') != call_seq:
                raise ValueError('duplicate call event or mismatched capture identity')
            recorder.record(kind, data)
            observed[kind] = data
            if kind == 'point_call_started':
                # This callback runs before base.point_call invokes model.generate.
                check_native_input(data, fixture, input_dir, recorder.output)
        rgb = np.load(Path(input_dir) / fixture['rgb_artifact'], allow_pickle=False)
        frame = {'rgb':rgb, 'capture_seq':call_seq}
        base.point_call(worker, frame, SimpleNamespace(output=recorder.output, record=record))
        if set(observed) != {'point_call_started', 'point_call_completed'}:
            raise ValueError('exactly one recorded input and output required per call')
        result = check_output(observed['point_call_completed'], fixture, worker_config)
        recorder.record('replay_call_checked', {'ordinal':ordinal, 'boundary':boundary, **result})


def run(args):
    global _RUN_STARTED
    if _RUN_STARTED:
        raise RuntimeError('each arm requires a fresh Python/model process')
    _RUN_STARTED = True
    manifest = load_inputs(args.inputs)
    recorder = RunRecorder(args.output, {'version':VERSION, 'arm':args.arm, 'order':ORDERS[args.arm],
        'planned_calls':3, 'passes':1, 'seed':1, 'inputs':str(Path(args.inputs).resolve()),
        'input_manifest_sha256':file_hash(Path(args.inputs) / 'manifest.json'),
        'protocol_sha256':file_hash(PROTOCOL), 'settings':base.SETTINGS, 'query':base.QUERY,
        'source_sha256':SOURCE_SHA256, 'no_execution':True, 'model_input_rgb_only':True},
        {'run_id':Path(args.output).name, 'code':code_identity(), 'versions':versions(), 'pid':os.getpid()})
    try:
        identity = model_identity(args.model_path)
        recorder.manifest_update({'model':identity})
        if identity['content_id'] != base.EXPECTED_MODEL_CONTENT_ID:
            raise ValueError('LocateAnything differs from frozen POINT checkpoint')
        from ..adapters.locateanything import LocateAnythingWorker
        import torch
        random.seed(1)
        np.random.seed(1)
        torch.manual_seed(1)
        worker = LocateAnythingWorker(args.model_path, device=args.device)
        loaded = {'model_config':serialize_model_config(worker.model.config.to_dict()), 'dtype':str(worker.dtype),
                  'tokenizer_model_max_length':worker.tokenizer.model_max_length,
                  'eos_token_id':worker.tokenizer.convert_tokens_to_ids('<|im_end|>'),
                  'model_training':worker.model.training, 'parameter_dtype':str(worker.model.dtype)}
        recorder.record('model_loaded', loaded)
        if any(loaded[k] != v for k,v in manifest['source_model_config'].items()):
            raise ValueError('loaded model configuration/dtype/tokenizer differs from source')
        if loaded['model_training'] or loaded['parameter_dtype'] != 'torch.bfloat16':
            raise ValueError('frozen eval mode and bfloat16 parameters required')
        recorder.record('inference_environment', {'device':str(worker.device), 'pid':os.getpid(),
            'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'), 'torch_threads':torch.get_num_threads(),
            'deterministic_algorithms':torch.are_deterministic_algorithms_enabled(),
            'gpu_name':torch.cuda.get_device_name(args.device) if args.device.startswith('cuda') else None,
            'vision_attention_implementation':worker.model.config.vision_config._attn_implementation,
            'text_attention_implementation':worker.model.config.text_config._attn_implementation,
            'fresh_process_one_arm_enforced':True})
        execute_calls(worker, manifest, args.inputs, recorder, args.arm, loaded)
        recorder.record('termination', {'reason':'point_replay_complete', 'calls':3})
    except BaseException as exc:
        recorder.record('failure', {'exception':repr(exc), 'retries':0})
        raise
    finally:
        recorder.close()


def report(output):
    output = Path(output)
    rows, errors = load_records(output / 'episodes.jsonl')
    config = one_record(rows, 'run_start')['resolved_config']
    inputs = Path(config['inputs'])
    if file_hash(inputs / 'manifest.json') != config['input_manifest_sha256']:
        raise ValueError('prepared input manifest changed')
    manifest = load_inputs(inputs)
    loaded = one_record(rows, 'model_loaded')
    model = one_record(rows, 'manifest_update')['model']
    if (model['content_id'] != base.EXPECTED_MODEL_CONTENT_ID
            or _sha256_json(model['files_sha256']) != model['content_id']
            or loaded['model_training'] or loaded['parameter_dtype'] != 'torch.bfloat16'
            or any(loaded[k] != v for k,v in manifest['source_model_config'].items())):
        raise ValueError('recorded model configuration/identity changed')
    if config['order'] != ORDERS[config['arm']] or config['planned_calls'] != 3 or config['passes'] != 1:
        raise ValueError('registered order or call count changed')
    reference = json.loads((inputs / 'archive-reference.json').read_text())
    if (reference['source_sha256'] != SOURCE_SHA256
            or reference['input_manifest_sha256'] != config['input_manifest_sha256']):
        raise ValueError('evaluator reference lineage changed')
    source_rows, source_errors = load_records(Path(reference['source']) / 'episodes.jsonl')
    if source_errors or file_hash(Path(reference['source']) / 'episodes.jsonl') != SOURCE_SHA256:
        raise ValueError('immutable source evidence changed')
    old = {r['data']['capture_seq']-1:r['data'] for r in source_rows if r['kind'] == 'point_call_completed'}
    if reference['outputs'] != [{'boundary':b, 'source_capture_seq':b+1, 'source_output':old[b]} for b in BOUNDARIES]:
        raise ValueError('archived outputs were changed in the evaluator reference')
    starts = {r['data']['capture_seq']:r['data'] for r in rows if r['kind'] == 'point_call_started'}
    outputs = {r['data']['capture_seq']:r['data'] for r in rows if r['kind'] == 'point_call_completed'}
    intents = [r['data'] for r in rows if r['kind'] == 'replay_call_intent']
    checked = [r['data'] for r in rows if r['kind'] == 'replay_call_checked']
    if len(starts) != sum(r['kind'] == 'point_call_started' for r in rows) or len(outputs) != sum(r['kind'] == 'point_call_completed' for r in rows):
        raise ValueError('duplicate call input/output')
    if (len(intents) > 3 or not set(outputs) <= set(starts) <= set(range(1, len(intents)+1))
            or len(checked) > len(outputs)):
        raise ValueError('unregistered/orphan call input/output')
    fixtures = {f['boundary']:f for f in manifest['fixtures']}
    results = []
    for ordinal, intent in enumerate(intents):
        boundary = ORDERS[config['arm']][ordinal]
        seq = ordinal + 1
        if intent != {'arm':config['arm'], 'ordinal':ordinal, 'boundary':boundary,
                      'fixture_id':fixtures[boundary]['fixture_id'], 'call_capture_seq':seq,
                      'source_capture_seq':boundary+1, 'prior_boundaries':ORDERS[config['arm']][:ordinal]}:
            raise ValueError('call order or fixture identity differs')
        if seq not in starts or seq not in outputs:
            continue
        check_native_input(starts[seq], fixtures[boundary], inputs, output)
        observation = check_output(outputs[seq], fixtures[boundary], loaded)
        result = outputs[seq]
        results.append({'ordinal':ordinal, 'boundary':boundary, 'cold_first_call':ordinal == 0,
            'prior_boundaries':ORDERS[config['arm']][:ordinal], **observation,
            'raw_output':result['raw_output'], 'parsed':result['parsed'], 'generation_audit':result['generation_audit'],
            'archive_raw_output_equal':result['raw_output'] == old[boundary]['raw_output'],
            'archive_generated_tokens_equal':result['generation_audit']['actual_generated_token_ids']
                == old[boundary]['generation_audit']['actual_generated_token_ids']})
    expected_checks = [{'ordinal':r['ordinal'], 'boundary':r['boundary'],
        'structurally_admissible_point':r['structurally_admissible_point'],
        'semantic_target_identity_verified':False} for r in results]
    if checked != expected_checks[:len(checked)]:
        raise ValueError('recorded call check differs from raw output audit')
    failures = [r['data'] for r in rows if r['kind'] == 'failure']
    terminal = [r['data'] for r in rows if r['kind'] == 'termination']
    return {'version':VERSION, 'arm':config['arm'], 'raw_sha256':file_hash(output / 'episodes.jsonl'),
            'input_manifest_sha256':config['input_manifest_sha256'], 'calls':results, 'failures':failures,
            'record_errors':errors, 'complete':not errors and not failures and len(results) == len(intents) == len(checked) == 3
                and set(starts) == set(outputs) == {1,2,3}
                and terminal == [{'reason':'point_replay_complete', 'calls':3}],
            'no_execution':True, 'scope':'exact RGB replay; no new target-correctness label or universal statelessness claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare')
    mode.add_argument('--output')
    mode.add_argument('--summarize')
    parser.add_argument('--source', default='runs/autonomous-research/coarse-point-boundary-01')
    parser.add_argument('--inputs')
    parser.add_argument('--arm', choices=ORDERS)
    parser.add_argument('--model-path', default='/home/junhongli/models/huggingface/LocateAnything-3B')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    if args.prepare:
        print(json.dumps(prepare(args.source, args.prepare), indent=2))
    elif args.summarize:
        print(json.dumps(report(args.summarize), indent=2))
    elif not args.inputs or not args.arm:
        parser.error('--output requires --inputs and --arm; one arm per fresh process')
    else:
        run(args)


if __name__ == '__main__':
    main()
