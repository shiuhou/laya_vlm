from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

from embodied_runtime.experiments import vlm_world_relations as probe
from embodied_runtime.experiments.records import file_hash


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    source = tmp_path/'parent'
    source.mkdir()
    (source/'manifest.json').write_text('{}')
    monkeypatch.setattr(probe.parent, 'load_inputs', lambda _: {'source_type': 'test_rgb'})
    for i in probe.PARENT_INDICES:
        pixels = np.zeros((600, 600, 3), dtype=np.uint8)
        pixels[:, :200] = [13+i, 21, 45]
        Image.fromarray(pixels).save(source/f'rgb-{i}.png')
    output = tmp_path/'inputs'
    manifest = probe.prepare(source, output)
    return output, manifest


def test_registered_images_are_exact_copies_mirrors_and_distinct_gray_control(prepared):
    output, manifest = prepared
    assert probe.load_inputs(output) == manifest
    for i in range(0, 6, 2):
        original, mirrored = [np.asarray(Image.open(output/f'image-{j}.png')) for j in (i, i+1)]
        assert np.array_equal(original[:, ::-1], mirrored)
        assert not np.array_equal(original, mirrored)
    assert np.all(np.asarray(Image.open(output/'image-6.png')) == 128)
    assert len(probe.PLANNED_CALLS) == 12
    assert sum(p['image_index'] is None for p in probe.PLANNED_CALLS) == 2


@pytest.mark.parametrize('defect', ['pixel_with_rehashed_manifest', 'transform', 'instruction', 'parent'])
def test_tampering_rejected_including_valid_image_hash_with_wrong_transformation(prepared, defect):
    output, manifest = prepared
    if defect == 'pixel_with_rehashed_manifest':
        Image.new('RGB', (600, 600), 'red').save(output/'image-1.png')
        manifest['examples'][1]['rgb_sha256'] = file_hash(output/'image-1.png')
    elif defect == 'transform':
        manifest['examples'][1]['transform'] = 'identity'
    elif defect == 'instruction':
        manifest['instructions']['neutral'] += ' Act now.'
    else:
        manifest['examples'][0]['parent_rgb_sha256'] = '0'*64
    (output/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        probe.load_inputs(output)


class Processor:
    image_processor = SimpleNamespace(merge_size=2, patch_size=14)
    image_token = 'image'
    tokenizer = SimpleNamespace(model_max_length=4096, convert_tokens_to_ids=lambda _: 4)

    def apply_chat_template(self, messages, **kwargs):
        return json.dumps(messages)

    def __call__(self, *, text, images, return_tensors, truncation):
        import torch
        assert truncation is False
        result = {'input_ids': torch.tensor([[4, 5] if images else [5, 5]]),
                  'attention_mask': torch.ones((1, 2), dtype=torch.long)}
        if images:
            result.update(image_grid_thw=torch.tensor([[1, 2, 2]]), pixel_values=torch.ones((4, 10)))
        return result


def test_relation_question_constant_with_exact_task_prefix_and_true_absent_image(prepared):
    output, manifest = prepared
    presentations = [probe.prepare_call(Processor(), output, p, manifest['examples'])[1]
                     for p in probe.PLANNED_CALLS]
    for p in presentations:
        content = p['messages'][0]['content']
        assert content[-1] == {'type': 'text', 'text': probe.INSTRUCTIONS[p['condition']]}
        assert len(content) == (1 if p['image_index'] is None else 2)
        assert (p['consumed_pixel_values'] is None) == (p['image_index'] is None)
    assert probe.INSTRUCTIONS['task'] == probe.TASK_PREFIX + probe.INSTRUCTIONS['neutral']
    assert presentations[0]['consumed_pixel_values'] is None
    assert presentations[1]['consumed_pixel_values'] is not None


@pytest.mark.parametrize('text', ['left,separated,upright.', 'left,separated',
    'I think left,separated,upright', 'left,separated,upright,uncertain', 'left,held,upright'])
def test_malformed_answers_never_salvaged(text):
    assert probe.parse_label(text) == {'status': 'invalid', 'label': None}


def test_only_registered_whitespace_normalization():
    assert probe.parse_label(' left, separated , upright\n') == {
        'status': 'valid', 'label': 'left,separated,upright'}


def evaluation_and_calls():
    gold = ['uncertain,uncertain,uncertain']*2 + [
        'left,separated,upright', 'right,separated,upright',
        'left,adjacent,upright', 'right,adjacent,upright',
        'aligned,separated,diagonal', 'aligned,separated,diagonal'] + [
        'uncertain,uncertain,uncertain', 'left,separated,upright',
        'left,adjacent,upright', 'aligned,separated,diagonal']
    evaluation = {'calls': [{'call_id': p['call_id'], 'acceptable_fields': [[v] for v in label.split(',')]}
                            for p, label in zip(probe.PLANNED_CALLS, gold)]}
    calls = [{**p, 'status': 'valid', 'label': label} for p, label in zip(probe.PLANNED_CALLS, gold)]
    return evaluation, calls


def test_all_uncertain_may_pass_mirror_consistency_but_has_zero_useful_scene_coverage():
    evaluation, calls = evaluation_and_calls()
    for call in calls:
        call['label'] = 'uncertain,uncertain,uncertain'
    result = probe.score_calls(calls, evaluation)
    assert result['neutral_scenes']['useful_correct_fields'] == 0
    assert result['neutral_scenes']['denominator_fields'] == 18
    assert result['abstention_controls']['all_field_agreements'] == 3
    assert all(p['mirror_consistent'] and not p['both_correct'] for p in result['mirror_pairs'])


def test_correct_dependent_pairs_and_context_degradation_reported_separately():
    evaluation, calls = evaluation_and_calls()
    calls[-1].update(status='invalid', label=None)
    result = probe.score_calls(calls, evaluation)
    assert result['neutral_scenes']['all_field_agreements'] == 6
    assert result['neutral_scenes']['useful_correct_fields'] == 18
    assert result['task_scenes']['all_field_agreements'] == 2
    assert result['task_scenes']['invalid_count'] == 1
    assert result['task_prefix_comparison'][-1]['changed']
    assert all(p['both_correct'] for p in result['mirror_pairs'])
    with pytest.raises(ValueError, match='twelve'):
        probe.score_calls(calls[:-1], evaluation)
    changed = deepcopy(evaluation)
    changed['calls'][0]['acceptable_fields'][0] = ['holding']
    with pytest.raises(ValueError, match='vocabulary'):
        probe.score_calls(calls, changed)
