from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import point_replay_order_probe as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records
from embodied_runtime.runtime_core import _sha256_json


def raw_output(boundary):
    if boundary == 25:
        return '<box><412><475></box>' + '<box><1><1><1><1></box>' * 12
    return f'<box><{220 if boundary == 21 else 412}><483></box>'


def token_ids(boundary):
    return [25] * 258 if boundary == 25 else [boundary, 99]


def native_input():
    return {'question':f'Point to: {probe.base.QUERY}.', 'formatted_text':'synthetic native text',
        'input_token_ids':[1,2,3], 'input_token_count':3, 'attention_mask':[[1,1,1]],
        'image_grid_hws':[[1,2,3]], 'pixel_values_original_dtype':'torch.bfloat16',
        'storage':'float32 exact representation of bfloat16 values'}


def fake_loaded():
    return {'model_config':probe.serialize_model_config({'test_config':True}),
            'dtype':'torch.bfloat16', 'tokenizer_model_max_length':16384}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    """Small, hash-chained source with evaluator-only arrays to detect leakage."""
    model = {'files_sha256':{'model.safetensors':'synthetic-model-bytes'}}
    model['content_id'] = _sha256_json(model['files_sha256'])
    monkeypatch.setattr(probe.base, 'EXPECTED_MODEL_CONTENT_ID', model['content_id'])
    source = tmp_path / 'source'
    recorder = RunRecorder(source, {'query':probe.base.QUERY, 'settings':probe.base.SETTINGS},
                           {'run_id':'source', 'code':{'commit':'source-commit'}})
    recorder.manifest_update({'model':model})
    recorder.manifest_update(fake_loaded())
    for boundary in probe.BOUNDARIES:
        seq = boundary + 1
        capture_path, pixel_path = f'capture-{seq}.npz', f'pixels-{seq}.npz'
        np.savez(source / capture_path, rgb=np.full((4,5,3), boundary, np.uint8),
                 depth_m=np.full((4,5), 99.), oracle_state=np.array([123456]))
        np.savez(source / pixel_path, pixel_values_float32=np.full((2,3), boundary/32., np.float32))
        recorder.record('vision_capture', {'capture_seq':seq, 'artifact':capture_path,
                                          'artifact_sha256':file_hash(source / capture_path)})
        recorder.record('point_call_started', {'capture_seq':seq, **native_input(),
            'pixel_values_artifact':pixel_path, 'pixel_values_sha256':file_hash(source / pixel_path)})
        recorder.record('point_call_completed', {'capture_seq':seq, 'raw_output':raw_output(boundary),
            'parsed':probe.parse_grounding(raw_output(boundary),5,4),
            'generation_audit':probe.generation_audit(token_ids(boundary),3,16384,99), 'latency_s':.1})
    recorder.record('termination', {'boundary':25})
    recorder.close()
    monkeypatch.setattr(probe, 'SOURCE_SHA256', file_hash(source / 'episodes.jsonl'))
    directory = tmp_path / 'inputs'
    manifest = probe.prepare(source, directory)
    return SimpleNamespace(source=source, directory=directory, manifest=manifest, model=model)


def fake_worker(calls, *, input_change=None, missing_tokens=False):
    """CPU tensors through the real shared point_call path, without model inference."""
    import torch

    class Inputs(dict):
        def to(self, _device):
            return self

    class Processor:
        def py_apply_chat_template(self, messages, **kwargs):
            assert messages[0]['content'][1]['text'] == native_input()['question']
            return native_input()['formatted_text']
        def process_vision_info(self, messages):
            return [messages[0]['content'][0]['image']], None
        def __call__(self, *, text, images, videos, return_tensors):
            boundary = np.asarray(images[0])[0,0,0].item()
            inputs = Inputs(input_ids=torch.tensor([[1,2,3]]), attention_mask=torch.ones((1,3),dtype=torch.int64),
                pixel_values=torch.full((2,3), boundary/32.), image_grid_hws=torch.tensor([[1,2,3]]))
            if input_change:
                input_change(inputs)
            return inputs

    tokenizer = SimpleNamespace(model_max_length=16384, convert_tokens_to_ids=lambda _:99,
        batch_decode=lambda sequences, **kwargs:[raw_output(sequences[0,0].item())])
    def generate(**kwargs):
        assert {k:kwargs[k] for k in probe.base.SETTINGS} == probe.base.SETTINGS
        boundary = int(kwargs['pixel_values'][0,0].item()*32)
        calls.append(boundary)
        if missing_tokens:
            return raw_output(boundary)
        return tokenizer.batch_decode(torch.tensor([token_ids(boundary)]))[0]
    config = SimpleNamespace(to_dict=lambda:{'test_config':True},
        vision_config=SimpleNamespace(_attn_implementation='sdpa'),
        text_config=SimpleNamespace(_attn_implementation='magi'))
    model = SimpleNamespace(generate=generate, config=config, training=False, dtype=torch.bfloat16)
    return SimpleNamespace(processor=Processor(), tokenizer=tokenizer, model=model,
                           dtype=torch.bfloat16, device='cpu', torch=torch)


