import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_fresh_point as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


def test_changed_source_binding_blocks_before_any_image_decode(tmp_path, monkeypatch):
    path = tmp_path / 'binding.json'
    path.write_text('{}')
    monkeypatch.setattr(probe, 'BINDING', path)
    monkeypatch.setattr(probe.adapter, 'verify_helpers', lambda: None)
    monkeypatch.setattr(probe.adapter, 'load_rgb', lambda *_: pytest.fail('no image decode before admission'))
    with pytest.raises(ValueError, match='qualified composite source'):
        probe.source_packet()


@pytest.mark.parametrize('change', ['freeze_commit', 'preflight_sha256', 'conditions', 'model_calls_authorized', 'physical_gpu'])
def test_exact_review_gate_rejects_changed_freeze_inputs_order_budget_or_gpu(tmp_path, change):
    value = {'status': 'PASS', 'freeze_commit': 'freeze', 'preflight_sha256': 'preflight',
        'protocol_sha256': file_hash(probe.PROTOCOL), 'source_admission_sha256': probe.ADMISSION_SHA,
        'conditions': list(probe.ORDER), 'model_calls_authorized': 4, 'physical_gpu': '2'}
    value[change] = 'different'
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='four-call code/config/input'):
        probe.check_review(path, {'code': {'commit': 'freeze'}}, 'preflight')


def test_cpu_preflight_constructs_only_processor_and_seals_four_exact_inputs(tmp_path, monkeypatch):
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '')
    monkeypatch.setattr(probe, 'code_identity', lambda: {'commit': 'frozen', 'dirty_status': ''})
    source = {'source_root': 'source', 'images': [{'case_id': case} for case in probe.ORDER]}
    monkeypatch.setattr(probe, 'source_packet', lambda: source)
    monkeypatch.setattr(probe, 'model_identity', lambda _: {'content_id': probe.baseline.MODEL_CONTENT_ID})
    monkeypatch.setattr(probe.native, 'source_config', lambda: ({'original': 'config'}, []))
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
        return None, None, {'condition': case, 'input_token_ids': [1, 2], 'question': probe.adapter.QUESTION}
    monkeypatch.setattr(probe.adapter, 'prepare_native_input', prepare)
    path = tmp_path / 'preflight.json'
    value = probe.processor_preflight(path)
    assert calls == ['processor', *probe.ORDER]
    assert value['model_calls'] == value['model_constructions'] == value['physics_calls'] == 0
    assert [r['condition'] for r in value['inputs']] == list(probe.ORDER)
    assert json.loads(path.read_text())['processor_device'] == 'cpu'


def test_nonadmission_does_not_change_four_case_order(tmp_path, monkeypatch):
    recorder = RunRecorder(tmp_path / 'batch', {}, {'run_id': 'batch'})
    called = []
    monkeypatch.setattr(probe, 'sealed_condition', lambda p: {'status': 'not_admitted'})
    monkeypatch.setattr(probe, 'file_hash', lambda _: 'fixed-sensor-hash')
    results = probe.execute_four(recorder, called.append)
    recorder.close()
    assert called == list(probe.ORDER) and len(results) == 4
    assert all(r['status'] == 'not_admitted' for r in results)
    rows, _ = load_records(recorder.output / 'episodes.jsonl')
    assert [r['data']['case_id'] for r in rows if r['kind'] == 'condition_intent'] == list(probe.ORDER)


def test_infrastructure_failure_stops_remaining_calls_without_retry(tmp_path, monkeypatch):
    recorder = RunRecorder(tmp_path / 'batch', {}, {'run_id': 'batch'})
    called = []
    monkeypatch.setattr(probe, 'sealed_condition', lambda p: {'status': 'admitted_rgb_point'})
    monkeypatch.setattr(probe, 'file_hash', lambda _: 'fixed-sensor-hash')
    def launch(case):
        called.append(case)
        if len(called) == 2:
            raise RuntimeError('failed native worker')
    with pytest.raises(RuntimeError, match='failed native worker'):
        probe.execute_four(recorder, launch)
    recorder.close()
    assert called == list(probe.ORDER[:2])


class Tensor:
    def __init__(self, array): self.array = array
    def to(self, _device): return self
    def float(self): return self
    def numpy(self): return self.array


@pytest.mark.parametrize('input_mismatch', [False, True])
def test_worker_calls_once_only_after_exact_input_and_retains_raw_before_sensor(tmp_path, monkeypatch, input_mismatch):
    monkeypatch.setattr(probe, '_STARTED', False)
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '2')
    batch = tmp_path / 'batch'
    recorder = RunRecorder(batch, {}, {'run_id': 'batch'})
    recorder.record('condition_intent', {'ordinal': 0, 'case_id': probe.ORDER[0]})
    recorder.close()
    (batch / 'review.json').write_text('{}')
    (batch / 'request.json').write_text(json.dumps({'preflight': 'fake', 'preflight_sha256': 'fake',
        'review_sha256': file_hash(batch / 'review.json')}))
    model, metadata = {'fixed': 'model'}, {'input_token_ids': [1, 2]}
    preflight = {'source': {'source_root': 'source', 'images': [{'case_id': probe.ORDER[0]}]},
        'model': model, 'source_model_config': {'original': 'config'}, 'inputs': [metadata]}
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
    monkeypatch.setattr(probe, 'loaded_configuration', lambda *_: {
        'model_config': {'original': 'config'}, 'model_training': False, 'dtype': 'torch.bfloat16',
        'parameter_dtype': 'torch.bfloat16', 'tokenizer_model_max_length': 16384, 'eos_token_id': 151645})
    actual = {'input_token_ids': [9]} if input_mismatch else metadata
    monkeypatch.setattr(probe.adapter, 'prepare_native_input', lambda *_: (
        Tensor(np.zeros(2)), Tensor(np.zeros((3, 2, 2))), actual))
    def call_once(worker, inputs, pixels, output, recorder):
        generations.append(1)
        recorder.record('call_started', {'model_call_ordinal': 1})
        return probe.native.seal_return(output, recorder, '<box>none</box>', [[[10, 151645]]], .001)
    monkeypatch.setattr(probe.native, 'call_once', call_once)
    if input_mismatch:
        with pytest.raises(ValueError, match='differs from reviewed CPU'):
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
