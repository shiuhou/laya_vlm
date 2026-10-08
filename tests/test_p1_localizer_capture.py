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
        sim=SimpleNamespace(forward=lambda: calls.append('forward')),
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
    def capture_bundle():
        calls.append('capture')
        return dict(views=views, proprio=proprio)
    def sensor_factory(world, **kwargs):
        assert kwargs['width'] == 384 and kwargs['height'] == 256
        assert kwargs['retained_gripper_command']() == 'OPEN'
        return SimpleNamespace(sensor_port=lambda: SimpleNamespace(capture=capture_bundle), close=lambda: calls.append('sensor_close'))
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
