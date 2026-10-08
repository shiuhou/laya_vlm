"""Mocked capture lifecycle only: no simulator, GPU, model, or real frames."""
from types import SimpleNamespace

import numpy as np
import pytest

from embodied_runtime.contracts import ProtocolError, content_hash
from embodied_runtime.experiments import p1_localizer_capture as capture
from embodied_runtime.experiments.p1_segmentation_probe import read, write, seal, verify_seal
from embodied_runtime.sensor_api import Proprioception


def fake_capture(tmp_path, monkeypatch, *, fail_reset=False):
    monkeypatch.setattr(capture, 'code_identity', lambda: dict(commit='synthetic-test', dirty_status=''))
    monkeypatch.setattr(capture, 'versions', lambda: {})
    calls = []
    def native_reset():
        calls.append('native_reset')
        if fail_reset:
            raise RuntimeError('Synthetic RandomizationError; do not retry')
    def forbidden_wrapper_reset():
        pytest.fail('retrying wrapper reset was called')
    env = SimpleNamespace(env=SimpleNamespace(reset=native_reset), reset=forbidden_wrapper_reset,
        sim=SimpleNamespace(forward=lambda: calls.append('forward'), data=SimpleNamespace(time=1.),
            model=SimpleNamespace(camera_name2id=lambda name: (*capture.CAMERAS, 'frontview').index(name),
                cam_bodyid=np.array([0, 1, 0]), cam_mode=np.zeros(3, dtype=int),
                cam_pos=np.arange(9, dtype=float).reshape(3, 3), cam_quat=np.tile([1., 0., 0., 0.], (3, 1)),
                cam_fovy=np.full(3, 45.), body_id2name=lambda index: 'world')),
        seed=lambda seed: calls.append(('seed', seed)), step=lambda action: calls.append(('step', action)))
    world = SimpleNamespace(env=env, close=lambda: calls.append('world_close'))
    def factory(**kwargs):
        calls.append('constructor')
        return world, dict(synthetic_fixture=True)
    def audit_writer(world, output):
        output.mkdir()
        write(output/'oracle.json', dict(secret='ONLY_COLLECTOR_AUDIT', time=1234))
        seal(output)
        return dict(scene_fingerprint_sha256='f'*64)
    proprio = Proprioception(1., 10, (0., 0., 0.), (0., 0., 0., 1.), (0.,), None, True,
                            ('robot/1',), reason_codes=('WIDTH_UNCALIBRATED',))
    views = [dict(rgb=np.full((256, 384, 3), n*40, dtype=np.uint8), depth_m=np.ones((256, 384), dtype=np.float32),
        intrinsics_K=np.array([[200., 0, 192], [0, 200., 128], [0, 0, 1]]), T_base_camera=np.eye(4),
        camera_id=camera, frame_seq=1, frame_id=f'{camera}:1', calibration_version='synthetic',
        capture_sim_time_s=1., capture_monotonic_ns=10, frame='robot_base') for n, camera in enumerate(capture.CAMERAS)]
    def capture_bundle(selected):
        calls.append('capture')
        sequence = calls.count('capture')
        current = [dict(v, frame_seq=sequence, frame_id=f"{v['camera_id']}:{sequence}", capture_monotonic_ns=10+sequence) for v in selected]
        return dict(views=current, proprio=proprio)
    def sensor_factory(world, **kwargs):
        width, height = kwargs['width'], kwargs['height']
        assert width > 0 and height > 0
        assert kwargs['retained_gripper_command']() == 'OPEN'
        selected = [v for v in views if v["camera_id"] in kwargs["camera_names"]]
        if 'frontview' in kwargs['camera_names']:
            selected.append(dict(views[0], camera_id='frontview', frame_id='frontview:1'))
        selected = [dict(v, rgb=np.full((height, width, 3), n*40, dtype=np.uint8),
            depth_m=np.ones((height, width), dtype=np.float32),
            intrinsics_K=np.array([[height, 0, width/2], [0, height, height/2], [0, 0, 1]])) for n, v in enumerate(selected)]
        assert tuple(v['camera_id'] for v in selected) == kwargs['camera_names']
        return SimpleNamespace(sensor_port=lambda: SimpleNamespace(capture=lambda: capture_bundle(selected)), close=lambda: calls.append('sensor_close'))
    return calls, dict(factory=factory, sensor_factory=sensor_factory, audit_writer=audit_writer)


