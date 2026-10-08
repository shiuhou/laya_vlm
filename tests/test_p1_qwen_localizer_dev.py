import hashlib
import json
import numpy as np
import pytest
from PIL import Image

from embodied_runtime.adapters.qwen3vl_grounding import generation_audit, messages_for, json_metadata, QUERY
from embodied_runtime.contracts import content_hash, ProtocolError
from embodied_runtime.experiments.p1_qwen_localizer_dev import execute_requests
from embodied_runtime.perception.grounding_observation import parse_qwen_grounding


def test_actual_eos_context_budget_and_fresh_request_messages():
    audit = generation_audit([5, 9], input_count=8, max_new_tokens=256,
                             model_max_length=10, eos_token_ids=[9])
    assert audit['effective_limit'] == 2
    assert audit['complete_generation'] and audit['length_limit_reached']
    missing = generation_audit([5, 6], input_count=8, max_new_tokens=256,
                               model_max_length=10, eos_token_ids=[9])
    reply = parse_qwen_grounding('[]', 384, 256, mode='BOX', audit=missing)
    assert reply.reason == 'INCOMPLETE_GENERATION'
    first = messages_for('BOX')
    first.append({'role': 'assistant', 'content': 'old result'})
    second = messages_for('POINT')
    assert len(second) == 2 and 'old result' not in json.dumps(second)
    assert QUERY in second[1]['content'][1]['text']


def test_native_hf_config_integer_keys_are_losslessly_json_metadata():
    config = {'model_type': 'qwen3_vl', 'text_config': {'id2label': {0: 'LABEL_0', 1: 'LABEL_1'},
              'eos_token_id': [151645, 151643]}, 'image_mean': np.array([.5, .5, .5]),
              'resample': Image.Resampling.BICUBIC}
    safe = json_metadata(config)
    assert safe['text_config']['id2label'] == {'0': 'LABEL_0', '1': 'LABEL_1'}
    assert len(content_hash(safe)) == 64
    assert safe['resample'] == 3
    assert config['text_config']['id2label'] == {0: 'LABEL_0', 1: 'LABEL_1'}
    with pytest.raises(ProtocolError, match='collide'):
        json_metadata({'id2label': {0: 'first', '0': 'second'}})


def test_typed_box_failure_does_not_suppress_independent_point_or_retry(tmp_path):
    rgb = np.zeros((256, 384, 3), dtype=np.uint8)
    digest = hashlib.sha256(rgb.tobytes()).hexdigest()
    source = dict(rgb_shape=list(rgb.shape), rgb_sha256=digest)

    class Worker:
        model_identity = {'mock': 'model'}
        processor_identity = {'mock': 'processor'}
        environment_identity = {'mock': 'environment'}
        calls = []

        def infer(self, image, *, mode, query, max_new_tokens):
            self.calls.append(mode)
            raw = '[]' if mode == 'BOX' else '[{"label":"drawer_front_pushable","point_2d":[500,500]}]'
            audit = generation_audit([5, 9], input_count=1, max_new_tokens=max_new_tokens,
                                     model_max_length=1024, eos_token_ids=[9])
            typed = parse_qwen_grounding(raw, 384, 256, mode=mode, audit=audit)
            return dict(raw_output=raw, typed=typed, audit=audit, terminal_special_tokens=(),
                input_evidence=dict(rgb_sha256=digest, query=query, input_token_ids=[1]), timing={})

    worker = Worker()
    frame = dict(recording='/test-recording', camera_id='robot0_eye_in_hand',
                 source_identity=source, view={'rgb': rgb})
    result = execute_requests(worker, [frame], tmp_path, max_new_tokens=256, request_timeout_s=5)
    assert worker.calls == ['BOX', 'POINT']
    assert result['runtime_failure'] is None
    record = result['records'][0]
    assert record['box_status'] == 'TYPED_REJECTED'
    assert record['point_status'] == 'COMPLETE'
    assert record['point_observation']['typed']['point_xy_px'] == [192., 128.]
    assert record['point_observation']['calibrated_confidence'] is None
