"""Pure fixed-point versus own-pad proxy arithmetic, not target/grasp inference."""
from __future__ import annotations

import numpy as np

from .proprio_frame_consistency import qmatrix


def point_to_box_distance(point, center, half_sizes):
    outside = np.maximum(np.abs(np.asarray(point)-center)-half_sizes, 0.)
    return float(np.linalg.norm(outside))


def point_jaw_relation(point_world, site_position_world, site_rotation_world, finger_joints):
    """Explicit consistent site frame; no target identity or trajectory argument."""
    p, origin = np.asarray(point_world, float), np.asarray(site_position_world, float)
    rotation, joints = np.asarray(site_rotation_world, float), np.asarray(finger_joints, float)
    if (p.shape != (3,) or origin.shape != (3,) or rotation.shape != (3, 3)
            or joints.shape != (2,) or not all(np.isfinite(v).all() for v in (p, origin, rotation, joints))
            or not np.allclose(rotation.T@rotation, np.eye(3), atol=1e-10, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-10, rtol=0)):
        raise ValueError('finite own-site rigid pose, fixed point and two signed joints required')
    q1, q2 = joints
    local = rotation.T@(p-origin)
    left = np.array([-q1-.0035, 0., -.0036])
    right = np.array([-q2+.0035, 0., -.0036])
    half = np.array([.004, .008, .008])
    gap_low, gap_high = -q1+.0005, -q2-.0005
    midpoint = np.array([-(q1+q2)/2, 0., -.0036])
    gap = gap_high-gap_low
    return {'fixed_point_in_site_m': local.tolist(),
            'fixed_point_relative_to_facing_gap_midpoint_m': (local-midpoint).tolist(),
            'world_TCP_to_fixed_point_m': float(np.linalg.norm(p-origin)),
            'signed_finger_joints_m': joints.tolist(), 'encoder_aperture_m': float(np.abs(joints).sum()),
            'static_facing_pad_gap_m': float(gap),
            'facing_gap_x_interval_m': [float(gap_low), float(gap_high)],
            'pad_y_interval_m': [-.008, .008], 'pad_z_interval_m': [-.0116, .0044],
            'point_minus_low_facing_plane_m': float(local[0]-gap_low),
            'high_facing_plane_minus_point_m': float(gap_high-local[0]),
            'inside_nonnegative_gap_prism': bool(gap >= 0 and gap_low <= local[0] <= gap_high
                                                and -.008 <= local[1] <= .008 and -.0116 <= local[2] <= .0044),
            'left_pad_box_point_distance_m': point_to_box_distance(local, left, half),
            'right_pad_box_point_distance_m': point_to_box_distance(local, right, half),
            'target_center_extent_identity_or_grasp_fit_established': False}


def returned_packet_relation(point_world, observation, body_to_site_rotation):
    """Returned position is already the site origin; apply only orientation mount."""
    rotation = qmatrix(observation['robot0_eef_quat'])@np.asarray(body_to_site_rotation)
    return point_jaw_relation(point_world, observation['robot0_eef_pos'], rotation,
                              observation['robot0_gripper_qpos'])
