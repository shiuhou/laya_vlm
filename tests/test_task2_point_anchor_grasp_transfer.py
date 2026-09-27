from contextlib import contextmanager, nullcontext
import inspect
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_point_anchor_grasp_transfer as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


def own(x=0):
    return {key: [x, 0., 0.] for key in probe.base.OBS_KEYS}


def frame(seq=1, sim_time=.5):
    return {'rgb': np.zeros((2, 2, 3), np.uint8), 'depth_m': np.zeros((2, 2), np.float32),
        'intrinsics': np.eye(3), 'camera_to_world': np.eye(4), 'capture_seq': seq,
        'capture_sim_time': sim_time, 'camera_name': 'fake'}


def test_hooks_keep_legacy_defaults():
    assert inspect.signature(probe.base.collect).parameters['after_approach'].default is None
    assert inspect.signature(probe.base.observe_controls).parameters['expected_grip'].default == -1
    assert inspect.signature(probe.base.observe_controls).parameters['after_control'].default is None
    assert inspect.signature(probe.base.replay).parameters['after_control'].default is None


def prefix_fixture(tmp_path, monkeypatch):
    original, current = tmp_path / 'source' / 'whole', tmp_path / 'current'
    monkeypatch.setattr(probe, 'SOURCE', tmp_path / 'source')
    termination = {'reason': 'rule_no_strict_nominal_improvement', 'first_contact_evaluator_only': None,
                   'attempted_actions': 1, 'completed_actions': 1, 'last_step': 1, 'grasp_attempted': False}
    def populate(recorder, changed=None):
        recorder.capture(frame())
        recorder.record('initial_frame_gate', {'own': own()})
        for kind in ('decision', 'control_started', 'native_before', 'native_after', 'control_completed', 'action_completed', 'endpoint'):
            recorder.record(kind, {'step': 0, 'value': 1 if kind == changed else 0})
        recorder.record('decision', {'step': 1, 'selected': 'STOP'})
    source = RunRecorder(original, {}, {'run_id': 'old'})
    populate(source)
    source.record('termination', termination)
    source.close()
    def collect(changed=None):
        recorder = RunRecorder(current, {}, {'run_id': 'fresh'})
        populate(recorder, changed)
        recorder.close()
        return current
    return termination, collect


def test_prefix_requires_exact_fresh_scientific_records_but_ignores_envelopes(tmp_path, monkeypatch):
    termination, collect = prefix_fixture(tmp_path, monkeypatch)
    result = probe.verify_prefix(collect(), 'whole', termination)
    assert result['exact_primary_captures'] == 1
    assert not result['archived_controls_used'] and not result['source_state_restored']
    assert not result['approach_STOP_executed']


@pytest.mark.parametrize('changed', ['decision', 'control_started', 'native_before', 'native_after',
                                     'control_completed', 'action_completed', 'endpoint'])
def test_any_prefix_scientific_mismatch_blocks_intervention(tmp_path, monkeypatch, changed):
    termination, collect = prefix_fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='prefix mismatch'):
        probe.verify_prefix(collect(changed), 'whole', termination)


@pytest.mark.parametrize('reason', ['new_robot_contact', 'action_budget', 'endpoint_veto_zero_remaining_pool', 'execution_contract_violation'])
def test_nonrule_approach_termination_rejects_before_read_or_action(reason):
    with pytest.raises(ValueError, match='Original no-improvement STOP'):
        probe.verify_prefix('/does-not-exist', 'whole', {'reason': reason, 'first_contact_evaluator_only': None})


