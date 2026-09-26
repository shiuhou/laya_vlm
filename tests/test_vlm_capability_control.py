from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from embodied_runtime.experiments import vlm_capability_control as control


def test_only_frozen_probes_and_exact_31_calls():
    relation, subgoal = (control.probe_for(name) for name in ('relations', 'subgoals'))
    assert len(relation.PLANNED_CALLS) == 24
    assert len(subgoal.PLANNED_CALLS) == 7
    assert relation.GENERATION == subgoal.GENERATION
    assert relation.GENERATION['max_new_tokens'] == 32
    with pytest.raises(ValueError, match='unregistered'):
        control.probe_for('extra')


def test_model_override_rejects_checkpoint_and_gold_mismatch_without_reading_labels(monkeypatch):
    identity = {'path': control.MODEL_PATH, 'content_id': 'pinned', 'files_sha256': {'weights': 'hash'}}
    registration = {'probes': {'relations': {'source': '/frozen-inputs', 'evaluation_sha256': 'gold-hash'}},
        'model': identity, 'acquisition': {'content_id': 'pinned', 'files_sha256': {'weights': 'hash'},
                                         'acquisition_sha256': 'acquired'}, 'protocol_sha256': 'protocol'}
    monkeypatch.setattr(control, 'load_registration', lambda _: registration)
    monkeypatch.setattr(control, 'file_hash', lambda _: 'registration-hash')
    monkeypatch.setattr(Path, 'read_text', lambda *_: pytest.fail('generator must not read gold'))
    args = SimpleNamespace(capability_registration='/registration', source='/frozen-inputs',
                           evaluation_sha256='gold-hash')
    assert control.registered_model(args, identity)['revision'] == control.REVISION
    for field, value in [('content_id', 'other'), ('path', '/other'), ('files_sha256', {})]:
        changed = {**identity, field: value}
        with pytest.raises(ValueError, match='checkpoint'):
            control.registered_model(args, changed)
    args.evaluation_sha256 = 'new-gold'
    with pytest.raises(ValueError, match='evaluator'):
        control.registered_model(args, identity)


def presentation():
    return {'call_id': 'rgb-0', 'image_index': 0, 'messages': ['fixed text'], 'prompt': 'template',
        'input_ids': [1, 2], 'input_token_count': 2, 'attention_mask': [[1, 1]], 'image_grid_thw': [[1, 2, 2]],
        'processor_pixel_values': 'float32', 'consumed_pixel_values': 'bf16', 'rgb_sha256': 'image',
        'processed_image_size_wh': [28, 28], 'image_pad_token_count': 1}


def test_comparison_reports_native_token_changes_but_rejects_message_image_or_order_changes():
    old = presentation()
    new = {**old, 'input_ids': [1, 2, 3], 'input_token_count': 3}
    result = control.compare_presentations([old], [new])[0]
    assert result['token_count_delta'] == 1
    assert result['equal']['messages'] and not result['equal']['input_ids']
    for key, value in [('messages', ['changed']), ('rgb_sha256', 'changed'), ('call_id', 'rgb-1')]:
        changed = {**new, key: value}
        with pytest.raises(ValueError):
            control.compare_presentations([old], [changed])
    with pytest.raises(ValueError, match='count'):
        control.compare_presentations([old], [])


def test_provider_verification_rejects_bad_hash_size_or_revision(tmp_path, monkeypatch):
    metadata = {'sha': control.REVISION, 'siblings': [{'rfilename': 'model.safetensors', 'size': 4,
        'blobId': 'git', 'lfs': {'sha256': 'weight-hash'}}]}
    receipt = {'name': 'model.safetensors', 'bytes': 4, 'sha256': 'weight-hash',
        'provider_etag': 'weight-hash', 'immutable_url': f'https://huggingface.co/{control.REPO}/resolve/{control.REVISION}/model.safetensors'}
    acquired = {'repo': control.REPO, 'revision': control.REVISION, 'content_id': 'content', 'files': [receipt]}
    import json
    path = tmp_path/'verified-acquisition.json'
    (tmp_path/'pinned-provider-metadata.json').write_text(json.dumps(metadata))
    path.write_text(json.dumps(acquired))
    assert control.acquisition_identity(path)['files_sha256'] == {'model.safetensors': 'weight-hash'}
    for key, value in [('bytes', 5), ('sha256', 'wrong'), ('provider_etag', 'wrong')]:
        changed = deepcopy(acquired)
        changed['files'][0][key] = value
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match='verification'):
            control.acquisition_identity(path)
    acquired['revision'] = 'different'
    path.write_text(json.dumps(acquired))
    with pytest.raises(ValueError, match='checkpoint'):
        control.acquisition_identity(path)


def test_postrun_documentation_commit_permitted_but_scientific_source_change_rejected(tmp_path, monkeypatch):
    import json
    frozen = {'commit': 'before', 'dirty_status': '', 'source_sha256': {'runner.py': 'frozen'}}
    registration = {'version': 'vlm7b-capability-control-v1', 'protocol_sha256': 'protocol',
        'total_unique_calls': 31, 'no_retries': True, 'no_execution': True, 'probes': {},
        'frozen_code': frozen, 'acquisition': {'acquisition_path': 'acquired'}}
    path = tmp_path/'registration.json'
    path.write_text(json.dumps(registration))
    monkeypatch.setattr(control, 'PROBES', {})
    monkeypatch.setattr(control, 'file_hash', lambda _: 'protocol')
    monkeypatch.setattr(control, 'acquisition_identity', lambda _: registration['acquisition'])
    current = {**frozen, 'commit': 'documentation-after'}
    monkeypatch.setattr(control, 'code_identity', lambda: current)
    assert control.load_registration(path, check_code=False) == registration
    with pytest.raises(ValueError, match='code/commit'):
        control.load_registration(path)
    current['source_sha256'] = {'runner.py': 'changed-validator'}
    with pytest.raises(ValueError, match='scientific source'):
        control.load_registration(path, check_code=False)