def test_one_native_reset_ten_settle_and_one_raw_bundle_with_separate_audit(tmp_path, monkeypatch):
    calls, inject = fake_capture(tmp_path, monkeypatch)
    root = tmp_path/'seed-42'
    result = capture.capture_seed(42, root, dev_only=True, **inject)
    assert calls.count('constructor') == calls.count('native_reset') == calls.count('capture') == 1
    steps = [x for x in calls if isinstance(x, tuple) and x[0] == 'step']
    assert len(steps) == 10 and all(action == list(capture.SETTLE_ACTION) for _, action in steps)
    assert result['explicit_reset_attempts'] == 1 and result['settle_ticks_completed'] == 10
    assert not result['heldout_claim'] and result['novelty_status'] == 'NOT_AUDITED'
    manifest = read(root/'sensor/manifest.json')
    assert len(manifest['source_identities']) == 2
    assert manifest['oracle_inputs'] is False and manifest['recording'] == 'frames'
    assert 'ONLY_COLLECTOR_AUDIT' not in (root/'sensor/manifest.json').read_text()
    assert 'collector-audit' not in (root/'sensor/manifest.json').read_text()
    assert calls[-2:] == ['sensor_close', 'world_close']
    verify_seal(root)
    with pytest.raises(FileExistsError):
        capture.capture_seed(42, root, dev_only=True, **inject)


def test_first_randomization_failure_is_preserved_without_settle_capture_retry(tmp_path, monkeypatch):
    calls, inject = fake_capture(tmp_path, monkeypatch, fail_reset=True)
    root = tmp_path/'failure'
    with pytest.raises(RuntimeError, match='RandomizationError'):
        capture.capture_seed(43, root, dev_only=True, **inject)
    failure = read(root/'failure.json')
    assert failure['stage'] == 'NATIVE_RESET' and failure['explicit_reset_attempts'] == 1
    assert failure['retry_count'] == 0 and failure['replacement_seed'] is None
    assert calls.count('native_reset') == 1 and 'capture' not in calls
    assert not any(isinstance(c, tuple) and c[0] == 'step' for c in calls)
    assert calls[-1] == 'world_close'
    verify_seal(root)
    with pytest.raises(ProtocolError):
        capture.capture_seed(44, tmp_path/'forbidden', dev_only=False, **inject)
    assert not (tmp_path/'forbidden').exists()


def test_scene_fingerprint_excludes_time_and_robot_noise_but_retains_object_motion():
    data = SimpleNamespace(body_xpos=np.array([[1., 2., 3.]]), body_xquat=np.array([[1., 0., 0., 0.]]),
        get_joint_qpos=lambda name: .12, time=1., qvel=np.array([0.]), qpos=np.array([.1]))
    model = SimpleNamespace(body_name2id=lambda name: 0, body_pos=np.array([[1., 2., 3.]]), body_quat=np.array([[1., 0., 0., 0.]]))
    obj = SimpleNamespace(root_body='cabinet', joints=['drawer'])
    env = SimpleNamespace(env=SimpleNamespace(fixtures_dict={'cabinet': obj}, objects_dict={}), sim=SimpleNamespace(model=model, data=data))
    before = content_hash(capture.scene_layout(env))
    data.time = 2.
    data.qpos[0] = .9
    data.qvel[0] = .7
    assert content_hash(capture.scene_layout(env)) == before
    data.body_xpos[0, 0] += .01
    assert content_hash(capture.scene_layout(env)) != before


def test_fixed_workspace_camera_lookat_axes_and_mount_rejection(tmp_path, monkeypatch):
    config = capture.WORKSPACE_FRONT
    rotation = capture.camera_look_at_rotation(config['position_world_m'], config['look_at_world_m'], config['world_up'])
    forward = np.array(config['look_at_world_m'])-np.array(config['position_world_m'])
    assert np.allclose(rotation @ [0, 0, -1], forward/np.linalg.norm(forward))
    assert np.allclose(rotation.T@rotation, np.eye(3)) and np.isclose(np.linalg.det(rotation), 1)
    assert (rotation @ [0, 1, 0])[2] > 0
    with pytest.raises(ProtocolError, match='parallel'):
        capture.camera_look_at_rotation([0, 0, 0], [0, 0, 1], [0, 0, 1])
    _, inject = fake_capture(tmp_path, monkeypatch)
    world, _ = inject['factory']()
    model = world.env.sim.model
    before = model.cam_pos.copy()
    model.cam_bodyid[2] = 1
    with pytest.raises(ProtocolError, match='world-mounted'):
        capture.configure_workspace_camera(world)
    assert np.array_equal(model.cam_pos, before)
    model.cam_bodyid[2] = 0
    result = capture.configure_workspace_camera(world)
    assert np.array_equal(model.cam_pos[:2], before[:2])
    assert model.cam_pos[2].tolist() == config['position_world_m']
    assert result['no_scene_state_used_for_aim'] and result['original_camera_configs_preserved']


