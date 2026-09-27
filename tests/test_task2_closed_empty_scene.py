from contextlib import nullcontext
import copy
import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.experiments import task2_closed_empty_scene as probe
from embodied_runtime.experiments.records import RunRecorder, file_hash, load_records


def own(value=0.):
    return {key: [value] * size for key, size in zip(probe.base.OBS_KEYS, (3, 4, 2, 2), strict=True)}


def fake_backend(monkeypatch, failure=None):
    data = SimpleNamespace(time=12.1)
    for name in probe.STATE_FIELDS:
        setattr(data, name, np.zeros(26 if name == 'qpos' else 24 if name == 'qvel' else 3))
    for name in probe.CACHE_FIELDS:
        setattr(data, name, np.zeros((2, 3)))
    for name in probe.SOLVER_FIELDS:
        setattr(data, name, np.zeros(2))
    data.ncon, data.nefc = 1, 2
    data.contact = [SimpleNamespace(geom1=0, geom2=1, dist=-.001, pos=np.zeros(3),
        frame=np.eye(3).flatten(), dim=3, efc_address=0)]
    controller = SimpleNamespace(goal_pos=np.zeros(3), sim=object(), interpolator=None)
    robot = SimpleNamespace(controller=controller, gripper=SimpleNamespace(current_action=np.array([-1.])),
                            recent_values=SimpleNamespace(buffer=np.zeros(3)), torques=np.zeros(7))
    env = SimpleNamespace(cur_time=12.1, timestep=242, done=False, _obs_cache={'own': np.zeros(3)},
                          _observables={'jaw': SimpleNamespace(timer=0., value=np.zeros(2))})
    calls = []
    def forward():
        calls.append('forward')
        data.geom_xpos[:] = data.qpos[16]
        data.qacc[:] = 1.
        data.qacc_warmstart[:] = 2.
        data.efc_force[:] = 3.
        if failure == 'forward_robot':
            data.qpos[0] = 99.
    def refresh(*, force_update):
        assert force_update is True
        calls.append('refresh')
        env._observables['jaw'].timer += .002
        env._obs_cache['own'] = np.ones(3)
        if failure == 'refresh_controller':
            controller.goal_pos[0] = 99.
        return {**own(1.), 'oracle_object_pose': 'must not enter own packet'}
    env._get_observations = refresh
    world = SimpleNamespace(data=data, obs=own(), model=object(), mujoco=SimpleNamespace(
        mj_contactForce=lambda model, data, index, force: force.fill(float(data.efc_force[0]))),
        env=SimpleNamespace(env=env, robots=[robot], sim=SimpleNamespace(forward=forward,
        model=SimpleNamespace(geom_id2name=lambda index: ('wine_bottle_1_geom', 'table_collision')[index]))))
    backend = SimpleNamespace(world=world, _grip_cmd=-1., step_m=.01)
    monkeypatch.setattr(probe, 'checked_static', lambda: {})
    monkeypatch.setattr(probe, 'model_gate', lambda *_: (16, {'fixed': 'model'}))
    monkeypatch.setattr(probe, 'geometry_admission', lambda *_: {'evaluator_only': True, 'static': 'admitted'})
    monkeypatch.setattr(probe.prior.local, 'integration_fingerprint', lambda w: repr(w.data.qpos.tolist()))
    monkeypatch.setattr(probe.prior.local, 'read_only_measurement', lambda _: nullcontext())
    return backend, calls


@pytest.mark.parametrize('condition,expected', [('neck-present', 0.), ('neck-away', .35)])
def test_scene_event_changes_only_named_object_and_refreshes_once(monkeypatch, condition, expected):
    backend, calls = fake_backend(monkeypatch)
    records, captures = [], []
    probe.event(backend, condition, lambda k, d: records.append((k, d)),
                lambda stage, packet: captures.append((stage, packet)))
    assert calls == ['forward', 'refresh'] and backend.world.data.time == 12.1
    assert backend.world.data.qpos[16] == expected
    assert np.count_nonzero(backend.world.data.qpos) == int(expected != 0)
    assert captures == [('before', own()), ('after', own(1.))]
    assert not any('oracle' in key for _, packet in captures for key in packet)
    states = [d for k, d in records if k == 'scene_state']
    assert [s['stage'] for s in states] == ['before', 'after_write', 'after_forward', 'after_refresh']
    leafs = states[1]['changes']
    qpos_changes = [x for x in leafs if x['path'].startswith('/state/qpos/')]
    assert [x['path'] for x in qpos_changes] == (['/state/qpos/16'] if expected else [])
    assert any(x['path'].startswith('/observable_state/') for x in states[3]['changes'])
    assert states[0]['audit']['contact_solver']['contacts'][0]['force_contact_frame'] == [0.] * 6
    assert states[2]['audit']['contact_solver']['contacts'][0]['force_contact_frame'] == [3.] * 6
    assert any(x['path'] == '/contact_solver/named_solver_buffers/efc_force/sha256'
               for x in states[2]['changes'])
    assert records[-1][1]['physics_controls'] == 0


