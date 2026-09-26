from copy import deepcopy
from itertools import product

import numpy as np
import pytest

from embodied_runtime.decision_interface import shared_atomic_candidates
from embodied_runtime.experiments.robot_only_geometry import VERSION, quaternion_matrix
from embodied_runtime.experiments.task2_box_support import sensor_representation
from embodied_runtime.experiments.task2_observed_surface_sweep import (
    GEOMS, MOVES, compute, distances, own_packet, place, subtree, summarize, support)


def calibration():
    def body(name, parent, position, quaternion=(1., 0., 0., 0.), joints=()):
        return {'name': name, 'parent': parent, 'position_parent_m': list(position),
                'quaternion_parent_wxyz': list(quaternion), 'joints': list(joints)}
    def joint(number):
        return {'name': 'gripper0_finger_joint'+str(number), 'kind': 'slide',
                'qpos_reference': 0., 'anchor_body_m': [0., 0., 0.], 'axis_body': [-1., 0., 0.]}
    bodies = [body('robot0_base', None, [4., 5., 6.]),
              body('robot0_right_hand', 'robot0_base', [1., 2., 3.]),
              body('gripper0_right_gripper', 'robot0_right_hand', [0., 0., 0.], [2**-.5, 0., 0., -2**-.5]),
              body('gripper0_eef', 'gripper0_right_gripper', [0., 0., .097]),
              body('gripper0_leftfinger', 'gripper0_right_gripper', [-.0035, 0., .0934], joints=[joint(1)]),
              body('gripper0_rightfinger', 'gripper0_right_gripper', [.0035, 0., .0934], joints=[joint(2)])]
    geometries = [{'name': name, 'body': owner, 'position_body_m': [0., 0., 0.],
                   'quaternion_body_wxyz': [1., 0., 0., 0.],
                   'vertices_local_m': (cube()*[.004, .008, .008]).tolist(),
                   'shape_representation': 'synthetic_analytic_box'}
                  for name, owner in zip(GEOMS, ['gripper0_right_gripper', 'gripper0_leftfinger',
                    'gripper0_leftfinger', 'gripper0_rightfinger', 'gripper0_rightfinger'])]
    return {'version': VERSION, 'bodies': bodies, 'geometries': geometries,
            'sites': [{'name': 'gripper0_grip_site', 'body': 'gripper0_eef', 'position_body_m': [0., 0., 0.],
                       'quaternion_body_wxyz': [1., 0., 0., 0.]}]}


def packet():
    return {'robot0_eef_pos': [1., 2., 3.], 'robot0_eef_quat': [0., 0., 0., 1.],
            'robot0_gripper_qpos': [.02, -.03]}


def cube():
    return np.asarray(list(product((-1., 1.), repeat=3)))


def test_direct_site_placement_preserves_signed_jaws_and_static_pad_geometry():
    vertices, pose = place(subtree(calibration()), packet())
    assert list(vertices) == GEOMS
    rotation = np.asarray(pose['returned_site_rotation_world'])
    for name, center in [(GEOMS[2], [-.0235, 0., -.0036]), (GEOMS[4], [.0335, 0., -.0036])]:
        local = (vertices[name]-packet()['robot0_eef_pos']) @ rotation
        np.testing.assert_allclose(local.mean(axis=0), center, atol=1e-14, rtol=0)
        np.testing.assert_allclose(np.ptp(local, axis=0)/2, [.004, .008, .008], atol=1e-14, rtol=0)


def test_subtree_discards_arm_base_and_own_adapter_discards_scene_fields():
    original = calibration()
    poisoned = deepcopy(original)
    for body in poisoned['bodies']:
        if body['name'].startswith('robot0_') and body['name'] != 'robot0_right_hand':
            body['position_parent_m'] = [float('nan')]*3
            body['joints'] = [{'scene': 'excluded'}]
    assert subtree(original) == subtree(poisoned)
    obs = {**packet(), 'qpos': [float('nan')]*40, 'contacts': 'oracle', 'bottle_pose': [999]*7}
    assert own_packet(obs) == packet()
    with pytest.raises(ValueError, match='Only returned own'):
        place(subtree(original), obs)


