from copy import deepcopy
import json

import numpy as np
import pytest

from embodied_runtime.experiments import vlm_world_single_relation as probe


def test_followup_has_fixed_same_images_and_independent_questions_without_slash_template():
    assert len(probe.PLANNED_CALLS) == 24
    for i, field in enumerate(probe.FIELDS):
        calls = probe.PLANNED_CALLS[i*8:(i+1)*8]
        assert [p['image_index'] for p in calls] == [None, 6, 0, 1, 2, 3, 4, 5]
        assert all(p['condition'] == field for p in calls)
        assert '/' not in probe.INSTRUCTIONS[field]
        assert 'Task:' not in probe.INSTRUCTIONS[field]
        assert probe.QUESTIONS[field].strip()[1:] in probe.parent.NEUTRAL
        for other in probe.FIELDS:
            if other != field:
                assert probe.QUESTIONS[other] not in probe.INSTRUCTIONS[field]


@pytest.mark.parametrize('field,text', [('horizontal', 'upright'), ('orientation', 'left'),
    ('gap', 'separated/adjacent'), ('horizontal', 'left.'), ('gap', 'The answer is separated')])
def test_wrong_field_vocabulary_and_malformed_outputs_are_invalid(field, text):
    assert probe.parse_label(text, field) == {'status': 'invalid', 'label': None}


class Tokenizer:
    all_special_ids = [9]

    def decode(self, ids, skip_special_tokens):
        return ''.join({1: 'left', 2: 'upright', 9: '' if skip_special_tokens else '<eos>'}[i] for i in ids)


def fixture(ids=(1, 9)):
    p = {'condition': 'horizontal', 'input_ids': [4, 5], 'consumed_pixel_values': None,
         'image_grid_thw': None, 'attention_mask': [[1, 1]]}
    traces = [{'input_ids': [p['input_ids'] if i == 0 else [ids[i-1]]], 'pixel_values': None,
               'image_grid_thw': None, 'attention_mask': p['attention_mask']} for i in range(len(ids))]
    raw = {'generated_ids': list(ids), 'sequence_ids': p['input_ids']+list(ids), 'forward_traces': traces,
           'raw_decoded_text': Tokenizer().decode(ids, False), 'decoded_text': Tokenizer().decode(ids, True)}
    logits = np.zeros((len(ids), 10))
    for i, token in enumerate(ids):
        logits[i, token] = 1
    return p, raw, logits


def test_native_integrity_audit_and_field_validation_remain_separate():
    p, raw, logits = fixture()
    assert probe.validate_generation(p, raw, logits, Tokenizer(), 9, 10)['status'] == 'valid'
    p, raw, logits = fixture((2, 9))
    result = probe.validate_generation(p, raw, logits, Tokenizer(), 9, 10)
    assert result['status'] == 'invalid' and result['terminal_eos']
    changed = deepcopy(raw)
    changed['forward_traces'][0]['input_ids'] = [[6, 7]]
    with pytest.raises(ValueError, match='consumed input'):
        probe.validate_generation(p, changed, logits, Tokenizer(), 9, 10)


def calls_and_labels():
    truth = [('uncertain', 'uncertain', 'left', 'right', 'left', 'right', 'aligned', 'aligned'),
             ('uncertain', 'uncertain', 'separated', 'separated', 'adjacent', 'adjacent', 'separated', 'separated'),
             ('uncertain', 'uncertain', 'upright', 'upright', 'upright', 'upright', 'diagonal', 'diagonal')]
    values = [v for field in truth for v in field]
    calls = [{**p, 'status': 'valid', 'label': value} for p, value in zip(probe.PLANNED_CALLS, values)]
    labels = {'calls': [{'call_id': p['call_id'], 'acceptable_labels': [value]}
                        for p, value in zip(probe.PLANNED_CALLS, values)]}
    return calls, labels


def test_dependent_pairs_coherence_and_abstention_are_reported_separately():
    calls, labels = calls_and_labels()
    result = probe.score_calls(calls, labels)
    assert result['scene_fields']['useful_correct'] == 18
    assert result['abstention_controls']['correct'] == 6
    assert result['coherent_scene_count'] == result['coherent_scene_denominator'] == 6
    assert all(p['both_correct'] for p in result['mirror_pairs'])
    for call in calls:
        call['label'] = 'uncertain'
    result = probe.score_calls(calls, labels)
    assert result['scene_fields']['useful_correct'] == result['coherent_scene_count'] == 0
    assert result['abstention_controls']['correct'] == 6
    assert all(p['mirror_consistent'] and not p['both_correct'] for p in result['mirror_pairs'])
    with pytest.raises(ValueError, match='twenty-four'):
        probe.score_calls(calls[:-1], labels)


def test_followup_rejects_image_or_settings_changes(tmp_path, monkeypatch):
    source = tmp_path/'parent'
    source.mkdir()
    (source/'manifest.json').write_text('{}')
    (source/'image.png').write_bytes(b'image bytes')
    original = {'source_type': 'test', 'examples': [{'rgb_artifact': 'image.png',
                'rgb_sha256': probe.file_hash(source/'image.png')}]}
    monkeypatch.setattr(probe.parent, 'load_inputs', lambda _: original)
    output = tmp_path/'child'
    manifest = probe.prepare(source, output)
    assert (output/'image.png').read_bytes() == b'image bytes'
    manifest['instructions']['gap'] += ' Close gripper.'
    (output/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='settings'):
        probe.load_inputs(output)
