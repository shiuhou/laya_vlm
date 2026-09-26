import numpy as np
import pytest

from embodied_runtime.experiments.task2_point_jaw_geometry import point_jaw_relation, returned_packet_relation
from embodied_runtime.experiments.proprio_frame_consistency import qmatrix


def test_gap_midpoint_width_and_point_box_distance_are_distinct():
    result = point_jaw_relation([0, 0, -.0036], [0, 0, 0], np.eye(3), [.04, -.04])
    assert result['static_facing_pad_gap_m'] == pytest.approx(.079)
    assert result['encoder_aperture_m'] == pytest.approx(.080)
    assert result['inside_nonnegative_gap_prism']
    assert result['left_pad_box_point_distance_m'] == pytest.approx(.0395)
    assert result['right_pad_box_point_distance_m'] == pytest.approx(.0395)
    assert result['fixed_point_relative_to_facing_gap_midpoint_m'] == [0, 0, 0]


def test_mounted_returned_pose_uses_site_origin_without_extra_offset():
    mount = qmatrix([0, 0, -np.sqrt(.5), np.sqrt(.5)])
    observation = {'robot0_eef_quat': [0, 0, 0, 1], 'robot0_eef_pos': [1, 2, 3],
                   'robot0_gripper_qpos': [.02, -.03]}
    result = returned_packet_relation([1.01, 2.02, 3.03], observation, mount)
    assert np.allclose(result['fixed_point_in_site_m'], [-.02, .01, .03])
    assert result['static_facing_pad_gap_m'] == pytest.approx(.049)
    assert not result['inside_nonnegative_gap_prism']


def test_gap_prism_membership_is_not_pad_contact_or_grasp():
    point = [-.0195, 0, -.0036]
    result = point_jaw_relation(point, [0, 0, 0], np.eye(3), [.02, -.02])
    assert result['left_pad_box_point_distance_m'] == pytest.approx(0.)
    assert not result['target_center_extent_identity_or_grasp_fit_established']
    with pytest.raises(ValueError):
        point_jaw_relation(point, [0, 0, 0], np.ones((3, 3)), [.02, -.02])
