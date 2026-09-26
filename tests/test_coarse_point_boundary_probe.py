from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from embodied_runtime.experiments import coarse_point_boundary_probe as boundary
from embodied_runtime.experiments.records import load_records


def args(tmp_path):
    return SimpleNamespace(output=str(tmp_path / 'new-run'), baseline_source=str(tmp_path / 'baseline'),
        steps=40, seed=1, init_state_id=0, device='cuda', locateanything_path='frozen-model',
        libero_root='libero', config_dir='config', timeout_s=900., condition='rule')


def prior_config(arguments):
    return {**vars(arguments), 'steps':20, 'version':boundary.base.VERSION,
            'protocol_sha256':'parent-protocol-hash'}


def test_wrapper_delegates_unchanged_arguments_and_only_adds_profile(tmp_path, monkeypatch):
    arguments = args(tmp_path)
    before = deepcopy(vars(arguments))
    seen = {}
    monkeypatch.setattr(boundary, 'frozen_baseline', lambda _:prior_config(arguments))
    def capture(actual, **kwargs):
        seen.update(arguments=actual, **kwargs)
        return actual.output
    monkeypatch.setattr(boundary.base, 'run', capture)
    assert boundary.run(arguments) == arguments.output
    assert seen['arguments'] is arguments and vars(arguments) == before
    assert seen['protocol'] == boundary.PROTOCOL
    profile = seen['experiment_profile']
    assert profile['max_executed_primitives'] == profile['absolute_budget_ceiling'] == 40
    assert profile['base_policy_version'] == boundary.base.VERSION
    assert profile['baseline_commit'] == boundary.BASELINE_COMMIT
    assert profile['baseline_sha256'] == boundary.BASELINE_SHA256
    assert profile['fresh_reset'] and profile['no_automatic_budget_extension']
    assert not profile['archived_controls_executed'] and not profile['archived_state_restored']
    assert profile['changed_behavior'] == 'execution_budget_only'


@pytest.mark.parametrize('change', [
    {'steps':41}, {'steps':0}, {'seed':2}, {'init_state_id':1},
    {'condition':'hold'}, {'timeout_s':901.}, {'timeout_s':0.},
])
def test_out_of_profile_rejected_before_source_read_or_execution(tmp_path, monkeypatch, change):
    arguments = args(tmp_path)
    vars(arguments).update(change)
    monkeypatch.setattr(boundary, 'frozen_baseline', lambda _:pytest.fail('must not read parent'))
    monkeypatch.setattr(boundary.base, 'run', lambda *a, **k:pytest.fail('must not execute'))
    with pytest.raises(ValueError, match='at most 40'):
        boundary.run(arguments)


def test_parent_output_cannot_be_reused(tmp_path):
    arguments = args(tmp_path)
    arguments.output = arguments.baseline_source
    with pytest.raises(ValueError, match='historical baseline'):
        boundary.validate_args(arguments)


def test_original_cli_still_rejects_action_21_before_execution(monkeypatch, tmp_path):
    monkeypatch.setattr('sys.argv', ['coarse_point_probe', '--output', str(tmp_path / 'unused'), '--steps', '21'])
    monkeypatch.setattr(boundary.base, 'run', lambda *a, **k:pytest.fail('original CLI cap must remain 20'))
    with pytest.raises(ValueError, match='bounded budget'):
        boundary.base.main()


def test_source_hash_is_checked_before_loading_any_world_or_model(tmp_path, monkeypatch):
    arguments = args(tmp_path)
    Path(arguments.baseline_source).mkdir()
    (Path(arguments.baseline_source) / 'episodes.jsonl').write_text('{}\n')
    monkeypatch.setattr(boundary.base, 'run', lambda *a, **k:pytest.fail('must not construct world/model'))
    with pytest.raises(ValueError, match='baseline identity'):
        boundary.run(arguments)


def test_settings_change_from_parent_rejected(tmp_path, monkeypatch):
    arguments = args(tmp_path)
    previous = prior_config(arguments)
    arguments.device = 'cpu'
    monkeypatch.setattr(boundary, 'frozen_baseline', lambda _:previous)
    monkeypatch.setattr(boundary.base, 'run', lambda *a, **k:pytest.fail('settings must match'))
    with pytest.raises(ValueError, match='settings differ'):
        boundary.run(arguments)


@pytest.mark.parametrize('custom_metadata', [False, True])
def test_shared_runner_records_protocol_profile_without_changing_default(tmp_path, monkeypatch, custom_metadata):
    arguments = args(tmp_path)
    arguments.steps = 20
    protocol = tmp_path / 'new-protocol.md'
    protocol.write_text('This is the separate boundary-finding protocol.\n')
    # Stop before World/model construction; CPU-only check of recorder metadata.
    monkeypatch.setattr(boundary.base, 'model_identity', lambda _: {'content_id':'wrong-checkpoint'})
    kwargs = {'protocol':protocol, 'experiment_profile':{'name':'metadata-only'}} if custom_metadata else {}
    with pytest.raises(ValueError, match='checkpoint differs'):
        boundary.base.run(arguments, **kwargs)
    rows, errors = load_records(Path(arguments.output) / 'episodes.jsonl')
    assert not errors
    config = next(r['data']['resolved_config'] for r in rows if r['kind'] == 'run_start')
    copied = (Path(arguments.output) / 'protocol.md').read_bytes()
    if custom_metadata:
        assert config['experiment_profile'] == {'name':'metadata-only'}
        assert copied == protocol.read_bytes()
    else:
        assert 'experiment_profile' not in config
        assert copied == boundary.base.PROTOCOL.read_bytes()
    assert config['version'] == boundary.base.VERSION
    assert config['settings'] == boundary.base.SETTINGS
    assert config['oracle_in_decision'] is False
    assert not any(r['kind'] in ('environment','decision_boundary','control_started') for r in rows)


def test_real_frozen_parent_is_complete_budget_evidence_when_available():
    source = Path('runs/autonomous-research/coarse-point-rule-01')
    if not (source / 'episodes.jsonl').exists():
        pytest.skip('frozen parent evidence unavailable')
    config = boundary.frozen_baseline(source)
    assert config['steps'] == 20 and config['condition'] == 'rule'
    assert config['seed'] == 1 and config['init_state_id'] == 0