def test_optin_camera_flag_adds_third_sensor_and_separate_configuration(tmp_path, monkeypatch):
    calls, inject = fake_capture(tmp_path, monkeypatch)
    root = tmp_path/'workspace'
    capture.capture_seed(42, root, dev_only=True, workspace_front=True, **inject)
    manifest = read(root/'sensor/manifest.json')
    assert manifest['cameras'] == [*capture.CAMERAS, 'frontview']
    assert len(manifest['source_identities']) == 3 and calls.count('capture') == 1
    config = read(root/'collector-audit/workspace-camera.json')
    assert config['position_world_m'] == [0., .7, 1.35]
    assert config['camera_mount_body_id'] == 0 and config['vertical_fov_deg'] == 45.
    verify_seal(root)


def sequence_fixture(*, first_cost_ns=250_000_000, fail_second=False):
    import io
    clock = SimpleNamespace(value=0)
    steps, messages = [], []
    calls = [0]
    def sleep(seconds):
        clock.value += round(seconds*1e9)
    def acquire():
        calls[0] += 1
        if fail_second and calls[0] == 2:
            raise RuntimeError('synthetic sensor failure')
        captured = clock.value
        clock.value += first_cost_ns if calls[0] == 1 else 10_000_000
        return dict(views=[dict(camera_id='frontview', frame_seq=calls[0], capture_monotonic_ns=captured,
                               capture_sim_time_s=len(steps)/20)], proprio={})
    def append(views, proprio, *, emitted_monotonic_ns):
        messages.append(dict(captured=views[0]['capture_monotonic_ns'], emitted=emitted_monotonic_ns))
        return SimpleNamespace(message_id=f'test/bundle/{len(messages)}')
    sensor = SimpleNamespace(sensor_port=lambda: SimpleNamespace(capture=acquire))
    world = SimpleNamespace(env=SimpleNamespace(step=lambda action: steps.append(action)))
    recorder = SimpleNamespace(episode_id='synthetic', append=append)
    events = io.StringIO()
    return world, sensor, recorder, events, clock, sleep, steps, messages


def test_continuous_slots_preserve_real_lateness_drop_and_timestamps():
    import json
    world, sensor, recorder, events, clock, sleep, steps, messages = sequence_fixture()
    schedule = capture.capture_schedule(frames=4, capture_hz=10)
    stats = capture.record_sequence(world, sensor, recorder, events, schedule,
                                    clock_ns=lambda: clock.value, sleep=sleep)
    rows = [json.loads(line) for line in events.getvalue().splitlines()]
    assert [r['status'] for r in rows] == ['CAPTURED', 'DROPPED_DEADLINE', 'CAPTURED', 'CAPTURED']
    assert stats['captured_bundles'] == 3 and stats['dropped_slots'] == 1
    assert [m['captured'] for m in messages] == [0, 250_000_000, 300_000_000]
    assert rows[2]['scheduled_monotonic_ns'] == 200_000_000
    assert rows[2]['view_capture_monotonic_ns'] == [250_000_000]
    assert len(steps) == 6 and all(s == list(capture.SETTLE_ACTION) for s in steps)
    assert stats['geometry_or_tracking_throughput_measured'] is False
    assert capture.capture_schedule(duration_s=.35, capture_hz=10)['planned_slots'] == 4
    with pytest.raises(ProtocolError):
        capture.capture_schedule(frames=4, duration_s=1.)


def test_continuous_failure_keeps_failed_and_remaining_unattempted_slots():
    import json
    world, sensor, recorder, events, clock, sleep, steps, messages = sequence_fixture(first_cost_ns=10_000_000, fail_second=True)
    with pytest.raises(RuntimeError, match='sensor failure'):
        capture.record_sequence(world, sensor, recorder, events, capture.capture_schedule(frames=4),
                                clock_ns=lambda: clock.value, sleep=sleep)
    statuses = [json.loads(line)['status'] for line in events.getvalue().splitlines()]
    assert statuses == ['CAPTURED', 'FAILED', 'NOT_ATTEMPTED_AFTER_FAILURE', 'NOT_ATTEMPTED_AFTER_FAILURE']
    assert len(messages) == 1


