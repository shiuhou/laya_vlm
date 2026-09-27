from contextlib import nullcontext
import json
import signal
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_point_region_control as probe
from embodied_runtime.experiments.records import RunRecorder, load_records


def frame():
    return {'rgb': np.zeros((4, 4, 3), dtype=np.uint8), 'depth_m': np.ones((4, 4)),
            'intrinsics': np.eye(3), 'camera_to_world': np.eye(4)}


def raw(text='<box><275><275></box>', tokens=None):
    return {'raw_response': text, 'raw_response_type': 'str',
            'observed_decoded_token_sequences': [[[12, 99] if tokens is None else tokens]]}


def test_native_projection_is_reused_and_ownership_stays_unknown():
    result = probe.analyze_return(raw(), 100, 16384, 99, frame())
    assert result['point']['sample_pixel_xy'] == [1, 1]
    assert result['point']['sample_pixel_center_xy'] == [1.5, 1.5]
    assert result['point']['position_world_m'] == [1.5, 1.5, 1.]
    assert result['resolved_depth_ownership'] is None
    assert result['semantic_confidence'] is None and result['grasp_quality'] is None
    assert not result['semantic_target_identity_verified']


@pytest.mark.parametrize('text,tokens,depth,reason', [
    ('<box><275><275></box>', [12], 1., 'incomplete_or_length_limited'),
    ('<box><275><275></box>', [12]*255+[99], 1., 'incomplete_or_length_limited'),
    ('<box><275><275></box>', [12]*260, 1., 'incomplete_or_length_limited'),
    ('<box><275><275></box>', [12, 99], np.nan, 'invalid_depth'),
    ('<box><1000><275></box>', [12, 99], 1., 'point_out_of_frame'),
    ('<box><100><100><200><200></box>', [12, 99], 1., 'single_box'),
    ('<box><275><275></box><box><375><375></box>', [12, 99], 1., 'multiple_points'),
    ('<box><275><275></box><box>', [12, 99], 1., 'malformed'),
])
def test_invalid_conditions_preserve_all_output_without_salvage(text, tokens, depth, reason):
    sensor = frame()
    sensor['depth_m'][1, 1] = depth
    result = probe.analyze_return(raw(text, tokens), 100, 16384, 99, sensor)
    assert result['status'] == 'not_admitted' and result['point'] is None
    assert result['reason'] == 'point_admission:' + reason
    assert result['raw_output'] == text
    assert result['generation_audit']['actual_generated_token_ids'] == tokens


def test_raw_return_seals_even_when_actual_token_audit_is_missing(tmp_path):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    value = probe.seal_return(recorder.output, recorder, 'malformed native text', [], .1)
    recorder.close()
    with pytest.raises(ValueError, match='token audit unavailable'):
        probe.analyze_return(value, 100, 16384, 99, frame())
    assert json.loads((recorder.output/'generation-return.json').read_text())['raw_response'] == 'malformed native text'
    rows, errors = load_records(recorder.output/'episodes.jsonl')
    assert not errors and rows[-1]['kind'] == 'generation_return_sealed'


class FakeSequence:
    def detach(self):
        return self
    def cpu(self):
        return self
    def tolist(self):
        return [[12, 99]]


@pytest.mark.parametrize('failure', [False, True])
def test_native_call_restores_decoder_and_signal_and_preserves_failure(tmp_path, failure):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    def decoder(*_a, **_k):
        return ['<box><275><275></box>']
    tokenizer = SimpleNamespace(batch_decode=decoder)
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        decoded = kwargs['tokenizer'].batch_decode(FakeSequence())
        if failure:
            raise RuntimeError('native failure after decoded output')
        return decoded[0], 'native extra return preserved'
    worker = SimpleNamespace(tokenizer=tokenizer, model=SimpleNamespace(generate=generate),
                             torch=SimpleNamespace(no_grad=nullcontext))
    previous = signal.getsignal(signal.SIGALRM)
    inputs = {k: object() for k in ('input_ids', 'attention_mask', 'image_grid_hws')}
    if failure:
        with pytest.raises(RuntimeError, match='native failure'):
            probe.call_once(worker, inputs, object(), recorder.output, recorder)
        saved = json.loads((recorder.output/'generation-exception.json').read_text())
    else:
        saved = probe.call_once(worker, inputs, object(), recorder.output, recorder)
        assert saved['raw_response'] == '<box><275><275></box>'
        assert 'native extra return preserved' in saved['returned_value_repr']
    recorder.close()
    assert saved['observed_decoded_token_sequences'] == [[[12, 99]]]
    assert tokenizer.batch_decode is decoder and signal.getsignal(signal.SIGALRM) == previous
    assert len(calls) == 1 and {k: calls[0][k] for k in probe.SETTINGS} == probe.SETTINGS


def test_both_registered_conditions_run_after_nonadmission(tmp_path, monkeypatch):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    called = []
    def launch(condition):
        called.append(condition)
        directory = recorder.output/condition
        directory.mkdir()
        (directory/'sensor-result.json').write_text('{}')
    monkeypatch.setattr(probe, 'sealed_condition', lambda _p: {'status': 'not_admitted'})
    results = probe.execute_pair(recorder, launch)
    recorder.close()
    assert called == ['whole', 'neck']
    assert [r['condition'] for r in results] == called
    assert [r['status'] for r in results] == ['not_admitted', 'not_admitted']


def test_infrastructure_failure_stops_pair_with_no_retry(tmp_path):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    called = []
    def launch(condition):
        called.append(condition)
        raise RuntimeError('infrastructure')
    with pytest.raises(RuntimeError, match='infrastructure'):
        probe.execute_pair(recorder, launch)
    recorder.close()
    assert called == ['whole']


def test_evaluator_does_not_open_proxy_before_both_results_seal(tmp_path, monkeypatch):
    recorder = RunRecorder(tmp_path/'run', {}, {'run_id': 'test'})
    recorder.record('condition_complete', {'condition': 'whole'})
    recorder.close()
    opened = []
    monkeypatch.setattr(probe.np, 'load', lambda *a, **k: opened.append(a))
    with pytest.raises(ValueError, match='both fixed condition rows'):
        probe.evaluate(recorder.output)
    assert not opened and not (recorder.output/'evaluation').exists()