@pytest.mark.parametrize('failure,expected_calls', [('forward_robot', ['forward']),
                                                    ('refresh_controller', ['forward', 'refresh'])])
def test_illegal_synchronization_mutation_stops_event_before_post_capture(monkeypatch, failure, expected_calls):
    backend, calls = fake_backend(monkeypatch, failure)
    captures, records = [], []
    with pytest.raises(ValueError, match='synchronization changed'):
        probe.event(backend, 'neck-away', lambda k, d: records.append((k, d)),
                    lambda stage, _: captures.append(stage))
    assert calls == expected_calls and captures == ['before']
    assert not any(k == 'scene_intervention_completed' for k, _ in records)


@pytest.mark.parametrize('field,index', [('qpos', 0), ('qpos', 19), ('qvel', 16), ('ctrl', 0)])
def test_object_write_gate_rejects_hidden_robot_rotation_velocity_or_control_edit(monkeypatch, field, index):
    backend, _ = fake_backend(monkeypatch)
    before = probe.snapshot(backend)
    after = copy.deepcopy(before)
    after['state']['qpos'][16] += .35
    after['state'][field][index] += 1.
    with pytest.raises(ValueError, match='outside the named object'):
        probe.require_write(before, after, 16, [.35, 0., 0.])


def test_unsupported_own_packet_or_unstable_state_serialization_fails_closed():
    with pytest.raises(ValueError, match='Complete finite'):
        probe.own_packet({**own(), 'robot0_gripper_qvel': [float('nan'), 0.]})
    with pytest.raises(TypeError, match='Unsupported audit'):
        probe.document(object())


def fake_camera(monkeypatch):
    from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
    def init(self, world):
        self.world, self.capture_seq = world, 0
    def capture(self):
        self.capture_seq += 1
        value = int(round(self.world.data.qpos[16] * 100))
        return {'rgb': np.full((2, 2, 3), value, np.uint8), 'depth_m': np.ones((2, 2), np.float32),
            'intrinsics': np.eye(3), 'camera_to_world': np.eye(4), 'capture_seq': self.capture_seq,
            'capture_sim_time': float(self.world.data.time), 'camera_name': 'fake'}
    monkeypatch.setattr(LiberoRgbdSource, '__init__', init)
    monkeypatch.setattr(LiberoRgbdSource, 'capture', capture)


def source_event(tmp_path, monkeypatch, condition='neck-away', failure=None):
    backend, calls = fake_backend(monkeypatch, failure)
    fake_camera(monkeypatch)
    recorder = RunRecorder(tmp_path / 'source', {}, {'run_id': 'source'})
    suffix = probe.SceneSuffix(condition)
    if failure:
        with pytest.raises(ValueError):
            suffix.before_scene(backend=backend, recorder=recorder, groups={}, approach={'completed_actions': 29})
    else:
        suffix.before_scene(backend=backend, recorder=recorder, groups={}, approach={'completed_actions': 29})
    recorder.close()
    return recorder.output, suffix, calls


def test_exact_event_replay_preserves_discontinuity_and_consumes_one_event(tmp_path, monkeypatch):
    source, suffix, _ = source_event(tmp_path, monkeypatch)
    output = tmp_path / 'replay'
    output.mkdir()
    replay = probe.SceneReplay(source, output)
    with pytest.raises(ValueError, match='Unconsumed'):
        replay.finish()
    backend, calls = fake_backend(monkeypatch)
    replay(backend, {'step': 28})
    assert calls == []
    replay(backend, {'step': 29, 'native_phase': 'close_or_hold'})
    assert calls == ['forward', 'refresh']
    replay(backend, {'step': 30, 'native_phase': 'additional_close'})
    replay.finish()
    assert probe.base.read(output / 'scene-result.json')['status'] == 'passed'
    with pytest.raises(ValueError, match='Duplicate'):
        replay(backend, {'step': 29, 'native_phase': 'close_or_hold'})
    assert [r['source_capture_seq'] for r in suffix.sensors] == [1, 2]
    assert [r['phase'] for r in suffix.sensors] == ['scene_before', 'scene_after']
    assert suffix.sensors[1]['own_observations'] == own(1.)
    assert suffix.sensors[1]['exact_observation_sample_time_s'] is None
    assert suffix.sensors[1]['own_source']['boundary'] == 'after'