def test_returned_pose_rotation_translation_covariance_without_extra_site_offset():
    base = packet()
    first, _ = place(subtree(calibration()), base)
    theta = .7
    q = [0., 0., np.sin(theta/2), np.cos(theta/2)]
    rotation = quaternion_matrix([q[3], *q[:3]])
    shift = np.array([-.4, .3, 1.2])
    moved = {**base, 'robot0_eef_quat': q, 'robot0_eef_pos': (rotation@base['robot0_eef_pos']+shift).tolist()}
    second, _ = place(subtree(calibration()), moved)
    for name in GEOMS:
        np.testing.assert_allclose(second[name], first[name]@rotation.T+shift, atol=1e-14, rtol=0)


def test_full_support_reuses_exact_inner_arithmetic_and_validity_convention():
    depth = np.linspace(.1, 2., 20*20).reshape(20, 20).astype(np.float32)
    depth[5, 5], depth[5, 6], depth[5, 7], depth[5, 8] = .0, np.nan, .01, 5.
    frame = {'rgb': np.zeros((20, 20, 3), np.uint8), 'depth_m': depth,
             'intrinsics': np.array([[12., 0., 7.], [0., 13., 8.], [0., 0., 1.]]), 'camera_to_world': np.eye(4)}
    saved = sensor_representation(frame, [2, 2, 18, 18])
    inner = support(depth, frame['intrinsics'], frame['camera_to_world'], saved['crop_xyxy'])
    expected = [{k: r[k] for k in ('pixel_xy', 'depth_m', 'position_world_m')} for r in saved['support_G']]
    assert inner == expected
    full = support(depth, frame['intrinsics'], frame['camera_to_world'], [2, 2, 18, 18])
    assert all(row in full for row in inner)
    assert [r['pixel_xy'] for r in full] == sorted([r['pixel_xy'] for r in full], key=lambda xy: (xy[1], xy[0]))


def test_sweep_contains_path_interior_and_stop_is_current_not_hold_simulation():
    points = np.array([[0., 0., 0.], [2., 0., 0.], [4., 0., 0.], [2., 2., 0.]])
    measured = distances(points, {'proxy': cube()}, np.array([4., 0., 0.]))
    np.testing.assert_allclose(measured['sweep']['distance'][:, 0], [0., 0., 0., 1.], atol=1e-13)
    assert measured['current']['distance'][1, 0] == 1.
    assert measured['endpoint']['distance'][1, 0] == 1.
    stop = distances(points, {'proxy': cube()}, np.zeros(3))
    for mode in ('endpoint', 'sweep'):
        for key in ('distance', 'closest', 'inside'):
            np.testing.assert_array_equal(stop[mode][key], stop['current'][key])


def test_union_preserves_jaw_gap_and_current_overlap_zeroes_every_sweep():
    geometries = {'left': cube()*.1+[-.3, 0., 0.], 'right': cube()*.1+[.3, 0., 0.]}
    points = np.array([[0., 0., 0.], [-.3, 0., 0.]])
    for delta in MOVES.values():
        result = distances(points, geometries, np.asarray(delta))
        assert result['current']['distance'][0].min() == pytest.approx(.2)
        assert result['sweep']['distance'][1].min() == 0.
        assert result['sweep']['distance'][0].min() > .18
        assert np.all(result['sweep']['distance'] <= result['current']['distance']+1e-12)


def test_witness_ties_row_major_then_proxy_and_empty_support_unknown():
    arrays = distances(np.zeros((2, 3)), {'a': cube(), 'b': cube()}, np.zeros(3))['current']
    rows = [{'pixel_xy': [1, 2], 'depth_m': 1., 'position_world_m': [0., 0., 0.]},
            {'pixel_xy': [2, 2], 'depth_m': 1., 'position_world_m': [0., 0., 0.]}]
    result = summarize(arrays, np.array([0, 1]), rows, ['a', 'b'])['union']
    assert result['exact_minimizer_count'] == 4
    assert result['nearest']['pixel_xy'] == [1, 2] and result['nearest']['proxy'] == 'a'
    empty = summarize(arrays, np.array([], int), rows, ['a', 'b'])['union']
    assert empty['minimum_m'] is None and empty['nearest'] is None


def test_worker_rejects_evaluator_fields_and_retains_existing_candidate_order(tmp_path):
    assert list(MOVES) == [c.token for c in shared_atomic_candidates() if c.token in MOVES]
    with pytest.raises(ValueError, match='Sanitized'):
        compute({'contacts': []}, tmp_path/'output')
