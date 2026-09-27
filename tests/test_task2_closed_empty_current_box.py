from contextlib import nullcontext
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_current_box as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


@pytest.mark.parametrize(('raw', 'tokens', 'status'), [
    ('<box><100><200><300><400></box><|im_end|>', [1, 151645], 'admitted_rgb_box'),
    ('<box><100><200></box><box><100><200><300><400></box><|im_end|>', [1, 151645], 'not_admitted'),
    ('<box><100><200><300><400></box><box><100><200><300><200></box><|im_end|>', [1, 151645], 'not_admitted'),
    ('<box><100><200><300><400></box><box><100><200><300><400></box><|im_end|>', [1, 151645], 'not_admitted'),
    ('<box>none</box><|im_end|>', [1, 151645], 'not_admitted'),
    ('<box><100><200><300><400></box>', [1], 'not_admitted'),
    ('<box><100><200><300><400></box><|im_end|>', [1] * 256 + [151645], 'not_admitted'),
])
def test_whole_return_box_admission_never_salvages_prefix_or_incomplete(raw, tokens, status):
    result = probe.analyze_box_return({'raw_response': raw, 'raw_response_type': 'str',
        'observed_decoded_token_sequences': [[tokens]]}, 237, 16384, 151645)
    assert result['status'] == status
    assert (result['admitted_box'] is None) == (status == 'not_admitted')
    assert result['holding'] is None and not result['depth_read'] and not result['support_extracted']
    assert not result['box_median_goal_created']


@pytest.mark.parametrize('fails', [False, True])
def test_real_native_call_preserves_historical_hybrid_kwargs_and_exact_binding(tmp_path, fails):
    original = probe.native.SETTINGS
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        assert probe.native.SETTINGS is original
        if fails:
            raise RuntimeError('model failed')
        return '<box>none</box><|im_end|>'
    tokenizer = SimpleNamespace(batch_decode=lambda *_: [])
    worker = SimpleNamespace(tokenizer=tokenizer, model=SimpleNamespace(generate=generate),
        torch=SimpleNamespace(no_grad=nullcontext))
    recorder = RunRecorder(tmp_path / 'case', {}, {'run_id': 'case'})
    inputs = {'input_ids': object(), 'attention_mask': object(), 'image_grid_hws': object()}
    pixels = object()
    try:
        if fails:
            with pytest.raises(RuntimeError, match='model failed'):
                probe.call_once(worker, inputs, pixels, recorder.output, recorder)
        else:
            probe.call_once(worker, inputs, pixels, recorder.output, recorder)
    finally:
        recorder.close()
    assert probe.native.SETTINGS is original and len(calls) == 1
    assert {key: calls[0][key] for key in original} == original == probe.SETTINGS
    assert json.loads((recorder.output / 'generation-settings.json').read_text()) == original
    rows, errors = load_records(recorder.output / 'episodes.jsonl')
    assert not errors and sum(r['kind'] == 'call_started' for r in rows) == 1