def test_partial_event_keeps_preimage_and_failure_without_admitting_replay(tmp_path, monkeypatch):
    source, suffix, _ = source_event(tmp_path, monkeypatch, failure='forward_robot')
    assert len(suffix.sensors) == 1
    assert (source / suffix.sensors[0]['artifact']).exists()
    rows, _ = load_records(source / 'episodes.jsonl')
    assert rows[-1]['kind'] == 'scene_intervention_failure'
    assert rows[-1]['data']['no_retry']
    with pytest.raises(ValueError, match='Complete scene'):
        probe.SceneReplay(source, tmp_path / 'replay')


def test_replay_rejects_actual_image_change(tmp_path, monkeypatch):
    source, _, _ = source_event(tmp_path, monkeypatch)
    output = tmp_path / 'replay'
    output.mkdir()
    replay = probe.SceneReplay(source, output)
    backend, _ = fake_backend(monkeypatch)
    from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
    original = LiberoRgbdSource.capture
    def changed(camera):
        frame = original(camera)
        frame['rgb'][0, 0, 0] ^= 1
        return frame
    monkeypatch.setattr(LiberoRgbdSource, 'capture', changed)
    with pytest.raises(ValueError, match='RGB/depth/K/T'):
        replay(backend, {'step': 29, 'native_phase': 'close_or_hold'})
    assert not (output / 'scene-result.json').exists()


def test_sensor_seal_includes_exact_named_own_controls_and_excludes_state_or_label(tmp_path, monkeypatch):
    source, suffix, _ = source_event(tmp_path, monkeypatch)
    # Append through a fresh independent fixture recorder; no alteration of a sealed journal.
    directory = tmp_path / 'controls'
    recorder = RunRecorder(directory, {}, {'run_id': 'controls'})
    recorder.record('action_started', {'step': 29, 'native_phase': 'close_or_hold'})
    recorder.record('control_completed', {'step': 29, 'control': 0, 'command': [0.] * 6 + [1.],
        'returned_own_observations': {**own(2.), 'object_pose': ['oracle']},
        'state_after': [12.15, 'oracle_full_state'], 'contacts': 'oracle_contact'})
    recorder.close()
    suffix = probe.SceneSuffix('neck-present')
    suffix.seal(directory)
    exported = probe.base.read(directory / 'own-controls.json')
    assert len(exported) == 1 and exported[0]['own_observations'] == own(2.)
    assert exported[0]['read_sim_time_s'] == 12.15
    assert 'oracle' not in str(exported)
    seal = probe.base.read(directory / 'sensor-seal.json')
    assert seal['sha256']['own-controls.json'] == file_hash(directory / 'own-controls.json')
    assert (directory / 'evaluator-only/labels.json').exists()


def test_generic_hooks_retain_previous_defaults():
    assert inspect.signature(probe.prior.Intervention).parameters['before_suffix'].default is None
    assert inspect.signature(probe.base.replay).parameters['before_action'].default is None
    assert inspect.signature(probe.base.replay).parameters['after_replay'].default is None
    assert probe.prior.Intervention('whole-close').before_suffix is None
    assert probe.SceneSuffix('neck-away').schedule == probe.SCHEDULE
    with pytest.raises(ValueError, match='fixed scene pair'):
        probe.SceneSuffix('whole-away')


@pytest.mark.parametrize('edit', ['unknown', 'missing', 'duplicate'])
def test_replay_rejects_unknown_missing_or_duplicate_scene_records(tmp_path, monkeypatch, edit):
    source, _, _ = source_event(tmp_path, monkeypatch)
    rows, _ = load_records(source / 'episodes.jsonl')
    recorder = RunRecorder(tmp_path / edit, {}, {'run_id': edit})
    for row in rows[1:]:
        if edit == 'missing' and row['kind'] == 'scene_state' and row['data']['stage'] == 'after_write':
            continue
        recorder.record(row['kind'], row['data'])
    if edit == 'unknown':
        recorder.record('scene_unknown_mutation', {'write': 'undeclared'})
    if edit == 'duplicate':
        recorder.record('scene_intervention_completed', rows[-1]['data'])
    recorder.close()
    with pytest.raises(ValueError, match='Unknown scene|complete ordered scene'):
        probe.SceneReplay(recorder.output, tmp_path / 'replay')