def execute(prepared, tmp_path, monkeypatch, arm, worker):
    # The evaluator reference is deliberately absent during generation.
    reference = prepared.directory / 'archive-reference.json'
    if reference.exists():
        reference.rename(prepared.directory / 'withheld-archive-reference.json')
    original = probe.base.point_call
    def inspect_frame(actual_worker, frame, recorder):
        assert set(frame) == {'rgb','capture_seq'}
        return original(actual_worker, frame, recorder)
    monkeypatch.setattr(probe.base, 'point_call', inspect_frame)
    monkeypatch.setattr(probe.base, 'admit_point', lambda *a:pytest.fail('offline output must not enter admission'))
    recorder = RunRecorder(tmp_path / 'calls', {}, {'run_id':'calls'})
    try:
        probe.execute_calls(worker, prepared.manifest, prepared.directory, recorder, arm,
                            {**fake_loaded(), 'eos_token_id':99})
    finally:
        recorder.close()
    return load_records(recorder.output / 'episodes.jsonl')[0]


def test_registered_orders_cover_both_critical_boundaries_cold_once():
    assert probe.ORDERS == {'target_first':[21,20,25], 'terminal_first':[25,20,21]}
    assert sum(len(order) for order in probe.ORDERS.values()) == 6


def test_preparation_separates_rgb_native_input_and_archived_answers(prepared):
    manifest = probe.load_inputs(prepared.directory)
    assert manifest == prepared.manifest
    assert [f['boundary'] for f in manifest['fixtures']] == [20,21,25]
    encoded = json.dumps(manifest)
    for forbidden in ('depth_m','oracle_state','raw_output','parsed','generation_audit','camera_to_world'):
        assert forbidden not in encoded
    for fixture in manifest['fixtures']:
        assert set(fixture['native_input']) == set(probe.INPUT_KEYS)
        rgb = np.load(prepared.directory / fixture['rgb_artifact'])
        assert rgb.dtype == np.uint8 and rgb.shape == (4,5,3)
    assert len(json.loads((prepared.directory / 'archive-reference.json').read_text())['outputs']) == 3


def test_source_hash_rejected_before_output_creation(tmp_path):
    source = tmp_path / 'bad-source'
    source.mkdir()
    (source / 'episodes.jsonl').write_text('{}\n')
    with pytest.raises(ValueError, match='source identity'):
        probe.prepare(source,tmp_path / 'unused')
    assert not (tmp_path / 'unused').exists()