def test_frontview_only_is_explicit_and_preserves_default_single_frame(tmp_path, monkeypatch):
    calls, inject = fake_capture(tmp_path, monkeypatch)
    root = tmp_path/'front-only'
    capture.capture_seed(42, root, dev_only=True, workspace_front=True, frontview_only=True, **inject)
    manifest = read(root/'sensor/manifest.json')
    assert manifest['cameras'] == ['frontview'] and manifest['frame_bundle_count'] == 1
    assert manifest['capture_statistics']['continuous_hold_ticks'] == 0
    assert calls.count('capture') == 1
    with pytest.raises(ProtocolError, match='requires'):
        capture.capture_seed(43, tmp_path/'invalid-front', dev_only=True, frontview_only=True, **inject)


def test_native_dimensions_reach_sensor_receipt_and_recorded_calibration(tmp_path, monkeypatch):
    from embodied_runtime.perception.recording import replay_frames
    _, inject = fake_capture(tmp_path, monkeypatch)
    root = tmp_path/'native768'
    capture.capture_seed(42, root, dev_only=True, workspace_front=True, frontview_only=True,
                         width=768, height=512, **inject)
    manifest = read(root/'sensor/manifest.json')
    assert (manifest['width'], manifest['height']) == (768, 512)
    assert manifest['resolution_source'] == 'native_simulator_render_no_interpolation'
    _, views = next(replay_frames(root/'sensor/frames'))
    assert views[0]['rgb'].shape == (512, 768, 3) and views[0]['depth_m'].shape == (512, 768)
    assert views[0]['intrinsics_K'][0][2] == 384 and views[0]['intrinsics_K'][1][2] == 256
    for width, height in ((0, 256), (384, -1), (True, 256)):
        with pytest.raises(ProtocolError, match='dimensions'):
            capture.capture_seed(43, tmp_path/'invalid-resolution', dev_only=True, width=width, height=height, **inject)


def test_render_priming_retains_cold_timing_without_world_step_capability():
    import json
    world, sensor, recorder, events, clock, sleep, steps, messages = sequence_fixture(first_cost_ns=400_000_000)
    stats = capture.record_warmup(sensor, recorder, events, 1, clock_ns=lambda: clock.value)
    rows = [json.loads(line) for line in events.getvalue().splitlines()]
    assert stats['captured_bundles'] == 1 and stats['wall_elapsed_s'] == .4
    assert stats['cold_start_is_preserved'] and stats['simulator_steps'] == 0
    assert rows[0]['capture_duration_s'] == .4 and rows[0]['oldest_view_age_at_write_s'] == .4
    assert messages[0]['captured'] == 0 and messages[0]['emitted'] == 400_000_000
    assert steps == []  # No world/step handle is passed to the priming function.


def test_priming_raw_and_sources_are_separate_from_timed_frames(tmp_path, monkeypatch):
    from embodied_runtime.perception.recording import replay_frames
    calls, inject = fake_capture(tmp_path, monkeypatch)
    root = tmp_path/'warm'
    capture.capture_seed(42, root, dev_only=True, workspace_front=True, frontview_only=True,
                         warmup_captures=1, **inject)
    manifest = read(root/'sensor/manifest.json')
    assert len(list(replay_frames(root/'sensor/warmup-frames'))) == 1
    assert len(list(replay_frames(root/'sensor/frames'))) == 1
    assert len(manifest['warmup_source_identities']) == len(manifest['source_identities']) == 1
    assert manifest['warmup_recording'] == 'warmup-frames'
    assert manifest['warmup_statistics']['reason'] == 'GPU_RENDER_INITIALIZATION'
    assert manifest['capture_statistics']['cadence_condition'] == 'EXPLICIT_RENDER_PRIMING_COMPLETE'
    assert calls.count('capture') == 2
    assert len([x for x in calls if isinstance(x, tuple) and x[0] == 'step']) == 10
    warm_view = next(replay_frames(root/'sensor/warmup-frames'))[1][0]
    timed_view = next(replay_frames(root/'sensor/frames'))[1][0]
    assert warm_view['canonical_frame_id'] != timed_view['canonical_frame_id']
    assert warm_view['capture_sim_time_s'] == timed_view['capture_sim_time_s']
    assert warm_view['frame_seq'] == 1 and timed_view['frame_seq'] == 2
    verify_seal(root)
