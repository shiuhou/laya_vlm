import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_additional_stationary_grasp as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records
from test_task2_point_anchor_grasp_transfer import frame, synthetic_suffix


def test_original_helper_defaults_preserve_registered_four_cell_behavior():
    prior = probe.prior
    assert prior.Intervention('whole-close').schedule == (('close_or_hold', 'GRASP'), ('lift', 'MV_UP'))
    assert prior.Intervention('neck-open_hold').schedule == (('close_or_hold', 'STOP'), ('lift', 'MV_UP'))
    assert prior.Intervention('whole-close').after_primitive is None
    assert inspect.signature(prior.AuxiliaryReplay).parameters['expected_count'].default == 16
    assert inspect.signature(prior.worker).parameters['auxiliary_count'].default == 16
    assert inspect.signature(prior.run_matrix).parameters['order'].default == prior.ORDER
    assert inspect.signature(prior.run_matrix).parameters['scripted_action_count'].default == 2
    assert inspect.signature(prior.run_matrix).parameters['module'].default == prior.MODULE


@pytest.mark.parametrize('condition', probe.ORDER)
def test_exactly_one_extra_grasp_then_lift_with_24_control_images(tmp_path, monkeypatch, condition):
    boundaries = []
    def gate(recorder, selected, offset, step):
        rows, errors = load_records(recorder.output / 'episodes.jsonl')
        assert not errors
        actions = [r['data'] for r in rows if r['kind'] == 'action_completed']
        assert len(actions) == offset + 1
        assert rows[-1]['kind'] == 'endpoint'
        boundaries.append((selected, offset, step))
    monkeypatch.setattr(probe, 'verify_first_grasp', gate)
    trial = synthetic_suffix(tmp_path, monkeypatch, condition, factory=probe.intervention)
    assert trial.error is None and trial.calls == ['GRASP', 'GRASP', 'MV_UP']
    assert boundaries == [(condition, i, 30 + i) for i in range(3)]
    assert trial.result['completed_actions'] == 33 and trial.result['scripted_completed_actions'] == 3
    assert [r['phase'] for r in trial.suffix.sensors] == ['close_or_hold'] * 8 + ['additional_close'] * 8 + ['lift'] * 8
    assert len(trial.suffix.labels) == 24 and not any(r['label']['valid_grasp_relation'] for r in trial.suffix.labels)
    assert all(r['data']['command'][-1] == 1 for r in trial.rows if r['kind'] == 'control_completed')
    probe.prior.check_collection(trial.directory, scripted_action_count=3)
    verifier = probe.prior.AuxiliaryReplay(trial.directory, expected_count=24)
    for row in trial.suffix.sensors:
        trial.world.data.time, trial.world.obs = row['capture_sim_time'], row['own_observations']
        verifier(trial.world, {'step': row['after_step'], 'native_phase': row['phase']}, row['control'])
    assert not verifier.expected and len(verifier.checked) == 24


def test_first_grasp_prefix_mismatch_blocks_added_interval_after_preserving_endpoint(tmp_path, monkeypatch):
    def mismatch(*_):
        raise ValueError('first-GRASP prefix mismatch')
    monkeypatch.setattr(probe, 'verify_first_grasp', mismatch)
    trial = synthetic_suffix(tmp_path, monkeypatch, 'whole-close', factory=probe.intervention)
    assert isinstance(trial.error, ValueError) and trial.calls == ['GRASP']
    assert len(trial.suffix.sensors) == 8 and sum(r['kind'] == 'endpoint' for r in trial.rows) == 1
    failure = next(r['data'] for r in trial.rows if r['kind'] == 'intervention_failure')
    assert failure['total_completed_actions'] == failure['total_attempted_actions'] == 31


@pytest.mark.parametrize('failure', ['runtime', 'validator', 'contact', 'count'])
@pytest.mark.parametrize('failure_action', [0, 1, 2])
def test_every_failure_stops_extra_schedule_without_retry(tmp_path, monkeypatch, failure, failure_action):
    boundaries = []
    monkeypatch.setattr(probe, 'verify_first_grasp', lambda _r, _c, offset, _s: boundaries.append(offset))
    trial = synthetic_suffix(tmp_path, monkeypatch, 'neck-close', factory=probe.intervention,
                             fail=failure, failure_action=failure_action)
    assert trial.error is not None and trial.calls == ['GRASP', 'GRASP', 'MV_UP'][:failure_action + 1]
    assert boundaries == list(range(failure_action))
    failure_row = next(r['data'] for r in trial.rows if r['kind'] == 'intervention_failure')
    assert failure_row['phase'] == probe.SCHEDULE[failure_action][0]
    assert failure_row['total_attempted_actions'] == 31 + failure_action
    assert failure_row['total_completed_actions'] == 30 + failure_action + (failure != 'runtime')