@pytest.mark.parametrize('pixel_mismatch', [False, True])
def test_cpu_box_preflight_changes_question_but_requires_exact_point_visual_input(tmp_path, monkeypatch, pixel_mismatch):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '')
    monkeypatch.setattr(probe, 'code_identity', lambda: {'commit': 'frozen', 'dirty_status': ''})
    source = {'source_root': 'source', 'images': [{'case_id': case} for case in probe.ORDER]}
    model = {'content_id': probe.baseline.MODEL_CONTENT_ID}
    old_inputs = [{'condition': case, 'question': 'Point to: the wine bottle.', 'input_token_ids': [1, 2],
        'rgb': {'sha': case}, 'image_grid_hws': [[28, 28]], 'pixel_values_original_dtype': 'torch.bfloat16',
        'pixel_values_float32': {'sha': case}} for case in probe.ORDER]
    old = {'source': source, 'versions': {}, 'model': model, 'inputs': old_inputs,
        'source_model_config': {'original': 'config'}}
    monkeypatch.setattr(probe, 'point_packet', lambda: ({'baseline': 'fixed'}, old))
    monkeypatch.setattr(probe, 'model_identity', lambda _: model)
    reference = tmp_path / 'reference'
    reference.mkdir()
    (reference / 'manifest.json').write_text(json.dumps({'versions': {}}))
    monkeypatch.setattr(probe.native, 'source_config', lambda: (old['source_model_config'], [{'directory': str(reference)}]))
    monkeypatch.setattr(probe, 'versions', lambda: {})
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(cuda=SimpleNamespace(is_initialized=lambda: False)))
    calls = []
    def processor(*args, **kwargs):
        calls.append('processor')
        assert kwargs == {'trust_remote_code': True, 'local_files_only': True}
        return object()
    monkeypatch.setitem(sys.modules, 'transformers', SimpleNamespace(
        AutoProcessor=SimpleNamespace(from_pretrained=processor)))
    monkeypatch.setattr(probe.adapter, 'load_rgb', lambda *_: np.zeros((384, 384, 3), np.uint8))
    def native_input(processor, rgb, condition):
        calls.append(condition['condition'])
        assert condition['question'] == probe.QUESTION and condition['query'] == 'the wine bottle'
        assert set(condition) == {'condition', 'query', 'question'}
        assert rgb.shape == (384, 384, 3)
        metadata = {**old_inputs[list(probe.ORDER).index(condition['condition'])],
            **condition, 'input_token_ids': [3, 4, 5]}
        if pixel_mismatch:
            metadata['pixel_values_float32'] = {'sha': 'changed'}
        return None, None, metadata
    monkeypatch.setattr(probe.native, 'native_input', native_input)
    path = tmp_path / 'preflight.json'
    if pixel_mismatch:
        with pytest.raises(ValueError, match='BOX visual tensors differ'):
            probe.processor_preflight(path)
        assert not path.exists()
    else:
        value = probe.processor_preflight(path)
        assert value['model_calls'] == value['model_constructions'] == value['physics_calls'] == 0
        assert all(row['input_token_ids'] == [3, 4, 5] and row['question'] == probe.QUESTION for row in value['inputs'])
        assert value['settings']['generation_mode'] == 'hybrid'
    assert calls == ['processor', *probe.ORDER]


@pytest.mark.parametrize('change', ['freeze_commit', 'preflight_sha256', 'conditions',
    'model_calls_authorized', 'physical_gpu', 'generation_settings', 'point_preflight_sha256', 'point_audit_sha256'])
def test_exact_box_review_gate(tmp_path, change):
    value = {'status': 'PASS', 'freeze_commit': 'freeze', 'preflight_sha256': 'preflight',
        'protocol_sha256': file_hash(probe.PROTOCOL), 'source_admission_sha256': probe.hybrid.ADMISSION_SHA,
        'conditions': list(probe.ORDER), 'model_calls_authorized': 2, 'physical_gpu': '2',
        'generation_settings': probe.SETTINGS, 'point_preflight_sha256': probe.POINT_PREFLIGHT_SHA,
        'point_audit_sha256': probe.POINT_AUDIT_SHA}
    value[change] = 'different'
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='two-call current BOX'):
        probe.check_review(path, {'code': {'commit': 'freeze'}}, 'preflight')


@pytest.mark.parametrize('infrastructure_failure', [False, True])
def test_two_case_budget_continues_box_nonadmission_but_stops_infrastructure_failure(tmp_path, monkeypatch, infrastructure_failure):
    recorder = RunRecorder(tmp_path / 'batch', {}, {'run_id': 'batch'})
    called = []
    monkeypatch.setattr(probe, 'sealed_condition', lambda p: {'status': 'not_admitted'})
    monkeypatch.setattr(probe, 'file_hash', lambda _: 'fixed-output-hash')
    def launch(case):
        called.append(case)
        if infrastructure_failure:
            raise RuntimeError('failed native worker')
    try:
        if infrastructure_failure:
            with pytest.raises(RuntimeError, match='failed native worker'):
                probe.execute_two(recorder, launch)
            assert called == list(probe.ORDER[:1])
        else:
            results = probe.execute_two(recorder, launch)
            assert called == list(probe.ORDER) and len(results) == 2
            assert all(r['status'] == 'not_admitted' for r in results)
    finally:
        recorder.close()