@pytest.mark.parametrize('mutation', ['order','extra_state','fixture','array','settings'])
def test_mutated_prepared_inputs_fail_closed(prepared, mutation):
    manifest = deepcopy(prepared.manifest)
    if mutation == 'order':
        manifest['orders']['target_first'] = [20,21,25]
    elif mutation == 'extra_state':
        manifest['oracle_state'] = [0,0,0]
    elif mutation == 'fixture':
        manifest['fixtures'][0]['native_input']['input_token_ids'] = [7]
    elif mutation == 'array':
        np.save(prepared.directory / manifest['fixtures'][0]['rgb_artifact'], np.zeros((4,5,3),np.uint8))
    elif mutation == 'settings':
        manifest['settings']['max_new_tokens'] = 512
    (prepared.directory / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        probe.load_inputs(prepared.directory)


@pytest.mark.parametrize('arm', ['target_first','terminal_first'])
def test_real_shared_call_preserves_malformed_output_and_continues_all_registered_calls(prepared,tmp_path,monkeypatch,arm):
    calls = []
    rows = execute(prepared,tmp_path,monkeypatch,arm,fake_worker(calls))
    assert calls == probe.ORDERS[arm]
    outputs = [r['data'] for r in rows if r['kind'] == 'point_call_completed']
    malformed = outputs[calls.index(25)]
    assert malformed['raw_output'] == raw_output(25)
    assert malformed['parsed']['status'] == 'malformed'
    assert malformed['generation_audit']['actual_generated_token_count'] == 258
    assert not malformed['generation_audit']['terminal_eos_observed']
    checks = [r['data'] for r in rows if r['kind'] == 'replay_call_checked']
    assert len(checks) == 3 and not checks[calls.index(25)]['structurally_admissible_point']


@pytest.mark.parametrize('field', ['input_ids','pixel_values'])
def test_native_input_mismatch_aborts_before_generate(prepared,tmp_path,monkeypatch,field):
    calls = []
    def change(inputs):
        inputs[field][0,0] += 1
    with pytest.raises(ValueError, match='differ'):
        execute(prepared,tmp_path,monkeypatch,'target_first',fake_worker(calls,input_change=change))
    assert calls == []


def test_missing_native_token_evidence_stops_remaining_calls(prepared,tmp_path,monkeypatch):
    calls = []
    with pytest.raises(ValueError, match='actual_generated_tokens_unavailable'):
        execute(prepared,tmp_path,monkeypatch,'terminal_first',fake_worker(calls,missing_tokens=True))
    assert calls == [25]


def test_fresh_process_guard_and_complete_report(prepared,tmp_path,monkeypatch):
    import embodied_runtime.adapters.locateanything as adapter
    calls = []
    monkeypatch.setattr(probe,'_RUN_STARTED',False)
    monkeypatch.setattr(probe,'model_identity',lambda _:prepared.model)
    monkeypatch.setattr(probe,'code_identity',lambda:{'commit':'test-commit'})
    monkeypatch.setattr(probe,'versions',lambda:{})
    monkeypatch.setattr(adapter,'LocateAnythingWorker',lambda *a,**k:fake_worker(calls))
    arguments = SimpleNamespace(inputs=prepared.directory, output=tmp_path / 'run', arm='terminal_first',
                                model_path='fake-checkpoint',device='cpu')
    probe.run(arguments)
    result = probe.report(arguments.output)
    assert result['complete'] and not result['failures'] and result['no_execution']
    assert [r['boundary'] for r in result['calls']] == [25,20,21]
    assert all(r['archive_raw_output_equal'] and r['archive_generated_tokens_equal'] for r in result['calls'])
    assert calls == [25,20,21]
    with pytest.raises(RuntimeError,match='fresh Python/model process'):
        probe.run(arguments)
    assert calls == [25,20,21]


@pytest.mark.parametrize('training,dtype', [(True,'bfloat16'), (False,'float32')])
def test_wrong_eval_or_parameter_dtype_rejected_before_generation(prepared,tmp_path,monkeypatch,training,dtype):
    import torch
    import embodied_runtime.adapters.locateanything as adapter
    calls = []
    worker = fake_worker(calls)
    worker.model.training, worker.model.dtype = training, getattr(torch,dtype)
    monkeypatch.setattr(probe,'_RUN_STARTED',False)
    monkeypatch.setattr(probe,'model_identity',lambda _:prepared.model)
    monkeypatch.setattr(probe,'code_identity',lambda:{'commit':'test-commit'})
    monkeypatch.setattr(probe,'versions',lambda:{})
    monkeypatch.setattr(adapter,'LocateAnythingWorker',lambda *a,**k:worker)
    arguments = SimpleNamespace(inputs=prepared.directory,output=tmp_path/'run',arm='target_first',
                                model_path='fake-checkpoint',device='cpu')
    with pytest.raises(ValueError,match='eval mode and bfloat16'):
        probe.run(arguments)
    assert not calls
    rows, errors = load_records(arguments.output / 'episodes.jsonl')
    assert not errors and rows[-1]['kind'] == 'failure'


def test_actual_frozen_source_prepares_and_checks_all_three_exact_inputs_when_available(tmp_path):
    source = Path('runs/autonomous-research/coarse-point-boundary-01')
    if not (source / 'episodes.jsonl').exists():
        pytest.skip('frozen boundary evidence unavailable')
    inputs = tmp_path / 'actual-inputs'
    manifest = probe.prepare(source,inputs)
    assert probe.load_inputs(inputs) == manifest
    rows,_ = load_records(source / 'episodes.jsonl')
    starts = {r['data']['capture_seq']:r['data'] for r in rows if r['kind']=='point_call_started'}
    for fixture in manifest['fixtures']:
        probe.check_native_input(starts[fixture['source_capture_seq']],fixture,inputs,source)