def synthetic_suffix(tmp_path, monkeypatch, condition, *, fail=None, failure_action=0, prefix_ok=True, factory=None):
    from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
    sensors = own(-99)
    calls, stale_reads = [], []
    world = SimpleNamespace(data=SimpleNamespace(time=.5), obs=sensors)
    def step(command):
        world.data.time += .05
        stale_reads.append(world.obs['robot0_eef_pos'][0])
        return own(len(stale_reads)), 0, False, {}
    world.env = SimpleNamespace(step=step, sim=SimpleNamespace(get_state=lambda: np.array([world.data.time])))
    backend = SimpleNamespace(world=world, step_m=.01, _grip_cmd=-1,
                              proprioception=lambda: {'tcp_pos_world_m': [0, 0, 0]})
    class Camera:
        def __init__(self, _world):
            self.capture_seq = 0
        def capture(self):
            self.capture_seq += 1
            return frame(self.capture_seq, world.data.time)
    monkeypatch.setattr(LiberoRgbdSource, '__init__', Camera.__init__)
    monkeypatch.setattr(LiberoRgbdSource, 'capture', Camera.capture)
    monkeypatch.setattr(probe.local, 'read_only_measurement', lambda _: nullcontext())
    monkeypatch.setattr(probe.observations, 'evaluation', lambda _: {
        'valid_grasp_relation': False, 'bottle_center_mm': [0, 0, 0], 'contacts': [{'hand': 'poison'}]})
    monkeypatch.setattr(probe.local, 'contact_snapshot', lambda *_: {'contacts': [{'geom_names': ['hand', 'bottle'], 'normal_force_N': .1}]})
    def prefix(*_):
        if not prefix_ok:
            raise ValueError('prefix deliberately mismatched')
        return {'exact': True}
    monkeypatch.setattr(probe, 'verify_prefix', prefix)
    @contextmanager
    def native(_world, recorder, phase, step, tracking, groups):
        contact = {'unexpected_robot_contact': fail == 'contact' and len(calls) == failure_action}
        rows = [{'control': i // 25, 'before': {'contacts': [contact]}, 'after': {'contacts': [contact]}} for i in range(200)]
        if fail == 'count' and len(calls) == failure_action:
            rows.pop()
        yield rows
    monkeypatch.setattr(probe.local, 'native_observer', native)
    def execute(token):
        index = len(calls)
        calls.append(token)
        backend._grip_cmd = 1 if token == 'GRASP' else backend._grip_cmd
        if fail == 'runtime' and index == failure_action:
            raise RuntimeError('synthetic runtime failure')
        for _ in range(8):
            world.obs = world.env.step([0., 0., 0., 0., 0., 0., backend._grip_cmd])[0]
        return {'execution_contract_violation': fail == 'validator' and index == failure_action,
                'execution_contract_reason': ['synthetic'], 'environment_step_count': 8}
    recorder = RunRecorder(tmp_path / 'run', {}, {'run_id': 'synthetic'})
    camera = Camera(world)
    recorder.capture(camera.capture())
    recorder.record('initial_frame_gate', {'initial_own_observations': own(-99)})
    suffix = probe.Intervention(condition) if factory is None else factory(condition)
    termination = {'completed_actions': 30, 'attempted_actions': 30, 'last_step': 30, 'reason': 'rule_no_strict_nominal_improvement'}
    result, error = None, None
    try:
        result = suffix(backend=backend, executor=SimpleNamespace(execute=execute), camera=camera,
                        recorder=recorder, groups={}, approach=termination)
        recorder.record('termination', result)
    except (RuntimeError, ValueError) as exc:
        error = exc
    finally:
        recorder.close()
        suffix.seal(recorder.output)
    rows, errors = load_records(recorder.output / 'episodes.jsonl')
    assert not errors
    return SimpleNamespace(calls=calls, rows=rows, result=result, error=error, suffix=suffix,
                           directory=recorder.output, world=world, stale_reads=stale_reads)


@pytest.mark.parametrize('condition,tokens,grip', [('whole-close', ['GRASP', 'MV_UP'], 1),
    ('whole-open_hold', ['STOP', 'MV_UP'], -1), ('neck-close', ['GRASP', 'MV_UP'], 1),
    ('neck-open_hold', ['STOP', 'MV_UP'], -1)])
def test_fixed_suffix_retains_weak_lift_and_exact_jaw_and_returned_packet(tmp_path, monkeypatch, condition, tokens, grip):
    trial = synthetic_suffix(tmp_path, monkeypatch, condition)
    assert trial.error is None and trial.calls == tokens
    assert trial.result['scripted_completed_actions'] == 2
    assert trial.result['grasp_attempted'] == (grip == 1)
    controls = [r['data'] for r in trial.rows if r['kind'] == 'control_completed']
    assert len(controls) == 16 and all(r['command'][-1] == grip for r in controls)
    captures = [r['data'] for r in trial.rows if r['kind'] == 'vision_capture']
    assert [r['capture_seq'] for r in captures] == [1, 2, 3]
    aux = [r['data'] for r in trial.rows if r['kind'] == 'auxiliary_capture']
    assert len(aux) == 16 and [r['source_capture_seq'] for r in aux] == list(range(1, 17))
    assert aux[0]['own_tcp_world_m'][0] == 1 and trial.stale_reads[0] == -99
    assert all(a['own_observations'] == c['returned_own_observations'] for a, c in zip(aux, controls))
    assert all(a['cached_geometry_sample_time_s'] is None and a['exact_observation_sample_time_s'] is None for a in aux)
    assert len(trial.suffix.labels) == 16 and not any(r['label']['valid_grasp_relation'] for r in trial.suffix.labels)
    assert trial.suffix.labels[-1]['raw_contact_snapshot']['contacts'][0]['geom_names'] == ['hand', 'bottle']
    manifest = probe.base.read(trial.directory / 'sensor-captures.json')
    assert [r['capture_id'] for r in manifest] == list(range(17))
    assert manifest[0]['tcp_source_field'] == 'initial_frame_gate.initial_own_observations.robot0_eef_pos'
    assert all('label' not in r and 'contacts' not in r and 'bottle_center_mm' not in r for r in manifest)
    seal = probe.base.read(trial.directory / 'sensor-seal.json')
    assert all(file_hash(trial.directory / p) == h for p, h in seal['sha256'].items())
    probe.check_collection(trial.directory)


@pytest.mark.parametrize('failure', ['runtime', 'validator', 'contact', 'count'])
@pytest.mark.parametrize('failure_action', [0, 1])
def test_failure_preserves_completed_endpoint_and_stops_tail(tmp_path, monkeypatch, failure, failure_action):
    trial = synthetic_suffix(tmp_path, monkeypatch, 'whole-close', fail=failure, failure_action=failure_action)
    assert trial.error is not None and trial.calls == ['GRASP', 'MV_UP'][:failure_action + 1]
    failure_row = [r['data'] for r in trial.rows if r['kind'] == 'intervention_failure'][0]
    assert failure_row['scripted_attempted_actions'] == failure_action + 1 and failure_row['no_retry']
    assert failure_row['token'] == trial.calls[-1] and failure_row['grasp_attempted']
    completed = failure_action + (failure != 'runtime')
    assert failure_row['total_attempted_actions'] == 30 + failure_action + 1
    assert failure_row['total_completed_actions'] == 30 + completed
    assert failure_row['step'] == 30 + failure_action
    assert failure_row['phase'] == ('close_or_hold', 'lift')[failure_action]
    assert sum(r['kind'] == 'action_completed' for r in trial.rows) == completed
    assert sum(r['kind'] == 'endpoint' for r in trial.rows) == completed
    assert len(trial.suffix.sensors) == completed * 8
    with pytest.raises(ValueError, match='stop matrix'):
        probe.check_collection(trial.directory)


def test_prefix_failure_executes_no_suffix_control(tmp_path, monkeypatch):
    trial = synthetic_suffix(tmp_path, monkeypatch, 'whole-close', prefix_ok=False)
    assert isinstance(trial.error, ValueError) and trial.calls == []
    assert not trial.suffix.sensors and not trial.suffix.labels


@pytest.mark.parametrize('failure_action', [0, 1])
def test_collector_suffix_failure_never_labels_approach_counters_as_totals(tmp_path, monkeypatch, failure_action):
    from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
    from embodied_runtime.experiments.privileged_multistage_task import WineBottleBottomDrawerAdapter
    world = SimpleNamespace(model=SimpleNamespace(opt=SimpleNamespace(timestep=.002, integrator=0)),
        data=SimpleNamespace(time=.5), gripper_geoms=[1, 2], scene=SimpleNamespace(geoms=[3]), obs=own(),
        env=SimpleNamespace(sim=SimpleNamespace(model=SimpleNamespace(geom_id2name=lambda g: f'{g}_pad_collision'))))
    backend = SimpleNamespace(world=world, step_m=.01, _grip_cmd=-1, close=lambda: None,
        proprioception=lambda: {'tcp_pos_world_m': [0., 0., 0.], 'gripper_width_m': .08, 'gripper_command': 'OPEN'})
    monkeypatch.setattr(WineBottleBottomDrawerAdapter, 'make_backend', lambda *_a, **_k: backend)
    monkeypatch.setattr(LiberoRgbdSource, '__init__', lambda *_: None)
    monkeypatch.setattr(LiberoRgbdSource, 'capture', lambda _: frame())
    measurements = ModuleType('jev_libero.measurements')
    measurements.Measurements = lambda _: SimpleNamespace(ids=lambda _: {1, 2})
    monkeypatch.setitem(sys.modules, 'jev_libero.measurements', measurements)
    monkeypatch.setattr(probe.base, 'read_only_measurement', lambda _: nullcontext())
    monkeypatch.setattr(probe.base, 'contact_snapshot', lambda *_: {'contacts': [], 'time_s': .5})
    review, protocol = tmp_path / 'review.txt', tmp_path / 'protocol.md'
    review.write_text('synthetic')
    protocol.write_text('synthetic')
    point = {'position_world_m': [0., 0., 0.], 'definition': 'fixed'}
    def suffix(**context):
        assert context['approach']['completed_actions'] == 0
        raise RuntimeError(f'invalid suffix action {failure_action}')
    args = SimpleNamespace(output=str(tmp_path / 'run'), review=str(review))
    with pytest.raises(RuntimeError, match='invalid suffix'):
        probe.base.collect(args, preflight_fn=lambda _: ({}, point, frame()),
                           protocol=protocol, after_approach=suffix)
    rows, errors = load_records(tmp_path / 'run' / 'episodes.jsonl')
    assert not errors
    for row in rows:
        if row['kind'] in ('failure', 'termination'):
            data = row['data']
            assert data['approach_attempted_actions'] == data['approach_completed_actions'] == data['approach_step'] == 0
            assert not {'attempted_actions', 'completed_actions', 'step', 'total_attempted_actions', 'total_completed_actions'} & data.keys()


def test_fixed_stage_order_and_failure_never_retries_or_continues(tmp_path):
    expected = [(condition, stage) for condition in probe.ORDER for stage in ('collect', 'replay')]
    for failure_at in range(9):
        recorder = RunRecorder(tmp_path / str(failure_at), {}, {'run_id': 'test'})
        calls = []
        def launch(condition, stage):
            calls.append((condition, stage))
            if len(calls) - 1 == failure_at:
                raise RuntimeError('failed')
        if failure_at < 8:
            with pytest.raises(RuntimeError):
                probe.execute_stages(recorder, launch)
            assert calls == expected[:failure_at + 1]
        else:
            probe.execute_stages(recorder, launch)
            assert calls == expected
        recorder.close()


def test_auxiliary_replay_checks_all_arrays_times_and_own_packets(tmp_path, monkeypatch):
    trial = synthetic_suffix(tmp_path, monkeypatch, 'neck-open_hold')
    verifier = probe.AuxiliaryReplay(trial.directory)
    for row in trial.suffix.sensors:
        trial.world.data.time = row['capture_sim_time']
        trial.world.obs = row['own_observations']
        verifier(trial.world, {'step': row['after_step'], 'native_phase': row['phase']}, row['control'])
    assert not verifier.expected and len(verifier.checked) == 16


@pytest.mark.parametrize('changed', ['rgb', 'time', 'own', 'phase'])
def test_auxiliary_replay_rejects_first_mismatch(tmp_path, monkeypatch, changed):
    trial = synthetic_suffix(tmp_path, monkeypatch, 'neck-open_hold')
    row = trial.suffix.sensors[0]
    trial.world.data.time = row['capture_sim_time'] + (1 if changed == 'time' else 0)
    trial.world.obs = own(999) if changed == 'own' else row['own_observations']
    if changed == 'rgb':
        from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
        original = LiberoRgbdSource.capture
        def corrupted(camera):
            result = original(camera)
            result['rgb'][0, 0, 0] = 1
            return result
        monkeypatch.setattr(LiberoRgbdSource, 'capture', corrupted)
    verifier = probe.AuxiliaryReplay(trial.directory)
    with pytest.raises(ValueError):
        verifier(trial.world, {'step': row['after_step'], 'native_phase': 'bad' if changed == 'phase' else row['phase']}, row['control'])
    assert not verifier.checked


def test_auxiliary_replay_rejects_duplicate_and_missing_source_keys(tmp_path):
    for n in (15, 16, 17):
        recorder = RunRecorder(tmp_path / str(n), {}, {'run_id': 'test'})
        for i in range(n):
            recorder.record('auxiliary_capture', {'after_step': 0, 'control': i % 15})
        recorder.close()
        with pytest.raises(ValueError, match='All 16'):
            probe.AuxiliaryReplay(recorder.output)


def test_review_binds_both_freeze_and_preflight(tmp_path):
    path = tmp_path / 'review'
    for content in ('PASS commit', 'PASS preflight', 'commit preflight'):
        path.write_text(content)
        with pytest.raises(ValueError, match='Prospective PASS'):
            probe.verify_review(path, 'commit', 'preflight')
    path.write_text('PASS commit preflight')
    probe.verify_review(path, 'commit', 'preflight')
