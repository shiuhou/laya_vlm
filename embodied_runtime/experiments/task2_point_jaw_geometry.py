"""Pure fixed-point versus own-pad proxy arithmetic, not target/grasp inference."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .proprio_frame_consistency import RAW, HASHES, qmatrix, static_mount
from .records import code_identity, file_hash, load_records


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


def explain(output):
    """Select only start, first-contact-control brackets, and terminal own packets."""
    source = RAW/'task2-box-point-boundary-run-01'
    expected = 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771'
    if file_hash(source/'episodes.jsonl') != expected:
        raise ValueError('sealed approach source differs')
    records, errors = load_records(source/'episodes.jsonl')
    if errors:
        raise ValueError(errors)
    def one(kind, **keys):
        found = [r for r in records if r['kind'] == kind and all(r['data'].get(k) == v for k, v in keys.items())]
        if len(found) != 1:
            raise ValueError('ambiguous selected record: '+kind)
        return found[0]
    calibration_path = 'robot-geometry-observability-03/robot-calibration.json'
    point_path = 'task2-box-support-run-02/sensor-representation.json'
    for name in (calibration_path, point_path):
        if file_hash(RAW/name) != HASHES[name]:
            raise ValueError('fixed calibration or point changed')
    _, mount, _ = static_mount(json.loads((RAW/calibration_path).read_text()))
    point = json.loads((RAW/point_path).read_text())['point_P']['position_world_m']
    initial, first, terminal = one('initial_frame_gate'), one('first_new_robot_contact'), one('termination')
    contact = first['data']['first_observed_sample']
    start = one('control_started', step=contact['step'], control=contact['control'])
    end = one('control_completed', step=contact['step'], control=contact['control'])
    endpoint = one('endpoint', step=terminal['data']['last_step'])
    capture = one('vision_capture', capture_seq=endpoint['data']['capture_seq'])
    if initial['data']['cached_point']['position_world_m'] != point:
        raise ValueError('approach used a different point')
    selections = [
        ('start', initial, 'initial_own_observations', initial['data']['fresh_capture_sim_time_s']),
        ('first_contact_control_before', start, 'previous_returned_own_observations', start['data']['state_before'][0]),
        ('first_contact_control_after', end, 'returned_own_observations', end['data']['state_after'][0]),
        ('termination', endpoint, 'own_observations', capture['data']['capture_sim_time']),
    ]
    results = []
    for label, record, field, read_time in selections:
        own = record['data'][field]
        result = returned_packet_relation(point, own, mount)
        results.append({'label': label, 'source_record_seq': record['seq'], 'source_record_id': record['record_id'],
                        'source_field': field, 'read_or_control_boundary_time_s': read_time,
                        'exact_observable_sample_time_s': None, 'own_observations': own, 'geometry': result})
    native = next(r for r in records if r['record_id'] == contact['raw_record_id'])
    pairs = {tuple(sorted(x['geom_ids'])) for x in first['data']['new_pairs']}
    contact_description = [{k: c[k] for k in ('geom_ids', 'geom_names', 'normal_force_N')}
                           for c in native['data']['contacts'] if tuple(sorted(c['geom_ids'])) in pairs]
    report = {'code': code_identity(), 'source': str(source), 'source_sha256': expected,
        'source_manifest_sha256': file_hash(source/'manifest.json'), 'calibration_sha256': HASHES[calibration_path],
        'point_source_sha256': HASHES[point_path], 'fixed_point_world_m': point,
        'first_contact_evaluator_only': first['data'], 'first_contact_descriptions_evaluator_only': contact_description,
        'first_contact_exact_pose_available': False, 'snapshots': results,
        'terminal_gripper_command': endpoint['data']['proprioception']['gripper_command'],
        'source_terminal_TCP_to_P_m': endpoint['data']['live_tcp_to_fixed_proxy_m'],
        'new_physics_FK_model_calls': 0,
        'limitations': ['P is an unqualified fixed proxy, not bottle center/extent',
                        'returned position/quaternion/finger exact sample times unknown',
                        'native contact time is bracketed by control packets, not an exact pose sample',
                        'static pad geometry does not include finger-body or hand collision proxies',
                        'no prepose comparison, target fitting or new policy']}
    if abs(results[-1]['geometry']['world_TCP_to_fixed_point_m']-report['source_terminal_TCP_to_P_m']) > 1e-12:
        raise ValueError('terminal fixed-point distance differs')
    output = Path(output)
    output.mkdir(exist_ok=False)
    (output/'interpretation.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps([{k: r[k] for k in ('label', 'read_or_control_boundary_time_s', 'geometry')} for r in results], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    explain(parser.parse_args().output)