def prefix_fixture(tmp_path, monkeypatch, *, changed=None, image_changed=False):
    source = tmp_path / 'source' / 'whole-close'
    monkeypatch.setattr(probe, 'SOURCE', source.parent)
    def populate(directory, current):
        recorder = RunRecorder(directory, {}, {'run_id': 'fresh' if current else 'source'})
        recorder.capture(frame())
        recorder.record('decision', {'selected': 'STOP', 'step': 0})
        recorder.record('approach_prefix_verified', {'exact': True})
        recorder.record('action_started', {'token': 'GRASP', 'step': 0, 'native_phase': 'close_or_hold'})
        for kind in ('control_started', 'native_before', 'native_after', 'control_completed', 'action_completed'):
            recorder.record(kind, {'step': 0, 'value': int(current and kind == changed)})
        auxiliary = frame(1)
        if current and image_changed:
            auxiliary['rgb'][0, 0, 0] = 1
        path = directory / 'aux.npz'
        np.savez_compressed(path, **{k: auxiliary[k] for k in probe.prior.base.FRAME_KEYS})
        recorder.record('auxiliary_capture', {'artifact': 'aux.npz', 'artifact_sha256': file_hash(path),
            'phase': 'close_or_hold', 'control': 0, 'capture_sim_time': .5})
        recorder.record('endpoint', {'step': 0, 'native_phase': 'close_or_hold',
            'value': int(current and changed == 'endpoint')})
        if not current:
            recorder.record('action_started', {'token': 'MV_UP', 'step': 1})
            recorder.record('termination', {'reason': 'closed'})
        recorder.close()
        return directory
    populate(source, False)
    directory = populate(tmp_path / 'current', True)
    result = []
    return SimpleNamespace(output=directory, record=lambda kind, data: result.append((kind, data))), result


def test_gate_matches_full_scientific_first_grasp_prefix_and_stops_before_old_lift(tmp_path, monkeypatch):
    recorder, result = prefix_fixture(tmp_path, monkeypatch)
    probe.verify_first_grasp(recorder, 'whole-close', 0, 0)
    assert len(result) == 1 and result[0][0] == 'first_GRASP_prefix_verified'
    assert result[0][1]['exact_image_captures'] == 2
    assert result[0][1]['next_token'] == 'GRASP' and not result[0][1]['archived_controls_used']
    probe.verify_first_grasp(SimpleNamespace(output=Path('/no-source')), 'whole-close', 1, 1)


@pytest.mark.parametrize('changed', ['control_started', 'native_before', 'native_after', 'control_completed', 'action_completed', 'endpoint'])
def test_any_first_grasp_scientific_mismatch_rejected(tmp_path, monkeypatch, changed):
    recorder, result = prefix_fixture(tmp_path, monkeypatch, changed=changed)
    with pytest.raises(ValueError, match='prefix data mismatch'):
        probe.verify_first_grasp(recorder, 'whole-close', 0, 0)
    assert result == []


def test_first_grasp_auxiliary_image_array_mismatch_rejected_even_when_hashes_valid(tmp_path, monkeypatch):
    recorder, result = prefix_fixture(tmp_path, monkeypatch, image_changed=True)
    with pytest.raises(ValueError, match='RGB/depth/K/T mismatch'):
        probe.verify_first_grasp(recorder, 'whole-close', 0, 0)
    assert result == []


def test_new_stage_order_contains_only_both_close_cells(tmp_path):
    recorder = RunRecorder(tmp_path / 'run', {}, {'run_id': 'test'})
    calls = []
    probe.prior.execute_stages(recorder, lambda condition, stage: calls.append((condition, stage)), order=probe.ORDER)
    recorder.close()
    assert calls == [('whole-close', 'collect'), ('whole-close', 'replay'), ('neck-close', 'collect'), ('neck-close', 'replay')]
    with pytest.raises(ValueError, match='close anchors'):
        probe.intervention('whole-open_hold')