@pytest.mark.parametrize('contact_name', ['gripper0_pad', 'robot0_link', 'mount0_base', None])
@pytest.mark.parametrize('location', ['native_before', 'native_after', 'endpoint'])
def test_away_raw_contact_qualification_includes_zero_force_contacts(tmp_path, contact_name, location):
    suffix = probe.SceneSuffix('neck-away')
    recorder = RunRecorder(tmp_path / 'source', {}, {'run_id': 'source'})
    ordinary = {'geom_names': ['wine_bottle_1_geom', 'table_collision'], 'normal_force_N': 1.}
    target = {'geom_names': [contact_name, 'wine_bottle_1_geom'], 'normal_force_N': 0.} if contact_name else ordinary
    for index in range(200):
        for kind in ('native_before', 'native_after'):
            recorder.record(kind, {'step': 29, 'control': index // 25, 'index': index,
                'contacts': [target if index == 199 and location == kind else ordinary]})
    suffix.labels = [{'step': 29, 'control': i, 'raw_contact_snapshot': {
        'contacts': [target if i == 7 and location == 'endpoint' else ordinary]}} for i in range(8)]
    if contact_name:
        with pytest.raises(RuntimeError, match='invalidates_empty'):
            suffix.qualify_empty(recorder, 0, 29)
    else:
        suffix.qualify_empty(recorder, 0, 29)
    recorder.close()
    records, _ = load_records(recorder.output / 'episodes.jsonl')
    qualification = records[-1]['data']
    assert qualification['raw_robot_bottle_contact_absent'] is (contact_name is None)
    assert qualification['settled_empty_not_inferred']
    assert len(qualification['violations']) == int(contact_name is not None)
    assert suffix.after_primitive == suffix.qualify_empty


def test_present_qualification_has_no_away_gate():
    probe.SceneSuffix('neck-present').qualify_empty(None, 0, 29)


def test_base_replay_completion_hook_failure_cannot_write_passed_result(tmp_path, monkeypatch):
    backend, calls = fake_backend(monkeypatch)
    fake_camera(monkeypatch)
    backend.close = lambda: calls.append('close')
    from embodied_runtime.adapters.libero_rgbd import LiberoRgbdSource
    from embodied_runtime.experiments.privileged_multistage_task import WineBottleBottomDrawerAdapter
    monkeypatch.setattr(WineBottleBottomDrawerAdapter, 'make_backend', lambda *args, **kwargs: backend)
    monkeypatch.setattr(probe.base, 'read_only_measurement', lambda _: nullcontext())
    frozen = {name: {} for name in ('code', 'source_sha256', 'unchanged_source_sha256', 'point',
        'protocol_sha256', 'versions', 'stepping_sources', 'jev', 'environment')}
    review = tmp_path / 'review.txt'
    review.write_text('fixture')
    frozen['review_sha256'] = file_hash(review)
    recorder = RunRecorder(tmp_path / 'source', {}, {'run_id': 'source', **frozen})
    (recorder.output / 'review.txt').write_text('fixture')
    recorder.record('scene_intervention_intent', {'fixture': True})
    recorder.record('initial_frame_gate', {'groups_evaluator_only': {}})
    recorder.capture(LiberoRgbdSource(backend.world).capture())
    recorder.record('termination', {})
    recorder.close()
    def unfinished():
        calls.append('finish')
        raise ValueError('Unconsumed scene event')
    output = tmp_path / 'replay'
    with pytest.raises(ValueError, match='Unconsumed scene event'):
        probe.base.replay(SimpleNamespace(source=recorder.output, output=output),
            preflight_fn=lambda _: (frozen, None, None), before_action=lambda *_: None, after_replay=unfinished)
    assert calls == ['finish', 'close']
    assert (output / 'failure.json').exists() and not (output / 'result.json').exists()


@pytest.mark.parametrize('kind', ['scene_intervention_intent', 'scene_unknown_mutation'])
def test_base_replay_requires_scene_handler_before_any_world(tmp_path, monkeypatch, kind):
    from embodied_runtime.experiments.privileged_multistage_task import WineBottleBottomDrawerAdapter
    def forbidden(*args, **kwargs):
        pytest.fail('world must not be constructed')
    monkeypatch.setattr(WineBottleBottomDrawerAdapter, 'make_backend', forbidden)
    recorder = RunRecorder(tmp_path / 'source', {}, {'run_id': 'source'})
    recorder.record(kind, {})
    recorder.close()
    with pytest.raises(ValueError, match='handler required before constructing'):
        probe.base.replay(SimpleNamespace(source=recorder.output, output=tmp_path / 'replay'))
