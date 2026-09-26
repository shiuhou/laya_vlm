import numpy as np
import pytest

from embodied_runtime.experiments.proprio_frame_consistency import angle, model_packet, qmatrix, static_mount


def test_quaternion_orders_and_right_side_mount():
    q = [0., 0., np.sqrt(.5), np.sqrt(.5)]
    rz = qmatrix(q)
    assert np.allclose(rz, [[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    assert np.allclose(rz, qmatrix([q[3], *q[:3]], 'wxyz'))
    rx = qmatrix([np.sqrt(.5), 0, 0, np.sqrt(.5)])
    assert not np.allclose(rx@rz, rz@rx)
    assert angle(rz) == pytest.approx(90.)
    with pytest.raises(ValueError):
        qmatrix([0, 0, 0, 0])


def test_fixed_mount_relative_world_rotation_cancels():
    a = qmatrix([.1, .2, .3, .9]); b = qmatrix([.3, .2, .1, .9])
    mount = qmatrix([0, 0, -np.sqrt(.5), np.sqrt(.5)])
    assert np.allclose((a@mount)@(b@mount).T, a@b.T, atol=1e-15)


def test_static_transform_translation_composes_in_parent_axes():
    c = {'bodies': [{'name': 'eef', 'parent': 'robot0_right_hand', 'joints': [],
                    'position_parent_m': [1., 0., 0.],
                    'quaternion_parent_wxyz': [np.sqrt(.5), 0., 0., np.sqrt(.5)]}],
         'sites': [{'name': 'gripper0_grip_site', 'body': 'eef',
                    'position_body_m': [1., 0., 0.], 'quaternion_body_wxyz': [1., 0., 0., 0.]}]}
    p, r, chain = static_mount(c)
    assert np.allclose(p, [1., 1., 0.])
    assert angle(r) == pytest.approx(90.)
    assert chain == ['eef']
    c['bodies'][0]['joints'] = [{'name': 'moving'}]
    with pytest.raises(ValueError):
        static_mount(c)


def test_existing_proprioception_and_model_effects_ignore_quaternion():
    sensor = {'returned_observations': {'robot0_eef_pos': [1., 2., 3.],
        'robot0_gripper_qpos': [.03, -.03], 'robot0_eef_quat': [0., 0., 0., 1.]},
        'command': [0, 0, 0, 0, 0, 0, -1], 'read_sim_time_s': .5}
    first = model_packet(sensor, [1.1, 2.2, 3.3])
    assert first == model_packet(sensor, [1.1, 2.2, 3.3], poison=True)
    assert first['effects']['effects']['GRASP'] == {'source': 'unknown', 'privileged': False, 'values': {}}
