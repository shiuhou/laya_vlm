from contextlib import nullcontext
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_slow_point as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


@pytest.mark.parametrize('fails', [False, True])
def test_real_native_call_gets_only_mode_change_and_restores_exact_binding(tmp_path, fails):
    original = probe.native.SETTINGS
    original_values = dict(original)
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        assert probe.native.SETTINGS is not original
        if fails:
            raise RuntimeError('model failed')
        return '<box>none</box><|im_end|>'
    tokenizer = SimpleNamespace(batch_decode=lambda *_: [])
    decode = tokenizer.batch_decode
    worker = SimpleNamespace(tokenizer=tokenizer, model=SimpleNamespace(generate=generate),
        torch=SimpleNamespace(no_grad=nullcontext))
    recorder = RunRecorder(tmp_path / 'case', {}, {'run_id': 'case'})
    inputs = {'input_ids': object(), 'attention_mask': object(), 'image_grid_hws': object()}
    pixels = object()
    try:
        if fails:
            with pytest.raises(RuntimeError, match='model failed'):
                probe.slow_call_once(worker, inputs, pixels, recorder.output, recorder)
        else:
            probe.slow_call_once(worker, inputs, pixels, recorder.output, recorder)
    finally:
        recorder.close()
    assert probe.native.SETTINGS is original and original == original_values
    assert tokenizer.batch_decode is decode
    assert len(calls) == 1
    kwargs = calls[0]
    assert {key: kwargs[key] for key in original} == probe.SLOW_SETTINGS
    assert [key for key in original if kwargs[key] != original[key]] == ['generation_mode']
    assert set(kwargs) == set(original) | set(inputs) | {'pixel_values', 'tokenizer'}
    assert kwargs['pixel_values'] is pixels and kwargs['tokenizer'] is tokenizer
    assert all(kwargs[key] is value for key, value in inputs.items())
    assert json.loads((recorder.output / 'generation-settings.json').read_text()) == probe.SLOW_SETTINGS
    rows, errors = load_records(recorder.output / 'episodes.jsonl')
    assert not errors
    assert [row['kind'] for row in rows].count('call_started') == 1
    assert rows[-1]['kind'] == ('generation_exception_sealed' if fails else 'generation_return_sealed')


@pytest.mark.parametrize('change', ['freeze_commit', 'preflight_sha256', 'conditions',
    'model_calls_authorized', 'physical_gpu', 'generation_settings', 'hybrid_preflight_sha256', 'hybrid_audit_sha256'])
def test_review_gate_rejects_changed_control(tmp_path, change):
    value = {'status': 'PASS', 'freeze_commit': 'freeze', 'preflight_sha256': 'preflight',
        'protocol_sha256': file_hash(probe.PROTOCOL), 'source_admission_sha256': probe.hybrid.ADMISSION_SHA,
        'conditions': list(probe.ORDER), 'model_calls_authorized': 2, 'physical_gpu': '2',
        'generation_settings': probe.SLOW_SETTINGS, 'hybrid_preflight_sha256': probe.HYBRID_PREFLIGHT_SHA,
        'hybrid_audit_sha256': probe.HYBRID_AUDIT_SHA}
    value[change] = 'different'
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='two-call slow code/config/input'):
        probe.check_review(path, {'code': {'commit': 'freeze'}}, 'preflight')


@pytest.mark.parametrize('input_mismatch', [False, True])
def test_cpu_preflight_requires_exact_two_archived_inputs(tmp_path, monkeypatch, input_mismatch):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '')
    monkeypatch.setattr(probe, 'code_identity', lambda: {'commit': 'frozen', 'dirty_status': ''})
    source = {'source_root': 'source', 'images': [{'case_id': case} for case in probe.hybrid.ORDER]}
    model = {'content_id': probe.baseline.MODEL_CONTENT_ID}
    metadata = [{'condition': case, 'input_token_ids': [1, 2]} for case in probe.hybrid.ORDER]
    old = {'source': source, 'versions': {}, 'model': model, 'inputs': metadata,
        'source_model_config': {'original': 'config'}}
    monkeypatch.setattr(probe, 'hybrid_packet', lambda: ({'baseline': 'fixed'}, old))
    monkeypatch.setattr(probe, 'model_identity', lambda _: model)
    reference = tmp_path / 'reference'
    reference.mkdir()
    (reference / 'manifest.json').write_text(json.dumps({'versions': {}}))
    def source_config():
        assert probe.native.SETTINGS == probe.HYBRID_SETTINGS
        return old['source_model_config'], [{'directory': str(reference)}]
    monkeypatch.setattr(probe.native, 'source_config', source_config)
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
    def prepare(processor, rgb, case):
        calls.append(case)
        item = dict(metadata[list(probe.ORDER).index(case)])
        if input_mismatch:
            item['input_token_ids'] = [9]
        return None, None, item
    monkeypatch.setattr(probe.adapter, 'prepare_native_input', prepare)
    path = tmp_path / 'preflight.json'
    if input_mismatch:
        with pytest.raises(ValueError, match='exact archived hybrid postevent inputs'):
            probe.processor_preflight(path)
        assert not path.exists()
    else:
        value = probe.processor_preflight(path)
        assert value['model_calls'] == value['model_constructions'] == value['physics_calls'] == 0
        assert value['inputs'] == metadata[:2] and value['settings'] == probe.SLOW_SETTINGS
    assert calls == ['processor', *probe.ORDER]


@pytest.mark.parametrize('infrastructure_failure', [False, True])
def test_fixed_two_case_budget_continues_nonadmission_but_stops_failure(tmp_path, monkeypatch, infrastructure_failure):
    recorder = RunRecorder(tmp_path / 'batch', {}, {'run_id': 'batch'})
    called = []
    monkeypatch.setattr(probe.hybrid, 'sealed_condition', lambda p: {'status': 'not_admitted'})
    monkeypatch.setattr(probe, 'file_hash', lambda _: 'fixed-sensor-hash')
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


def test_changed_archived_baseline_blocks_before_source_or_processor(tmp_path, monkeypatch):
    path = tmp_path / 'old.json'
    path.write_text('{}')
    monkeypatch.setattr(probe, 'HYBRID_PREFLIGHT', path)
    monkeypatch.setattr(probe.hybrid, 'source_packet', lambda: pytest.fail('source gate not reached'))
    with pytest.raises(ValueError, match='audited hybrid baseline'):
        probe.hybrid_packet()


class Tensor:
    def __init__(self, array): self.array = array
    def to(self, _device): return self
    def float(self): return self
    def numpy(self): return self.array


@pytest.mark.parametrize('mismatch', [None, 'input', 'loaded'])
def test_cold_worker_checks_hybrid_loaded_and_cpu_input_before_one_call(tmp_path, monkeypatch, mismatch):
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
        'hybrid_reference': {'cases': [{'loaded': loaded}]}}
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
    monkeypatch.setattr(probe.adapter, 'prepare_native_input', lambda *_: (
        Tensor(np.zeros(2)), Tensor(np.zeros((3, 2, 2))), actual))
    def call_once(worker, inputs, pixels, output, recorder):
        generations.append(1)
        assert probe.native.SETTINGS == probe.SLOW_SETTINGS
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
        result = probe.hybrid.sealed_condition(batch / probe.ORDER[0])
        assert result['status'] == 'not_admitted' and result['holding'] is None
        assert np.array_equal(np.load(batch / probe.ORDER[0] / 'rgb-input.npy'), rgb)
    assert constructors == [1]
    with pytest.raises(RuntimeError, match='fresh Python/model'):
        probe.condition_run(batch, probe.ORDER[1])