class Tensor:
    def __init__(self, array): self.array = array
    def to(self, _device): return self
    def float(self): return self
    def numpy(self): return self.array


@pytest.mark.parametrize('mismatch', [None, 'input', 'loaded'])
def test_box_worker_checks_loaded_and_exact_input_before_raw_then_box_seal(tmp_path, monkeypatch, mismatch):
    monkeypatch.setattr(probe, '_STARTED', False)
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '2')
    recorder = RunRecorder(tmp_path / 'batch', {}, {'run_id': 'batch'})
    batch = recorder.output
    recorder.record('condition_intent', {'ordinal': 0, 'case_id': probe.ORDER[0]})
    recorder.close()
    (batch / 'review.json').write_text('{}')
    (batch / 'request.json').write_text(json.dumps({'preflight': 'fake', 'preflight_sha256': 'fake',
        'review_sha256': file_hash(batch / 'review.json')}))
    model, metadata = {'fixed': 'model'}, {'input_token_ids': [1, 2]}
    loaded = {'model_config': {'original': 'config'}, 'model_training': False, 'dtype': 'torch.bfloat16',
        'parameter_dtype': 'torch.bfloat16', 'tokenizer_model_max_length': 16384, 'eos_token_id': 151645}
    preflight = {'source': {'source_root': 'source', 'images': [{'case_id': probe.ORDER[0]}]},
        'model': model, 'source_model_config': loaded['model_config'], 'inputs': [metadata],
        'point_reference': {'cases': [{'loaded': loaded}]}}
    monkeypatch.setattr(probe, 'load_preflight', lambda *_: preflight)
    monkeypatch.setattr(probe, 'check_review', lambda *_: None)
    monkeypatch.setattr(probe, 'code_identity', lambda: {'commit': 'fixed'})
    monkeypatch.setattr(probe, 'model_identity', lambda _: model)
    monkeypatch.setattr(probe, 'versions', lambda: {})
    rgb = np.arange(384 * 384 * 3, dtype=np.uint8).reshape(384, 384, 3)
    monkeypatch.setattr(probe.adapter, 'load_rgb', lambda *_: rgb)
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(manual_seed=lambda _: None))
    from embodied_runtime.adapters import locateanything
    constructors, generations = [], []
    def worker(*args, **kwargs):
        constructors.append(1)
        return SimpleNamespace(processor=object())
    monkeypatch.setattr(locateanything, 'LocateAnythingWorker', worker)
    monkeypatch.setattr(probe.hybrid, 'loaded_configuration', lambda *_:
        {**loaded, 'gpu_name': 'changed'} if mismatch == 'loaded' else loaded)
    actual = {'input_token_ids': [9]} if mismatch == 'input' else metadata
    monkeypatch.setattr(probe, 'prepare_native_input', lambda *_: (
        Tensor(np.zeros(2)), Tensor(np.zeros((3, 2, 2))), actual))
    def call_once(worker, inputs, pixels, output, recorder):
        generations.append(1)
        assert probe.native.SETTINGS == probe.SETTINGS
        recorder.record('call_started', {'model_call_ordinal': 1})
        return probe.native.seal_return(output, recorder, '<box>none</box>', [[[10, 151645]]], .001)
    monkeypatch.setattr(probe.native, 'call_once', call_once)
    if mismatch:
        with pytest.raises(ValueError, match='differs from'):
            probe.condition_run(batch, probe.ORDER[0])
        assert generations == []
    else:
        probe.condition_run(batch, probe.ORDER[0])
        assert generations == [1]
        result = probe.sealed_condition(batch / probe.ORDER[0])
        assert result['status'] == 'not_admitted' and result['holding'] is None
        assert np.array_equal(np.load(batch / probe.ORDER[0] / 'rgb-input.npy'), rgb)
    assert constructors == [1]
    with pytest.raises(RuntimeError, match='fresh Python/model'):
        probe.condition_run(batch, probe.ORDER[1])
